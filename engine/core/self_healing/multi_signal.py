"""
Çok-Sinyalli Self-Healing (mabl tarzı)
═══════════════════════════════════════════════════════════════════════════

Mevcut ``locator_recovery.py`` bir **fallback cascade**tir (sırayla alternatif
selector dener). Bu modül onun yerine geçmez, onu **güçlendirir**: mabl'ın
yaptığı gibi her elementten **çok sayıda sinyal** (parmak izi) yakalar ve
locator kırıldığında canlı sayfadaki **tüm adayları ağırlıklı çok-sinyalli
benzerlikle** skorlayıp en iyi eşleşmeyi seçer.

İki aşama:
  1. ``capture_fingerprint(page, selector)`` — çalışan locator'dan zengin parmak
     izi çıkarır (id, testid, name, aria, role, text, placeholder, type, class,
     konum/bbox, komşu metinler, aynı-tag index, attribute sözlüğü).
  2. ``heal(page, fingerprint)`` — canlı sayfadaki tüm etkileşimli adayları
     çıkarır, her birini parmak izine karşı ``score()`` ile puanlar, eşik üstü
     en iyi adayın kararlı selector'ını döndürür.

``score()`` SAF fonksiyondur (browser'sız unit-test edilebilir).
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# ── Sinyal ağırlıkları (mabl: ~35 attribute, çok-sinyalli skorlama) ──────────
# Yalnızca parmak izinde MEVCUT olan sinyaller paydaya katılır → kısmi parmak
# izi de adil skorlanır.
_WEIGHTS: dict[str, float] = {
    "testid": 0.30,    # en güçlü kararlı sinyal
    "id": 0.18,
    "name": 0.12,
    "aria": 0.10,
    "text": 0.15,
    "placeholder": 0.07,
    "role": 0.05,
    "tag": 0.05,
    "type": 0.04,
    "classes": 0.06,   # Jaccard
    "position": 0.08,  # bbox merkez yakınlığı
    "neighbors": 0.08, # komşu metin örtüşmesi
    "tag_index": 0.04, # aynı tag içinde sıra
}

_DEFAULT_THRESHOLD = 0.55


# ── Saf benzerlik yardımcıları ───────────────────────────────────────────────

def _norm(s) -> str:
    return str(s or "").strip().lower()


def _token_overlap(a, b) -> float:
    """İki metnin token (kelime) Jaccard benzerliği (0..1)."""
    ta = {w for w in _norm(a).split() if w}
    tb = {w for w in _norm(b).split() if w}
    if not ta and not tb:
        return 0.0
    if not ta or not tb:
        return 0.0
    inter = len(ta & tb)
    union = len(ta | tb)
    return inter / union if union else 0.0


def _jaccard(a, b) -> float:
    sa, sb = set(a or []), set(b or [])
    if not sa and not sb:
        return 0.0
    union = len(sa | sb)
    return len(sa & sb) / union if union else 0.0


def _exact(a, b) -> float:
    a, b = _norm(a), _norm(b)
    return 1.0 if a and a == b else 0.0


def _position_sim(fp: dict, cand: dict) -> float:
    """bbox merkezleri arası mesafeden yakınlık (0..1). Viewport ~1500px varsayımı."""
    fb, cb = fp.get("bbox"), cand.get("bbox")
    if not fb or not cb:
        return 0.0
    fx = fb.get("x", 0) + fb.get("w", 0) / 2
    fy = fb.get("y", 0) + fb.get("h", 0) / 2
    cx = cb.get("x", 0) + cb.get("w", 0) / 2
    cy = cb.get("y", 0) + cb.get("h", 0) / 2
    dist = ((fx - cx) ** 2 + (fy - cy) ** 2) ** 0.5
    # 0px → 1.0, 1500px+ → 0.0
    return max(0.0, 1.0 - dist / 1500.0)


def score(fingerprint: dict, candidate: dict) -> float:
    """Bir adayın parmak izine çok-sinyalli ağırlıklı benzerliği (0..1).

    SAF fonksiyon — yalnızca dict girdileri kullanır, browser gerektirmez.
    """
    sims = {
        "testid": _exact(fingerprint.get("testid"), candidate.get("testid")),
        "id": _exact(fingerprint.get("id"), candidate.get("id")),
        "name": _exact(fingerprint.get("name"), candidate.get("name")),
        "aria": _exact(fingerprint.get("aria"), candidate.get("aria")),
        "text": max(_exact(fingerprint.get("text"), candidate.get("text")),
                    _token_overlap(fingerprint.get("text"), candidate.get("text"))),
        "placeholder": _exact(fingerprint.get("placeholder"), candidate.get("placeholder")),
        "role": _exact(fingerprint.get("role"), candidate.get("role")),
        "tag": _exact(fingerprint.get("tag"), candidate.get("tag")),
        "type": _exact(fingerprint.get("type"), candidate.get("type")),
        "classes": _jaccard(fingerprint.get("classes"), candidate.get("classes")),
        "position": _position_sim(fingerprint, candidate),
        "neighbors": _token_overlap(
            " ".join(fingerprint.get("neighbors", []) or []),
            " ".join(candidate.get("neighbors", []) or []),
        ),
        "tag_index": 1.0 if (fingerprint.get("tag_index") is not None
                             and fingerprint.get("tag_index") == candidate.get("tag_index")) else 0.0,
    }

    total_weight = 0.0
    acc = 0.0
    for sig, weight in _WEIGHTS.items():
        # Sinyal parmak izinde "mevcut" mu? (boş/None değilse paydaya kat)
        fp_val = fingerprint.get(sig if sig != "position" else "bbox")
        present = fp_val not in (None, "", [], {})
        if sig == "tag_index":
            present = fingerprint.get("tag_index") is not None
        if not present:
            continue
        total_weight += weight
        acc += weight * sims[sig]

    return round(acc / total_weight, 4) if total_weight else 0.0


def rank_candidates(fingerprint: dict, candidates: list[dict]) -> list[dict]:
    """Adayları skora göre azalan sırada döndürür (her birine 'score' ekler)."""
    scored = [{**c, "score": score(fingerprint, c)} for c in candidates]
    return sorted(scored, key=lambda c: c["score"], reverse=True)


def best_selector(candidate: dict) -> str:
    """Bir aday için en kararlı Playwright selector'ını üretir."""
    if candidate.get("testid"):
        return f'[data-testid="{candidate["testid"]}"]'
    if candidate.get("id"):
        return f'#{candidate["id"]}'
    if candidate.get("name"):
        return f'[name="{candidate["name"]}"]'
    if candidate.get("aria"):
        return f'[aria-label="{candidate["aria"]}"]'
    if candidate.get("text"):
        return f'text={candidate["text"]}'
    return candidate.get("css") or candidate.get("tag", "*")


