"""Gherkin Parser — text → GherkinFeature."""
from __future__ import annotations

import logging
import re
from typing import Optional

from ..schemas.scenario import GherkinFeature, GherkinScenario, GherkinStep

logger = logging.getLogger(__name__)


_STEP_KEYWORDS = {
    "Given": ("given", "verilen", "diyelim", "farzedelim"),
    "When": ("when", "eğer", "eger", "o anda"),
    "Then": ("then", "o zaman", "beklenir"),
    "And": ("and", "ve"),
    "But": ("but", "fakat", "ama"),
}

_STEP_KEYWORDS_LOOKUP: dict[str, str] = {}
for canonical, aliases in _STEP_KEYWORDS.items():
    for a in aliases:
        _STEP_KEYWORDS_LOOKUP[a] = canonical

_STEP_RE = re.compile(
    r"^\s*(?P<kw>"
    + "|".join(re.escape(k) for k in _STEP_KEYWORDS_LOOKUP.keys())
    + r")\s+(?P<text>.+?)\s*$",
    re.IGNORECASE,
)

_FEATURE_RE = re.compile(r"^\s*(Özellik|Feature)\s*:\s*(.+?)\s*$", re.IGNORECASE)
_SCENARIO_RE = re.compile(
    r"^\s*(Senaryo(?:\s*Taslağı)?|Scenario(?:\s*Outline)?)\s*:\s*(.+?)\s*$",
    re.IGNORECASE,
)
_BACKGROUND_RE = re.compile(r"^\s*(Artalan|Background)\s*:\s*$", re.IGNORECASE)
_EXAMPLES_RE = re.compile(r"^\s*(Örnekler|Examples)\s*:\s*$", re.IGNORECASE)
_LANG_RE = re.compile(r"^\s*#\s*language\s*:\s*([a-z]{2})", re.IGNORECASE)


def parse_gherkin_text(text: str) -> GherkinFeature | None:
    text = _strip_fence(text)
    lines = text.splitlines()

    language = "tr"
    feature_name: str | None = None
    feature_desc: list[str] = []
    feature_tags: list[str] = []
    pending_tags: list[str] = []

    scenarios: list[GherkinScenario] = []
    background: list[GherkinStep] | None = None

    current_scenario: GherkinScenario | None = None
    in_background = False
    in_examples = False
    example_headers: list[str] = []
    current_examples: list[dict] = []

    mode = "top"

    for raw in lines:
        line = raw.rstrip()
        if not line.strip():
            continue
        m = _LANG_RE.match(line)
        if m:
            language = m.group(1).lower()
            continue
        if line.lstrip().startswith("#"):
            continue

        stripped = line.strip()
        if stripped.startswith("@"):
            tags = [t for t in stripped.split() if t.startswith("@")]
            pending_tags.extend(t[1:] for t in tags)
            continue

        m = _FEATURE_RE.match(line)
        if m:
            feature_name = m.group(2).strip()
            feature_tags = pending_tags[:]
            pending_tags = []
            mode = "feature_desc"
            continue

        m = _SCENARIO_RE.match(line)
        if m:
            kw = m.group(1).lower()
            is_outline = "outline" in kw or "taslağı" in kw
            current_scenario = GherkinScenario(
                name=m.group(2).strip(),
                tags=pending_tags[:],
                is_outline=is_outline,
            )
            pending_tags = []
            scenarios.append(current_scenario)
            mode = "scenario"
            in_background = False
            in_examples = False
            continue

        if _BACKGROUND_RE.match(line):
            background = []
            in_background = True
            mode = "background"
            continue

        if _EXAMPLES_RE.match(line) and current_scenario:
            in_examples = True
            example_headers = []
            current_examples = []
            mode = "examples"
            continue

        m = _STEP_RE.match(line)
        if m:
            kw = _STEP_KEYWORDS_LOOKUP.get(m.group("kw").lower(), "Given")
            step = GherkinStep(keyword=kw, text=m.group("text").strip())  # type: ignore[arg-type]
            if in_background and background is not None:
                background.append(step)
            elif current_scenario:
                current_scenario.steps.append(step)
            continue

        if in_examples and current_scenario and line.strip().startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if not example_headers:
                example_headers = cells
            else:
                current_examples.append(dict(zip(example_headers, cells)))
                current_scenario.examples = current_examples
            continue

        if mode == "feature_desc":
            feature_desc.append(line.strip())

    if feature_name is None:
        return None

    return GherkinFeature(
        name=feature_name,
        description="\n".join(feature_desc).strip(),
        tags=feature_tags,
        background=background,
        scenarios=scenarios,
        language=language,
    )


def _strip_fence(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        lines = t.splitlines()
        lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        t = "\n".join(lines)
    return t
