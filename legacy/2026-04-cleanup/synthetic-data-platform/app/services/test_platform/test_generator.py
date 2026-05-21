"""
TestGenerator — Gereksinimlerden Otomatik Test Case Üretimi

17 farklı test alanında (smoke, regression, functional, UI, API,
performance, security, exploratory vb.) test case üretir.
Her test case: başlık, açıklama, ön koşullar, adımlar, beklenen
sonuç ve öncelik içerir.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class TestType(str, Enum):
    SMOKE = "smoke"
    SANITY = "sanity"
    REGRESSION = "regression"
    FUNCTIONAL = "functional"
    INTEGRATION = "integration"
    UI = "ui"
    API = "api"
    PERFORMANCE = "performance"
    SECURITY = "security"
    ACCESSIBILITY = "accessibility"
    USABILITY = "usability"
    COMPATIBILITY = "compatibility"
    LOCALIZATION = "localization"
    DATABASE = "database"
    EXPLORATORY = "exploratory"
    BOUNDARY = "boundary"
    NEGATIVE = "negative"


class Priority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class TestStep:
    step_number: int
    action: str
    expected_result: str
    test_data: str = ""


@dataclass
class TestCase:
    id: str
    title: str
    description: str
    test_type: TestType
    priority: Priority
    preconditions: List[str]
    steps: List[TestStep]
    expected_outcome: str
    tags: List[str] = field(default_factory=list)
    estimated_duration_minutes: int = 5
    is_automatable: bool = True
    requirement_ids: List[str] = field(default_factory=list)


@dataclass
class TestSuite:
    id: str
    name: str
    description: str
    test_cases: List[TestCase]
    total_cases: int
    coverage_areas: List[str]
    estimated_total_minutes: int


class TestGenerator:
    """
    Gereksinim listesinden test case üretir.

    Desteklenen giriş tipleri:
      - Requirement nesneleri (DocumentAnalyzer çıktısı)
      - UserStory nesneleri
      - Ham metin gereksinim listesi
    """

    # Bankacılık domain'ine özgü test senaryoları
    _BANKING_SCENARIOS = [
        "Geçersiz hesap numarası girişi",
        "Yetersiz bakiye durumu",
        "Maksimum transfer limiti aşımı",
        "Eş zamanlı işlem çakışması",
        "Oturum zaman aşımı sırasında işlem",
        "TCKN format doğrulama",
        "IBAN checksum doğrulama",
        "Para birimi dönüşüm hassasiyeti",
        "Negatif tutar girişi",
        "XSS/SQL Injection denemesi",
    ]

    def generate_from_requirements(
        self,
        requirements: list,
        test_types: Optional[List[TestType]] = None,
    ) -> TestSuite:
        """
        Gereksinim listesinden test suite üretir.

        Args:
            requirements: Requirement veya UserStory nesneleri, ya da string listesi
            test_types: Üretilecek test tipleri (None ise tümü)

        Returns:
            TestSuite: Üretilen test case'leri içeren suite
        """
        if test_types is None:
            test_types = [
                TestType.FUNCTIONAL,
                TestType.NEGATIVE,
                TestType.BOUNDARY,
                TestType.SMOKE,
                TestType.REGRESSION,
            ]

        all_cases: List[TestCase] = []
        coverage_areas: set = set()

        for req in requirements:
            req_text = self._get_req_text(req)
            req_id = self._get_req_id(req)

            for t_type in test_types:
                cases = self._generate_for_type(req_text, req_id, t_type)
                all_cases.extend(cases)
                coverage_areas.add(t_type.value)

        # Smoke test'leri her zaman ekle (kritik path)
        if not any(c.test_type == TestType.SMOKE for c in all_cases):
            all_cases.extend(self._generate_smoke_tests())

        suite_id = str(uuid.uuid4())[:8]
        total_minutes = sum(c.estimated_duration_minutes for c in all_cases)

        return TestSuite(
            id=suite_id,
            name="Otomatik Üretilen Test Suite",
            description=f"{len(requirements)} gereksinimden {len(all_cases)} test case üretildi.",
            test_cases=all_cases,
            total_cases=len(all_cases),
            coverage_areas=sorted(coverage_areas),
            estimated_total_minutes=total_minutes,
        )

    def _generate_for_type(
        self, req_text: str, req_id: str, test_type: TestType
    ) -> List[TestCase]:
        """Bir gereksinim için belirli tipte test case'ler üretir."""
        generators = {
            TestType.FUNCTIONAL: self._gen_functional,
            TestType.NEGATIVE: self._gen_negative,
            TestType.BOUNDARY: self._gen_boundary,
            TestType.SMOKE: self._gen_smoke,
            TestType.REGRESSION: self._gen_regression,
            TestType.API: self._gen_api,
            TestType.SECURITY: self._gen_security,
            TestType.PERFORMANCE: self._gen_performance,
        }
        gen_fn = generators.get(test_type, self._gen_functional)
        return gen_fn(req_text, req_id)

    def _gen_functional(self, req_text: str, req_id: str) -> List[TestCase]:
        tc_id = f"TC-FUNC-{self._short_id()}"
        return [TestCase(
            id=tc_id,
            title=f"[Fonksiyonel] {req_text[:60]}",
            description=f"Gereksinim '{req_id}' için pozitif senaryo testi.",
            test_type=TestType.FUNCTIONAL,
            priority=Priority.HIGH,
            preconditions=["Kullanıcı oturum açmış olmalı", "Test ortamı hazır olmalı"],
            steps=[
                TestStep(1, "Test verilerini hazırla", "Veriler geçerli formatta hazır"),
                TestStep(2, req_text[:100], "Sistem beklenen davranışı göstermeli"),
                TestStep(3, "Sonucu doğrula", "Beklenen çıktı alınmış olmalı"),
            ],
            expected_outcome=f"Sistem '{req_text[:80]}' gereksinimini karşılar.",
            tags=["functional", req_id],
            estimated_duration_minutes=5,
            requirement_ids=[req_id],
        )]

    def _gen_negative(self, req_text: str, req_id: str) -> List[TestCase]:
        tc_id = f"TC-NEG-{self._short_id()}"
        return [TestCase(
            id=tc_id,
            title=f"[Negatif] Geçersiz veri ile {req_text[:50]}",
            description="Hatalı giriş verisiyle sistemin doğru hata mesajı üretip üretmediğini test eder.",
            test_type=TestType.NEGATIVE,
            priority=Priority.HIGH,
            preconditions=["Kullanıcı oturum açmış olmalı"],
            steps=[
                TestStep(1, "Geçersiz / boş veri gir", "Form alanı aktif"),
                TestStep(2, "İşlemi tamamlamayı dene", "Sistem işlemi engeller"),
                TestStep(3, "Hata mesajını doğrula", "Anlamlı hata mesajı görüntülenir"),
            ],
            expected_outcome="Sistem uygun hata mesajı gösterir ve işlemi tamamlamaz.",
            tags=["negative", "validation", req_id],
            estimated_duration_minutes=3,
            requirement_ids=[req_id],
        )]

    def _gen_boundary(self, req_text: str, req_id: str) -> List[TestCase]:
        tc_id = f"TC-BND-{self._short_id()}"
        return [TestCase(
            id=tc_id,
            title=f"[Sınır] Minimum/maksimum değer testi — {req_text[:50]}",
            description="Sınır değerlerinde (0, -1, max, max+1) sistemin davranışını doğrular.",
            test_type=TestType.BOUNDARY,
            priority=Priority.MEDIUM,
            preconditions=["Geçerli oturum mevcut"],
            steps=[
                TestStep(1, "Minimum sınır değerini gir (0 veya min)", "Alan min değeri kabul eder"),
                TestStep(2, "Maximum sınır değerini gir", "Alan max değeri kabul eder"),
                TestStep(3, "Max+1 değerini gir", "Sistem reddetmeli ve uyarı vermeli"),
            ],
            expected_outcome="Sınır değerlerinde sistem kurallara uygun davranır.",
            tags=["boundary", "edge-case", req_id],
            estimated_duration_minutes=4,
            requirement_ids=[req_id],
        )]

    def _gen_smoke(self, req_text: str, req_id: str) -> List[TestCase]:
        return [TestCase(
            id=f"TC-SMK-{self._short_id()}",
            title=f"[Smoke] Temel işlev çalışıyor mu — {req_text[:50]}",
            description="Kritik işlevlerin en temel düzeyde çalıştığını hızlıca doğrular.",
            test_type=TestType.SMOKE,
            priority=Priority.CRITICAL,
            preconditions=["Uygulama başlatılmış olmalı"],
            steps=[
                TestStep(1, "Uygulamayı aç", "Uygulama yüklendi"),
                TestStep(2, "Ana işlevi tetikle", "İşlev hatasız çalışır"),
            ],
            expected_outcome="Temel işlev hatasız çalışır.",
            tags=["smoke", "critical-path"],
            estimated_duration_minutes=2,
            requirement_ids=[req_id],
        )]

    def _gen_regression(self, req_text: str, req_id: str) -> List[TestCase]:
        return [TestCase(
            id=f"TC-REG-{self._short_id()}",
            title=f"[Regresyon] Mevcut işlev bozulmadı — {req_text[:50]}",
            description="Yeni değişikliklerin mevcut işlevleri bozmadığını doğrular.",
            test_type=TestType.REGRESSION,
            priority=Priority.HIGH,
            preconditions=["Önceki release ile karşılaştırma yapılabilmeli"],
            steps=[
                TestStep(1, "Mevcut senaryoyu çalıştır", "Scenario çalışır"),
                TestStep(2, "Sonucu önceki release ile karşılaştır", "Sonuçlar eşleşmeli"),
            ],
            expected_outcome="Davranış değişmemiş, regresyon yok.",
            tags=["regression"],
            estimated_duration_minutes=5,
            requirement_ids=[req_id],
        )]

    def _gen_api(self, req_text: str, req_id: str) -> List[TestCase]:
        return [TestCase(
            id=f"TC-API-{self._short_id()}",
            title=f"[API] REST endpoint doğrulama — {req_text[:50]}",
            description="İlgili API endpoint'inin doğru HTTP kodu, header ve body döndürdüğünü test eder.",
            test_type=TestType.API,
            priority=Priority.HIGH,
            preconditions=["API servisi çalışıyor olmalı", "Auth token mevcut olmalı"],
            steps=[
                TestStep(1, "POST/GET isteği gönder", "HTTP 200/201 alınır"),
                TestStep(2, "Response body'yi doğrula", "Beklenen JSON şeması döner"),
                TestStep(3, "Error case: 401/403/404 test et", "Doğru HTTP hata kodları döner"),
            ],
            expected_outcome="API kurallara uygun yanıt üretir.",
            tags=["api", "rest", req_id],
            estimated_duration_minutes=6,
            is_automatable=True,
            requirement_ids=[req_id],
        )]

    def _gen_security(self, req_text: str, req_id: str) -> List[TestCase]:
        return [TestCase(
            id=f"TC-SEC-{self._short_id()}",
            title=f"[Güvenlik] SQL/XSS injection testi — {req_text[:40]}",
            description="Giriş alanlarına zararlı payload gönderilerek güvenlik açığı araştırılır.",
            test_type=TestType.SECURITY,
            priority=Priority.CRITICAL,
            preconditions=["Test ortamı izole edilmiş olmalı"],
            steps=[
                TestStep(1, "SQL injection payload gir: ' OR 1=1--", "Sistem engeller"),
                TestStep(2, "XSS payload gir: <script>alert('xss')</script>", "Sistem encode eder"),
                TestStep(3, "CSRF token olmadan istek gönder", "403 döner"),
            ],
            expected_outcome="Sistem tüm zararlı girdileri engeller, veri sızıntısı olmaz.",
            tags=["security", "owasp", req_id],
            estimated_duration_minutes=10,
            is_automatable=True,
            requirement_ids=[req_id],
        )]

    def _gen_performance(self, req_text: str, req_id: str) -> List[TestCase]:
        return [TestCase(
            id=f"TC-PERF-{self._short_id()}",
            title=f"[Performans] Yanıt süresi SLA — {req_text[:40]}",
            description="İşlemin tanımlı SLA süresi içinde tamamlandığını doğrular.",
            test_type=TestType.PERFORMANCE,
            priority=Priority.MEDIUM,
            preconditions=["Performans test ortamı hazır", "Referans veri yüklü"],
            steps=[
                TestStep(1, "10 eş zamanlı istek gönder", "Tümü < 2 saniyede yanıt verir"),
                TestStep(2, "100 kullanıcı yükü simüle et", "Yanıt süresi < 5 saniye"),
                TestStep(3, "CPU/Memory metriklerini izle", "Kaynak kullanımı %80 altında"),
            ],
            expected_outcome="SLA gereksinimleri karşılanır, sistem stabil kalır.",
            tags=["performance", "load", req_id],
            estimated_duration_minutes=15,
            is_automatable=True,
            requirement_ids=[req_id],
        )]

    def _generate_smoke_tests(self) -> List[TestCase]:
        """Genel uygulama smoke testleri."""
        return [TestCase(
            id=f"TC-SMK-GEN-{self._short_id()}",
            title="[Smoke] Uygulama açılıyor ve ana sayfa yükleniyor",
            description="Uygulamanın başarıyla başlatıldığını ve ana sayfanın yüklendiğini doğrular.",
            test_type=TestType.SMOKE,
            priority=Priority.CRITICAL,
            preconditions=["Test ortamı hazır"],
            steps=[
                TestStep(1, "Uygulamayı başlat", "Uygulama yüklenmeye başlar"),
                TestStep(2, "Ana sayfanın yüklendiğini doğrula", "Sayfa < 3 saniyede yüklenir"),
                TestStep(3, "Ana menü öğelerinin görünür olduğunu doğrula", "Tüm menü öğeleri mevcut"),
            ],
            expected_outcome="Uygulama hatasız açılır.",
            tags=["smoke", "sanity"],
            estimated_duration_minutes=2,
        )]

    def _get_req_text(self, req) -> str:
        if isinstance(req, str):
            return req
        return getattr(req, "description", str(req))[:100]

    def _get_req_id(self, req) -> str:
        if isinstance(req, str):
            return "REQ-GEN"
        return getattr(req, "id", "REQ-GEN")

    # ── Public API (compatibility wrappers) ──────────────────────────────

    def generate_test_cases(self, requirements: list) -> list:
        """
        Gereksinim listesinden test case dict'leri üret.

        Args:
            requirements: Requirement dict veya nesne listesi.

        Returns:
            Test case dict'lerinin listesi.
            Her dict: id, title, description, steps, expected_result, priority, category.
        """
        suite = self.generate_from_requirements(requirements)
        return [self._case_to_dict(tc) for tc in suite.test_cases]

    def generate_from_user_story(self, story: str) -> list:
        """
        Tek bir user story metninden test case dict'leri üret.

        Args:
            story: User story metni (ör. "As a user I want to...").

        Returns:
            Test case dict'lerinin listesi.
            Her dict: id, title, description, steps, expected_result, priority, category.
        """
        if not story or not story.strip():
            return []
        suite = self.generate_from_requirements([story])
        return [self._case_to_dict(tc) for tc in suite.test_cases]

    @staticmethod
    def _case_to_dict(tc: "TestCase") -> dict:
        """TestCase dataclass'ini düz dict'e dönüştür."""
        return {
            "id": tc.id,
            "title": tc.title,
            "description": tc.description,
            "steps": [s.action for s in tc.steps],
            "expected_result": tc.expected_outcome,
            "priority": tc.priority.value if hasattr(tc.priority, "value") else tc.priority,
            "category": tc.test_type.value if hasattr(tc.test_type, "value") else tc.test_type,
        }

    @staticmethod
    def _short_id() -> str:
        return str(uuid.uuid4())[:6].upper()
