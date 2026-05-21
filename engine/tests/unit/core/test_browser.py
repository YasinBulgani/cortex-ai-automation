
import pytest
from unittest.mock import MagicMock, patch, ANY
from core.browser import BrowserEngine

@pytest.fixture
def mock_playwright():
    with patch("core.browser.sync_playwright") as mock:
        # Mock instance structure
        instance = mock.return_value.start.return_value
        
        # Mock browser launcher (chromium, firefox, etc)
        launcher = MagicMock()
        setattr(instance, "chromium", launcher)
        
        # Mock browser
        browser = launcher.launch.return_value
        
        # Mock context
        context = browser.new_context.return_value
        
        # Mock page
        page = context.new_page.return_value
        
        yield {
            "playwright": instance,
            "browser": browser,
            "context": context,
            "page": page
        }

def test_browser_engine_lifecycle(mock_playwright):
    """Tarayıcı başlatma ve durdurma döngüsini test eder."""
    engine = BrowserEngine(browser_type="chromium", headless=True)
    
    engine.start()
    assert engine._browser is not None
    assert engine.page is not None
    
    engine.stop()
    mock_playwright["browser"].close.assert_called_once()
    mock_playwright["playwright"].stop.assert_called_once()

def test_browser_engine_context_manager(mock_playwright):
    """Context manager (with bloğu) kullanımını test eder."""
    with BrowserEngine() as engine:
        assert engine.page is not None
    
    mock_playwright["browser"].close.assert_called_once()

def test_uninitialized_page_access():
    """Başlatılmamış motor üzerinden page erişimini test eder."""
    engine = BrowserEngine()
    with pytest.raises(RuntimeError, match="başlatılmadı"):
        _ = engine.page

def test_navigate(mock_playwright):
    """Navigasyon fonksiyonunu test eder."""
    engine = BrowserEngine()
    engine.start()
    engine.navigate("https://test.com")
    
    mock_playwright["page"].goto.assert_called_with(
        "https://test.com", 
        wait_until="domcontentloaded", 
        timeout=ANY
    )
