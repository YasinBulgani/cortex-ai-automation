"""DSL Grounding for BDD — packages/dsl/catalog'u BDD üretimine bağlar.

İki ana API:

1. ``grounded_aliases_for_text(text, top_k=30)`` — Verilen doğal dil metni için
   kataloğun en alakalı TR alias'larını getirir ve Given/When/Then kovasına
   ayırır. LLM sistem prompt'una ve rule-based fallback'e "allow-list" olarak
   enjekte edilir.

2. ``snap_step_to_catalog(keyword, text, min_score=0.55)`` — LLM veya
   fallback'in ürettiği ham bir step metnini en yakın DSL alias'ına map
   eder. Eşleşen kanonik kalıp + parametre yer tutucusunu dolduracak bir
   metin + action_id döner. Post-process aşamasında "Giriş Yap butonuna
   tıklar" gibi ifadeleri kanonik "kullanıcı \"Giriş Yap\" metnine tıklar"
   kalıbına çevirmek için kullanılır.

Hem BDDGenerator (requirement-based) hem de legacy ``generate_bdd_scenarios``
(analysis-based) yollarını bu ortak modül besler. Katalog yüklenemezse tüm
fonksiyonlar sessizce "no-op" döner — mevcut davranış korunur.

Python 3.9+ uyumlu.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any, Dict, Iterable, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ── Heuristic mappings ───────────────────────────────────────────────────────

# Kategoriden Gherkin kovasına: ilk eşleşen kullanılır.
_CATEGORY_TO_BUCKET: List[Tuple[str, str]] = [
    ("assert.", "then"),
    ("assertions.", "then"),
    ("api.response", "then"),
    ("bgts.state.", "given"),
    ("bgts.auth", "given"),
    ("ui.wait", "given"),
    ("ui.open", "given"),
    ("ui.navigate", "given"),
    ("api.request", "when"),
    ("ui.", "when"),
    ("mobile.", "when"),
]

# Tag'den kovaya (öncelik): given/when/then tag'i varsa direkt ona düşer.
_TAG_BUCKETS = ("given", "when", "then")

# Tırnaklı ifadeleri parametre yer tutucusuna çevirmek için regex.
_QUOTED_RE = re.compile(r'"([^"]+)"|\'([^\']+)\'')

# {param} veya {string} gibi yer tutucuları bulmak için.
_PLACEHOLDER_RE = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")

# Parametre yer tutucularını eşleştirmek için.
_PARAM_CAPTURE_RE = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")


# ── Public API: Grounding ────────────────────────────────────────────────────


@dataclass
class GroundedAlias:
    """Tek bir aday DSL alias'ı."""

    action_id: str
    pattern: str  # canonical TR (veya EN fallback) alias
    language: str
    category: str
    bucket: str  # "given" | "when" | "then"
    score: float = 0.0


@dataclass
class GroundedAliases:
    """Metin için getirilen aday alias'ların given/when/then kovalarına ayrılmış hali."""

    given: List[GroundedAlias] = field(default_factory=list)
    when: List[GroundedAlias] = field(default_factory=list)
    then: List[GroundedAlias] = field(default_factory=list)
    flat: List[GroundedAlias] = field(default_factory=list)

    def is_empty(self) -> bool:
        return not (self.given or self.when or self.then or self.flat)


def grounded_aliases_for_text(
    text: str,
    *,
    top_k: int = 30,
    lang: Optional[str] = "tr",
) -> GroundedAliases:
    """Verilen metne en alakalı DSL alias'larını döner.

    hybrid_search çalışıyorsa onu, yoksa lexical search, o da yoksa tüm
    kataloğu fallback olarak kullanır. Katalog yoksa boş ``GroundedAliases``
    döner (mevcut davranışı bozmaz).

    Args:
        text: Gereksinim, analiz metni veya senaryo başlığı.
        top_k: Toplam döndürülecek aday sayısı. Kovalar arası eşit dağıtılır.
        lang: Tercih edilen alias dili. "tr" öncelikli; yoksa "en" fallback.
    """
    if not text or not text.strip():
        return GroundedAliases()

    cache_key = _cache_key(text, top_k, lang)
    cached = _grounded_cache_get(cache_key)
    if cached is not None:
        return cached

    try:
        hits = _fetch_hybrid_hits(text, top_k=top_k, lang=lang)
    except Exception as exc:  # noqa: BLE001
        logger.debug("DSL hybrid_search başarısız, fallback lexical: %s", exc)
        hits = _fetch_lexical_hits(text, top_k=top_k, lang=lang)

    if not hits:
        hits = _fetch_lexical_hits(text, top_k=top_k, lang=lang)

    grouped = _bucketize(hits)
    _grounded_cache_set(cache_key, grouped)
    return grouped


