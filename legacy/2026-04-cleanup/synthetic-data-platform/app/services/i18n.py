"""
Uluslararasılaştırma (i18n) Servisi - JSON tabanlı çok dilli destek

Bu modül, SyntheticBankData platformunda çoklu dil desteği sağlar.
Locale JSON dosyalarından çeviriler yükler, nokta-gösterimi anahtarlarını
çözer, parametre ikamesi ve çoğul form desteği sunar.

Desteklenen diller: Türkçe (tr), İngilizce (en), Almanca (de),
Fransızca (fr), Arapça (ar).
"""
import json
import os
import re
import logging
from typing import Dict, Optional, List, Any
from pathlib import Path
from functools import lru_cache
from datetime import datetime

try:
    from fastapi import Request
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False

try:
    from jinja2 import Environment
    HAS_JINJA2 = True
except ImportError:
    HAS_JINJA2 = False

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Sabitler
# ---------------------------------------------------------------------------

SUPPORTED_LOCALES: Dict[str, str] = {
    "tr": "Türkçe",
    "en": "English",
    "de": "Deutsch",
    "fr": "Français",
    "ar": "العربية",
}

DEFAULT_LOCALE: str = "tr"
FALLBACK_LOCALE: str = "en"

# Sağdan sola yazılan dil kodları
_RTL_LOCALES = {"ar", "he", "fa", "ur"}

# Locale dosyaları için varsayılan dizin (proje kökünden göreli)
_DEFAULT_LOCALES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "static", "locales",
)

# ---------------------------------------------------------------------------
# Gömülü yedek çeviriler (locale dosyası bulunamazsa kullanılır)
# ---------------------------------------------------------------------------

