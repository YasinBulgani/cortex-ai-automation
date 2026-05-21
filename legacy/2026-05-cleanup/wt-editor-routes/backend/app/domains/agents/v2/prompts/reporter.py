"""Reporter Agent prompt."""
from __future__ import annotations


REPORTER_SYSTEM_PROMPT = """Sen bir QA raporlama uzmanısın. Pipeline çıktısından yönetim için PROFESYONEL Türkçe özet yazarsın.

KURALLAR:
- Emoji YOK
- 3-5 madde
- İstatistik + tek cümle yorum
- Riskli bulgu varsa ilk madde
- <500 kelime
- Teknik detaya girme (CIO/QA Lead için)
"""


def build_reporter_user_prompt(
    run_id: str,
    intent_title: str,
    scenario_count: int,
    passed: int,
    failed: int,
    flaky: int,
    healing_fixes: int,
    total_cost_usd: float,
    total_tokens: int,
    duration_minutes: float,
) -> str:
    return f"""=== PIPELINE ÖZETİ ===
Run ID: {run_id[:12]}
Konu: {intent_title}
Üretilen senaryo: {scenario_count}
Test sonucu: {passed} geçti / {failed} kaldı / {flaky} oynak
Self-healing uygulaması: {healing_fixes}
Toplam süre: {duration_minutes:.1f} dk
LLM maliyet: ${total_cost_usd:.3f} ({total_tokens} token)

=== GÖREV ===
TR profesyonel yönetim raporu yaz.
"""
