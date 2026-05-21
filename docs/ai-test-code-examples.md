# AI Test Otomasyonu — Kod ve Konfigürasyon Örnekleri

**Tarih:** 2026-04-03
**Kapsam:** 13 AI test otomasyon yaklaşımı için TypeScript, Python ve Java dillerinde çalıştırılabilir örnekler

---

## İçindekiler

1. [AI Locator Chain (TypeScript)](#1-ai-locator-chain)
2. [Self-Healing Middleware (TypeScript)](#2-self-healing-middleware)
3. [Test Generator Service (Python)](#3-test-generator-service)
4. [BDD Senaryo Generator (Python)](#4-bdd-senaryo-generator)
5. [Test Prioritizer (Python)](#5-test-prioritizer)
6. [Anomaly Detector (Python)](#6-anomaly-detector)
7. [Flaky Test Detector (Python)](#7-flaky-test-detector)
8. [Coverage Gap Analyzer (Python)](#8-coverage-gap-analyzer)
9. [Assertion Öneri Engine (Python)](#9-assertion-oneri-engine)
10. [LLM Gateway (Python)](#10-llm-gateway)
11. [Sentetik Veri Generator (Python)](#11-sentetik-veri-generator)
12. [Security Scanner Entegrasyonu (Python)](#12-security-scanner)
13. [CI/CD Workflow Konfigürasyonu (YAML)](#13-cicd-workflow)
14. [Playwright MCP Konfigürasyonu (TypeScript)](#14-playwright-mcp)
15. [Java Legacy Refactoring Helper (Java)](#15-java-refactoring)

---

## 1. AI Locator Chain

AI destekli locator fallback chain — `data-testid` öncelikli, AI fallback'li.

```typescript
// e2e/utils/ai-locator.ts
import { type Page, type Locator } from "@playwright/test";

interface LocatorResult {
  locator: Locator;
  strategy: "testId" | "role" | "label" | "text" | "ai-generated" | "css";
  confidence: number;
}

interface LocatorHistoryEntry {
  elementIntent: string;
  strategy: string;
  selector: string;
  timestamp: number;
  success: boolean;
}

const locatorHistory: Map<string, LocatorHistoryEntry[]> = new Map();

export async function findElement(
  page: Page,
  intent: string,
  options?: { role?: string; fallbackCss?: string }
): Promise<LocatorResult> {
  // Strategy 1: data-testid (en güvenilir)
  const byTestId = page.getByTestId(intent);
  if ((await byTestId.count()) > 0) {
    recordSuccess(intent, "testId", `[data-testid="${intent}"]`);
    return { locator: byTestId, strategy: "testId", confidence: 1.0 };
  }

  // Strategy 2: ARIA role
  if (options?.role) {
    const byRole = page.getByRole(options.role as any, { name: intent });
    if ((await byRole.count()) > 0) {
      recordSuccess(intent, "role", `role=${options.role}[name="${intent}"]`);
      return { locator: byRole, strategy: "role", confidence: 0.9 };
    }
  }

  // Strategy 3: Label
  const byLabel = page.getByLabel(intent);
  if ((await byLabel.count()) > 0) {
    recordSuccess(intent, "label", `label="${intent}"`);
    return { locator: byLabel, strategy: "label", confidence: 0.85 };
  }

  // Strategy 4: Text content
  const byText = page.getByText(intent, { exact: false });
  if ((await byText.count()) === 1) {
    recordSuccess(intent, "text", `text="${intent}"`);
    return { locator: byText, strategy: "text", confidence: 0.7 };
  }

  // Strategy 5: AI fallback — accessibility snapshot + LLM
  try {
    const snapshot = await page.accessibility.snapshot();
    if (snapshot) {
      const aiLocator = await llmFindElement(snapshot, intent);
      const byAi = page.locator(aiLocator);
      if ((await byAi.count()) > 0) {
        recordSuccess(intent, "ai-generated", aiLocator);
        return { locator: byAi, strategy: "ai-generated", confidence: 0.6 };
      }
    }
  } catch {
    // AI fallback başarısız, CSS'e geç
  }

  // Strategy 6: CSS fallback
  if (options?.fallbackCss) {
    const byCss = page.locator(options.fallbackCss);
    recordSuccess(intent, "css", options.fallbackCss);
    return { locator: byCss, strategy: "css", confidence: 0.4 };
  }

  throw new Error(`Element bulunamadı: "${intent}" — tüm stratejiler başarısız`);
}

async function llmFindElement(
  snapshot: any,
  intent: string
): Promise<string> {
  const response = await fetch(`${process.env.ENGINE_BASE}/api/ai/find-element`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      accessibility_tree: JSON.stringify(snapshot),
      element_intent: intent,
    }),
  });
  const data = await response.json();
  return data.locator;
}

function recordSuccess(intent: string, strategy: string, selector: string) {
  const history = locatorHistory.get(intent) || [];
  history.push({ elementIntent: intent, strategy, selector, timestamp: Date.now(), success: true });
  locatorHistory.set(intent, history.slice(-10));
}
```

---

## 2. Self-Healing Middleware

Playwright test hook'u olarak çalışan self-healing mekanizması.

```typescript
// e2e/utils/self-healer.ts
import { type Page, type TestInfo } from "@playwright/test";
import * as fs from "fs";
import * as path from "path";

interface HealingResult {
  healed: boolean;
  oldLocator: string;
  newLocator: string;
  strategy: string;
  summary: string;
}

interface HealingLog {
  testTitle: string;
  timestamp: string;
  result: HealingResult;
  domSnapshotPath: string;
}

const HEALING_LOG_PATH = "reports/healing-log.json";

export async function attemptHealing(
  page: Page,
  testInfo: TestInfo
): Promise<HealingResult> {
  const error = testInfo.error;
  if (!error?.message) {
    return { healed: false, oldLocator: "", newLocator: "", strategy: "none", summary: "No error" };
  }

  const locatorMatch = error.message.match(/locator\('([^']+)'\)|getByTestId\('([^']+)'\)/);
  if (!locatorMatch) {
    return { healed: false, oldLocator: "", newLocator: "", strategy: "none", summary: "Locator hatası değil" };
  }

  const oldLocator = locatorMatch[1] || locatorMatch[2];

  // DOM snapshot al
  const snapshot = await page.accessibility.snapshot();
  const snapshotPath = path.join("reports", "dom-snapshots", `${testInfo.testId}.json`);
  fs.mkdirSync(path.dirname(snapshotPath), { recursive: true });
  fs.writeFileSync(snapshotPath, JSON.stringify(snapshot, null, 2));

  // Engine self-heal endpoint'ini çağır
  try {
    const response = await fetch(`${process.env.ENGINE_BASE || "http://127.0.0.1:5001"}/api/ai/self-heal`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        failed_locator: oldLocator,
        accessibility_tree: JSON.stringify(snapshot),
        error_message: error.message,
        page_url: page.url(),
      }),
    });

    if (!response.ok) {
      return { healed: false, oldLocator, newLocator: "", strategy: "api-error", summary: "Healing API hatası" };
    }

    const data = await response.json();
    const newLocator = data.new_locator;

    // Yeni locator ile element var mı kontrol et
    const element = page.locator(newLocator);
    if ((await element.count()) > 0) {
      const result: HealingResult = {
        healed: true,
        oldLocator,
        newLocator,
        strategy: data.strategy,
        summary: `${oldLocator} → ${newLocator} (${data.strategy})`,
      };

      logHealing(testInfo.title, result, snapshotPath);
      return result;
    }
  } catch {
    // Healing başarısız
  }

  return { healed: false, oldLocator, newLocator: "", strategy: "failed", summary: "Healing başarısız" };
}

function logHealing(testTitle: string, result: HealingResult, snapshotPath: string) {
  const log: HealingLog = {
    testTitle,
    timestamp: new Date().toISOString(),
    result,
    domSnapshotPath: snapshotPath,
  };

  let logs: HealingLog[] = [];
  if (fs.existsSync(HEALING_LOG_PATH)) {
    logs = JSON.parse(fs.readFileSync(HEALING_LOG_PATH, "utf-8"));
  }
  logs.push(log);
  fs.writeFileSync(HEALING_LOG_PATH, JSON.stringify(logs, null, 2));
}

export function setupSelfHealing() {
  return {
    afterEach: async ({ page }: { page: Page }, testInfo: TestInfo) => {
      if (testInfo.status === "failed") {
        const result = await attemptHealing(page, testInfo);
        if (result.healed) {
          testInfo.annotations.push({
            type: "healed",
            description: result.summary,
          });
        }
      }
    },
  };
}
```

---

## 3. Test Generator Service

Doğal dil gereksinimden test kodu üreten Python servisi.

```python
# engine/services/ai_test_generator.py
from dataclasses import dataclass
from pathlib import Path
import json
import ast
import subprocess

from openai import AsyncOpenAI


@dataclass
class GeneratedTest:
    framework: str          # "playwright-ts" | "pytest-bdd" | "pytest"
    code: str
    file_path: str
    validation_passed: bool
    validation_errors: list[str]


SYSTEM_PROMPT = """Sen BGTS Test Platformu için test kodu üreten bir AI asistanısın.

Kurallar:
1. data-testid locator'ları kullan (pattern: {screen}-{element-type}-{identifier})
2. BasePage'den türeyen page object'lere referans ver
3. Türkçe senaryo isimleri kullan
4. Her test tek bir kullanıcı akışını doğrulasın
5. Assertion'lar page object metotları içinde olsun
6. Hardcoded değer kullanma — test data fixture'larından al

Mevcut page object'ler:
- LoginPage: login-page, login-input-email, login-input-password, login-btn-submit
- ProjectsPage: projects-page, projects-btn-new, projects-table
- ScenariosListPage: scenarios-page, scenarios-btn-new, scenarios-table
- ApprovalsPage: approvals-page, approvals-table
- ExecutionsPage: executions-page, executions-table
"""


class AITestGenerator:
    def __init__(self, openai_api_key: str, model: str = "gpt-4o"):
        self.client = AsyncOpenAI(api_key=openai_api_key)
        self.model = model

    async def generate_from_requirement(
        self,
        requirement: str,
        framework: str = "pytest-bdd",
        page_objects: list[str] | None = None,
    ) -> GeneratedTest:
        """Doğal dil gereksinimden test kodu üretir."""
        context = self._build_context(framework, page_objects)

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"{context}\n\nGereksinim: {requirement}"},
            ],
            temperature=0.2,
        )

        raw_code = response.choices[0].message.content
        code = self._extract_code_block(raw_code)
        file_path = self._determine_file_path(requirement, framework)

        validation_errors = self._validate_code(code, framework)

        return GeneratedTest(
            framework=framework,
            code=code,
            file_path=file_path,
            validation_passed=len(validation_errors) == 0,
            validation_errors=validation_errors,
        )

    def _build_context(self, framework: str, page_objects: list[str] | None) -> str:
        parts = [f"Framework: {framework}"]
        if page_objects:
            parts.append(f"Kullanılacak Page Object'ler: {', '.join(page_objects)}")
        if framework == "pytest-bdd":
            parts.append("Çıktı: Gherkin feature dosyası + Python step definitions")
        elif framework == "playwright-ts":
            parts.append("Çıktı: TypeScript Playwright spec dosyası")
        return "\n".join(parts)

    def _extract_code_block(self, raw: str) -> str:
        """Markdown code block'larını çıkarır."""
        lines = raw.split("\n")
        in_block = False
        code_lines = []
        for line in lines:
            if line.startswith("```") and not in_block:
                in_block = True
                continue
            elif line.startswith("```") and in_block:
                in_block = False
                code_lines.append("\n---\n")
                continue
            if in_block:
                code_lines.append(line)
        return "\n".join(code_lines) if code_lines else raw

    def _determine_file_path(self, requirement: str, framework: str) -> str:
        slug = requirement[:50].lower().replace(" ", "_").replace("/", "_")
        if framework == "pytest-bdd":
            return f"engine/features/ai_generated/{slug}.feature"
        elif framework == "playwright-ts":
            return f"e2e/ai-generated/{slug}.spec.ts"
        return f"engine/tests/ai_generated/test_{slug}.py"

    def _validate_code(self, code: str, framework: str) -> list[str]:
        errors = []
        if framework in ("pytest-bdd", "pytest"):
            for block in code.split("---"):
                block = block.strip()
                if not block or block.startswith("Feature:"):
                    continue
                try:
                    ast.parse(block)
                except SyntaxError as e:
                    errors.append(f"Python syntax error: {e}")
        return errors


# Flask route entegrasyonu
def register_routes(app, generator: AITestGenerator):
    from flask import request, jsonify

    @app.route("/api/ai/generate-test", methods=["POST"])
    async def generate_test():
        data = request.get_json()
        result = await generator.generate_from_requirement(
            requirement=data["requirement"],
            framework=data.get("framework", "pytest-bdd"),
            page_objects=data.get("page_objects"),
        )
        return jsonify({
            "framework": result.framework,
            "code": result.code,
            "file_path": result.file_path,
            "validation_passed": result.validation_passed,
            "validation_errors": result.validation_errors,
        })
```

---

## 4. BDD Senaryo Generator

Gereksinimlerden Gherkin feature dosyaları ve step definition'lar üreten servis.

```python
# engine/services/bdd_generator.py
from dataclasses import dataclass
from pathlib import Path
import json
import re

from openai import AsyncOpenAI


@dataclass
class BDDOutput:
    feature_content: str
    step_definitions: str
    matched_existing_steps: list[str]
    new_steps_needed: list[str]


BDD_SYSTEM_PROMPT = """Sen bankacılık test senaryoları için BDD Gherkin feature dosyaları üreten bir uzmansın.

Kurallar:
1. Gherkin formatı: Feature / Scenario / Given / When / Then
2. Türkçe senaryo başlıkları kullan
3. Her senaryo tek bir iş akışını test etsin
4. Edge case ve negatif senaryolar ekle
5. data-testid convention'ına uygun locator referansları kullan
6. Step'ler mümkün olduğunca mevcut step kütüphanesinden eşleştirilsin

Mevcut step kütüphanesi:
- Given kullanıcı "{url}" sayfasında
- Given kullanıcı giriş yapmış
- When "{field}" alanına "{value}" yazar
- When "{button}" butonuna tıklar
- Then "{element}" görünür olmalı
- Then sayfa "{url}" adresine yönlenmeli
- Then hata mesajı "{message}" görünmeli
- Then tablo en az {count} satır içermeli
"""


class BDDGenerator:
    def __init__(self, openai_api_key: str, model: str = "gpt-4o"):
        self.client = AsyncOpenAI(api_key=openai_api_key)
        self.model = model
        self.existing_steps = self._load_existing_steps()

    def _load_existing_steps(self) -> list[str]:
        """Mevcut step definition'ları tarar."""
        steps = []
        steps_dir = Path("engine/steps")
        if steps_dir.exists():
            for py_file in steps_dir.glob("*.py"):
                content = py_file.read_text()
                patterns = re.findall(
                    r'@(?:given|when|then)\(["\'](.+?)["\']\)', content
                )
                steps.extend(patterns)
        return steps

    async def generate(self, requirement: str) -> BDDOutput:
        """Gereksinimden BDD feature + step definition üretir."""
        steps_context = "\n".join(f"  - {s}" for s in self.existing_steps)

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": BDD_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"Mevcut step'ler:\n{steps_context}\n\n"
                        f"Gereksinim: {requirement}\n\n"
                        "İki bölüm üret:\n"
                        "1. FEATURE: Gherkin feature dosyası\n"
                        "2. STEPS: Eksik step definition'lar (Python pytest-bdd)"
                    ),
                },
            ],
            temperature=0.2,
        )

        raw = response.choices[0].message.content
        feature_content, step_definitions = self._parse_output(raw)
        matched, new_needed = self._analyze_step_coverage(feature_content)

        return BDDOutput(
            feature_content=feature_content,
            step_definitions=step_definitions,
            matched_existing_steps=matched,
            new_steps_needed=new_needed,
        )

    def _parse_output(self, raw: str) -> tuple[str, str]:
        """LLM çıktısını feature ve step bölümlerine ayırır."""
        feature_match = re.search(
            r"(?:FEATURE|```gherkin)(.*?)(?:STEPS|```)", raw, re.DOTALL
        )
        steps_match = re.search(r"(?:STEPS|```python)(.*?)(?:```|$)", raw, re.DOTALL)

        feature = feature_match.group(1).strip() if feature_match else raw
        steps = steps_match.group(1).strip() if steps_match else ""
        return feature, steps

    def _analyze_step_coverage(self, feature: str) -> tuple[list[str], list[str]]:
        """Feature'daki step'lerin mevcut kütüphane ile eşleşmesini analiz eder."""
        feature_steps = re.findall(
            r"(?:Given|When|Then|And|But)\s+(.+)", feature
        )
        matched = []
        new_needed = []

        for step in feature_steps:
            if any(self._step_matches(step, existing) for existing in self.existing_steps):
                matched.append(step)
            else:
                new_needed.append(step)

        return matched, new_needed

    def _step_matches(self, feature_step: str, existing_pattern: str) -> bool:
        regex_pattern = re.sub(r'\{[^}]+\}', '.+', existing_pattern)
        return bool(re.match(regex_pattern, feature_step.strip()))
```

---

## 5. Test Prioritizer

Git diff ve test geçmişine dayalı akıllı test önceliklendirme.

```python
# engine/services/test_prioritizer.py
from dataclasses import dataclass, field
import subprocess
import json
from pathlib import Path


@dataclass
class ScoredTest:
    test_id: str
    file_path: str
    risk_score: float
    factors: dict = field(default_factory=dict)


@dataclass
class PrioritizationResult:
    total_tests: int
    selected_tests: list[ScoredTest]
    skipped_tests: list[ScoredTest]
    estimated_time_saved_seconds: int


class TestPrioritizer:
    def __init__(
        self,
        test_history_path: str = "reports/test-history.json",
        dependency_map_path: str = "reports/test-dependency-map.json",
    ):
        self.test_history = self._load_json(test_history_path)
        self.dependency_map = self._load_json(dependency_map_path)

    def prioritize(
        self,
        git_diff: str | None = None,
        time_budget_seconds: int = 300,
        min_score_threshold: float = 0.1,
    ) -> PrioritizationResult:
        """Kod değişikliklerine göre testleri önceliklendirir."""
        if git_diff is None:
            git_diff = self._get_git_diff()

        changed_files = self._parse_git_diff(git_diff)
        all_tests = self._get_all_tests()

        scored: list[ScoredTest] = []
        for test in all_tests:
            score, factors = self._calculate_risk_score(test, changed_files)
            scored.append(ScoredTest(
                test_id=test["id"],
                file_path=test["file"],
                risk_score=score,
                factors=factors,
            ))

        scored.sort(key=lambda t: t.risk_score, reverse=True)

        selected = []
        skipped = []
        accumulated_time = 0

        for test in scored:
            test_time = self._estimate_test_time(test.test_id)
            if test.risk_score >= min_score_threshold and accumulated_time + test_time <= time_budget_seconds:
                selected.append(test)
                accumulated_time += test_time
            else:
                skipped.append(test)

        return PrioritizationResult(
            total_tests=len(all_tests),
            selected_tests=selected,
            skipped_tests=skipped,
            estimated_time_saved_seconds=sum(
                self._estimate_test_time(t.test_id) for t in skipped
            ),
        )

    def _calculate_risk_score(
        self, test: dict, changed_files: list[str]
    ) -> tuple[float, dict]:
        factors = {}

        # Dosya bağımlılığı skoru (0-1)
        deps = self.dependency_map.get(test["id"], [])
        dep_overlap = len(set(deps) & set(changed_files))
        factors["dependency"] = min(dep_overlap / max(len(deps), 1), 1.0)

        # Geçmiş başarısızlık oranı (0-1)
        history = self.test_history.get(test["id"], [])
        if history:
            failures = sum(1 for h in history[-20:] if h["status"] == "failed")
            factors["failure_rate"] = failures / min(len(history), 20)
        else:
            factors["failure_rate"] = 0.5  # bilinmeyen → orta risk

        # Son değişiklik yakınlığı (0-1)
        if history:
            last_change = history[-1].get("code_changed_days_ago", 30)
            factors["recency"] = max(0, 1 - (last_change / 30))
        else:
            factors["recency"] = 0.5

        # Öncelik ağırlıkları
        weights = {"dependency": 0.4, "failure_rate": 0.35, "recency": 0.25}
        score = sum(factors[k] * weights[k] for k in weights)
        return score, factors

    def _get_git_diff(self) -> str:
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD~1"],
            capture_output=True, text=True,
        )
        return result.stdout

    def _parse_git_diff(self, diff: str) -> list[str]:
        return [line.strip() for line in diff.strip().split("\n") if line.strip()]

    def _get_all_tests(self) -> list[dict]:
        tests = []
        for spec in Path("e2e").glob("*.spec.ts"):
            tests.append({"id": spec.stem, "file": str(spec), "type": "e2e"})
        for test_file in Path("engine/tests").rglob("test_*.py"):
            tests.append({"id": test_file.stem, "file": str(test_file), "type": "engine"})
        return tests

    def _estimate_test_time(self, test_id: str) -> int:
        history = self.test_history.get(test_id, [])
        if history:
            durations = [h.get("duration_seconds", 30) for h in history[-5:]]
            return int(sum(durations) / len(durations))
        return 30  # varsayılan 30 saniye

    def _load_json(self, path: str) -> dict:
        p = Path(path)
        if p.exists():
            return json.loads(p.read_text())
        return {}
```

---

## 6. Anomaly Detector

Test sonuçları ve performans metriklerinde anomaly tespiti.

```python
# engine/services/anomaly_detector.py
from dataclasses import dataclass
import statistics
import json
from pathlib import Path
from datetime import datetime


@dataclass
class Anomaly:
    metric_name: str
    current_value: float
    expected_range: tuple[float, float]
    z_score: float
    severity: str  # "warning" | "critical"
    description: str


class AnomalyDetector:
    def __init__(
        self,
        history_path: str = "reports/metrics-history.json",
        z_threshold_warning: float = 2.0,
        z_threshold_critical: float = 3.0,
    ):
        self.history = self._load_history(history_path)
        self.z_warning = z_threshold_warning
        self.z_critical = z_threshold_critical

    def analyze_test_run(self, run_results: dict) -> list[Anomaly]:
        """Test çalışma sonuçlarını analiz eder ve anomaly'leri tespit eder."""
        anomalies = []

        metrics = {
            "total_duration_seconds": run_results.get("total_duration"),
            "failure_rate": run_results.get("failed", 0) / max(run_results.get("total", 1), 1),
            "avg_test_duration": run_results.get("avg_duration"),
            "flaky_count": run_results.get("flaky_count", 0),
        }

        for metric_name, current_value in metrics.items():
            if current_value is None:
                continue
            historical = self._get_metric_history(metric_name)
            if len(historical) < 5:
                continue  # yeterli veri yok

            anomaly = self._detect_anomaly(metric_name, current_value, historical)
            if anomaly:
                anomalies.append(anomaly)

        self._update_history(metrics)
        return anomalies

    def analyze_k6_results(self, k6_summary: dict) -> list[Anomaly]:
        """k6 performans test sonuçlarını analiz eder."""
        anomalies = []

        perf_metrics = {}
        if "metrics" in k6_summary:
            m = k6_summary["metrics"]
            if "http_req_duration" in m:
                perf_metrics["p95_response_ms"] = m["http_req_duration"]["values"].get("p(95)")
                perf_metrics["avg_response_ms"] = m["http_req_duration"]["values"].get("avg")
            if "http_req_failed" in m:
                perf_metrics["error_rate"] = m["http_req_failed"]["values"].get("rate", 0)

        for name, value in perf_metrics.items():
            if value is None:
                continue
            historical = self._get_metric_history(f"k6_{name}")
            if len(historical) >= 5:
                anomaly = self._detect_anomaly(f"k6_{name}", value, historical)
                if anomaly:
                    anomalies.append(anomaly)

        return anomalies

    def _detect_anomaly(
        self, name: str, current: float, historical: list[float]
    ) -> Anomaly | None:
        mean = statistics.mean(historical)
        stdev = statistics.stdev(historical) if len(historical) > 1 else 0

        if stdev == 0:
            return None

        z_score = (current - mean) / stdev

        if abs(z_score) >= self.z_critical:
            severity = "critical"
        elif abs(z_score) >= self.z_warning:
            severity = "warning"
        else:
            return None

        return Anomaly(
            metric_name=name,
            current_value=current,
            expected_range=(mean - 2 * stdev, mean + 2 * stdev),
            z_score=round(z_score, 2),
            severity=severity,
            description=f"{name}: {current:.2f} (beklenen: {mean:.2f} ± {2*stdev:.2f}, z={z_score:.2f})",
        )

    def _get_metric_history(self, metric_name: str) -> list[float]:
        return [
            entry[metric_name]
            for entry in self.history
            if metric_name in entry
        ][-30:]

    def _update_history(self, metrics: dict):
        entry = {"timestamp": datetime.now().isoformat(), **metrics}
        self.history.append(entry)

    def _load_history(self, path: str) -> list[dict]:
        p = Path(path)
        if p.exists():
            return json.loads(p.read_text())
        return []
```

---

## 7. Flaky Test Detector

Test geçmişinden flaky testleri tespit eden ve karantinaya alan servis.

```python
# engine/services/flaky_detector.py
from dataclasses import dataclass
import json
from pathlib import Path


@dataclass
class FlakyTestInfo:
    test_id: str
    flaky_score: float        # 0 (stabil) — 1 (tamamen rastgele)
    total_runs: int
    pass_count: int
    fail_count: int
    flip_count: int           # ardışık durum değişikliği sayısı
    recommendation: str       # "stable" | "monitor" | "quarantine" | "fix"
    last_failure_reason: str


class FlakyDetector:
    QUARANTINE_THRESHOLD = 0.3
    MONITOR_THRESHOLD = 0.1

    def __init__(self, history_path: str = "reports/test-history.json"):
        self.history = self._load_json(history_path)

    def analyze_all(self, window: int = 20) -> list[FlakyTestInfo]:
        """Tüm testleri flaky açısından analiz eder."""
        results = []
        for test_id, runs in self.history.items():
            recent = runs[-window:]
            if len(recent) < 5:
                continue
            info = self._analyze_test(test_id, recent)
            results.append(info)

        results.sort(key=lambda t: t.flaky_score, reverse=True)
        return results

    def get_quarantine_list(self) -> list[str]:
        """Karantinaya alınması gereken test ID'lerini döndürür."""
        all_tests = self.analyze_all()
        return [t.test_id for t in all_tests if t.recommendation == "quarantine"]

    def generate_pytest_deselect_args(self) -> list[str]:
        """pytest --deselect argümanlarını üretir."""
        quarantined = self.get_quarantine_list()
        return [f"--deselect={tid}" for tid in quarantined]

    def _analyze_test(self, test_id: str, runs: list[dict]) -> FlakyTestInfo:
        statuses = [r["status"] for r in runs]
        pass_count = statuses.count("passed")
        fail_count = statuses.count("failed")
        total = len(statuses)

        # Flip count: ardışık pass/fail değişikliği
        flip_count = sum(
            1 for i in range(1, len(statuses)) if statuses[i] != statuses[i - 1]
        )

        # Flaky skoru: flip oranı * failure oranı ağırlıklı
        flip_ratio = flip_count / max(total - 1, 1)
        failure_ratio = fail_count / total
        flaky_score = 0.6 * flip_ratio + 0.4 * failure_ratio

        if flaky_score >= self.QUARANTINE_THRESHOLD:
            recommendation = "quarantine"
        elif flaky_score >= self.MONITOR_THRESHOLD:
            recommendation = "monitor"
        elif fail_count == 0:
            recommendation = "stable"
        else:
            recommendation = "fix"

        last_failure = next(
            (r.get("error", "Bilinmeyen") for r in reversed(runs) if r["status"] == "failed"),
            "Yok",
        )

        return FlakyTestInfo(
            test_id=test_id,
            flaky_score=round(flaky_score, 3),
            total_runs=total,
            pass_count=pass_count,
            fail_count=fail_count,
            flip_count=flip_count,
            recommendation=recommendation,
            last_failure_reason=last_failure,
        )

    def _load_json(self, path: str) -> dict:
        p = Path(path)
        if p.exists():
            return json.loads(p.read_text())
        return {}
```

---

## 8. Coverage Gap Analyzer

Coverage raporunu analiz edip test önerileri üreten servis.

```python
# engine/services/coverage_analyzer.py
from dataclasses import dataclass
from pathlib import Path
import json
import re

from openai import AsyncOpenAI


@dataclass
class CoverageGap:
    file_path: str
    uncovered_lines: list[int]
    line_coverage_pct: float
    priority: str           # "critical" | "high" | "medium" | "low"
    suggested_test: str     # AI tarafından üretilen test kodu/açıklaması


class CoverageAnalyzer:
    CRITICAL_THRESHOLD = 50.0
    HIGH_THRESHOLD = 70.0
    MEDIUM_THRESHOLD = 85.0

    def __init__(self, openai_api_key: str, model: str = "gpt-4o"):
        self.llm = AsyncOpenAI(api_key=openai_api_key)
        self.model = model

    async def analyze(
        self,
        coverage_json_path: str = "reports/coverage.json",
        generate_suggestions: bool = True,
    ) -> list[CoverageGap]:
        """Coverage raporunu analiz eder ve gap'leri önceliklendirir."""
        coverage_data = self._load_coverage(coverage_json_path)
        gaps = []

        for file_path, data in coverage_data.items():
            if self._should_skip(file_path):
                continue

            uncovered = data.get("uncovered_lines", [])
            total = data.get("total_lines", 1)
            covered = data.get("covered_lines", 0)
            pct = (covered / total) * 100 if total > 0 else 0

            if pct >= self.MEDIUM_THRESHOLD:
                continue

            priority = self._determine_priority(pct, file_path)

            suggested_test = ""
            if generate_suggestions and priority in ("critical", "high"):
                source = self._read_source(file_path)
                if source:
                    suggested_test = await self._generate_test_suggestion(
                        file_path, source, uncovered
                    )

            gaps.append(CoverageGap(
                file_path=file_path,
                uncovered_lines=uncovered,
                line_coverage_pct=round(pct, 1),
                priority=priority,
                suggested_test=suggested_test,
            ))

        gaps.sort(key=lambda g: {"critical": 0, "high": 1, "medium": 2, "low": 3}[g.priority])
        return gaps

    def _determine_priority(self, pct: float, file_path: str) -> str:
        critical_patterns = ["auth", "security", "payment", "transaction"]
        is_critical_file = any(p in file_path.lower() for p in critical_patterns)

        if pct < self.CRITICAL_THRESHOLD or is_critical_file:
            return "critical"
        elif pct < self.HIGH_THRESHOLD:
            return "high"
        elif pct < self.MEDIUM_THRESHOLD:
            return "medium"
        return "low"

    async def _generate_test_suggestion(
        self, file_path: str, source: str, uncovered_lines: list[int]
    ) -> str:
        uncovered_snippets = self._extract_uncovered_snippets(source, uncovered_lines)

        response = await self.llm.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "Verilen kaynak kodun test edilmemiş bölümleri için pytest test önerisi üret.",
                },
                {
                    "role": "user",
                    "content": (
                        f"Dosya: {file_path}\n"
                        f"Test edilmemiş kod bölümleri:\n{uncovered_snippets}\n\n"
                        "Bu bölümler için pytest test kodu öner."
                    ),
                },
            ],
            temperature=0.2,
            max_tokens=1000,
        )
        return response.choices[0].message.content

    def _extract_uncovered_snippets(self, source: str, uncovered: list[int]) -> str:
        lines = source.split("\n")
        snippets = []
        for line_no in uncovered[:20]:
            if 0 < line_no <= len(lines):
                start = max(0, line_no - 3)
                end = min(len(lines), line_no + 2)
                snippet = "\n".join(f"{'>>>' if i+1 == line_no else '   '} {i+1}: {lines[i]}" for i in range(start, end))
                snippets.append(snippet)
        return "\n---\n".join(snippets)

    def _load_coverage(self, path: str) -> dict:
        p = Path(path)
        if p.exists():
            return json.loads(p.read_text())
        return {}

    def _read_source(self, file_path: str) -> str | None:
        p = Path(file_path)
        if p.exists():
            return p.read_text()
        return None

    def _should_skip(self, file_path: str) -> bool:
        skip_patterns = ["__pycache__", "migrations", "node_modules", ".venv", "test_"]
        return any(p in file_path for p in skip_patterns)
```

---

## 9. Assertion Öneri Engine

Mevcut testlerdeki eksik assertion'ları tespit eden servis.

```python
# engine/services/assertion_engine.py
from dataclasses import dataclass
import ast
import re
from pathlib import Path

from openai import AsyncOpenAI


@dataclass
class AssertionSuggestion:
    test_file: str
    test_name: str
    current_assertions: list[str]
    suggested_assertions: list[str]
    rationale: str


class AssertionEngine:
    def __init__(self, openai_api_key: str):
        self.llm = AsyncOpenAI(api_key=openai_api_key)

    async def analyze_test_file(self, file_path: str) -> list[AssertionSuggestion]:
        """Test dosyasındaki testleri analiz eder ve assertion önerileri üretir."""
        source = Path(file_path).read_text()
        test_functions = self._extract_test_functions(source)

        suggestions = []
        for func_name, func_body in test_functions:
            current_asserts = self._extract_assertions(func_body)

            if len(current_asserts) < 2:
                suggestion = await self._suggest_assertions(
                    file_path, func_name, func_body, current_asserts
                )
                if suggestion:
                    suggestions.append(suggestion)

        return suggestions

    def _extract_test_functions(self, source: str) -> list[tuple[str, str]]:
        """Test fonksiyonlarını çıkarır."""
        tree = ast.parse(source)
        functions = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name.startswith("test_"):
                    func_source = ast.get_source_segment(source, node)
                    if func_source:
                        functions.append((node.name, func_source))
        return functions

    def _extract_assertions(self, func_body: str) -> list[str]:
        """Mevcut assertion'ları çıkarır."""
        patterns = [
            r"assert\s+.+",
            r"expect\(.+\)\..+",
            r"assertEqual\(.+\)",
            r"assertTrue\(.+\)",
            r"assertIn\(.+\)",
        ]
        assertions = []
        for pattern in patterns:
            assertions.extend(re.findall(pattern, func_body))
        return assertions

    async def _suggest_assertions(
        self,
        file_path: str,
        func_name: str,
        func_body: str,
        current_asserts: list[str],
    ) -> AssertionSuggestion | None:
        response = await self.llm.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Sen test kalitesi uzmanısın. Verilen test fonksiyonunu analiz et "
                        "ve eksik assertion'ları öner. Sadece anlamlı kontroller öner."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Dosya: {file_path}\n"
                        f"Test: {func_name}\n"
                        f"Mevcut assertion'lar: {current_asserts}\n\n"
                        f"Kod:\n{func_body}\n\n"
                        "Eksik ancak anlamlı assertion'lar neler olabilir? "
                        "Her öneri için kısa gerekçe yaz."
                    ),
                },
            ],
            temperature=0.2,
        )

        content = response.choices[0].message.content
        suggested = re.findall(r"(?:assert|expect)\s*.+", content)

        if suggested:
            return AssertionSuggestion(
                test_file=file_path,
                test_name=func_name,
                current_assertions=current_asserts,
                suggested_assertions=suggested,
                rationale=content,
            )
        return None
```

---

## 10. LLM Gateway

Merkezi LLM erişim katmanı — caching, PII sanitization, maliyet takibi.

```python
# engine/services/llm_gateway.py
from dataclasses import dataclass, field
import hashlib
import json
import re
import time
from datetime import datetime

from openai import AsyncOpenAI
from anthropic import AsyncAnthropic


@dataclass
class LLMResponse:
    content: str
    model: str
    tokens_used: int
    cached: bool
    cost_usd: float
    latency_ms: int


@dataclass
class UsageStats:
    total_calls: int = 0
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    cache_hits: int = 0
    calls_by_model: dict = field(default_factory=dict)


# Token başına yaklaşık maliyet (USD)
MODEL_COSTS = {
    "gpt-4o": {"input": 0.0025 / 1000, "output": 0.01 / 1000},
    "gpt-4o-mini": {"input": 0.00015 / 1000, "output": 0.0006 / 1000},
    "claude-3-5-sonnet": {"input": 0.003 / 1000, "output": 0.015 / 1000},
    "claude-3-5-haiku": {"input": 0.0008 / 1000, "output": 0.004 / 1000},
}

PII_PATTERNS = [
    (r"\b\d{11}\b", "[TC_KIMLIK]"),           # TC Kimlik
    (r"\b\d{10,16}\b", "[HESAP_NO]"),          # Banka hesap numarası
    (r"\b[A-Z]{2}\d{2}\s?\d{4}\s?\d{4}\s?\d{4}\s?\d{4}\s?\d{4}\s?\d{2}\b", "[IBAN]"),
    (r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b", "[EMAIL]"),
    (r"\b05\d{2}[\s-]?\d{3}[\s-]?\d{2}[\s-]?\d{2}\b", "[TELEFON]"),
]


class LLMGateway:
    def __init__(
        self,
        openai_api_key: str | None = None,
        anthropic_api_key: str | None = None,
        enable_cache: bool = True,
        enable_pii_sanitization: bool = True,
        budget_limit_usd: float = 100.0,
    ):
        self.openai = AsyncOpenAI(api_key=openai_api_key) if openai_api_key else None
        self.anthropic = AsyncAnthropic(api_key=anthropic_api_key) if anthropic_api_key else None
        self.enable_cache = enable_cache
        self.enable_pii_sanitization = enable_pii_sanitization
        self.budget_limit = budget_limit_usd
        self.cache: dict[str, LLMResponse] = {}
        self.stats = UsageStats()

    async def complete(
        self,
        messages: list[dict],
        model: str = "gpt-4o",
        temperature: float = 0.2,
        max_tokens: int = 2000,
    ) -> LLMResponse:
        """Merkezi LLM çağrısı — cache, PII sanitize, maliyet kontrolü ile."""
        if self.stats.total_cost_usd >= self.budget_limit:
            raise RuntimeError(
                f"LLM bütçe limiti aşıldı: ${self.stats.total_cost_usd:.2f} >= ${self.budget_limit:.2f}"
            )

        if self.enable_pii_sanitization:
            messages = self._sanitize_messages(messages)

        cache_key = self._cache_key(messages, model, temperature)
        if self.enable_cache and cache_key in self.cache:
            self.stats.cache_hits += 1
            cached = self.cache[cache_key]
            return LLMResponse(
                content=cached.content, model=cached.model,
                tokens_used=0, cached=True, cost_usd=0, latency_ms=0,
            )

        start = time.monotonic()

        if model.startswith("claude"):
            response = await self._call_anthropic(messages, model, temperature, max_tokens)
        else:
            response = await self._call_openai(messages, model, temperature, max_tokens)

        latency = int((time.monotonic() - start) * 1000)
        response.latency_ms = latency

        self._update_stats(response)

        if self.enable_cache:
            self.cache[cache_key] = response

        return response

    async def _call_openai(self, messages, model, temperature, max_tokens) -> LLMResponse:
        resp = await self.openai.chat.completions.create(
            model=model, messages=messages,
            temperature=temperature, max_tokens=max_tokens,
        )
        tokens = resp.usage.total_tokens if resp.usage else 0
        cost = self._calculate_cost(model, resp.usage.prompt_tokens, resp.usage.completion_tokens) if resp.usage else 0
        return LLMResponse(
            content=resp.choices[0].message.content,
            model=model, tokens_used=tokens, cached=False,
            cost_usd=cost, latency_ms=0,
        )

    async def _call_anthropic(self, messages, model, temperature, max_tokens) -> LLMResponse:
        system_msg = next((m["content"] for m in messages if m["role"] == "system"), "")
        user_msgs = [m for m in messages if m["role"] != "system"]
        resp = await self.anthropic.messages.create(
            model=model, system=system_msg, messages=user_msgs,
            temperature=temperature, max_tokens=max_tokens,
        )
        tokens = resp.usage.input_tokens + resp.usage.output_tokens
        cost = self._calculate_cost(model, resp.usage.input_tokens, resp.usage.output_tokens)
        return LLMResponse(
            content=resp.content[0].text,
            model=model, tokens_used=tokens, cached=False,
            cost_usd=cost, latency_ms=0,
        )

    def _sanitize_messages(self, messages: list[dict]) -> list[dict]:
        sanitized = []
        for msg in messages:
            content = msg["content"]
            for pattern, replacement in PII_PATTERNS:
                content = re.sub(pattern, replacement, content)
            sanitized.append({**msg, "content": content})
        return sanitized

    def _cache_key(self, messages, model, temperature) -> str:
        raw = json.dumps({"messages": messages, "model": model, "temp": temperature}, sort_keys=True)
        return hashlib.sha256(raw.encode()).hexdigest()

    def _calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        costs = MODEL_COSTS.get(model, MODEL_COSTS["gpt-4o"])
        return input_tokens * costs["input"] + output_tokens * costs["output"]

    def _update_stats(self, response: LLMResponse):
        self.stats.total_calls += 1
        self.stats.total_tokens += response.tokens_used
        self.stats.total_cost_usd += response.cost_usd
        model_stats = self.stats.calls_by_model.setdefault(response.model, {"calls": 0, "tokens": 0, "cost": 0})
        model_stats["calls"] += 1
        model_stats["tokens"] += response.tokens_used
        model_stats["cost"] += response.cost_usd
```

---

## 11. Sentetik Veri Generator

Bankacılık verileri için gelişmiş sentetik veri üretimi.

```python
# engine/ai_synthetic_data/generators/banking_generator.py
from dataclasses import dataclass
from typing import Any
import random
from datetime import datetime, timedelta

from faker import Faker


fake = Faker("tr_TR")


@dataclass
class CustomerProfile:
    customer_id: str
    segment: str             # "bireysel" | "ticari" | "kobi"
    tc_kimlik: str
    full_name: str
    birth_date: str
    city: str
    income_bracket: str
    risk_score: float


@dataclass
class AccountData:
    account_id: str
    customer_id: str
    account_type: str        # "vadesiz" | "vadeli" | "kredi"
    currency: str
    balance: float
    opened_date: str
    status: str


@dataclass
class TransactionData:
    transaction_id: str
    account_id: str
    transaction_type: str    # "havale" | "eft" | "pos" | "atm"
    amount: float
    currency: str
    timestamp: str
    counterparty: str
    description: str


SEGMENT_INCOME_MAP = {
    "bireysel": {"low": (2000, 8000), "mid": (8000, 25000), "high": (25000, 100000)},
    "ticari": {"low": (50000, 200000), "mid": (200000, 1000000), "high": (1000000, 10000000)},
    "kobi": {"low": (10000, 50000), "mid": (50000, 500000), "high": (500000, 5000000)},
}

SEGMENT_BALANCE_CORRELATION = {
    "bireysel": {"low": (500, 5000), "mid": (5000, 50000), "high": (50000, 500000)},
    "ticari": {"low": (10000, 100000), "mid": (100000, 1000000), "high": (1000000, 50000000)},
    "kobi": {"low": (2000, 20000), "mid": (20000, 200000), "high": (200000, 2000000)},
}


class BankingSyntheticGenerator:
    """Bankacılık domain'i için korelasyon-koruyan sentetik veri üretici."""

    def __init__(self, seed: int = 42):
        random.seed(seed)
        fake.seed_instance(seed)

    def generate_customer(self, segment: str | None = None) -> CustomerProfile:
        if segment is None:
            segment = random.choice(["bireysel", "ticari", "kobi"])

        income_bracket = random.choices(
            ["low", "mid", "high"], weights=[0.5, 0.35, 0.15]
        )[0]
        income_range = SEGMENT_INCOME_MAP[segment][income_bracket]

        age = self._correlated_age(income_bracket)
        risk_score = self._correlated_risk(segment, income_bracket, age)

        return CustomerProfile(
            customer_id=f"C{fake.unique.random_number(digits=8, fix_len=True)}",
            segment=segment,
            tc_kimlik=self._generate_tc_kimlik(),
            full_name=fake.name(),
            birth_date=fake.date_of_birth(minimum_age=age - 5, maximum_age=age + 5).isoformat(),
            city=fake.city(),
            income_bracket=income_bracket,
            risk_score=round(risk_score, 2),
        )

    def generate_account(
        self, customer: CustomerProfile, account_type: str | None = None
    ) -> AccountData:
        if account_type is None:
            account_type = random.choice(["vadesiz", "vadeli", "kredi"])

        balance_range = SEGMENT_BALANCE_CORRELATION[customer.segment][customer.income_bracket]
        balance = round(random.uniform(*balance_range), 2)

        if account_type == "kredi":
            balance = -abs(balance)

        return AccountData(
            account_id=f"A{fake.unique.random_number(digits=10, fix_len=True)}",
            customer_id=customer.customer_id,
            account_type=account_type,
            currency="TRY",
            balance=balance,
            opened_date=fake.date_between(start_date="-5y").isoformat(),
            status=random.choices(["aktif", "pasif", "kapali"], weights=[0.85, 0.1, 0.05])[0],
        )

    def generate_transactions(
        self, account: AccountData, count: int = 10
    ) -> list[TransactionData]:
        txns = []
        base_amount = abs(account.balance) / max(count, 1)

        for _ in range(count):
            tx_type = random.choices(
                ["havale", "eft", "pos", "atm"], weights=[0.3, 0.25, 0.3, 0.15]
            )[0]

            amount = round(base_amount * random.uniform(0.1, 3.0), 2)

            txns.append(TransactionData(
                transaction_id=f"T{fake.unique.random_number(digits=12, fix_len=True)}",
                account_id=account.account_id,
                transaction_type=tx_type,
                amount=amount,
                currency=account.currency,
                timestamp=fake.date_time_between(start_date="-30d").isoformat(),
                counterparty=fake.company() if tx_type in ("havale", "eft") else fake.company(),
                description=self._generate_description(tx_type),
            ))

        txns.sort(key=lambda t: t.timestamp)
        return txns

    def generate_dataset(
        self, customer_count: int = 100, accounts_per_customer: int = 2, txns_per_account: int = 10
    ) -> dict[str, list]:
        customers = []
        accounts = []
        transactions = []

        for _ in range(customer_count):
            customer = self.generate_customer()
            customers.append(customer)

            for _ in range(random.randint(1, accounts_per_customer)):
                account = self.generate_account(customer)
                accounts.append(account)

                txns = self.generate_transactions(account, random.randint(5, txns_per_account))
                transactions.extend(txns)

        return {
            "customers": [c.__dict__ for c in customers],
            "accounts": [a.__dict__ for a in accounts],
            "transactions": [t.__dict__ for t in transactions],
        }

    def _correlated_age(self, income_bracket: str) -> int:
        """Gelir ile yaş arasında pozitif korelasyon."""
        age_ranges = {"low": (22, 35), "mid": (30, 50), "high": (35, 65)}
        return random.randint(*age_ranges[income_bracket])

    def _correlated_risk(self, segment: str, income: str, age: int) -> float:
        """Segment, gelir ve yaşa bağlı risk skoru."""
        base = {"bireysel": 0.3, "ticari": 0.5, "kobi": 0.4}[segment]
        income_adj = {"low": 0.2, "mid": 0.0, "high": -0.15}[income]
        age_adj = -0.005 * (age - 30) if age > 30 else 0.01 * (30 - age)
        return max(0.01, min(0.99, base + income_adj + age_adj + random.uniform(-0.1, 0.1)))

    def _generate_tc_kimlik(self) -> str:
        """Geçerli formatta TC Kimlik numarası üretir (gerçek değil)."""
        digits = [random.randint(1, 9)] + [random.randint(0, 9) for _ in range(8)]
        d10 = ((sum(digits[0:9:2]) * 7) - sum(digits[1:8:2])) % 10
        digits.append(d10)
        d11 = sum(digits[:10]) % 10
        digits.append(d11)
        return "".join(map(str, digits))

    def _generate_description(self, tx_type: str) -> str:
        descriptions = {
            "havale": ["Fatura ödemesi", "Kira transferi", "Maaş ödemesi", "Tedarikçi ödemesi"],
            "eft": ["EFT gönderimi", "Fatura ödemesi", "Kredi ödemesi"],
            "pos": ["Market alışverişi", "Online alışveriş", "Restoran", "Akaryakıt"],
            "atm": ["Nakit çekim", "Havale gönderimi"],
        }
        return random.choice(descriptions.get(tx_type, ["İşlem"]))
```

---

## 12. Security Scanner

Güvenlik tarama entegrasyonu.

```python
# engine/services/security_scanner.py
from dataclasses import dataclass
import subprocess
import json


@dataclass
class SecurityFinding:
    severity: str        # "critical" | "high" | "medium" | "low" | "info"
    category: str        # "injection" | "xss" | "auth" | "config" | "info_disclosure"
    title: str
    description: str
    url: str
    evidence: str
    cwe_id: str


class SecurityScanner:
    """ZAP tabanlı güvenlik tarama entegrasyonu."""

    def __init__(self, zap_path: str = "zap-cli", target_url: str = "http://127.0.0.1:8000"):
        self.zap_path = zap_path
        self.target_url = target_url

    def quick_scan(self) -> list[SecurityFinding]:
        """Hızlı güvenlik taraması (spider + active scan)."""
        # ZAP spider
        subprocess.run(
            [self.zap_path, "spider", self.target_url],
            capture_output=True, timeout=300,
        )
        # ZAP active scan
        subprocess.run(
            [self.zap_path, "active-scan", self.target_url],
            capture_output=True, timeout=600,
        )
        # Sonuçları al
        result = subprocess.run(
            [self.zap_path, "alerts", "-f", "json"],
            capture_output=True, text=True,
        )
        return self._parse_alerts(result.stdout)

    def api_scan(self, openapi_spec_url: str) -> list[SecurityFinding]:
        """OpenAPI spec tabanlı API güvenlik taraması."""
        result = subprocess.run(
            [self.zap_path, "openapi", openapi_spec_url, "-t", self.target_url, "-f", "json"],
            capture_output=True, text=True, timeout=600,
        )
        return self._parse_alerts(result.stdout)

    def _parse_alerts(self, json_output: str) -> list[SecurityFinding]:
        try:
            alerts = json.loads(json_output)
        except json.JSONDecodeError:
            return []

        findings = []
        for alert in alerts:
            findings.append(SecurityFinding(
                severity=self._map_risk(alert.get("risk", "info")),
                category=self._categorize(alert.get("cweid", "")),
                title=alert.get("name", "Bilinmeyen"),
                description=alert.get("description", ""),
                url=alert.get("url", ""),
                evidence=alert.get("evidence", ""),
                cwe_id=alert.get("cweid", ""),
            ))
        return findings

    def _map_risk(self, risk: str) -> str:
        return {"High": "high", "Medium": "medium", "Low": "low", "Informational": "info"}.get(risk, "info")

    def _categorize(self, cwe_id: str) -> str:
        injection_cwes = {"89", "78", "90", "91"}
        xss_cwes = {"79", "80"}
        auth_cwes = {"287", "306", "862"}
        if cwe_id in injection_cwes:
            return "injection"
        if cwe_id in xss_cwes:
            return "xss"
        if cwe_id in auth_cwes:
            return "auth"
        return "config"
```

---

## 13. CI/CD Workflow Konfigürasyonu

AI destekli test akışını GitHub Actions ile entegre eden workflow.

```yaml
# .github/workflows/ai-test-pipeline.yml
name: AI-Enhanced Test Pipeline

on:
  pull_request:
    branches: [main, develop]
  schedule:
    - cron: '0 2 * * *'  # Her gece 02:00 UTC
  workflow_dispatch:

env:
  TEST_ENV: ci
  DATABASE_URL: postgresql+psycopg2://test_user:test_password@localhost:5432/syndata_test
  OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}

jobs:
  # Faz 1: AI Test Prioritization
  prioritize:
    if: github.event_name == 'pull_request'
    runs-on: ubuntu-latest
    outputs:
      selected-tests: ${{ steps.prioritize.outputs.tests }}
      time-saved: ${{ steps.prioritize.outputs.time_saved }}
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: AI Test Prioritization
        id: prioritize
        run: |
          cd engine
          pip install -r requirements.txt
          python -c "
          from services.test_prioritizer import TestPrioritizer
          import json
          p = TestPrioritizer()
          result = p.prioritize(time_budget_seconds=300)
          tests = [t.test_id for t in result.selected_tests]
          print(f'::set-output name=tests::{json.dumps(tests)}')
          print(f'::set-output name=time_saved::{result.estimated_time_saved_seconds}')
          print(f'Seçilen: {len(result.selected_tests)}/{result.total_tests} test')
          print(f'Tahmini zaman tasarrufu: {result.estimated_time_saved_seconds}s')
          "

  # Faz 2: Test Data Preparation
  prepare-data:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Generate Synthetic Test Data
        run: |
          cd engine
          pip install -r requirements.txt
          python -c "
          from ai_synthetic_data.generators.banking_generator import BankingSyntheticGenerator
          import json
          gen = BankingSyntheticGenerator(seed=42)
          data = gen.generate_dataset(customer_count=50, accounts_per_customer=2, txns_per_account=5)
          with open('test_data/synthetic_dataset.json', 'w') as f:
              json.dump(data, f, indent=2, ensure_ascii=False)
          print(f'Üretildi: {len(data[\"customers\"])} müşteri, {len(data[\"accounts\"])} hesap, {len(data[\"transactions\"])} işlem')
          "

      - uses: actions/upload-artifact@v4
        with:
          name: synthetic-data
          path: engine/test_data/synthetic_dataset.json

  # Faz 3: Smoke Tests (her PR'da)
  smoke:
    needs: [prepare-data]
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_USER: test_user
          POSTGRES_PASSWORD: test_password
          POSTGRES_DB: syndata_test
        ports: ['5432:5432']
      redis:
        image: redis:7
        ports: ['6379:6379']
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: 18

      - name: Install and run smoke tests
        run: |
          npm ci
          npx playwright install chromium
          npm run test:e2e:smoke

      - name: Self-Healing Retry
        if: failure()
        run: |
          echo "Smoke testler başarısız — self-healing retry başlatılıyor..."
          npm run test:e2e:smoke -- --retries=1

      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: smoke-report
          path: reports/

  # Faz 4: AI-Selected Regression (PR'da)
  regression:
    if: github.event_name == 'pull_request'
    needs: [prioritize, smoke]
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_USER: test_user
          POSTGRES_PASSWORD: test_password
          POSTGRES_DB: syndata_test
        ports: ['5432:5432']
      redis:
        image: redis:7
        ports: ['6379:6379']
    steps:
      - uses: actions/checkout@v4

      - name: Run AI-Prioritized Tests
        run: |
          SELECTED='${{ needs.prioritize.outputs.selected-tests }}'
          echo "AI seçimi: $SELECTED"
          npm run test:e2e:regression

  # Faz 5: Nightly Full Suite
  nightly:
    if: github.event_name == 'schedule'
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_USER: test_user
          POSTGRES_PASSWORD: test_password
          POSTGRES_DB: syndata_test
        ports: ['5432:5432']
      redis:
        image: redis:7
        ports: ['6379:6379']
    steps:
      - uses: actions/checkout@v4

      - name: Full Test Suite
        run: npm run test:all:full

      - name: Coverage Gap Analysis
        if: always()
        run: |
          cd engine
          python -c "
          import asyncio
          from services.coverage_analyzer import CoverageAnalyzer
          async def main():
              analyzer = CoverageAnalyzer(openai_api_key='$OPENAI_API_KEY')
              gaps = await analyzer.analyze(generate_suggestions=True)
              for g in gaps[:10]:
                  print(f'{g.priority}: {g.file_path} ({g.line_coverage_pct}%)')
          asyncio.run(main())
          "

      - name: Flaky Test Analysis
        if: always()
        run: |
          cd engine
          python -c "
          from services.flaky_detector import FlakyDetector
          detector = FlakyDetector()
          results = detector.analyze_all()
          quarantined = [t for t in results if t.recommendation == 'quarantine']
          print(f'Flaky testler: {len(quarantined)} karantinada')
          for t in quarantined:
              print(f'  {t.test_id}: skor={t.flaky_score}, flipler={t.flip_count}')
          "

  # Faz 6: Post-Test Anomaly Detection
  analyze:
    if: always()
    needs: [smoke, regression]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Anomaly Detection
        run: |
          cd engine
          pip install -r requirements.txt
          python -c "
          from services.anomaly_detector import AnomalyDetector
          import json
          detector = AnomalyDetector()
          # Test sonuçlarını oku (önceki job'dan artifact)
          results = {'total': 50, 'passed': 47, 'failed': 3, 'total_duration': 180, 'avg_duration': 3.6}
          anomalies = detector.analyze_test_run(results)
          if anomalies:
              print('ANOMALY TESPİT EDİLDİ:')
              for a in anomalies:
                  print(f'  [{a.severity}] {a.description}')
          else:
              print('Anomaly tespit edilmedi — sonuçlar normal.')
          "
```

---

## 14. Playwright MCP Konfigürasyonu

Playwright MCP (Model Context Protocol) ile AI agent entegrasyonu.

```typescript
// e2e/config/mcp-config.ts
export interface MCPConfig {
  browser: "chromium" | "firefox" | "webkit";
  headless: boolean;
  viewport: { width: number; height: number };
  snapshotMode: "accessibility" | "screenshot" | "both";
  healerEnabled: boolean;
  healerMaxRetries: number;
  llmEndpoint: string;
}

export const mcpConfig: MCPConfig = {
  browser: "chromium",
  headless: true,
  viewport: { width: 1280, height: 720 },
  snapshotMode: "accessibility",
  healerEnabled: true,
  healerMaxRetries: 2,
  llmEndpoint: process.env.ENGINE_BASE || "http://127.0.0.1:5001",
};

// playwright.config.ts'e eklenecek MCP-aware proje
export const mcpProject = {
  name: "ai-assisted",
  testMatch: ["**/*.spec.ts"],
  use: {
    ...mcpConfig,
    trace: "on",
    screenshot: "on",
  },
  retries: mcpConfig.healerMaxRetries,
  timeout: 120_000,
};
```

---

## 15. Java Legacy Refactoring Helper

NexusQA Java/Selenium kodunu analiz edip Playwright eşdeğeri öneren yardımcı.

```java
// NexusQATestOtomasyon/src/main/java/helpers/RefactoringAnalyzer.java
package helpers;

import java.io.*;
import java.nio.file.*;
import java.util.*;
import java.util.regex.*;

/**
 * NexusQA Selenium test kodunu analiz edip
 * Playwright TypeScript eşdeğerine dönüşüm önerileri üretir.
 */
public class RefactoringAnalyzer {

    private static final Map<String, String> SELENIUM_TO_PLAYWRIGHT = Map.ofEntries(
        Map.entry("driver.findElement(By.id(\"", "page.getByTestId(\""),
        Map.entry("driver.findElement(By.xpath(\"", "page.locator(\""),
        Map.entry("driver.findElement(By.cssSelector(\"", "page.locator(\""),
        Map.entry("driver.findElement(By.name(\"", "page.locator('[name=\""),
        Map.entry(".click()", ".click()"),
        Map.entry(".sendKeys(", ".fill("),
        Map.entry(".getText()", ".textContent()"),
        Map.entry(".isDisplayed()", ".isVisible()"),
        Map.entry("Thread.sleep(", "// await page.waitForTimeout("),
        Map.entry("WebDriverWait", "// page.waitForSelector veya expect kullanın"),
        Map.entry("Assert.assertEquals", "expect(actual).toBe(expected)"),
        Map.entry("Assert.assertTrue", "expect(condition).toBeTruthy()")
    );

    public record ConversionSuggestion(
        String filePath,
        int lineNumber,
        String originalCode,
        String suggestedCode,
        String reason
    ) {}

    public List<ConversionSuggestion> analyzeFile(String filePath) throws IOException {
        List<String> lines = Files.readAllLines(Path.of(filePath));
        List<ConversionSuggestion> suggestions = new ArrayList<>();

        for (int i = 0; i < lines.size(); i++) {
            String line = lines.get(i).trim();
            for (var entry : SELENIUM_TO_PLAYWRIGHT.entrySet()) {
                if (line.contains(entry.getKey())) {
                    String suggested = line.replace(entry.getKey(), entry.getValue());
                    suggestions.add(new ConversionSuggestion(
                        filePath, i + 1, line, suggested,
                        "Selenium → Playwright dönüşümü"
                    ));
                }
            }

            if (line.contains("Thread.sleep")) {
                suggestions.add(new ConversionSuggestion(
                    filePath, i + 1, line,
                    "// Sabit bekleme yerine: await page.waitForSelector() veya expect().toBeVisible()",
                    "Thread.sleep anti-pattern — Playwright auto-wait kullanın"
                ));
            }
        }

        return suggestions;
    }

    public Map<String, List<ConversionSuggestion>> analyzeDirectory(String dirPath) throws IOException {
        Map<String, List<ConversionSuggestion>> results = new LinkedHashMap<>();

        try (var stream = Files.walk(Path.of(dirPath))) {
            stream.filter(p -> p.toString().endsWith(".java"))
                  .forEach(p -> {
                      try {
                          List<ConversionSuggestion> suggestions = analyzeFile(p.toString());
                          if (!suggestions.isEmpty()) {
                              results.put(p.toString(), suggestions);
                          }
                      } catch (IOException e) {
                          System.err.println("Hata: " + p + " — " + e.getMessage());
                      }
                  });
        }

        return results;
    }
}
```