_BUILTIN_TRANSLATIONS: Dict[str, Dict] = {
    "tr": {
        "app": {
            "name": "SyntheticBankData",
            "version": "Sürüm",
            "loading": "Yükleniyor...",
            "error": "Hata",
            "success": "Başarılı",
            "warning": "Uyarı",
            "info": "Bilgi",
            "save": "Kaydet",
            "cancel": "İptal",
            "delete": "Sil",
            "edit": "Düzenle",
            "create": "Oluştur",
            "back": "Geri",
            "next": "İleri",
            "close": "Kapat",
            "search": "Ara",
            "filter": "Filtrele",
            "export": "Dışa Aktar",
            "import": "İçe Aktar",
            "refresh": "Yenile",
        },
        "dashboard": {
            "title": "Gösterge Paneli",
            "welcome": "Hoş Geldiniz, {name}",
            "total_rows": "Toplam Satır",
            "total_columns": "Toplam Sütun",
            "quality_score": "Kalite Skoru",
            "last_updated": "Son Güncelleme",
        },
        "quality": {
            "title": "Veri Kalitesi",
            "analysis": "Kalite Analizi",
            "score": "Kalite Skoru",
            "null_ratio": "Null Oranı",
            "unique_count": "Tekil Değer Sayısı",
            "anomaly_count": "Anomali Sayısı",
            "anomaly_count_one": "{count} anomali",
            "anomaly_count_other": "{count} anomali",
        },
        "report": {
            "title": "Raporlar",
            "generate": "Rapor Oluştur",
            "download": "İndir",
            "quality_report": "Kalite Raporu",
            "test_report": "Test Raporu",
            "audit_report": "Denetim Raporu",
            "generated_at": "Oluşturulma Tarihi",
            "author": "Yazar",
            "page": "Sayfa",
        },
        "auth": {
            "login": "Giriş Yap",
            "logout": "Çıkış Yap",
            "username": "Kullanıcı Adı",
            "password": "Parola",
            "email": "E-posta",
            "forgot_password": "Parolamı Unuttum",
            "register": "Kayıt Ol",
            "invalid_credentials": "Geçersiz kullanıcı adı veya parola",
            "session_expired": "Oturumunuz sona erdi, lütfen tekrar giriş yapın",
        },
        "errors": {
            "not_found": "Sayfa bulunamadı",
            "forbidden": "Bu işlem için yetkiniz yok",
            "server_error": "Sunucu hatası oluştu",
            "validation_error": "Doğrulama hatası: {field}",
            "required_field": "{field} alanı zorunludur",
        },
        "data": {
            "rows_one": "{count} satır",
            "rows_other": "{count} satır",
            "columns_one": "{count} sütun",
            "columns_other": "{count} sütun",
            "no_data": "Veri bulunamadı",
            "loading_data": "Veriler yükleniyor...",
        },
        "settings": {
            "title": "Ayarlar",
            "language": "Dil",
            "theme": "Tema",
            "notifications": "Bildirimler",
            "profile": "Profil",
            "security": "Güvenlik",
            "saved": "Ayarlar kaydedildi",
        },
    },
    "en": {
        "app": {
            "name": "SyntheticBankData",
            "version": "Version",
            "loading": "Loading...",
            "error": "Error",
            "success": "Success",
            "warning": "Warning",
            "info": "Info",
            "save": "Save",
            "cancel": "Cancel",
            "delete": "Delete",
            "edit": "Edit",
            "create": "Create",
            "back": "Back",
            "next": "Next",
            "close": "Close",
            "search": "Search",
            "filter": "Filter",
            "export": "Export",
            "import": "Import",
            "refresh": "Refresh",
        },
        "dashboard": {
            "title": "Dashboard",
            "welcome": "Welcome, {name}",
            "total_rows": "Total Rows",
            "total_columns": "Total Columns",
            "quality_score": "Quality Score",
            "last_updated": "Last Updated",
        },
        "quality": {
            "title": "Data Quality",
            "analysis": "Quality Analysis",
            "score": "Quality Score",
            "null_ratio": "Null Ratio",
            "unique_count": "Unique Count",
            "anomaly_count": "Anomaly Count",
            "anomaly_count_one": "{count} anomaly",
            "anomaly_count_other": "{count} anomalies",
        },
        "report": {
            "title": "Reports",
            "generate": "Generate Report",
            "download": "Download",
            "quality_report": "Quality Report",
            "test_report": "Test Report",
            "audit_report": "Audit Report",
            "generated_at": "Generated At",
            "author": "Author",
            "page": "Page",
        },
        "auth": {
            "login": "Login",
            "logout": "Logout",
            "username": "Username",
            "password": "Password",
            "email": "Email",
            "forgot_password": "Forgot Password",
            "register": "Register",
            "invalid_credentials": "Invalid username or password",
            "session_expired": "Your session has expired, please log in again",
        },
        "errors": {
            "not_found": "Page not found",
            "forbidden": "You do not have permission for this action",
            "server_error": "A server error occurred",
            "validation_error": "Validation error: {field}",
            "required_field": "{field} is required",
        },
        "data": {
            "rows_one": "{count} row",
            "rows_other": "{count} rows",
            "columns_one": "{count} column",
            "columns_other": "{count} columns",
            "no_data": "No data found",
            "loading_data": "Loading data...",
        },
        "settings": {
            "title": "Settings",
            "language": "Language",
            "theme": "Theme",
            "notifications": "Notifications",
            "profile": "Profile",
            "security": "Security",
            "saved": "Settings saved",
        },
    },
    "de": {
        "app": {
            "name": "SyntheticBankData",
            "version": "Version",
            "loading": "Wird geladen...",
            "error": "Fehler",
            "success": "Erfolg",
            "warning": "Warnung",
            "info": "Info",
            "save": "Speichern",
            "cancel": "Abbrechen",
            "delete": "Löschen",
            "edit": "Bearbeiten",
            "create": "Erstellen",
            "back": "Zurück",
            "next": "Weiter",
            "close": "Schließen",
            "search": "Suchen",
            "filter": "Filtern",
            "export": "Exportieren",
            "import": "Importieren",
            "refresh": "Aktualisieren",
        },
        "dashboard": {
            "title": "Übersicht",
            "welcome": "Willkommen, {name}",
            "total_rows": "Gesamtzeilen",
            "total_columns": "Gesamtspalten",
            "quality_score": "Qualitätswert",
            "last_updated": "Zuletzt aktualisiert",
        },
        "errors": {
            "not_found": "Seite nicht gefunden",
            "forbidden": "Sie haben keine Berechtigung für diese Aktion",
            "server_error": "Ein Serverfehler ist aufgetreten",
            "validation_error": "Validierungsfehler: {field}",
            "required_field": "{field} ist erforderlich",
        },
        "data": {
            "rows_one": "{count} Zeile",
            "rows_other": "{count} Zeilen",
            "columns_one": "{count} Spalte",
            "columns_other": "{count} Spalten",
            "no_data": "Keine Daten gefunden",
            "loading_data": "Daten werden geladen...",
        },
    },
    "fr": {
        "app": {
            "name": "SyntheticBankData",
            "version": "Version",
            "loading": "Chargement...",
            "error": "Erreur",
            "success": "Succès",
            "warning": "Avertissement",
            "info": "Info",
            "save": "Enregistrer",
            "cancel": "Annuler",
            "delete": "Supprimer",
            "edit": "Modifier",
            "create": "Créer",
            "back": "Retour",
            "next": "Suivant",
            "close": "Fermer",
            "search": "Rechercher",
            "filter": "Filtrer",
            "export": "Exporter",
            "import": "Importer",
            "refresh": "Actualiser",
        },
        "dashboard": {
            "title": "Tableau de bord",
            "welcome": "Bienvenue, {name}",
            "total_rows": "Total des lignes",
            "total_columns": "Total des colonnes",
            "quality_score": "Score de qualité",
            "last_updated": "Dernière mise à jour",
        },
        "errors": {
            "not_found": "Page introuvable",
            "forbidden": "Vous n'avez pas la permission pour cette action",
            "server_error": "Une erreur serveur s'est produite",
            "validation_error": "Erreur de validation : {field}",
            "required_field": "{field} est obligatoire",
        },
        "data": {
            "rows_one": "{count} ligne",
            "rows_other": "{count} lignes",
            "columns_one": "{count} colonne",
            "columns_other": "{count} colonnes",
            "no_data": "Aucune donnée trouvée",
            "loading_data": "Chargement des données...",
        },
    },
    "ar": {
        "app": {
            "name": "SyntheticBankData",
            "version": "الإصدار",
            "loading": "جار التحميل...",
            "error": "خطأ",
            "success": "نجاح",
            "warning": "تحذير",
            "info": "معلومة",
            "save": "حفظ",
            "cancel": "إلغاء",
            "delete": "حذف",
            "edit": "تعديل",
            "create": "إنشاء",
            "back": "رجوع",
            "next": "التالي",
            "close": "إغلاق",
            "search": "بحث",
            "filter": "تصفية",
            "export": "تصدير",
            "import": "استيراد",
            "refresh": "تحديث",
        },
        "dashboard": {
            "title": "لوحة التحكم",
            "welcome": "مرحباً، {name}",
            "total_rows": "إجمالي الصفوف",
            "total_columns": "إجمالي الأعمدة",
            "quality_score": "درجة الجودة",
            "last_updated": "آخر تحديث",
        },
        "errors": {
            "not_found": "الصفحة غير موجودة",
            "forbidden": "ليس لديك صلاحية لهذا الإجراء",
            "server_error": "حدث خطأ في الخادم",
            "validation_error": "خطأ في التحقق: {field}",
            "required_field": "{field} مطلوب",
        },
        "data": {
            "rows_one": "{count} صف",
            "rows_other": "{count} صفوف",
            "columns_one": "{count} عمود",
            "columns_other": "{count} أعمدة",
            "no_data": "لا توجد بيانات",
            "loading_data": "جار تحميل البيانات...",
        },
    },
}


