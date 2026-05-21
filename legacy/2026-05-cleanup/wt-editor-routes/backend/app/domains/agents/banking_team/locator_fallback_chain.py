"""
AI Locator Fallback Chain — Selector kirildiginda 6 katmanli otomatik kurtarma.

Zincir (oncelik sirasina gore):
  Strateji 1: Exact Match — Orijinal selector'i dene
  Strateji 2: Attribute Cascade — data-testid > role > aria-label > id > name > placeholder > text
  Strateji 3: Similarity Search — Kirik selector'dan hint cikar, benzer element bul
  Strateji 4: pgvector Cache — Daha once ayni selector heal edilmis mi?
  Strateji 5: AI/LLM Onerisi — DOM context + hata bilgisi ile LLM'e sor
  Strateji 6: Playwright MCP Live — Gercek browser'da DOM tarayarak bul

Her strateji bir confidence skoru doner (0.0-1.0).
Zincir, confidence >= threshold olan ilk basarili stratejiyle durur.
Tum stratejiler basarisizsa, en yuksek confidence'li sonucu doner.

Entegrasyon:
  TestRunner -> LocatorFallbackChain.resolve() -> Calisan selector doner
  Healer -> LocatorFallbackChain kullanarak daha dogru heal yapar
"""
from __future__ import annotations

import logging
import time
import re
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# Confidence thresholds
DEFAULT_CONFIDENCE_THRESHOLD = 0.75
MIN_USEFUL_CONFIDENCE = 0.40

# ── Playwright selector parsers ──────────────────────────────────────────────
# Patterns to extract target values from Playwright-style selector strings.
_RE_GET_BY_TEST_ID = re.compile(r"(?:page\.)?getByTestId\(\s*['\"](.+?)['\"]\s*\)")
_RE_GET_BY_ROLE = re.compile(
    r"(?:page\.)?getByRole\(\s*['\"](.+?)['\"]"
    r"(?:\s*,\s*\{[^}]*name\s*:\s*['\"](.+?)['\"][^}]*\})?\s*\)"
)
_RE_GET_BY_LABEL = re.compile(r"(?:page\.)?getByLabel\(\s*['\"](.+?)['\"]\s*\)")
_RE_GET_BY_PLACEHOLDER = re.compile(r"(?:page\.)?getByPlaceholder\(\s*['\"](.+?)['\"]\s*\)")
_RE_GET_BY_TEXT = re.compile(r"(?:page\.)?getByText\(\s*['\"](.+?)['\"]\s*\)")
_RE_LOCATOR = re.compile(r"(?:page\.)?locator\(\s*['\"](.+?)['\"]\s*\)")

# Attribute tiers for Strategy 2 — (attr_name, confidence, stability, selector_builder)
_ATTRIBUTE_TIERS: list[tuple[str, float, int]] = [
    ("data-testid", 0.95, 5),
    ("role",        0.90, 5),
    ("aria-label",  0.85, 4),
    ("id",          0.80, 4),
    ("name",        0.75, 3),
    ("placeholder", 0.70, 3),
]

# Unstable ID patterns (React, Radix, MUI, hex hashes)
_UNSTABLE_ID_RE = re.compile(
    r"^(:r|:R|radix-|rc-|react-|\d+$|[a-f0-9]{6,}$)"
)


@dataclass
class FallbackResult:
    """Tek bir strateji sonucu."""
    strategy: str           # exact, attribute_cascade, similarity, cache, llm, playwright_live
    selector: str
    confidence: float       # 0.0-1.0
    stability_score: int    # 0-5
    found: bool
    element_info: dict[str, Any] = field(default_factory=dict)  # tag, text, attributes
    reason: str = ""
    latency_ms: int = 0


@dataclass
class ChainResult:
    """Fallback zincirinin toplam sonucu."""
    success: bool
    best: FallbackResult | None
    all_results: list[FallbackResult]
    original_selector: str
    strategies_tried: int
    total_latency_ms: int
    stopped_at_strategy: str = ""


def _not_found(strategy: str, reason: str = "") -> FallbackResult:
    """Hizli 'bulunamadi' sonucu olustur."""
    return FallbackResult(
        strategy=strategy, selector="", confidence=0.0,
        stability_score=0, found=False, reason=reason,
    )


# ── Selector Parsing Helpers ─────────────────────────────────────────────────

