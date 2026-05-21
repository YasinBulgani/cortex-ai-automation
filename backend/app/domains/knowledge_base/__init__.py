"""Internal knowledge base — G5 (wiki + how-to + runbook articles)."""
from app.domains.knowledge_base.service import (
    Article,
    create_article,
    delete_article,
    get_article,
    list_articles,
    search,
    update_article,
    clear,
    seed_default_articles,
)

# Auto-seed default articles on import so /kb always has content.
try:
    seed_default_articles()
except Exception:
    pass

__all__ = [
    "Article",
    "create_article",
    "delete_article",
    "get_article",
    "list_articles",
    "search",
    "update_article",
    "clear",
    "seed_default_articles",
]
