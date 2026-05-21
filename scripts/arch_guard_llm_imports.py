#!/usr/bin/env python3
"""Arch Guard — Direct LLM SDK import yasağı (Dalga 0 · ADR-0011).

L2 politikası:
    ``openai`` / ``anthropic`` SDK'ları sadece aşağıdaki "gateway" katmanında
    import edilebilir. Başka yerde edilmiş ise CI kırılır.

Allowlist (L2 + bootstrapping):
    * ai-gateway/**                          → LLM provider adapterları
    * backend/app/domains/ai/service.py      → backend direct client (kademeli
                                               olarak gateway_client'a taşınacak)
    * engine/services/llm_gateway.py         → engine LLM sarıcı

Debt register (mevcut ihlaller — bu liste SADECE küçültülebilir):
    Aşağıdaki dosyalar kullanımdan kaldırılana dek geçici izinli. Yeni ekleme
    yapılamaz; liste sadece "bu dosyayı gateway'e taşıdım" PR'ında KÜÇÜLTÜLEBİLİR.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import List, Set

# ─────────────────────────────────────────────────────────────────────────
# ALLOWLIST — L2 + bootstrapping. Bu listeye YENİ dosya eklenemez.
# ─────────────────────────────────────────────────────────────────────────
ALLOWLIST: Set[str] = {
    # L2 — gerçek LLM boundary
    "ai-gateway/",  # prefix allow
    "backend/app/domains/ai/service.py",
    "engine/services/llm_gateway.py",
    # Scripts/tools — standalone, gateway üzerinden geçmez (küçük kabul)
    "tools/aday-analizi/analyzer.py",
    # Legacy — arşivde, docs/ADR ile kaldırılacak
    "legacy/",
    # Self (bu dosya — allowlist kendisi)
    "scripts/arch_guard_llm_imports.py",
}
MAX_ALLOWLIST_ENTRIES = 6

# ─────────────────────────────────────────────────────────────────────────
# DEBT REGISTER — mevcut ihlaller. Bu liste SADECE küçültülebilir.
# Yeni ihlal tespit edilirse (dosya burada değilse) CI kırılır.
# Bir dosyayı kaldırmak için: ya gateway'e taşı, ya import'u sil, ya ADR'de
# kabul edildiğini açıkla. Liste büyüdüğünde PR reddedilir.
# ─────────────────────────────────────────────────────────────────────────
DEBT_REGISTER: Set[str] = set()
MAX_DEBT_REGISTER_ENTRIES = 0

# Forbidden import patterns
_PATTERNS = [
    re.compile(r"^\s*from\s+openai\s+import\b"),
    re.compile(r"^\s*import\s+openai\b"),
    re.compile(r"^\s*from\s+anthropic\s+import\b"),
    re.compile(r"^\s*import\s+anthropic\b"),
]


def is_allowed(rel_path: str) -> bool:
    """Dosya ALLOWLIST'te veya bir prefix eşleşmesindeyse izinli."""
    for allowed in ALLOWLIST:
        if allowed.endswith("/"):
            if rel_path.startswith(allowed):
                return True
        elif rel_path == allowed:
            return True
    return False


def scan_file(path: Path, rel: str) -> List[str]:
    """Bu dosyada yasak import var mı? Hata mesajlarını döndür."""
    errors: List[str] = []
    try:
        with path.open("r", encoding="utf-8", errors="replace") as fh:
            for lineno, line in enumerate(fh, 1):
                for pat in _PATTERNS:
                    if pat.match(line):
                        errors.append(f"{rel}:{lineno}: {line.rstrip()}")
    except OSError:
        pass
    return errors


_SKIP_DIRS = {
    ".venv", "venv", ".git", ".claude", ".claire", ".cursor", ".idea",
    ".vscode", ".pytest_cache", ".pw-browsers", "node_modules",
    "__pycache__", "dist", "build", "allure-report", "allure-results",
}


def _should_skip(path: Path) -> bool:
    if any(part in _SKIP_DIRS for part in path.parts):
        return True
    # Local Codex/worktree snapshots can contain another full repo copy. They
    # are not production source and make the guard double-count stale imports.
    return any("-wt-" in part for part in path.parts)


def main() -> int:
    repo = Path(__file__).resolve().parent.parent
    py_files = [p for p in repo.rglob("*.py") if not _should_skip(p)]

    violations: List[str] = []  # allowed/debt olmayan ihlaller
    debt_hits: Set[str] = set()  # debt register'da kalan gerçekten kullanılan dosyalar

    for py in py_files:
        rel = str(py.relative_to(repo))
        errors = scan_file(py, rel)
        if not errors:
            continue

        if is_allowed(rel):
            continue

        if rel in DEBT_REGISTER:
            debt_hits.add(rel)
            continue

        violations.extend(errors)

    # Debt register'da olup artık ihlal etmeyen dosyaları raporla
    # (burn-down fırsatı — allowlist güncellenmeli)
    stale_debt = DEBT_REGISTER - debt_hits

    exit_code = 0

    if len(ALLOWLIST) > MAX_ALLOWLIST_ENTRIES:
        print(
            "\n❌ ALLOWLIST büyüdü — direct LLM import istisna listesi "
            f"{MAX_ALLOWLIST_ENTRIES} kaydı aşamaz"
        )
        exit_code = 1

    if len(DEBT_REGISTER) > MAX_DEBT_REGISTER_ENTRIES:
        print(
            "\n❌ DEBT_REGISTER büyüdü — direct LLM debt listesi sadece küçülebilir"
        )
        exit_code = 1

    if violations:
        print("\n❌ Arch Guard IHLAL — L2 dışında direct LLM SDK import yasak")
        print("─" * 70)
        for v in violations:
            print(f"  {v}")
        print("\nÇözüm yolları:")
        print("  1. backend/app/domains/ai/gateway_client.py kullan (önerilen)")
        print("  2. engine/services/llm_gateway.py üzerinden git")
        print("  3. ai-gateway/'e yeni provider adapter ekle")
        print("\nSadece istisnai durumda: ADR açıp allowlist'e ekle.")
        exit_code = 1

    if stale_debt:
        print("\n⚠️  DEBT REGISTER güncellenebilir — artık import etmiyor:")
        for d in sorted(stale_debt):
            print(f"  {d}")
        print("\nBu dosyaları DEBT_REGISTER listesinden kaldır (burn-down).")
        # Bu uyarı, CI'ı KIRAR değil (opt-in improvement).

    if debt_hits:
        print(f"\nℹ️  Debt register: {len(debt_hits)} dosya hâlâ direct import kullanıyor")
        print("   (hedef: her ay en az 1 dosya gateway'e taşı)")

    if exit_code == 0 and not stale_debt:
        print("✅ Arch Guard temiz — direct LLM import ihlali yok")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
