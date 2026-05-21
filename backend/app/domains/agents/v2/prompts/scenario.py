"""Scenario Agent prompt template'leri."""
from __future__ import annotations


SCENARIO_SYSTEM_PROMPT = """Sen deneyimli bir BDD test mühendisisin. Verilen Intent Graph ve App Map'ten Gherkin feature üretirsin.

ÖNCELİKLER:
1. Türkçe Gherkin (Özellik, Senaryo, Verilen/Eğer/O zaman)
2. DSL KATALOG adımlarını tercih et (grounding)
3. Senaryolar kısa, net, tek amaçlı (happy + negative + edge)
4. Tag'le: @smoke, @regression, @banking, @<domain>
5. Scenario Outline + Örnekler kullan

ÇIKIŞ:
- SADECE Gherkin metni
- "# language: tr" ilk satır
- Her senaryo en az 3 adım
"""


def build_scenario_user_prompt(
    intent_graph_json: str,
    app_map_summary: str,
    dsl_candidates: list[str] | None = None,
    max_scenarios: int = 10,
) -> str:
    dsl_block = ""
    if dsl_candidates:
        dsl_block = (
            "\n\n=== DSL KATALOG ADAYI ADIMLAR (tercih et) ===\n"
            + "\n".join(f"- {s}" for s in dsl_candidates[:30])
            + "\n=== DSL SONU ==="
        )
    return f"""Aşağıdaki Intent Graph'a dayanarak en fazla {max_scenarios} Gherkin senaryosu üret.

=== INTENT GRAPH (JSON) ===
{intent_graph_json}
=== INTENT SONU ===

=== UYGULAMA HARİTASI ÖZETİ ===
{app_map_summary}
=== HARİTA SONU ==={dsl_block}

# language: tr ile başla. Her kabul kriterini en az bir senaryoda karşıla.
"""
