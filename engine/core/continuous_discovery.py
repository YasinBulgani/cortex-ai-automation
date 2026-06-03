"""
Sürekli Arka Plan Test Üretimi (Checksum tarzı)
═══════════════════════════════════════════════════════════════════════════

Tetiklemeli ``auto_discovery``'nin üstüne **always-on** bir döngü kurar:
periyodik olarak hedef uygulamaları crawl edip yeni akışları keşfeder ve
SADECE daha önce görülmemiş olanları üretir/kalıcılaştırır.

Anahtar fark: **dedup**. Her akış normalize edilip imzalanır; kalıcı bir
registry'de tutulur. Böylece döngü aynı testleri tekrar tekrar üretmez —
yalnızca uygulama değiştikçe ortaya çıkan YENİ akışları ekler.

``_flow_signature`` ve registry işlemleri SAF/dosya-tabanlıdır (browser'sız
test edilebilir). Döngü daemon thread'de çalışır (interruptible).
"""
from __future__ import annotations

import hashlib
import json
import logging
import threading
from pathlib import Path

logger = logging.getLogger(__name__)

_REGISTRY_PATH = Path(__file__).resolve().parent.parent / "reports" / "continuous_discovery_registry.json"


# ═══════════════════════════════════════════════════════════════════════════
# SAF: imza + registry (browser'sız test edilebilir)
# ═══════════════════════════════════════════════════════════════════════════

def _flow_signature(flow: dict) -> str:
    """Bir akıştan deterministik dedup imzası üretir.

    Adımların (action, normalize-target) dizisinden hash. Değerler (value)
    dahil edilmez — aynı akış farklı test-verisiyle tekrar üretilmesin.
    """
    parts = []
    for step in flow.get("steps", []) or []:
        action = str(step.get("action", "")).strip().lower()
        target = str(step.get("target", "")).strip().lower()
        parts.append(f"{action}:{target}")
    base = str(flow.get("title", "")).strip().lower() + "|" + "→".join(parts)
    return hashlib.sha256(base.encode("utf-8")).hexdigest()[:16]


def load_registry(path: Path | None = None) -> dict:
    """Görülen akış imzalarını yükler ({signature: {title, first_seen_cycle, target}})."""
    p = path or _REGISTRY_PATH
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.warning("Registry okunamadı: %s", exc)
    return {}


def save_registry(registry: dict, path: Path | None = None) -> None:
    p = path or _REGISTRY_PATH
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(registry, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as exc:
        logger.warning("Registry yazılamadı: %s", exc)


def filter_new_flows(flows: list[dict], registry: dict) -> tuple[list[dict], list[dict]]:
    """Akışları (yeni, zaten_görülen) olarak ayırır — imza dedup'ı."""
    new, seen = [], []
    for fl in flows:
        sig = _flow_signature(fl)
        fl["signature"] = sig
        (seen if sig in registry else new).append(fl)
    return new, seen


# ═══════════════════════════════════════════════════════════════════════════
# Döngü çekirdeği: tek tur
# ═══════════════════════════════════════════════════════════════════════════

def run_cycle(
    targets: list[str],
    max_pages: int = 8,
    max_flows: int = 6,
    cycle_index: int = 0,
    persist: bool = True,
) -> dict:
    """Tüm hedefler için bir keşif turu çalıştırır; sadece YENİ akışları üretir.

    Dönüş: tur özeti (hedef başına yeni/dedup sayıları + toplam).
    """
    from core.auto_discovery import run_discovery

    registry = load_registry()
    per_target = []
    total_new = 0
    total_dedup = 0

    for url in targets:
        try:
            # persist=False: önce dedup, sonra sadece yeni olanları kalıcılaştır
            result = run_discovery(url, max_pages=max_pages, max_flows=max_flows, persist=False)
            flows = result.get("flows", [])
            new_flows, seen_flows = filter_new_flows(flows, registry)

            persisted = 0
            for fl in new_flows:
                registry[fl["signature"]] = {
                    "title": fl["title"], "target": url, "first_seen_cycle": cycle_index,
                }
                if persist:
                    try:
                        from core.auto_discovery import persist_flow
                        fl["test_id"] = persist_flow(fl)
                        persisted += 1
                    except Exception as exc:
                        logger.warning("Sürekli keşif persist hatası: %s", exc)

            total_new += len(new_flows)
            total_dedup += len(seen_flows)
            per_target.append({
                "target": url, "crawled_pages": result.get("pages_crawled", 0),
                "new_flows": len(new_flows), "deduped": len(seen_flows), "persisted": persisted,
            })
        except Exception as exc:
            logger.warning("Sürekli keşif hedef hatası (%s): %s", url, exc)
            per_target.append({"target": url, "error": str(exc)})

    save_registry(registry)
    return {
        "cycle": cycle_index,
        "targets": per_target,
        "total_new": total_new,
        "total_deduped": total_dedup,
        "registry_size": len(registry),
    }


# ═══════════════════════════════════════════════════════════════════════════
# Daemon döngü (always-on)
# ═══════════════════════════════════════════════════════════════════════════

class ContinuousDiscovery:
    """Arka planda periyodik keşif çalıştıran tekil yönetici."""

    def __init__(self):
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self.config: dict = {}
        self.last_cycle: dict | None = None
        self.cycle_count = 0
        self.running = False

    def start(self, targets: list[str], interval_minutes: int = 60,
              max_pages: int = 8, max_flows: int = 6) -> dict:
        with self._lock:
            if self.running:
                return {"status": "already_running", "config": self.config}
            if not targets:
                raise ValueError("En az bir hedef URL gerekli")
            self.config = {
                "targets": targets, "interval_minutes": max(1, int(interval_minutes)),
                "max_pages": max_pages, "max_flows": max_flows,
            }
            self._stop.clear()
            self.running = True
            self._thread = threading.Thread(target=self._loop, daemon=True, name="continuous-discovery")
            self._thread.start()
            logger.info("Sürekli keşif başlatıldı: %s hedef, %sdk", len(targets), interval_minutes)
            return {"status": "started", "config": self.config}

    def stop(self) -> dict:
        with self._lock:
            if not self.running:
                return {"status": "not_running"}
            self._stop.set()
            self.running = False
            logger.info("Sürekli keşif durduruldu")
            return {"status": "stopped", "cycles_completed": self.cycle_count}

    def status(self) -> dict:
        return {
            "running": self.running,
            "config": self.config,
            "cycle_count": self.cycle_count,
            "last_cycle": self.last_cycle,
            "registry_size": len(load_registry()),
        }

    def _loop(self) -> None:
        interval_sec = self.config["interval_minutes"] * 60
        while not self._stop.is_set():
            self.cycle_count += 1
            try:
                self.last_cycle = run_cycle(
                    self.config["targets"],
                    max_pages=self.config["max_pages"],
                    max_flows=self.config["max_flows"],
                    cycle_index=self.cycle_count,
                    persist=True,
                )
                logger.info("Sürekli keşif tur %s: %s yeni akış",
                            self.cycle_count, self.last_cycle.get("total_new"))
            except Exception as exc:
                logger.exception("Sürekli keşif tur hatası: %s", exc)
            # Interruptible bekleme
            self._stop.wait(interval_sec)


# Tekil yönetici
_manager: ContinuousDiscovery | None = None


def get_manager() -> ContinuousDiscovery:
    global _manager
    if _manager is None:
        _manager = ContinuousDiscovery()
    return _manager
