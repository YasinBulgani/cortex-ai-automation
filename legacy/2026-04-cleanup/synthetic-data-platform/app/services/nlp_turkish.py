"""
Türkçe Bankacılık NLP Modülü
=============================

Bu modül, Türkçe doğal dil işleme (NLP) araçlarını sentetik bankacılık
verisi platformu için özelleştirilmiş biçimde sunar.

Bileşenler:
    TurkishMorphology  : Kök bulma, normalleştirme, tokenizasyon, stop-word kaldırma.
    BankingDictionary  : 150+ bankacılık teriminden oluşan sözlük ve arama araçları.
    IntentDetector     : Kullanıcı niyeti tespit etme (ÜRET, ANALİZ, DIŞA_AKTAR…).
    EntityExtractor    : Metin içinden tutar, tarih, hesap türü, para birimi çıkarma.
    ContextTracker     : Çok turlu konuşma bağlamı yönetimi.
    TurkishBankingNLP  : Tüm bileşenleri birleştiren ana boru hattı.

Bağımlılıklar:
    re, typing, dataclasses, enum, logging, json, datetime, collections
    Opsiyonel: rapidfuzz (bulanık eşleştirme için)
"""

from __future__ import annotations

import json
import logging
import re
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from enum import Enum
from typing import (
    Any,
    Deque,
    Dict,
    List,
    Optional,
    Tuple,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Opsiyonel bulanık eşleştirme
# ---------------------------------------------------------------------------

try:
    from rapidfuzz import fuzz as _fuzz  # type: ignore[import]
    HAS_FUZZY = True
except ImportError:
    HAS_FUZZY = False


# ---------------------------------------------------------------------------
# Saf Python Levenshtein mesafesi
# ---------------------------------------------------------------------------

def levenshtein_distance(s1: str, s2: str) -> int:
    """
    İki dizi arasındaki Levenshtein (düzenleme) mesafesini hesapla.

    Parametreler:
        s1 (str): Birinci dizi.
        s2 (str): İkinci dizi.

    Döner:
        int: Minimum düzenleme işlemi sayısı.
    """
    m, n = len(s1), len(s2)
    if m == 0:
        return n
    if n == 0:
        return m

    # Sadece iki satır bellekte tut
    prev = list(range(n + 1))
    curr = [0] * (n + 1)

    for i in range(1, m + 1):
        curr[0] = i
        for j in range(1, n + 1):
            cost = 0 if s1[i - 1] == s2[j - 1] else 1
            curr[j] = min(
                curr[j - 1] + 1,       # ekleme
                prev[j] + 1,           # silme
                prev[j - 1] + cost,    # değiştirme
            )
        prev, curr = curr, prev

    return prev[n]


def fuzzy_match(
    query: str,
    choices: List[str],
    threshold: float = 0.8,
) -> Optional[str]:
    """
    Verilen adaylar arasından en yakın eşleşmeyi bul.

    rapidfuzz varsa kullanır, yoksa Levenshtein tabanlı benzerlik uygular.

    Parametreler:
        query     (str)        : Aranan dizi.
        choices   (List[str])  : Aday diziler.
        threshold (float)      : Minimum benzerlik oranı [0, 1].

    Döner:
        Optional[str]: En iyi eşleşme veya eşik altındaysa None.
    """
    if not choices:
        return None

    best_match: Optional[str] = None
    best_score = 0.0

    if HAS_FUZZY:
        for c in choices:
            score = _fuzz.ratio(query, c) / 100.0
            if score > best_score:
                best_score = score
                best_match = c
    else:
        for c in choices:
            max_len = max(len(query), len(c), 1)
            dist    = levenshtein_distance(query.lower(), c.lower())
            score   = 1.0 - dist / max_len
            if score > best_score:
                best_score = score
                best_match = c

    return best_match if best_score >= threshold else None


# ---------------------------------------------------------------------------
# TurkishMorphology
# ---------------------------------------------------------------------------

class TurkishMorphology:
    """
    Türkçe morfoloji araçları: kökleştirme, normalleştirme, tokenizasyon.

    Türkçe'nin sondan eklemeli yapısı gözetilerek tasarlanmıştır.
    Hafif kural tabanlı bir yaklaşım kullanılır; ağır morphological
    analiz kütüphanelerine bağımlılık yoktur.
    """

    # 50+ Türkçe ek (uzundan kısaya sıralı — greedy removal için önemli)
    SUFFIXES: List[str] = [
        # Zaman ve kip ekleri
        "maktadır", "mektedir", "maktadır",
        "abilirsiniz", "ebilirsiniz",
        "abilirsin", "ebilirsin",
        "acaksınız", "eceksiniz",
        "acaksın", "eceksin",
        "acaktır", "ecektir",
        "abilir", "ebilir",
        "acaklar", "ecekler",
        "acaktı", "ecekti",
        "malıdır", "melidir",
        "malısın", "melisin",
        "acak", "ecek",
        "malı", "meli",
        "iyor", "ıyor", "uyor", "üyor",
        "yordu", "yorlar",
        "miş", "mış", "muş", "müş",
        "tir", "tır", "tur", "tür",
        "dir", "dır", "dur", "dür",
        "dık", "dik", "duk", "dük",
        "tık", "tik", "tuk", "tük",
        "dı", "di", "du", "dü",
        "ti", "tı", "tu", "tü",
        "yor",
        # İyelik ve durum ekleri
        "nın", "nin", "nun", "nün",
        "ların", "lerin",
        "ların", "lerin",
        "lara", "lere",
        "ları", "leri",
        "lardan", "lerden",
        "larda", "lerde",
        "larla", "lerle",
        "lar", "ler",
        "dan", "den",
        "tan", "ten",
        "nda", "nde",
        "ndan", "nden",
        "nın", "nin",
        "da", "de",
        "ta", "te",
        "na", "ne",
        "nı", "ni",
        "nu", "nü",
        "ın", "in", "un", "ün",
        "yı", "yi", "yu", "yü",
        "ya", "ye",
        "la", "le",
        "ca", "ce",
        "cı", "ci", "cu", "cü",
        # Fiil kipleri
        "mak", "mek",
        "ma", "me",
        "an", "en",
        "ar", "er",
        "ir", "ır", "ur", "ür",
        "sa", "se",
        # Kısa ekler
        "lı", "li", "lu", "lü",
        "sı", "si", "su", "sü",
        "ı", "i", "u", "ü",
        "a", "e",
    ]

    # Türkçe ayraç karakterleri
    _CHAR_MAP: Dict[str, str] = {
        "ğ": "g", "ş": "s", "ı": "i", "ö": "o",
        "ü": "u", "ç": "c", "â": "a", "î": "i", "û": "u",
        "Ğ": "G", "Ş": "S", "İ": "I", "Ö": "O",
        "Ü": "U", "Ç": "C",
    }

    # 100+ yaygın Türkçe stop-word
    TURKISH_STOPWORDS: List[str] = [
        "ve", "veya", "ile", "ama", "fakat", "ancak", "lakin", "ki", "de",
        "da", "ne", "bu", "şu", "o", "bir", "için", "gibi", "kadar", "daha",
        "en", "çok", "az", "hem", "ya", "ya da", "bile", "dahi", "ise",
        "eğer", "madem", "nasıl", "neden", "niçin", "nerede", "nereden",
        "nereye", "ne zaman", "hangi", "hangisi", "kim", "kimin", "kime",
        "kimi", "kimde", "kimden", "her", "hiç", "hiçbir", "bütün", "tüm",
        "bazı", "birkaç", "birçok", "çeşitli", "diğer", "diğerleri", "aynı",
        "farklı", "şöyle", "böyle", "öyle", "bunu", "şunu", "onu", "bunun",
        "şunun", "onun", "bunlar", "şunlar", "onlar", "biz", "siz", "ben",
        "sen", "ben", "benim", "senin", "onun", "bizim", "sizin", "onların",
        "bana", "sana", "ona", "bize", "size", "onlara", "bende", "sende",
        "onda", "bizde", "sizde", "onlarda", "benden", "senden", "ondan",
        "bizden", "sizden", "onlardan", "var", "yok", "olan", "olur", "oldu",
        "olmak", "olmaz", "olmuş", "olsa", "olmadı", "değil", "değildir",
        "ile", "iken", "rağmen", "karşın", "göre", "doğru", "karşı", "önce",
        "sonra", "sırasında", "boyunca", "arasında", "içinde", "dışında",
        "üstünde", "altında", "yanında", "üzerinde", "altında", "arkasında",
        "önünde", "etrafında", "çevresinde", "hakkında", "konusunda",
        "bakımından", "açısından", "itibaren", "itibarıyla", "süresince",
        "esnasında", "sırasında", "zarfında", "ait", "ilişkin", "dair",
        "göre", "nazaran", "kıyasla", "beraber", "birlikte", "ayrıca",
        "üstelik", "dahası", "hatta", "yani", "örneğin", "mesela", "nitekim",
        "dolayısıyla", "bu nedenle", "bu yüzden", "sonuç olarak",
        "öte yandan", "buna karşın", "bununla birlikte",
    ]

    _STOPWORD_SET: Optional[set] = None

    @classmethod
    def _get_stopword_set(cls) -> set:
        """Stopword setini önbellekle döndür."""
        if cls._STOPWORD_SET is None:
            cls._STOPWORD_SET = set(cls.TURKISH_STOPWORDS)
        return cls._STOPWORD_SET

    @classmethod
    def stem(cls, word: str) -> str:
        """
        Kelimeden Türkçe ekleri iteratif olarak kaldır.

        Minimum kök uzunluğu 3 karakterdir. Ekler SUFFIXES listesinden
        uzundan kısaya doğru denenir.

        Parametreler:
            word (str): Kökleştirilecek kelime.

        Döner:
            str: Bulunan kök veya değiştirilmemiş kelime.
        """
        w = word.strip().lower()
        changed = True
        while changed and len(w) > 3:
            changed = False
            for suffix in cls.SUFFIXES:
                if w.endswith(suffix) and len(w) - len(suffix) >= 3:
                    w = w[: -len(suffix)]
                    changed = True
                    break
        return w

    @classmethod
    def normalize(cls, text: str, ascii_only: bool = False) -> str:
        """
        Türkçe metni normalleştir.

        ascii_only=True ise ğ->g, ş->s, ı->i, ö->o, ü->u, ç->c dönüşümü
        uygulanır. False ise yalnızca büyük/küçük harf ve boşluk düzeltmesi
        yapılır.

        Parametreler:
            text      (str) : Normalleştirilecek metin.
            ascii_only (bool): ASCII dönüşümünü uygula.

        Döner:
            str: Normalleştirilmiş metin.
        """
        text = text.strip()
        # Birden fazla boşluk tek boşluğa indir
        text = re.sub(r"\s+", " ", text)

        if ascii_only:
            result = []
            for ch in text:
                result.append(cls._CHAR_MAP.get(ch, ch))
            text = "".join(result)

        return text

    @classmethod
    def tokenize(cls, text: str) -> List[str]:
        """
        Türkçe metni kelime tokenlarına ayır.

        Noktalama işaretlerini kaldırır, küçük harfe çevirir.

        Parametreler:
            text (str): Tokenlanacak metin.

        Döner:
            List[str]: Token listesi.
        """
        text = cls.normalize(text)
        # Unicode harf ve rakamları token olarak al
        tokens = re.findall(r"[^\W\d_]+|\d+(?:[.,]\d+)*", text, re.UNICODE)
        return [t.lower() for t in tokens if t.strip()]

    @classmethod
    def remove_stopwords(cls, tokens: List[str]) -> List[str]:
        """
        Token listesinden stop-word'leri çıkar.

        Parametreler:
            tokens (List[str]): Giriş token listesi.

        Döner:
            List[str]: Stop-word'siz token listesi.
        """
        sw = cls._get_stopword_set()
        return [t for t in tokens if t.lower() not in sw]


# ---------------------------------------------------------------------------
# BankingDictionary
# ---------------------------------------------------------------------------

class BankingDictionary:
    """
    Türkçe–İngilizce bankacılık terminolojisi sözlüğü.

    150+ bankacılık terimi içerir. Arama yaparken Türkçe morfoloji
    normalizasyonu ve opsiyonel bulanık eşleştirme kullanılır.
    """

    TERMS: Dict[str, List[str]] = {
        # Temel kavramlar
        "hesap":            ["account"],
        "kredi":            ["credit", "loan"],
        "faiz":             ["interest", "interest rate"],
        "faiz oranı":       ["interest rate"],
        "taksit":           ["installment"],
        "vade":             ["maturity", "term"],
        "ipotek":           ["mortgage"],
        "borç":             ["debt"],
        "alacak":           ["receivable"],
        "bakiye":           ["balance"],
        "transfer":         ["transfer"],
        "havale":           ["wire transfer", "remittance"],
        "eft":              ["electronic funds transfer", "EFT"],
        "swift":            ["SWIFT"],
        "iban":             ["IBAN"],
        "bic":              ["BIC"],
        "işlem":            ["transaction"],
        "para":             ["money", "currency"],
        "döviz":            ["foreign exchange", "FX"],
        "kur":              ["exchange rate"],
        "mevduat":          ["deposit"],
        "vadeli mevduat":   ["time deposit", "term deposit"],
        "vadesiz mevduat":  ["demand deposit"],
        "cari hesap":       ["current account", "checking account"],
        "tasarruf hesabı":  ["savings account"],
        "çek":              ["check", "cheque"],
        "senet":            ["promissory note", "bill"],
        "bono":             ["bond", "bill"],
        "tahvil":           ["bond", "debenture"],
        "hisse":            ["share", "stock"],
        "hisse senedi":     ["stock", "equity share"],
        "portföy":          ["portfolio"],
        "yatırım":          ["investment"],
        "fon":              ["fund"],
        "yatırım fonu":     ["mutual fund"],
        "emeklilik fonu":   ["pension fund"],
        "sigorta":          ["insurance"],
        "hayat sigortası":  ["life insurance"],
        "bireysel emeklilik":["individual pension"],
        "banka":            ["bank"],
        "şube":             ["branch"],
        "atm":              ["ATM", "automated teller machine"],
        "pos":              ["POS", "point of sale"],
        "online bankacılık":["online banking", "internet banking"],
        "mobil bankacılık": ["mobile banking"],
        "kredi kartı":      ["credit card"],
        "banka kartı":      ["debit card"],
        "ön ödemeli kart":  ["prepaid card"],
        "kart limiti":      ["card limit", "credit limit"],
        "ekstra":           ["extra statement period"],
        "taksitlendirme":   ["installment plan"],
        "borç yapılandırma":["debt restructuring"],
        "nakit avans":      ["cash advance"],
        "çevrimiçi ödeme":  ["online payment"],
        "otomatik ödeme":   ["auto payment", "standing order"],
        "düzenli ödeme":    ["recurring payment"],
        "fatura ödeme":     ["bill payment"],
        "vergi":            ["tax"],
        "stopaj":           ["withholding tax"],
        "kdv":              ["VAT", "value added tax"],
        "komisyon":         ["commission", "fee"],
        "masraf":           ["charge", "fee", "expense"],
        "gecikme faizi":    ["late payment interest"],
        "ücret":            ["fee", "charge"],
        "kefalet":          ["surety", "guarantee"],
        "teminat":          ["collateral", "guarantee"],
        "ipotek tescili":   ["mortgage registration"],
        "tapu":             ["title deed"],
        "konut kredisi":    ["housing loan", "mortgage"],
        "taşıt kredisi":    ["vehicle loan", "auto loan"],
        "ihtiyaç kredisi":  ["personal loan", "consumer loan"],
        "ticari kredi":     ["commercial loan"],
        "işletme kredisi":  ["business loan"],
        "ihracat kredisi":  ["export credit"],
        "ithalat kredisi":  ["import credit"],
        "akreditif":        ["letter of credit", "LC"],
        "teminat mektubu":  ["letter of guarantee", "bank guarantee"],
        "kefaletname":      ["surety bond"],
        "proje finansmanı": ["project finance"],
        "sendikasyon":      ["syndication", "syndicated loan"],
        "repo":             ["repo", "repurchase agreement"],
        "ters repo":        ["reverse repo"],
        "interbank":        ["interbank"],
        "merkez bankası":   ["central bank"],
        "bddk":             ["BDDK", "Banking Regulation and Supervision Agency"],
        "tcmb":             ["CBRT", "Central Bank of the Republic of Turkey"],
        "hazine":           ["treasury"],
        "devlet tahvili":   ["government bond"],
        "eurobond":         ["eurobond"],
        "kıymet":           ["security", "asset"],
        "likit":            ["liquid", "liquidity"],
        "likidite":         ["liquidity"],
        "nakit akışı":      ["cash flow"],
        "özkaynak":         ["equity", "net equity"],
        "sermaye":          ["capital"],
        "öz sermaye":       ["equity capital"],
        "kar":              ["profit", "gain"],
        "zarar":            ["loss"],
        "net kar":          ["net profit"],
        "brüt kar":         ["gross profit"],
        "bütçe":            ["budget"],
        "gelir":            ["income", "revenue"],
        "gider":            ["expense", "expenditure"],
        "aktif":            ["asset"],
        "pasif":            ["liability", "passive"],
        "bilanço":          ["balance sheet"],
        "gelir tablosu":    ["income statement", "P&L"],
        "nakit akış tablosu":["cash flow statement"],
        "denetim":          ["audit", "control"],
        "iç denetim":       ["internal audit"],
        "dış denetim":      ["external audit"],
        "uyum":             ["compliance"],
        "aml":              ["AML", "anti-money laundering"],
        "kyd":              ["KYC", "know your customer"],
        "kara para":        ["money laundering"],
        "dolandırıcılık":   ["fraud"],
        "sahte":            ["counterfeit", "fake"],
        "risk":             ["risk"],
        "kredi riski":      ["credit risk"],
        "piyasa riski":     ["market risk"],
        "operasyonel risk": ["operational risk"],
        "likidite riski":   ["liquidity risk"],
        "kur riski":        ["currency risk", "FX risk"],
        "faiz riski":       ["interest rate risk"],
        "karşı taraf riski":["counterparty risk"],
        "stres testi":      ["stress test"],
        "senaryo analizi":  ["scenario analysis"],
        "var":              ["VaR", "value at risk"],
        "baz puan":         ["basis point", "bps"],
        "spread":           ["spread"],
        "marj":             ["margin"],
        "volatilite":       ["volatility"],
        "korelasyon":       ["correlation"],
        "beta":             ["beta"],
        "endeks":           ["index"],
        "borsa":            ["stock exchange", "bourse"],
        "bist":             ["BIST", "Borsa Istanbul"],
        "takasbank":        ["Takasbank"],
        "mkk":              ["CSD", "central securities depository"],
        "saklama":          ["custody", "safekeeping"],
        "clearing":         ["clearing"],
        "takas":            ["settlement", "clearing"],
        "valör":            ["value date"],
        "dekont":           ["receipt", "voucher"],
        "ekstre":           ["statement", "account statement"],
        "hesap özeti":      ["account summary"],
        "bloke":            ["block", "hold"],
        "serbest":          ["free", "available"],
        "kullanılabilir":   ["available"],
        "müşteri":          ["customer", "client"],
        "kurumsal":         ["corporate", "institutional"],
        "bireysel":         ["individual", "retail"],
        "kobi":             ["SME", "small and medium enterprise"],
        "ticari":           ["commercial"],
        "perakende":        ["retail"],
        "özel bankacılık":  ["private banking"],
        "servet yönetimi":  ["wealth management"],
    }

    # Tüm terimlerin küçük harf seti (hızlı kontrol için)
    _TERM_KEYS_LOWER: Optional[set] = None

    @classmethod
    def _keys_lower(cls) -> set:
        if cls._TERM_KEYS_LOWER is None:
            cls._TERM_KEYS_LOWER = {k.lower() for k in cls.TERMS}
        return cls._TERM_KEYS_LOWER

    @classmethod
    def lookup(cls, term: str) -> Optional[List[str]]:
        """
        Türkçe bankacılık terimini İngilizce karşılıklarıyla döndür.

        Önce tam eşleşme, bulunamazsa kökleştirme, ardından bulanık
        eşleştirme dener.

        Parametreler:
            term (str): Aranacak Türkçe terim.

        Döner:
            Optional[List[str]]: İngilizce karşılıklar listesi ya da None.
        """
        key = term.strip().lower()
        if key in cls.TERMS:
            return cls.TERMS[key]

        # Kök tabanlı eşleştirme
        stem = TurkishMorphology.stem(key)
        for k in cls.TERMS:
            if TurkishMorphology.stem(k) == stem:
                return cls.TERMS[k]

        # Bulanık eşleştirme
        match = fuzzy_match(key, list(cls.TERMS.keys()), threshold=0.75)
        if match:
            return cls.TERMS[match]

        return None

    @classmethod
    def is_banking_term(cls, word: str) -> bool:
        """
        Kelimenin bankacılık terimi olup olmadığını kontrol et.

        Parametreler:
            word (str): Kontrol edilecek kelime.

        Döner:
            bool: Bankacılık terimi ise True.
        """
        return cls.lookup(word) is not None

    @classmethod
    def get_synonyms(cls, term: str) -> List[str]:
        """
        Terimin tüm İngilizce eş anlamlılarını döndür.

        Parametreler:
            term (str): Türkçe terim.

        Döner:
            List[str]: Eş anlamlı İngilizce terimler.
        """
        result = cls.lookup(term)
        return result if result is not None else []

    @classmethod
    def all_turkish_terms(cls) -> List[str]:
        """Sözlükteki tüm Türkçe terimleri döndür."""
        return list(cls.TERMS.keys())


# ---------------------------------------------------------------------------
# IntentDetector
# ---------------------------------------------------------------------------

class IntentDetector:
    """
    Türkçe metin içinden kullanıcı niyetini tespit eder.

    Anahtar kelime eşleştirmesi + TF-IDF benzeri ağırlıklı puanlama
    kullanılır. Her niyet için güven skoru [0, 1] aralığındadır.
    """

    INTENTS: Dict[str, List[str]] = {
        "ÜRET": [
            "üret", "oluştur", "generate", "yap", "ekle", "kayıt",
            "veri üret", "yeni veri", "örnek oluştur", "simüle et",
            "simulasyon", "mock", "fake veri", "test verisi", "veri yarat",
            "sentetik", "yapay", "üretim", "başlat", "çalıştır",
        ],
        "ANALİZ_ET": [
            "analiz", "incele", "kontrol", "doğrula", "test", "karşılaştır",
            "denetle", "değerlendir", "ölç", "hesapla", "istatistik",
            "dağılım", "korelasyon", "anomali", "kalite", "puan",
            "skor", "metrik", "performans", "değer", "sapma",
        ],
        "DIŞA_AKTAR": [
            "dışa aktar", "export", "kaydet", "indir", "çıkar", "aktar",
            "dosya", "json", "csv", "excel", "pdf", "rapor al",
            "yedekle", "backup", "çıktı al", "hazırla",
        ],
        "SORGULA": [
            "göster", "listele", "bul", "ara", "kaç", "ne kadar", "sorgula",
            "getir", "döndür", "filtrele", "seç", "bak", "gör", "oku",
            "son", "ilk", "tüm", "hepsi", "hangi",
        ],
        "RAPOR": [
            "rapor", "özet", "istatistik", "dashboard", "görsel",
            "grafik", "tablo", "chart", "özet rapor", "günlük rapor",
            "haftalık", "aylık", "yıllık", "dönemsel", "periyodik",
        ],
        "SİL": [
            "sil", "kaldır", "temizle", "iptal", "geri al", "delete",
            "reset", "başa al", "temizlik",
        ],
        "GÜNCELLE": [
            "güncelle", "değiştir", "düzenle", "update", "edit",
            "ayarla", "yapılandır", "parametre", "config",
        ],
    }

    @classmethod
    def detect(cls, text: str) -> Tuple[str, float]:
        """
        Metindeki en baskın niyeti ve güven skorunu döndür.

        Parametreler:
            text (str): Kullanıcı girdi metni.

        Döner:
            Tuple[str, float]: (niyet_kodu, güven_skoru).
            Eşleşme yoksa ("BILINMIYOR", 0.0) döner.
        """
        all_detected = cls.detect_all(text)
        if not all_detected:
            return ("BILINMIYOR", 0.0)
        return all_detected[0]

    @classmethod
    def detect_all(cls, text: str) -> List[Tuple[str, float]]:
        """
        Metindeki tüm niyetleri güven skoruna göre sıralı döndür.

        Parametreler:
            text (str): Kullanıcı girdi metni.

        Döner:
            List[Tuple[str, float]]: (niyet, güven) çiftlerinin listesi.
        """
        tokens = TurkishMorphology.tokenize(text)
        lower_text = text.lower()
        scores: Dict[str, float] = {}

        for intent, keywords in cls.INTENTS.items():
            score = 0.0
            for kw in keywords:
                kw_lower = kw.lower()
                # Tam ifade eşleşmesi (daha yüksek ağırlık)
                if kw_lower in lower_text:
                    weight = 1.0 + 0.5 * (len(kw_lower.split()) - 1)
                    score += weight
                else:
                    # Token düzeyinde kısmi eşleşme
                    kw_tokens = kw_lower.split()
                    matches   = sum(1 for kt in kw_tokens if kt in tokens)
                    if matches > 0:
                        score += 0.4 * matches / len(kw_tokens)

            if score > 0:
                # Normalize: max mümkün skor bu intent için keywords sayısı
                max_score = float(len(keywords))
                scores[intent] = min(score / max(max_score, 1.0), 1.0)

        if not scores:
            return []

        sorted_intents = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return sorted_intents


# ---------------------------------------------------------------------------
# EntityExtractor
# ---------------------------------------------------------------------------

class EntityExtractor:
    """
    Türkçe bankacılık metinlerinden varlık çıkarır.

    Desteklenen Varlık Türleri:
        - Tutar (TL, USD, EUR, GBP, CHF, JPY)
        - Tarih (15.03.2024, 15 Mart 2024, geçen ay, bu hafta, vb.)
        - Hesap türü (vadesiz, vadeli, kredi, tasarruf, vb.)
        - Para birimi
        - Adet / sayı
    """

    # Türkçe ay isimleri
    TR_MONTHS: Dict[str, int] = {
        "ocak": 1, "şubat": 2, "mart": 3, "nisan": 4,
        "mayıs": 5, "haziran": 6, "temmuz": 7, "ağustos": 8,
        "eylül": 9, "ekim": 10, "kasım": 11, "aralık": 12,
    }

    # Para birimi eşlemeleri
    CURRENCY_MAP: Dict[str, str] = {
        "tl": "TRY", "türk lirası": "TRY", "lira": "TRY", "₺": "TRY",
        "dolar": "USD", "usd": "USD", "$": "USD",
        "euro": "EUR", "eur": "EUR", "€": "EUR",
        "sterlin": "GBP", "gbp": "GBP", "£": "GBP",
        "frank": "CHF", "chf": "CHF", "isviçre frangı": "CHF",
        "yen": "JPY", "jpy": "JPY",
        "ruble": "RUB", "rub": "RUB",
    }

    # Hesap türleri
    ACCOUNT_TYPES: List[str] = [
        "vadesiz hesap", "vadesiz mevduat",
        "vadeli hesap", "vadeli mevduat",
        "tasarruf hesabı", "tasarruf",
        "cari hesap", "çek hesabı",
        "kredi hesabı", "kredi",
        "konut kredisi", "taşıt kredisi", "ihtiyaç kredisi",
        "ticari kredi", "işletme kredisi",
        "bireysel emeklilik", "emeklilik",
        "yatırım hesabı", "portföy",
    ]

    # Sayı kelimeleri
    TR_NUMBERS: Dict[str, int] = {
        "bir": 1, "iki": 2, "üç": 3, "dört": 4, "beş": 5,
        "altı": 6, "yedi": 7, "sekiz": 8, "dokuz": 9, "on": 10,
        "yirmi": 20, "otuz": 30, "kırk": 40, "elli": 50,
        "altmış": 60, "yetmiş": 70, "seksen": 80, "doksan": 90,
        "yüz": 100, "bin": 1000, "milyon": 1_000_000,
        "milyar": 1_000_000_000, "trilyon": 1_000_000_000_000,
    }

    @classmethod
    def extract_amount(cls, text: str) -> Optional[Dict[str, Any]]:
        """
        Metinden para tutarını çıkar.

        Desteklenen formatlar:
            "5.000 TL", "5000 lira", "5 bin TL", "1.5 milyon dolar",
            "500 €", "1,250.00 USD"

        Parametreler:
            text (str): İşlenecek metin.

        Döner:
            Optional[dict]: {"value": float, "currency": str, "raw": str}
            ya da None.
        """
        text_lower = text.lower()

        # 1) Sayısal format: 1.000,50 TL / 1,000.50 USD
        pattern_numeric = re.compile(
            r"([\d]{1,3}(?:[.,\s]\d{3})*(?:[.,]\d+)?)"
            r"\s*"
            r"(tl|türk lirası|lira|₺|dolar|usd|\$|euro|eur|€|sterlin|gbp|£|frank|chf|yen|jpy)",
            re.IGNORECASE,
        )
        m = pattern_numeric.search(text_lower)
        if m:
            raw_num = m.group(1).replace(" ", "")
            # Binlik ayraç mı ondalık mı? Son ayracı kontrol et
            if "," in raw_num and "." in raw_num:
                # 1.000,50 -> nokta binlik, virgül ondalık
                raw_num = raw_num.replace(".", "").replace(",", ".")
            elif "," in raw_num:
                raw_num = raw_num.replace(",", ".")
            elif "." in raw_num:
                # "5.000" -> binlik; "5.5" -> ondalık
                parts = raw_num.split(".")
                if len(parts) == 2 and len(parts[1]) == 3:
                    raw_num = raw_num.replace(".", "")
            try:
                value    = float(raw_num)
                currency = cls.CURRENCY_MAP.get(m.group(2).lower(), "TRY")
                return {"value": value, "currency": currency, "raw": m.group(0).strip()}
            except ValueError:
                pass

        # 2) Sözel format: "5 bin TL", "1.5 milyon dolar"
        pattern_verbal = re.compile(
            r"(\d+(?:[.,]\d+)?)\s*(bin|milyon|milyar|trilyon)"
            r"(?:\s*(tl|lira|₺|dolar|usd|\$|euro|eur|€|sterlin|gbp|£|frank|chf))?",
            re.IGNORECASE,
        )
        m2 = pattern_verbal.search(text_lower)
        if m2:
            base_str   = m2.group(1).replace(",", ".")
            multiplier = cls.TR_NUMBERS.get(m2.group(2).lower(), 1)
            try:
                value    = float(base_str) * multiplier
                cur_raw  = m2.group(3) or "tl"
                currency = cls.CURRENCY_MAP.get(cur_raw.lower(), "TRY")
                return {"value": value, "currency": currency, "raw": m2.group(0).strip()}
            except ValueError:
                pass

        return None

    @classmethod
    def extract_date(cls, text: str) -> Optional[Dict[str, Any]]:
        """
        Metinden tarih ifadesini çıkar.

        Desteklenen formatlar:
            "15.03.2024", "15/03/2024", "15-03-2024",
            "15 Mart 2024", "Mart 2024",
            "geçen ay", "bu hafta", "dün", "bugün", "yarın",
            "geçen yıl", "bu yıl", "önümüzdeki ay"

        Parametreler:
            text (str): İşlenecek metin.

        Döner:
            Optional[dict]: {"value": date, "raw": str, "relative": bool}
            ya da None.
        """
        text_lower = text.lower()
        today      = date.today()

        # Göreli tarihler
        relative_map: List[Tuple[str, date]] = [
            ("bugün",          today),
            ("dün",            today - timedelta(days=1)),
            ("yarın",          today + timedelta(days=1)),
            ("bu hafta",       today - timedelta(days=today.weekday())),
            ("geçen hafta",    today - timedelta(days=today.weekday() + 7)),
            ("bu ay",          today.replace(day=1)),
            ("geçen ay",       (today.replace(day=1) - timedelta(days=1)).replace(day=1)),
            ("önümüzdeki ay",  (today.replace(day=28) + timedelta(days=4)).replace(day=1)),
            ("bu yıl",         today.replace(month=1, day=1)),
            ("geçen yıl",      today.replace(year=today.year - 1, month=1, day=1)),
        ]
        for phrase, resolved in relative_map:
            if phrase in text_lower:
                return {"value": resolved, "raw": phrase, "relative": True}

        # DD.MM.YYYY veya DD/MM/YYYY veya DD-MM-YYYY
        pattern_dmy = re.compile(
            r"\b(\d{1,2})[./\-](\d{1,2})[./\-](\d{2,4})\b"
        )
        m = pattern_dmy.search(text)
        if m:
            day, month, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
            if year < 100:
                year += 2000
            try:
                d = date(year, month, day)
                return {"value": d, "raw": m.group(0), "relative": False}
            except ValueError:
                pass

        # DD Ay YYYY  (örn: "15 Mart 2024")
        month_names = "|".join(cls.TR_MONTHS.keys())
        pattern_verbal = re.compile(
            rf"\b(\d{{1,2}})\s+({month_names})\s+(\d{{4}})\b",
            re.IGNORECASE,
        )
        m2 = pattern_verbal.search(text_lower)
        if m2:
            day   = int(m2.group(1))
            month = cls.TR_MONTHS[m2.group(2).lower()]
            year  = int(m2.group(3))
            try:
                d = date(year, month, day)
                return {"value": d, "raw": m2.group(0), "relative": False}
            except ValueError:
                pass

        # Ay YYYY  (örn: "Mart 2024")
        pattern_my = re.compile(
            rf"\b({month_names})\s+(\d{{4}})\b",
            re.IGNORECASE,
        )
        m3 = pattern_my.search(text_lower)
        if m3:
            month = cls.TR_MONTHS[m3.group(1).lower()]
            year  = int(m3.group(2))
            try:
                d = date(year, month, 1)
                return {"value": d, "raw": m3.group(0), "relative": False}
            except ValueError:
                pass

        return None

    @classmethod
    def extract_account_type(cls, text: str) -> Optional[str]:
        """
        Metinden hesap türünü çıkar.

        Parametreler:
            text (str): İşlenecek metin.

        Döner:
            Optional[str]: Hesap türü adı ya da None.
        """
        text_lower = text.lower()
        # Uzun eşleşmelere öncelik ver
        for acct in sorted(cls.ACCOUNT_TYPES, key=len, reverse=True):
            if acct in text_lower:
                return acct
        return None

    @classmethod
    def extract_currency(cls, text: str) -> Optional[str]:
        """
        Metinden para birimi kodunu çıkar (TRY, USD, EUR, vb.).

        Parametreler:
            text (str): İşlenecek metin.

        Döner:
            Optional[str]: ISO 4217 para birimi kodu ya da None.
        """
        text_lower = text.lower()
        # Uzun ifadelere öncelik ver
        for phrase, code in sorted(
            cls.CURRENCY_MAP.items(), key=lambda x: len(x[0]), reverse=True
        ):
            if phrase in text_lower:
                return code
        return None

    @classmethod
    def extract_count(cls, text: str) -> Optional[int]:
        """
        Metinden adet/sayı ifadesini çıkar.

        Desteklenen formatlar:
            "100 kayıt", "bin adet", "5 milyon satır", "50k"

        Parametreler:
            text (str): İşlenecek metin.

        Döner:
            Optional[int]: Bulunan sayı ya da None.
        """
        text_lower = text.lower()

        # Adet belirteçleri — bunlarla birlikte gelen sayılar önceliklidir
        COUNT_MARKERS = r"(?:adet|kayıt|satır|tane|kez|örnek|müşteri|hesap|kullanıcı|işlem)"

        # 1) "5k", "10k" gibi kısaltmalar
        m_k = re.search(r"\b(\d+(?:\.\d+)?)\s*k\b", text_lower)
        if m_k:
            try:
                return int(float(m_k.group(1)) * 1000)
            except ValueError:
                pass

        # 2) Sayısal + belirteç: "100 kayıt", "50 müşteri" — yüksek öncelik
        pattern_marked = re.compile(
            rf"(\d{{1,3}}(?:[.,]\d{{3}})*|\d+)\s+{COUNT_MARKERS}",
            re.IGNORECASE,
        )
        m_marked = pattern_marked.search(text_lower)
        if m_marked:
            raw = m_marked.group(1).replace(".", "").replace(",", "")
            try:
                return int(raw)
            except ValueError:
                pass

        # 3) Büyük birim + belirteç: "2 bin kayıt", "5 milyon satır"
        pattern_big_marked = re.compile(
            rf"(\d+(?:[.,]\d+)?)\s*(bin|milyon|milyar)\s+{COUNT_MARKERS}",
            re.IGNORECASE,
        )
        m_bm = pattern_big_marked.search(text_lower)
        if m_bm:
            multiplier = cls.TR_NUMBERS.get(m_bm.group(2).lower(), 1)
            try:
                return int(float(m_bm.group(1).replace(",", ".")) * multiplier)
            except ValueError:
                pass

        # 4) Büyük birim (belirteçsiz): "5 bin", "2 milyon"
        pattern_big = re.compile(
            r"(\d+(?:[.,]\d+)?)\s*(bin|milyon|milyar)",
            re.IGNORECASE,
        )
        m2 = pattern_big.search(text_lower)
        if m2:
            multiplier = cls.TR_NUMBERS.get(m2.group(2).lower(), 1)
            try:
                return int(float(m2.group(1).replace(",", ".")) * multiplier)
            except ValueError:
                pass

        # 5) Sade sayısal (belirteçsiz): "100", "1.000"
        pattern_num = re.compile(
            r"(\d{1,3}(?:[.,]\d{3})*|\d+)",
            re.IGNORECASE,
        )
        m3 = pattern_num.search(text)
        if m3:
            raw = m3.group(1).replace(".", "").replace(",", "")
            try:
                return int(raw)
            except ValueError:
                pass

        # 6) Yazıyla sayılar: "yüz", "bin", vb.
        for word, val in sorted(
            cls.TR_NUMBERS.items(), key=lambda x: x[1], reverse=True
        ):
            if re.search(r"\b" + re.escape(word) + r"\b", text_lower):
                return val

        return None

    @classmethod
    def extract_all(cls, text: str) -> Dict[str, Any]:
        """
        Metindeki tüm varlıkları tek sözlükte döndür.

        Parametreler:
            text (str): İşlenecek metin.

        Döner:
            dict: {
                "amount":       dict | None,
                "date":         dict | None,
                "account_type": str | None,
                "currency":     str | None,
                "count":        int | None,
            }
        """
        return {
            "amount":       cls.extract_amount(text),
            "date":         cls.extract_date(text),
            "account_type": cls.extract_account_type(text),
            "currency":     cls.extract_currency(text),
            "count":        cls.extract_count(text),
        }


# ---------------------------------------------------------------------------
# ContextTracker
# ---------------------------------------------------------------------------

class ContextTracker:
    """
    Çok turlu konuşma bağlamını takip eder.

    Özellikler:
        - Geçmişin son `max_history` turunu tutar.
        - Belirsiz zamiri referansları çözer ("bunu", "onu", "aynısını").
        - Son intent ve varlıklara hızlı erişim sağlar.

    Parametreler:
        max_history (int): Saklanacak maksimum tur sayısı. Varsayılan: 10.
    """

    # Türkçe belirsiz zamirler
    ANAPHORA_TOKENS: List[str] = [
        "bunu", "buna", "bunun", "bunlar", "bunları",
        "şunu", "şuna", "şunun", "şunlar", "şunları",
        "onu", "ona", "onun", "onlar", "onları",
        "aynısını", "aynısı", "aynı şeyi",
        "onu", "bunu", "onu tekrar", "aynısını",
    ]

    def __init__(self, max_history: int = 10) -> None:
        """
        ContextTracker nesnesini başlat.

        Parametreler:
            max_history (int): Tutulacak konuşma turu sayısı.
        """
        self.max_history = max_history
        self._history: Deque[Dict[str, Any]] = deque(maxlen=max_history)

    def add_turn(
        self,
        user_text: str,
        parsed: Dict[str, Any],
        response: str,
    ) -> None:
        """
        Konuşmaya yeni bir tur ekle.

        Parametreler:
            user_text (str)  : Kullanıcının ham girdi metni.
            parsed    (dict) : NLP boru hattından dönen ayrıştırma sonucu.
            response  (str)  : Sistemin ürettiği yanıt metni.
        """
        self._history.append({
            "user_text": user_text,
            "parsed":    parsed,
            "response":  response,
            "timestamp": datetime.now().isoformat(),
        })

    def get_context(self) -> List[Dict[str, Any]]:
        """
        Tüm konuşma geçmişini listele.

        Döner:
            List[dict]: Konuşma turlarının listesi (kronolojik sıra).
        """
        return list(self._history)

    def resolve_reference(self, text: str) -> str:
        """
        Belirsiz zamiri önceki turdaki bağlamla çöz.

        Metinde bir zamir tespit edilirse son turun kullanıcı metniyle
        ikame edilmiş yeni metin döner.

        Parametreler:
            text (str): Zamir içerebilecek kullanıcı metni.

        Döner:
            str: Zarifi çözülmüş metin.
        """
        text_lower = text.lower()
        has_anaphora = any(
            token in text_lower for token in self.ANAPHORA_TOKENS
        )
        if not has_anaphora or not self._history:
            return text

        # Son turdaki kullanıcı metnini referans al
        last_turn = self._history[-1]
        last_text = last_turn.get("user_text", "")
        if not last_text:
            return text

        # Basit ikame: zamiri önceki içerikle değiştir
        resolved = text
        for token in self.ANAPHORA_TOKENS:
            if token in text_lower:
                # Büyük/küçük harf duyarsız ikame
                resolved = re.sub(
                    re.escape(token),
                    last_text,
                    resolved,
                    flags=re.IGNORECASE,
                )
                break  # Tek zamir çözümü yeterli

        return resolved

    def clear(self) -> None:
        """Tüm konuşma geçmişini temizle."""
        self._history.clear()

    def get_last_intent(self) -> Optional[str]:
        """
        Son turda tespit edilen niyeti döndür.

        Döner:
            Optional[str]: Niyet kodu ya da None.
        """
        if not self._history:
            return None
        last = self._history[-1]
        return last.get("parsed", {}).get("intent")

    def get_last_entities(self) -> Dict[str, Any]:
        """
        Son turda çıkarılan varlıkları döndür.

        Döner:
            dict: Varlık sözlüğü.
        """
        if not self._history:
            return {}
        last = self._history[-1]
        return last.get("parsed", {}).get("entities", {})

    def get_accumulated_entities(self) -> Dict[str, Any]:
        """
        Tüm konuşma boyunca toplanan varlıkları birleştir.

        Sonraki turlar önceki turları geçersiz kılar (son değer öncelikli).

        Döner:
            dict: Birleştirilmiş varlık sözlüğü.
        """
        accumulated: Dict[str, Any] = {}
        for turn in self._history:
            entities = turn.get("parsed", {}).get("entities", {})
            for key, val in entities.items():
                if val is not None:
                    accumulated[key] = val
        return accumulated

    def __len__(self) -> int:
        return len(self._history)

    def __repr__(self) -> str:
        return (
            f"ContextTracker(turns={len(self)}, max={self.max_history})"
        )


# ---------------------------------------------------------------------------
# TurkishBankingNLP — Ana Boru Hattı
# ---------------------------------------------------------------------------

class TurkishBankingNLP:
    """
    Türkçe Bankacılık NLP Ana Boru Hattı.

    Tek bir metin için şu adımları sırayla uygular:
        1. Normalleştirme
        2. Tokenizasyon
        3. Stop-word kaldırma
        4. Kökleştirme
        5. Niyet tespiti
        6. Varlık çıkarma
        7. Bankacılık terimi tespiti

    Kullanım::

        nlp = TurkishBankingNLP()
        result = nlp.parse("100 müşteri için vadesiz hesap verisi üret")
        print(result["intent"])    # "ÜRET"
        print(result["entities"]) # {"count": 100, "account_type": "vadesiz hesap", ...}
    """

    def __init__(self) -> None:
        """TurkishBankingNLP nesnesini başlat."""
        self.morphology  = TurkishMorphology
        self.dictionary  = BankingDictionary
        self.intent_det  = IntentDetector
        self.entity_ext  = EntityExtractor
        logger.info("TurkishBankingNLP boru hattı başlatıldı.")

    def parse(
        self,
        text: str,
        context: Optional[ContextTracker] = None,
    ) -> Dict[str, Any]:
        """
        Tek bir Türkçe metni tam boru hattından geçir.

        Parametreler:
            text    (str)                      : Kullanıcı girdi metni.
            context (ContextTracker | None)    : Bağlam takipçisi (opsiyonel).

        Döner:
            dict: {
                "original":      str,
                "normalized":    str,
                "tokens":        List[str],
                "stems":         List[str],
                "intent":        str,
                "intent_confidence": float,
                "all_intents":   List[Tuple[str, float]],
                "entities":      dict,
                "banking_terms": List[str],
                "context_resolved": bool,
            }
        """
        # Bağlam çözümlemesi
        context_resolved = False
        if context is not None:
            resolved_text    = context.resolve_reference(text)
            context_resolved = resolved_text != text
            text             = resolved_text

        # 1. Normalleştirme
        normalized = self.morphology.normalize(text)

        # 2. Tokenizasyon
        tokens = self.morphology.tokenize(normalized)

        # 3. Stop-word kaldırma
        clean_tokens = self.morphology.remove_stopwords(tokens)

        # 4. Kökleştirme
        stems = [self.morphology.stem(t) for t in clean_tokens]

        # 5. Niyet tespiti
        intent, confidence = self.intent_det.detect(normalized)
        all_intents        = self.intent_det.detect_all(normalized)

        # 6. Varlık çıkarma
        entities = self.entity_ext.extract_all(normalized)

        # 7. Bankacılık terimi tespiti
        banking_terms = [
            t for t in clean_tokens
            if self.dictionary.is_banking_term(t)
        ]

        result: Dict[str, Any] = {
            "original":           text,
            "normalized":         normalized,
            "tokens":             tokens,
            "clean_tokens":       clean_tokens,
            "stems":              stems,
            "intent":             intent,
            "intent_confidence":  confidence,
            "all_intents":        all_intents,
            "entities":           entities,
            "banking_terms":      banking_terms,
            "context_resolved":   context_resolved,
        }

        # Bağlam güncelle
        if context is not None:
            context.add_turn(
                user_text=text,
                parsed=result,
                response="",  # yanıt dışarıda oluşturulur
            )

        logger.debug(
            "Ayrıştırma tamamlandı: intent=%s (%.2f), entities=%s",
            intent, confidence, entities,
        )
        return result

    def parse_batch(
        self,
        texts: List[str],
        context: Optional[ContextTracker] = None,
    ) -> List[Dict[str, Any]]:
        """
        Birden fazla metni sırayla ayrıştır.

        Her metin bağımsız olarak işlenir; eğer context sağlanmışsa
        sıralı turlar olarak bağlama eklenir.

        Parametreler:
            texts   (List[str])                : Metin listesi.
            context (ContextTracker | None)    : Paylaşılan bağlam takipçisi.

        Döner:
            List[dict]: Her metne karşılık gelen ayrıştırma sonuçları.
        """
        results = []
        for text in texts:
            results.append(self.parse(text, context=context))
        return results

    def explain(self, parse_result: Dict[str, Any]) -> str:
        """
        Ayrıştırma sonucunu insan okunabilir Türkçe açıklama olarak döndür.

        Parametreler:
            parse_result (dict): parse() yönteminin döndürdüğü sözlük.

        Döner:
            str: Açıklama metni.
        """
        lines = [
            f"Niyet       : {parse_result.get('intent')} "
            f"(güven: {parse_result.get('intent_confidence', 0):.0%})",
        ]
        entities = parse_result.get("entities", {})
        if entities.get("count"):
            lines.append(f"Adet        : {entities['count']:,}")
        if entities.get("amount"):
            amt = entities["amount"]
            lines.append(
                f"Tutar       : {amt['value']:,.2f} {amt['currency']}"
            )
        if entities.get("account_type"):
            lines.append(f"Hesap Türü  : {entities['account_type']}")
        if entities.get("currency"):
            lines.append(f"Para Birimi : {entities['currency']}")
        if entities.get("date"):
            dt = entities["date"]
            lines.append(f"Tarih       : {dt['value']} (raw: {dt['raw']})")
        if parse_result.get("banking_terms"):
            lines.append(
                f"Bank.Terimler: {', '.join(parse_result['banking_terms'])}"
            )
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Modül düzeyinde kolaylık fonksiyonları
# ---------------------------------------------------------------------------

def parse_command(
    text: str,
    context: Optional[ContextTracker] = None,
) -> Dict[str, Any]:
    """
    Tek seferlik hızlı ayrıştırma için kolaylık fonksiyonu.

    Parametreler:
        text    (str)                  : Kullanıcı komutu.
        context (ContextTracker|None)  : Opsiyonel bağlam takipçisi.

    Döner:
        dict: TurkishBankingNLP.parse() çıktısı.
    """
    nlp = TurkishBankingNLP()
    return nlp.parse(text, context=context)


def detect_intent(text: str) -> Tuple[str, float]:
    """
    Metindeki niyeti hızlıca tespit et.

    Parametreler:
        text (str): Kullanıcı metni.

    Döner:
        Tuple[str, float]: (niyet_kodu, güven_skoru).
    """
    return IntentDetector.detect(text)


def extract_entities(text: str) -> Dict[str, Any]:
    """
    Metindeki tüm varlıkları hızlıca çıkar.

    Parametreler:
        text (str): İşlenecek metin.

    Döner:
        dict: Varlık sözlüğü.
    """
    return EntityExtractor.extract_all(text)
