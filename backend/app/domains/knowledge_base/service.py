"""Knowledge base service.

In-memory CRUD for articles. Production'da DB table + full-text search index.
"""

from __future__ import annotations

import re
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional


@dataclass
class Article:
    id: str
    title: str
    body: str  # markdown
    tags: List[str] = field(default_factory=list)
    category: str = "general"
    author_id: str = ""
    author_name: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    view_count: int = 0
    helpful_count: int = 0
    unhelpful_count: int = 0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "body": self.body,
            "tags": list(self.tags),
            "category": self.category,
            "author_id": self.author_id,
            "author_name": self.author_name,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "view_count": self.view_count,
            "helpful_count": self.helpful_count,
            "unhelpful_count": self.unhelpful_count,
        }


_STORE: Dict[str, Article] = {}


def create_article(
    *,
    title: str,
    body: str,
    author_id: str,
    author_name: str = "",
    tags: Optional[List[str]] = None,
    category: str = "general",
) -> Article:
    if not title.strip() or not body.strip():
        raise ValueError("title ve body zorunlu")
    aid = "a-" + secrets.token_urlsafe(8)
    article = Article(
        id=aid,
        title=title.strip(),
        body=body.strip(),
        author_id=author_id,
        author_name=author_name,
        tags=tags or [],
        category=category,
    )
    _STORE[aid] = article
    return article


def get_article(article_id: str, *, increment_views: bool = True) -> Optional[Article]:
    article = _STORE.get(article_id)
    if article and increment_views:
        article.view_count += 1
    return article


def list_articles(
    *,
    category: Optional[str] = None,
    tag: Optional[str] = None,
    sort: str = "newest",  # newest | popular | helpful
) -> List[Article]:
    items = list(_STORE.values())
    if category:
        items = [a for a in items if a.category == category]
    if tag:
        items = [a for a in items if tag in a.tags]
    if sort == "popular":
        items.sort(key=lambda a: -a.view_count)
    elif sort == "helpful":
        items.sort(key=lambda a: -(a.helpful_count - a.unhelpful_count))
    else:  # newest
        items.sort(key=lambda a: a.created_at, reverse=True)
    return items


def update_article(
    article_id: str,
    actor_id: str,
    *,
    title: Optional[str] = None,
    body: Optional[str] = None,
    tags: Optional[List[str]] = None,
    category: Optional[str] = None,
    is_admin: bool = False,
) -> Optional[Article]:
    article = _STORE.get(article_id)
    if article is None:
        return None
    if article.author_id != actor_id and not is_admin:
        raise PermissionError("Sadece yazar veya admin düzenleyebilir")
    if title is not None:
        article.title = title.strip()
    if body is not None:
        article.body = body.strip()
    if tags is not None:
        article.tags = tags
    if category is not None:
        article.category = category
    article.updated_at = datetime.now(timezone.utc)
    return article


def delete_article(article_id: str, actor_id: str, *, is_admin: bool = False) -> bool:
    article = _STORE.get(article_id)
    if article is None:
        return False
    if article.author_id != actor_id and not is_admin:
        raise PermissionError("Sadece yazar veya admin silebilir")
    del _STORE[article_id]
    return True


def search(query: str, *, limit: int = 20) -> List[Article]:
    """Naive substring + tag search; production'da Elastic/Tantivy."""
    if not query.strip():
        return []
    q = query.lower().strip()
    matches: list[tuple[float, Article]] = []
    for a in _STORE.values():
        score = 0.0
        if q in a.title.lower():
            score += 5.0
        if q in a.body.lower():
            score += 1.0
        for tag in a.tags:
            if q == tag.lower():
                score += 3.0
            elif q in tag.lower():
                score += 1.5
        if score > 0:
            matches.append((score, a))
    matches.sort(key=lambda x: (-x[0], -x[1].view_count))
    return [a for _, a in matches[:limit]]


def vote_helpful(article_id: str, helpful: bool) -> Optional[Article]:
    article = _STORE.get(article_id)
    if article is None:
        return None
    if helpful:
        article.helpful_count += 1
    else:
        article.unhelpful_count += 1
    return article


def clear() -> None:
    """Test helper."""
    _STORE.clear()


