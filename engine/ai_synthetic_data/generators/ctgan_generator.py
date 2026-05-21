"""
CTGAN (Conditional Tabular GAN) tabanlı sentetik veri üretici.

SDV (Synthetic Data Vault) kütüphanesini kullanarak
tablo yapısındaki verileri derin öğrenme ile üretir.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class CTGANConfig:
    epochs: int = 100
    batch_size: int = 500
    generator_dim: tuple = (256, 256)
    discriminator_dim: tuple = (256, 256)
    verbose: bool = False


class CTGANGenerator:
    """CTGAN/SDV tabanlı sentetik veri üretici."""

    def __init__(self, config: CTGANConfig | None = None):
        self.config = config or CTGANConfig()
        self._model = None
        self._metadata = None

    def fit(self, records: list[dict], metadata: dict | None = None):
        """Orijinal veri üzerinde CTGAN modeli eğitir."""
        import pandas as pd
        from sdv.single_table import CTGANSynthesizer
        from sdv.metadata import Metadata

        df = pd.DataFrame(records)

        if metadata:
            self._metadata = Metadata.load_from_dict(metadata)
        else:
            self._metadata = Metadata()
            self._metadata.detect_from_dataframe(data=df)

        self._model = CTGANSynthesizer(
            metadata=self._metadata,
            epochs=self.config.epochs,
            batch_size=self.config.batch_size,
            generator_dim=self.config.generator_dim,
            discriminator_dim=self.config.discriminator_dim,
            verbose=self.config.verbose,
        )
        self._model.fit(df)

    def generate(self, count: int = 1000) -> list[dict]:
        """Eğitilmiş CTGAN modelinden sentetik veri üretir."""
        if self._model is None:
            raise RuntimeError("Model henüz eğitilmedi — önce fit() çağırın")
        df = self._model.sample(num_rows=count)
        return df.to_dict(orient="records")

    def evaluate(self, original: list[dict], synthetic: list[dict]) -> dict:
        """Üretilen verinin kalitesini SDV metrikleriyle değerlendirir."""
        import pandas as pd
        from sdv.evaluation.single_table import evaluate_quality

        orig_df = pd.DataFrame(original)
        syn_df = pd.DataFrame(synthetic)
        report = evaluate_quality(orig_df, syn_df, self._metadata)
        return {"overall_score": report.get_score(), "details": str(report.get_details())}

    @property
    def is_fitted(self) -> bool:
        return self._model is not None