def _parse_selector_target(selector: str) -> dict[str, str | None]:
    """
    Playwright selector string'inden hedef bilgileri cikar.
    Doner: {type, value, name} — ornegin:
      page.getByTestId('login-btn') -> {type:'testid', value:'login-btn'}
      page.getByRole('button', {name:'OK'}) -> {type:'role', value:'button', name:'OK'}
      page.locator('#my-id') -> {type:'css', value:'#my-id'}
    """
    info: dict[str, str | None] = {"type": None, "value": None, "name": None}

    m = _RE_GET_BY_TEST_ID.search(selector)
    if m:
        info["type"] = "testid"
        info["value"] = m.group(1)
        return info

    m = _RE_GET_BY_ROLE.search(selector)
    if m:
        info["type"] = "role"
        info["value"] = m.group(1)
        info["name"] = m.group(2) if m.group(2) else None
        return info

    m = _RE_GET_BY_LABEL.search(selector)
    if m:
        info["type"] = "label"
        info["value"] = m.group(1)
        return info

    m = _RE_GET_BY_PLACEHOLDER.search(selector)
    if m:
        info["type"] = "placeholder"
        info["value"] = m.group(1)
        return info

    m = _RE_GET_BY_TEXT.search(selector)
    if m:
        info["type"] = "text"
        info["value"] = m.group(1)
        return info

    m = _RE_LOCATOR.search(selector)
    if m:
        info["type"] = "css"
        info["value"] = m.group(1)
        return info

    # Fallback: bare CSS / XPath
    stripped = selector.strip()
    if stripped.startswith("//") or stripped.startswith("xpath="):
        info["type"] = "xpath"
        info["value"] = stripped.replace("xpath=", "", 1)
    elif stripped:
        info["type"] = "css"
        info["value"] = stripped

    return info


def _extract_hints_from_selector(selector: str) -> dict[str, str | None]:
    """
    Kirik selector'dan ipucu cikar: tag, id fragment, class, text, attribute.
    Strategy 3 (similarity) icin kullanilir.
    """
    hints: dict[str, str | None] = {
        "tag": None,
        "id_fragment": None,
        "class_fragment": None,
        "text_hint": None,
        "attr_name": None,
        "attr_value": None,
        "testid_hint": None,
        "role_hint": None,
    }

    parsed = _parse_selector_target(selector)
    ptype = parsed.get("type")
    pvalue = parsed.get("value") or ""

    if ptype == "testid":
        hints["testid_hint"] = pvalue
        # testid'den tag ve isim cikarma: "login-btn" -> tag ipucu yok, text ipucu "login"
        parts = re.split(r"[-_]", pvalue)
        if parts:
            hints["text_hint"] = parts[0]
    elif ptype == "role":
        hints["role_hint"] = pvalue
        hints["text_hint"] = parsed.get("name")
    elif ptype == "label":
        hints["text_hint"] = pvalue
    elif ptype == "placeholder":
        hints["text_hint"] = pvalue
    elif ptype == "text":
        hints["text_hint"] = pvalue
    elif ptype == "css":
        css = pvalue
        # #id
        id_m = re.search(r"#([\w-]+)", css)
        if id_m:
            hints["id_fragment"] = id_m.group(1)
        # .class
        class_m = re.search(r"\.([\w-]+)", css)
        if class_m:
            hints["class_fragment"] = class_m.group(1)
        # tag
        tag_m = re.match(r"^(\w+)", css)
        if tag_m and tag_m.group(1) not in ("text", "xpath", "role", "label"):
            hints["tag"] = tag_m.group(1)
        # [attr=val]
        attr_m = re.search(r"\[(\w[\w-]*)=['\"]?([^'\"\]]+)", css)
        if attr_m:
            hints["attr_name"] = attr_m.group(1)
            hints["attr_value"] = attr_m.group(2)
    elif ptype == "xpath":
        # xpath'den tag cikar: //div[@id='x'] -> tag=div
        xpath_tag = re.search(r"//(\w+)", pvalue)
        if xpath_tag:
            hints["tag"] = xpath_tag.group(1)
        xpath_attr = re.search(r"@(\w+)=['\"]([^'\"]+)", pvalue)
        if xpath_attr:
            hints["attr_name"] = xpath_attr.group(1)
            hints["attr_value"] = xpath_attr.group(2)

    return hints


def _build_pw_selector(attr: str, value: str, tag: str = "") -> str:
    """Attribute + value'dan Playwright selector string olustur."""
    if attr == "data-testid":
        return "page.getByTestId('%s')" % value
    if attr == "role":
        return "page.getByRole('%s')" % value
    if attr == "aria-label":
        return "page.getByLabel('%s')" % value
    if attr == "placeholder":
        return "page.getByPlaceholder('%s')" % value
    if attr == "name":
        return "page.locator('%s[name=\"%s\"]')" % (tag or "*", value)
    if attr == "id":
        return "page.locator('#%s')" % value
    # fallback
    return "page.locator('[%s=\"%s\"]')" % (attr, value)