_SEED_ARTICLES = [
    {
        "title": "Neurex QA'ya Hoş Geldiniz",
        "category": "getting-started",
        "tags": ["başlangıç", "temel"],
        "body": """# Neurex QA'ya Hoş Geldiniz

Neurex QA, Türkçe doğal dilden uçtan uca test otomasyonuna giden AI destekli platformdur.

## Hızlı Başlangıç
1. **Proje oluştur** → Sağ üstten yeni proje açın
2. **Senaryo yaz** → Türkçe yazın; sistem Gherkin'e çevirir
3. **Çalıştır** → Tek tıkla Playwright/Appium ile koşturun
4. **İzle** → Self-healing locator + flaky tespit otomatik çalışır
""",
    },
    {
        "title": "Türkçe Senaryo Yazma Rehberi",
        "category": "authoring",
        "tags": ["senaryo", "gherkin", "bdd"],
        "body": """# Türkçe Senaryo Yazma Rehberi

## Temel Yapı
```
Senaryo: Kullanıcı giriş yapar
  Verildiği gibi kullanıcı giriş sayfasındadır
  Eğer e-posta ve şifreyi doğru girer
  O zaman ana sayfaya yönlendirilir
```

## İpuçları
- Tek senaryo = tek davranış
- Veri varyasyonları için **Senaryo Şablonu** kullanın
- AI üretim için "AI'dan üret" butonu — doğal dilde anlatın yeter
""",
    },
    {
        "title": "Self-Healing Locator Sistemi",
        "category": "execution",
        "tags": ["healing", "locator", "ai"],
        "body": """# Self-Healing Locator

Bir test seçici (locator) artık çalışmadığında Healer ajan devreye girer:

1. **DOM analizi** — değişen element tespit edilir
2. **Aday üretimi** — alternatif seçiciler skorlanır
3. **Otomatik PR** — GitHub'a düzeltme PR'ı açılır
4. **Onay akışı** — siz onaylayana kadar merge edilmez

## Stability Score
Her locator için 0-100 arası kararlılık skoru. 60 altı → riskli, refactor önerilir.
""",
    },
    {
        "title": "Flaky Test Tespiti ve Karantina",
        "category": "execution",
        "tags": ["flaky", "karantina", "ml"],
        "body": """# Flaky Test Tespiti

Predictive flaky ML modeli, son N koşumdaki başarı/başarısızlık desenini izler.

- **Flake skoru ≥ 0.7** → Otomatik karantinaya alınır (auto-quarantine)
- **Karantinadaki testler** → CI gate'i bloklamaz, raporda ayrı listelenir
- **Tek tık çıkış** — manuel çözüm sonrası karantinadan çıkarın

İlgili: [[locator-stability]], [[execution-best-practices]]
""",
    },
    {
        "title": "AI Pipeline: Analyze → Iterate",
        "category": "ai",
        "tags": ["pipeline", "agents", "ai"],
        "body": """# AI Pipeline'ı

9 ajan, 6 aşamalı pipeline:

| Aşama | Ajanlar | Ne Yapar |
|------|---------|----------|
| Analyze | Analyst, Explorer | Gereksinim + sayfa keşfi |
| Design | Scenario, Coder | Senaryo + kod üretimi |
| Data | (Locator) | Test verisi parametrize |
| Execute | Runner | Playwright/Appium koşumu |
| Observe | Healer, Reviewer | Self-heal + smell tespiti |
| Iterate | Reporter | Trend + öneri |

`/p/{projectId}/pipeline` sayfasından canlı durumu izleyin.
""",
    },
    {
        "title": "Klavye Kısayolları",
        "category": "productivity",
        "tags": ["kısayol", "verimlilik"],
        "body": """# Klavye Kısayolları

| Kısayol | İşlev |
|---------|-------|
| ⌘K / Ctrl+K | Komut paleti |
| ⌘J / Ctrl+J | AI asistan |
| g s | Senaryolara git |
| g r | Çalıştırmalara git |
| ? | Tüm kısayolları göster |
""",
    },
    {
        "title": "Ekip Çalışması: Yorumlar ve Onaylar",
        "category": "collaboration",
        "tags": ["yorum", "onay", "ekip"],
        "body": """# Ekip İş Birliği

- **Inline yorumlar** — Her senaryo adımına yorum bırakın
- **Onay akışları** — Production'a gitmeden önce reviewer ataması
- **Bildirim merkezi** — Sağ üstte çan ikonu; mention'larınızı görün
- **Aktivite akışı** — Kim, ne zaman, neyi değiştirdi
""",
    },
    {
        "title": "Mobil Test Otomasyonu",
        "category": "mobile",
        "tags": ["mobil", "appium", "ios", "android"],
        "body": """# Mobil Testler

Appium üzerinde iOS + Android paralel.

- **Device picker** — gerçek cihaz veya emulatör seçimi
- **Gesture desteği** — swipe, pinch, long-press
- **BrowserStack/Sauce Labs** entegrasyonu
- **Mobil paralel** — sharding ile 4× hız
""",
    },
]


def seed_default_articles(force: bool = False) -> int:
    """Bootstrap KB with default Turkish articles. Idempotent unless force=True."""
    if _STORE and not force:
        return 0
    if force:
        _STORE.clear()
    for a in _SEED_ARTICLES:
        create_article(
            title=a["title"],
            body=a["body"],
            author_id="system",
            author_name="Neurex QA",
            tags=a.get("tags", []),
            category=a.get("category", "general"),
        )
    return len(_SEED_ARTICLES)
