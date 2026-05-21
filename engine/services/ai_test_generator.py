"""
Doğal dil gereksinimden test kodu üreten servis.

Desteklenen framework'ler: pytest-bdd, playwright-ts, pytest
Page Object repository'si ve framework kuralları ile LLM context'i zenginleştirir.

Dalga 2 değişiklikleri:
    * Self-refine loop — validation hatalarında LLM'e "şu hataları düzelt"
      diye 2 tur daha gönderir (maksimum 3 deneme).
    * Structured output — code tek bir ``code`` alanında, kararlı fence parser.
    * Testid disiplini — UI framework'lerde assertion ve data-testid kullanımı
      sistem prompt'unda explicit zorlanır (eval suite'iyle uyumlu).
    * Observability — Prometheus ``llm_refine_iterations`` metriği emit eder.
"""
from __future__ import annotations

import ast
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

from .llm_gateway import LLMGateway
from .prompt_loader import get_engine_prompt

logger = logging.getLogger(__name__)

_ENGINE_ROOT = Path(__file__).resolve().parent.parent
SYSTEM_PROMPT = get_engine_prompt("test_generator")


REFINE_PROMPT = """\
Önceki cevabın aşağıdaki validation hatalarıyla reddedildi:

{errors}

Aynı gereksinim için kodu bu hataları giderecek şekilde YENİDEN YAZ.
Çıktı kuralı aynı: tek fenced code block, ek metin yok.
"""


@dataclass
class GeneratedTest:
    framework: str
    code: str
    file_path: str
    validation_passed: bool
    validation_errors: list[str] = field(default_factory=list)
    refine_iterations: int = 0