class LocatorFallbackChain:
    """
    6-strateji fallback zinciri.

    Kullanim:
        chain = LocatorFallbackChain()
        result = chain.resolve(
            selector="page.getByTestId('login-btn')",
            dom_snippet="<div>...</div>",
            page_url="https://app.example.com/login",
            error_message="locator.click: Timeout 5000ms exceeded",
        )
        if result.success:
            print(f"Yeni selector: {result.best.selector} (confidence: {result.best.confidence})")
    """

    def __init__(
        self,
        confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
        project_id: str | None = None,
    ):
        self.confidence_threshold = confidence_threshold
        self._project_id = project_id

    def resolve(
        self,
        selector: str,
        dom_snippet: str = "",
        page_url: str = "",
        error_message: str = "",
        context: dict[str, Any] | None = None,
        session_id: str = "",
        confidence_threshold: float | None = None,
    ) -> ChainResult:
        """
        6 katmanli fallback zincirini calistir.

        Args:
            selector: Kirilan orijinal selector
            dom_snippet: DOM HTML snippet (varsa)
            page_url: Sayfanin URL'si
            error_message: Playwright hata mesaji
            context: Ek baglam (test_name, file_path, vb.)
            session_id: Playwright MCP oturum ID'si (varsa)
        """
        t0 = time.time()
        results: list[FallbackResult] = []
        ctx = context or {}
        self._project_id = ctx.get("project_id") or self._project_id
        effective_threshold = confidence_threshold or self.confidence_threshold

        strategies = [
            ("exact", self._strategy_exact),
            ("attribute_cascade", self._strategy_attribute_cascade),
            ("similarity", self._strategy_similarity),
            ("cache", self._strategy_cache),
            ("llm", self._strategy_llm),
            ("playwright_live", self._strategy_playwright_live),
        ]

        stopped_at = ""
        for name, strategy_fn in strategies:
            try:
                st = time.time()
                result = strategy_fn(
                    selector=selector,
                    dom_snippet=dom_snippet,
                    page_url=page_url,
                    error_message=error_message,
                    context=ctx,
                    session_id=session_id,
                )
                result.latency_ms = int((time.time() - st) * 1000)
                results.append(result)

                if result.found and result.confidence >= effective_threshold:
                    stopped_at = name
                    break
            except Exception as exc:
                logger.debug("Fallback strateji '%s' hatasi: %s", name, exc)
                results.append(FallbackResult(
                    strategy=name,
                    selector="",
                    confidence=0.0,
                    stability_score=0,
                    found=False,
                    reason="Hata: %s" % str(exc)[:200],
                ))

        # En iyi sonucu bul
        successful = [r for r in results if r.found and r.confidence >= MIN_USEFUL_CONFIDENCE]
        best = max(successful, key=lambda r: r.confidence) if successful else None

        total_ms = int((time.time() - t0) * 1000)

        # KnowledgeStore'a kaydet (fire-and-forget)
        self._log_chain_result(selector, best, results, total_ms)

        return ChainResult(
            success=best is not None,
            best=best,
            all_results=results,
            original_selector=selector,
            strategies_tried=len(results),
            total_latency_ms=total_ms,
            stopped_at_strategy=stopped_at,
        )

    # ── Strategy 1: Exact Match ──────────────────────────────────────────────

    def _strategy_exact(self, selector: str, dom_snippet: str, **kwargs: Any) -> FallbackResult:
        """Orijinal selector DOM'da var mi kontrol et."""
        if not dom_snippet:
            return _not_found("exact", "DOM snippet yok — exact kontrol yapilamadi")

        parsed = _parse_selector_target(selector)
        ptype = parsed.get("type")
        pvalue = parsed.get("value") or ""

        if not ptype or not pvalue:
            return _not_found("exact", "Selector parse edilemedi")

        found = False
        element_info: dict[str, Any] = {}

        if ptype == "testid":
            pattern = re.compile(
                r'''data-testid\s*=\s*['"]''' + re.escape(pvalue) + r'''['"]''',
                re.IGNORECASE,
            )
            found = bool(pattern.search(dom_snippet))

        elif ptype == "role":
            pattern = re.compile(
                r'''role\s*=\s*['"]''' + re.escape(pvalue) + r'''['"]''',
                re.IGNORECASE,
            )
            found = bool(pattern.search(dom_snippet))
            # If role found but name specified, verify name too
            pname = parsed.get("name")
            if found and pname:
                name_pat = re.compile(
                    r'''(?:aria-label|name)\s*=\s*['"]''' + re.escape(pname) + r'''['"]''',
                    re.IGNORECASE,
                )
                found = bool(name_pat.search(dom_snippet))

        elif ptype == "label":
            pattern = re.compile(
                r'''aria-label\s*=\s*['"]''' + re.escape(pvalue) + r'''['"]''',
                re.IGNORECASE,
            )
            found = bool(pattern.search(dom_snippet))

        elif ptype == "placeholder":
            pattern = re.compile(
                r'''placeholder\s*=\s*['"]''' + re.escape(pvalue) + r'''['"]''',
                re.IGNORECASE,
            )
            found = bool(pattern.search(dom_snippet))

        elif ptype == "text":
            found = pvalue.lower() in dom_snippet.lower()

        elif ptype == "css":
            # CSS selector — try matching id, class, tag in DOM
            id_m = re.search(r"#([\w-]+)", pvalue)
            if id_m:
                pattern = re.compile(
                    r'''\bid\s*=\s*['"]''' + re.escape(id_m.group(1)) + r'''['"]''',
                    re.IGNORECASE,
                )
                found = bool(pattern.search(dom_snippet))
            else:
                # Try matching the entire selector as attribute pattern
                attr_m = re.search(r"\[(\w[\w-]*)=['\"]?([^'\"\]]+)", pvalue)
                if attr_m:
                    pattern = re.compile(
                        re.escape(attr_m.group(1)) + r'''\s*=\s*['"]''' +
                        re.escape(attr_m.group(2)) + r'''['"]''',
                        re.IGNORECASE,
                    )
                    found = bool(pattern.search(dom_snippet))

        elif ptype == "xpath":
            # xpath exact match is unreliable via regex — low confidence
            xpath_attr = re.search(r"@(\w+)=['\"]([^'\"]+)", pvalue)
            if xpath_attr:
                pattern = re.compile(
                    re.escape(xpath_attr.group(1)) + r'''\s*=\s*['"]''' +
                    re.escape(xpath_attr.group(2)) + r'''['"]''',
                    re.IGNORECASE,
                )
                found = bool(pattern.search(dom_snippet))

        if found:
            # Extract surrounding tag info for element_info
            if ptype == "testid":
                tag_m = re.search(
                    r"<(\w+)[^>]*data-testid\s*=\s*['\"]" + re.escape(pvalue) + r"['\"]",
                    dom_snippet, re.IGNORECASE,
                )
                if tag_m:
                    element_info["tag"] = tag_m.group(1).lower()

            return FallbackResult(
                strategy="exact",
                selector=selector,
                confidence=0.98,
                stability_score=5,
                found=True,
                element_info=element_info,
                reason="Orijinal selector DOM'da mevcut",
            )

        return _not_found("exact", "Orijinal selector DOM'da bulunamadi")

    # ── Strategy 2: Attribute Cascade ────────────────────────────────────────

    def _strategy_attribute_cascade(self, selector: str, dom_snippet: str, **kwargs: Any) -> FallbackResult:
        """Hierarchy: data-testid > role > aria-label > id > name > placeholder > text."""
        if not dom_snippet:
            return _not_found("attribute_cascade", "DOM snippet yok")

        # Parse selector to find what element we're looking for
        parsed = _parse_selector_target(selector)
        hints = _extract_hints_from_selector(selector)

        # Find the target element context in DOM — narrow down to nearby elements
        # Try to find a contextual region around the broken selector target
        target_region = dom_snippet  # default: search entire snippet

        # If we have a tag hint, look for elements of that tag
        tag_filter = hints.get("tag") or ""

        for attr_name, confidence, stability in _ATTRIBUTE_TIERS:
            # Extract all attribute values from DOM
            if attr_name == "data-testid":
                pattern = re.compile(
                    r'<(\w+)[^>]*?data-testid\s*=\s*[\'"]([^\'"]+)[\'"]([^>]*)>',
                    re.IGNORECASE | re.DOTALL,
                )
            elif attr_name == "role":
                pattern = re.compile(
                    r'<(\w+)[^>]*?role\s*=\s*[\'"]([^\'"]+)[\'"]([^>]*)>',
                    re.IGNORECASE | re.DOTALL,
                )
            elif attr_name == "aria-label":
                pattern = re.compile(
                    r'<(\w+)[^>]*?aria-label\s*=\s*[\'"]([^\'"]+)[\'"]([^>]*)>',
                    re.IGNORECASE | re.DOTALL,
                )
            elif attr_name == "id":
                pattern = re.compile(
                    r'<(\w+)[^>]*?\bid\s*=\s*[\'"]([^\'"]+)[\'"]([^>]*)>',
                    re.IGNORECASE | re.DOTALL,
                )
            elif attr_name == "name":
                pattern = re.compile(
                    r'<(\w+)[^>]*?\bname\s*=\s*[\'"]([^\'"]+)[\'"]([^>]*)>',
                    re.IGNORECASE | re.DOTALL,
                )
            elif attr_name == "placeholder":
                pattern = re.compile(
                    r'<(\w+)[^>]*?placeholder\s*=\s*[\'"]([^\'"]+)[\'"]([^>]*)>',
                    re.IGNORECASE | re.DOTALL,
                )
            else:
                continue

            matches = pattern.findall(target_region)
            if not matches:
                continue

            for match_tuple in matches:
                tag = match_tuple[0].lower()
                value = match_tuple[1]

                # Filter: if we have a tag hint, prefer matching tags
                if tag_filter and tag != tag_filter:
                    continue

                # Filter: skip unstable IDs
                if attr_name == "id" and _UNSTABLE_ID_RE.match(value):
                    continue

                # Filter: skip very short or numeric-only IDs
                if attr_name == "id" and (len(value) <= 2 or re.match(r"^\d+$", value)):
                    continue

                # Build selector
                new_selector = _build_pw_selector(attr_name, value, tag)

                # For role selectors, check if there's an aria-label/name nearby
                if attr_name == "role":
                    rest_of_tag = match_tuple[2] if len(match_tuple) > 2 else ""
                    full_tag_str = match_tuple[0] + " " + rest_of_tag
                    name_m = re.search(
                        r'(?:aria-label|name)\s*=\s*[\'"]([^\'"]+)[\'"]',
                        full_tag_str, re.IGNORECASE,
                    )
                    if name_m:
                        role_name = name_m.group(1)
                        new_selector = "page.getByRole('%s', { name: '%s' })" % (value, role_name)
                        confidence = min(confidence + 0.03, 0.98)

                return FallbackResult(
                    strategy="attribute_cascade",
                    selector=new_selector,
                    confidence=confidence,
                    stability_score=stability,
                    found=True,
                    element_info={"tag": tag, "attr": attr_name, "value": value},
                    reason="Attribute cascade: %s='%s' bulundu" % (attr_name, value),
                )

        # Text fallback tier — lowest priority
        text_matches = re.findall(r">([^<]{3,40})<", target_region)
        text_matches = [t.strip() for t in text_matches if t.strip() and not t.strip().startswith("{")]
        if text_matches:
            # If we have a text hint from the selector, prefer matching texts
            text_hint = hints.get("text_hint")
            best_text = text_matches[0]
            if text_hint:
                for txt in text_matches:
                    if text_hint.lower() in txt.lower():
                        best_text = txt
                        break

            return FallbackResult(
                strategy="attribute_cascade",
                selector="page.getByText('%s')" % best_text.replace("'", "\\'"),
                confidence=0.60,
                stability_score=2,
                found=True,
                element_info={"text": best_text},
                reason="Attribute cascade: text='%s' ile eslesti" % best_text,
            )

        return _not_found("attribute_cascade", "Hicbir attribute katmaninda esleme bulunamadi")

    # ── Strategy 3: Similarity Search ────────────────────────────────────────

    def _strategy_similarity(self, selector: str, dom_snippet: str, **kwargs: Any) -> FallbackResult:
        """Kirik selector'dan hint cikar, DOM'da en benzer elementi bul."""
        if not dom_snippet:
            return _not_found("similarity", "DOM snippet yok")

        hints = _extract_hints_from_selector(selector)

        # Collect all elements from DOM
        element_pattern = re.compile(r"<(\w+)(\s[^>]*)?>", re.DOTALL)
        elements: list[dict[str, Any]] = []

        for m in element_pattern.finditer(dom_snippet):
            tag = m.group(1).lower()
            attrs_str = m.group(2) or ""

            # Skip non-interactive or structural tags
            if tag in ("html", "head", "body", "meta", "link", "script", "style", "br", "hr"):
                continue

            # Extract all attributes
            attrs: dict[str, str] = {}
            for attr_m in re.finditer(r'(\w[\w-]*)\s*=\s*[\'"]([^\'"]*)[\'"]', attrs_str):
                attrs[attr_m.group(1).lower()] = attr_m.group(2)

            # Extract text content following this element (simplified)
            pos = m.end()
            close_pos = dom_snippet.find("<", pos)
            text = dom_snippet[pos:close_pos].strip() if close_pos > pos else ""
            text = text[:100]

            elements.append({
                "tag": tag,
                "attrs": attrs,
                "text": text,
                "start": m.start(),
            })

        if not elements:
            return _not_found("similarity", "DOM'da parse edilebilir element bulunamadi")

        # Score each element against hints
        scored: list[tuple[float, dict[str, Any]]] = []
        for elem in elements:
            score = 0.0
            match_reasons: list[str] = []
            attrs = elem["attrs"]

            # testid match (partial)
            if hints.get("testid_hint") and attrs.get("data-testid"):
                if hints["testid_hint"].lower() in attrs["data-testid"].lower():
                    score += 4.0
                    match_reasons.append("testid partial match")
                elif _token_overlap(hints["testid_hint"], attrs["data-testid"]) >= 0.5:
                    score += 2.5
                    match_reasons.append("testid token overlap")

            # role match
            if hints.get("role_hint") and attrs.get("role"):
                if hints["role_hint"].lower() == attrs["role"].lower():
                    score += 3.0
                    match_reasons.append("role match")

            # tag match
            if hints.get("tag") and elem["tag"] == hints["tag"].lower():
                score += 1.0
                match_reasons.append("tag match")

            # id fragment match
            if hints.get("id_fragment") and attrs.get("id"):
                if hints["id_fragment"].lower() in attrs["id"].lower():
                    score += 3.0
                    match_reasons.append("id fragment match")

            # class fragment match
            if hints.get("class_fragment"):
                class_val = attrs.get("class", "")
                if hints["class_fragment"].lower() in class_val.lower():
                    score += 2.0
                    match_reasons.append("class fragment match")

            # attr match
            if hints.get("attr_name") and hints.get("attr_value"):
                attr_val = attrs.get(hints["attr_name"], "")
                if attr_val and hints["attr_value"].lower() in attr_val.lower():
                    score += 3.0
                    match_reasons.append("attr value match")

            # text match
            if hints.get("text_hint") and elem["text"]:
                if hints["text_hint"].lower() in elem["text"].lower():
                    score += 2.0
                    match_reasons.append("text match")

            if score >= 2.0:
                scored.append((score, {**elem, "reasons": match_reasons}))

        if not scored:
            return _not_found("similarity", "Hicbir element 2+ ipucu ile eslesemedi")

        scored.sort(key=lambda x: x[0], reverse=True)
        best_score, best_elem = scored[0]

        # Normalize score to confidence (max plausible score ~12)
        max_plausible = 12.0
        raw_confidence = min(best_score / max_plausible, 1.0)
        # Scale to 0.40-0.90 range
        confidence = 0.40 + raw_confidence * 0.50

        # Build selector for best match
        best_attrs = best_elem["attrs"]
        new_selector = ""
        stability = 2

        if best_attrs.get("data-testid"):
            new_selector = "page.getByTestId('%s')" % best_attrs["data-testid"]
            stability = 5
        elif best_attrs.get("role"):
            label = best_attrs.get("aria-label", "")
            if label:
                new_selector = "page.getByRole('%s', { name: '%s' })" % (best_attrs["role"], label)
            else:
                new_selector = "page.getByRole('%s')" % best_attrs["role"]
            stability = 5
        elif best_attrs.get("aria-label"):
            new_selector = "page.getByLabel('%s')" % best_attrs["aria-label"]
            stability = 4
        elif best_attrs.get("id") and not _UNSTABLE_ID_RE.match(best_attrs["id"]):
            new_selector = "page.locator('#%s')" % best_attrs["id"]
            stability = 4
        elif best_attrs.get("name"):
            new_selector = "page.locator('%s[name=\"%s\"]')" % (best_elem["tag"], best_attrs["name"])
            stability = 3
        elif best_attrs.get("placeholder"):
            new_selector = "page.getByPlaceholder('%s')" % best_attrs["placeholder"]
            stability = 3
        elif best_elem["text"]:
            new_selector = "page.getByText('%s')" % best_elem["text"].replace("'", "\\'")
            stability = 2
        else:
            return _not_found("similarity", "Benzer element bulundu ama selector uretilemedi")

        return FallbackResult(
            strategy="similarity",
            selector=new_selector,
            confidence=round(confidence, 3),
            stability_score=stability,
            found=True,
            element_info={
                "tag": best_elem["tag"],
                "text": best_elem.get("text", ""),
                "match_score": best_score,
                "reasons": best_elem.get("reasons", []),
            },
            reason="Similarity: %s (skor=%.1f)" % (
                ", ".join(best_elem.get("reasons", [])), best_score
            ),
        )

    # ── Strategy 4: pgvector Cache ───────────────────────────────────────────

    def _strategy_cache(self, selector: str, **kwargs: Any) -> FallbackResult:
        """KnowledgeStore'dan daha once ayni selector icin heal var mi?"""
        try:
            from app.domains.ai.knowledge_store import KnowledgeStore
        except ImportError:
            return _not_found("cache", "KnowledgeStore import edilemedi")

        try:
            store = KnowledgeStore(project_id=self._project_id)
            chunks = store.retrieve(
                "Selector Heal: '%s'" % selector,
                top_k=3,
                sources=["error_pattern"],
                min_similarity=0.80,
                project_id=self._project_id,
            )

            if not chunks:
                return _not_found("cache", "Cache'de benzer heal bulunamadi")

            # Find best matching heal record
            for chunk in chunks:
                meta = chunk.metadata or {}
                if meta.get("type") != "selector_heal":
                    continue

                healed_selector = meta.get("healed", "")
                if not healed_selector:
                    continue

                cached_strategy = meta.get("strategy", "cached")
                cached_confidence = float(meta.get("confidence", 0.80))
                similarity = chunk.similarity

                # Adjust confidence based on similarity
                # similarity 0.80 -> confidence * 0.85
                # similarity 1.00 -> confidence * 1.00
                adj_factor = 0.70 + similarity * 0.30
                adjusted_confidence = min(cached_confidence * adj_factor, 0.95)

                # Determine stability from cached strategy
                stability_map = {
                    "data-testid": 5, "role": 5,
                    "aria-label": 4, "label": 4, "id": 4,
                    "placeholder": 3, "name": 3,
                    "text": 2, "css": 2,
                    "xpath": 1, "llm": 3,
                }
                stability = stability_map.get(cached_strategy, 3)

                return FallbackResult(
                    strategy="cache",
                    selector=healed_selector,
                    confidence=round(adjusted_confidence, 3),
                    stability_score=stability,
                    found=True,
                    element_info={
                        "cached_strategy": cached_strategy,
                        "similarity": round(similarity, 3),
                        "original_confidence": cached_confidence,
                    },
                    reason="Cache hit: benzerlik=%.2f strateji=%s" % (similarity, cached_strategy),
                )

            return _not_found("cache", "Cache kayitlari eslesmedi (type != selector_heal)")

        except Exception as exc:
            logger.debug("Cache strateji hatasi: %s", exc)
            return _not_found("cache", "Cache sorgu hatasi: %s" % str(exc)[:100])

    # ── Strategy 5: AI/LLM ──────────────────────────────────────────────────

    def _strategy_llm(self, selector: str, dom_snippet: str, error_message: str, **kwargs: Any) -> FallbackResult:
        """LLM ile DOM + hata analizi yaparak yeni selector oner."""
        if not dom_snippet and not error_message:
            return _not_found("llm", "DOM ve hata mesaji yok — LLM'e gonderilecek veri yetersiz")

        try:
            from .auto_healer import AutoHealerAgent
        except ImportError:
            return _not_found("llm", "AutoHealerAgent import edilemedi")

        try:
            healer = AutoHealerAgent()
            llm_result = healer._llm_heal(
                broken=selector,
                dom=dom_snippet[:2000],
                error=error_message[:500],
                test_name=kwargs.get("context", {}).get("test_name", ""),
            )

            if not llm_result:
                return _not_found("llm", "LLM onerisi donmedi")

            new_selector = llm_result.get("selector", "")
            if not new_selector:
                return _not_found("llm", "LLM bos selector onerdi")

            llm_confidence = float(llm_result.get("confidence", 0.70))
            llm_stability = int(llm_result.get("stability", 3))
            strategy_name = llm_result.get("strategy", "llm")

            return FallbackResult(
                strategy="llm",
                selector=new_selector,
                confidence=min(llm_confidence, 0.90),  # LLM cap at 0.90
                stability_score=llm_stability,
                found=True,
                element_info={
                    "llm_strategy": strategy_name,
                    "root_cause": llm_result.get("root_cause", ""),
                    "reason": llm_result.get("reason", ""),
                },
                reason="LLM onerisi: %s (strateji=%s)" % (
                    llm_result.get("reason", "")[:100], strategy_name
                ),
            )

        except Exception as exc:
            logger.debug("LLM strateji hatasi: %s", exc)
            return _not_found("llm", "LLM cagrisi basarisiz: %s" % str(exc)[:100])

    # ── Strategy 6: Playwright MCP Live ──────────────────────────────────────

    def _strategy_playwright_live(
        self, selector: str, session_id: str, page_url: str, **kwargs: Any,
    ) -> FallbackResult:
        """Playwright MCP ile gercek browser'da DOM tarayarak element bul."""
        if not session_id:
            return _not_found("playwright_live", "session_id yok — canli tarama yapilamaz")

        try:
            import asyncio
            from app.domains.playwright_mcp.browser_manager import BrowserManager
        except ImportError:
            return _not_found("playwright_live", "BrowserManager import edilemedi")

        try:
            manager = BrowserManager()

            async def _live_search() -> FallbackResult:
                # 1. Validate the original selector
                try:
                    validation = await manager.validate_selectors(
                        session_id, [selector],
                    )
                    results = validation.get("results", [])
                    if results and results[0].get("found"):
                        # Original selector works in live browser
                        alternatives = results[0].get("suggested_alternatives", [])
                        stability = results[0].get("stability_score", 3)
                        return FallbackResult(
                            strategy="playwright_live",
                            selector=selector,
                            confidence=0.95,
                            stability_score=stability,
                            found=True,
                            element_info={
                                "tag": results[0].get("tag_name", ""),
                                "attributes": results[0].get("attributes", {}),
                                "alternatives": alternatives,
                            },
                            reason="Canli browser'da orijinal selector calisiyor",
                        )
                except (KeyError, RuntimeError):
                    pass  # Session not found or other error — continue to suggest

                # 2. Try suggest_selectors with a description derived from selector
                parsed = _parse_selector_target(selector)
                description = parsed.get("value") or parsed.get("name") or selector
                # Expand description with type info
                if parsed.get("type") == "testid":
                    description = "test id %s" % description
                elif parsed.get("type") == "role":
                    name = parsed.get("name") or ""
                    description = "%s %s" % (description, name)

                try:
                    suggestions = await manager.suggest_selectors(
                        session_id, description.strip(),
                    )
                except (KeyError, RuntimeError):
                    return _not_found(
                        "playwright_live",
                        "Session '%s' bulunamadi veya hata" % session_id,
                    )

                if not suggestions:
                    return _not_found(
                        "playwright_live",
                        "Canli browser'da eslesen element bulunamadi",
                    )

                best = suggestions[0]
                raw_selector = best.get("selector", "")
                stability = best.get("stability_score", 2)

                # Convert raw CSS selector to Playwright API if possible
                pw_selector = _css_to_playwright_selector(raw_selector)

                return FallbackResult(
                    strategy="playwright_live",
                    selector=pw_selector,
                    confidence=min(0.85, 0.60 + stability * 0.05),
                    stability_score=stability,
                    found=True,
                    element_info={
                        "tag": best.get("tag_name", ""),
                        "attributes": best.get("attributes", {}),
                        "alternatives": best.get("suggested_alternatives", []),
                    },
                    reason="Canli browser suggest: '%s'" % pw_selector,
                )

            # Run the async function — handle both sync and async contexts
            try:
                loop = asyncio.get_running_loop()
                # Already in async context — cannot run synchronously
                # Return not-found; caller should use async version
                return _not_found(
                    "playwright_live",
                    "Async context — sync cagri yapilamadi (session_id: %s)" % session_id,
                )
            except RuntimeError:
                # No running loop — safe to use asyncio.run()
                return asyncio.run(_live_search())

        except Exception as exc:
            logger.debug("Playwright live strateji hatasi: %s", exc)
            return _not_found(
                "playwright_live",
                "Canli tarama hatasi: %s" % str(exc)[:100],
            )

    # ── Helper: Log to KnowledgeStore ────────────────────────────────────────

    def _log_chain_result(
        self,
        original: str,
        best: FallbackResult | None,
        all_results: list[FallbackResult],
        total_ms: int,
    ) -> None:
        """Fire-and-forget logging."""
        try:
            from app.domains.ai.knowledge_store import KnowledgeStore
            store = KnowledgeStore(project_id=self._project_id)
            store.ingest(
                text=(
                    "Locator Fallback: '%s' -> '%s' "
                    "strateji=%s conf=%s"
                ) % (
                    original,
                    best.selector if best else "FAIL",
                    best.strategy if best else "none",
                    best.confidence if best else 0,
                ),
                source="error_pattern",
                metadata={
                    "type": "locator_fallback",
                    "original": original,
                    "resolved": best.selector if best else "",
                    "strategy": best.strategy if best else "",
                    "confidence": best.confidence if best else 0,
                    "strategies_tried": len(all_results),
                    "total_ms": total_ms,
                },
                project_id=self._project_id,
            )
        except Exception:
            pass


