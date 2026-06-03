"""
Gereksinim Yutucu (Requirement Ingest) — Dış kaynaktan test üretimi
═══════════════════════════════════════════════════════════════════════════

TestStory/Kualitee tarzı: Jira ticket'ı, Confluence PRD'si veya ham gereksinim
metnini → yapısal test case'leri + (opsiyonel) çalıştırılabilir Gherkin'e çevirir.

Mevcut altyapıyı yeniden kullanır:
  * ``AIEngine.extract_test_cases_from_document`` — metin → zengin test case'ler
  * ``AIEngine.generate_gherkin`` — case → Neurex feature
  * ``core.db`` — manuel test kalıcılığı
  * Jira için ``routes.jira_routes.get_jira_client`` (dışa-dönük entegrasyonla aynı client)
"""
from __future__ import annotations

import html as _html
import logging
import re

logger = logging.getLogger(__name__)


def _strip_html(raw: str) -> str:
    """Confluence storage HTML'ini düz metne indirger."""
    if not raw:
        return ""
    text = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", raw, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</(p|li|h[1-6]|tr|div)>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = _html.unescape(text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    return text.strip()


def _extract_cases(text: str) -> list[dict]:
    """Gereksinim metninden zengin test case'leri üretir (dayanıklı JSON parse).

    Kırılgan ``AIEngine.extract_test_cases_from_document`` (katı json.loads,
    yerel LLM'in trailing-comma'sında patlar) yerine merkezi gateway + tolerant
    parser kullanır.
    """
    from services import get_llm_gateway
    from core.auto_discovery import _extract_json

    system = ("Sen kıdemli bir QA Test Analiz uzmanısın. Gereksinim metninden "
              "yapısal test case'leri üretirsin. SADECE JSON döndür.")
    user = f"""Aşağıdaki gereksinimden çıkarılabilecek tüm mantıklı test case'leri üret.

GEREKSİNİM:
{text}

SADECE şu JSON'u döndür (başka açıklama yok):
{{
  "cases": [
    {{
      "title": "Kısa başlık",
      "description": "Tek cümle amaç",
      "priority": "P1|P2|P3",
      "tags": ["smoke"],
      "steps": [{{"action": "Adım", "expected": "Beklenen sonuç"}}]
    }}
  ]
}}"""
    gw = get_llm_gateway()
    resp = gw.complete(
        messages=[{"role": "system", "content": system},
                  {"role": "user", "content": user}],
        temperature=0.2, max_tokens=3000,
    )
    data = _extract_json(resp.content)
    cases = data.get("cases", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
    clean = []
    for c in cases:
        if not isinstance(c, dict) or not c.get("title"):
            continue
        clean.append({
            "title": str(c.get("title"))[:120],
            "description": str(c.get("description", "")),
            "priority": str(c.get("priority", "P2")).upper(),
            "tags": [str(t) for t in (c.get("tags") or []) if t],
            "steps": [s for s in (c.get("steps") or []) if isinstance(s, dict)],
        })
    return clean


# ═══════════════════════════════════════════════════════════════════════════
# Çekirdek: metin → testler
# ═══════════════════════════════════════════════════════════════════════════

def text_to_tests(
    text: str,
    title: str = "",
    target_url: str | None = None,
    persist: bool = False,
    gherkin: bool = True,
    source: str = "manual",
) -> dict:
    """Ham gereksinim metninden test case'leri (ve opsiyonel Gherkin) üretir.

    Dönüş::

        {
          "source": "jira|confluence|manual",
          "title": ...,
          "cases": [ {title, description, priority, tags, steps, test_id?} ],
          "features": [ {title, content} ],   # gherkin=True ise
          "stats": {cases, persisted}
        }
    """
    from core import db

    if not text or not text.strip():
        raise ValueError("Boş gereksinim metni")

    cases = _extract_cases(text)

    features: list[dict] = []
    persisted = 0
    for case in cases:
        c_title = str(case.get("title") or "İsimsiz test")[:120]

        if persist:
            try:
                tid = db.create_manual_test(f"[{source}] {c_title}")
                for step in case.get("steps", []) or []:
                    db.add_manual_step(
                        tid,
                        str(step.get("action", "")),
                        str(step.get("expected", "")),
                    )
                case["test_id"] = tid
                persisted += 1
            except Exception as exc:
                logger.warning("Case kalıcılaştırılamadı (%s): %s", c_title, exc)
                case["test_id"] = None

        if gherkin:
            try:
                from core.ai_engine import get_ai_engine
                steps_text = "\n".join(
                    f"- {s.get('action','')} => {s.get('expected','')}"
                    for s in case.get("steps", []) or []
                )
                req = f"Senaryo: {c_title}\nÖncelik: {case.get('priority','P2')}\nAdımlar:\n{steps_text}"
                feature = get_ai_engine().generate_gherkin(req, target_url)
                features.append({"title": c_title, "content": feature})
            except Exception as exc:
                logger.warning("Gherkin üretilemedi (%s): %s", c_title, exc)

    return {
        "source": source,
        "title": title or (cases[0].get("title") if cases else ""),
        "cases": cases,
        "features": features,
        "stats": {"cases": len(cases), "persisted": persisted},
    }


# ═══════════════════════════════════════════════════════════════════════════
# Jira: issue → testler
# ═══════════════════════════════════════════════════════════════════════════

def jira_issue_to_tests(issue_key: str, persist: bool = False, gherkin: bool = True,
                        target_url: str | None = None) -> dict:
    """Bir Jira issue'sunu çeker (özet+açıklama) ve test üretir.

    Mevcut dışa-dönük entegrasyonun client'ını yeniden kullanır.
    """
    from routes.jira_routes import get_jira_client

    client = get_jira_client()
    if client is None:
        raise RuntimeError("Jira yapılandırılmamış (config/credentials eksik)")

    issue = client.issue(issue_key)
    summary = getattr(issue.fields, "summary", "") or ""
    description = getattr(issue.fields, "description", "") or ""
    # Bazı Jira sürümlerinde description ADF (dict) olabilir
    if not isinstance(description, str):
        description = str(description)

    text = f"Başlık: {summary}\n\nAçıklama:\n{description}"
    result = text_to_tests(
        text, title=f"{issue_key}: {summary}", target_url=target_url,
        persist=persist, gherkin=gherkin, source="jira",
    )
    result["issue_key"] = issue_key
    return result


# ═══════════════════════════════════════════════════════════════════════════
# Confluence: sayfa → testler
# ═══════════════════════════════════════════════════════════════════════════

def fetch_confluence_page(base_url: str, page_id: str, email: str, api_token: str) -> dict:
    """Confluence REST API'den sayfa içeriğini çeker (storage HTML → düz metin)."""
    import httpx

    base_url = base_url.rstrip("/")
    url = f"{base_url}/wiki/rest/api/content/{page_id}?expand=body.storage,title"
    resp = httpx.get(url, auth=(email, api_token), timeout=30.0,
                     headers={"Accept": "application/json"})
    resp.raise_for_status()
    data = resp.json()
    storage = (((data.get("body") or {}).get("storage") or {}).get("value")) or ""
    return {"title": data.get("title", ""), "text": _strip_html(storage)}


def confluence_page_to_tests(
    base_url: str, page_id: str, email: str, api_token: str,
    persist: bool = False, gherkin: bool = True, target_url: str | None = None,
) -> dict:
    """Bir Confluence sayfasını (PRD/gereksinim) çeker ve test üretir."""
    page = fetch_confluence_page(base_url, page_id, email, api_token)
    if not page["text"].strip():
        raise RuntimeError("Confluence sayfası boş veya okunamadı")
    result = text_to_tests(
        page["text"], title=page["title"], target_url=target_url,
        persist=persist, gherkin=gherkin, source="confluence",
    )
    result["page_id"] = page_id
    return result
