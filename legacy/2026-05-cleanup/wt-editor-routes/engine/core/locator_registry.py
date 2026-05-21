"""
Locator Registry — Merkezi seçici yönetimi ve self-healing desteği.

Her element için birden fazla seçici adayı (selector chain) tutarak
playback sırasında otomatik fallback ve self-healing sağlar.

Kullanım:
    registry = LocatorRegistry()
    registry.register("login_submit", SelectorChain([
        SelectorCandidate("testid", '[data-testid="login-btn-submit"]', 1.0, True),
        SelectorCandidate("role",   'button >> text="Giriş Yap"',      0.95, True),
        SelectorCandidate("css",    'button[type="submit"]',            0.6,  False),
    ]), page_url="/login")

    resolved = registry.resolve("login_submit", page)
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class SelectorCandidate:
    """Tek bir seçici adayı."""
    type: str           # testid, role, label, css, xpath, text
    value: str
    confidence: float   # 0.0 — 1.0
    stable: bool        # UI değişikliklerinde kırılma riski düşük mü?

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> SelectorCandidate:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class SelectorChain:
    """Bir element için sıralı seçici zinciri."""
    candidates: list[SelectorCandidate] = field(default_factory=list)

    def __post_init__(self):
        self.candidates.sort(key=lambda c: -c.confidence)

    @property
    def primary(self) -> SelectorCandidate | None:
        return self.candidates[0] if self.candidates else None

    @property
    def fallbacks(self) -> list[SelectorCandidate]:
        return self.candidates[1:]

    def add(self, candidate: SelectorCandidate):
        self.candidates.append(candidate)
        self.candidates.sort(key=lambda c: -c.confidence)

    def to_list(self) -> list[dict]:
        return [c.to_dict() for c in self.candidates]

    @classmethod
    def from_list(cls, items: list[dict]) -> SelectorChain:
        return cls([SelectorCandidate.from_dict(i) for i in items])


@dataclass
class LocatorEntry:
    """Registry'deki tek bir element kaydı."""
    name: str
    chain: SelectorChain
    page_url: str = ""
    screen: str = ""
    element_type: str = ""
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "chain": self.chain.to_list(),
            "page_url": self.page_url,
            "screen": self.screen,
            "element_type": self.element_type,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: dict) -> LocatorEntry:
        return cls(
            name=d["name"],
            chain=SelectorChain.from_list(d.get("chain", [])),
            page_url=d.get("page_url", ""),
            screen=d.get("screen", ""),
            element_type=d.get("element_type", ""),
            metadata=d.get("metadata", {}),
        )


