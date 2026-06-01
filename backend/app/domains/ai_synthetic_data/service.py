"""AI Synthetic Data — thin service facade.

HTTP-agnostic. Raises ValueError for bad input, KeyError for not-found.
Wraps KDE / CTGAN generator internals.
"""
from __future__ import annotations

import logging
import time
import uuid
from typing import Any, Dict, List, Optional

from app.domains.ai_synthetic_data.advanced_generators import (
    BankingDataGenerator,
    CTGANGenerator,
    KDEGenerator,
)

logger = logging.getLogger(__name__)

# In-process dataset store (ephemeral — replace with DB persistence as needed)
_datasets: Dict[str, Dict[str, Any]] = {}


def generate(config: Dict[str, Any]) -> Dict[str, Any]:
    """Generate synthetic records from sample data.

    Args:
        config: Must contain 'sample_data' (list[dict]).
                Optional: 'generator_type' ('kde'|'ctgan'), 'count' (int),
                'seed' (int), 'conditions' (dict).

    Returns:
        Dict with 'dataset_id', 'records', 'quality_metrics', 'duration_ms'.

    Raises:
        ValueError: Missing or invalid sample_data / generator_type.
    """
    sample_data: List[dict] = config.get("sample_data") or []
    if not sample_data:
        raise ValueError("sample_data zorunludur — en az birkaç örnek satır sağlayın.")

    generator_type: str = str(config.get("generator_type") or "kde").lower()
    count: int = int(config.get("count") or 10)
    seed: Optional[int] = config.get("seed")
    conditions: Optional[dict] = config.get("conditions")

    t0 = time.time()

    if generator_type == "ctgan":
        gen = CTGANGenerator()
        gen.fit(sample_data)
        records = gen.generate(count, conditions=conditions)
        quality = gen.quality_report(sample_data, records)
    elif generator_type == "kde":
        gen_kde = KDEGenerator()
        gen_kde.fit(sample_data)
        records = gen_kde.generate(count, seed=seed)
        quality = gen_kde.quality_metrics(sample_data, records)
    else:
        raise ValueError(f"Bilinmeyen generator_type: '{generator_type}'. Geçerli: 'kde', 'ctgan'.")

    duration_ms = round((time.time() - t0) * 1000, 2)
    dataset_id = uuid.uuid4().hex[:12]

    _datasets[dataset_id] = {
        "id": dataset_id,
        "dataset_id": dataset_id,  # alias for API compatibility
        "generator_type": generator_type,
        "count": len(records),
        "records": records,
        "quality_metrics": quality,
        "duration_ms": duration_ms,
    }
    logger.info("Synthetic dataset %s üretildi (%d kayıt, %s ms)", dataset_id, len(records), duration_ms)
    return _datasets[dataset_id]


def list_datasets() -> List[Dict[str, Any]]:
    """Return summaries of all in-process generated datasets."""
    return [
        {k: v for k, v in ds.items() if k != "records"}
        for ds in _datasets.values()
    ]


def get_dataset(dataset_id: str) -> Dict[str, Any]:
    """Fetch a generated dataset by ID.

    Raises:
        KeyError: Dataset not found.
    """
    ds = _datasets.get(dataset_id)
    if ds is None:
        raise KeyError(f"Dataset '{dataset_id}' bulunamadı.")
    return ds
