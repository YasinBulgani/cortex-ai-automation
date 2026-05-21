"""Test Impact Analysis — PR diff'e göre etkilenen testleri seç.

Plan: docs/AI_OTOMASYON_GELISTIRME_PLANI.md §4 / E2.3.

Giriş: PR'ın değişen dosya listesi (``git diff --name-only base..HEAD``).
Çıkış: çalıştırılacak test kimliklerinin listesi.

Üç sinyal kaynağı (öncelik sırasıyla):
    1. **Coverage map**: ``coverage.xml`` veya ``lcov.info`` parse edilerek
       ``{src_file -> Set[test_file]}`` eşlemesi. En güvenilir sinyal;
       gerçek runtime dependency.
    2. **Import graph**: Test dosyaları içinde değişen src'ye ``import`` /
       ``from X import`` veya ``require()`` referansları. Python + JS/TS
       destekli basit regex tabanlı tarayıcı (AST gerektirmez; edge-case
       kaçırsa bile safe-over-recall prensibiyle UNION alınır).
    3. **Git churn history**: Son N commit'te aynı anda değişen dosya
       çiftleri. İstatistiksel korelasyon — coverage yoksa fallback.

Tasarım kararları:
    * Pure Python, sadece stdlib. CI'da ek dep yok.
    * Tüm sinyaller ``set[str]`` döndürür; orchestrator UNION alır →
      **recall öncelikli, precision ikincil**. Yanlış pozitif (fazla test
      koşmak) yanlış negatiften (bug kaçırmak) tercih edilir.
    * ``changed_files`` içinde test dosyası varsa direkt tabana ekle
      (test'in kendisi değiştiyse kesin koşulmalı).
    * Eşik: değişen dosya sayısı > ``TIA_MAX_IMPACT_RATIO`` × toplam src →
       tüm test suite'ini koş (değişiklik çok büyük, seçici koşum güvensiz).
"""
from __future__ import annotations

import logging
import os
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple
from xml.etree import ElementTree as ET

logger = logging.getLogger(__name__)


# Dizin bazlı test tespiti — proje kabul kuralları
_TEST_DIR_MARKERS = ("/tests/", "/test/", "/__tests__/", "/e2e/", "/spec/")
_TEST_FILE_SUFFIXES = (
    ".spec.ts", ".spec.tsx", ".spec.js", ".spec.jsx",
    ".test.ts", ".test.tsx", ".test.js", ".test.jsx",
)
_TEST_FILE_PREFIXES = ("test_",)  # pytest convention

# src extensions we care about for impact
_SRC_EXTS = (".py", ".ts", ".tsx", ".js", ".jsx", ".vue", ".svelte")


def is_test_file(path: str) -> bool:
    p = path.replace("\\", "/").lower()
    if any(m in f"/{p}" for m in _TEST_DIR_MARKERS):
        return True
    name = p.rsplit("/", 1)[-1]
    if any(name.endswith(s) for s in _TEST_FILE_SUFFIXES):
        return True
    if name.startswith(_TEST_FILE_PREFIXES) and name.endswith(".py"):
        return True
    return False


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, str(default)))
    except ValueError:
        return default


# ── Coverage map ──────────────────────────────────────────────────────────


@dataclass
class CoverageMap:
    """src_file → set(test_file) eşlemesi."""

    src_to_tests: Dict[str, Set[str]] = field(default_factory=dict)

    def impacted_tests(self, changed_src: Iterable[str]) -> Set[str]:
        out: Set[str] = set()
        for src in changed_src:
            tests = self.src_to_tests.get(src)
            if tests:
                out.update(tests)
        return out


def parse_coverage_xml(path: Path) -> CoverageMap:
    """coverage.py ``coverage xml`` çıktısı.

    Tek bir coverage raporunda test-başı ayrım yoktur (toplam coverage'dır);
    ancak ``contextual coverage`` varsa test bağlamı per-line saklanır.
    Bu parser contextual ``<contexts>`` varsa kullanır, yoksa boş döner
    (import graph fallback'e düşülür).
    """
    cmap = CoverageMap()
    if not path.exists():
        return cmap
    try:
        tree = ET.parse(path)
    except ET.ParseError as exc:
        logger.warning("coverage.xml parse error: %s", exc)
        return cmap

    root = tree.getroot()
    for cls in root.iter("class"):
        filename = cls.attrib.get("filename")
        if not filename:
            continue
        tests: Set[str] = set()
        for line in cls.iter("line"):
            contexts_el = line.find("contexts")
            if contexts_el is None:
                continue
            for ctx in contexts_el.iter("context"):
                ctx_text = (ctx.text or "").strip()
                # context metni "tests/x.py::test_y|run" gibi
                # "|" ve "::" ayırt edilerek test dosyasına indirilir
                if "::" in ctx_text:
                    test_file = ctx_text.split("::", 1)[0]
                    if test_file:
                        tests.add(test_file)
                elif ctx_text:
                    tests.add(ctx_text)
        if tests:
            cmap.src_to_tests.setdefault(filename, set()).update(tests)
    return cmap


