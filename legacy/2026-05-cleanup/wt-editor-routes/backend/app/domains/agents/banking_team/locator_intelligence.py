"""
Locator Intelligence — Proaktif selector analizi ve POM uretimi.

Yetenekler:
  1. Stability Analysis — Tum selector'lari tarayip kirilma riski hesapla
  2. Proactive Suggestions — Zayif selector'lar icin iyilestirme oner
  3. Heal History Learning — Gecmis heal'lerden pattern ogren
  4. POM Generator — DOM'dan Page Object Model uret
  5. Trend Analysis — Hangi selector tipleri en cok kiriliyor?

Entegrasyon:
  LocatorIntelligence.analyze_stability(locators) -> StabilityReport
  LocatorIntelligence.generate_page_object(url, elements) -> TypeScript POM kodu
  LocatorIntelligence.predict_breakage(locators) -> Kirilma tahminleri
"""
from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field
from typing import Any

from .base_agent import BaseAgent, AgentResult

logger = logging.getLogger(__name__)

# ── Stability scoring rules ─────────────────────────────────────────────────
# Mirrors dom_analyzer.compute_selector_stability but with enriched detail.

_STABILITY_RULES: list[tuple[str, int, str]] = [
    # (pattern_description, score, reason)
    ("data-testid", 5, "data-testid: en stabil, deployment'lar arasi degismez"),
    ("data-test-id", 5, "data-test-id: en stabil variant"),
    ("getByTestId", 5, "getByTestId: Playwright best practice"),
    ("getByRole", 5, "getByRole: accessibility-first, stabil"),
    ("role=", 5, "role attribute: stabil"),
    ("aria-label", 4, "aria-label: accessibility attribute, yuksek stabilite"),
    ("getByLabel", 4, "getByLabel: aria-label/label bazli, iyi"),
    ("label=", 4, "label association: stabil"),
    ("#", 4, "id selector: genelde stabil (dynamic id'ler haric)"),
    ("getByPlaceholder", 3, "placeholder: orta stabilite, metin degisebilir"),
    ("placeholder", 3, "placeholder attr: orta stabilite"),
    ("[name=", 3, "name attribute: form element'leri icin iyi"),
    ("getByText", 2, "text bazli: metin degisikligi riski var"),
    ("text=", 2, "text selector: metin degisikligi riski"),
    ("xpath=", 1, "xpath: en kirilgan, DOM yapisi degisince kirilir"),
    ("//", 1, "xpath: en kirilgan"),
]

# Patterns that indicate an unstable selector
_UNSTABLE_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r":r[A-Z0-9]"), "React auto-generated id (:rX pattern)"),
    (re.compile(r"radix-"), "Radix UI dynamic id"),
    (re.compile(r"rc-\w+-\d+"), "rc-component dynamic id"),
    (re.compile(r"react-select"), "react-select dynamic id"),
    (re.compile(r"\.[a-zA-Z0-9_]{20,}"), "CSS module hash class (>20 char)"),
    (re.compile(r"nth-child\(\d+\)"), "nth-child: DOM sirasi degisince kirilir"),
    (re.compile(r">\s*>.*>"), "Deeply nested child combinator (>3)"),
    (re.compile(r"\s+\w+\s+\w+\s+\w+\s+\w+"), "Deeply nested descendant (>4 levels)"),
    (re.compile(r"style="), "Inline style selector — cok kirilgan"),
    (re.compile(r"\[class\*?="), "Class attribute selector — CSS module/tailwind riski"),
]


@dataclass
class StabilityReport:
    """Selector stabilite raporu."""
    total_locators: int
    healthy: int       # score >= 4
    warning: int       # score 2-3
    critical: int      # score <= 1
    avg_score: float
    details: list[dict[str, Any]]       # per-locator scores with reasons
    improvements: list[dict[str, Any]]  # suggested improvements for weak locators


