"""Pipeline status aggregator — Analyze → Design → Data → Execute → Observe → Iterate.

Hesaplama mantığı: her stage için relevant DB sayım + heuristic durum.
Hızlı endpoint — UI dashboard'lar için.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Optional

StageStatus = Literal["complete", "in_progress", "pending", "blocked"]


@dataclass
class StageInfo:
    id: str
    title: str
    status: StageStatus
    metric_label: str
    metric_value: int | str
    description: str = ""


@dataclass
class PipelineStatus:
    project_id: str
    overall_progress_pct: int
    stages: list[StageInfo] = field(default_factory=list)
    last_run_pass_rate: Optional[float] = None
    open_failures: int = 0
    ai_generated_count: int = 0
    total_scenarios: int = 0
    total_executions: int = 0

    def to_dict(self) -> dict:
        return {
            "project_id": self.project_id,
            "overall_progress_pct": self.overall_progress_pct,
            "stages": [
                {
                    "id": s.id,
                    "title": s.title,
                    "status": s.status,
                    "metric_label": s.metric_label,
                    "metric_value": s.metric_value,
                    "description": s.description,
                }
                for s in self.stages
            ],
            "last_run_pass_rate": self.last_run_pass_rate,
            "open_failures": self.open_failures,
            "ai_generated_count": self.ai_generated_count,
            "total_scenarios": self.total_scenarios,
            "total_executions": self.total_executions,
        }


def compute_pipeline_status(
    *,
    project_id: str,
    scenario_count: int = 0,
    ai_generated_count: int = 0,
    requirement_count: int = 0,
    data_set_count: int = 0,
    execution_count: int = 0,
    last_run: Optional[dict] = None,
    open_failures: int = 0,
    has_ci_config: bool = False,
) -> PipelineStatus:
    """Compute stage statuses based on project metrics.

    Pure function — DB extractor caller'ı yapar, bu sadece sınıflandırır.
    """
    last_pass_rate: Optional[float] = None
    if last_run and last_run.get("scenario_total"):
        last_pass_rate = round(
            100.0 * (last_run.get("passed_count") or 0) / last_run["scenario_total"], 1
        )

    stages: list[StageInfo] = []

    # 1. Analyze
    analyze_status: StageStatus = (
        "complete"
        if requirement_count > 0 or ai_generated_count > 0
        else "pending"
    )
    stages.append(StageInfo(
        id="analyze",
        title="Analiz",
        status=analyze_status,
        metric_label="Gereksinim/AI girdi",
        metric_value=requirement_count + ai_generated_count,
        description="Doküman + spec analizi",
    ))

    # 2. Design
    design_status: StageStatus = "complete" if scenario_count > 0 else "pending"
    stages.append(StageInfo(
        id="design",
        title="Tasarım",
        status=design_status,
        metric_label="Senaryolar",
        metric_value=scenario_count,
        description="Senaryo + locator yönetimi",
    ))

    # 3. Data
    data_status: StageStatus = "complete" if data_set_count > 0 else "pending"
    stages.append(StageInfo(
        id="data",
        title="Veri",
        status=data_status,
        metric_label="Veri setleri",
        metric_value=data_set_count,
        description="Sentetik veri + parametrelendirme",
    ))

    # 4. Execute
    if execution_count == 0:
        execute_status: StageStatus = "pending"
    elif open_failures > scenario_count * 0.3:
        execute_status = "blocked"
    elif execution_count > 0:
        execute_status = "complete"
    else:
        execute_status = "in_progress"
    stages.append(StageInfo(
        id="execute",
        title="Koşum",
        status=execute_status,
        metric_label="Toplam koşum",
        metric_value=execution_count,
        description="Web + Mobil + API koşumu",
    ))

    # 5. Observe
    observe_status: StageStatus = (
        "complete" if last_pass_rate is not None else "pending"
    )
    stages.append(StageInfo(
        id="observe",
        title="Gözlem",
        status=observe_status,
        metric_label="Son başarı %",
        metric_value=int(last_pass_rate) if last_pass_rate is not None else "—",
        description="Raporlar + flaky + healing",
    ))

    # 6. Iterate
    iterate_status: StageStatus = "complete" if has_ci_config else "pending"
    stages.append(StageInfo(
        id="iterate",
        title="İyileştirme",
        status=iterate_status,
        metric_label="Açık hata",
        metric_value=open_failures,
        description="CI/CD + onay + sürekli iyileştirme",
    ))

    # Overall progress: complete stages out of 6
    completed = sum(1 for s in stages if s.status == "complete")
    overall_pct = int(round(100 * completed / 6))

    return PipelineStatus(
        project_id=project_id,
        overall_progress_pct=overall_pct,
        stages=stages,
        last_run_pass_rate=last_pass_rate,
        open_failures=open_failures,
        ai_generated_count=ai_generated_count,
        total_scenarios=scenario_count,
        total_executions=execution_count,
    )