class AITestGenerator:
    """Doğal dil → çalıştırılabilir test kodu (self-refine loop ile)."""

    # Varsayılan: 2 refine denemesi (toplam 3 LLM çağrısı).
    # Her refine: önceki validation hatalarını prompt'a geri koy.
    DEFAULT_MAX_REFINE = 2

    def __init__(
        self,
        gateway: LLMGateway,
        model: str | None = None,
        max_refine: int | None = None,
    ):
        self.gateway = gateway
        self.model = model or "gpt-4o"
        self.max_refine = (
            max_refine if max_refine is not None else self.DEFAULT_MAX_REFINE
        )

    def generate_from_requirement(
        self,
        requirement: str,
        framework: str = "pytest-bdd",
        page_objects: list[str] | None = None,
    ) -> GeneratedTest:
        context = self._build_context(framework, page_objects)
        po_summary = self._scan_page_objects(framework)

        system_msg = SYSTEM_PROMPT + ("\n\n" + po_summary if po_summary else "")
        user_msg = f"{context}\n\nGereksinim: {requirement}"

        messages: list[dict[str, str]] = [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg},
        ]

        code: str = ""
        errors: list[str] = []
        refines_done = 0   # sadece gerçek refine sayısı (ilk deneme hariç)

        for attempt in range(self.max_refine + 1):
            resp = self.gateway.complete(
                messages, model=self.model, temperature=0.2, max_tokens=3000,
            )
            code = self._extract_code_blocks(resp.content)
            errors = self._validate_code(code, framework)

            if not errors:
                break

            if attempt >= self.max_refine:
                # Son deneme hatalı kaldı, loop biter
                break

            # Bir refine turu daha — LLM'e hataları geri ver
            refines_done += 1
            logger.info(
                "ai_test_generator refine #%d — %d hata",
                refines_done, len(errors),
            )
            messages = [
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg},
                {"role": "assistant", "content": resp.content},
                {
                    "role": "user",
                    "content": REFINE_PROMPT.format(
                        errors="\n".join(f"  - {e}" for e in errors)
                    ),
                },
            ]

        iterations = refines_done

        # Prometheus — refine iterasyon sayısı
        try:
            from app.domains.ai.metrics import record_refine  # type: ignore

            record_refine(task_type="test_gen", iterations=iterations)
        except Exception:
            pass  # engine backend paketine bağlı değil; metric yoksa sessiz

        file_path = self._determine_file_path(requirement, framework)
        return GeneratedTest(
            framework=framework,
            code=code,
            file_path=file_path,
            validation_passed=len(errors) == 0,
            validation_errors=errors,
            refine_iterations=iterations,
        )

    # ── helpers ─────────────────────────────────────────────────────────────

    def _build_context(self, framework: str, page_objects: list[str] | None) -> str:
        parts = [f"Framework: {framework}"]
        if page_objects:
            parts.append(f"Kullanılacak Page Object'ler: {', '.join(page_objects)}")
        if framework == "pytest-bdd":
            parts.append("Çıktı formatı: Gherkin feature dosyası + Python step definitions")
        elif framework == "playwright-ts":
            parts.append("Çıktı formatı: TypeScript Playwright spec dosyası (.spec.ts)")
        else:
            parts.append("Çıktı formatı: Python pytest test fonksiyonu")
        return "\n".join(parts)

    def _scan_page_objects(self, framework: str) -> str:
        """Mevcut page object'lerin metot imzalarıyla özetini döndürür.

        Python POM'leri için AST ile sınıf + public method isimlerini çıkarır.
        TypeScript için kısıtlı — sadece ``class X`` satırları. LLM prompt'unda
        metot listesi test üretim kalitesini eval suite skorunda ölçülebilir
        biçimde yükseltir (RAG-light).
        """
        if framework == "playwright-ts":
            pages_dir = _ENGINE_ROOT.parent / "e2e" / "pages"
            suffix = ".ts"
        else:
            pages_dir = _ENGINE_ROOT / "pages"
            suffix = ".py"

        if not pages_dir.exists():
            return ""

        lines: list[str] = ["Mevcut Page Object'ler (kullanılabilir metotlar):"]
        max_files = 30  # context budget koruması
        count = 0

        for f in sorted(pages_dir.glob(f"*{suffix}")):
            if f.name.startswith("_") or f.name in {"index.ts", "BasePage.ts"}:
                continue
            if count >= max_files:
                lines.append(f"  ... (+{len(list(pages_dir.glob(f'*{suffix}'))) - count} daha)")
                break

            methods = self._extract_methods(f, framework)
            if methods:
                lines.append(f"  - {f.stem}: {', '.join(methods[:8])}")
            else:
                lines.append(f"  - {f.stem}")
            count += 1

        return "\n".join(lines) if len(lines) > 1 else ""

    @staticmethod
    def _extract_methods(path: Path, framework: str) -> list[str]:
        """Public method isimlerini çek — POM retrieval için (RAG-light)."""
        try:
            src = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return []

        methods: list[str] = []
        if framework != "playwright-ts":
            try:
                tree = ast.parse(src)
            except SyntaxError:
                return []
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if node.name.startswith("_") or node.name == "__init__":
                        continue
                    methods.append(f"{node.name}()")
        else:
            # TS için hafif regex — async method(...) veya method(...)
            for m in re.finditer(
                r"^\s*(?:async\s+)?([a-zA-Z_][a-zA-Z0-9_]*)\s*\([^)]*\)\s*[:{]",
                src,
                re.MULTILINE,
            ):
                name = m.group(1)
                if name in {"constructor", "if", "for", "while", "switch"} or name.startswith("_"):
                    continue
                methods.append(f"{name}()")

        # tekrarları at + sıra koru
        seen, unique = set(), []
        for m in methods:
            if m not in seen:
                seen.add(m)
                unique.append(m)
        return unique

    @staticmethod
    def _extract_code_blocks(raw: str) -> str:
        blocks: list[str] = []
        in_block = False
        buf: list[str] = []
        for line in raw.split("\n"):
            if line.startswith("```") and not in_block:
                in_block = True
                continue
            if line.startswith("```") and in_block:
                in_block = False
                blocks.append("\n".join(buf))
                buf = []
                continue
            if in_block:
                buf.append(line)
        if buf:
            blocks.append("\n".join(buf))
        return "\n\n# ---\n\n".join(blocks) if blocks else raw

    @staticmethod
    def _determine_file_path(requirement: str, framework: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "_", requirement[:60].lower()).strip("_")
        if framework == "pytest-bdd":
            return f"engine/features/ai_generated/{slug}.feature"
        if framework == "playwright-ts":
            return f"e2e/ai-generated/{slug}.spec.ts"
        return f"engine/tests/ai_generated/test_{slug}.py"

    @staticmethod
    def _validate_code(code: str, framework: str) -> list[str]:
        errors: list[str] = []
        if not code.strip():
            errors.append("Üretilen kod boş")
            return errors

        # 1) Python AST — pytest / pytest-bdd için
        if framework in ("pytest-bdd", "pytest"):
            for i, block in enumerate(code.split("# ---")):
                block = block.strip()
                if not block or block.startswith("Feature:") or block.startswith("Senaryo"):
                    continue
                try:
                    ast.parse(block)
                except SyntaxError as exc:
                    errors.append(f"Blok {i}: Python syntax hatası — {exc}")

        # 2) UI framework'lerde assertion / expect mutlak
        ui_frameworks = {"pytest", "pytest-bdd", "playwright-ts"}
        if framework in ui_frameworks:
            assertion_patterns = (
                r"\bassert\s",
                r"expect\s*\(",
                r"\.assert_[a-z_]+\(",
                r"pytest\.raises\(",
            )
            if not any(re.search(p, code) for p in assertion_patterns):
                errors.append(
                    "UI testinde assertion / expect bulunamadı "
                    "(en az bir assertion mutlaka gerekli)"
                )

            # 3) data-testid tercih edilmeli (zayıf uyarı, hata sayılır ki
            # refine tetiklensin; fail-closed eval)
            testid_patterns = (
                r"data[-_]testid",
                r"getByTestId",
                r"get_by_test_id",
                r"GET_BY_TESTID",
            )
            if not any(re.search(p, code, re.I) for p in testid_patterns):
                errors.append(
                    "data-testid locator'ı tespit edilmedi — UI testi "
                    "için öncelikli locator stratejisi"
                )

        return errors