def _score_single_locator(locator: dict[str, Any]) -> dict[str, Any]:
    """Tek bir locator'in stabilite skorunu ve nedenlerini hesapla."""
    selector = locator.get("selector", "")
    loc_type = locator.get("type", "")
    element_name = locator.get("name", locator.get("element_name", ""))

    if not selector:
        return {
            "selector": selector,
            "name": element_name,
            "score": 0,
            "reasons": ["Bos selector"],
            "risk_factors": [],
        }

    score = 2  # default: orta
    reasons: list[str] = []
    risk_factors: list[str] = []

    # Positive scoring: match stability rules
    for pattern, rule_score, reason in _STABILITY_RULES:
        if pattern in selector:
            if rule_score > score:
                score = rule_score
                reasons.append(reason)
            break  # First match wins (rules ordered by priority)

    # Negative scoring: check for unstable patterns
    for pattern, risk_desc in _UNSTABLE_PATTERNS:
        if pattern.search(selector):
            risk_factors.append(risk_desc)
            score = max(0, score - 1)

    # Additional checks
    if len(selector) > 150:
        risk_factors.append("Cok uzun selector (>150 char) — kirilma riski yuksek")
        score = max(0, score - 1)

    # Dynamic id detection
    id_m = re.search(r"#([\w-]+)", selector)
    if id_m:
        id_val = id_m.group(1)
        if re.match(r"^[a-f0-9]{6,}$", id_val):
            risk_factors.append("Hex hash id — muhtemelen dynamic")
            score = max(0, score - 1)
        elif re.match(r"^\d+$", id_val):
            risk_factors.append("Numeric-only id — muhtemelen dynamic index")
            score = max(0, score - 1)

    score = max(0, min(5, score))

    if not reasons:
        if score >= 4:
            reasons.append("Iyi selector yapisi")
        elif score >= 2:
            reasons.append("Orta stabilite — iyilestirme onerilir")
        else:
            reasons.append("Dusuk stabilite — acil iyilestirme gerekli")

    return {
        "selector": selector,
        "name": element_name,
        "type": loc_type,
        "score": score,
        "reasons": reasons,
        "risk_factors": risk_factors,
    }