def grounding_as_prompt_block(
    grounded: GroundedAliases,
    *,
    max_per_bucket: int = 10,
    header: str = "## DSL Standart Kalıpları (ÖNCELİKLE bunları kullan)",
) -> str:
    """``GroundedAliases``'ı LLM prompt'una enjekte edilecek metne çevirir."""
    if grounded.is_empty():
        return ""

    sections: List[str] = [header]

    def _dump_bucket(label: str, items: List[GroundedAlias]) -> None:
        if not items:
            return
        sections.append("\n{lbl}:".format(lbl=label))
        for g in items[:max_per_bucket]:
            sections.append("- {p}".format(p=g.pattern))

    _dump_bucket("DIYELIM KI (Given)", grounded.given)
    _dump_bucket("EGER (When)", grounded.when)
    _dump_bucket("O ZAMAN (Then)", grounded.then)

    sections.append(
        "\nKURAL: Listede tam uyan kalıp varsa onu kullan, parametrelerini "
        "(\"{text}\", \"{value}\" gibi yer tutucuları) senaryo bağlamına "
        "göre doldur. Kalıp bulamazsan doğal Türkçe yaz ama adıma "
        "\"@needs-dsl\" tag'i ekle."
    )
    return "\n".join(sections)


# ── Public API: Snap ─────────────────────────────────────────────────────────


@dataclass
class SnappedStep:
    """Ham bir step'in DSL'e snap edilmiş hali."""

    canonical_pattern: str  # "{text} butonuna tıklanır" gibi yer tutuculu
    filled_text: str  # parametreler dolduruldu — "\"Giriş Yap\" butonuna tıklanır"
    action_id: str
    score: float
    language: str


def snap_step_to_catalog(
    keyword: str,
    text: str,
    *,
    min_score: float = 0.55,
    lang: Optional[str] = "tr",
) -> Optional[SnappedStep]:
    """Ham step metnini en yakın DSL alias'ına map eder.

    Args:
        keyword: Gherkin anahtar kelimesi ("Diyelim ki", "Eger", "O zaman"…).
                 Kova hint'i olarak kullanılır (given/when/then filtresi).
        text: Step metni (keyword'süz). Örn: "Giriş Yap butonuna tıklar".
        min_score: Eşik. Altındaysa None döner (snap yapma).
        lang: Tercih edilen alias dili.

    Returns:
        Eşleşme varsa ``SnappedStep``, yoksa ``None``.
    """
    if not text or not text.strip():
        return None

    bucket_hint = _keyword_to_bucket(keyword)

    # hybrid_search top 8 ile en yakın alias adayını bul
    try:
        hits = _fetch_hybrid_hits(text, top_k=8, lang=lang)
    except Exception:
        hits = []

    # Hybrid boş döndüyse lexical fallback (token-overlap) kullan
    if not hits:
        hits = _fetch_lexical_hits(text, top_k=8, lang=lang)

    if not hits:
        return None

    # Kova hint'i uyanlara öncelik ver; hiç uyan yoksa genel listeyi kullan.
    preferred = [h for h in hits if h.bucket == bucket_hint] if bucket_hint else []
    candidates = preferred if preferred else hits

    # Skor yeniden hesapla: hybrid score + fuzzy overlap bonus
    best: Optional[Tuple[float, GroundedAlias]] = None
    for cand in candidates:
        combined = _combined_snap_score(cand, text)
        if best is None or combined > best[0]:
            best = (combined, cand)

    if best is None or best[0] < min_score:
        return None

    score, alias = best
    filled = _fill_placeholders(alias.pattern, text)
    return SnappedStep(
        canonical_pattern=alias.pattern,
        filled_text=filled,
        action_id=alias.action_id,
        score=round(score, 3),
        language=alias.language,
    )


