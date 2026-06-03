"""
Semantik Görsel AI (Applitools / mabl tarzı)
═══════════════════════════════════════════════════════════════════════════

Mevcut ``visual_regression.py`` / ``visual_ai.py`` SSIM/pixel-diff yapar — ama
"pikseller (100,200)'de farklı" der. Bu modül farkı **anlamlandırır**:

  1. **DOM-bölge atfı**: değişen piksel kümelerini sayfanın DOM bileşenlerine
     (selector/role/text + bbox) eşler → "button#login kaymış/değişmiş".
  2. **Otomatik dinamik-bölge tespiti**: aynı durumun iki ardışık ekran
     görüntüsünü diff'ler; kendiliğinden değişen pikseller (saat, animasyon,
     reklam) volatil kabul edilip maskeye eklenir → pixel-diff'in ürettiği
     yanlış-pozitifler elenir. ("self-stabilizing baseline")
  3. **Anlamsal sınıflandırma**: appeared / disappeared / moved / resized /
     content_changed.

``attribute_to_components`` ve ``classify_change`` SAF fonksiyonlardır
(browser/numpy gerektirmez, unit-test edilebilir).
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

_DEFAULT_PX_THRESHOLD = 25     # bir pikselin "değişti" sayılması için RGB farkı
_GRID = 48                     # kümeleme ızgara çözünürlüğü (hücre sayısı/eksen)
_CELL_CHANGE_RATIO = 0.12      # bir ızgara hücresinin "değişti" sayılması oranı


# ═══════════════════════════════════════════════════════════════════════════
# SAF: geometri + atıf + sınıflandırma (browser'sız test edilebilir)
# ═══════════════════════════════════════════════════════════════════════════

def _overlap_area(a: dict, b: dict) -> float:
    """İki bbox'ın kesişim alanı (px²)."""
    ax2, ay2 = a["x"] + a["w"], a["y"] + a["h"]
    bx2, by2 = b["x"] + b["w"], b["y"] + b["h"]
    ix = max(0.0, min(ax2, bx2) - max(a["x"], b["x"]))
    iy = max(0.0, min(ay2, by2) - max(a["y"], b["y"]))
    return ix * iy


def _bbox_area(a: dict) -> float:
    return max(0.0, a["w"]) * max(0.0, a["h"])


def attribute_to_components(
    changed_boxes: list[dict],
    layout_boxes: list[dict],
    min_overlap_ratio: float = 0.10,
) -> list[dict]:
    """Değişen piksel kümelerini DOM bileşenlerine atfeder.

    ``changed_boxes``: [{x,y,w,h}] — değişen bölge bbox'ları
    ``layout_boxes``:  [{selector, role, text, x,y,w,h}] — DOM bileşenleri
    Dönüş: etkilenen bileşenler + örtüşme oranı (skora göre azalan).
    """
    findings: list[dict] = []
    for comp in layout_boxes:
        comp_area = _bbox_area(comp) or 1.0
        overlap = sum(_overlap_area(comp, cb) for cb in changed_boxes)
        ratio = min(1.0, overlap / comp_area)
        if ratio >= min_overlap_ratio:
            findings.append({
                "selector": comp.get("selector", ""),
                "role": comp.get("role", ""),
                "text": comp.get("text", ""),
                "bbox": {k: comp[k] for k in ("x", "y", "w", "h")},
                "change_ratio": round(ratio, 3),
            })
    return sorted(findings, key=lambda f: f["change_ratio"], reverse=True)


def classify_change(
    baseline_comp: dict | None,
    current_comp: dict | None,
    pos_tol: int = 6,
    size_tol: int = 6,
) -> str:
    """İki snapshot'taki aynı bileşenin durumundan değişim türünü sınıflandırır."""
    if baseline_comp and not current_comp:
        return "disappeared"
    if current_comp and not baseline_comp:
        return "appeared"
    if not baseline_comp and not current_comp:
        return "none"
    b, c = baseline_comp, current_comp
    moved = abs(b["x"] - c["x"]) > pos_tol or abs(b["y"] - c["y"]) > pos_tol
    resized = abs(b["w"] - c["w"]) > size_tol or abs(b["h"] - c["h"]) > size_tol
    text_changed = (b.get("text") or "").strip() != (c.get("text") or "").strip()
    if moved and resized:
        return "moved_resized"
    if moved:
        return "moved"
    if resized:
        return "resized"
    if text_changed:
        return "content_changed"
    return "unchanged"


def subtract_dynamic(changed_boxes: list[dict], dynamic_boxes: list[dict],
                     overlap_ratio: float = 0.6) -> tuple[list[dict], list[dict]]:
    """Dinamik (volatil) bölgelerle büyük oranda örtüşen değişimleri eler.

    Dönüş: (gerçek_değişimler, gürültü_olarak_elenenler)
    """
    real, noise = [], []
    for cb in changed_boxes:
        cb_area = _bbox_area(cb) or 1.0
        covered = sum(_overlap_area(cb, db) for db in dynamic_boxes)
        if covered / cb_area >= overlap_ratio:
            noise.append(cb)
        else:
            real.append(cb)
    return real, noise


# ═══════════════════════════════════════════════════════════════════════════
# numpy: piksel diff → değişen bölge kümeleri
# ═══════════════════════════════════════════════════════════════════════════