class LocatorIntelligence(BaseAgent):
    """
    Proaktif locator analizi ve POM uretimi ajani.

    Kullanim:
        intel = LocatorIntelligence()
        report = intel.analyze_stability(locators)
        pom = intel.generate_page_object("https://...", elements, "LoginPage")
    """

    name = "Locator Zekasi"
    temperature = 0.15
    max_tokens = 4096

    # ── 1. Stability Analysis ────────────────────────────────────────────────

    def analyze_stability(self, locators: list[dict[str, Any]]) -> StabilityReport:
        """
        Her locator'i 0-5 arasinda puanla, riskli olanlari belirle.

        Args:
            locators: [{"selector": "...", "name": "...", "type": "..."}]

        Returns:
            StabilityReport — toplam, saglam, uyari, kritik, ortalama, detay
        """
        details: list[dict[str, Any]] = []
        for loc in locators:
            detail = _score_single_locator(loc)
            details.append(detail)

        total = len(details)
        healthy = sum(1 for d in details if d["score"] >= 4)
        warning = sum(1 for d in details if 2 <= d["score"] <= 3)
        critical = sum(1 for d in details if d["score"] <= 1)
        avg = sum(d["score"] for d in details) / total if total else 0.0

        # Generate improvements for weak locators
        weak = [d for d in details if d["score"] <= 3]
        improvements = self._generate_quick_improvements(weak)

        return StabilityReport(
            total_locators=total,
            healthy=healthy,
            warning=warning,
            critical=critical,
            avg_score=round(avg, 2),
            details=details,
            improvements=improvements,
        )

    def _generate_quick_improvements(self, weak_locators: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Zayif locator'lar icin hizli iyilestirme onerileri (LLM gerektirmez)."""
        improvements: list[dict[str, Any]] = []

        for loc in weak_locators:
            selector = loc.get("selector", "")
            name = loc.get("name", "")
            score = loc.get("score", 0)
            suggestion: dict[str, Any] = {
                "original": selector,
                "name": name,
                "current_score": score,
                "suggested_selector": "",
                "suggested_score": 0,
                "action": "",
            }

            if score <= 1:
                # Critical: xpath or deeply nested — suggest adding data-testid
                suggestion["action"] = (
                    "Elemente data-testid attribute ekleyin: "
                    "data-testid=\"%s\"" % _generate_testid_suggestion(name, selector)
                )
                suggestion["suggested_selector"] = (
                    "page.getByTestId('%s')" % _generate_testid_suggestion(name, selector)
                )
                suggestion["suggested_score"] = 5
            elif score == 2:
                # Warning-low: text-based — suggest role or aria-label
                suggestion["action"] = (
                    "Elemente role + aria-label ekleyin veya data-testid kullanin"
                )
                suggestion["suggested_selector"] = (
                    "page.getByTestId('%s')" % _generate_testid_suggestion(name, selector)
                )
                suggestion["suggested_score"] = 5
            elif score == 3:
                # Warning-mid: placeholder/name — acceptable but improvable
                suggestion["action"] = (
                    "Mumkunse data-testid ekleyin; mevcut selector kabul edilebilir"
                )
                suggestion["suggested_selector"] = (
                    "page.getByTestId('%s')" % _generate_testid_suggestion(name, selector)
                )
                suggestion["suggested_score"] = 5

            improvements.append(suggestion)

        return improvements

    # ── 2. Suggest Improvements ──────────────────────────────────────────────

    def suggest_improvements(
        self, locators: list[dict[str, Any]], dom_snippet: str = "",
    ) -> list[dict[str, Any]]:
        """
        Zayif locator'lar icin daha iyi alternatifler oner.

        LLM-powered: DOM varsa DOM'a bakarak, yoksa kural bazli.

        Args:
            locators: [{"selector": "...", "name": "...", "type": "..."}]
            dom_snippet: DOM HTML (varsa, LLM daha isabetli onerir)

        Returns:
            [{"original": "...", "suggested": "...", "reason": "...", "confidence": 0.9}]
        """
        # First pass: quick rule-based for all
        report = self.analyze_stability(locators)
        weak = [d for d in report.details if d["score"] <= 3]

        if not weak:
            return []

        # If DOM available, use LLM for richer suggestions
        if dom_snippet and len(weak) <= 10:
            return self._llm_suggest_improvements(weak, dom_snippet)

        # Otherwise return rule-based suggestions
        return report.improvements

    def _llm_suggest_improvements(
        self, weak_locators: list[dict[str, Any]], dom_snippet: str,
    ) -> list[dict[str, Any]]:
        """LLM ile DOM'a bakarak daha iyi selector onerileri."""
        system = (
            "Sen bir Playwright test muhendisisin. Asagidaki zayif selector'lar icin "
            "DOM'a bakarak daha stabil alternatifler oner.\n\n"
            "Oncelik sirasi: data-testid > role > aria-label > id > name > placeholder > text\n\n"
            "JSON formatinda yanit ver:\n"
            '{"improvements": [{"original": "...", "suggested": "page.getByTestId(\'...\')", '
            '"reason": "...", "confidence": 0.95}]}'
        )
        user = "Zayif selector'lar:\n"
        for loc in weak_locators[:10]:
            user += "- %s (skor: %d)\n" % (loc.get("selector", ""), loc.get("score", 0))
        user += "\nDOM snippet:\n%s" % dom_snippet[:3000]

        try:
            result = self.call_json(system, user)
            return result.get("improvements", [])
        except Exception as exc:
            logger.debug("LLM suggest_improvements hatasi: %s", exc)
            # Fallback to rule-based
            return self._generate_quick_improvements(weak_locators)

    # ── 3. Learn from History ────────────────────────────────────────────────

    def learn_from_history(self, heal_history: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Gecmis heal kayitlarindan pattern ogren.

        Args:
            heal_history: [{"broken": "...", "healed": "...", "strategy": "...",
                           "confidence": 0.9, "timestamp": "..."}]

        Returns:
            {
                "total_heals": 42,
                "strategy_distribution": {"data-testid": 15, "role": 10, ...},
                "most_broken_type": "xpath",
                "avg_confidence": 0.85,
                "patterns": [{"pattern": "...", "frequency": 5, "fix": "..."}],
                "recommendations": ["..."]
            }
        """
        if not heal_history:
            return {
                "total_heals": 0,
                "strategy_distribution": {},
                "most_broken_type": "",
                "avg_confidence": 0.0,
                "patterns": [],
                "recommendations": ["Henuz heal gecmisi yok — veri biriktikce analiz yapilacak"],
            }

        total = len(heal_history)

        # Strategy distribution
        strategy_counts: dict[str, int] = {}
        for h in heal_history:
            s = h.get("strategy", "unknown")
            strategy_counts[s] = strategy_counts.get(s, 0) + 1

        # Broken selector type distribution
        broken_type_counts: dict[str, int] = {}
        for h in heal_history:
            broken = h.get("broken", "")
            btype = _classify_selector_type(broken)
            broken_type_counts[btype] = broken_type_counts.get(btype, 0) + 1

        most_broken = max(broken_type_counts, key=broken_type_counts.get) if broken_type_counts else ""

        # Average confidence
        confidences = [float(h.get("confidence", 0)) for h in heal_history if h.get("confidence")]
        avg_conf = sum(confidences) / len(confidences) if confidences else 0.0

        # Detect recurring patterns
        broken_selectors: list[str] = [h.get("broken", "") for h in heal_history]
        patterns = _detect_recurring_patterns(broken_selectors)

        # Generate recommendations
        recommendations: list[str] = []

        if broken_type_counts.get("xpath", 0) > total * 0.3:
            recommendations.append(
                "XPath selector'lari cok kiriliyor (%d/%d). "
                "data-testid veya role bazli selector'lara gecis onerilir." % (
                    broken_type_counts.get("xpath", 0), total,
                )
            )

        if broken_type_counts.get("css_class", 0) > total * 0.2:
            recommendations.append(
                "CSS class bazli selector'lar sik kiriliyor. "
                "Tailwind/CSS module hash'leri yerine data-testid kullanin."
            )

        if broken_type_counts.get("text", 0) > total * 0.25:
            recommendations.append(
                "Text bazli selector'lar kiriliyor — muhtemelen ceviri veya "
                "metin degisiklikleri. aria-label veya data-testid tercih edin."
            )

        if avg_conf < 0.70:
            recommendations.append(
                "Ortalama heal confidence dusuk (%.2f). "
                "LLM heal'lere guvenilirlik artirmak icin DOM snippet kalitesini artirin." % avg_conf
            )

        if not recommendations:
            recommendations.append(
                "Heal performansi iyi gorunuyor (ortalama confidence: %.2f)." % avg_conf
            )

        return {
            "total_heals": total,
            "strategy_distribution": strategy_counts,
            "broken_type_distribution": broken_type_counts,
            "most_broken_type": most_broken,
            "avg_confidence": round(avg_conf, 3),
            "patterns": patterns,
            "recommendations": recommendations,
        }

    # ── 4. POM Generator ─────────────────────────────────────────────────────

    def generate_page_object(
        self,
        page_url: str,
        elements: list[dict[str, Any]],
        page_name: str = "",
    ) -> str:
        """
        DOM element'lerinden TypeScript Page Object Model sinifi uret.

        Args:
            page_url: Sayfa URL'si
            elements: [{tag, id, data_testid, role, aria_label, name, type, placeholder, text}]
            page_name: POM sinif adi (bos ise URL'den turetilir)

        Returns:
            TypeScript POM sinif kodu
        """
        if not page_name:
            page_name = _url_to_class_name(page_url)

        system = (
            "Sen deneyimli bir Playwright test muhendisisin. "
            "Verilen sayfa element'lerinden TypeScript Page Object Model sinifi uret.\n\n"
            "Kurallar:\n"
            "1. Her element icin en stabil selector'i sec: "
            "data-testid > role > aria-label > id > name > placeholder > text\n"
            "2. Getter property'ler kullan (get xxx())\n"
            "3. Interaktif element'ler icin action method'lari ekle\n"
            "4. Playwright best practice'lerini takip et\n"
            "5. Turkce yorum ekle\n\n"
            "Ornek format:\n"
            "```typescript\n"
            "import { Page } from '@playwright/test';\n\n"
            "export class LoginPage {\n"
            "  constructor(private page: Page) {}\n\n"
            "  // Selectors\n"
            "  get emailInput() { return this.page.getByTestId('email-input'); }\n"
            "  get passwordInput() { return this.page.getByTestId('password-input'); }\n"
            "  get submitButton() { return this.page.getByRole('button', { name: 'Giris' }); }\n\n"
            "  // Actions\n"
            "  async login(email: string, password: string) {\n"
            "    await this.emailInput.fill(email);\n"
            "    await this.passwordInput.fill(password);\n"
            "    await this.submitButton.click();\n"
            "  }\n"
            "}\n"
            "```\n\n"
            "YALNIZCA TypeScript kodu dondur. JSON veya aciklama YAZMA."
        )

        # Prepare elements summary
        elem_lines: list[str] = []
        for i, elem in enumerate(elements[:50]):  # Cap at 50 elements
            parts: list[str] = []
            tag = elem.get("tag", "unknown")
            parts.append("tag=%s" % tag)
            for attr in ("data_testid", "role", "aria_label", "id", "name",
                         "type", "placeholder", "text"):
                val = elem.get(attr) or elem.get(attr.replace("_", "-"), "")
                if val:
                    parts.append("%s='%s'" % (attr, str(val)[:50]))
            elem_lines.append("%d. %s" % (i + 1, " | ".join(parts)))

        user = (
            "Sayfa: %s\n"
            "Sinif adi: %s\n"
            "URL: %s\n\n"
            "Element'ler:\n%s"
        ) % (page_name, page_name, page_url, "\n".join(elem_lines))

        try:
            raw = self.call(system, user, json_mode=False)
            # Extract TypeScript code from response
            return _extract_typescript_code(raw)
        except Exception as exc:
            logger.warning("POM generate hatasi: %s — fallback uretiliyor", exc)
            return self._fallback_generate_pom(page_name, page_url, elements)

    def _fallback_generate_pom(
        self, page_name: str, page_url: str, elements: list[dict[str, Any]],
    ) -> str:
        """LLM basarisiz olursa kural bazli POM uret."""
        lines: list[str] = [
            "import { Page } from '@playwright/test';",
            "",
            "export class %s {" % page_name,
            "  constructor(private page: Page) {}",
            "",
            "  // ── Selectors ──────────────────────────────────────",
        ]

        action_targets: list[tuple[str, str, str]] = []  # (property_name, selector, tag)

        for elem in elements[:30]:
            tag = elem.get("tag", "")
            prop_name = _element_to_property_name(elem)
            if not prop_name:
                continue

            selector = _best_selector_for_element(elem)
            lines.append("  get %s() { return this.page.%s; }" % (prop_name, selector))

            # Track interactive elements for action methods
            if tag in ("input", "textarea", "select", "button", "a"):
                action_targets.append((prop_name, selector, tag))

        # Generate action methods for interactive elements
        if action_targets:
            lines.append("")
            lines.append("  // ── Actions ───────────────────────────────────────")

            fill_targets = [(n, s, t) for n, s, t in action_targets if t in ("input", "textarea")]
            click_targets = [(n, s, t) for n, s, t in action_targets if t in ("button", "a")]

            # Fill method if there are input fields
            if fill_targets:
                for prop, _sel, _tag in fill_targets:
                    lines.append(
                        "  async fill%s(value: string) { await this.%s.fill(value); }" % (
                            prop[0].upper() + prop[1:], prop,
                        )
                    )

            # Click methods for buttons
            if click_targets:
                for prop, _sel, _tag in click_targets:
                    lines.append(
                        "  async click%s() { await this.%s.click(); }" % (
                            prop[0].upper() + prop[1:], prop,
                        )
                    )

        lines.append("}")
        return "\n".join(lines)

    # ── 5. Predict Breakage ──────────────────────────────────────────────────

    def predict_breakage(
        self,
        locators: list[dict[str, Any]],
        recent_changes: str = "",
    ) -> list[dict[str, Any]]:
        """
        Hangi locator'larin kirilma riski yuksek oldugunu tahmin et.

        Args:
            locators: [{"selector": "...", "name": "...", "type": "..."}]
            recent_changes: Son kod degisiklikleri (git diff ozeti)

        Returns:
            [{"selector": "...", "risk": "high|medium|low", "reason": "...",
              "probability": 0.8}]
        """
        predictions: list[dict[str, Any]] = []

        for loc in locators:
            pred = self._predict_single(loc, recent_changes)
            predictions.append(pred)

        # Sort by probability descending
        predictions.sort(key=lambda p: p.get("probability", 0), reverse=True)
        return predictions

    def _predict_single(
        self, locator: dict[str, Any], recent_changes: str,
    ) -> dict[str, Any]:
        """Tek bir locator icin kirilma tahmini."""
        detail = _score_single_locator(locator)
        selector = locator.get("selector", "")
        score = detail["score"]
        risk_factors = detail["risk_factors"]

        probability = 0.0
        risk = "low"
        reasons: list[str] = []

        # Score-based base probability
        if score <= 1:
            probability = 0.70
            risk = "high"
            reasons.append("Cok dusuk stabilite skoru (%d/5)" % score)
        elif score == 2:
            probability = 0.45
            risk = "medium"
            reasons.append("Dusuk stabilite skoru (%d/5)" % score)
        elif score == 3:
            probability = 0.25
            risk = "medium"
            reasons.append("Orta stabilite skoru (%d/5)" % score)
        else:
            probability = 0.10
            risk = "low"
            reasons.append("Iyi stabilite skoru (%d/5)" % score)

        # Risk factor adjustments
        for rf in risk_factors:
            probability = min(0.95, probability + 0.10)
            reasons.append(rf)

        # Recent changes adjustment
        if recent_changes:
            # Check if the selector or related elements are mentioned in changes
            selector_parts = re.findall(r"[\w-]{3,}", selector)
            for part in selector_parts:
                if part.lower() in recent_changes.lower():
                    probability = min(0.95, probability + 0.15)
                    reasons.append("Selector parcasi '%s' son degisikliklerde goruldu" % part)
                    if risk != "high":
                        risk = "high" if probability > 0.60 else "medium"
                    break

        # Final risk classification
        if probability >= 0.60:
            risk = "high"
        elif probability >= 0.30:
            risk = "medium"
        else:
            risk = "low"

        return {
            "selector": selector,
            "name": locator.get("name", ""),
            "risk": risk,
            "probability": round(probability, 3),
            "reasons": reasons,
            "current_score": score,
        }

    # ── BaseAgent.run() implementation ───────────────────────────────────────

    def run(self, context: dict[str, Any]) -> AgentResult:
        """
        Analiz pipeline'ini calistir.

        context keys:
          locators        — [{"selector": "...", "name": "...", "type": "..."}]
          dom_snippet     — DOM HTML (POM uretimi ve iyilestirme onerileri icin)
          page_url        — Sayfa URL'si (POM icin)
          page_name       — POM sinif adi
          heal_history    — Gecmis heal kayitlari
          recent_changes  — Son kod degisiklikleri
          actions         — Yapilacak islemler listesi: ["stability", "suggest", "learn", "pom", "predict"]
        """
        t0 = time.time()
        locators = context.get("locators", [])
        actions = context.get("actions", ["stability"])
        result_data: dict[str, Any] = {}

        try:
            if "stability" in actions and locators:
                report = self.analyze_stability(locators)
                result_data["stability"] = {
                    "total": report.total_locators,
                    "healthy": report.healthy,
                    "warning": report.warning,
                    "critical": report.critical,
                    "avg_score": report.avg_score,
                    "details": report.details,
                    "improvements": report.improvements,
                }

            if "suggest" in actions and locators:
                dom = context.get("dom_snippet", "")
                improvements = self.suggest_improvements(locators, dom)
                result_data["suggestions"] = improvements

            if "learn" in actions:
                history = context.get("heal_history", [])
                learning = self.learn_from_history(history)
                result_data["learning"] = learning

            if "pom" in actions:
                page_url = context.get("page_url", "")
                page_name = context.get("page_name", "")
                elements = context.get("elements", locators)
                pom_code = self.generate_page_object(page_url, elements, page_name)
                result_data["pom"] = pom_code

            if "predict" in actions and locators:
                changes = context.get("recent_changes", "")
                predictions = self.predict_breakage(locators, changes)
                result_data["predictions"] = predictions

            # Log insights to KnowledgeStore
            if "stability" in result_data:
                stability_info = result_data["stability"]
                if stability_info.get("critical", 0) > 0:
                    self.learn(
                        "Locator Intelligence: %d/%d kritik selector tespit edildi. "
                        "Ortalama skor: %.2f" % (
                            stability_info["critical"],
                            stability_info["total"],
                            stability_info["avg_score"],
                        ),
                        metadata={
                            "type": "locator_analysis",
                            "critical_count": stability_info["critical"],
                            "avg_score": stability_info["avg_score"],
                        },
                    )

            return AgentResult(
                agent_name=self.name,
                success=True,
                data=result_data,
                duration_ms=int((time.time() - t0) * 1000),
            )

        except Exception as exc:
            logger.error("%s hatasi: %s", self.name, exc)
            return AgentResult(
                agent_name=self.name,
                success=False,
                error=str(exc),
                data=result_data,
                duration_ms=int((time.time() - t0) * 1000),
            )


# ── Module-level helpers ─────────────────────────────────────────────────────

def _classify_selector_type(selector: str) -> str:
    """Selector'in tipini siniflandir."""
    if not selector:
        return "empty"
    if "data-testid" in selector or "getByTestId" in selector:
        return "data-testid"
    if "role=" in selector or "getByRole" in selector:
        return "role"
    if "aria-label" in selector or "getByLabel" in selector:
        return "aria-label"
    if "getByPlaceholder" in selector or "placeholder" in selector:
        return "placeholder"
    if "getByText" in selector or "text=" in selector:
        return "text"
    if selector.startswith("//") or "xpath=" in selector:
        return "xpath"
    if re.search(r"\.\w+", selector) and not selector.startswith("#"):
        return "css_class"
    if selector.startswith("#") or "id=" in selector:
        return "id"
    return "css_other"


def _detect_recurring_patterns(broken_selectors: list[str]) -> list[dict[str, Any]]:
    """Tekrar eden kirilma pattern'lerini tespit et."""
    # Group by type
    type_groups: dict[str, list[str]] = {}
    for sel in broken_selectors:
        stype = _classify_selector_type(sel)
        if stype not in type_groups:
            type_groups[stype] = []
        type_groups[stype].append(sel)

    patterns: list[dict[str, Any]] = []

    # Find common prefixes within each type
    for stype, selectors in type_groups.items():
        if len(selectors) < 2:
            continue

        # Look for common substring patterns
        common_parts: dict[str, int] = {}
        for sel in selectors:
            parts = re.findall(r"[\w-]{4,}", sel)
            for part in parts:
                common_parts[part] = common_parts.get(part, 0) + 1

        for part, count in common_parts.items():
            if count >= 2:
                patterns.append({
                    "pattern": part,
                    "type": stype,
                    "frequency": count,
                    "fix": "Bu pattern'i iceren selector'lari data-testid ile degistirin",
                })

    # Sort by frequency
    patterns.sort(key=lambda p: p["frequency"], reverse=True)
    return patterns[:20]


def _url_to_class_name(url: str) -> str:
    """URL'den PascalCase sinif adi uret."""
    if not url:
        return "UnknownPage"

    # Extract path part
    path = url.split("?")[0].split("#")[0]
    path = path.rstrip("/")

    # Take last segment
    segments = [s for s in path.split("/") if s and s not in ("http:", "https:", "")]
    if not segments:
        return "HomePage"

    last = segments[-1]
    # Remove file extensions
    last = re.sub(r"\.\w+$", "", last)
    # Convert to PascalCase
    parts = re.split(r"[-_\s]+", last)
    class_name = "".join(p.capitalize() for p in parts if p)

    if not class_name:
        return "UnknownPage"

    # Ensure it ends with Page
    if not class_name.endswith("Page"):
        class_name += "Page"

    return class_name


def _generate_testid_suggestion(name: str, selector: str) -> str:
    """Element adi veya selector'dan makul bir data-testid oner."""
    if name:
        # Sanitize name: lowercase, kebab-case
        testid = re.sub(r"[^a-zA-Z0-9]+", "-", name.lower()).strip("-")
        if testid:
            return testid

    # Extract from selector
    parts = re.findall(r"[a-zA-Z]{3,}", selector)
    filtered = [p.lower() for p in parts if p.lower() not in (
        "page", "get", "locator", "text", "xpath", "role", "button",
        "input", "div", "span", "css", "name",
    )]
    if filtered:
        return "-".join(filtered[:3])

    return "element"


def _element_to_property_name(elem: dict[str, Any]) -> str:
    """DOM element'inden camelCase property adi uret."""
    # Prefer data-testid
    testid = elem.get("data_testid") or elem.get("data-testid", "")
    if testid:
        return _to_camel_case(testid)

    # Then name
    name = elem.get("name", "")
    if name:
        return _to_camel_case(name)

    # Then aria-label
    label = elem.get("aria_label") or elem.get("aria-label", "")
    if label:
        return _to_camel_case(label)

    # Then id
    eid = elem.get("id", "")
    if eid:
        return _to_camel_case(eid)

    # Then text (short)
    text = elem.get("text", "")
    if text and len(text) < 30:
        return _to_camel_case(text)

    # Fallback
    tag = elem.get("tag", "element")
    etype = elem.get("type", "")
    if etype:
        return _to_camel_case("%s-%s" % (tag, etype))

    return ""


def _to_camel_case(text: str) -> str:
    """Metni camelCase'e donustur."""
    # Clean non-alphanumeric
    cleaned = re.sub(r"[^a-zA-Z0-9]+", " ", text).strip()
    if not cleaned:
        return ""
    parts = cleaned.split()
    if not parts:
        return ""
    # First word lowercase, rest capitalize
    result = parts[0].lower()
    for p in parts[1:]:
        result += p.capitalize()
    return result


def _best_selector_for_element(elem: dict[str, Any]) -> str:
    """Element icin en iyi Playwright selector'i sec."""
    testid = elem.get("data_testid") or elem.get("data-testid", "")
    if testid:
        return "getByTestId('%s')" % testid

    role = elem.get("role", "")
    label = elem.get("aria_label") or elem.get("aria-label", "")
    if role and label:
        return "getByRole('%s', { name: '%s' })" % (role, label)
    if role:
        return "getByRole('%s')" % role

    if label:
        return "getByLabel('%s')" % label

    eid = elem.get("id", "")
    if eid:
        return "locator('#%s')" % eid

    name = elem.get("name", "")
    tag = elem.get("tag", "*")
    if name:
        return "locator('%s[name=\"%s\"]')" % (tag, name)

    placeholder = elem.get("placeholder", "")
    if placeholder:
        return "getByPlaceholder('%s')" % placeholder

    text = elem.get("text", "")
    if text and len(text) < 50:
        return "getByText('%s')" % text.replace("'", "\\'")

    return "locator('%s')" % tag


def _extract_typescript_code(raw: str) -> str:
    """LLM yaniti icinden TypeScript kodunu cikar."""
    raw = raw.strip()

    # Try to extract from markdown code block
    code_block_m = re.search(
        r"```(?:typescript|ts)?\s*\n(.*?)```",
        raw, re.DOTALL,
    )
    if code_block_m:
        return code_block_m.group(1).strip()

    # If it looks like TypeScript already (starts with import or export)
    if raw.startswith("import ") or raw.startswith("export "):
        return raw

    # Return as-is
    return raw