def snap_steps(
    steps: Iterable[Dict[str, Any]],
    *,
    min_score: float = 0.55,
) -> List[Dict[str, Any]]:
    """Batch: step listesini snap eder, orijinal step yapısını korur.

    Her step'e (snap başarılıysa) ``dsl_action_id``, ``dsl_score``,
    ``dsl_canonical`` alanları eklenir ve ``text`` kanonik hale getirilir.
    Snap eşik altındaysa step değişmeden kalır.
    """
    snapped: List[Dict[str, Any]] = []
    for raw in steps:
        if not isinstance(raw, dict):
            snapped.append(raw)
            continue
        keyword = raw.get("keyword", "")
        text = raw.get("text", "")
        result = snap_step_to_catalog(keyword, text, min_score=min_score)
        if result is None:
            snapped.append(raw)
            continue
        merged = dict(raw)
        merged["text"] = result.filled_text
        merged["dsl_action_id"] = result.action_id
        merged["dsl_score"] = result.score
        merged["dsl_canonical"] = result.canonical_pattern
        snapped.append(merged)
    return snapped


# ── Internal: hit fetching ───────────────────────────────────────────────────


def _fetch_hybrid_hits(
    query: str,
    *,
    top_k: int,
    lang: Optional[str],
) -> List[GroundedAlias]:
    """``dsl.service.hybrid_search`` üzerinden aday listesi kur."""
    try:
        from app.domains.dsl import service as dsl_service
    except Exception:
        return []

    response = dsl_service.hybrid_search(query, limit=top_k, lang=lang)
    items = getattr(response, "items", []) or []
    result: List[GroundedAlias] = []
    for it in items:
        action = getattr(it, "action", None)
        if action is None:
            continue
        pattern = _pick_pattern(action, preferred=getattr(it, "matched_language", lang) or lang)
        if not pattern:
            continue
        result.append(
            GroundedAlias(
                action_id=action.id,
                pattern=pattern,
                language=getattr(it, "matched_language", "tr") or "tr",
                category=action.category or "",
                bucket=_action_bucket(action),
                score=float(getattr(it, "score", 0.0) or 0.0),
            )
        )
    return result


def _fetch_lexical_hits(
    query: str,
    *,
    top_k: int,
    lang: Optional[str],
) -> List[GroundedAlias]:
    """Token-overlap tabanlı lexical fallback.

    ``catalog_cache.search`` substring tabanlıdır — ``"kullanıcı tıklar"``
    sorgusu ``kullanıcı "{text}" metnine tıklar`` alias'ına isabet etmez.
    Burada query ve alias'ı kelime bazında karşılaştırıp Jaccard benzeri bir
    skorla sıralıyoruz. Böylece fiil/anahtar kelime uyuşmaları yakalanır.
    """
    try:
        from app.domains.dsl.loader import catalog_cache
    except Exception:
        return []

    try:
        actions = catalog_cache.all()
    except Exception as exc:  # noqa: BLE001
        logger.debug("catalog_cache.all() başarısız: %s", exc)
        return []

    if not actions:
        return []

    q_tokens = _tokenize_for_match(query)
    if not q_tokens:
        return []

    scored: List[Tuple[float, GroundedAlias]] = []
    for action in actions:
        aliases = (action.aliases or {})
        lang_order = [lang] if lang else list(aliases.keys())
        # "tr" öncelikli olsun
        if "tr" in lang_order and lang_order[0] != "tr":
            lang_order = ["tr"] + [l for l in lang_order if l != "tr"]

        best_score = 0.0
        best_alias: Optional[str] = None
        best_lang: Optional[str] = None

        for ln in lang_order:
            for alias in aliases.get(ln, []):
                score = _token_overlap_score(q_tokens, alias)
                if score > best_score:
                    best_score = score
                    best_alias = alias
                    best_lang = ln

        # Description üzerinden de dene (alias'sız action'lar için)
        if best_alias is None:
            desc_score = _token_overlap_score(q_tokens, action.description or "")
            if desc_score > best_score:
                best_score = desc_score
                best_alias = _pick_pattern(action, preferred=lang or "tr")
                best_lang = lang or "tr"

        if best_alias and best_score > 0.0:
            scored.append((
                best_score,
                GroundedAlias(
                    action_id=action.id,
                    pattern=best_alias,
                    language=best_lang or "tr",
                    category=action.category or "",
                    bucket=_action_bucket(action),
                    score=best_score,
                ),
            ))

    scored.sort(key=lambda s: -s[0])
    return [ga for _, ga in scored[:top_k]]


def _tokenize_for_match(text: str) -> set:
    """Çok kısa ve stop-word karakterleri filtreleyerek token kümesi üret."""
    if not text:
        return set()
    lowered = _normalize(text)
    tokens = set()
    for tok in lowered.split():
        if len(tok) < 3:
            continue
        # Parametre placeholder'ları atla
        if tok.startswith("{") and tok.endswith("}"):
            continue
        tokens.add(tok)
    return tokens


