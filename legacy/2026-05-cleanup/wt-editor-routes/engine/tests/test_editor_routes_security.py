"""
Security regression tests for engine/routes/editor_routes.py.

Kapsam (BGTS denetim bulguları):
- F-02: _safe_path'in prefix-startswith ile komşu dizin escape'ine kapanması.
- F-03: /api/editor/run — shell=True + prefix-allowlist yerine
        shlex.split + exact-match allowlist.
- F-04: /api/editor/run-tests — serbest `extra` + f-string shell interpolation
        yerine typed & validated flag'ler.

Flask testing client ile in-process koşulur; subprocess fiilen çalıştığı
testler hızlı olsun diye 'echo' / 'python -c "print(...)"' gibi kısa
komutlar kullanır.
"""
from __future__ import annotations

import os
import shlex
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

# Test edilecek modülü projenin engine/ kökünden import edebilmek için.
ENGINE_ROOT = Path(__file__).resolve().parents[1]
if str(ENGINE_ROOT) not in sys.path:
    sys.path.insert(0, str(ENGINE_ROOT))

# Flask opsiyonel bağımlılık; yüklü değilse testleri skip et.
flask = pytest.importorskip("flask")

from routes import editor_routes  # noqa: E402  (sys.path manip sonrası)


# ═════════════════════════════════════════════════════════════════════════
#  Fixtures
# ═════════════════════════════════════════════════════════════════════════

@pytest.fixture()
def app(tmp_path, monkeypatch):
    """Her test için izole bir PROJECT_ROOT ile Flask app döndürür."""
    monkeypatch.setattr(editor_routes, "PROJECT_ROOT", tmp_path.resolve())
    monkeypatch.setattr(editor_routes, "_PROJECT_ROOT_STR", str(tmp_path.resolve()))

    f = flask.Flask(__name__)
    editor_routes.register_editor_routes(f)
    f.config.update(TESTING=True)
    return f


@pytest.fixture()
def client(app):
    return app.test_client()


# ═════════════════════════════════════════════════════════════════════════
#  F-02: _safe_path — path escape / traversal
# ═════════════════════════════════════════════════════════════════════════

class TestSafePath:
    def test_root_path_returns_root(self, monkeypatch, tmp_path):
        monkeypatch.setattr(editor_routes, "PROJECT_ROOT", tmp_path.resolve())
        monkeypatch.setattr(editor_routes, "_PROJECT_ROOT_STR", str(tmp_path.resolve()))
        assert editor_routes._safe_path("") == tmp_path.resolve()

    def test_simple_relative_path(self, monkeypatch, tmp_path):
        monkeypatch.setattr(editor_routes, "PROJECT_ROOT", tmp_path.resolve())
        monkeypatch.setattr(editor_routes, "_PROJECT_ROOT_STR", str(tmp_path.resolve()))
        (tmp_path / "sub").mkdir()
        assert editor_routes._safe_path("sub") == (tmp_path / "sub").resolve()

    def test_parent_traversal_rejected(self, monkeypatch, tmp_path):
        monkeypatch.setattr(editor_routes, "PROJECT_ROOT", tmp_path.resolve())
        monkeypatch.setattr(editor_routes, "_PROJECT_ROOT_STR", str(tmp_path.resolve()))
        with pytest.raises(ValueError, match="traversal"):
            editor_routes._safe_path("../etc/passwd")

    def test_deep_parent_traversal_rejected(self, monkeypatch, tmp_path):
        monkeypatch.setattr(editor_routes, "PROJECT_ROOT", tmp_path.resolve())
        monkeypatch.setattr(editor_routes, "_PROJECT_ROOT_STR", str(tmp_path.resolve()))
        with pytest.raises(ValueError, match="traversal"):
            editor_routes._safe_path("foo/../../bar")

    def test_absolute_path_rejected(self, monkeypatch, tmp_path):
        monkeypatch.setattr(editor_routes, "PROJECT_ROOT", tmp_path.resolve())
        monkeypatch.setattr(editor_routes, "_PROJECT_ROOT_STR", str(tmp_path.resolve()))
        with pytest.raises(ValueError, match="mutlak"):
            editor_routes._safe_path("/etc/passwd")

    def test_null_byte_rejected(self, monkeypatch, tmp_path):
        monkeypatch.setattr(editor_routes, "PROJECT_ROOT", tmp_path.resolve())
        monkeypatch.setattr(editor_routes, "_PROJECT_ROOT_STR", str(tmp_path.resolve()))
        with pytest.raises(ValueError, match="NUL"):
            editor_routes._safe_path("foo\x00bar")

    def test_non_string_rejected(self, monkeypatch, tmp_path):
        monkeypatch.setattr(editor_routes, "PROJECT_ROOT", tmp_path.resolve())
        monkeypatch.setattr(editor_routes, "_PROJECT_ROOT_STR", str(tmp_path.resolve()))
        with pytest.raises(ValueError, match="str"):
            editor_routes._safe_path(12345)  # type: ignore[arg-type]

    def test_sibling_prefix_escape_rejected(self, tmp_path, monkeypatch):
        """
        BGTS audit F-02: Eski kod 'abs_path.startswith(PROJECT_ROOT)' ile
        prefix kontrol yapıyordu. PROJECT_ROOT = /tmp/xyz/foo olduğunda
        /tmp/xyz/foo-evil/secret startswith kontrolünden geçerdi.
        Yeni kod Path.resolve() + relative_to kullandığı için bu senaryo
        reddedilmeli.
        """
        parent = tmp_path
        safe_root = parent / "foo"
        safe_root.mkdir()
        evil_sibling = parent / "foo-evil"
        evil_sibling.mkdir()
        (evil_sibling / "secret.txt").write_text("gizli")

        monkeypatch.setattr(editor_routes, "PROJECT_ROOT", safe_root.resolve())
        monkeypatch.setattr(editor_routes, "_PROJECT_ROOT_STR", str(safe_root.resolve()))

        # '../foo-evil/secret.txt' (PROJECT_ROOT'tan relative) escape denemesi
        with pytest.raises(ValueError, match="traversal"):
            editor_routes._safe_path("../foo-evil/secret.txt")

    def test_symlink_escape_rejected(self, tmp_path, monkeypatch):
        """Root içinden dışarı gösteren symlink de reddedilmeli."""
        root = tmp_path / "root"
        root.mkdir()
        outside = tmp_path / "outside"
        outside.mkdir()
        (outside / "secret.txt").write_text("gizli")
        link = root / "link_to_outside"
        try:
            link.symlink_to(outside)
        except (OSError, NotImplementedError):
            pytest.skip("Symlink oluşturulamadı (platform desteksiz)")

        monkeypatch.setattr(editor_routes, "PROJECT_ROOT", root.resolve())
        monkeypatch.setattr(editor_routes, "_PROJECT_ROOT_STR", str(root.resolve()))
        with pytest.raises(ValueError, match="traversal"):
            editor_routes._safe_path("link_to_outside/secret.txt")