# ---------------------------------------------------------------------------
# I18nService
# ---------------------------------------------------------------------------

class I18nService:
    """
    Çok dilli metin çözümleme ve biçimlendirme servisi.

    JSON locale dosyalarını yükler, bellekte önbelleğe alır,
    nokta gösterimiyle anahtar çözümler ve parametre ikamesi yapar.
    """

    def __init__(self, locales_dir: str = None):
        """
        Servis başlatıcı.

        Parametreler
        ------------
        locales_dir : str, optional
            Locale JSON dosyalarının bulunduğu dizin.
            Belirtilmezse varsayılan olarak app/static/locales/ kullanılır.
        """
        self.locales_dir = locales_dir or _DEFAULT_LOCALES_DIR
        self._cache: Dict[str, dict] = {}
        self._current_locale: str = DEFAULT_LOCALE
        self._load_all_locales()

    # ------------------------------------------------------------------
    # Locale yükleme
    # ------------------------------------------------------------------

    def load_locale(self, lang: str) -> dict:
        """
        Belirtilen dil için çeviri sözlüğünü yükler ve önbelleğe alır.

        Önce locale dizinindeki JSON dosyasına bakar; bulamazsa gömülü
        yedek çevirileri kullanır.

        Parametreler
        ------------
        lang : str
            Dil kodu (örn. "tr", "en").

        Döndürür
        --------
        dict
            Çeviri sözlüğü.
        """
        if lang in self._cache:
            return self._cache[lang]

        # Dosyadan yüklemeyi dene
        locale_file = os.path.join(self.locales_dir, f"{lang}.json")
        if os.path.isfile(locale_file):
            try:
                with open(locale_file, encoding="utf-8") as f:
                    data = json.load(f)
                self._cache[lang] = data
                logger.debug("Locale dosyası yüklendi: %s", locale_file)
                return data
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning("Locale dosyası okunamadı (%s): %s", locale_file, exc)

        # Gömülü yedek çevirileri kullan
        if lang in _BUILTIN_TRANSLATIONS:
            self._cache[lang] = _BUILTIN_TRANSLATIONS[lang]
            logger.debug("Gömülü locale kullanıldı: %s", lang)
            return self._cache[lang]

        # Fallback diline geç
        if lang != FALLBACK_LOCALE:
            logger.warning("Locale bulunamadı (%s), fallback: %s", lang, FALLBACK_LOCALE)
            return self.load_locale(FALLBACK_LOCALE)

        # Son çare: boş sözlük
        self._cache[lang] = {}
        return {}

    def _load_all_locales(self):
        """
        Desteklenen tüm locale'leri önceden yükler (eager loading).

        Uygulama başlangıcında çağrılır; tüm dil dosyalarını önbelleğe alır.
        """
        for lang in SUPPORTED_LOCALES:
            self.load_locale(lang)

    def reload_locales(self):
        """
        Önbelleği temizleyerek tüm locale'leri yeniden yükler.

        Geliştirme ortamında locale dosyaları güncellendiğinde
        yeniden yükleme (hot-reload) için kullanılır.
        """
        self._cache.clear()
        self._load_all_locales()
        logger.info("Tüm locale'ler yeniden yüklendi.")

    # ------------------------------------------------------------------
    # Temel metin alma
    # ------------------------------------------------------------------

    def get_text(self, key: str, lang: str = None, **params) -> str:
        """
        Verilen anahtara karşılık gelen çeviriyi döndürür.

        Nokta gösterimiyle iç içe anahtarları destekler
        (örn. "dashboard.title").

        Parametreler
        ------------
        key : str
            Çeviri anahtarı. Nokta ile ayrılmış iç içe anahtarlar desteklenir.
        lang : str, optional
            Dil kodu. Belirtilmezse varsayılan locale kullanılır.
        **params
            Metin içindeki {parametre_adı} yer tutucularını doldurmak
            için anahtar-değer çiftleri.

        Döndürür
        --------
        str
            Çevrilmiş ve parametreler ikame edilmiş metin.
            Anahtar bulunamazsa anahtar dizisinin kendisi döndürülür.
        """
        resolved_lang = lang or self._current_locale
        translations = self.load_locale(resolved_lang)
        text = self._resolve_key(translations, key)

        if text is None and resolved_lang != FALLBACK_LOCALE:
            # Fallback dilde dene
            fallback_translations = self.load_locale(FALLBACK_LOCALE)
            text = self._resolve_key(fallback_translations, key)

        if text is None:
            logger.debug("Çeviri anahtarı bulunamadı: %s (lang=%s)", key, resolved_lang)
            return key

        if params:
            text = self._substitute_params(text, params)

        return text

    def get_plural(self, key: str, count: int, lang: str = None) -> str:
        """
        Sayıya göre uygun çoğul form çevirisini döndürür.

        {key}_one (tekil), {key}_other (çoğul), {key}_zero (sıfır)
        biçiminde tanımlanmış anahtarları arar.

        Parametreler
        ------------
        key : str
            Temel çeviri anahtarı.
        count : int
            Öğe sayısı; çoğul form seçiminde kullanılır.
        lang : str, optional
            Dil kodu.

        Döndürür
        --------
        str
            Uygun çoğul form metni; bulunamazsa temel anahtar metni.
        """
        resolved_lang = lang or self._current_locale

        # Uygun form anahtarını belirle
        if count == 0:
            form_key = f"{key}_zero"
        elif count == 1:
            form_key = f"{key}_one"
        else:
            form_key = f"{key}_other"

        translations = self.load_locale(resolved_lang)
        text = self._resolve_key(translations, form_key)

        # Bulunamazsa _other'a düş
        if text is None:
            text = self._resolve_key(translations, f"{key}_other")

        # Hâlâ bulunamazsa temel anahtarı dene
        if text is None:
            text = self._resolve_key(translations, key)

        # Fallback
        if text is None and resolved_lang != FALLBACK_LOCALE:
            return self.get_plural(key, count, FALLBACK_LOCALE)

        if text is None:
            return key

        return self._substitute_params(text, {"count": count})

    def get_with_params(self, key: str, params: dict, lang: str = None) -> str:
        """
        Çeviri metnini sözlük parametreleriyle döndürür.

        Parametreler
        ------------
        key : str
            Çeviri anahtarı.
        params : dict
            Yer tutucu adı → değer eşlemeleri.
        lang : str, optional
            Dil kodu.

        Döndürür
        --------
        str
            Parametreler ikame edilmiş çeviri metni.
        """
        return self.get_text(key, lang=lang, **params)

    def get_section(self, section: str, lang: str = None) -> dict:
        """
        Belirli bir bölümün tüm çeviri anahtarlarını döndürür.

        Parametreler
        ------------
        section : str
            Bölüm adı (örn. "dashboard", "auth").
        lang : str, optional
            Dil kodu.

        Döndürür
        --------
        dict
            O bölüme ait tüm çeviri sözlüğü.
        """
        resolved_lang = lang or self._current_locale
        translations = self.load_locale(resolved_lang)
        section_data = translations.get(section, {})

        # Fallback ile birleştir
        if resolved_lang != FALLBACK_LOCALE:
            fallback = self.load_locale(FALLBACK_LOCALE)
            fallback_section = fallback.get(section, {})
            merged = {**fallback_section, **section_data}
            return merged

        return section_data

    # ------------------------------------------------------------------
    # Locale yönetimi
    # ------------------------------------------------------------------

    def set_locale(self, lang: str):
        """
        Bu servis örneği için varsayılan dili ayarlar.

        Parametreler
        ------------
        lang : str
            Dil kodu. SUPPORTED_LOCALES içinde olmalıdır.

        Uyarı
        -----
        Desteklenmeyen bir dil kodu verilirse varsayılan locale korunur.
        """
        if lang in SUPPORTED_LOCALES:
            self._current_locale = lang
            logger.debug("Locale ayarlandı: %s", lang)
        else:
            logger.warning("Desteklenmeyen locale: %s; varsayılan korundu: %s",
                           lang, self._current_locale)

    def get_supported_locales(self) -> List[dict]:
        """
        Desteklenen dillerin listesini döndürür.

        Döndürür
        --------
        List[dict]
            Her öğe: {"code": str, "name": str, "rtl": bool}
        """
        return [
            {
                "code": code,
                "name": name,
                "rtl": self.is_rtl(code),
            }
            for code, name in SUPPORTED_LOCALES.items()
        ]

    def is_rtl(self, lang: str) -> bool:
        """
        Verilen dilin sağdan sola (RTL) yazıldığını kontrol eder.

        Parametreler
        ------------
        lang : str
            Dil kodu.

        Döndürür
        --------
        bool
            True ise Arapça/İbranice gibi RTL dildir.
        """
        return lang.lower() in _RTL_LOCALES

    # ------------------------------------------------------------------
    # Sayı, tarih ve para birimi biçimlendirme
    # ------------------------------------------------------------------

    def format_number(self, value: float, lang: str = None) -> str:
        """
        Sayıyı locale'e uygun biçimde biçimlendirir.

        Türkçe ve bazı Avrupa dillerinde ondalık ayracı olarak virgül,
        binlik ayraç olarak nokta kullanılır.

        Parametreler
        ------------
        value : float
            Biçimlendirilecek sayı.
        lang : str, optional
            Dil kodu.

        Döndürür
        --------
        str
            Biçimlendirilmiş sayı dizesi.
        """
        resolved_lang = lang or self._current_locale

        # Ondalık ve binlik ayraç kuralları
        dot_decimal_langs = {"en"}   # noktayı ondalık ayraç olarak kullananlar
        comma_decimal_langs = {"tr", "de", "fr", "ar"}

        try:
            if resolved_lang in dot_decimal_langs:
                # 1,234,567.89
                formatted = f"{value:,.2f}"
            elif resolved_lang in comma_decimal_langs:
                # 1.234.567,89
                formatted = f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            else:
                formatted = f"{value:,.2f}"
        except (ValueError, TypeError):
            formatted = str(value)

        return formatted

    def format_date(
        self,
        dt: datetime,
        lang: str = None,
        format: str = "short",
    ) -> str:
        """
        Tarih nesnesini locale'e uygun biçimde biçimlendirir.

        Parametreler
        ------------
        dt : datetime
            Biçimlendirilecek tarih.
        lang : str, optional
            Dil kodu.
        format : str
            "short" (GG.AA.YYYY veya MM/DD/YYYY), "long" (tam ad), "iso".

        Döndürür
        --------
        str
            Biçimlendirilmiş tarih dizesi.
        """
        resolved_lang = lang or self._current_locale

        if not isinstance(dt, datetime):
            return str(dt)

        if format == "iso":
            return dt.isoformat()

        if format == "long":
            month_names = {
                "tr": ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
                        "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"],
                "en": ["January", "February", "March", "April", "May", "June",
                        "July", "August", "September", "October", "November", "December"],
                "de": ["Januar", "Februar", "März", "April", "Mai", "Juni",
                        "Juli", "August", "September", "Oktober", "November", "Dezember"],
                "fr": ["janvier", "février", "mars", "avril", "mai", "juin",
                        "juillet", "août", "septembre", "octobre", "novembre", "décembre"],
                "ar": ["يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو",
                        "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"],
            }
            months = month_names.get(resolved_lang, month_names["en"])
            month_name = months[dt.month - 1]
            if resolved_lang == "tr":
                return f"{dt.day} {month_name} {dt.year}"
            elif resolved_lang == "de":
                return f"{dt.day}. {month_name} {dt.year}"
            elif resolved_lang == "fr":
                return f"{dt.day} {month_name} {dt.year}"
            elif resolved_lang == "ar":
                return f"{dt.day} {month_name} {dt.year}"
            else:
                return f"{month_name} {dt.day}, {dt.year}"

        # short format
        if resolved_lang in ("tr", "de"):
            return dt.strftime("%d.%m.%Y")
        elif resolved_lang == "en":
            return dt.strftime("%m/%d/%Y")
        elif resolved_lang == "fr":
            return dt.strftime("%d/%m/%Y")
        elif resolved_lang == "ar":
            return dt.strftime("%d/%m/%Y")
        else:
            return dt.strftime("%Y-%m-%d")

    def format_currency(
        self,
        amount: float,
        currency: str = "TRY",
        lang: str = None,
    ) -> str:
        """
        Para miktarını locale'e uygun biçimde biçimlendirir.

        Parametreler
        ------------
        amount : float
            Para miktarı.
        currency : str
            ISO 4217 para birimi kodu (örn. "TRY", "USD", "EUR").
        lang : str, optional
            Dil kodu.

        Döndürür
        --------
        str
            Biçimlendirilmiş para dizesi.
        """
        resolved_lang = lang or self._current_locale

        # Para birimi sembolleri
        currency_symbols = {
            "TRY": "₺",
            "USD": "$",
            "EUR": "€",
            "GBP": "£",
            "JPY": "¥",
            "CHF": "Fr",
            "AED": "د.إ",
            "SAR": "﷼",
        }
        symbol = currency_symbols.get(currency.upper(), currency)

        formatted_amount = self.format_number(amount, lang=resolved_lang)

        # Sembol konumu: bazı dillerde önde, bazılarında arkada
        if resolved_lang in ("en",):
            return f"{symbol}{formatted_amount}"
        elif resolved_lang == "tr":
            return f"{formatted_amount} {symbol}"
        elif resolved_lang == "de":
            return f"{formatted_amount} {symbol}"
        elif resolved_lang == "fr":
            return f"{formatted_amount} {symbol}"
        elif resolved_lang == "ar":
            return f"{formatted_amount} {symbol}"
        else:
            return f"{symbol}{formatted_amount}"

    # ------------------------------------------------------------------
    # Dahili yardımcılar
    # ------------------------------------------------------------------

    def _resolve_key(self, translations: dict, key: str) -> Optional[str]:
        """
        Nokta gösterimiyle iç içe sözlükte anahtar çözümler.

        Örneğin "dashboard.title" anahtarı, translations["dashboard"]["title"]
        değerini döndürür.

        Parametreler
        ------------
        translations : dict
            Çeviri sözlüğü.
        key : str
            Nokta ile ayrılmış anahtar yolu.

        Döndürür
        --------
        str veya None
            Bulunan değer ya da None.
        """
        if not translations or not key:
            return None

        parts = key.split(".")
        current = translations

        for part in parts:
            if not isinstance(current, dict):
                return None
            current = current.get(part)
            if current is None:
                return None

        return str(current) if not isinstance(current, dict) else None

    def _substitute_params(self, text: str, params: dict) -> str:
        """
        Metindeki {parametre_adı} yer tutucularını değerlerle değiştirir.

        Parametreler
        ------------
        text : str
            Yer tutucu içerebilen metin şablonu.
        params : dict
            Yer tutucu adı → değer eşlemeleri.

        Döndürür
        --------
        str
            Parametreler ikame edilmiş metin.
        """
        if not params:
            return text

        try:
            return text.format(**params)
        except (KeyError, ValueError, IndexError) as exc:
            logger.debug("Parametre ikame hatası (%s): %s", text, exc)
            # Başarısız format yerine regex tabanlı güvenli ikame dene
            result = text
            for k, v in params.items():
                result = result.replace(f"{{{k}}}", str(v))
            return result


