"""Visual — thin service facade for visual regression comparisons.

HTTP-agnostic. Raises ValueError/KeyError instead of HTTPException.
Wraps the compare module's compare_png function.
"""
from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, List, Optional

from app.domains.visual.compare import compare_png

logger = logging.getLogger(__name__)

# In-process result store (ephemeral — replace with DB persistence as needed)
_results: Dict[str, Dict[str, Any]] = {}


def start_comparison(
    name: str,
    actual_bytes: bytes,
    threshold_ratio: Optional[float] = None,
    update_baseline: bool = False,
) -> Dict[str, Any]:
    """Run a visual regression comparison.

    Args:
        name: Baseline name identifier (e.g. 'login', 'dashboard').
        actual_bytes: Raw PNG bytes of the candidate screenshot.
        threshold_ratio: Pixel-difference ratio threshold (0.0–1.0).
        update_baseline: If True, replace the stored baseline.

    Returns:
        Result dict including 'result_id', 'ok', 'status', 'diff_ratio', etc.

    Raises:
        ValueError: Empty image bytes or Pillow unavailable.
    """
    if not actual_bytes:
        raise ValueError("actual_bytes boş olamaz — geçerli bir PNG sağlayın.")

    result = compare_png(
        name=name,
        actual_bytes=actual_bytes,
        threshold_ratio=threshold_ratio,
        update_baseline=update_baseline,
    )

    if result.status == "pillow_unavailable":
        raise ValueError("Pillow kurulu değil — visual regression kullanılamıyor.")

    result_id = uuid.uuid4().hex[:12]
    entry: Dict[str, Any] = {
        "result_id": result_id,
        "name": name,
        "ok": result.ok,
        "status": result.status,
        "reason": result.reason,
        "baseline_path": result.baseline_path,
        "diff_path": result.diff_path,
        "diff_pixels": result.diff_pixels,
        "total_pixels": result.total_pixels,
        "diff_ratio": result.diff_ratio,
        "threshold_ratio": result.threshold_ratio,
        "width": result.width,
        "height": result.height,
    }
    _results[result_id] = entry
    logger.info(
        "Visual comparison: name=%s ok=%s diff_ratio=%s result_id=%s",
        name, result.ok, result.diff_ratio, result_id,
    )
    return entry


def get_result(result_id: str) -> Dict[str, Any]:
    """Fetch a stored comparison result by ID.

    Raises:
        KeyError: Result not found.
    """
    entry = _results.get(result_id)
    if entry is None:
        raise KeyError(f"Visual result '{result_id}' bulunamadı.")
    return entry


def list_results(name_filter: Optional[str] = None) -> List[Dict[str, Any]]:
    """Return all stored comparison results, optionally filtered by name.

    Args:
        name_filter: If provided, only return results matching this baseline name.
    """
    items = list(_results.values())
    if name_filter:
        items = [r for r in items if r.get("name") == name_filter]
    return items