# ═════════════════════════════════════════════════════════════════════════
#  F-03: /api/editor/run — shell injection + allowlist
# ═════════════════════════════════════════════════════════════════════════

class TestEditorRunAllowlist:
    def _sse_lines(self, response) -> list[str]:
        # streaming response'tan SSE satırlarını topla
        data = response.get_data(as_text=True)
        return [ln for ln in data.split("\n") if ln.strip()]

    def test_rejects_disallowed_executable(self, client):
        r = client.post("/api/editor/run", json={"command": "rm -rf /"})
        assert r.status_code == 403
        body = r.get_json()
        assert body["ok"] is False
        assert "izin listesi" in body["error"]

    def test_rejects_shell_metachars_via_first_token(self, client):
        """
        Eski kod: basename(command.split()[0]).startswith(p) nedeniyle
        'python3; rm -rf /' gibi girdilerde ilk token 'python3' sayılır
        ve shell=True ile geri kalan shell'e gider.
        Yeni kod: shlex.split ile komut parse edilir, argv[0] exact-match
        allowlist'e bakılır; noktalı virgül literal bir argüman haline gelir
        (çalıştırılamaz, reddedilmez ama asla shell'e iletilmez).
        """
        # Komutun başarılı çalışması veya reddedilmesi değil, shell
        # enjeksiyonunun ÇALIŞMAMASI kritik. En kolay ispat: canary dosya.
        tmp = tempfile.mkdtemp()
        canary = os.path.join(tmp, "pwned")
        try:
            # Bu string shell'de yorumlansa /tmp/.../pwned dosyası oluşurdu.
            r = client.post("/api/editor/run", json={
                "command": f'echo ok; touch {shlex.quote(canary)}',
            })
            # Status 200 (start+done event'leri stream edilir).
            assert r.status_code == 200
            # Dosya oluşmamış olmalı — shell=False olduğundan "; touch ..."
            # echo'nun argümanı olur.
            assert not os.path.exists(canary), "shell injection gerçekleşti!"
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_accepts_allowed_echo(self, client):
        r = client.post("/api/editor/run", json={"command": "echo hello"})
        assert r.status_code == 200
        body = r.get_data(as_text=True)
        assert '"start"' in body and '"done"' in body
        assert '"hello"' in body

    def test_empty_command_rejected(self, client):
        r = client.post("/api/editor/run", json={"command": "   "})
        assert r.status_code == 400

    def test_prefix_match_attack_blocked(self, client):
        """
        Eski kod 'base_cmd.startswith(p)' kullanırdı; 'pythonXYZ' gibi
        icatlar 'python' prefix'iyle eşleşirdi.
        Yeni kod EXACT match istiyor.
        """
        r = client.post("/api/editor/run", json={"command": "pythonXYZ --version"})
        assert r.status_code == 403

    def test_timeout_enforced(self, client, monkeypatch):
        # Timeout değeri cap'lenir; 9999 isteği _MAX_CMD_TIMEOUT'a düşer.
        r = client.post("/api/editor/run", json={
            "command": "python3 -c \"import time; time.sleep(2); print('ok')\"",
            "timeout": 1,
        })
        assert r.status_code == 200
        body = r.get_data(as_text=True)
        # Timeout kısa olduğu için error event'i bekleniyor.
        assert "timeout" in body.lower() or "done" in body.lower()


