"""
Core modulu — AI Web Otomasyon Test Altyapisi

Mevcut moduller:
  - BrowserEngine: Playwright tarayici yonetimi
  - AIEngine: LLM ile test uretimi
  - PageInspector: DOM analizi
  - Reporter: HTML/JSON rapor uretimi

NexusQA'dan port edilen yeni moduller:
  - LocatorManager: JSON locator yukleyici
  - DataReader: Domain/env bazli test verisi okuyucu
  - Actions: Playwright aksiyon sarmalayicilari
  - ExcelReporter: Excel rapor ureticisi
  - GlobalContext: Adimlar arasi veri paylasimi (iyilestirildi)
"""
from .locator_manager import LocatorManager
from .data_reader import DataReader
from .context import GlobalContext

# Playwright/AI bagimliliklari olan moduller lazy import edilir
# boylece sadece LocatorManager/DataReader/Context kullanan
# unit testler tum engine bagimliliklerini gerektirmez
def __getattr__(name):
    _lazy = {
        "BrowserEngine": ".browser",
        "AIEngine": ".ai_engine",
        "PageInspector": ".page_inspector",
        "Reporter": ".reporter",
        "Actions": ".actions",
    }
    if name in _lazy:
        import importlib
        mod = importlib.import_module(_lazy[name], __package__)
        return getattr(mod, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "BrowserEngine",
    "AIEngine",
    "PageInspector",
    "Reporter",
    "LocatorManager",
    "DataReader",
    "Actions",
    "GlobalContext",
]