def parse_lcov(path: Path) -> CoverageMap:
    """lcov.info parser (JS/TS projeleri için).

    LCOV contextual değil, bu yüzden bu parse sadece src file listesini
    doldurur — test eşleşmesi import graph fallback'e kalır. Yine de
    src dosyalarını "kapsanan" olarak işaretleyip orchestrator
    filtrelemesi için kullanırız.
    """
    cmap = CoverageMap()
    if not path.exists():
        return cmap
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return cmap
    for line in text.splitlines():
        if line.startswith("SF:"):
            src = line[3:].strip()
            cmap.src_to_tests.setdefault(src, set())
    return cmap


# ── Import graph fallback ─────────────────────────────────────────────────


_PY_IMPORT_RE = re.compile(
    r"^\s*(?:from\s+([a-zA-Z0-9_.]+)\s+import|import\s+([a-zA-Z0-9_.]+))",
    re.MULTILINE,
)
_JS_IMPORT_RE = re.compile(
    r"""(?:^|\s)(?:import\s+(?:[^'"]+?\s+from\s+)?|require\s*\(\s*)['"]([^'"]+)['"]""",
    re.MULTILINE,
)


def _module_name_for(py_file: Path, repo_root: Path) -> Optional[str]:
    try:
        rel = py_file.resolve().relative_to(repo_root.resolve())
    except ValueError:
        return None
    parts = list(rel.with_suffix("").parts)
    if parts and parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts) if parts else None


def _extract_imports(text: str, *, py: bool) -> Set[str]:
    out: Set[str] = set()
    if py:
        for m in _PY_IMPORT_RE.finditer(text):
            mod = (m.group(1) or m.group(2) or "").strip()
            if mod:
                out.add(mod)
    else:
        for m in _JS_IMPORT_RE.finditer(text):
            spec = (m.group(1) or "").strip()
            if spec:
                out.add(spec)
    return out


def build_import_graph(
    repo_root: Path,
    *,
    test_roots: Iterable[Path],
) -> Dict[str, Set[str]]:
    """Test dosyalarının değişen src'ye bağımlılığını kaba kes.

    Return: src_file_relative → set(test_file_relative)
    """
    graph: Dict[str, Set[str]] = {}
    for root in test_roots:
        if not root.exists():
            continue
        for f in root.rglob("*"):
            if not f.is_file():
                continue
            if not is_test_file(str(f)):
                continue
            suffix = f.suffix.lower()
            is_py = suffix == ".py"
            if not is_py and suffix not in {".ts", ".tsx", ".js", ".jsx"}:
                continue
            try:
                text = f.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            imports = _extract_imports(text, py=is_py)
            try:
                rel_test = str(f.resolve().relative_to(repo_root.resolve()))
            except ValueError:
                continue
            for imp in imports:
                # Python: modül adı → path deneyerek eşle
                # JS/TS: relative path import'ları repo içinde resolve et
                candidates = _candidate_src_paths(imp, f, repo_root, is_py=is_py)
                for c in candidates:
                    graph.setdefault(c, set()).add(rel_test)
    return graph


def _candidate_src_paths(
    imp: str, from_file: Path, repo_root: Path, *, is_py: bool
) -> List[str]:
    """Import spesifikasyonundan olası kaynak path'i üret (repo-relative)."""
    out: List[str] = []
    if is_py:
        # Python: üçüncü parti modüllerini es geç (sadece dotlu iç moduller)
        if imp.startswith("."):
            # Relative import — çözümlenmiş yol
            # Çok basit yakalama: from .foo → klasör aynı
            parent = from_file.parent
            parts = imp.lstrip(".").split(".")
            # leading dots = level (bir üste çıkma)
            level = len(imp) - len(imp.lstrip("."))
            for _ in range(max(0, level - 1)):
                parent = parent.parent
            candidate = parent.joinpath(*parts) if parts != [""] else parent
            for ext in (".py", "/__init__.py"):
                c = Path(str(candidate) + ext) if ext == ".py" else candidate / "__init__.py"
                try:
                    rel = str(c.resolve().relative_to(repo_root.resolve()))
                    out.append(rel)
                except ValueError:
                    continue
        else:
            # Absolute: "app.domains.ai" → repo/app/domains/ai.py veya /__init__.py
            parts = imp.split(".")
            base = repo_root.joinpath(*parts)
            for variant in (base.with_suffix(".py"), base / "__init__.py"):
                try:
                    rel = str(variant.resolve().relative_to(repo_root.resolve()))
                    out.append(rel)
                except ValueError:
                    continue
    else:
        # JS/TS: sadece relative import'lara bakıyoruz (node_modules ignore)
        if imp.startswith("."):
            base = (from_file.parent / imp).resolve()
            for ext in (".ts", ".tsx", ".js", ".jsx", "/index.ts", "/index.tsx"):
                c = Path(str(base) + ext) if ext.startswith(".") else base / ("index" + ext.lstrip("/"))
                try:
                    rel = str(c.resolve().relative_to(repo_root.resolve()))
                    out.append(rel)
                except ValueError:
                    continue
    return out


