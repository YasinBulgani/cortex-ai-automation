"""
Test Şemaları Modülü

Pydantic v2 şemaları test otomasyonu, görsel regresyon, erişilebilirlik testi
ve test kaydı/oynatması için gereken veri yapılarını tanımlar.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, validator


# Enum Tanımları
class ChangeTypeEnum(str, Enum):
    """Görsel değişim türleri."""
    identical = "identical"
    minor = "minor"
    significant = "significant"
    critical = "critical"


class A11yIssueSeverity(str, Enum):
    """Erişilebilirlik sorunu önem dereceleri."""
    critical = "critical"
    major = "major"
    minor = "minor"


class ActionTypeEnum(str, Enum):
    """Test adım türleri."""
    click = "click"
    type = "type"
    navigate = "navigate"
    wait = "wait"
    screenshot = "screenshot"
    assert_action = "assert"
    hover = "hover"
    scroll = "scroll"
    select = "select"
    submit = "submit"


class AssertionTypeEnum(str, Enum):
    """Test onaylama türleri."""
    element_visible = "element_visible"
    element_hidden = "element_hidden"
    text_contains = "text_contains"
    value_equals = "value_equals"
    url_equals = "url_equals"
    element_count = "element_count"


# Görsel Regresyon Şemaları
class VisualRegressionRequest(BaseModel):
    """
    Görsel regresyon testi isteği.

    Temel görüntünün yakalanması veya mevcut görüntüyle karşılaştırılması için.
    """
    test_name: str = Field(..., description="Test adı")
    baseline_path: Optional[str] = Field(None, description="Temel görüntü dosya yolu")
    current_path: Optional[str] = Field(None, description="Mevcut görüntü dosya yolu")
    image_data: Optional[bytes] = Field(None, description="Görüntü verileri (bytes)")
    capture_baseline: bool = Field(
        False,
        description="Temel görüntü yakalansın mı?"
    )
    generate_diff_report: bool = Field(
        True,
        description="Fark raporu oluşturulsun mu?"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Ek meta veriler"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "test_name": "login_page_visual_test",
                "current_path": "/screenshots/login_current.png",
                "baseline_path": "/screenshots/login_baseline.png",
                "generate_diff_report": True
            }
        }


class VisualRegressionResult(BaseModel):
    """
    Görsel regresyon testi sonucu.

    Karşılaştırma sonuçları ve fark bilgilerini içerir.
    """
    test_id: str = Field(..., description="Test tanımlayıcısı")
    test_name: str = Field(..., description="Test adı")
    passed: bool = Field(..., description="Test başarılı mı?")
    change_type: ChangeTypeEnum = Field(..., description="Değişim türü")
    similarity_percentage: float = Field(..., description="Benzerlik yüzdesi (0-100)")
    changed_pixels_count: int = Field(..., description="Değişen piksel sayısı")
    changed_pixels_percentage: float = Field(..., description="Değişen piksellerin yüzdesi")
    regions_affected: List[Dict[str, int]] = Field(..., description="Etkilenen bölgeler")
    baseline_path: str = Field(..., description="Temel görüntü yolu")
    current_path: str = Field(..., description="Mevcut görüntü yolu")
    diff_report_path: Optional[str] = Field(None, description="Fark raporu dosya yolu")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Test zamanı")

    class Config:
        json_schema_extra = {
            "example": {
                "test_id": "vr_test_001",
                "test_name": "login_page_visual_test",
                "passed": True,
                "change_type": "minor",
                "similarity_percentage": 98.5,
                "changed_pixels_count": 150,
                "changed_pixels_percentage": 0.02,
                "regions_affected": [{"x": 100, "y": 200, "width": 50, "height": 30}],
                "baseline_path": "/screenshots/login_baseline.png",
                "current_path": "/screenshots/login_current.png"
            }
        }


# Erişilebilirlik Şemaları
class A11yIssueDetail(BaseModel):
    """
    Erişilebilirlik sorunu detayı.

    Tespit edilen sorunun tam bilgisini içerir.
    """
    issue_type: str = Field(..., description="Sorun türü")
    severity: A11yIssueSeverity = Field(..., description="Önem derecesi")
    element_id: str = Field(..., description="Etkilenen eleman ID'si")
    element_type: str = Field(..., description="Eleman türü (button, input, vb.)")
    message: str = Field(..., description="Sorun açıklaması")
    suggestion: str = Field(..., description="Çözüm önerisi")
    location: Optional[Dict[str, Any]] = Field(None, description="Eleman konumu")


class AccessibilityCheckRequest(BaseModel):
    """
    Erişilebilirlik kontrol isteği.

    Sayfa veya bileşen erişilebilirliğini kontrol etmek için.
    """
    test_name: str = Field(..., description="Test adı")
    elements: List[Dict[str, Any]] = Field(
        ...,
        description="Kontrol edilecek HTML elemanları"
    )
    check_contrast: bool = Field(True, description="Renk kontrastı kontrol edilsin mi?")
    check_aria_labels: bool = Field(True, description="ARIA etiketleri kontrol edilsin mi?")
    check_keyboard: bool = Field(True, description="Klavye navigasyonu kontrol edilsin mi?")
    check_screen_reader: bool = Field(True, description="Ekran okuyucu uyumluluğu kontrol edilsin mi?")
    wcag_level: str = Field("AA", description="Hedef WCAG seviyesi (A, AA, AAA)")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Ek meta veriler")

    class Config:
        json_schema_extra = {
            "example": {
                "test_name": "login_form_accessibility",
                "elements": [
                    {
                        "id": "email_input",
                        "type": "input",
                        "aria_label": "Email adresi",
                        "keyboard_accessible": True
                    }
                ],
                "wcag_level": "AA"
            }
        }


class AccessibilityReport(BaseModel):
    """
    Erişilebilirlik testi raporu.

    Tüm erişilebilirlik testlerinin sonuçlarını içerir.
    """
    test_id: str = Field(..., description="Test tanımlayıcısı")
    test_name: str = Field(..., description="Test adı")
    test_date: str = Field(..., description="Test tarihi")
    total_checks: int = Field(..., description="Toplam kontrol sayısı")
    passed_checks: int = Field(..., description="Başarılan kontrol sayısı")
    failed_checks: int = Field(..., description="Başarısız kontrol sayısı")
    compliance_percentage: float = Field(..., description="Uyumluluk yüzdesi (0-100)")
    wcag_level: str = Field(..., description="Ulaşılan WCAG seviyesi")
    issues: List[A11yIssueDetail] = Field(..., description="Tespit edilen sorunlar")
    recommendations: List[str] = Field(..., description="Düzeltme önerileri")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Rapor oluşturma zamanı")

    class Config:
        json_schema_extra = {
            "example": {
                "test_id": "a11y_test_001",
                "test_name": "login_form_accessibility",
                "test_date": "2024-03-29",
                "total_checks": 15,
                "passed_checks": 13,
                "failed_checks": 2,
                "compliance_percentage": 86.7,
                "wcag_level": "AA",
                "issues": [],
                "recommendations": ["Tüm form elemanlarına aria-label ekleyin"]
            }
        }


# Test Kaydı Şemaları
class TestStepSchema(BaseModel):
    """
    Test adımı şeması.

    Tek bir test adımını temsil eder.
    """
    id: str = Field(..., description="Adım tanımlayıcısı")
    timestamp: datetime = Field(..., description="Adım zamanı")
    action: ActionTypeEnum = Field(..., description="Adım türü")
    selector: str = Field("", description="CSS/XPath seçici")
    value: Optional[str] = Field(None, description="Adımla ilişkili değer")
    duration_ms: int = Field(0, description="Adım süresi (milisaniye)")
    screenshot_path: Optional[str] = Field(None, description="Ekran görüntüsü dosya yolu")
    assertion_type: Optional[AssertionTypeEnum] = Field(None, description="Onaylama türü")
    assertion_expected: Optional[str] = Field(None, description="Beklenen onaylama değeri")
    assertion_passed: bool = Field(True, description="Onaylama başarılı mı?")
    error_message: Optional[str] = Field(None, description="Hata mesajı")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Ek meta veriler")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "step_001",
                "timestamp": "2024-03-29T10:30:00",
                "action": "click",
                "selector": "#login_button",
                "duration_ms": 100,
                "assertion_type": "element_visible",
                "assertion_expected": "login_modal"
            }
        }


class TestRecording(BaseModel):
    """
    Test kaydı şeması.

    Tamamlanmış bir test oturumunun kaydını temsil eder.
    """
    id: str = Field(..., description="Oturum tanımlayıcısı")
    name: str = Field(..., description="Test adı")
    description: Optional[str] = Field(None, description="Test açıklaması")
    created_at: datetime = Field(..., description="Oluşturma zamanı")
    started_at: Optional[datetime] = Field(None, description="Başlama zamanı")
    ended_at: Optional[datetime] = Field(None, description="Bitme zamanı")
    status: str = Field(..., description="Oturum durumu (recording, completed, failed)")
    total_duration_ms: int = Field(0, description="Toplam süre (milisaniye)")
    success_rate: float = Field(100.0, description="Başarı oranı (0-100)")
    tags: List[str] = Field(default_factory=list, description="Oturum etiketleri")
    steps: List[TestStepSchema] = Field(..., description="Test adımları")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "session_001",
                "name": "login_test",
                "description": "Login sayfasının test edilmesi",
                "created_at": "2024-03-29T10:00:00",
                "status": "completed",
                "total_duration_ms": 5000,
                "success_rate": 100.0,
                "steps": []
            }
        }


class TestSessionSummary(BaseModel):
    """
    Test oturumu özeti.

    Kaydedilmiş oturum hakkında kısa bilgi.
    """
    id: str = Field(..., description="Oturum tanımlayıcısı")
    name: str = Field(..., description="Test adı")
    created_at: datetime = Field(..., description="Oluşturma zamanı")
    started_at: Optional[datetime] = Field(None, description="Başlama zamanı")
    ended_at: Optional[datetime] = Field(None, description="Bitme zamanı")
    status: str = Field(..., description="Oturum durumu")
    total_steps: int = Field(0, description="Toplam adım sayısı")
    total_duration_ms: int = Field(0, description="Toplam süre (milisaniye)")
    success_rate: float = Field(100.0, description="Başarı oranı (0-100)")
    tags: List[str] = Field(default_factory=list, description="Oturum etiketleri")


# Test Çalıştırma Şemaları
class TestRunRequest(BaseModel):
    """
    Test çalıştırma isteği.

    Bir test otomasyonunun çalıştırılmasını isteklendirir.
    """
    test_id: str = Field(..., description="Çalıştırılacak test ID'si")
    test_name: str = Field(..., description="Çalıştırılacak test adı")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Test parametreleri")
    timeout_ms: int = Field(30000, description="Test zaman aşımı (milisaniye)")
    retry_count: int = Field(0, description="Başarısız olursa yeniden deneme sayısı")
    tags: List[str] = Field(default_factory=list, description="Test etiketleri")

    class Config:
        json_schema_extra = {
            "example": {
                "test_id": "test_001",
                "test_name": "login_test",
                "parameters": {"username": "test@example.com"},
                "timeout_ms": 30000
            }
        }


class TestRunResult(BaseModel):
    """
    Test çalıştırma sonucu.

    Bir test çalıştırmasının sonucunu temsil eder.
    """
    test_run_id: str = Field(..., description="Test çalıştırması tanımlayıcısı")
    test_id: str = Field(..., description="Test tanımlayıcısı")
    test_name: str = Field(..., description="Test adı")
    passed: bool = Field(..., description="Test başarılı mı?")
    started_at: datetime = Field(..., description="Başlama zamanı")
    ended_at: datetime = Field(..., description="Bitme zamanı")
    duration_ms: int = Field(..., description="Test süresi (milisaniye)")
    error_message: Optional[str] = Field(None, description="Hata mesajı (başarısızsa)")
    assertions_passed: int = Field(0, description="Başarılan onaylamalar")
    assertions_total: int = Field(0, description="Toplam onaylamalar")
    logs: List[str] = Field(default_factory=list, description="Test günlükleri")

    class Config:
        json_schema_extra = {
            "example": {
                "test_run_id": "run_001",
                "test_id": "test_001",
                "test_name": "login_test",
                "passed": True,
                "started_at": "2024-03-29T10:30:00",
                "ended_at": "2024-03-29T10:35:00",
                "duration_ms": 5000,
                "assertions_passed": 5,
                "assertions_total": 5
            }
        }