# ---------------------------------------------------------------------------
# Dil Algılama
# ---------------------------------------------------------------------------

class LanguageDetector:
    """
    HTTP istek bilgisinden kullanıcının tercih ettiği dili algılayan sınıf.

    Accept-Language başlığı, URL yolu, sorgu parametresi gibi farklı
    kaynaklardan dil bilgisi çıkarır.
    """

    @staticmethod
    def from_accept_language(header: str) -> str:
        """
        HTTP Accept-Language başlığını ayrıştırır.

        Örnek giriş: "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7"

        Parametreler
        ------------
        header : str
            Accept-Language başlık değeri.

        Döndürür
        --------
        str
            En yüksek öncelikli desteklenen dil kodu.
        """
        if not header:
            return DEFAULT_LOCALE

        # "dil-BÖLGE;q=ağırlık" biçimini ayrıştır
        entries = []
        for part in header.split(","):
            part = part.strip()
            if not part:
                continue
            if ";q=" in part:
                lang_tag, q_str = part.split(";q=", 1)
                try:
                    q = float(q_str)
                except ValueError:
                    q = 0.0
            else:
                lang_tag = part
                q = 1.0
            entries.append((lang_tag.strip(), q))

        # Ağırlığa göre sırala (yüksekten düşüğe)
        entries.sort(key=lambda x: x[1], reverse=True)

        for lang_tag, _ in entries:
            # Dil kodunu normalleştir: "tr-TR" → "tr"
            lang_code = lang_tag.split("-")[0].lower()
            if lang_code in SUPPORTED_LOCALES:
                return lang_code

        return DEFAULT_LOCALE

    @staticmethod
    def from_path(path: str) -> Optional[str]:
        """
        URL yolundan dil kodunu çıkarır.

        Örnek: "/tr/dashboard" → "tr", "/en/reports" → "en"

        Parametreler
        ------------
        path : str
            URL yolu.

        Döndürür
        --------
        str veya None
            Dil kodu ya da bulunamazsa None.
        """
        if not path:
            return None

        # /dil_kodu/... biçimini dene
        match = re.match(r"^/([a-z]{2})(?:/|$)", path)
        if match:
            lang_code = match.group(1)
            if lang_code in SUPPORTED_LOCALES:
                return lang_code

        return None

    @staticmethod
    def from_query_param(params: dict) -> Optional[str]:
        """
        Sorgu parametrelerinden dil kodunu çıkarır.

        ?lang=tr veya ?locale=en gibi parametreleri arar.

        Parametreler
        ------------
        params : dict
            Sorgu parametre sözlüğü.

        Döndürür
        --------
        str veya None
            Dil kodu ya da bulunamazsa None.
        """
        if not params:
            return None

        for param_name in ("lang", "locale", "language", "l"):
            value = params.get(param_name)
            if value:
                lang_code = str(value).lower().split("-")[0]
                if lang_code in SUPPORTED_LOCALES:
                    return lang_code

        return None

    @classmethod
    def detect(cls, request_info: dict) -> str:
        """
        İstek bilgisinden dili öncelik sırasıyla algılar.

        Öncelik sırası: URL yolu → sorgu parametresi → Accept-Language → varsayılan

        Parametreler
        ------------
        request_info : dict
            Aşağıdaki anahtarları içerebilir:
            - "path": URL yolu (str)
            - "query_params": sorgu parametreleri (dict)
            - "accept_language": Accept-Language başlığı (str)

        Döndürür
        --------
        str
            Algılanan dil kodu.
        """
        # 1. URL yolundan algıla
        path = request_info.get("path", "")
        lang = cls.from_path(path)
        if lang:
            return lang

        # 2. Sorgu parametresinden algıla
        query_params = request_info.get("query_params", {})
        lang = cls.from_query_param(query_params)
        if lang:
            return lang

        # 3. Accept-Language başlığından algıla
        accept_language = request_info.get("accept_language", "")
        lang = cls.from_accept_language(accept_language)
        if lang:
            return lang

        return DEFAULT_LOCALE