def impact_by_imports(
    graph: Dict[str, Set[str]],
    changed_files: Iterable[str],
) -> Set[str]:
    """changed src → (graph lookup) → test dosyaları."""
    out: Set[str] = set()
    for ch in changed_files:
        tests = graph.get(ch)
        if tests:
            out.update(tests)
    return out


# ── Git helpers ──────────────────────────────────────────────────────────


def git_diff_names(
    repo_root: Path, *, base: str = "origin/main", head: str = "HEAD"
) -> List[str]:
    """git diff --name-only base..head çıktısı (repo-relative)."""
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo_root), "diff", "--name-only", f"{base}...{head}"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        logger.warning("git diff failed: %s", exc)
        return []
    if proc.returncode != 0:
        logger.warning("git diff exit=%d stderr=%s", proc.returncode, proc.stderr[:200])
        return []
    return [ln.strip() for ln in proc.stdout.splitlines() if ln.strip()]


# ── Orchestrator ─────────────────────────────────────────────────────────


@dataclass
class ImpactResult:
    """Nihai TIA sonucu.

    ``run_all`` True ise caller tüm suite'i koşmalı. Aksi halde ``tests``
    listesi koşulur.
    """

    run_all: bool
    reason: str
    tests: List[str] = field(default_factory=list)
    changed_files: List[str] = field(default_factory=list)
    impact_sources: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "run_all": self.run_all,
            "reason": self.reason,
            "tests": self.tests,
            "changed_files": self.changed_files,
            "impact_sources": self.impact_sources,
        }


def map_changes_to_tests(
    *,
    repo_root: Path,
    changed_files: Iterable[str],
    coverage_paths: Optional[Iterable[Path]] = None,
    test_roots: Optional[Iterable[Path]] = None,
    total_src_count: Optional[int] = None,
) -> ImpactResult:
    changed_list = [c for c in changed_files if c]
    if not changed_list:
        return ImpactResult(run_all=False, reason="no_changes", changed_files=[])

    # 1. Eşik: değişim çok büyükse tüm suite
    if total_src_count and total_src_count > 0:
        ratio = len(changed_list) / total_src_count
        max_ratio = _env_float("TIA_MAX_IMPACT_RATIO", 0.30)
        if ratio >= max_ratio:
            return ImpactResult(
                run_all=True,
                reason=f"too_many_changes_{int(ratio*100)}pct",
                changed_files=changed_list,
            )

    # 2. Değişen test dosyaları direkt koşuma girer
    direct_tests: Set[str] = {f for f in changed_list if is_test_file(f)}
    src_changes: Set[str] = {f for f in changed_list if not is_test_file(f)}

    # 3. Coverage sinyali
    coverage_hits: Set[str] = set()
    if coverage_paths:
        for cp in coverage_paths:
            if str(cp).endswith(".xml"):
                cm = parse_coverage_xml(cp)
            elif str(cp).endswith(".info") or str(cp).endswith(".lcov"):
                cm = parse_lcov(cp)
            else:
                continue
            coverage_hits.update(cm.impacted_tests(src_changes))

    # 4. Import graph fallback
    import_hits: Set[str] = set()
    if test_roots:
        graph = build_import_graph(repo_root, test_roots=test_roots)
        import_hits = impact_by_imports(graph, src_changes)

    all_tests = direct_tests | coverage_hits | import_hits
    sources = {
        "direct_test_changes": len(direct_tests),
        "coverage_mapped": len(coverage_hits),
        "import_graph": len(import_hits),
    }

    if not all_tests and src_changes:
        # Hiçbir sinyalden test çıkmadı → güvenli taraf: tüm suite'i öner
        return ImpactResult(
            run_all=True,
            reason="no_signal_run_all",
            changed_files=changed_list,
            impact_sources=sources,
        )

    return ImpactResult(
        run_all=False,
        reason="selective",
        tests=sorted(all_tests),
        changed_files=changed_list,
        impact_sources=sources,
    )
