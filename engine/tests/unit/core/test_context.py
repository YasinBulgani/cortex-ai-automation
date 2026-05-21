
import pytest
from core.context import GlobalContext

@pytest.fixture(autouse=True)
def clean_context():
    """Her testten önce context'i temizler."""
    GlobalContext.clear()
    yield
    GlobalContext.clear()

def test_set_get_value():
    """Değer atama ve okuma işlemini test eder."""
    GlobalContext.set_value("token", "abc-123")
    assert GlobalContext.get_value("token") == "abc-123"
    assert GlobalContext.get_value("non-existent", "default") == "default"

def test_render_string():
    """String içerisindeki değişkenlerin yerleştirilmesini test eder."""
    GlobalContext.set_value("username", "yasin")
    GlobalContext.set_value("order_id", "555")
    
    text = "Merhaba {username}, sipariş numaranız: {order_id}."
    rendered = GlobalContext.render(text)
    
    assert rendered == "Merhaba yasin, sipariş numaranız: 555."

def test_render_with_missing_keys():
    """Olmayan anahtarların render edilmesini test eder (Olduğu gibi kalmalı)."""
    GlobalContext.set_value("a", "1")
    
    text = "{a} ve {b}"
    rendered = GlobalContext.render(text)
    
    # {b} veritabanında/context'te yoksa olduğu gibi kalmalı veya boş string olmalı?
    # Mevcut kodda match.group(0) yani {b} kalıyor.
    assert rendered == "1 ve {b}"

def test_clear_context():
    """Context temizleme işlemini test eder."""
    GlobalContext.set_value("x", "y")
    GlobalContext.clear()
    assert GlobalContext.get_value("x") == ""
