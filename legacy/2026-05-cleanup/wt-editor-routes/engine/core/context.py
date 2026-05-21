"""
core/context.py — Test Adimlari Arasi Veri Paylasimi

Senaryolar ve adimlar arasinda dinamik test verisini saklar.
Hem TestwrightAI {var} hem de MaviYaka @var placeholder syntax'ini destekler.

Ayrica DataReader verilerini de cozumleme zincirine dahil eder:
  1. Oncelik: GlobalContext._data (adim icerisinde set edilen degerler)
  2. Fallback: DataReader._data (JSON dosyasindan yuklenen degerler)
"""
import re


class GlobalContext:
    """
    Adimlar arasi dinamik test verisi deposu.
    Thread-safe degil; pytest-bdd tek thread'de calisir.
    """
    _data: dict[str, str] = {}

    @classmethod
    def set_value(cls, key: str, value: str):
        cls._data[key] = value

    @classmethod
    def get_value(cls, key: str, default: str = "") -> str:
        return cls._data.get(key, default)

    @classmethod
    def has(cls, key: str) -> bool:
        return key in cls._data

    @classmethod
    def render(cls, text: str) -> str:
        """
        Metindeki placeholder'lari cozumler.

        Desteklenen syntax'lar:
          {VAR_NAME}  — TestwrightAI mevcut pattern
          @var_name   — MaviYaka pattern (tek kelime, @ ile baslar)

        Cozumleme sirasi:
          1. GlobalContext._data
          2. DataReader._data (import edilmisse)
        """
        if not isinstance(text, str):
            return text

        # {var} syntax'i
        def repl_brace(match):
            key = match.group(1)
            val = cls._data.get(key)
            if val is not None:
                return str(val)
            val = cls._try_data_reader(key)
            if val is not None:
                return str(val)
            return match.group(0)

        text = re.sub(r'\{([^}]+)\}', repl_brace, text)

        # @var syntax'i (NexusQA uyumlulugu)
        def repl_at(match):
            key = match.group(1)
            val = cls._data.get(key)
            if val is not None:
                return str(val)
            val = cls._try_data_reader(key)
            if val is not None:
                return str(val)
            return match.group(0)

        text = re.sub(r'@(\w+)', repl_at, text)

        return text

    @classmethod
    def clear(cls):
        cls._data.clear()

    @classmethod
    def as_dict(cls) -> dict[str, str]:
        return dict(cls._data)

    @classmethod
    def _try_data_reader(cls, key: str):
        """DataReader'dan deger almaya calisir (import hatasini yutarak)."""
        try:
            from core.data_reader import DataReader
            val = DataReader.get(key)
            if val:
                return val
        except Exception:
            pass
        return None