# ---------------------------------------------------------------------------
# FastAPI Middleware
# ---------------------------------------------------------------------------

if HAS_FASTAPI:
    class I18nMiddleware:
        """
        FastAPI için i18n dil algılama middleware'i.

        Her gelen istekten dil bilgisini algılar ve ASGI scope
        durumuna ekler. Route handler'lar request.state.lang ile
        algılanan dile erişebilir.
        """

        def __init__(self, app, i18n_service: "I18nService"):
            """
            Middleware başlatıcı.

            Parametreler
            ------------
            app : ASGI uygulaması
                Sarmalanacak uygulama.
            i18n_service : I18nService
                Kullanılacak i18n servis örneği.
            """
            self.app = app
            self.i18n = i18n_service

        async def __call__(self, scope, receive, send):
            """
            ASGI çağrı noktası: dili algılar, scope.state'e ekler.

            Parametreler
            ------------
            scope : dict
                ASGI bağlantı kapsamı.
            receive : callable
                ASGI receive çağrısı.
            send : callable
                ASGI send çağrısı.
            """
            if scope.get("type") == "http":
                # Yol bilgisi
                path = scope.get("path", "")

                # Sorgu parametreleri
                query_string = scope.get("query_string", b"").decode("utf-8")
                query_params: Dict[str, str] = {}
                if query_string:
                    for pair in query_string.split("&"):
                        if "=" in pair:
                            k, v = pair.split("=", 1)
                            query_params[k] = v

                # Accept-Language başlığı
                accept_language = ""
                for header_name, header_value in scope.get("headers", []):
                    if header_name.lower() == b"accept-language":
                        accept_language = header_value.decode("utf-8", errors="ignore")
                        break

                # Dil algıla
                lang = LanguageDetector.detect({
                    "path": path,
                    "query_params": query_params,
                    "accept_language": accept_language,
                })

                # Scope state'e ekle
                if "state" not in scope:
                    scope["state"] = {}
                scope["state"]["lang"] = lang
                scope["state"]["i18n"] = self.i18n

            await self.app(scope, receive, send)