def changed_clusters(arr1, arr2, px_threshold: int = _DEFAULT_PX_THRESHOLD) -> list[dict]:
    """İki görüntü dizisinden değişen bölgelerin bbox kümelerini çıkarır.

    Izgara-tabanlı bağlı-bileşen kümeleme (hızlı, deterministik).
    """
    import numpy as np

    if arr1.shape != arr2.shape:
        # Boyut farkı → en küçük ortak alan
        h = min(arr1.shape[0], arr2.shape[0])
        w = min(arr1.shape[1], arr2.shape[1])
        arr1, arr2 = arr1[:h, :w], arr2[:h, :w]

    H, W = arr1.shape[0], arr1.shape[1]
    diff = np.abs(arr1.astype(np.int16) - arr2.astype(np.int16))
    mask = np.any(diff > px_threshold, axis=2) if diff.ndim == 3 else (diff > px_threshold)

    # Izgaraya indir: her hücrede değişen piksel oranı
    cell_h = max(1, H // _GRID)
    cell_w = max(1, W // _GRID)
    rows = (H + cell_h - 1) // cell_h
    cols = (W + cell_w - 1) // cell_w
    grid = np.zeros((rows, cols), dtype=bool)
    for r in range(rows):
        for c in range(cols):
            cell = mask[r * cell_h:(r + 1) * cell_h, c * cell_w:(c + 1) * cell_w]
            if cell.size and cell.mean() >= _CELL_CHANGE_RATIO:
                grid[r, c] = True

    # Bağlı hücreleri BFS ile kümele → bbox
    visited = np.zeros_like(grid)
    boxes: list[dict] = []
    for r in range(rows):
        for c in range(cols):
            if not grid[r, c] or visited[r, c]:
                continue
            stack = [(r, c)]
            visited[r, c] = True
            minr, maxr, minc, maxc = r, r, c, c
            while stack:
                cr, cc = stack.pop()
                minr, maxr = min(minr, cr), max(maxr, cr)
                minc, maxc = min(minc, cc), max(maxc, cc)
                for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nr, nc = cr + dr, cc + dc
                    if 0 <= nr < rows and 0 <= nc < cols and grid[nr, nc] and not visited[nr, nc]:
                        visited[nr, nc] = True
                        stack.append((nr, nc))
            boxes.append({
                "x": minc * cell_w, "y": minr * cell_h,
                "w": (maxc - minc + 1) * cell_w, "h": (maxr - minr + 1) * cell_h,
            })
    return boxes


# ═══════════════════════════════════════════════════════════════════════════
# Canlı sayfa: layout yakalama + dinamik bölge tespiti
# ═══════════════════════════════════════════════════════════════════════════

_LAYOUT_JS = r"""
() => {
    const q = 'button, a[href], input:not([type=hidden]), textarea, select, ' +
              'img, h1, h2, h3, [role=button], [role=link], [data-testid], nav, header, footer';
    const out = [];
    document.querySelectorAll(q).forEach(el => {
        const r = el.getBoundingClientRect();
        if (r.width < 4 || r.height < 4) return;
        const st = window.getComputedStyle(el);
        if (st.display === 'none' || st.visibility === 'hidden') return;
        let sel = el.id ? '#'+el.id
            : el.getAttribute('data-testid') ? `[data-testid="${el.getAttribute('data-testid')}"]`
            : el.tagName.toLowerCase();
        out.push({
            selector: sel,
            role: el.getAttribute('role') || el.tagName.toLowerCase(),
            text: (el.innerText || el.value || el.getAttribute('aria-label') || '').trim().slice(0, 50),
            x: Math.round(r.x), y: Math.round(r.y),
            w: Math.round(r.width), h: Math.round(r.height),
        });
    });
    return out;
}
"""


def capture_with_layout(page) -> dict:
    """Ekran görüntüsü (PNG bytes) + DOM bileşen kutuları döndürür."""
    layout = page.evaluate(_LAYOUT_JS) or []
    png = page.screenshot(full_page=False)
    return {"png": png, "layout": layout}


def detect_dynamic_regions(page, settle_ms: int = 700) -> list[dict]:
    """Aynı durumun iki ardışık görüntüsünü diff'leyip volatil bölgeleri bulur.

    Saat/animasyon/reklam gibi kendiliğinden değişen alanlar otomatik maskeye girer.
    """
    import numpy as np
    from io import BytesIO
    try:
        from PIL import Image
    except Exception:
        return []

    shot1 = page.screenshot(full_page=False)
    page.wait_for_timeout(settle_ms)
    shot2 = page.screenshot(full_page=False)
    a1 = np.array(Image.open(BytesIO(shot1)).convert("RGB"))
    a2 = np.array(Image.open(BytesIO(shot2)).convert("RGB"))
    return changed_clusters(a1, a2)


# ═══════════════════════════════════════════════════════════════════════════
# Orkestrasyon: semantik karşılaştırma
# ═══════════════════════════════════════════════════════════════════════════

def semantic_compare(
    baseline_png: bytes,
    current_png: bytes,
    layout_boxes: list[dict],
    dynamic_boxes: list[dict] | None = None,
    px_threshold: int = _DEFAULT_PX_THRESHOLD,
) -> dict:
    """Baseline vs current'ı semantik olarak karşılaştırır.

    Dönüş::

        {
          "verdict": "match|changed",
          "changed_components": [ {selector, role, text, change_ratio} ],
          "raw_changed_regions": int,
          "noise_filtered": int,
        }
    """
    import numpy as np
    from io import BytesIO
    from PIL import Image

    a1 = np.array(Image.open(BytesIO(baseline_png)).convert("RGB"))
    a2 = np.array(Image.open(BytesIO(current_png)).convert("RGB"))

    clusters = changed_clusters(a1, a2, px_threshold=px_threshold)
    real, noise = subtract_dynamic(clusters, dynamic_boxes or [])
    components = attribute_to_components(real, layout_boxes)

    return {
        "verdict": "changed" if components else "match",
        "changed_components": components,
        "raw_changed_regions": len(clusters),
        "noise_filtered": len(noise),
        "real_changed_regions": len(real),
    }
