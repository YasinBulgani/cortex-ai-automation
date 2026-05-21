"""
DeepSynthesizer — CTGAN ve TVAE wrapper.

SDV kutuphanesi yuklu ise onu kullanir, degilse graceful fallback
olarak CopulaSynthesizer'a duser.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)

try:
    from sdv.single_table import CTGANSynthesizer as _CTGAN
    from sdv.single_table import TVAESynthesizer as _TVAE
    from sdv.metadata import Metadata as _Metadata
    HAS_SDV = True
except ImportError:
    HAS_SDV = False
    logger.info("SDV yuklu degil — DeepSynthesizer CopulaSynthesizer fallback kullanacak")


class DeepSynthesizer:
    """CTGAN/TVAE tabanlı derin ogrenme sentezleyici."""

    def __init__(self, method: str = "tvae") -> None:
        """
        Args:
            method: 'ctgan' veya 'tvae' (varsayilan tvae — daha kararli)
        """
        self._method = method
        self._model: Any = None
        self._metadata: Any = None
        self._fitted = False
        self._fallback = False

    @property
    def is_sdv_available(self) -> bool:
        return HAS_SDV

    # ------------------------------------------------------------------
    # Fit
    # ------------------------------------------------------------------

    def fit(self, df: pd.DataFrame, epochs: int = 300) -> dict:
        """Modeli egit. SDV yoksa CopulaSynthesizer'a fallback."""
        if not HAS_SDV:
            return self._fit_fallback(df)

        self._metadata = _Metadata.detect_from_dataframe(data=df, table_name="synthetic")

        if self._method == "ctgan":
            self._model = _CTGAN(self._metadata, epochs=epochs, verbose=True)
        else:
            self._model = _TVAE(self._metadata, epochs=epochs)

        self._model.fit(df)
        self._fitted = True
        logger.info("%s egitimi tamamlandi: %d satir, %d epoch", self._method.upper(), len(df), epochs)
        return {"status": "fitted", "method": self._method, "rows": len(df), "epochs": epochs}

    def _fit_fallback(self, df: pd.DataFrame) -> dict:
        """SDV yoksa Copula kulllan."""
        from app.core.copula_synth import CopulaSynthesizer
        self._model = CopulaSynthesizer()
        self._model.fit(df)
        self._fitted = True
        self._fallback = True
        logger.info("Fallback: CopulaSynthesizer kullaniliyor")
        return {"status": "fitted", "method": "copula_fallback", "rows": len(df)}

    # ------------------------------------------------------------------
    # Sample
    # ------------------------------------------------------------------

    def sample(self, n: int) -> pd.DataFrame:
        if not self._fitted:
            raise RuntimeError("Once fit() cagirin")

        if self._fallback:
            return self._model.sample(n)

        return self._model.sample(num_rows=n)

    # ------------------------------------------------------------------
    # Model Persistance
    # ------------------------------------------------------------------

    def save_model(self, path: str | Path) -> None:
        """Egitilmis modeli diske kaydet."""
        if not self._fitted:
            raise RuntimeError("Once fit() cagirin")

        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        if self._fallback:
            logger.warning("Copula fallback modeli kaydetme desteklemiyor")
            return

        self._model.save(str(path))
        logger.info("Model kaydedildi: %s", path)

    def load_model(self, path: str | Path) -> None:
        """Kaydedilmis modeli yukle."""
        if not HAS_SDV:
            raise RuntimeError("SDV yuklu degil — model yuklenemez")

        path = Path(path)
        if self._method == "ctgan":
            self._model = _CTGAN.load(str(path))
        else:
            self._model = _TVAE.load(str(path))
        self._fitted = True
        logger.info("Model yuklendi: %s", path)

    def get_status(self) -> dict:
        return {
            "method": self._method,
            "sdv_available": HAS_SDV,
            "fitted": self._fitted,
            "fallback": self._fallback,
        }