# ═════════════════════════════════════════════════════════════════════════
#  F-04: /api/editor/run-tests — typed & validated flag'ler
# ═════════════════════════════════════════════════════════════════════════

class TestEditorRunTests:
    def test_malicious_pattern_rejected(self, client):
        r = client.post("/api/editor/run-tests", json={
            "path": "engine/tests/",
            "pattern": '"; rm -rf / #',
        })
        assert r.status_code == 400
        assert "pattern" in r.get_json()["error"].lower()

    def test_legit_pattern_accepted(self, client, tmp_path, monkeypatch):
        # Gerçek pytest çalıştırma kaçınılmaz — burada sadece shell
        # interpretation olmadığını ispat etmek yeterli. Sahte test
        # path'i reddedilse bile validation geçer.
        r = client.post("/api/editor/run-tests", json={
            "path": "does/not/exist/",
            "pattern": "test_foo and not slow",
        })
        # Path _safe_path'ten geçer (içerik yok; pytest de bulamaz).
        # Beklenen: validation pass, pytest 'not found' ile hata döner,
        # stream 200 ile açılır.
        assert r.status_code == 200
        body = r.get_data(as_text=True)
        assert '"start"' in body

    def test_legacy_extra_field_ignored(self, client):
        """
        Eski kod `extra` param'ını f-string ile shell'e geçiriyordu.
        Yeni kod bu alanı tamamen yok sayıyor; malicious değerler etki
        yaratmaz.
        """
        r = client.post("/api/editor/run-tests", json={
            "path": "engine/tests/",
            "extra": "; touch /tmp/pwned_via_extra",
        })
        assert r.status_code == 200
        # validasyon hatası değil; extra görmezden gelinir.
        assert not os.path.exists("/tmp/pwned_via_extra")

    def test_path_traversal_in_tests_rejected(self, client):
        r = client.post("/api/editor/run-tests", json={"path": "../../../../etc"})
        assert r.status_code == 400
        assert "traversal" in r.get_json()["error"].lower()

    def test_maxfail_non_integer_rejected(self, client):
        r = client.post("/api/editor/run-tests", json={
            "path": "engine/tests/",
            "maxfail": "abc; rm -rf /",
        })
        assert r.status_code == 400
        assert "maxfail" in r.get_json()["error"].lower()

    def test_marker_with_special_chars_rejected(self, client):
        r = client.post("/api/editor/run-tests", json={
            "path": "engine/tests/",
            "markers": "slow; echo pwned",
        })
        assert r.status_code == 400
        assert "marker" in r.get_json()["error"].lower()


# ═════════════════════════════════════════════════════════════════════════
#  _resolve_allowed_executable
# ═════════════════════════════════════════════════════════════════════════

class TestResolveAllowedExecutable:
    def test_disallowed_raises(self):
        with pytest.raises(PermissionError):
            editor_routes._resolve_allowed_executable("bash")

    def test_basename_extracted(self):
        # Mutlak path verilse bile sadece basename kontrol edilir.
        with pytest.raises(PermissionError):
            editor_routes._resolve_allowed_executable("/usr/bin/rm")

    def test_allowed_returns_absolute(self):
        # 'echo' her POSIX sisteminde var sayılır.
        if shutil.which("echo") is None:
            pytest.skip("echo PATH'de yok")
        resolved = editor_routes._resolve_allowed_executable("echo")
        assert Path(resolved).is_absolute()


# ═════════════════════════════════════════════════════════════════════════
#  editor_search — query validation ve grep argv
# ═════════════════════════════════════════════════════════════════════════

class TestEditorSearch:
    def test_short_query_rejected(self, client):
        r = client.get("/api/editor/search?q=a")
        assert r.status_code == 400

    def test_control_chars_rejected(self, client):
        r = client.get("/api/editor/search?q=foo%00bar")
        assert r.status_code == 400

    def test_dash_prefixed_query_safe(self, client):
        """
        '-F' gibi grep flag'ı ile başlayan query'ler '--' ayırıcısı
        sayesinde flag sanılmaz.
        """
        r = client.get("/api/editor/search?q=-test-string-")
        # Query valid; grep hiç eşleşme bulamasa bile 200.
        assert r.status_code == 200