# ── Canlı sayfa entegrasyonu (Playwright) ────────────────────────────────────

# Tek element ya da tüm adaylar için aynı sinyal sözleşmesini çıkaran JS.
_SIGNAL_FN = r"""
(el) => {
    const cs = (el.className && typeof el.className === 'string')
        ? el.className.trim().split(/\s+/).filter(Boolean) : [];
    const r = el.getBoundingClientRect();
    const sibsText = [];
    if (el.previousElementSibling) sibsText.push((el.previousElementSibling.innerText||'').trim().slice(0,40));
    if (el.nextElementSibling) sibsText.push((el.nextElementSibling.innerText||'').trim().slice(0,40));
    if (el.parentElement) sibsText.push((el.parentElement.getAttribute('aria-label')||'').trim().slice(0,40));
    let tagIndex = 0, sib = el;
    while (sib = sib.previousElementSibling) { if (sib.tagName === el.tagName) tagIndex++; }
    return {
        tag: el.tagName.toLowerCase(),
        id: el.id || '',
        testid: el.getAttribute('data-testid') || el.getAttribute('data-test-id') || '',
        name: el.getAttribute('name') || '',
        aria: el.getAttribute('aria-label') || '',
        role: el.getAttribute('role') || '',
        type: el.getAttribute('type') || '',
        placeholder: el.getAttribute('placeholder') || '',
        text: (el.innerText || el.value || '').trim().slice(0, 80),
        classes: cs,
        bbox: { x: r.x, y: r.y, w: r.width, h: r.height },
        neighbors: sibsText.filter(Boolean),
        tag_index: tagIndex,
    };
}
"""

_CANDIDATES_JS = r"""
() => {
    const SIGNAL = %s;
    const q = 'button, a[href], input:not([type=hidden]), textarea, select, ' +
              '[role=button], [role=link], [role=textbox], [role=tab], [role=menuitem], [onclick]';
    const out = [];
    document.querySelectorAll(q).forEach(el => {
        const st = window.getComputedStyle(el);
        if (st.display === 'none' || st.visibility === 'hidden') return;
        out.push(SIGNAL(el));
    });
    return out;
}
""" % _SIGNAL_FN.strip()


def capture_fingerprint(page, selector: str) -> dict | None:
    """Çalışan bir locator'dan zengin parmak izi yakalar (kayıt anında çağrılır)."""
    try:
        handle = page.query_selector(selector)
        if handle is None:
            return None
        fp = page.evaluate(f"({_SIGNAL_FN})", handle)
        fp["origin_selector"] = selector
        return fp
    except Exception as exc:
        logger.warning("Parmak izi yakalanamadı (%s): %s", selector, exc)
        return None


def collect_candidates(page) -> list[dict]:
    """Canlı sayfadaki tüm görünür etkileşimli elementlerin sinyallerini çıkarır."""
    try:
        return page.evaluate(_CANDIDATES_JS) or []
    except Exception as exc:
        logger.warning("Aday toplama başarısız: %s", exc)
        return []


def heal(page, fingerprint: dict, threshold: float = _DEFAULT_THRESHOLD) -> dict | None:
    """Kırılan locator için canlı sayfada en iyi çok-sinyalli eşleşmeyi bulur.

    Dönüş: ``{selector, score, signals, matched}`` veya eşik altıysa None.
    """
    candidates = collect_candidates(page)
    if not candidates:
        return None
    ranked = rank_candidates(fingerprint, candidates)
    top = ranked[0]
    if top["score"] < threshold:
        logger.info("Self-heal eşik altı: en iyi skor %.2f < %.2f", top["score"], threshold)
        return None
    return {
        "selector": best_selector(top),
        "score": top["score"],
        "matched": top,
        "runner_up_score": ranked[1]["score"] if len(ranked) > 1 else None,
        "candidates_considered": len(candidates),
    }
