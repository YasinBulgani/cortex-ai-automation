"""
Test veri modülü.

Testlerde kullanılan örnek veri setlerini içerir.
"""


class TestData:
    """
    Test verileri sınıfı.
    """

    # Geçerli kullanıcı verisi
    valid_users = [
        {
            'username': 'test_user',
            'password': 'Test@123456',
            'email': 'test@example.com'
        },
        {
            'username': 'admin',
            'password': 'Admin@123456',
            'email': 'admin@example.com'
        }
    ]

    # Geçersiz kullanıcı verisi
    invalid_users = [
        {
            'username': '',
            'password': ''
        },
        {
            'username': 'invalid_user',
            'password': 'wrong_password'
        },
        {
            'username': 'test_user',
            'password': ''
        }
    ]

    # Form test verisi
    form_data = [
        {
            'firstname': 'Ahmet',
            'lastname': 'Yılmaz',
            'email': 'ahmet@example.com',
            'phone': '+90 555 123 45 67',
            'message': 'Bu bir test mesajıdır.'
        },
        {
            'firstname': 'Fatma',
            'lastname': 'Kara',
            'email': 'fatma@example.com',
            'phone': '+90 555 987 65 43',
            'message': 'Test mesajı - 2'
        }
    ]

    # Arama sorguları
    search_queries = [
        'Test arama sorgusu 1',
        'Test arama sorgusu 2',
        'Ürün arama',
        'Hizmet arama',
        'Bilgi arama'
    ]

    # Sayfa başlıkları
    page_titles = {
        'home': 'Ana Sayfa',
        'login': 'Giriş',
        'about': 'Hakkımızda',
        'contact': 'İletişim'
    }

    # Error mesajları
    error_messages = {
        'invalid_credentials': 'Geçersiz kullanıcı adı veya şifre',
        'required_field': 'Bu alan gereklidir',
        'invalid_email': 'Geçersiz e-posta adresi',
        'network_error': 'Ağ hatası oluştu'
    }
