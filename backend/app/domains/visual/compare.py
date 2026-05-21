"""Visual regression — baseline yönetimi + pixel diff.

Plan: docs/AI_OTOMASYON_GELISTIRME_PLANI.md §4 / E2.4.

Akış:
    1. Playwright test screenshot çeker → POST /visual/compare (name, image)
    2. Baseline store'da ``<name>.png`` varsa karşılaştır; yoksa yeni baseline
    3. Fark piksel sayısı → ratio; threshold üstündeyse FAIL + diff image üret
    4. Sonuç + diff yolu döner

Tasarım:
    * Opsiyonel Pillow bağımlılığı — yoksa "unavailable" döner, pipeline kırılmaz
    * Baseline store: VISUAL_BASELINE_DIR (default reports/visual/baselines)
    * Diff store: VISUAL_DIFF_DIR (default reports/visual/diffs)
    * Tolerans: VISUAL_THRESHOLD_PCT (default 0.5% — pixel farkı ratio)
    * Diff algoritması: piksel-piksel RGB delta; |r1-r2|+|g1-g2|+|b1-b2| > 30
      → farklı sayılır (antialiasing'e karşı dayanıklı)
    * Boyut uyumsuzluğunda resize YAPMAZ — mismatch olarak raporlar
      (baseline değişikliği operatör onayı gerektirir)

Kullanım (test'ten):
    from app.domains.visual import compare_png
    r = compare_png(name="login.png", actual_bytes=png_bytes)
    if not r.ok: raise AssertionError(r.reason)
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Optional, Tuple

logger = logging.getLogger(__name__)


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, str(default)))
    except ValueError:
        return default


def _baseline_dir() -> Path:
    raw = os.environ.get("VISUAL_BASELINE_DIR")
    if raw:
        return Path(raw).expanduser().resolve()
    return Path(__file__).resolve().parents[4] / "reports" / "visual" / "baselines"


def _diff_dir() -> Path:
    raw = os.environ.get("VISUAL_DIFF_DIR")
    if raw:
        return Path(raw).expanduser().resolve()
    return Path(__file__).resolve().parents[4] / "reports" / "visual" / "diffs"


# ── Result tipleri ──────────────────────────────────────────────────────


CompareStatus = Literal[
    "ok",
    "new_baseline",
    "size_mismatch",
    "diff_exceeds_threshold",
    "pillow_unavailable",
    "invalid_image",
]


@dataclass
class CompareResult:
    ok: bool
    status: CompareStatus
    reason: str
    baseline_path: Optional[str] = None
    diff_path: Optional[str] = None
    diff_pixels: int = 0
    total_pixels: int = 0
    diff_ratio: float = 0.0
    threshold_ratio: float = 0.0
    width: int = 0
    height: int = 0


# ── Pillow opsiyonel ────────────────────────────────────────────────────


def _load_pillow():
    try:
        from PIL import Image  # type: ignore

        return Image
    except ImportError:
        return None


# ── Pure diff (Pillow varsa) ─────────────────────────────────────────────


def _pixel_diff(
    img_a, img_b, *, per_pixel_delta_threshold: int = 30
) -> Tuple[int, int, Optional[object]]:
    """(diff_pixels, total, diff_image). Pillow gereklidir."""
    from PIL import Image, ImageChops  # type: ignore

    if img_a.size != img_b.size:
        raise ValueError(f"boyut uyumsuz: {img_a.size} vs {img_b.size}")

    a = img_a.convert("RGB")
    b = img_b.convert("RGB")
    diff = ImageChops.difference(a, b)
    # Diff pixel sayısı: her pixel'in toplam kanal farkı > threshold
    pixels = list(diff.getdata())
    changed = sum(
        1 for (r, g, bl) in pixels if (r + g + bl) > per_pixel_delta_threshold
    )
    total = len(pixels)

    # Diff görüntüsü: farkı kırmızı ile vurgula
    out = Image.new("RGB", a.size, (0, 0, 0))
    out_pixels = out.load()
    a_pixels = a.load()
    for y in range(a.size[1]):
        for x in range(a.size[0]):
            ar, ag, ab = a_pixels[x, y]
            br, bg, bb = img_b.convert("RGB").load()[x, y]
            delta = abs(ar - br) + abs(ag - bg) + abs(ab - bb)
            if delta > per_pixel_delta_threshold:
                out_pixels[x, y] = (255, 0, 0)
            else:
                # Greyscale'i hafifçe göster (bağlam için)
                gray = (ar + ag + ab) // 6
                out_pixels[x, y] = (gray, gray, gray)
    return changed, total, out


def _safe_name(name: str) -> str:
    """Path traversal + ayracı önle."""
    name = name.strip().replace("\\", "/")
    if ".." in name.split("/") or name.startswith("/"):
        raise ValueError(f"Güvensiz isim: {name}")
    # PNG uzantısı yoksa ekle
    if not name.lower().endswith(".png"):
        name += ".png"
    return name


# ── Public API ──────────────────────────────────────────────────────────


def compare_png(
    *,
    name: str,
    actual_bytes: bytes,
    threshold_ratio: Optional[float] = None,
    update_baseline: bool = False,
    baseline_dir: Optional[Path] = None,
    diff_dir: Optional[Path] = None,
) -> CompareResult:
    """PNG byte'larını baseline ile karşılaştır.

    Args:
        name: Baseline dosya adı (tests/login örneği → "login" veya
              "login.png"). Slash izinli (alt dizin), '..' yasak.
        actual_bytes: Yeni çekilen screenshot (PNG).
        threshold_ratio: Farkın max oranı (0..1). None → env.
        update_baseline: True → baseline değişti kabul edilir (operatör
            onayı sonrası; CI'da sadece manuel tetik). Baseline yoksa her
            durumda yeni baseline yazılır.
        baseline_dir / diff_dir: override; None → env veya default.
    """
    Image = _load_pillow()
    if Image is None:
        return CompareResult(
            ok=False,
            status="pillow_unavailable",
            reason="Pillow kurulu değil (pip install Pillow)",
        )

    try:
        safe = _safe_name(name)
    except ValueError as exc:
        return CompareResult(ok=False, status="invalid_image", reason=str(exc))

    base_dir = (baseline_dir or _baseline_dir()).resolve()
    d_dir = (diff_dir or _diff_dir()).resolve()
    base_dir.mkdir(parents=True, exist_ok=True)
    d_dir.mkdir(parents=True, exist_ok=True)

    baseline_path = base_dir / safe

    # Parse actual
    try:
        import io

        actual_img = Image.open(io.BytesIO(actual_bytes))
        actual_img.load()
    except Exception as exc:
        return CompareResult(ok=False, status="invalid_image", reason=str(exc))

    # Yeni baseline veya update
    if not baseline_path.exists() or update_baseline:
        baseline_path.parent.mkdir(parents=True, exist_ok=True)
        actual_img.save(baseline_path, format="PNG")
        return CompareResult(
            ok=True,
            status="new_baseline",
            reason="baseline yazıldı" if not update_baseline else "baseline güncellendi",
            baseline_path=str(baseline_path),
            width=actual_img.size[0],
            height=actual_img.size[1],
        )

    # Karşılaştır
    try:
        baseline_img = Image.open(baseline_path)
        baseline_img.load()
    except Exception as exc:
        return CompareResult(
            ok=False, status="invalid_image", reason=f"baseline okunamadı: {exc}"
        )

    if baseline_img.size != actual_img.size:
        return CompareResult(
            ok=False,
            status="size_mismatch",
            reason=(
                f"boyut farklı: baseline={baseline_img.size} "
                f"actual={actual_img.size}"
            ),
            baseline_path=str(baseline_path),
        )

    try:
        diff_px, total, diff_img = _pixel_diff(baseline_img, actual_img)
    except ValueError as exc:
        return CompareResult(ok=False, status="size_mismatch", reason=str(exc))

    ratio = diff_px / total if total else 0.0
    thr = threshold_ratio if threshold_ratio is not None else (
        _env_float("VISUAL_THRESHOLD_PCT", 0.005)
    )

    diff_path: Optional[str] = None
    ok = ratio <= thr
    if not ok and diff_img is not None:
        diff_out = d_dir / safe
        diff_out.parent.mkdir(parents=True, exist_ok=True)
        try:
            diff_img.save(diff_out, format="PNG")
            diff_path = str(diff_out)
        except Exception as exc:
            logger.warning("visual diff yazılamadı: %s", exc)

    return CompareResult(
        ok=ok,
        status="ok" if ok else "diff_exceeds_threshold",
        reason=(
            f"diff %{ratio*100:.3f} ≤ %{thr*100:.3f}"
            if ok
            else f"diff %{ratio*100:.3f} > %{thr*100:.3f}"
        ),
        baseline_path=str(baseline_path),
        diff_path=diff_path,
        diff_pixels=diff_px,
        total_pixels=total,
        diff_ratio=round(ratio, 6),
        threshold_ratio=round(thr, 6),
        width=actual_img.size[0],
        height=actual_img.size[1],
    )
