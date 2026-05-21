"""BGTS DSL Python Loader.

packages/dsl/catalog/*.yaml'dan okunan cümlecikleri pytest-bdd step'leri olarak
kaydeder. Her cümlecik için bir Python implementation referansı çağrılır.

Kullanım (örn. conftest.py içinde):
    from packages.dsl.loaders.python import register_catalog
    register_catalog()
"""
from .loader import register_catalog, load_catalog, CatalogBinding

__all__ = ["register_catalog", "load_catalog", "CatalogBinding"]