class LocatorRegistry:
    """
    Merkezi locator deposu.

    Tüm ekranların element seçicilerini tutar ve
    resolve sırasında selector chain üzerinde cascade yapar.
    """

    def __init__(self):
        self._entries: dict[str, LocatorEntry] = {}
        self._heal_log: list[dict] = []

    # ── Kayıt ──────────────────────────────────────────────────────────────
    def register(
        self,
        name: str,
        chain: SelectorChain,
        page_url: str = "",
        screen: str = "",
        element_type: str = "",
        metadata: dict | None = None,
    ):
        self._entries[name] = LocatorEntry(
            name=name,
            chain=chain,
            page_url=page_url,
            screen=screen,
            element_type=element_type,
            metadata=metadata or {},
        )

    def unregister(self, name: str):
        self._entries.pop(name, None)

    def get(self, name: str) -> LocatorEntry | None:
        return self._entries.get(name)

    def get_by_screen(self, screen: str) -> list[LocatorEntry]:
        return [e for e in self._entries.values() if e.screen == screen]

    @property
    def all_entries(self) -> list[LocatorEntry]:
        return list(self._entries.values())

    # ── Çözümleme (Resolve) ────────────────────────────────────────────────
    def resolve(self, name: str, page: Any = None) -> str:
        """
        Verilen element adı için en iyi çalışan seçiciyi döner.

        page verilmişse (Playwright Page), her aday canlı DOM'da denenip
        ilk bulunan döndürülür (self-healing cascade).
        page None ise, en yüksek güvenli adayın değeri döner.
        """
        entry = self._entries.get(name)
        if not entry:
            return name

        if page is None:
            primary = entry.chain.primary
            return primary.value if primary else name

        for candidate in entry.chain.candidates:
            try:
                selector = self._to_playwright_selector(candidate)
                if page.locator(selector).count() > 0:
                    if candidate != entry.chain.primary:
                        self._log_heal(name, entry.chain.primary, candidate)
                    return selector
            except Exception:
                continue

        logger.warning("Locator '%s': tüm adaylar başarısız", name)
        primary = entry.chain.primary
        return primary.value if primary else name

    @staticmethod
    def _to_playwright_selector(candidate: SelectorCandidate) -> str:
        """SelectorCandidate'i Playwright uyumlu seçiciye dönüştürür."""
        if candidate.type == "testid":
            tid = candidate.value
            if tid.startswith("[data-testid="):
                tid = tid.split('"')[1]
            return f'[data-testid="{tid}"]'
        if candidate.type == "role":
            return candidate.value
        return candidate.value

    def _log_heal(self, name: str, original: SelectorCandidate | None, healed: SelectorCandidate):
        entry = {
            "element": name,
            "original_type": original.type if original else "none",
            "original_value": original.value if original else "",
            "healed_type": healed.type,
            "healed_value": healed.value,
        }
        self._heal_log.append(entry)
        logger.info(
            "Self-heal: '%s' | %s -> %s",
            name,
            original.value if original else "none",
            healed.value,
        )

    @property
    def heal_log(self) -> list[dict]:
        return list(self._heal_log)

    # ── Persistence ────────────────────────────────────────────────────────
    def save(self, path: Path | str):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {name: entry.to_dict() for name, entry in self._entries.items()}
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        logger.info("Registry kaydedildi: %s (%d entry)", path, len(data))

    def load(self, path: Path | str):
        path = Path(path)
        if not path.exists():
            logger.warning("Registry dosyası bulunamadı: %s", path)
            return
        data = json.loads(path.read_text(encoding="utf-8"))
        for name, entry_dict in data.items():
            self._entries[name] = LocatorEntry.from_dict(entry_dict)
        logger.info("Registry yüklendi: %s (%d entry)", path, len(data))

    # ── DB Entegrasyonu ────────────────────────────────────────────────────
    def sync_from_db(self):
        """Engine SQLite object_repository tablosundan mevcut locator'ları yükler."""
        try:
            from core.db import get_locators
            for loc in get_locators():
                name = loc["name"]
                if name not in self._entries:
                    chain = SelectorChain([
                        SelectorCandidate(
                            type="css" if not loc["locator_value"].startswith("//") else "xpath",
                            value=loc["locator_value"],
                            confidence=0.7,
                            stable=False,
                        )
                    ])
                    self.register(
                        name=name,
                        chain=chain,
                        page_url=loc.get("page_url", ""),
                    )
        except Exception as exc:
            logger.warning("DB sync başarısız: %s", exc)

    def sync_to_db(self):
        """Registry'deki primary seçicileri object_repository tablosuna yazar."""
        try:
            from core.db import save_locator
            for entry in self._entries.values():
                primary = entry.chain.primary
                if primary:
                    save_locator(entry.name, primary.value, entry.page_url)
        except Exception as exc:
            logger.warning("DB sync başarısız: %s", exc)

    # ── İstatistikler ──────────────────────────────────────────────────────
    def stats(self) -> dict:
        total = len(self._entries)
        by_screen = {}
        by_type = {}
        fragile = 0

        for entry in self._entries.values():
            screen = entry.screen or "unknown"
            by_screen[screen] = by_screen.get(screen, 0) + 1

            primary = entry.chain.primary
            if primary:
                by_type[primary.type] = by_type.get(primary.type, 0) + 1
                if not primary.stable:
                    fragile += 1

        return {
            "total": total,
            "by_screen": by_screen,
            "by_primary_type": by_type,
            "fragile_count": fragile,
            "heal_count": len(self._heal_log),
        }
