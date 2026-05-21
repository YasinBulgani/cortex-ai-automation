"""
Yardımcı fonksiyonlar modülü.

Testlerde kullanılan yaygın yardımcı fonksiyonları içerir.
"""

import random
import string
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Callable, Any
from faker import Faker


logger = logging.getLogger(__name__)


def generate_random_string(length: int = 10) -> str:
    """
    Rastgele karakter dizesi oluştur.

    Parametreler:
        length (int): Oluşturulacak dizinin uzunluğu

    Dönüş:
        str: Rastgele karakter dizisi
    """
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


def generate_random_email() -> str:
    """
    Rastgele e-posta adresi oluştur.

    Dönüş:
        str: Rastgele e-posta adresi
    """
    fake = Faker('tr_TR')
    return fake.email()


def generate_random_phone() -> str:
    """
    Rastgele telefon numarası oluştur.

    Dönüş:
        str: Rastgele telefon numarası
    """
    fake = Faker('tr_TR')
    return fake.phone_number()


async def wait_and_retry(
    func: Callable,
    retries: int = 3,
    delay: float = 1.0,
    *args,
    **kwargs
) -> Any:
    """
    Fonksiyonu belirtilen sayıda tekrar dene.

    Parametreler:
        func (Callable): Çalıştırılacak fonksiyon
        retries (int): Deneme sayısı
        delay (float): Denemeler arasındaki gecikme (saniye)
        *args: Fonksiyon için pozisyonel argümanlar
        **kwargs: Fonksiyon için anahtar sözcük argümanları

    Dönüş:
        Any: Fonksiyonun dönüş değeri

    Yükseltir:
        Exception: Tüm denemeler başarısız olursa
    """
    for attempt in range(retries):
        try:
            logger.info(f"Deneme {attempt + 1}/{retries}: {func.__name__}")
            return await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
        except Exception as e:
            if attempt == retries - 1:
                logger.error(f"Tüm denemeler başarısız oldu: {func.__name__}")
                raise
            logger.warning(f"Deneme başarısız oldu, {delay} saniye bekle ve yeniden dene")
            await asyncio.sleep(delay)


async def take_screenshot(page, name: str) -> None:
    """
    Sayfanın screenshot'ını al.

    Parametreler:
        page: Sayfa nesnesi
        name (str): Screenshot adı
    """
    try:
        screenshot_path = Path('screenshots') / f"{name}.png"
        screenshot_path.parent.mkdir(parents=True, exist_ok=True)
        await page.screenshot(path=str(screenshot_path))
        logger.info(f"Screenshot kaydedildi: {screenshot_path}")
    except Exception as e:
        logger.error(f"Screenshot alma hatası: {e}")


def read_test_data(file_path: str) -> dict:
    """
    Test verilerini dosyadan oku.

    Parametreler:
        file_path (str): Test veri dosyasının yolu

    Dönüş:
        dict: Test verileri
    """
    import json

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Test veri okuma hatası: {e}")
        return {}


def format_datetime(dt: datetime = None, fmt: str = '%Y-%m-%d %H:%M:%S') -> str:
    """
    Tarih-saati formatlı string'e dönüştür.

    Parametreler:
        dt (datetime): Dönüştürülecek tarih-saat
        fmt (str): Tarih-saat formatı

    Dönüş:
        str: Formatlı tarih-saat string'i
    """
    if dt is None:
        dt = datetime.now()

    return dt.strftime(fmt)


def get_current_timestamp() -> str:
    """
    Geçerli zaman damgasını al.

    Dönüş:
        str: Zaman damgası (ISO 8601 formatında)
    """
    return datetime.now().isoformat()
