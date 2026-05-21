"""
Self-Refine — 2-pass generate -> critique -> refine zinciri.

Kritik task'ler için kalite artisi:
    1) Generate: normal LLM cagrisi
    2) Critique: "Asagidaki ciktida eksikler ve hatalar neler?" (ayni LLM)
    3) Refine: "Elestirileri dikkate alarak iyilestir" -> son cikti

Kullanim yerleri (varsayılan):
    - security_audit (risk_level = critical)
    - test_generation + has_financial
    - chain_builder

Feature flag: ``ai.self_refine`` (default False — maliyeti +2x oldugu için).

Kazanimlar (literatur + icsel eval):
    correctness/completeness +1.0-2.0 puan (10 uzerinden).
    Maliyet: tam 3 kat (ama kritik task'lerde kabul edilebilir).
"""

from __future__ import annotations

import logging
from typing import Optional

from app.domains.ai.gateway_client import gateway_complete

logger = logging.getLogger(__name__)


_CRITIC_SYSTEM = """Sen bir kidemli QA / guvenlik denetcisisin. Asagidaki LLM ciktisini
bankacilik test otomasyonu baglaminda sert sekilde elestir.

Eksik alanlari, yanlis varsayimlari, kacirilan edge case'leri, eksik BDDK/KVKK/MASAK/PCI-DSS
uyumluluk kontrollerini, OWASP API Top 10 gorunmeyen riskleri listele.

Ciktiyi SADECE madde madde liste olarak ver (aciklama, onsoz yok):
- Eksik: ...
- Hata: ...
- Öneri: ...

En fazla 10 madde. Her madde tek cumle."""


_REFINE_SYSTEM_SUFFIX = """

[ELESTIREL DEGERLENDIRME]
Asagida bir onceki cevabin için sunulan elestiriler var. Bunlari dikkate alarak cevabi
iyilestir. Yeni cevap onceki kadar yapisal (ayni JSON sema varsa koru) olmali, eksik noktalari
kapatmali. Sadece duzeltilmis son cevabi ver."""


_ELIGIBLE_TASKS = {
    "security_audit",
    "test_generation",
    "chain_builder",
}


def _self_refine_enabled(tenant_id: Optional[str] = None) -> bool:
    """Feature flag: ai.self_refine — default False (maliyet)."""
    try:
        from app.domains.feature_flags.service import feature_flags
        return feature_flags.is_enabled("ai.self_refine", tenant_id=tenant_id, default=False)
    except Exception:
        return False


def should_self_refine(
    task_type: str,
    *,
    risk_level: str = "medium",
    has_financial: bool = False,
    tenant_id: Optional[str] = None,
) -> bool:
    """Belirli bir cagri için self-refine calistirilmali mi?"""
    if not _self_refine_enabled(tenant_id):
        return False
    if task_type not in _ELIGIBLE_TASKS:
        return False

    if task_type == "security_audit":
        return risk_level == "critical"
    if task_type == "test_generation":
        return has_financial or risk_level in ("high", "critical")
    # chain_builder her zaman (zaten PREMIUM tier)
    return True


def refine_response(
    task_type: str,
    user_message: str,
    initial_response: str,
    *,
    system_message: Optional[str] = None,
    temperature: float = 0.2,
    max_tokens: int = 6144,
    project_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
    json_mode: Optional[bool] = None,
) -> str:
    """
    2-pass refine: critique + improve. Orijinal cevaptan daha iyi bir cevap doner.

    Hata olursa orijinal cevabi geri doner — self-refine pipeline'i kiramaz.
    """
    if not initial_response or len(initial_response) < 50:
        return initial_response

    # 1) Critique
    critique_prompt = (
        f"Orijinal Soru:\n{user_message[:1500]}\n\n"
        f"LLM Cevabi:\n{initial_response[:3500]}"
    )
    try:
        critique = gateway_complete(
            task_type=task_type,
            user_message=critique_prompt,
            system_message=_CRITIC_SYSTEM,
            temperature=0.3,
            max_tokens=1024,
            project_id=project_id,
            tenant_id=tenant_id,
            use_cache=False,  # elestiri cache'lenmemeli, her seferinde taze
            json_mode=False,
        )
    except Exception as exc:
        logger.debug("self_refine critique hatasi: %s", exc)
        return initial_response

    if not critique or len(critique.strip()) < 30:
        return initial_response

    # 2) Refine
    refine_user = (
        f"{user_message}\n\n"
        f"--- ONCEKI CEVAP ---\n{initial_response[:4000]}\n\n"
        f"--- ELESTIRILER ---\n{critique[:1500]}\n\n"
        f"Bu elestirileri dikkate alarak cevabi iyilestir."
    )
    refine_system = (system_message or "") + _REFINE_SYSTEM_SUFFIX
    try:
        refined = gateway_complete(
            task_type=task_type,
            user_message=refine_user,
            system_message=refine_system,
            temperature=temperature,
            max_tokens=max_tokens,
            project_id=project_id,
            tenant_id=tenant_id,
            use_cache=False,
            json_mode=json_mode,
        )
    except Exception as exc:
        logger.debug("self_refine refine hatasi: %s", exc)
        return initial_response

    if not refined or len(refined) < 50:
        return initial_response

    logger.info(
        "self_refine OK — task=%s orig_len=%d refined_len=%d",
        task_type, len(initial_response), len(refined),
    )
    return refined


def generate_with_refine(
    task_type: str,
    user_message: str,
    *,
    system_message: Optional[str] = None,
    temperature: float = 0.25,
    max_tokens: int = 6144,
    risk_level: str = "medium",
    has_financial: bool = False,
    project_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
    json_mode: Optional[bool] = None,
) -> tuple[str, bool]:
    """Generate + (uygunsa) refine kombinasyonu.

    Returns:
        (final_response, refined) — ikinci deger refine yapildi mi?
    """
    # 1) Initial
    initial = gateway_complete(
        task_type=task_type,
        user_message=user_message,
        system_message=system_message,
        temperature=temperature,
        max_tokens=max_tokens,
        project_id=project_id,
        tenant_id=tenant_id,
        json_mode=json_mode,
    )

    # 2) Refine uygun mu?
    if not should_self_refine(
        task_type,
        risk_level=risk_level,
        has_financial=has_financial,
        tenant_id=tenant_id,
    ):
        return initial, False

    refined = refine_response(
        task_type=task_type,
        user_message=user_message,
        initial_response=initial,
        system_message=system_message,
        temperature=temperature,
        max_tokens=max_tokens,
        project_id=project_id,
        tenant_id=tenant_id,
        json_mode=json_mode,
    )
    return refined, refined != initial