else:
    class I18nMiddleware:
        """
        FastAPI bulunamadığında kullanılan yer tutucu I18nMiddleware.

        Gerçek middleware işlevi yoktur; yalnızca API uyumluluğu için
        tanımlanmıştır.
        """

        def __init__(self, app, i18n_service):
            """Başlatıcı – FastAPI yoksa işlevsizdir."""
            self.app = app
            self.i18n = i18n_service
            logger.warning("FastAPI bulunamadı; I18nMiddleware devre dışı.")

        async def __call__(self, scope, receive, send):
            """Direkt geçiş yapar."""
            await self.app(scope, receive, send)


# ---------------------------------------------------------------------------
# Jinja2 Entegrasyonu
# ---------------------------------------------------------------------------

if HAS_JINJA2:
    class Jinja2Integration:
        """
        Jinja2 şablon motoruna i18n filtre ve global fonksiyonlarını kaydeder.

        Şablonlarda {{ _('dashboard.title') }}, {{ 'data.rows'|ngettext(5) }}
        gibi kullanımları mümkün kılar.
        """

        @staticmethod
        def register_filters(env: "Environment", i18n: "I18nService", lang: str):
            """
            Jinja2 Environment nesnesine i18n filtrelerini ve global
            fonksiyonlarını kaydeder.

            Kaydedilen öğeler
            -----------------
            - _(key, **params)           : get_text kısayolu (global)
            - ngettext(key, count)       : çoğul form (global)
            - locale_number(value)       : sayı biçimlendirici (filtre)
            - locale_date(dt, fmt)       : tarih biçimlendirici (filtre)
            - locale_currency(amount, c) : para birimi biçimlendirici (filtre)

            Parametreler
            ------------
            env : jinja2.Environment
                Filtre kaydedilecek Jinja2 ortamı.
            i18n : I18nService
                Kullanılacak i18n servis örneği.
            lang : str
                Varsayılan dil kodu.
            """
            # _() global fonksiyonu
            def translate(key: str, **params) -> str:
                return i18n.get_text(key, lang=lang, **params)

            # ngettext() global fonksiyonu
            def ngettext_fn(key: str, count: int) -> str:
                return i18n.get_plural(key, count, lang=lang)

            # locale_number filtresi
            def locale_number_filter(value: float) -> str:
                return i18n.format_number(value, lang=lang)

            # locale_date filtresi
            def locale_date_filter(dt: datetime, fmt: str = "short") -> str:
                return i18n.format_date(dt, lang=lang, format=fmt)

            # locale_currency filtresi
            def locale_currency_filter(amount: float, currency: str = "TRY") -> str:
                return i18n.format_currency(amount, currency=currency, lang=lang)

            # Kayıt işlemleri
            env.globals["_"] = translate
            env.globals["ngettext"] = ngettext_fn
            env.filters["locale_number"] = locale_number_filter
            env.filters["locale_date"] = locale_date_filter
            env.filters["locale_currency"] = locale_currency_filter

            logger.debug("Jinja2 i18n filtreleri kaydedildi (lang=%s)", lang)