# ── Module-level helpers ─────────────────────────────────────────────────────

def _token_overlap(a: str, b: str) -> float:
    """Iki string arasindaki token (tire/alt cizgi parcalari) overlap orani."""
    tokens_a = set(re.split(r"[-_\s]+", a.lower()))
    tokens_b = set(re.split(r"[-_\s]+", b.lower()))
    tokens_a.discard("")
    tokens_b.discard("")
    if not tokens_a or not tokens_b:
        return 0.0
    intersection = tokens_a & tokens_b
    union = tokens_a | tokens_b
    return len(intersection) / len(union) if union else 0.0


def _css_to_playwright_selector(css_sel: str) -> str:
    """
    Raw CSS selector'i Playwright API formatina donustur (best-effort).
    '[data-testid="x"]' -> "page.getByTestId('x')"
    '#myid' -> "page.locator('#myid')"
    """
    css_sel = css_sel.strip()

    # data-testid
    tid_m = re.match(r'^\[data-testid=["\']([^"\']+)["\']\]$', css_sel)
    if tid_m:
        return "page.getByTestId('%s')" % tid_m.group(1)

    # role + aria-label
    role_m = re.search(r'role=["\']([^"\']+)["\']', css_sel)
    if role_m:
        label_m = re.search(r'aria-label=["\']([^"\']+)["\']', css_sel)
        if label_m:
            return "page.getByRole('%s', { name: '%s' })" % (role_m.group(1), label_m.group(1))
        return "page.getByRole('%s')" % role_m.group(1)

    # aria-label
    al_m = re.match(r'^\[aria-label=["\']([^"\']+)["\']\]$', css_sel)
    if al_m:
        return "page.getByLabel('%s')" % al_m.group(1)

    # placeholder
    ph_m = re.match(r'^\[placeholder=["\']([^"\']+)["\']\]$', css_sel)
    if ph_m:
        return "page.getByPlaceholder('%s')" % ph_m.group(1)

    # text=
    txt_m = re.match(r'^text=["\']([^"\']+)["\']$', css_sel)
    if txt_m:
        return "page.getByText('%s')" % txt_m.group(1)

    # #id
    id_m = re.match(r'^#[\w-]+$', css_sel)
    if id_m:
        return "page.locator('%s')" % css_sel

    # Anything else — wrap in locator
    return "page.locator('%s')" % css_sel.replace("'", "\\'")
