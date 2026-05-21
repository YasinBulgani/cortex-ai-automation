"""
SynthesizerSelector — Veri boyutu ve kullanici tercihine gore
en uygun sentetik veri uretim yontemini otomatik secer.
"""
from __future__ import annotations

import logging
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)


class SynthesizerSelector:
    """Veri ozelliklerine gore synthesizer sec ve uret."""

    METHODS = ("stat", "kde", "copula", "ctgan", "tvae", "auto")

    def select(self, df: pd.DataFrame, method: str = "auto") -> str:
        """En uygun yontemi sec ve adini don."""
        if method != "auto" and method in self.METHODS:
            return method

        n_rows = len(df)
        n_cols = len(df.columns)

        if n_rows < 100:
            selected = "stat"
        elif n_rows < 1000:
            selected = "kde"
        elif n_rows < 50000:
            selected = "copula"
        else:
            try:
                from app.core.deep_synth import DeepSynthesizer
                ds = DeepSynthesizer()
                selected = "tvae" if ds.is_sdv_available else "copula"
            except Exception:
                selected = "copula"

        if n_cols > 30 and selected in ("kde", "stat"):
            selected = "copula"

        logger.info("Yontem secildi: %s (rows=%d, cols=%d, requested=%s)",
                     selected, n_rows, n_cols, method)
        return selected

    def create_synthesizer(self, method: str) -> Any:
        """Secilen yonteme gore synthesizer nesnesi olustur."""
        if method == "stat":
            from app.core.generator import SyntheticGenerator
            return SyntheticGenerator()
        elif method == "kde":
            from app.core.kde_synth import KDESynthesizer
            return KDESynthesizer()
        elif method == "copula":
            from app.core.copula_synth import CopulaSynthesizer
            return CopulaSynthesizer()
        elif method in ("ctgan", "tvae"):
            from app.core.deep_synth import DeepSynthesizer
            return DeepSynthesizer(method=method)
        else:
            from app.core.kde_synth import KDESynthesizer
            return KDESynthesizer()

    def fit_and_sample(
        self, df: pd.DataFrame, n: int, method: str = "auto",
    ) -> pd.DataFrame:
        """Otomatik sec, fit et, ornekle — tek satir API."""
        selected = self.select(df, method)
        synth = self.create_synthesizer(selected)

        if selected == "stat":
            from app.core.analyzer import SchemaAnalyzer
            from app.core.classifier import SemanticClassifier
            from app.core.rule_engine import RuleEngine
            sa = SchemaAnalyzer()
            sc = SemanticClassifier()
            re = RuleEngine()
            schema = sa.analyze_dataframe("auto", df)
            schema = sc.enrich_schema(schema)
            rules = re.infer_rules(schema)
            return synth.generate(schema, rules, row_count=n)
        elif selected in ("ctgan", "tvae"):
            synth.fit(df)
            return synth.sample(n)
        else:
            synth.fit(df)
            return synth.sample(n)