def _token_overlap_score(q_tokens: set, alias: str) -> float:
    """q_tokens ile alias arasındaki Jaccard benzeri skor (0-1)."""
    if not alias or not q_tokens:
        return 0.0
    alias_tokens = _tokenize_for_match(_strip_placeholders(alias))
    if not alias_tokens:
        return 0.0
    overlap = q_tokens & alias_tokens
    if not overlap:
        return 0.0
    # Alias tarafındaki anahtar kelimelerin yüzdesi — kısa alias'lar avantajlı
    return len(overlap) / max(len(alias_tokens), 1)


def _pick_pattern(action: Any, *, preferred: Optional[str]) -> str:
    """Action'dan gösterilecek alias string'ini seç. TR öncelikli."""
    aliases = getattr(action, "aliases", {}) or {}
    order = []
    if preferred:
        order.append(preferred)
    for fallback in ("tr", "en"):
        if fallback not in order:
            order.append(fallback)

    for ln in order:
        vals = aliases.get(ln)
        if vals:
            return vals[0]

    # Son çare: description
    desc = getattr(action, "description", "") or ""
    return desc.replace("Eylem: ", "").replace("Doğrulama: ", "").strip()


# ── Internal: bucketizing ────────────────────────────────────────────────────


def _bucketize(hits: List[GroundedAlias]) -> GroundedAliases:
    """Adayları given/when/then kovalarına ayır ve tekilleştir."""
    seen: set = set()
    given: List[GroundedAlias] = []
    when: List[GroundedAlias] = []
    then: List[GroundedAlias] = []
    flat: List[GroundedAlias] = []

    for h in hits:
        if h.action_id in seen:
            continue
        seen.add(h.action_id)
        flat.append(h)
        if h.bucket == "given":
            given.append(h)
        elif h.bucket == "then":
            then.append(h)
        else:
            when.append(h)

    # Skora göre sırala
    given.sort(key=lambda g: -g.score)
    when.sort(key=lambda g: -g.score)
    then.sort(key=lambda g: -g.score)
    flat.sort(key=lambda g: -g.score)
    return GroundedAliases(given=given, when=when, then=then, flat=flat)


def _action_bucket(action: Any) -> str:
    """Tag + kategori heuristics ile bucket belirle."""
    tags = [t.lower() for t in (getattr(action, "tags", []) or [])]
    for t in tags:
        if t in _TAG_BUCKETS:
            return t

    category = (getattr(action, "category", "") or "").lower()
    for prefix, bucket in _CATEGORY_TO_BUCKET:
        if category.startswith(prefix):
            return bucket

    # Son heuristic: description fiilleri
    desc = (getattr(action, "description", "") or "").lower()
    if "doğrulama" in desc or "olmalı" in desc or "görünür" in desc:
        return "then"
    if "ön koşul" in desc or "hazır" in desc:
        return "given"
    return "when"


def _keyword_to_bucket(keyword: str) -> Optional[str]:
    kw = (keyword or "").lower().strip().rstrip(":")
    if not kw:
        return None
    if kw in ("diyelim ki", "olduğu gibi", "given"):
        return "given"
    if kw in ("eğer", "eger", "when"):
        return "when"
    if kw in ("o zaman", "then"):
        return "then"
    if kw in ("ve", "ama", "and", "but"):
        return None  # bilinmiyor — kullanıcıya bırak
    return None


# ── Internal: snap scoring ───────────────────────────────────────────────────


def _combined_snap_score(alias: GroundedAlias, text: str) -> float:
    """Hybrid hit skoru + kelime çakışma bonusunu birleştir.

    Snap için kritik olan: pattern'in anlamlı kelimelerinin çoğu metinde
    geçiyor mu? Metinde fazladan kelime olması (ör. parametre değerleri)
    snap skorunu düşürmemeli. Bu yüzden overlap_ratio = overlap / |pattern|.
    """
    text_norm = _normalize(text)
    pattern_norm = _normalize(_strip_placeholders(alias.pattern))
    # Stop-word çok kısa token'ları at — "ki", "ve" gibi
    text_words = {w for w in text_norm.split() if len(w) >= 3}
    pattern_words = {w for w in pattern_norm.split() if len(w) >= 3}
    if not text_words or not pattern_words:
        return alias.score

    overlap = text_words & pattern_words
    # "Pattern'in yüzde kaçı metinde geçiyor" — snap için doğru metrik bu.
    overlap_ratio = len(overlap) / max(len(pattern_words), 1)
    # Hybrid skoru (0-1) + pattern-merkezli overlap — ağırlıklı toplam.
    return (alias.score * 0.45) + (overlap_ratio * 0.55)


