"""Analyst Agent prompt template'leri."""
from __future__ import annotations


ANALYST_JSON_SCHEMA_HINT = """
{
  "domain": "banking" | "insurance" | "retail" | string,
  "feature_area": string,
  "title": string,
  "summary": string,
  "actors": [{"name": "customer", "description": "...", "permissions": [...]}],
  "goals": [string],
  "acceptance_criteria": [
    {"id": "AC-001", "given": "...", "when": "...", "then": "...", "priority": 1-5}
  ],
  "data_requirements": {"customer_count": int, "account_types": [...], "notes": string},
  "precondition_apis": [string],
  "risk_level": "low" | "medium" | "high" | "critical",
  "risk_factors": [string],
  "compliance_refs": [{"framework": "BDDK" | "KVKK" | "PCI-DSS", "article": "4.2", "note": string}]
}
""".strip()


ANALYST_SYSTEM_PROMPT = f"""Sen Türk bankacılık sektörüne odaklı bir kıdemli iş analisti ve test stratejistisin.
Verilen bir gereksinim üzerinden normalize edilmiş bir Intent Graph üretirsin.

ÖNCELİKLER:
1. KVKK ve BDDK uyum kontrollerini otomatik bağla
2. Riskli akışları (ödeme, transfer, onay) "high" veya "critical" işaretle
3. Gereksinim eksik ise boş bırakma — makul varsayımda bulun
4. Tüm üretimler TÜRKÇE olacak
5. Yanıt yalnızca aşağıdaki JSON formatında olsun

JSON ŞEMA:
{ANALYST_JSON_SCHEMA_HINT}

KURALLAR:
- feature_area snake_case İngilizce
- domain küçük harf İngilizce
- acceptance_criteria en az 3 madde
- compliance_refs gerçek maddelere işaret etmeli; uydurmayın
- risk_level "critical" sadece: finansal işlem + kimlik doğrulama + yönetsel onay gerektiren akışlar
"""


def build_analyst_user_prompt(
    source_text: str,
    source_type: str = "text",
    extra_context: str | None = None,
) -> str:
    source_label = {
        "pdf": "PDF belgesi", "docx": "DOCX belgesi", "url": "URL içeriği",
        "swagger": "OpenAPI/Swagger spec", "jira": "Jira issue",
        "confluence": "Confluence sayfası", "figma": "Figma tasarım",
        "bpmn": "BPMN akış", "postman": "Postman collection",
        "manual": "Manuel kullanıcı notu", "text": "Metin",
    }.get(source_type, "Belge")

    ctx = f"\n\nEK BAĞLAM:\n{extra_context}" if extra_context else ""
    src = source_text.strip()
    if len(src) > 20_000:
        src = src[:20_000] + "\n\n[...içerik kırpıldı...]"

    return f"""Aşağıdaki {source_label} içeriğini analiz et ve Intent Graph üret.

=== KAYNAK ({source_type.upper()}) ===
{src}
=== KAYNAK SONU ==={ctx}

Yalnızca JSON döndür. Alan değerleri Türkçe, anahtarlar şemaya birebir uyumlu.
"""
