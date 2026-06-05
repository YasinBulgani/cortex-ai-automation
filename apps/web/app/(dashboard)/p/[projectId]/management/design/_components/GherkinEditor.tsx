"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { cn } from "@/lib/utils";

// ── Types ─────────────────────────────────────────────────────────────────────

export interface GherkinStep {
  step_no: number;
  action: string;
  expected_result: string;
  test_data?: Record<string, unknown>;
  notes?: null;
  is_required?: boolean;
}

// ── Keyword config ─────────────────────────────────────────────────────────────

const KEYWORDS = ["Feature", "Scenario", "Scenario Outline", "Background", "Given", "When", "Then", "And", "But", "Examples"] as const;
type GherkinKeyword = (typeof KEYWORDS)[number];

const KEYWORD_CLASS: Record<string, string> = {
  Feature:          "text-violet-400 font-semibold",
  Scenario:         "text-blue-400 font-semibold",
  "Scenario Outline": "text-blue-400 font-semibold",
  Background:       "text-teal-400 font-semibold",
  Given:            "text-emerald-400 font-medium",
  When:             "text-amber-400 font-medium",
  Then:             "text-sky-400 font-medium",
  And:              "text-emerald-300 font-medium",
  But:              "text-rose-400 font-medium",
  Examples:         "text-purple-400 font-medium",
};

// Keywords that trigger autocomplete on partial match
const AUTOCOMPLETE_TRIGGERS = ["G", "W", "T", "A", "B", "S", "F", "E"] as const;

function getAutocompleteSuggestions(word: string): GherkinKeyword[] {
  if (!word) return [];
  const upper = word.toUpperCase();
  return KEYWORDS.filter(k => k.toUpperCase().startsWith(upper)) as GherkinKeyword[];
}

// ── Syntax highlight (tokenise a line into spans) ────────────────────────────

function tokeniseLine(line: string): React.ReactNode {
  // Find if line starts with a keyword (with optional leading spaces)
  const trimmed = line.trimStart();
  const leadingSpaces = line.length - trimmed.length;
  const prefix = line.slice(0, leadingSpaces);

  for (const kw of KEYWORDS) {
    if (trimmed === kw || trimmed.startsWith(kw + ":") || trimmed.startsWith(kw + " ")) {
      const rest = trimmed.slice(kw.length);
      return (
        <>
          {prefix && <span>{prefix}</span>}
          <span className={KEYWORD_CLASS[kw] ?? ""}>{kw}</span>
          {rest && <span className="text-fg-muted">{rest}</span>}
        </>
      );
    }
  }

  // Comments
  if (trimmed.startsWith("#")) {
    return <span className="text-fg-disabled italic">{line}</span>;
  }

  // Table rows
  if (trimmed.startsWith("|")) {
    return <span className="text-cyan-300">{line}</span>;
  }

  // Tags
  if (trimmed.startsWith("@")) {
    return <span className="text-pink-400">{line}</span>;
  }

  return <span className="text-fg-muted">{line}</span>;
}

// ── Parse Gherkin → steps ─────────────────────────────────────────────────────

export interface GherkinScenario {
  name: string;
  steps: GherkinStep[];
}

/** Parse all scenarios in a feature file and return them individually. */
export function parseGherkinScenarios(gherkin: string): GherkinScenario[] {
  const lines = gherkin.split("\n");
  const scenarios: GherkinScenario[] = [];
  let current: GherkinScenario | null = null;
  let stepNo = 1;

  for (const rawLine of lines) {
    const line = rawLine.trim();

    // New scenario boundary
    const scenarioMatch = /^(?:Scenario(?: Outline)?|Örnek):\s*(.*)$/i.exec(line);
    if (scenarioMatch) {
      if (current) scenarios.push(current);
      stepNo = 1;
      current = { name: scenarioMatch[1]?.trim() ?? "Senaryo", steps: [] };
      continue;
    }

    if (!current) continue;

    // Given / When / And / But: action step
    const givenWhen = /^(Given|When|And|But|Diyelim|Eğer|Ve|Ama)\s+(.+)$/i.exec(line);
    if (givenWhen) {
      current.steps.push({
        step_no: stepNo++,
        action: givenWhen[2] ?? "",
        expected_result: "",
        is_required: true,
      });
      continue;
    }

    // Then: assertion step
    const then = /^(Then|O zaman|Sonra)\s+(.+)$/i.exec(line);
    if (then) {
      current.steps.push({
        step_no: stepNo++,
        action: "Doğrula",
        expected_result: then[2] ?? "",
        is_required: true,
      });
    }
  }

  if (current) scenarios.push(current);
  return scenarios;
}

/** Backward-compatible: returns flat steps from first scenario. */
export function parseGherkinToSteps(gherkin: string): GherkinStep[] {
  const scenarios = parseGherkinScenarios(gherkin);
  if (scenarios.length === 0) return [];
  // Re-number across all steps if single scenario, or just first
  const all = scenarios[0]?.steps ?? [];
  return all.map((s, i) => ({ ...s, step_no: i + 1 }));
}

// ── Highlighted overlay ───────────────────────────────────────────────────────

function HighlightedCode({ text }: { text: string }) {
  const lines = text.split("\n");
  return (
    <div className="pointer-events-none select-none">
      {lines.map((line, i) => (
        <div key={i} className="leading-[1.6rem] min-h-[1.6rem]">
          {tokeniseLine(line)}
        </div>
      ))}
    </div>
  );
}

// ── Main GherkinEditor ────────────────────────────────────────────────────────

interface GherkinEditorProps {
  value: string;
  onChange: (v: string) => void;
  onConvert?: (steps: GherkinStep[]) => void;
}

