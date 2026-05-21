"""
Document Analyzer — BRD/FRD/User Story doküman analizi servisi.

Desteklenen doküman tipleri:
  - BRD  (Business Requirements Document)
  - FRD  (Functional Requirements Document)
  - User Story (Agile format: "As a ... I want ... so that ...")
  - Test Plan (mevcut test planlarını içe aktarma)

Ana işlevler:
  - Dokümanı parse et ve gereksinim listesi çıkar
  - Her gereksinimi öncelik, kategori ve test edilebilirlik açısından değerlendir
  - Kabul kriterlerini tespit et
  - Riskli alanları belirle
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class DocumentType(str, Enum):
    """Desteklenen doküman tipleri."""
    BRD = "brd"
    FRD = "frd"
    USER_STORY = "user_story"
    TEST_PLAN = "test_plan"
    UNKNOWN = "unknown"


class RequirementPriority(str, Enum):
    """Gereksinim öncelik seviyeleri."""
    CRITICAL = "critical"    # Must have — sistem çalışmaz
    HIGH = "high"            # Should have — önemli işlevsellik
    MEDIUM = "medium"        # Could have — kullanışlı ama opsiyonel
    LOW = "low"              # Won't have now — gelecek sürüm


class RequirementType(str, Enum):
    """Gereksinim kategorileri."""
    FUNCTIONAL = "functional"         # İşlevsel gereksinim
    NON_FUNCTIONAL = "non_functional" # Performans, güvenlik vb.
    UI_UX = "ui_ux"                   # Arayüz gereksinimleri
    SECURITY = "security"             # Güvenlik gereksinimleri
    INTEGRATION = "integration"       # Entegrasyon gereksinimleri
    DATA = "data"                     # Veri gereksinimleri
    BUSINESS_RULE = "business_rule"   # İş kuralları


@dataclass
class Requirement:
    """Tespit edilmiş tek bir gereksinim."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    title: str = ""
    description: str = ""
    req_type: RequirementType = RequirementType.FUNCTIONAL
    priority: RequirementPriority = RequirementPriority.MEDIUM
    acceptance_criteria: list[str] = field(default_factory=list)
    test_scenarios: list[str] = field(default_factory=list)
    risk_level: str = "low"         # low / medium / high
    testability_score: float = 0.0  # 0.0 — 1.0 arası
    source_line: int = 0            # Dokümandaki satır numarası
    tags: list[str] = field(default_factory=list)


@dataclass
class AnalysisResult:
    """Doküman analizi sonucu."""
    document_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    document_type: DocumentType = DocumentType.UNKNOWN
    title: str = ""
    analyzed_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    requirements: list[Requirement] = field(default_factory=list)
    total_requirements: int = 0
    high_priority_count: int = 0
    risk_areas: list[str] = field(default_factory=list)
    missing_details: list[str] = field(default_factory=list)
    coverage_score: float = 0.0     # Kapsam puanı 0.0 — 1.0
    metadata: dict[str, Any] = field(default_factory=dict)


# ────────────────────────────────────────────────────────────────────────
# Anahtar kelime listeleri
# ────────────────────────────────────────────────────────────────────────

# Öncelik belirleyen anahtar kelimeler
_CRITICAL_KEYWORDS = {"kritik", "zorunlu", "must", "shall", "required", "critical", "mandatory"}
_HIGH_KEYWORDS = {"önemli", "should", "high priority", "yüksek öncelik", "temel"}
_LOW_KEYWORDS = {"opsiyonel", "nice to have", "could", "might", "ileride", "gelecek"}

# Gereksinim tipi anahtar kelimeleri
_SECURITY_KEYWORDS = {"güvenlik", "şifre", "yetkilendirme", "kimlik", "security", "auth", "ssl", "tls", "kvkk", "gdpr"}
_PERFORMANCE_KEYWORDS = {"performans", "hız", "süre", "response time", "latency", "throughput", "sla"}
_UI_KEYWORDS = {"arayüz", "ekran", "buton", "form", "sayfa", "ui", "ux", "kullanıcı arayüzü", "responsive"}
_INTEGRATION_KEYWORDS = {"entegrasyon", "api", "web service", "soap", "rest", "kafka", "rabbitmq", "integration"}
_DATA_KEYWORDS = {"veri", "veritabanı", "data", "database", "kayıt", "rapor", "tablo"}
_BUSINESS_KEYWORDS = {"iş kuralı", "business rule", "kural", "koşul", "limit", "doğrulama", "validation"}

