"""Onboarding scorecard domain — UX-F3-302.

Yeni kullanıcının "3/7 kurulum tamam" ilerleme çubuğu için backend.
MVP: adım tanımları sabit, state bellekte. Production'a geçişte DB
migration ile `projects.onboarding_state` JSON field'a taşınacak.
"""

from app.domains.onboarding.service import (  # noqa: F401
    DEFAULT_STEPS,
    ProgressEntry,
    ProgressStore,
    compute_progress,
    progress_store,
)
from app.domains.onboarding.schemas import (  # noqa: F401
    OnboardingProgress,
    OnboardingStep,
    ProgressUpdateRequest,
)
