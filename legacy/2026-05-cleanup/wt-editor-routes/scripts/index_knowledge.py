#!/usr/bin/env python3
"""
index_knowledge.py — Projenin tüm kaynak kodunu KnowledgeStore'a indexle.

Kaynaklar:
  1. BDD .feature dosyaları    → source: feature_file
  2. docs/*.md dokümanları     → source: docs
  3. e2e/*.spec.ts testleri    → source: feature_file
  4. Git commit geçmişi        → source: code_change
  5. Mevcut rapor dosyaları    → source: execution

Chunking stratejisi:
  - Büyük dosyalar 500 karakter'lik parçalara bölünür
  - Her chunk metadata ile etiketlenir (dosya adı, satır aralığı)

Kullanım:
  python scripts/index_knowledge.py                  # Tüm kaynakları indexle
  python scripts/index_knowledge.py --source feature # Sadece feature dosyaları
  python scripts/index_knowledge.py --stats          # İstatistik göster
  python scripts/index_knowledge.py --dry-run        # Kaydetmeden sayıları göster
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

# Backend'e path ekle
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

CHUNK_SIZE = 500  # karakter
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _chunk_text(text: str, chunk_size: int = CHUNK_SIZE) -> list[str]:
    """Metni satır sınırlarında parçalara böl."""
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    lines = text.split("\n")
    current = ""
    for line in lines:
        if len(current) + len(line) + 1 > chunk_size and current:
            chunks.append(current)
            current = line
        else:
            current = current + "\n" + line if current else line
    if current.strip():
        chunks.append(current)
    return chunks


def index_feature_files(store, dry_run: bool = False) -> int:
    """BDD .feature dosyalarını indexle."""
    count = 0
    patterns = [
        PROJECT_ROOT / "engine" / "features",
        PROJECT_ROOT / "e2e",
    ]
    for base in patterns:
        if not base.exists():
            continue
        for f in sorted(base.rglob("*.feature")):
            try:
                text = f.read_text(encoding="utf-8", errors="ignore")
                if len(text.strip()) < 20:
                    continue
                chunks = _chunk_text(text)
                for i, chunk in enumerate(chunks):
                    if not dry_run:
                        store.ingest(
                            text=chunk,
                            source="feature_file",
                            metadata={
                                "file": str(f.relative_to(PROJECT_ROOT)),
                                "chunk": i + 1,
                                "total_chunks": len(chunks),
                            },
                        )
                    count += 1
            except Exception:
                continue
    return count


def index_docs(store, dry_run: bool = False) -> int:
    """docs/ klasöründeki markdown dosyalarını indexle."""
    count = 0
    docs_dir = PROJECT_ROOT / "docs"
    if not docs_dir.exists():
        return 0

    for f in sorted(docs_dir.rglob("*.md")):
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
            if len(text.strip()) < 30:
                continue
            chunks = _chunk_text(text, chunk_size=800)
            for i, chunk in enumerate(chunks):
                if not dry_run:
                    store.ingest(
                        text=chunk,
                        source="docs",
                        metadata={
                            "file": str(f.relative_to(PROJECT_ROOT)),
                            "chunk": i + 1,
                        },
                    )
                count += 1
        except Exception:
            continue
    return count


def index_e2e_specs(store, dry_run: bool = False) -> int:
    """E2E test spec dosyalarından test başlıklarını çıkar."""
    import re
    count = 0
    e2e_dir = PROJECT_ROOT / "e2e"
    if not e2e_dir.exists():
        return 0

    for f in sorted(e2e_dir.rglob("*.spec.ts")):
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
            # test('...') veya it('...') kalıplarını çıkar
            tests = re.findall(r"(?:test|it)\(['\"](.+?)['\"]", text)
            if not tests:
                continue
            summary = f"E2E Testleri ({f.name}):\n" + "\n".join(f"  - {t}" for t in tests[:30])
            if not dry_run:
                store.ingest(
                    text=summary,
                    source="feature_file",
                    metadata={"file": str(f.relative_to(PROJECT_ROOT)), "test_count": len(tests)},
                )
            count += 1
        except Exception:
            continue
    return count


def index_git_log(store, dry_run: bool = False) -> int:
    """Son 50 commit'i indexle."""
    try:
        result = subprocess.run(
            ["git", "log", "--oneline", "-50", "--no-merges", "--format=%h %s"],
            cwd=str(PROJECT_ROOT),
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode != 0:
            return 0

        lines = result.stdout.strip().split("\n")
        if not lines:
            return 0

        # 10'arlı gruplar halinde chunk'la
        chunks = [lines[i:i + 10] for i in range(0, len(lines), 10)]
        count = 0
        for chunk in chunks:
            text = "Son commit'ler:\n" + "\n".join(f"  - {l}" for l in chunk)
            if not dry_run:
                store.ingest(
                    text=text,
                    source="code_change",
                    metadata={"commits": len(chunk)},
                )
            count += 1
        return count
    except Exception:
        return 0


def index_reports(store, dry_run: bool = False) -> int:
    """reports/ klasöründeki JSON raporları özetle."""
    count = 0
    reports_dir = PROJECT_ROOT / "reports"
    if not reports_dir.exists():
        return 0

    for f in sorted(reports_dir.glob("*.json")):
        try:
            data = __import__("json").loads(f.read_text(encoding="utf-8"))
            # Raporun özetini al
            summary_parts = []
            if isinstance(data, dict):
                for key in ["summary", "total", "pass_rate", "status", "scenarios"]:
                    if key in data:
                        val = data[key]
                        if isinstance(val, list):
                            summary_parts.append(f"{key}: {len(val)} öğe")
                        else:
                            summary_parts.append(f"{key}: {val}")
            if summary_parts:
                text = f"Rapor ({f.name}): " + ", ".join(summary_parts)
                if not dry_run:
                    store.ingest(
                        text=text,
                        source="execution",
                        metadata={"file": f.name},
                    )
                count += 1
        except Exception:
            continue
    return count


def show_stats():
    """Mevcut KnowledgeStore istatistiklerini göster."""
    from app.domains.ai.knowledge_store import KnowledgeStore
    store = KnowledgeStore()
    stats = store.stats()
    print(f"\n{'═' * 50}")
    print(f"  KnowledgeStore İstatistikleri")
    print(f"{'═' * 50}")
    print(f"  Toplam kayıt:     {stats.get('total', 0)}")
    print(f"  Embedding model:  {stats.get('embedding_model', '?')}")
    print(f"  Embedding boyut:  {stats.get('embedding_dim', '?')}")
    print()
    for src in stats.get("by_source", []):
        print(f"  {src['source']:20s}  {src['count']:5d} kayıt  (son: {src.get('last_update', '?')})")
    print(f"{'═' * 50}\n")


def main():
    parser = argparse.ArgumentParser(description="Proje bilgisini KnowledgeStore'a indexle")
    parser.add_argument("--source", choices=["feature", "docs", "e2e", "git", "reports", "all"],
                        default="all", help="Hangi kaynağı indexle")
    parser.add_argument("--dry-run", action="store_true", help="Kaydetmeden sayıları göster")
    parser.add_argument("--stats", action="store_true", help="İstatistik göster")
    args = parser.parse_args()

    if args.stats:
        show_stats()
        return

    from app.domains.ai.knowledge_store import KnowledgeStore
    store = KnowledgeStore()

    results = {}
    indexers = {
        "feature": ("BDD Feature dosyaları", index_feature_files),
        "docs": ("Markdown dokümanlar", index_docs),
        "e2e": ("E2E spec testleri", index_e2e_specs),
        "git": ("Git commit geçmişi", index_git_log),
        "reports": ("Rapor dosyaları", index_reports),
    }

    targets = indexers.keys() if args.source == "all" else [args.source]

    print(f"\n{'─' * 50}")
    print(f"  {'DRY RUN — ' if args.dry_run else ''}Proje indexleme başlıyor...")
    print(f"{'─' * 50}\n")

    total = 0
    for key in targets:
        label, fn = indexers[key]
        count = fn(store, dry_run=args.dry_run)
        results[key] = count
        total += count
        marker = "📝" if not args.dry_run else "👀"
        print(f"  {marker} {label:30s} → {count:5d} chunk")

    print(f"\n  {'═' * 40}")
    print(f"  Toplam: {total} chunk {'indexlendi' if not args.dry_run else '(dry-run)'}")
    print(f"  {'═' * 40}\n")


if __name__ == "__main__":
    main()
