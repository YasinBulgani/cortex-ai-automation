"""CoverUp — Code coverage analizi Pydantic şemaları."""
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field


class CoverageUploadRequest(BaseModel):
    """Coverage raporu yükleme."""

    project_id: str = Field(description="Coverage raporunun ait oldugu BGTS proje ID'si")
    format: str = Field(description="lcov|istanbul|nyc|cobertura|coveragepy")
    report_data: str = Field(description="Rapor içeriği (metin)")
    project_name: str = Field(default="")
    commit_sha: str = Field(default="")
    branch: str = Field(default="main")


class FileCoverage(BaseModel):
    """Tek dosyanın kapsam verisi."""

    file_path: str
    total_lines: int = 0
    covered_lines: int = 0
    missed_lines: int = 0
    line_rate: float = 0.0  # 0.0-1.0
    branch_rate: float = 0.0
    total_branches: int = 0
    covered_branches: int = 0
    total_functions: int = 0
    covered_functions: int = 0
    missed_line_numbers: List[int] = Field(default_factory=list)
    missed_branch_lines: List[int] = Field(default_factory=list)
    uncovered_functions: List[str] = Field(default_factory=list)
    complexity: Optional[float] = None


class CoverageSummary(BaseModel):
    total_files: int = 0
    total_lines: int = 0
    covered_lines: int = 0
    missed_lines: int = 0
    line_rate: float = 0.0
    branch_rate: float = 0.0
    function_rate: float = 0.0
    total_functions: int = 0
    covered_functions: int = 0


class CoverageReport(BaseModel):
    """Toplam coverage raporu."""

    report_id: str
    project_id: str = ""
    project_name: str = ""
    commit_sha: str = ""
    branch: str = "main"
    format: str
    created_at: str
    summary: CoverageSummary
    files: List[FileCoverage]


class CoverageGapTarget(BaseModel):
    """Kapsanmayan kod hedefi."""

    file_path: str
    function_name: Optional[str] = None
    start_line: int
    end_line: int
    gap_type: str = Field(description="line|branch|function")
    risk_score: float = Field(default=0.5, ge=0.0, le=1.0)
    risk_factors: List[str] = Field(default_factory=list)
    code_snippet: str = ""
    suggestion: str = ""


class AnalyzeRequest(BaseModel):
    report_id: str
    focus_paths: List[str] = Field(
        default_factory=list, description="Odaklanılacak dosya patternleri"
    )
    min_risk_score: float = Field(default=0.3, ge=0.0, le=1.0)
    include_code_snippets: bool = True
    max_targets: int = Field(default=50, ge=1, le=200)


class AnalyzeResponse(BaseModel):
    report_id: str
    targets: List[CoverageGapTarget]
    summary: CoverageSummary
    high_risk_count: int = 0
    medium_risk_count: int = 0
    low_risk_count: int = 0
    banking_critical_paths: List[str] = Field(default_factory=list)


class GenerateTestRequest(BaseModel):
    """Kapsanmayan kod için test üretme."""

    report_id: str
    targets: List[CoverageGapTarget] = Field(
        default_factory=list, description="Boşsa tüm high-risk hedefleri kullan"
    )
    framework: str = Field(
        default="playwright", description="playwright|pytest|jest|vitest"
    )
    language: str = Field(default="typescript", description="typescript|python")
    max_tests: int = Field(default=10, ge=1, le=50)
    banking_context: bool = Field(
        default=True, description="Bankacılık bağlamını dahil et"
    )


class GeneratedTest(BaseModel):
    target_file: str
    target_function: Optional[str] = None
    test_file_path: str
    test_code: str
    test_framework: str
    estimated_coverage_gain: float = 0.0
    lines_targeted: List[int] = Field(default_factory=list)


class GenerateTestResponse(BaseModel):
    tests: List[GeneratedTest]
    total_generated: int
    estimated_total_gain: float = 0.0


class CoverageReportListItem(BaseModel):
    report_id: str
    project_id: str = ""
    project_name: str = ""
    commit_sha: str = ""
    branch: str = ""
    format: str
    created_at: str
    line_rate: float = 0.0
    branch_rate: float = 0.0
    total_files: int = 0


class TrendPoint(BaseModel):
    report_id: str
    project_id: str = ""
    commit_sha: str = ""
    branch: str = ""
    created_at: str
    line_rate: float
    branch_rate: float
    function_rate: float
    total_lines: int
    covered_lines: int


class TrendResponse(BaseModel):
    points: List[TrendPoint]
    direction: str = Field(
        default="stable", description="improving|stable|degrading"
    )
    current_line_rate: float = 0.0
    delta_7d: float = 0.0
    delta_30d: float = 0.0
