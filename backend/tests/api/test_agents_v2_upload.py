"""agents/v2/upload endpoint'i için güvenlik ve işlevsellik testleri.

Amaç:
- **Auth zorunlu**: token olmadan 401.
- **Uzantı whitelist**: izinsiz suffix → 400.
- **Boyut limiti**: 20 MB + 1 → 413.
- **Path traversal koruması**: dosya adı UUID'e mapleniyor (orijinal disk'e
  yazılmıyor).
- **Başarılı yükleme**: file_path, original_name, size_bytes, suffix döner.
"""

from __future__ import annotations

import io

from fastapi.testclient import TestClient


def test_upload_rejects_anonymous(client: TestClient) -> None:
    """JWT olmadan 401 döner — anonymous upload yasak."""
    resp = client.post(
        "/api/v1/agents/v2/upload",
        files={"file": ("doc.txt", io.BytesIO(b"hello"), "text/plain")},
    )
    assert resp.status_code == 401, resp.text


# ────────────────────────────────────────────────────────────────
# Auth-gerektiren testler — DB migration zincirine bağımlı.
# `auth_headers` fixture'ı başarısız olursa pytest otomatik skip eder.
# ────────────────────────────────────────────────────────────────
import pytest


def _skip_if_no_admin(auth_headers):
    if not auth_headers.get("Authorization"):
        pytest.skip("admin token alınamadı — DB migration eksik olabilir")


def test_upload_rejects_bad_extension(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    _skip_if_no_admin(auth_headers)
    resp = client.post(
        "/api/v1/agents/v2/upload",
        files={"file": ("bad.exe", io.BytesIO(b"x"), "application/octet-stream")},
        headers=auth_headers,
    )
    assert resp.status_code == 400
    detail = resp.json().get("detail", "")
    assert ".exe" in detail or "Desteklenmeyen" in detail


def test_upload_success_returns_uuid_path(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    _skip_if_no_admin(auth_headers)
    payload = b"# Test markdown\nContent here."
    resp = client.post(
        "/api/v1/agents/v2/upload",
        files={"file": ("readme.md", io.BytesIO(payload), "text/markdown")},
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["suffix"] == ".md"
    assert data["original_name"] == "readme.md"
    assert data["size_bytes"] == len(payload)
    # Path traversal koruması: orijinal "readme.md" adı disk'te olmamalı;
    # UUID hex + .md olmalı.
    assert "readme.md" not in data["file_path"]
    assert data["file_path"].endswith(".md")


def test_upload_rejects_oversize(
    client: TestClient, auth_headers: dict[str, str], monkeypatch
) -> None:
    """20 MB limitinin üstündeki yükleme 413 döner."""
    _skip_if_no_admin(auth_headers)
    # Gerçek 20 MB yaratmak yavaş — küçük limit ile hızlı doğrula
    from app.domains.agents.v2 import router as r_mod

    monkeypatch.setattr(r_mod, "_MAX_UPLOAD_BYTES", 10)
    resp = client.post(
        "/api/v1/agents/v2/upload",
        files={"file": ("big.txt", io.BytesIO(b"0" * 50), "text/plain")},
        headers=auth_headers,
    )
    assert resp.status_code == 413, resp.text
    assert "çok büyük" in resp.json().get("detail", "").lower()


def test_upload_accepts_all_whitelisted_suffixes(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    _skip_if_no_admin(auth_headers)
    for name, suffix in [
        ("a.pdf", ".pdf"),
        ("b.docx", ".docx"),
        ("c.txt", ".txt"),
        ("d.json", ".json"),
        ("e.csv", ".csv"),
    ]:
        resp = client.post(
            "/api/v1/agents/v2/upload",
            files={"file": (name, io.BytesIO(b"x"), "application/octet-stream")},
            headers=auth_headers,
        )
        assert resp.status_code == 201, (name, resp.text)
        assert resp.json()["suffix"] == suffix
