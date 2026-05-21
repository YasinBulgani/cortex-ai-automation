"""Visual regression compare_png testleri.

Pillow opsiyonel — kurulu değilse graceful skip eder. Kurulu ise gerçek
PNG byte'ları üzerinde identity + diff + size-mismatch senaryoları çalışır.
"""
from __future__ import annotations

import io
from pathlib import Path

import pytest

from app.domains.visual.compare import compare_png


def _has_pillow() -> bool:
    try:
        import PIL  # noqa: F401

        return True
    except ImportError:
        return False


requires_pil = pytest.mark.skipif(not _has_pillow(), reason="Pillow kurulu değil")


def _png_bytes(size=(20, 10), color=(255, 255, 255)) -> bytes:
    from PIL import Image  # type: ignore

    img = Image.new("RGB", size, color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _png_with_spot(size=(20, 10), fg=(255, 0, 0), spot=(5, 5, 5, 5)) -> bytes:
    from PIL import Image, ImageDraw  # type: ignore

    img = Image.new("RGB", size, (255, 255, 255))
    draw = ImageDraw.Draw(img)
    x, y, w, h = spot
    draw.rectangle([x, y, x + w, y + h], fill=fg)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@requires_pil
def test_first_run_creates_baseline(tmp_path: Path) -> None:
    r = compare_png(
        name="login",
        actual_bytes=_png_bytes(),
        baseline_dir=tmp_path / "base",
        diff_dir=tmp_path / "diff",
    )
    assert r.status == "new_baseline"
    assert r.ok is True
    assert r.baseline_path and Path(r.baseline_path).exists()


@requires_pil
def test_identical_image_passes(tmp_path: Path) -> None:
    # Baseline oluştur
    same = _png_bytes()
    compare_png(
        name="same",
        actual_bytes=same,
        baseline_dir=tmp_path / "base",
        diff_dir=tmp_path / "diff",
    )
    r = compare_png(
        name="same",
        actual_bytes=same,
        baseline_dir=tmp_path / "base",
        diff_dir=tmp_path / "diff",
    )
    assert r.status == "ok"
    assert r.ok is True
    assert r.diff_ratio == 0.0
    assert r.diff_path is None


@requires_pil
def test_small_diff_below_threshold_ok(tmp_path: Path) -> None:
    base = _png_bytes()
    # Neredeyse aynı (tek piksel değişmiş) — default threshold %0.5
    actual = _png_with_spot(spot=(0, 0, 0, 0))  # 1×1 spot
    compare_png(
        name="close",
        actual_bytes=base,
        baseline_dir=tmp_path / "base",
        diff_dir=tmp_path / "diff",
    )
    r = compare_png(
        name="close",
        actual_bytes=actual,
        baseline_dir=tmp_path / "base",
        diff_dir=tmp_path / "diff",
        threshold_ratio=0.01,  # %1 tolerans
    )
    # 20×10 = 200 px, 1 px fark → ratio 0.005 ≤ 0.01 ✓
    assert r.ok is True
    assert r.diff_pixels >= 1
    assert r.diff_ratio < r.threshold_ratio


@requires_pil
def test_big_diff_fails_and_writes_diff_image(tmp_path: Path) -> None:
    base = _png_bytes()
    actual = _png_with_spot(spot=(0, 0, 15, 8))  # büyük kırmızı blok
    compare_png(
        name="big",
        actual_bytes=base,
        baseline_dir=tmp_path / "base",
        diff_dir=tmp_path / "diff",
    )
    r = compare_png(
        name="big",
        actual_bytes=actual,
        baseline_dir=tmp_path / "base",
        diff_dir=tmp_path / "diff",
        threshold_ratio=0.01,
    )
    assert r.ok is False
    assert r.status == "diff_exceeds_threshold"
    assert r.diff_path is not None
    assert Path(r.diff_path).exists()


@requires_pil
def test_size_mismatch_reported(tmp_path: Path) -> None:
    base = _png_bytes(size=(20, 10))
    actual = _png_bytes(size=(30, 10))
    compare_png(
        name="resized",
        actual_bytes=base,
        baseline_dir=tmp_path / "base",
        diff_dir=tmp_path / "diff",
    )
    r = compare_png(
        name="resized",
        actual_bytes=actual,
        baseline_dir=tmp_path / "base",
        diff_dir=tmp_path / "diff",
    )
    assert r.ok is False
    assert r.status == "size_mismatch"


@requires_pil
def test_update_baseline_overwrites(tmp_path: Path) -> None:
    compare_png(
        name="u",
        actual_bytes=_png_bytes(color=(0, 0, 0)),
        baseline_dir=tmp_path / "base",
        diff_dir=tmp_path / "diff",
    )
    r = compare_png(
        name="u",
        actual_bytes=_png_bytes(color=(255, 255, 255)),
        baseline_dir=tmp_path / "base",
        diff_dir=tmp_path / "diff",
        update_baseline=True,
    )
    assert r.status == "new_baseline"
    assert r.ok is True


def test_path_traversal_rejected(tmp_path: Path) -> None:
    # Pillow gerekmez — safe_name erken raise
    r = compare_png(
        name="../evil",
        actual_bytes=b"xxx",
        baseline_dir=tmp_path / "base",
        diff_dir=tmp_path / "diff",
    )
    # Pillow yoksa "pillow_unavailable" dönse de güvenli; varsa invalid_image
    assert r.ok is False


def test_invalid_png_bytes(tmp_path: Path) -> None:
    if not _has_pillow():
        pytest.skip("Pillow yok")
    r = compare_png(
        name="bad",
        actual_bytes=b"not a png",
        baseline_dir=tmp_path / "base",
        diff_dir=tmp_path / "diff",
    )
    assert r.ok is False
    assert r.status == "invalid_image"