else:
    class Jinja2Integration:
        """
        Jinja2 bulunamadığında kullanılan yer tutucu sınıf.
        """

        @staticmethod
        def register_filters(env, i18n, lang: str):
            """Jinja2 yoksa işlevsizdir."""
            logger.warning("Jinja2 bulunamadı; i18n filtreleri kaydedilmedi.")


# ---------------------------------------------------------------------------
# Çeviri Doğrulama
# ---------------------------------------------------------------------------

class TranslationValidator:
    """
    Farklı diller arasındaki çeviri tutarlılığını doğrulayan sınıf.

    Eksik ve fazladan anahtarları tespit eder, kapsam yüzdesini hesaplar.
    """

    def __init__(self, i18n_service: "I18nService"):
        """
        Başlatıcı.

        Parametreler
        ------------
        i18n_service : I18nService
            Doğrulama için kullanılacak servis örneği.
        """
        self.i18n = i18n_service

    def _flatten_keys(self, d: dict, prefix: str = "") -> List[str]:
        """
        İç içe sözlükteki tüm yaprak anahtarları nokta gösterimiyle düzleştirir.

        Parametreler
        ------------
        d : dict
            Düzleştirilecek sözlük.
        prefix : str
            Özyinelemeli çağrılarda mevcut önek.

        Döndürür
        --------
        List[str]
            Tüm yaprak anahtarların nokta gösterimli listesi.
        """
        keys = []
        for k, v in d.items():
            full_key = f"{prefix}.{k}" if prefix else k
            if isinstance(v, dict):
                keys.extend(self._flatten_keys(v, full_key))
            else:
                keys.append(full_key)
        return keys

    def find_missing_keys(
        self,
        base_lang: str = "en",
        target_lang: str = "tr",
    ) -> List[str]:
        """
        Hedef dilde eksik olan çeviri anahtarlarını bulur.

        Parametreler
        ------------
        base_lang : str
            Referans dil kodu.
        target_lang : str
            Eksik anahtarların arandığı dil kodu.

        Döndürür
        --------
        List[str]
            Base dilde olan ama target dilde olmayan anahtar listesi.
        """
        base_translations = self.i18n.load_locale(base_lang)
        target_translations = self.i18n.load_locale(target_lang)

        base_keys = set(self._flatten_keys(base_translations))
        target_keys = set(self._flatten_keys(target_translations))

        missing = sorted(base_keys - target_keys)
        return missing

    def find_extra_keys(
        self,
        base_lang: str = "en",
        target_lang: str = "tr",
    ) -> List[str]:
        """
        Hedef dilde fazladan bulunan (base dilde olmayan) anahtarları bulur.

        Parametreler
        ------------
        base_lang : str
            Referans dil kodu.
        target_lang : str
            Fazladan anahtarların arandığı dil kodu.

        Döndürür
        --------
        List[str]
            Target dilde olan ama base dilde olmayan anahtar listesi.
        """
        base_translations = self.i18n.load_locale(base_lang)
        target_translations = self.i18n.load_locale(target_lang)

        base_keys = set(self._flatten_keys(base_translations))
        target_keys = set(self._flatten_keys(target_translations))

        extra = sorted(target_keys - base_keys)
        return extra

    def validate_all(self) -> dict:
        """
        Desteklenen tüm diller için kapsam analizi yapar.

        İngilizce (en) referans alınarak her dilin eksik/fazladan
        anahtarları ve kapsam yüzdesi hesaplanır.

        Döndürür
        --------
        dict
            {lang: {"missing": [...], "extra": [...], "coverage_percent": float}}
        """
        base_lang = FALLBACK_LOCALE
        base_translations = self.i18n.load_locale(base_lang)
        base_keys = set(self._flatten_keys(base_translations))
        total_base = len(base_keys)

        results = {}
        for lang in SUPPORTED_LOCALES:
            if lang == base_lang:
                results[lang] = {
                    "missing": [],
                    "extra": [],
                    "coverage_percent": 100.0,
                }
                continue

            missing = self.find_missing_keys(base_lang, lang)
            extra = self.find_extra_keys(base_lang, lang)

            covered = total_base - len(missing)
            coverage = (covered / total_base * 100) if total_base > 0 else 0.0

            results[lang] = {
                "missing": missing,
                "extra": extra,
                "coverage_percent": round(coverage, 2),
            }

        return results


