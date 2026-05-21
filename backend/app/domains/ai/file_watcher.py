"""
File Watcher — Proje dosyalarını izle, değişince KnowledgeStore'a indexle.

İzlenen dosya türleri:
  - *.feature    → BDD senaryoları
  - *.spec.ts    → E2E testleri
  - docs/*.md    → Dokümanlar

Çalışma:
  - Backend startup'ında arka plan thread'i olarak başlar
  - Her 60 saniyede dosya mtime'larını kontrol eder (polling)
  - Sadece değişen dosyaları yeniden indexler (mtime tabanlı)
  - watchdog kütüphanesi gerekmez — sıfır dependency
"""

from __future__ import annotations

import logging
import os
import threading
import time
from pathlib import Path

logger = logging.getLogger(__name__)

# Polling aralığı (saniye)
POLL_INTERVAL = 60

# İzlenecek kalıplar ve source mapping
WATCH_PATTERNS: dict[str, str] = {
    "*.feature": "feature_file",
    "*.spec.ts": "feature_file",
}
WATCH_DIRS: dict[str, str] = {
    "docs": "docs",
}


class ProjectFileWatcher:
    """Polling-based file watcher — sıfır dependency."""

    def __init__(self, project_root: str | Path | None = None):
        self._root = Path(project_root) if project_root else self._detect_root()
        self._mtimes: dict[str, float] = {}
        self._running = False
        self._thread: threading.Thread | None = None

    @staticmethod
    def _detect_root() -> Path:
        """Proje kökünü bul."""
        return Path(__file__).resolve().parent.parent.parent.parent

    def start(self) -> None:
        """Arka plan thread'i başlat."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True, name="file-watcher")
        self._thread.start()
        logger.info("File watcher başlatıldı (root: %s, interval: %ds)", self._root, POLL_INTERVAL)

    def stop(self) -> None:
        self._running = False

    def _poll_loop(self) -> None:
        """Ana polling döngüsü."""
        # İlk scan: mtime'ları kaydet (indexleme yapma)
        self._initial_scan()

        while self._running:
            time.sleep(POLL_INTERVAL)
            if not self._running:
                break
            try:
                self._check_changes()
            except Exception as e:
                logger.debug("File watcher check hatası: %s", e)

    def _initial_scan(self) -> None:
        """Mevcut dosyaların mtime'larını kaydet."""
        for path in self._collect_files():
            try:
                self._mtimes[str(path)] = path.stat().st_mtime
            except OSError:
                pass
        logger.info("File watcher: %d dosya izleniyor", len(self._mtimes))

    def _check_changes(self) -> None:
        """Değişen ve silinen dosyalari bul ve isle."""
        changed: list[tuple[Path, str]] = []
        current_files: set[str] = set()

        for path in self._collect_files():
            path_str = str(path)
            current_files.add(path_str)
            try:
                mtime = path.stat().st_mtime
            except OSError:
                continue

            old_mtime = self._mtimes.get(path_str)
            if old_mtime is None or mtime > old_mtime:
                # Yeni veya degismis dosya
                source = self._source_for(path)
                changed.append((path, source))
                self._mtimes[path_str] = mtime

        # Silinen dosyalari tespit et
        deleted_paths = set(self._mtimes.keys()) - current_files
        if deleted_paths:
            for dp in deleted_paths:
                del self._mtimes[dp]
            logger.info("File watcher: %d dosya silindi, mtime kayitlari temizlendi", len(deleted_paths))

        if changed:
            self._index_changed(changed)

    def _collect_files(self) -> list[Path]:
        """İzlenecek tüm dosyaları topla."""
        files: list[Path] = []
        for pattern in WATCH_PATTERNS:
            for base in [self._root / "engine" / "features", self._root / "e2e", self._root]:
                if base.exists():
                    files.extend(base.rglob(pattern))
        for dir_name in WATCH_DIRS:
            d = self._root / dir_name
            if d.exists():
                files.extend(d.rglob("*.md"))
        return files

    def _source_for(self, path: Path) -> str:
        """Dosya yolundan KnowledgeStore source'unu belirle."""
        suffix = path.suffix
        name = path.name
        if suffix == ".feature":
            return "feature_file"
        if name.endswith(".spec.ts"):
            return "feature_file"
        if suffix == ".md":
            return "docs"
        return "docs"

    def _index_changed(self, changed: list[tuple[Path, str]]) -> None:
        """Değişen dosyaları KnowledgeStore'a indexle."""
        try:
            from app.domains.ai.knowledge_store import KnowledgeStore
            store = KnowledgeStore(project_id="__system__")

            for path, source in changed:
                try:
                    text = path.read_text(encoding="utf-8", errors="ignore")
                    if len(text.strip()) < 20:
                        continue
                    rel = str(path.relative_to(self._root))
                    store.ingest(
                        text=text[:4000],
                        source=source,
                        metadata={"file": rel, "trigger": "file_watcher"},
                        project_id="__system__",
                    )
                    logger.info("File watcher: indexlendi → %s", rel)
                except Exception as e:
                    logger.debug("File watcher index hatası (%s): %s", path, e)

        except Exception as e:
            logger.warning("File watcher KnowledgeStore bağlantı hatası: %s", e)


# Singleton — startup'ta bir kez oluşturulur
_watcher: ProjectFileWatcher | None = None


def start_file_watcher(project_root: str | Path | None = None) -> None:
    """File watcher'ı başlat (idempotent)."""
    global _watcher
    if _watcher is not None:
        return
    _watcher = ProjectFileWatcher(project_root)
    _watcher.start()


def stop_file_watcher() -> None:
    """File watcher'ı durdur."""
    global _watcher
    if _watcher is not None:
        _watcher.stop()
        _watcher = None