# Kabul kriteri kalıpları
_ACCEPTANCE_PATTERNS = [
    r"kabul kriteri[:\s]+(.+)",
    r"acceptance criteria[:\s]+(.+)",
    r"given\s+.+when\s+.+then\s+.+",
    r"✓\s*(.+)",
    r"[-•]\s*(kullanıcı .+ yapabilmeli)",
    r"[-•]\s*(sistem .+ yapmalı)",
]

# User Story kalıpları
_USER_STORY_PATTERN = re.compile(
    r"(?:bir|as\s+a|as\s+an)\s+(.+?)\s+"
    r"(?:olarak|i want to|want to)\s+(.+?)\s+"
    r"(?:istiyorum|so that|in order to)\s+(.+?)(?:\.|$)",
    re.IGNORECASE | re.DOTALL,
)

# BRD bölüm başlıkları
_BRD_SECTION_PATTERN = re.compile(
    r"^(\d+\.?\d*\.?\d*)\s+([A-ZÇŞĞÜÖIa-zçşğüöı\s]+)",
    re.MULTILINE,
)


class DocumentAnalyzer:
    """
    BRD, FRD ve User Story dokümanlarını analiz eder.

    Kullanım:
        analyzer = DocumentAnalyzer()
        result = analyzer.analyze("Kullanıcı sisteme giriş yapabilmeli.", doc_type="user_story")
    """

    def analyze(self, content: str, doc_type: str = "auto", title: str = "") -> AnalysisResult:
        """
        Doküman içeriğini analiz et ve gereksinimleri çıkar.

        Args:
            content: Doküman metni
            doc_type: "brd" | "frd" | "user_story" | "test_plan" | "auto"
            title: Doküman başlığı (opsiyonel)

        Returns:
            AnalysisResult: Tüm gereksinimleri içeren analiz sonucu
        """
        if not content or not content.strip():
            return AnalysisResult(title=title or "Boş Doküman")

        # Doküman tipini belirle
        detected_type = self._detect_doc_type(content) if doc_type == "auto" else DocumentType(doc_type)

        # Tipine göre parse et
        if detected_type == DocumentType.USER_STORY:
            requirements = self._parse_user_stories(content)
        elif detected_type in (DocumentType.BRD, DocumentType.FRD):
            requirements = self._parse_brd_frd(content)
        else:
            requirements = self._parse_generic(content)

        # Her gereksinimi zenginleştir
        for req in requirements:
            req.req_type = self._classify_requirement_type(req.description)
            req.priority = self._determine_priority(req.description)
            req.acceptance_criteria = self._extract_acceptance_criteria(req.description)
            req.testability_score = self._calculate_testability(req)
            req.risk_level = self._assess_risk(req)
            req.test_scenarios = self._generate_test_scenarios(req)

        # Sonuç nesnesini oluştur
        result = AnalysisResult(
            document_type=detected_type,
            title=title or self._extract_title(content),
            requirements=requirements,
            total_requirements=len(requirements),
            high_priority_count=sum(
                1 for r in requirements
                if r.priority in (RequirementPriority.CRITICAL, RequirementPriority.HIGH)
            ),
            risk_areas=self._identify_risk_areas(requirements),
            missing_details=self._find_missing_details(requirements),
            coverage_score=self._calculate_coverage(requirements),
        )
        return result

    # ── Doküman tipi tespiti ─────────────────────────────────────────────

    def _detect_doc_type(self, content: str) -> DocumentType:
        """İçeriğe bakarak doküman tipini tespit et."""
        lower = content.lower()
        user_story_hits = sum([
            "as a" in lower,
            "as an" in lower,
            "i want" in lower,
            "so that" in lower,
            "bir " in lower and "olarak" in lower,
            "istiyorum" in lower,
        ])
        if user_story_hits >= 2:
            return DocumentType.USER_STORY

        brd_hits = sum([
            "business requirement" in lower,
            "iş gereksinimi" in lower,
            "brd" in lower,
            "executive summary" in lower,
        ])
        if brd_hits >= 1:
            return DocumentType.BRD

        frd_hits = sum([
            "functional requirement" in lower,
            "frd" in lower,
            "use case" in lower,
            "işlevsel gereksinim" in lower,
        ])
        if frd_hits >= 1:
            return DocumentType.FRD

        return DocumentType.UNKNOWN

    # ── User Story parse ─────────────────────────────────────────────────

    def _parse_user_stories(self, content: str) -> list[Requirement]:
        """User Story formatındaki gereksinimleri parse et."""
        requirements: list[Requirement] = []

        # Satır bazlı tarama
        lines = content.split("\n")
        current_story = ""
        story_lines: list[str] = []
        line_no = 0

        for i, line in enumerate(lines):
            stripped = line.strip()
            if not stripped:
                # Boş satır — mevcut story'yi tamamla
                if story_lines:
                    req = self._build_user_story_req("\n".join(story_lines), line_no)
                    if req:
                        requirements.append(req)
                    story_lines = []
                continue

            # User story başlangıcı
            lower = stripped.lower()
            if any(lower.startswith(kw) for kw in ("as a", "as an", "bir ", "kullanıcı olarak")):
                if story_lines:
                    req = self._build_user_story_req("\n".join(story_lines), line_no)
                    if req:
                        requirements.append(req)
                story_lines = [stripped]
                line_no = i + 1
            elif story_lines:
                story_lines.append(stripped)

        # Son story
        if story_lines:
            req = self._build_user_story_req("\n".join(story_lines), line_no)
            if req:
                requirements.append(req)

        # Tek satırlı story'ler — regex ile tara
        if not requirements:
            for match in _USER_STORY_PATTERN.finditer(content):
                req = Requirement(
                    title=f"User Story: {match.group(1).strip()[:50]}",
                    description=match.group(0).strip(),
                    source_line=content[:match.start()].count("\n") + 1,
                )
                requirements.append(req)

        return requirements

    def _build_user_story_req(self, text: str, line_no: int) -> Requirement | None:
        """Birleştirilmiş user story metninden Requirement oluştur."""
        if len(text.strip()) < 10:
            return None
        # Başlık için ilk satırı kısalt
        first_line = text.split("\n")[0][:80]
        return Requirement(
            title=first_line,
            description=text,
            source_line=line_no,
            tags=["user_story"],
        )

    # ── BRD/FRD parse ───────────────────────────────────────────────────

    def _parse_brd_frd(self, content: str) -> list[Requirement]:
        """BRD/FRD dokümanını madde madde parse et."""
        requirements: list[Requirement] = []
        lines = content.split("\n")
        buffer: list[str] = []
        current_title = ""
        line_no = 0

        for i, line in enumerate(lines):
            stripped = line.strip()
            if not stripped:
                continue

            # Numaralı madde başlangıcı: "1.2 Kullanıcı Girişi" formatı
            section_match = re.match(r"^(\d+\.?\d*\.?\d*)\s+(.+)", stripped)
            if section_match and len(stripped) < 120:
                if buffer and current_title:
                    req = Requirement(
                        title=current_title[:100],
                        description="\n".join(buffer),
                        source_line=line_no,
                    )
                    requirements.append(req)
                current_title = stripped
                buffer = []
                line_no = i + 1
            # Büyük harf başlıklı satır
            elif stripped.isupper() and 5 < len(stripped) < 100:
                if buffer and current_title:
                    req = Requirement(
                        title=current_title[:100],
                        description="\n".join(buffer),
                        source_line=line_no,
                    )
                    requirements.append(req)
                current_title = stripped
                buffer = []
                line_no = i + 1
            else:
                buffer.append(stripped)

        # Son blok
        if buffer and current_title:
            req = Requirement(
                title=current_title[:100],
                description="\n".join(buffer),
                source_line=line_no,
            )
            requirements.append(req)

        # Eğer yapısal parse başarısız olduysa generic'e geç
        if not requirements:
            return self._parse_generic(content)

        return requirements

    # ── Generic parse ────────────────────────────────────────────────────

    def _parse_generic(self, content: str) -> list[Requirement]:
        """Belirsiz formatlı dokümanları satır/madde bazlı parse et."""
        requirements: list[Requirement] = []
        lines = content.split("\n")

        for i, line in enumerate(lines):
            stripped = line.strip()
            # Madde işaretli satırlar
            if re.match(r"^[-•*▶►→✓✗]\s+.{15,}", stripped):
                req = Requirement(
                    title=stripped[:80],
                    description=stripped,
                    source_line=i + 1,
                )
                requirements.append(req)
            # Numaralı maddeler
            elif re.match(r"^\d+[.)]\s+.{15,}", stripped):
                req = Requirement(
                    title=stripped[:80],
                    description=stripped,
                    source_line=i + 1,
                )
                requirements.append(req)
            # Fiil içeren uzun cümleler (gereksinim cümlesi)
            elif len(stripped) > 30 and any(
                kw in stripped.lower()
                for kw in ("yapabilmeli", "olmalı", "gerekli", "must", "should", "shall", "will")
            ):
                req = Requirement(
                    title=stripped[:80],
                    description=stripped,
                    source_line=i + 1,
                )
                requirements.append(req)

        return requirements

    # ── Sınıflama & Zenginleştirme ───────────────────────────────────────

    def _classify_requirement_type(self, text: str) -> RequirementType:
        """Gereksinim metnine bakarak tipini belirle."""
        lower = text.lower()
        if any(kw in lower for kw in _SECURITY_KEYWORDS):
            return RequirementType.SECURITY
        if any(kw in lower for kw in _PERFORMANCE_KEYWORDS):
            return RequirementType.NON_FUNCTIONAL
        if any(kw in lower for kw in _UI_KEYWORDS):
            return RequirementType.UI_UX
        if any(kw in lower for kw in _INTEGRATION_KEYWORDS):
            return RequirementType.INTEGRATION
        if any(kw in lower for kw in _DATA_KEYWORDS):
            return RequirementType.DATA
        if any(kw in lower for kw in _BUSINESS_KEYWORDS):
            return RequirementType.BUSINESS_RULE
        return RequirementType.FUNCTIONAL

    def _determine_priority(self, text: str) -> RequirementPriority:
        """Metin içindeki anahtar kelimelere göre öncelik ata."""
        lower = text.lower()
        if any(kw in lower for kw in _CRITICAL_KEYWORDS):
            return RequirementPriority.CRITICAL
        if any(kw in lower for kw in _HIGH_KEYWORDS):
            return RequirementPriority.HIGH
        if any(kw in lower for kw in _LOW_KEYWORDS):
            return RequirementPriority.LOW
        return RequirementPriority.MEDIUM

    def _extract_acceptance_criteria(self, text: str) -> list[str]:
        """Metinden kabul kriterlerini çek."""
        criteria: list[str] = []
        lower = text.lower()

        for pattern in _ACCEPTANCE_PATTERNS:
            for match in re.finditer(pattern, lower):
                crit = match.group(0).strip()
                if len(crit) > 5:
                    criteria.append(crit)

        # "Given/When/Then" Gherkin bloklarını bul
        gherkin = re.findall(
            r"(?:given|when|then|ve|and)\s+[^\n.]+",
            lower,
        )
        criteria.extend(g.strip() for g in gherkin if len(g) > 10)

        return list(dict.fromkeys(criteria))[:10]  # Tekrarsız, max 10

    def _calculate_testability(self, req: Requirement) -> float:
        """
        Gereksinimin test edilebilirlik puanını hesapla.

        Kriterler:
          - Kabul kriteri var mı?     (+0.3)
          - Ölçülebilir mi?           (+0.2)
          - Belirsiz kelime var mı?   (-0.1 her biri için)
          - Kısa mu (<20 karakter)?   (-0.2)
        """
        score = 0.5  # Taban puan

        if req.acceptance_criteria:
            score += 0.3

        # Ölçülebilirlik göstergeleri
        measurable_patterns = [r"\d+", r"%", r"saniye", r"ms", r"second", r"limit"]
        if any(re.search(p, req.description) for p in measurable_patterns):
            score += 0.2

        # Belirsiz kelimeler
        vague_words = ["hızlı", "iyi", "uygun", "bazı", "genellikle", "bazen", "efficient", "appropriate"]
        for word in vague_words:
            if word in req.description.lower():
                score -= 0.1

        # Çok kısa gereksinim
        if len(req.description) < 20:
            score -= 0.2

        return max(0.0, min(1.0, score))

    def _assess_risk(self, req: Requirement) -> str:
        """Gereksinim riskini değerlendir."""
        if req.priority == RequirementPriority.CRITICAL:
            return "high"
        if req.req_type in (RequirementType.SECURITY, RequirementType.INTEGRATION):
            return "high"
        if req.priority == RequirementPriority.HIGH:
            return "medium"
        if req.testability_score < 0.3:
            return "medium"
        return "low"

    def _generate_test_scenarios(self, req: Requirement) -> list[str]:
        """Gereksinim için temel test senaryosu önerileri üret."""
        scenarios: list[str] = []
        desc = req.description

        # Pozitif senaryo her zaman ekle
        scenarios.append(f"[Pozitif] {req.title[:60]} — başarılı akış testi")

        # Negatif senaryo — güvenlik/doğrulama gereksinimleri için
        if req.req_type in (RequirementType.SECURITY, RequirementType.FUNCTIONAL):
            scenarios.append(f"[Negatif] {req.title[:60]} — hatalı giriş testi")

        # Sınır değer — sayısal değer içeren gereksinimler
        if re.search(r"\d+", desc):
            scenarios.append(f"[Sınır Değer] {req.title[:60]} — limit değerleri testi")

        # Performans — SLA/hız gereksinimleri
        if req.req_type == RequirementType.NON_FUNCTIONAL:
            scenarios.append(f"[Performans] {req.title[:60]} — yük altında davranış testi")

        # Güvenlik — security gereksinimleri
        if req.req_type == RequirementType.SECURITY:
            scenarios.append(f"[Güvenlik] {req.title[:60]} — yetkisiz erişim testi")

        return scenarios

    # ── Yardımcı metodlar ────────────────────────────────────────────────

    def _extract_title(self, content: str) -> str:
        """Dokümanın başlığını ilk anlamlı satırdan çıkar."""
        for line in content.split("\n"):
            stripped = line.strip()
            if stripped and len(stripped) > 5:
                return stripped[:100]
        return "Analiz Edilmiş Doküman"

    def _identify_risk_areas(self, requirements: list[Requirement]) -> list[str]:
        """Yüksek riskli alanları listele."""
        areas: set[str] = set()
        for req in requirements:
            if req.risk_level == "high":
                areas.add(f"{req.req_type.value}: {req.title[:50]}")
        return list(areas)[:10]

    def _find_missing_details(self, requirements: list[Requirement]) -> list[str]:
        """Eksik veya yetersiz detaylı gereksinimleri tespit et."""
        missing: list[str] = []
        for req in requirements:
            if not req.acceptance_criteria:
                missing.append(f"[{req.id}] '{req.title[:50]}' — kabul kriteri eksik")
            if req.testability_score < 0.3:
                missing.append(f"[{req.id}] '{req.title[:50]}' — ölçülebilir kriter yok")
        return missing[:20]

    def _calculate_coverage(self, requirements: list[Requirement]) -> float:
        """Gereksinim kapsam puanını hesapla."""
        if not requirements:
            return 0.0
        avg_testability = sum(r.testability_score for r in requirements) / len(requirements)
        has_acceptance = sum(1 for r in requirements if r.acceptance_criteria)
        acceptance_ratio = has_acceptance / len(requirements)
        return round((avg_testability + acceptance_ratio) / 2, 2)
