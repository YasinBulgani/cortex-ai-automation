"""
AI Synthetic Data — Platform Modülü (Faz 3.B — ADR-0003).

`synthetic-data/platform-v4/` kodunun backend'e port'lanmış versiyonu.
Gap analizi: docs/architecture/synthetic-data-gap-analysis.md

Sunulan bileşenler:
    - models.py            — SQLAlchemy tablolar (Project, DetectedSchema,
                             GenerationRule, GenerationHistory)
    - schema_analyzer.py   — CSV/JSON → şema profili
    - column_classifier.py — semantik kolon sınıflandırma + PII tespit
    - rule_engine.py       — kolon istatistiklerinden üretim kuralları
    - learning_engine.py   — geçmiş üretimden kural iyileştirme
    - scenarios.py         — bankacılık senaryo şablonları
"""

from .models import (
    SyntheticProject,
    SyntheticDetectedSchema,
    SyntheticGenerationRule,
    SyntheticGenerationHistory,
)
from .schema_analyzer import SchemaAnalyzer
from .column_classifier import ColumnClassifier
from .rule_engine import RuleEngine
from .learning_engine import LearningEngine
from .scenarios import ScenarioManager, SCENARIOS

__all__ = [
    "SyntheticProject",
    "SyntheticDetectedSchema",
    "SyntheticGenerationRule",
    "SyntheticGenerationHistory",
    "SchemaAnalyzer",
    "ColumnClassifier",
    "RuleEngine",
    "LearningEngine",
    "ScenarioManager",
    "SCENARIOS",
]