# ---------------------------------------------------------------------------
# Modül düzeyinde singleton ve kısayol fonksiyonlar
# ---------------------------------------------------------------------------

_i18n_instance: Optional[I18nService] = None


def get_i18n() -> I18nService:
    """
    Modül düzeyindeki I18nService singleton örneğini döndürür.

    İlk çağrıda yeni bir örnek oluşturur; sonraki çağrılarda aynı
    örneği döndürür.

    Döndürür
    --------
    I18nService
        Paylaşılan i18n servis örneği.
    """
    global _i18n_instance
    if _i18n_instance is None:
        _i18n_instance = I18nService()
    return _i18n_instance


def _(key: str, lang: str = None, **params) -> str:
    """
    Çeviri metni almak için modül düzeyi kısayol fonksiyon.

    Parametreler
    ------------
    key : str
        Çeviri anahtarı.
    lang : str, optional
        Dil kodu; belirtilmezse varsayılan locale kullanılır.
    **params
        Yer tutucu ikame parametreleri.

    Döndürür
    --------
    str
        Çevrilmiş metin.
    """
    return get_i18n().get_text(key, lang=lang, **params)


def ngettext(key: str, count: int, lang: str = None) -> str:
    """
    Çoğul form çevirisi için modül düzeyi kısayol fonksiyon.

    Parametreler
    ------------
    key : str
        Temel çeviri anahtarı.
    count : int
        Öğe sayısı.
    lang : str, optional
        Dil kodu.

    Döndürür
    --------
    str
        Sayıya göre seçilmiş çoğul form metni.
    """
    return get_i18n().get_plural(key, count, lang=lang)
