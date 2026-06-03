"""
Cortex MCP Server
═══════════════════════════════════════════════════════════════════════════

Cortex/Neurex test-otomasyon motorunun yeteneklerini **Model Context Protocol**
(MCP) tool'ları olarak dışa açar. Böylece Cursor, Claude Desktop veya başka bir
MCP istemcisi Cortex'i doğrudan sürebilir: "şu siteyi keşfet ve testleri üret",
"bu test neden fail oldu?", "bu Jira ticket'ından test çıkar" gibi.

(Octomind MCP server muadili — dış AI agent'ların Cortex'i çağırabilmesi için.)

Mimari: Bu süreç KULLANICININ makinesinde çalışır ve Cortex engine'in HTTP
API'sine ``X-Internal-Key`` ile proxy yapar. Engine container'ında çalışmaz.

Çalıştırma (stdio transport — Claude Desktop/Cursor için):
    CORTEX_ENGINE_URL=http://localhost:5001 \
    CORTEX_INTERNAL_KEY=<engine internal key> \
    python cortex_mcp.py

İstemci yapılandırması için bkz. README.md.
"""
from __future__ import annotations

import os
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP

ENGINE_URL = os.environ.get("CORTEX_ENGINE_URL", "http://localhost:5001").rstrip("/")
INTERNAL_KEY = os.environ.get("CORTEX_INTERNAL_KEY", "")
TIMEOUT = float(os.environ.get("CORTEX_MCP_TIMEOUT", "180"))

mcp = FastMCP("cortex")


def _post(path: str, payload: dict) -> dict[str, Any]:
    """Engine'e kimlikli POST proxy."""
    headers = {"Content-Type": "application/json"}
    if INTERNAL_KEY:
        headers["X-Internal-Key"] = INTERNAL_KEY
    resp = httpx.post(f"{ENGINE_URL}{path}", json=payload, headers=headers, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def _get(path: str) -> dict[str, Any]:
    headers = {"X-Internal-Key": INTERNAL_KEY} if INTERNAL_KEY else {}
    resp = httpx.get(f"{ENGINE_URL}{path}", headers=headers, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()


# ── Tool'lar ─────────────────────────────────────────────────────────────────

@mcp.tool()
def discover_tests(url: str, max_pages: int = 8, max_flows: int = 6) -> dict:
    """Bir web uygulamasını otonom keşfet ve kritik kullanıcı akışları için
    çalıştırılabilir testler üret.

    Args:
        url: Hedef uygulamanın başlangıç URL'si.
        max_pages: Gezilecek maksimum sayfa sayısı.
        max_flows: Üretilecek maksimum akış (test) sayısı.

    Returns: Keşfedilen akışlar + üretilen Gherkin feature'lar + istatistik.
    """
    return _post("/api/discovery/run", {
        "url": url, "max_pages": max_pages, "max_flows": max_flows, "persist": True,
    })


@mcp.tool()
def crawl_site(url: str, max_pages: int = 8) -> dict:
    """Bir uygulamayı crawl edip sayfa yapısını (buton/input/form) döndür —
    test üretmeden sadece keşif.
    """
    return _post("/api/discovery/crawl", {"url": url, "max_pages": max_pages})


@mcp.tool()
def analyze_test_failure(
    test_name: str,
    error_message: str,
    stack_trace: str = "",
    failed_step: str = "",
) -> dict:
    """Başarısız bir testin kök nedenini sınıflandır ve açıkla.

    Kategoriler: PRODUCT_BUG, TEST_ISSUE, ENVIRONMENT, AUTOMATION_DEBT, UNKNOWN.

    Returns: kategori, güven, açıklama, kanıt ve önerilen düzeltme.
    """
    return _post("/api/rca/analyze", {
        "test_name": test_name, "error_message": error_message,
        "stack_trace": stack_trace, "failed_step": failed_step,
    })


@mcp.tool()
def generate_tests_from_requirement(text: str, title: str = "", gherkin: bool = True) -> dict:
    """Bir gereksinim/PRD metninden yapısal test case'leri (ve opsiyonel Gherkin) üret.

    Args:
        text: Ham gereksinim/kabul kriteri metni.
        title: Opsiyonel başlık.
        gherkin: True ise her case için çalıştırılabilir feature da üretilir.
    """
    return _post("/api/connectors/text-to-tests", {
        "text": text, "title": title, "gherkin": gherkin, "persist": True,
    })


@mcp.tool()
def jira_issue_to_tests(issue_key: str) -> dict:
    """Bir Jira issue'sundan (özet+açıklama) test case'leri üret.

    Engine'de Jira yapılandırması gerektirir.
    """
    return _post("/api/connectors/jira/issue-to-tests", {"issue_key": issue_key, "persist": True})


@mcp.tool()
def heal_locator(url: str, fingerprint: dict, threshold: float = 0.55) -> dict:
    """Kırılan bir locator için canlı sayfada çok-sinyalli en iyi eşleşmeyi bul.

    Args:
        url: Elementin bulunduğu sayfa.
        fingerprint: Daha önce yakalanmış element parmak izi (capture_fingerprint çıktısı).
        threshold: Minimum eşleşme skoru.
    """
    return _post("/api/self-heal/heal", {"url": url, "fingerprint": fingerprint, "threshold": threshold})


@mcp.tool()
def capabilities() -> dict:
    """Cortex'in MCP üzerinden sunulan tüm yeteneklerinin sağlık durumunu döndür."""
    out = {}
    for name, path in (
        ("discovery", "/api/discovery/health"),
        ("root_cause", "/api/rca/health"),
        ("self_healing", "/api/self-heal/health"),
        ("connectors", "/api/connectors/health"),
        ("visual_semantic", "/api/visual-semantic/health"),
        ("continuous", "/api/continuous/health"),
    ):
        try:
            out[name] = _get(path)
        except Exception as exc:
            out[name] = {"status": "unreachable", "error": str(exc)}
    return out


if __name__ == "__main__":
    mcp.run()