export function GherkinEditor({ value, onChange, onConvert }: GherkinEditorProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [suggestions, setSuggestions] = useState<GherkinKeyword[]>([]);
  const [suggIdx, setSuggIdx] = useState(0);

  // Figure out the current word being typed at cursor position
  function getCurrentWord(ta: HTMLTextAreaElement): string {
    const pos = ta.selectionStart;
    const textBefore = ta.value.slice(0, pos);
    const lineStart = textBefore.lastIndexOf("\n") + 1;
    const currentLine = textBefore.slice(lineStart);
    // Only suggest if we're at the start of a line (possibly with spaces)
    const m = /^\s*(\w+)$/.exec(currentLine);
    return m ? m[1] : "";
  }

  function handleChange(e: React.ChangeEvent<HTMLTextAreaElement>) {
    const val = e.target.value;
    onChange(val);
    const word = getCurrentWord(e.target);
    const suggs = word ? getAutocompleteSuggestions(word) : [];
    setSuggestions(suggs);
    setSuggIdx(0);
  }

  function applySuggestion(kw: GherkinKeyword) {
    const ta = textareaRef.current;
    if (!ta) return;
    const pos = ta.selectionStart;
    const textBefore = ta.value.slice(0, pos);
    const lineStart = textBefore.lastIndexOf("\n") + 1;
    const lineText = textBefore.slice(lineStart);
    const m = /^(\s*)(\w+)$/.exec(lineText);
    if (!m) return;
    const [, spaces, word] = m;
    const replaceStart = lineStart + spaces.length;
    const replaceEnd = pos;
    const suffix = ["Feature", "Scenario", "Scenario Outline", "Background", "Examples"].includes(kw) ? ": " : " ";
    const newVal = ta.value.slice(0, replaceStart) + kw + suffix + ta.value.slice(replaceEnd);
    onChange(newVal);
    setSuggestions([]);
    // Move cursor after the keyword
    const newCursor = replaceStart + kw.length + suffix.length;
    requestAnimationFrame(() => {
      ta.focus();
      ta.setSelectionRange(newCursor, newCursor);
    });
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (suggestions.length > 0) {
      if (e.key === "ArrowDown") { e.preventDefault(); setSuggIdx(i => (i + 1) % suggestions.length); return; }
      if (e.key === "ArrowUp")   { e.preventDefault(); setSuggIdx(i => (i - 1 + suggestions.length) % suggestions.length); return; }
      if (e.key === "Enter" || e.key === "Tab") {
        e.preventDefault();
        const chosen = suggestions[suggIdx];
        if (chosen) applySuggestion(chosen);
        return;
      }
      if (e.key === "Escape") { setSuggestions([]); return; }
    }

    // Tab → insert 2 spaces
    if (e.key === "Tab") {
      e.preventDefault();
      const ta = e.currentTarget;
      const start = ta.selectionStart;
      const end = ta.selectionEnd;
      const newVal = ta.value.slice(0, start) + "  " + ta.value.slice(end);
      onChange(newVal);
      requestAnimationFrame(() => { ta.setSelectionRange(start + 2, start + 2); });
    }
  }

  const lines = value.split("\n");
  const lineCount = Math.max(lines.length, 10);

  return (
    <div className="relative flex flex-col rounded-xl border border-border bg-surface-base text-[13px] font-mono shadow-sm">
      {/* Editor body */}
      <div className="flex min-h-[280px] overflow-auto">
        {/* Line numbers */}
        <div
          className="select-none border-r border-border bg-surface-raised px-3 py-3 text-right text-[11px] leading-[1.6rem] text-fg-disabled"
          aria-hidden
        >
          {Array.from({ length: lineCount }, (_, i) => (
            <div key={i}>{i + 1}</div>
          ))}
        </div>

        {/* Highlight overlay + textarea */}
        <div className="relative flex-1">
          {/* Highlighted text (absolute, behind textarea) */}
          <div className="absolute inset-0 overflow-hidden px-4 py-3 leading-[1.6rem]">
            <HighlightedCode text={value} />
          </div>

          {/* Transparent textarea on top */}
          <textarea
            ref={textareaRef}
            value={value}
            onChange={handleChange}
            onKeyDown={handleKeyDown}
            spellCheck={false}
            className="relative z-10 h-full min-h-[280px] w-full resize-none bg-transparent px-4 py-3 leading-[1.6rem] text-transparent caret-fg outline-none"
            style={{ caretColor: "var(--color-fg, #e2e8f0)" }}
            placeholder=""
          />
        </div>
      </div>

      {/* Autocomplete dropdown */}
      {suggestions.length > 0 && (
        <div className="absolute left-12 top-8 z-50 overflow-hidden rounded-lg border border-border bg-surface-raised shadow-elevated">
          {suggestions.map((kw, i) => (
            <button
              key={kw}
              type="button"
              onMouseDown={e => { e.preventDefault(); applySuggestion(kw); }}
              className={cn(
                "flex w-full items-center gap-2 px-3 py-1.5 text-left text-[12px] font-mono transition-colors",
                i === suggIdx ? "bg-brand-soft text-brand" : "text-fg-muted hover:bg-surface-overlay",
              )}
            >
              <span className={KEYWORD_CLASS[kw] ?? ""}>{kw}</span>
            </button>
          ))}
        </div>
      )}

      {/* Convert button */}
      {onConvert && (
        <div className="flex items-center justify-end border-t border-border px-4 py-2">
          <button
            type="button"
            onClick={() => onConvert(parseGherkinToSteps(value))}
            className="rounded-lg bg-brand px-4 py-1.5 text-[12px] font-semibold text-brand-fg shadow-sm transition-colors hover:brightness-105"
          >
            Senaryoya Dönüştür
          </button>
        </div>
      )}
    </div>
  );
}
