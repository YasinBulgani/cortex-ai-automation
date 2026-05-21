"""Onboarding katalog + in-memory progress tracker.

MVP karar: state bellek-içi dict'te tutulur. Bu:
    * Horizontal scale'de pod başına farklı state anlamına gelir
      (kullanıcı deneyimi: scorecard bazen tam tamamlanmış, bazen yarım görünür)
    * Restart'ta sıfırlanır
    * Ama: ilk iterasyon için yeterli, DB migration iş yükünü bir sonraki
      sprint'e atar. Kullanıcı "X/7 tamam" sayısını zaten localStorage'ta
      da tutabilir (frontend bu endpoint'i auth edilmiş tekil kaynak
      olarak kullanır, dirty tracking yok).

Production yolu (ayrı PR):
    * `projects` tablosuna `onboarding_state JSONB DEFAULT '{}'::jsonb`
    * Bu servis `Session`'dan okuyup yazar
    * Pod'lar arası tutarlı
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Dict, List

from app.domains.onboarding.schemas import OnboardingProgress, OnboardingStep


@dataclass(frozen=True)
class ProgressEntry:
    project_id: str
    step_id: str
    done: bool


# ── Adım kataloğu ─────────────────────────────────────────────────────────

DEFAULT_STEPS: List[OnboardingStep] = [
    OnboardingStep(
        id="create_project",
        order=1,
        title="Proje oluştur",
        description="Test çalışmalarını organize etmek için ilk projenizi açın.",
        is_optional=False,
        action_url="/projects",
        help_doc="/docs/user-guide/01-quickstart.md",
    ),
    OnboardingStep(
        id="select_ai_provider",
        order=2,
        title="AI sağlayıcı seç",
        description="Ollama (ücretsiz lokal) veya bulut (OpenAI/Anthropic/Gemini).",
        is_optional=False,
        action_url="/admin/ai-providers",
        help_doc="/docs/user-guide/01-quickstart.md#seçenek-a--demo-modu-önerilen-ilk-deneme-için",
    ),
    OnboardingStep(
        id="load_dsl_catalog",
        order=3,
        title="DSL kataloğunu yükle",
        description="Varsayılan 751 aksiyonla başlayın; isterseniz kendinizinkini ekleyin.",
        is_optional=False,
        action_url="/admin/dsl",
        help_doc="/docs/user-guide/02-manual-to-automation.md#dsl-kataloğu--sistem-ne-biliyor",
    ),
    OnboardingStep(
        id="write_first_scenario",
        order=4,
        title="İlk manuel test senaryosunu yaz",
        description="Türkçe cümlelerle bir oturum açma senaryosu yazın.",
        is_optional=False,
        action_url="/bgtest-wizard",
        help_doc="/docs/user-guide/02-manual-to-automation.md#pratik-kılavuz-iyi-senaryo-yazmak",
    ),
    OnboardingStep(
        id="generate_first_test",
        order=5,
        title="İlk Playwright testini üret",
        description="Wizard otomatik Gherkin + kod üretir.",
        is_optional=False,
        action_url="/bgtest-wizard",
        help_doc="/docs/user-guide/02-manual-to-automation.md",
    ),
    OnboardingStep(
        id="run_first_test",
        order=6,
        title="İlk testi koştur",
        description="Üretilen testi Engine üzerinden çalıştırın.",
        is_optional=False,
        action_url="/p/[projectId]/executions",
        help_doc="/docs/user-guide/01-quickstart.md",
    ),
    OnboardingStep(
        id="connect_cicd",
        order=7,
        title="CI/CD webhook bağla",
        description="GitHub/GitLab/Jenkins'e bağlayıp otomatik koştur.",
        is_optional=True,
        action_url="/p/[projectId]/cicd",
        help_doc="/docs/user-guide/03-ci-cd.md",
    ),
]


# ── In-memory store ───────────────────────────────────────────────────────


class ProgressStore:
    """Thread-safe, proje bazlı tamamlanma durumu."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        # { project_id: { step_id: bool } }
        self._state: Dict[str, Dict[str, bool]] = {}

    def get(self, project_id: str) -> Dict[str, bool]:
        with self._lock:
            return dict(self._state.get(project_id, {}))

    def set(self, project_id: str, step_id: str, done: bool) -> None:
        with self._lock:
            bucket = self._state.setdefault(project_id, {})
            bucket[step_id] = done

    def reset(self, project_id: str) -> None:
        """Test amaçlı veya 'onboarding'i tekrar göster' tercihi."""
        with self._lock:
            self._state.pop(project_id, None)

    def snapshot(self) -> Dict[str, Dict[str, bool]]:
        with self._lock:
            return {pid: dict(v) for pid, v in self._state.items()}


progress_store = ProgressStore()


# ── Hesap ─────────────────────────────────────────────────────────────────


def compute_progress(
    project_id: str,
    completed: Dict[str, bool],
    steps: List[OnboardingStep] = None,
) -> OnboardingProgress:
    """Kullanıcı state'inden OnboardingProgress DTO üret."""
    catalog = steps if steps is not None else DEFAULT_STEPS
    required = [s for s in catalog if not s.is_optional]
    completed_required = sum(
        1 for s in required if completed.get(s.id, False)
    )
    total_required = len(required) or 1
    pct = round(100.0 * completed_required / total_required, 1)
    # Default all to False for UI convenience
    full_map = {s.id: bool(completed.get(s.id, False)) for s in catalog}

    return OnboardingProgress(
        project_id=project_id,
        steps=catalog,
        completed=full_map,
        completion_pct=pct,
        total_required=len(required),
        completed_required=completed_required,
        is_fully_onboarded=(completed_required == len(required)),
    )