def _normalize(text: str) -> str:
    lowered = text.lower()
    # Noktalama temizliği
    lowered = re.sub(r"[\"',.;:!?()\[\]]+", " ", lowered)
    lowered = re.sub(r"\s+", " ", lowered).strip()
    return lowered


def _strip_placeholders(pattern: str) -> str:
    return _PLACEHOLDER_RE.sub(" ", pattern)


def _fill_placeholders(pattern: str, source_text: str) -> str:
    """Pattern'deki {param} yer tutucularını source_text'ten çıkarılan
    tırnaklı değerlerle doldur. Yeterli değer yoksa yer tutucuyu bırak.

    Pattern'de zaten "{x}" şeklinde tırnaklarla sarılı yer tutucu varsa
    ekstra tırnak eklemiyoruz (yoksa ""Sign in"" gibi çift tırnak çıkar).
    """
    params = _PARAM_CAPTURE_RE.findall(pattern)
    if not params:
        return pattern

    quoted_values: List[str] = []
    for m in _QUOTED_RE.finditer(source_text):
        val = m.group(1) or m.group(2)
        if val:
            quoted_values.append(val)

    # Tırnaklı değer yoksa Büyük harfle başlayan kelime öbeklerini kullan
    if not quoted_values:
        quoted_values = _extract_capitalized_phrases(source_text)

    filled = pattern
    for i, name in enumerate(params):
        if i >= len(quoted_values):
            break
        placeholder = "{" + name + "}"
        value = quoted_values[i]
        # Pattern'de "{x}" ise tırnak pattern tarafında zaten var; yalın değer koy.
        # Diğer durumda değeri tırnakla sar.
        quoted_placeholder_double = '"' + placeholder + '"'
        quoted_placeholder_single = "'" + placeholder + "'"
        if quoted_placeholder_double in filled:
            filled = filled.replace(quoted_placeholder_double, '"{v}"'.format(v=value), 1)
        elif quoted_placeholder_single in filled:
            filled = filled.replace(quoted_placeholder_single, "'{v}'".format(v=value), 1)
        else:
            filled = filled.replace(placeholder, '"{v}"'.format(v=value), 1)
    return filled


def _extract_capitalized_phrases(text: str) -> List[str]:
    """Büyük harfle başlayan kelime öbeklerini yakalar ("Giriş Yap" gibi)."""
    phrases: List[str] = []
    words = text.split()
    buffer: List[str] = []
    for w in words:
        cleaned = w.strip(".,;:!?\"'()[]")
        if cleaned and cleaned[0].isupper() and len(cleaned) > 1:
            buffer.append(cleaned)
        else:
            if buffer:
                phrases.append(" ".join(buffer))
                buffer = []
    if buffer:
        phrases.append(" ".join(buffer))
    return phrases


# ── Internal: caching ────────────────────────────────────────────────────────

# LRU cache — aynı metin için tekrarlanan çağrılar için.
_GROUND_CACHE_MAX = 256
_ground_cache: Dict[str, GroundedAliases] = {}
_ground_cache_order: List[str] = []


def _cache_key(text: str, top_k: int, lang: Optional[str]) -> str:
    # İlk 512 karakter yeterli — çok uzun metinler için hash kullanırız.
    snippet = text.strip()[:512]
    return "{k}|{t}|{l}".format(k=top_k, t=snippet, l=lang or "")


def _grounded_cache_get(key: str) -> Optional[GroundedAliases]:
    return _ground_cache.get(key)


def _grounded_cache_set(key: str, value: GroundedAliases) -> None:
    if key in _ground_cache:
        return
    _ground_cache[key] = value
    _ground_cache_order.append(key)
    while len(_ground_cache_order) > _GROUND_CACHE_MAX:
        oldest = _ground_cache_order.pop(0)
        _ground_cache.pop(oldest, None)


def clear_grounding_cache() -> None:
    """Test / katalog reload sonrası cache'i temizlemek için."""
    _ground_cache.clear()
    _ground_cache_order.clear()


# ── Debug helpers ────────────────────────────────────────────────────────────


@lru_cache(maxsize=1)
def is_catalog_available() -> bool:
    """Katalog yüklenebilir durumda mı? (ImportError / filesystem hatası varsa False.)"""
    try:
        from app.domains.dsl.loader import catalog_cache
        catalog_cache.ensure_loaded()
        return len(catalog_cache.all()) > 0
    except Exception:
        return False
