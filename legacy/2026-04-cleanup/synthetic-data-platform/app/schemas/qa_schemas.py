"""
QA Engine Modülü - Pydantic Şemaları

Bu modül, QA Engine uygulaması için tüm veri modelleri ve şemaları içerir.
FastAPI ve Pydantic v2 ile uyumludur.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


# ============================
# ENUM SINIFLARI
# ============================

class TestCategory(str, Enum):
    """
    Test kategorileri.

    Test senaryolarını farklı türlere göre sınıflandırmak için kullanılır.
    """
    FUNCTIONAL = "functional"
    UI = "ui"
    API = "api"
    PERFORMANCE = "performance"
    SECURITY = "security"
    MONKEY = "monkey"


class TestPriority(str, Enum):
    """
    Test öncelikleri.

    Testlerin yürütülme sırasını ve önemini belirtir.
    """
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class TestStatus(str, Enum):
    """
    Test durumları.

    Test yürütmesinin güncel durumunu temsil eder.
    """
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"
    PENDING = "pending"
    RUNNING = "running"


class BrowserType(str, Enum):
    """
    Desteklenen tarayıcı türleri.

    Playwright tarafından desteklenen tarayıcılar.
    """
    CHROMIUM = "chromium"
    FIREFOX = "firefox"
    WEBKIT = "webkit"


# ============================
# TEST PLANI VE SENARYOLARI İÇİN ŞEMALAR
# ============================

class TestStep(BaseModel):
    """
    Tekil test adımı.

    Test senaryosunun her bir adımını temsil eder.
    Bir adım, bir aksiyonu (tıklama, yazma, vs.) ve onun doğrulanmasını içerir.
    """

    model_config = ConfigDict(json_schema_extra={"example": {
        "step_id": 1,
        "action": "click",
        "selector": "#login-button",
        "value": None,
        "assertion": "Login page should load"
    }})

    step_id: int = Field(
        ...,
        description="Adım ID'si. Her adımın benzersiz bir numarası vardır."
    )
    action: str = Field(
        ...,
        description="Yapılacak aksiyonun türü. Örn: click, type, navigate, hover, wait"
    )
    selector: Optional[str] = Field(
        default=None,
        description="CSS veya XPath seçicisi. Element bulma için kullanılır."
    )
    value: Optional[str] = Field(
        default=None,
        description="Aksiyonla birlikte kullanılan değer. Örn: 'type' aksiyonunda yazılacak metin"
    )
    assertion: Optional[str] = Field(
        default=None,
        description="Bu adımın sonunda kontrol edilmesi gereken iddia"
    )


class TestScenario(BaseModel):
    """
    Tekil test senaryosu.

    Bir test planının içindeki bireysel test senaryosu.
    Her senaryo, belirli bir işlevselliği test etmek için tasarlanmış bir dizi adımı içerir.
    """

    model_config = ConfigDict(json_schema_extra={"example": {
        "scenario_id": "scn_001",
        "name": "Kullanıcı giriş testi",
        "category": "functional",
        "steps": [],
        "priority": "critical",
        "expected_result": "Kullanıcı başarıyla giriş yapmalı"
    }})

    scenario_id: str = Field(
        ...,
        description="Senaryo benzersiz tanımlayıcı"
    )
    name: str = Field(
        ...,
        description="Senaryo adı. Anlaşılır ve açıklayıcı olmalıdır."
    )
    category: TestCategory = Field(
        ...,
        description="Test kategorisi. Senaryo türünü belirtir."
    )
    steps: List[TestStep] = Field(
        default_factory=list,
        description="Bu senaryonun adımları"
    )
    priority: TestPriority = Field(
        default=TestPriority.MEDIUM,
        description="Senaryo önceliği"
    )
    expected_result: str = Field(
        ...,
        description="Test başarılı olduğunda beklenen sonuç"
    )


class TestPlanRequest(BaseModel):
    """
    Test planı isteği.

    URL analizi ve test planı üretme isteğini temsil eder.
    Kullanıcı, test planı oluşturma için gerekli parametreleri bu model ile gönderir.
    """

    model_config = ConfigDict(json_schema_extra={"example": {
        "url": "https://example.com",
        "app_name": "E-Commerce Platform",
        "test_types": ["functional", "api"],
        "environment": "dev"
    }})

    url: str = Field(
        ...,
        description="Test edilecek URL adresi"
    )
    app_name: Optional[str] = Field(
        default=None,
        description="Uygulamanın adı (opsiyonel)"
    )
    test_types: List[TestCategory] = Field(
        default_factory=lambda: [TestCategory.FUNCTIONAL],
        description="Oluşturulacak test türleri listesi"
    )
    environment: str = Field(
        default="dev",
        description="Hedef ortam. Örn: dev, staging, prod"
    )


class TestPlanResponse(BaseModel):
    """
    Test planı yanıtı.

    Test planı oluşturma isteğine verilen yanıt.
    Oluşturulan test senaryolarını ve planın detaylarını içerir.
    """

    model_config = ConfigDict(json_schema_extra={"example": {
        "plan_id": "plan_001",
        "url": "https://example.com",
        "scenarios": [],
        "total_scenarios": 5,
        "created_at": "2026-03-29T10:00:00"
    }})

    plan_id: str = Field(
        ...,
        description="Test planının benzersiz tanımlayıcı ID'si"
    )
    url: str = Field(
        ...,
        description="Test planının hedefi olan URL adresi"
    )
    scenarios: List[TestScenario] = Field(
        default_factory=list,
        description="Plana dahil edilen test senaryoları"
    )
    total_scenarios: int = Field(
        ...,
        description="Toplam senaryo sayısı"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Test planının oluşturulma tarihi ve saati"
    )


# ============================
# MONKEY TESTING İÇİN ŞEMALAR
# ============================

class MonkeyTestConfig(BaseModel):
    """
    Monkey test konfigürasyonu.

    Rastgele ve otomatik test çalıştırmak için gerekli konfigürasyon parametreleri.
    Monkey testing, uygulamaya rastgele girdiler göndererek stabilite ve dayanıklılığını test eder.
    """

    model_config = ConfigDict(json_schema_extra={"example": {
        "url": "https://example.com",
        "duration_seconds": 300,
        "max_actions": 500,
        "include_form_fuzzing": True,
        "include_xss_check": True,
        "include_sql_injection": True,
        "viewport_sizes": ["1920x1080", "768x1024"],
        "scroll_stress": True,
        "check_console_errors": True,
        "check_broken_links": True
    }})

    url: str = Field(
        ...,
        description="Test edilecek uygulama URL'si"
    )
    duration_seconds: int = Field(
        default=60,
        description="Monkey testinin çalışma süresi (saniye)"
    )
    max_actions: int = Field(
        default=100,
        description="Maksimum rastgele aksiyonların sayısı"
    )
    include_form_fuzzing: bool = Field(
        default=True,
        description="Form fuzzing testinin dahil edilip edilmeyeceği"
    )
    include_xss_check: bool = Field(
        default=True,
        description="XSS (Cross-Site Scripting) kontrolleri yapılacak mı"
    )
    include_sql_injection: bool = Field(
        default=True,
        description="SQL Injection testlerinin dahil edilip edilmeyeceği"
    )
    viewport_sizes: List[str] = Field(
        default_factory=lambda: ["1920x1080", "768x1024"],
        description="Test edilecek viewport boyutları (width x height formatında)"
    )
    scroll_stress: bool = Field(
        default=True,
        description="Scroll stres testi yapılacak mı"
    )
    check_console_errors: bool = Field(
        default=True,
        description="Tarayıcı konsol hatalarının kontrol edilip edilmeyeceği"
    )
    check_broken_links: bool = Field(
        default=True,
        description="Kırık linklerin kontrol edilip edilmeyeceği"
    )


class ErrorInfo(BaseModel):
    """
    Hata bilgisi.

    Test sırasında bulunun hataların detaylarını içerir.
    Her hatanın türü, mesajı ve oluş tarihi kaydedilir.
    """

    model_config = ConfigDict(json_schema_extra={"example": {
        "error_type": "XSS",
        "message": "Potansiyel XSS açığı tespit edildi",
        "selector": "input#search",
        "screenshot_path": "/results/error_001.png",
        "timestamp": "2026-03-29T10:15:30",
        "severity": "high"
    }})

    error_type: str = Field(
        ...,
        description="Hata türü. Örn: XSS, SQL Injection, Console Error, Broken Link"
    )
    message: str = Field(
        ...,
        description="Hatanın açıklayıcı mesajı"
    )
    selector: Optional[str] = Field(
        default=None,
        description="Hatayla ilgili HTML elementi için seçici (varsa)"
    )
    screenshot_path: Optional[str] = Field(
        default=None,
        description="Hatanın ekran görüntüsünün yolu"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Hatanın tespit edilme tarihi ve saati"
    )
    severity: str = Field(
        default="medium",
        description="Hatanın önem derecesi: critical, high, medium, low"
    )


class MonkeyTestResult(BaseModel):
    """
    Monkey test sonucu.

    Monkey test çalıştırmasının tüm sonuçlarını ve bulunun sorunları içerir.
    Detaylı analiz ve raporlama için kullanılır.
    """

    model_config = ConfigDict(json_schema_extra={"example": {
        "test_id": "monkey_001",
        "url": "https://example.com",
        "duration": 300.5,
        "total_actions": 450,
        "errors_found": [],
        "console_errors": [],
        "broken_links": [],
        "screenshots": [],
        "memory_usage": {"initial_mb": 150, "peak_mb": 250},
        "network_failures": [],
        "summary": {}
    }})

    test_id: str = Field(
        ...,
        description="Test çalıştırmasının benzersiz ID'si"
    )
    url: str = Field(
        ...,
        description="Test edilen URL adresi"
    )
    duration: float = Field(
        ...,
        description="Test çalışma süresi (saniye)"
    )
    total_actions: int = Field(
        ...,
        description="Yürütülen toplam rastgele aksiyonların sayısı"
    )
    errors_found: List[ErrorInfo] = Field(
        default_factory=list,
        description="Tespit edilen hatalar"
    )
    console_errors: List[str] = Field(
        default_factory=list,
        description="Tarayıcı konsolundaki hata mesajları"
    )
    broken_links: List[str] = Field(
        default_factory=list,
        description="Tespit edilen kırık bağlantılar"
    )
    screenshots: List[str] = Field(
        default_factory=list,
        description="Alınan ekran görüntülerinin dosya yolları"
    )
    memory_usage: Dict[str, float] = Field(
        default_factory=dict,
        description="Bellek kullanımı metrikleri (MB cinsinden)"
    )
    network_failures: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Ağ başarısızlıkları ve bağlantı sorunları"
    )
    summary: Dict[str, Any] = Field(
        default_factory=dict,
        description="Test sonuçlarının özet istatistikleri"
    )


# ============================
# PROJE KONFIGÜRASYONU İÇİN ŞEMALAR
# ============================

class EnvironmentConfig(BaseModel):
    """
    Ortam konfigürasyonu.

    Test edilecek belirli bir ortamın (dev, staging, prod) ayarlarını içerir.
    Her ortamın farklı base URL'si ve kimlik bilgileri olabilir.
    """

    model_config = ConfigDict(json_schema_extra={"example": {
        "name": "dev",
        "base_url": "https://dev.example.com",
        "api_url": "https://api.dev.example.com",
        "credentials": {"username": "testuser", "password": "testpass"},
        "variables": {"timeout": 30, "retry_count": 3}
    }})

    name: str = Field(
        ...,
        description="Ortamın adı. Örn: dev, staging, prod"
    )
    base_url: str = Field(
        ...,
        description="Ortamın temel URL adresi"
    )
    api_url: Optional[str] = Field(
        default=None,
        description="API sunucusunun URL adresi (varsa)"
    )
    credentials: Optional[Dict[str, str]] = Field(
        default=None,
        description="Ortama erişim için kimlik bilgileri (kullanıcı adı, şifre, vs.)"
    )
    variables: Dict[str, Any] = Field(
        default_factory=dict,
        description="Ortama özel değişkenler ve ayarlar"
    )


class ProjectConfig(BaseModel):
    """
    Yeni proje scaffolding konfigürasyonu.

    QA Engine uygulamasında yeni bir test projesini yapılandırmak için kullanılır.
    Temel ayarlar, ortamlar ve test parametrelerini içerir.
    """

    model_config = ConfigDict(json_schema_extra={"example": {
        "project_name": "E-Commerce QA",
        "base_url": "https://example.com",
        "browser": "chromium",
        "headless": True,
        "parallel_workers": 4,
        "environments": [],
        "output_dir": "./test_results"
    }})

    project_name: str = Field(
        ...,
        description="Proje adı"
    )
    base_url: str = Field(
        ...,
        description="Projenin ana URL adresi"
    )
    browser: BrowserType = Field(
        default=BrowserType.CHROMIUM,
        description="Testler için kullanılacak tarayıcı"
    )
    headless: bool = Field(
        default=True,
        description="Tarayıcının başsız (headless) modda çalıştırılıp çalıştırılmayacağı"
    )
    parallel_workers: int = Field(
        default=4,
        description="Paralel test çalıştırması için işçi (worker) sayısı"
    )
    environments: List[EnvironmentConfig] = Field(
        default_factory=list,
        description="Projedeki test ortamları"
    )
    output_dir: str = Field(
        default="./test_results",
        description="Test sonuçlarının kaydedileceği dizin yolu"
    )


# ============================
# TEST SONUÇLARI VE RAPORLAMA İÇİN ŞEMALAR
# ============================

class TestResultDetail(BaseModel):
    """
    Test sonuç detayı.

    Tekil bir test senaryosunun yürütme sonuçlarının ayrıntılarını içerir.
    Her senaryo için status, duration ve hata bilgileri kaydedilir.
    """

    model_config = ConfigDict(json_schema_extra={"example": {
        "scenario_id": "scn_001",
        "scenario_name": "Kullanıcı giriş testi",
        "status": "passed",
        "duration": 5.2,
        "error_message": None,
        "screenshot": "/results/scn_001.png",
        "steps_completed": 5,
        "total_steps": 5
    }})

    scenario_id: str = Field(
        ...,
        description="Test senaryosu ID'si"
    )
    scenario_name: str = Field(
        ...,
        description="Test senaryosu adı"
    )
    status: TestStatus = Field(
        ...,
        description="Testinin sonuç durumu"
    )
    duration: float = Field(
        ...,
        description="Test çalışma süresi (saniye)"
    )
    error_message: Optional[str] = Field(
        default=None,
        description="Test başarısız olmuşsa, hata mesajı"
    )
    screenshot: Optional[str] = Field(
        default=None,
        description="Test örneklemesinin ekran görüntüsü yolu"
    )
    steps_completed: int = Field(
        ...,
        description="Tamamlanan adım sayısı"
    )
    total_steps: int = Field(
        ...,
        description="Toplam adım sayısı"
    )


class QAReport(BaseModel):
    """
    QA rapor modeli.

    Test yürütme sonrasında oluşturulan kapsamlı QA raporu.
    Testlerin başarı oranı, detaylar ve önemli metrikleri içerir.
    """

    model_config = ConfigDict(json_schema_extra={"example": {
        "report_id": "report_001",
        "test_plan_id": "plan_001",
        "execution_date": "2026-03-29T10:00:00",
        "total_tests": 25,
        "passed": 23,
        "failed": 2,
        "skipped": 0,
        "duration": 125.5,
        "pass_rate": 92.0,
        "report_formats": ["html", "json"],
        "screenshots": [],
        "details": []
    }})

    report_id: str = Field(
        ...,
        description="Raporun benzersiz tanımlayıcı ID'si"
    )
    test_plan_id: str = Field(
        ...,
        description="Bu raporu oluşturan test planının ID'si"
    )
    execution_date: datetime = Field(
        default_factory=datetime.utcnow,
        description="Test yürütme tarihi ve saati"
    )
    total_tests: int = Field(
        ...,
        description="Toplam test sayısı"
    )
    passed: int = Field(
        ...,
        description="Başarılı geçen test sayısı"
    )
    failed: int = Field(
        ...,
        description="Başarısız olan test sayısı"
    )
    skipped: int = Field(
        ...,
        description="Atlanan test sayısı"
    )
    duration: float = Field(
        ...,
        description="Tüm testlerin çalışma süresi (saniye)"
    )
    pass_rate: float = Field(
        ...,
        description="Başarı oranı (yüzde olarak)"
    )
    report_formats: List[str] = Field(
        default_factory=lambda: ["html"],
        description="Raporun üretildiği formatlar (html, json, pdf, vs.)"
    )
    screenshots: List[str] = Field(
        default_factory=list,
        description="Raporda eklenen ekran görüntüleri"
    )
    details: List[TestResultDetail] = Field(
        default_factory=list,
        description="Her bir test senaryosunun detaylı sonuçları"
    )


# ============================
# OTOMASYON SCRIPTI ÜRETİMİ İÇİN ŞEMALAR
# ============================

class GeneratedFile(BaseModel):
    """
    Üretilen dosya.

    Otomasyon scripti üretme işleminden sonra oluşturulan dosyaların içeriğini temsil eder.
    Her dosya için yol, içerik ve dosya türü kaydedilir.
    """

    model_config = ConfigDict(json_schema_extra={"example": {
        "file_path": "tests/test_login.py",
        "content": "# Üretilen test dosyası...",
        "file_type": "python"
    }})

    file_path: str = Field(
        ...,
        description="Dosyanın proje içindeki yolu"
    )
    content: str = Field(
        ...,
        description="Dosyanın tam içeriği"
    )
    file_type: str = Field(
        ...,
        description="Dosya türü. Örn: python, javascript, typescript, java"
    )


class AutomationRequest(BaseModel):
    """
    Otomasyon scripti üretim isteği.

    Test senaryolarından otomatik olarak test scripti üretmek için gerekli parametreler.
    Framework, dil ve Page Object Pattern seçeneklerini içerir.
    """

    model_config = ConfigDict(json_schema_extra={"example": {
        "test_plan_id": "plan_001",
        "framework": "playwright",
        "language": "python",
        "use_page_object": True
    }})

    test_plan_id: str = Field(
        ...,
        description="Kodun üretileceği test planının ID'si"
    )
    framework: str = Field(
        default="playwright",
        description="Test otomasyonu framework'ü. Örn: playwright, selenium, cypress, puppeteer"
    )
    language: str = Field(
        default="python",
        description="Üretilecek kodun programlama dili. Örn: python, javascript, java, csharp"
    )
    use_page_object: bool = Field(
        default=True,
        description="Page Object Model pattern kullanılacak mı"
    )


class AutomationResponse(BaseModel):
    """
    Otomasyon yanıtı.

    Otomasyon scripti üretme isteğine verilen yanıt.
    Üretilen dosyaları ve framework bilgisini içerir.
    """

    model_config = ConfigDict(json_schema_extra={"example": {
        "files": [],
        "total_files": 5,
        "framework": "playwright"
    }})

    files: List[GeneratedFile] = Field(
        ...,
        description="Üretilen kod dosyaları"
    )
    total_files: int = Field(
        ...,
        description="Toplam üretilen dosya sayısı"
    )
    framework: str = Field(
        ...,
        description="Kullanılan test otomasyonu framework'ü"
    )


# ============================
# PERFORMANS METRİKLERİ İÇİN ŞEMALAR
# ============================

class PerformanceMetrics(BaseModel):
    """
    Performans metrikleri.

    Web uygulamasının performans özelliklerini ölçen çeşitli metrikler.
    Sayfa yükleme zamanı, Core Web Vitals ve kaynak kullanımını içerir.
    """

    model_config = ConfigDict(json_schema_extra={"example": {
        "url": "https://example.com",
        "page_load_time": 2.5,
        "first_contentful_paint": 1.2,
        "largest_contentful_paint": 2.1,
        "time_to_interactive": 3.0,
        "total_blocking_time": 150.0,
        "memory_usage_mb": 85.5,
        "api_response_times": {"GET /api/users": 0.25},
        "resource_count": 45,
        "total_resource_size_kb": 2500.0
    }})

    url: str = Field(
        ...,
        description="Performans analizi yapılan URL adresi"
    )
    page_load_time: float = Field(
        ...,
        description="Sayfa tam yükleme süresi (saniye)"
    )
    first_contentful_paint: float = Field(
        ...,
        description="İlk içeriğin görüntülenme süresi - FCP (saniye)"
    )
    largest_contentful_paint: float = Field(
        ...,
        description="En büyük içeriğin görüntülenme süresi - LCP (saniye)"
    )
    time_to_interactive: float = Field(
        ...,
        description="Etkileşime hazır hale gelme süresi - TTI (saniye)"
    )
    total_blocking_time: float = Field(
        ...,
        description="Toplam engelleme süresi - TBT (milisaniye)"
    )
    memory_usage_mb: float = Field(
        ...,
        description="Bellek kullanımı (megabayt)"
    )
    api_response_times: Dict[str, float] = Field(
        default_factory=dict,
        description="API çağrılarının yanıt süreleri (saniye)"
    )
    resource_count: int = Field(
        ...,
        description="Yüklenen kaynak (resim, script, stil, vs.) sayısı"
    )
    total_resource_size_kb: float = Field(
        ...,
        description="Tüm kaynakların toplam boyutu (kilobayt)"
    )


# ============================
# TEST ÇALIŞTIRILMASI İÇİN ŞEMALAR
# ============================

class RunTestsRequest(BaseModel):
    """
    Test çalıştırma isteği.

    Mevcut bir test planını belirli bir ortamda çalıştırmak için isteği temsil eder.
    Parallelism, tags ve diğer çalıştırma seçeneklerini içerir.
    """

    model_config = ConfigDict(json_schema_extra={"example": {
        "test_plan_id": "plan_001",
        "environment": "staging",
        "parallel": True,
        "tags": ["smoke", "regression"],
        "headless": True
    }})

    test_plan_id: str = Field(
        ...,
        description="Çalıştırılacak test planının ID'si"
    )
    environment: str = Field(
        ...,
        description="Testlerin çalıştırılacağı ortam. Örn: dev, staging, prod"
    )
    parallel: bool = Field(
        default=False,
        description="Testlerin paralel olarak çalıştırılıp çalıştırılmayacağı"
    )
    tags: Optional[List[str]] = Field(
        default=None,
        description="Sadece belirtilen etiketlere sahip testleri çalıştır (opsiyonel)"
    )
    headless: bool = Field(
        default=True,
        description="Tarayıcının başsız (headless) modda çalıştırılacak mı"
    )


class RunTestsResponse(BaseModel):
    """
    Test çalıştırma yanıtı.

    Test çalıştırma isteğine verilen yanıt.
    Yürütme ID'si, durum ve tamamlandığında raporunu içerir.
    """

    model_config = ConfigDict(json_schema_extra={"example": {
        "execution_id": "exec_001",
        "status": "running",
        "report": None
    }})

    execution_id: str = Field(
        ...,
        description="Test yürütmesinin benzersiz ID'si"
    )
    status: TestStatus = Field(
        ...,
        description="Yürütmenin güncel durumu"
    )
    report: Optional[QAReport] = Field(
        default=None,
        description="Testler tamamlandığında, sonuç raporu (henüz çalışıyorsa None)"
    )


# ============================
# GENEL DURUM VE YANITLAR İÇİN ŞEMALAR
# ============================

class QAStatusResponse(BaseModel):
    """
    Genel durum yanıtı.

    API'nin çeşitli uç noktalarından genel durum bilgisini almak için kullanılır.
    Başarı/başarısızlık ve isteğe bağlı detaylı verileri içerir.
    """

    model_config = ConfigDict(json_schema_extra={"example": {
        "status": "success",
        "message": "İşlem başarıyla tamamlandı",
        "data": {"key": "value"}
    }})

    status: str = Field(
        ...,
        description="İşlemin sonuç durumu. Örn: success, error, pending"
    )
    message: str = Field(
        ...,
        description="Durum hakkında açıklayıcı mesaj"
    )
    data: Optional[Dict[str, Any]] = Field(
        default=None,
        description="İsteğe bağlı ekstra veriler (varsa)"
    )
