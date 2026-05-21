"""
FastAPI REST API endpoint tanımları.

Bankacılık sentetik veri üretim platformunun tüm API endpointlerini içerir.
Her endpoint async çalışır, Pydantic şemalarıyla doğrulanır ve Türkçe
açıklamalar ile Swagger UI'da belgelenir.

Endpointler:
  - Dosya yükleme ve veri seti yönetimi
  - Şema analizi, kolon sınıflandırma, PII tespiti
  - Kural çıkarımı, ilişki tespiti
  - Sentetik veri üretimi (standart, senaryo, doğal dil)
  - Dışa aktarım ve iş takibi
  - Sağlık kontrolü ve platform istatistikleri
"""

import os
import shutil
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import pandas as pd
from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from sqlalchemy import func as sa_func
from sqlalchemy.orm import Session

from app.config import settings
from app.models.database import get_db
from app.models.dataset import (
    ColumnProfile,
    Dataset,
    DatasetStatus,
    FileType,
    GenerationJob,
    GenerationStatus,
    InferredRule,
    TableRelationship,
)
from app.schemas.dataset import (
    AnalysisResponse,
    ClassifyResponse,
    ColumnProfileResponse,
    DatasetDetailResponse,
    DatasetListResponse,
    DatasetResponse,
    ErrorResponse,
    ExportResponse,
    GenerateDetailRequest,
    GenerationResponse,
    HealthResponse,
    JobListResponse,
    JobResponse,
    NaturalLanguageRequest,
    NaturalLanguageResponse,
    PIIDetectionResponse,
    RelationshipInferRequest,
    RelationshipInferResponse,
    RelationshipResponse,
    RuleInferResponse,
    RuleListResponse,
    RuleResponse,
    ScenarioGenerateRequest,
    ScenarioInfo,
    ScenarioListResponse,
    StatsResponse,
    UploadResponse,
)

# ═══════════════════════════════════════════════════════════════════════
# Router Tanımı
# ═══════════════════════════════════════════════════════════════════════

router = APIRouter(prefix="/api/v1", tags=["SyntheticBankData API"])

# Geçici dosya yükleme klasörü
UPLOAD_DIR = Path(tempfile.gettempdir()) / "syntheticbankdata_uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Üretilen dosyaların saklanacağı klasör
OUTPUT_DIR = Path(tempfile.gettempdir()) / "syntheticbankdata_outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Uygulama başlangıç zamanı (uptime hesabı için)
_start_time = time.time()

# Dosya uzantısı → FileType eşleştirmesi
_EXTENSION_MAP: dict[str, FileType] = {
    ".csv": FileType.CSV,
    ".xlsx": FileType.XLSX,
    ".xls": FileType.XLSX,
    ".json": FileType.JSON,
    ".sql": FileType.SQL,
    ".ddl": FileType.DDL,
}


# ═══════════════════════════════════════════════════════════════════════
# Yardımcı Fonksiyonlar
# ═══════════════════════════════════════════════════════════════════════


def _get_dataset_or_404(dataset_id: int, db: Session) -> Dataset:
    """Veri setini ID ile getir, bulunamazsa 404 döndür."""
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Veri seti bulunamadı: ID={dataset_id}",
        )
    return dataset


def _get_job_or_404(job_id: int, db: Session) -> GenerationJob:
    """Üretim görevini ID ile getir, bulunamazsa 404 döndür."""
    job = db.query(GenerationJob).filter(GenerationJob.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Üretim görevi bulunamadı: ID={job_id}",
        )
    return job


def _detect_file_type(filename: str) -> FileType:
    """Dosya uzantısından FileType enum değerini tespit et."""
    ext = Path(filename).suffix.lower()
    file_type = _EXTENSION_MAP.get(ext)
    if not file_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Desteklenmeyen dosya formatı: '{ext}'. "
                f"Desteklenen formatlar: {', '.join(_EXTENSION_MAP.keys())}"
            ),
        )
    return file_type


def _read_dataframe(file_path: str, file_type: FileType) -> pd.DataFrame:
    """Dosyayı uygun okuyucu ile DataFrame'e yükle."""
    try:
        if file_type == FileType.CSV:
            return pd.read_csv(file_path, nrows=50_000)
        elif file_type == FileType.XLSX:
            return pd.read_excel(file_path, nrows=50_000)
        elif file_type == FileType.JSON:
            return pd.read_json(file_path, lines=False)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Bu dosya formatı henüz analiz edilemiyor: {file_type.value}",
            )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Dosya okunamadı: {str(exc)}",
        )


# ═══════════════════════════════════════════════════════════════════════
# 1. DOSYA YÜKLEME VE VERİ SETİ YÖNETİMİ
# ═══════════════════════════════════════════════════════════════════════


@router.post(
    "/upload",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Dosya Yükle",
    description="CSV, Excel (.xlsx) veya JSON dosyası yükleyerek yeni bir veri seti oluşturur. "
    "Dosya sunucuya kaydedilir ve ön analiz yapılır.",
    responses={
        400: {"model": ErrorResponse, "description": "Geçersiz dosya formatı"},
        413: {"model": ErrorResponse, "description": "Dosya boyutu çok büyük"},
    },
)
async def upload_file(
    file: UploadFile = File(
        ..., description="Yüklenecek veri dosyası (CSV, XLSX, JSON)"
    ),
    name: Optional[str] = Query(
        None, description="Veri seti adı (boş bırakılırsa dosya adı kullanılır)"
    ),
    description: Optional[str] = Query(
        None, description="Veri seti açıklaması"
    ),
    db: Session = Depends(get_db),
) -> UploadResponse:
    """
    Bankacılık veri dosyası yükle.

    Desteklenen formatlar: CSV, Excel (.xlsx/.xls), JSON.
    Maksimum dosya boyutu: 50 MB.
    Yükleme sonrası veri seti kaydı oluşturulur ve satır sayısı hesaplanır.
    """
    # Dosya boyutu kontrolü
    contents = await file.read()
    file_size = len(contents)
    if file_size > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=(
                f"Dosya boyutu çok büyük: {file_size:,} byte. "
                f"Maksimum: {settings.MAX_UPLOAD_SIZE:,} byte ({settings.MAX_UPLOAD_SIZE // (1024*1024)} MB)"
            ),
        )

    # Dosya tipi kontrolü
    filename = file.filename or "unknown.csv"
    file_type = _detect_file_type(filename)

    # Dosyayı geçici klasöre kaydet
    safe_name = filename.replace(" ", "_")
    dest_path = UPLOAD_DIR / f"{int(time.time())}_{safe_name}"
    with open(dest_path, "wb") as f:
        f.write(contents)

    # Satır sayısını tespit et
    row_count: Optional[int] = None
    try:
        df = _read_dataframe(str(dest_path), file_type)
        row_count = len(df)
    except Exception:
        pass  # Satır sayısı opsiyonel, hata durumunda None kalır

    # Veritabanına kaydet
    dataset_name = name or Path(filename).stem
    dataset = Dataset(
        name=dataset_name,
        description=description,
        file_path=str(dest_path),
        file_type=file_type,
        row_count=row_count,
        status=DatasetStatus.UPLOADED,
    )
    db.add(dataset)
    db.commit()
    db.refresh(dataset)

    return UploadResponse(
        dataset_id=dataset.id,
        name=dataset.name,
        file_type=file_type,
        file_size=file_size,
        row_count=row_count,
        message=f"Dosya başarıyla yüklendi: {filename} ({file_size:,} byte)",
    )


# ═══════════════════════════════════════════════════════════════════════
# 2. ANALİZ VE SINIFLANDIRMA ENDPOINTLERİ
# ═══════════════════════════════════════════════════════════════════════


@router.post(
    "/analyze/{dataset_id}",
    response_model=AnalysisResponse,
    summary="Şema Analizi Başlat",
    description="Yüklenen veri seti için kapsamlı şema analizi yapar. "
    "Kolon tipleri, istatistikler, pattern'lar ve dağılımlar tespit edilir.",
    responses={
        404: {"model": ErrorResponse, "description": "Veri seti bulunamadı"},
        422: {"model": ErrorResponse, "description": "Dosya analiz edilemedi"},
    },
)
async def analyze_dataset(
    dataset_id: int,
    db: Session = Depends(get_db),
) -> AnalysisResponse:
    """
    Veri seti şema analizi.

    SchemaAnalyzer servisi ile tüm kolonlar analiz edilir:
    - Veri tipi tespiti (string, integer, float, date, boolean)
    - İstatistiksel profil (min, max, mean, median, std)
    - Pattern tespiti (TCKN, IBAN, telefon, email vb.)
    - Dağılım analizi (histogram, frekans)
    """
    dataset = _get_dataset_or_404(dataset_id, db)

    if not dataset.file_path or not os.path.exists(dataset.file_path):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Veri seti dosyası bulunamadı. Lütfen dosyayı tekrar yükleyin.",
        )

    # Durumu güncelle
    dataset.status = DatasetStatus.ANALYZING
    db.commit()

    try:
        # SchemaAnalyzer ile analiz
        from app.services.schema_analyzer import SchemaAnalyzer

        analyzer = SchemaAnalyzer()
        result = analyzer.analyze(dataset.file_path)

        # Mevcut profilleri temizle
        db.query(ColumnProfile).filter(
            ColumnProfile.dataset_id == dataset_id
        ).delete()

        # Kolon profillerini kaydet
        for col_analysis in result.columns:
            profile_dict = col_analysis.to_column_profile_dict()
            profile = ColumnProfile(
                dataset_id=dataset_id,
                **profile_dict,
            )
            db.add(profile)

        # Durumu güncelle
        dataset.status = DatasetStatus.ANALYZED
        dataset.row_count = result.row_count
        db.commit()
        db.refresh(dataset)

        # Profilleri tekrar çek
        profiles = (
            db.query(ColumnProfile)
            .filter(ColumnProfile.dataset_id == dataset_id)
            .all()
        )

        return AnalysisResponse(
            dataset_id=dataset_id,
            status=dataset.status,
            column_count=len(profiles),
            rule_count=0,
            relationship_count=0,
            pii_column_count=sum(1 for p in profiles if p.is_pii),
            columns=[ColumnProfileResponse.model_validate(p) for p in profiles],
            rules=[],
            relationships=[],
        )

    except HTTPException:
        raise
    except Exception as exc:
        dataset.status = DatasetStatus.FAILED
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Şema analizi sırasında hata oluştu: {str(exc)}",
        )


@router.post(
    "/classify/{dataset_id}",
    response_model=ClassifyResponse,
    summary="Kolon Sınıflandırma",
    description="Veri setindeki kolonları semantik tiplerine göre sınıflandırır. "
    "Bankacılık domainine özel 30 semantik tip desteklenir.",
    responses={
        404: {"model": ErrorResponse, "description": "Veri seti bulunamadı"},
    },
)
async def classify_columns(
    dataset_id: int,
    db: Session = Depends(get_db),
) -> ClassifyResponse:
    """
    Kolon semantik sınıflandırma.

    ColumnClassifier servisi ile her kolon için semantik tip belirlenir:
    - Ad-soyad, TC kimlik, IBAN, email, telefon
    - Bakiye, tutar, kredi notu, faiz oranı
    - Hesap tipi, segment, durum, kanal
    """
    dataset = _get_dataset_or_404(dataset_id, db)

    profiles = (
        db.query(ColumnProfile)
        .filter(ColumnProfile.dataset_id == dataset_id)
        .all()
    )

    if not profiles:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Önce şema analizi yapılmalıdır. POST /api/v1/analyze/{dataset_id}",
        )

    try:
        from app.services.column_classifier import ColumnClassifier
        from app.services.schema_analyzer import ColumnAnalysis

        classifier = ColumnClassifier()
        classifications = []

        for profile in profiles:
            # ColumnProfile'dan ColumnAnalysis oluştur
            col_analysis = ColumnAnalysis(
                name=profile.name,
                data_type=profile.data_type,
                semantic_type=profile.semantic_type,
                null_ratio=profile.null_ratio or 0.0,
                distinct_ratio=profile.distinct_ratio or 0.0,
                sample_values=profile.sample_values.get("values", []) if profile.sample_values else [],
                statistics=profile.statistics or {},
                pattern=profile.pattern,
            )
            result = classifier.classify(col_analysis)
            result_dict = classifier.classify_to_dict(col_analysis)

            # Profildeki semantik tipi güncelle
            if result.semantic_type:
                profile.semantic_type = result.semantic_type.value

            classifications.append(result_dict)

        db.commit()

        return ClassifyResponse(
            dataset_id=dataset_id,
            column_count=len(classifications),
            classifications=classifications,
            message=f"{len(classifications)} kolon başarıyla sınıflandırıldı",
        )

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Kolon sınıflandırma sırasında hata oluştu: {str(exc)}",
        )


@router.post(
    "/detect-pii/{dataset_id}",
    response_model=PIIDetectionResponse,
    summary="PII Tespiti",
    description="Veri setindeki kişisel verileri (PII) tespit eder. "
    "KVKK (6698 sayılı kanun) kategorilerine göre sınıflandırma yapar.",
    responses={
        404: {"model": ErrorResponse, "description": "Veri seti bulunamadı"},
    },
)
async def detect_pii(
    dataset_id: int,
    db: Session = Depends(get_db),
) -> PIIDetectionResponse:
    """
    PII (Kişisel Bilgi) tespiti.

    PIIDetector servisi ile her kolon için:
    - PII kategorisi (kritik, yüksek, orta, düşük)
    - KVKK veri kategorisi (kimlik, iletişim, finansal vb.)
    - Önerilen aksiyon (sentezle, maskele, hashle)
    - Risk skoru hesaplaması
    """
    dataset = _get_dataset_or_404(dataset_id, db)

    profiles = (
        db.query(ColumnProfile)
        .filter(ColumnProfile.dataset_id == dataset_id)
        .all()
    )

    if not profiles:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Önce şema analizi yapılmalıdır. POST /api/v1/analyze/{dataset_id}",
        )

    try:
        from app.services.pii_detector import PIIDetector
        from app.services.schema_analyzer import ColumnAnalysis

        detector = PIIDetector()
        detections = []

        for profile in profiles:
            col_analysis = ColumnAnalysis(
                name=profile.name,
                data_type=profile.data_type,
                semantic_type=profile.semantic_type,
                null_ratio=profile.null_ratio or 0.0,
                distinct_ratio=profile.distinct_ratio or 0.0,
                sample_values=profile.sample_values.get("values", []) if profile.sample_values else [],
                statistics=profile.statistics or {},
                pattern=profile.pattern,
            )
            result = detector.detect(col_analysis)
            result_dict = detector.detect_to_dict(col_analysis)

            # Profildeki PII bilgilerini güncelle
            profile.is_pii = result.is_pii
            if result.category:
                from app.models.dataset import PIILevel

                level_map = {
                    "CRITICAL": PIILevel.CRITICAL,
                    "HIGH": PIILevel.HIGH,
                    "MEDIUM": PIILevel.MEDIUM,
                    "LOW": PIILevel.LOW,
                    "NONE": PIILevel.NONE,
                }
                profile.pii_level = level_map.get(
                    result.category.value if hasattr(result.category, "value") else str(result.category),
                    PIILevel.NONE,
                )

            detections.append(result_dict)

        db.commit()

        # Rapor oluştur
        pii_columns = sum(1 for d in detections if d.get("is_pii", False))
        risk_score = 0.0
        kvkk_summary: dict[str, Any] = {}

        try:
            all_analyses = []
            for profile in profiles:
                all_analyses.append(
                    ColumnAnalysis(
                        name=profile.name,
                        data_type=profile.data_type,
                        semantic_type=profile.semantic_type,
                        null_ratio=profile.null_ratio or 0.0,
                        distinct_ratio=profile.distinct_ratio or 0.0,
                        sample_values=profile.sample_values.get("values", []) if profile.sample_values else [],
                        statistics=profile.statistics or {},
                        pattern=profile.pattern,
                    )
                )
            report = detector.analyze_dataset(dataset.name, all_analyses)
            risk_score = report.risk_score
            kvkk_summary = report.kvkk_summary if hasattr(report, "kvkk_summary") else {}
        except Exception:
            pass  # Rapor opsiyonel

        return PIIDetectionResponse(
            dataset_id=dataset_id,
            total_columns=len(profiles),
            pii_columns=pii_columns,
            risk_score=risk_score,
            detections=detections,
            kvkk_summary=kvkk_summary if kvkk_summary else None,
            message=f"PII tespiti tamamlandı: {pii_columns}/{len(profiles)} kolon PII içeriyor",
        )

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"PII tespiti sırasında hata oluştu: {str(exc)}",
        )


# ═══════════════════════════════════════════════════════════════════════
# 3. KURAL ÇIKARIMI VE İLİŞKİ TESPİTİ
# ═══════════════════════════════════════════════════════════════════════


@router.post(
    "/infer-rules/{dataset_id}",
    response_model=RuleInferResponse,
    summary="Kural Çıkarımı",
    description="Veri setinden otomatik iş kuralları çıkarır. "
    "Aralık, enum, regex, dağılım ve bağımlılık kuralları tespit edilir.",
    responses={
        404: {"model": ErrorResponse, "description": "Veri seti bulunamadı"},
    },
)
async def infer_rules(
    dataset_id: int,
    db: Session = Depends(get_db),
) -> RuleInferResponse:
    """
    Otomatik kural çıkarımı.

    RuleInferenceEngine servisi ile:
    - RANGE: Sayısal aralık kuralları
    - ENUM: Sabit değer kümeleri
    - REGEX: Format kuralları (TCKN, IBAN vb.)
    - DISTRIBUTION: İstatistiksel dağılım kuralları
    - DEPENDENCY: Kolonlar arası bağımlılıklar
    """
    dataset = _get_dataset_or_404(dataset_id, db)

    profiles = (
        db.query(ColumnProfile)
        .filter(ColumnProfile.dataset_id == dataset_id)
        .all()
    )

    if not profiles:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Önce şema analizi yapılmalıdır. POST /api/v1/analyze/{dataset_id}",
        )

    try:
        from app.services.rule_engine import RuleInferenceEngine
        from app.services.schema_analyzer import ColumnAnalysis

        engine = RuleInferenceEngine()
        columns = []

        for profile in profiles:
            col_analysis = ColumnAnalysis(
                name=profile.name,
                data_type=profile.data_type,
                semantic_type=profile.semantic_type,
                null_ratio=profile.null_ratio or 0.0,
                distinct_ratio=profile.distinct_ratio or 0.0,
                sample_values=profile.sample_values.get("values", []) if profile.sample_values else [],
                statistics=profile.statistics or {},
                pattern=profile.pattern,
            )
            columns.append(col_analysis)

        inferred = engine.infer_rules(columns)

        # Mevcut kuralları temizle ve yenilerini kaydet
        db.query(InferredRule).filter(
            InferredRule.dataset_id == dataset_id
        ).delete()

        for rule_result in inferred:
            rule = InferredRule(
                dataset_id=dataset_id,
                column_name=rule_result.column_name,
                rule_type=rule_result.rule_type,
                rule_definition=rule_result.rule_definition,
                confidence_score=rule_result.confidence_score,
                is_active=True,
            )
            db.add(rule)

        db.commit()

        # Rapor oluştur
        report = engine.generate_report(inferred) if hasattr(engine, "generate_report") else None
        type_dist: dict[str, int] = {}
        avg_confidence = 0.0
        rules_list = []

        for r in inferred:
            t = r.rule_type.value if hasattr(r.rule_type, "value") else str(r.rule_type)
            type_dist[t] = type_dist.get(t, 0) + 1
            rules_list.append(r.to_dict() if hasattr(r, "to_dict") else {
                "column_name": r.column_name,
                "rule_type": t,
                "rule_definition": r.rule_definition,
                "confidence_score": r.confidence_score,
            })

        if inferred:
            avg_confidence = sum(r.confidence_score for r in inferred) / len(inferred)

        return RuleInferResponse(
            dataset_id=dataset_id,
            rule_count=len(inferred),
            rules=rules_list,
            average_confidence=round(avg_confidence, 3),
            type_distribution=type_dist,
            message=f"{len(inferred)} kural başarıyla çıkarıldı",
        )

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Kural çıkarımı sırasında hata oluştu: {str(exc)}",
        )


@router.post(
    "/infer-relationships",
    response_model=RelationshipInferResponse,
    summary="İlişki Çıkarımı",
    description="Birden fazla veri seti arasındaki ilişkileri otomatik tespit eder. "
    "Yabancı anahtar, mantıksal ve AI tabanlı ilişkiler bulunur.",
    responses={
        400: {"model": ErrorResponse, "description": "Yetersiz veri seti"},
        404: {"model": ErrorResponse, "description": "Veri seti bulunamadı"},
    },
)
async def infer_relationships(
    request: RelationshipInferRequest,
    db: Session = Depends(get_db),
) -> RelationshipInferResponse:
    """
    Çoklu dataset ilişki çıkarımı.

    RelationshipInference servisi ile:
    - Kolon adı eşleştirme (tam, FK pattern, fuzzy)
    - Semantik tip uyumu
    - Değer kümesi örtüşme (Jaccard)
    - Bankacılık domain ilişkileri
    """
    # Tüm dataset'lerin varlığını kontrol et
    datasets = []
    for ds_id in request.dataset_ids:
        ds = _get_dataset_or_404(ds_id, db)
        datasets.append(ds)

    try:
        from app.services.relationship_inference import ColumnInfo, RelationshipInference

        inference = RelationshipInference()

        # Her dataset için kolon bilgilerini ekle
        for ds in datasets:
            profiles = (
                db.query(ColumnProfile)
                .filter(ColumnProfile.dataset_id == ds.id)
                .all()
            )
            if not profiles:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Veri seti '{ds.name}' (ID={ds.id}) henüz analiz edilmemiş.",
                )

            col_infos = []
            for p in profiles:
                col_info = ColumnInfo(
                    name=p.name,
                    semantic_type=p.semantic_type,
                    data_type=p.data_type,
                    distinct_ratio=p.distinct_ratio or 0.0,
                    sample_values=p.sample_values.get("values", []) if p.sample_values else [],
                    statistics=p.statistics or {},
                )
                col_infos.append(col_info)

            inference.add_dataset_columns(ds.name, col_infos)

        # İlişkileri çıkar
        candidates = inference.infer_relationships()

        # Mevcut ilişkileri temizle ve yenilerini kaydet
        for ds in datasets:
            db.query(TableRelationship).filter(
                (TableRelationship.source_dataset_id == ds.id)
                | (TableRelationship.target_dataset_id == ds.id)
            ).delete(synchronize_session="fetch")

        # Dataset adı → ID eşleştirmesi
        name_to_id = {ds.name: ds.id for ds in datasets}

        relationships_list = []
        for cand in candidates:
            rel_dict = cand.to_dict() if hasattr(cand, "to_dict") else {
                "source_table": cand.source_table,
                "source_column": cand.source_column,
                "target_table": cand.target_table,
                "target_column": cand.target_column,
                "confidence_score": cand.confidence_score,
            }
            relationships_list.append(rel_dict)

            # Veritabanına kaydet
            source_id = name_to_id.get(cand.source_table)
            target_id = name_to_id.get(cand.target_table)
            if source_id and target_id:
                from app.models.dataset import RelationshipType as RT

                rel = TableRelationship(
                    source_dataset_id=source_id,
                    source_column=cand.source_column,
                    target_dataset_id=target_id,
                    target_column=cand.target_column,
                    relationship_type=RT.INFERRED,
                    cardinality=cand.cardinality if hasattr(cand, "cardinality") else None,
                    confidence_score=cand.confidence_score,
                )
                db.add(rel)

        db.commit()

        # Üretim sırası
        generation_order = None
        try:
            gen_order = inference.get_generation_order()
            generation_order = gen_order
        except Exception:
            pass

        return RelationshipInferResponse(
            dataset_ids=request.dataset_ids,
            relationship_count=len(candidates),
            relationships=relationships_list,
            generation_order=generation_order,
            message=f"{len(candidates)} ilişki tespit edildi",
        )

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"İlişki çıkarımı sırasında hata oluştu: {str(exc)}",
        )


# ═══════════════════════════════════════════════════════════════════════
# 4. SENTETİK VERİ ÜRETİMİ
# ═══════════════════════════════════════════════════════════════════════


@router.post(
    "/generate/{dataset_id}",
    response_model=GenerationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Sentetik Veri Üret",
    description="Belirtilen veri seti şemasına dayalı sentetik bankacılık verisi üretir. "
    "Çıkarılan kurallar ve ilişkiler korunarak gerçekçi veri oluşturulur.",
    responses={
        404: {"model": ErrorResponse, "description": "Veri seti bulunamadı"},
    },
)
async def generate_data(
    dataset_id: int,
    request: GenerateDetailRequest,
    db: Session = Depends(get_db),
) -> GenerationResponse:
    """
    Standart sentetik veri üretimi.

    SyntheticDataGenerator servisi ile:
    - Kolon profillerine dayalı üretim
    - Kural uyumu (aralık, enum, regex, dağılım)
    - İlişkisel bütünlük (FK referanslar)
    - Dağılım koruma (histogram bazlı)
    """
    dataset = _get_dataset_or_404(dataset_id, db)

    if dataset.status not in (DatasetStatus.ANALYZED, DatasetStatus.COMPLETED):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Veri seti henüz analiz edilmemiş. Önce analiz başlatın.",
        )

    # Üretim görevi oluştur
    job = GenerationJob(
        dataset_id=dataset_id,
        row_count=request.row_count,
        parameters={
            "output_format": request.output_format,
            "preserve_distribution": request.preserve_distribution,
            "seed": request.seed,
            "rules_override": request.rules_override,
        },
        status=GenerationStatus.PENDING,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    try:
        job.status = GenerationStatus.RUNNING
        dataset.status = DatasetStatus.GENERATING
        db.commit()

        from app.services.synthetic_generator import SyntheticDataGenerator

        generator = SyntheticDataGenerator()

        if request.seed is not None:
            generator.set_seed(request.seed)

        # Kolon profillerini ve kuralları hazırla
        profiles = (
            db.query(ColumnProfile)
            .filter(ColumnProfile.dataset_id == dataset_id)
            .all()
        )
        rules = (
            db.query(InferredRule)
            .filter(InferredRule.dataset_id == dataset_id, InferredRule.is_active.is_(True))
            .all()
        )

        # Tablo konfigürasyonunu hazırla
        table_config = {
            "name": dataset.name,
            "columns": [],
        }
        for p in profiles:
            col_config: dict[str, Any] = {
                "name": p.name,
                "data_type": p.data_type,
                "semantic_type": p.semantic_type,
                "null_ratio": p.null_ratio or 0.0,
                "statistics": p.statistics or {},
            }
            table_config["columns"].append(col_config)

        # Kural listesini hazırla
        rule_configs = []
        for r in rules:
            rule_configs.append({
                "column_name": r.column_name,
                "rule_type": r.rule_type.value if hasattr(r.rule_type, "value") else str(r.rule_type),
                "rule_definition": r.rule_definition,
            })

        # Üretim yap
        result = generator.generate(
            table_configs=[table_config],
            rules=rule_configs,
            row_counts={dataset.name: request.row_count},
        )

        # Çıktıyı kaydet
        output_filename = f"synth_{dataset.name}_{job.id}.{request.output_format}"
        output_path = OUTPUT_DIR / output_filename

        if dataset.name in result.tables:
            df = result.tables[dataset.name]
            if request.output_format == "csv":
                df.to_csv(str(output_path), index=False)
            elif request.output_format == "json":
                df.to_json(str(output_path), orient="records", force_ascii=False)
            elif request.output_format == "sql":
                # SQL INSERT ifadeleri oluştur
                generator.export_sql(
                    result, str(output_path), table_names=[dataset.name]
                )

        job.status = GenerationStatus.COMPLETED
        job.output_path = str(output_path)
        job.completed_at = datetime.utcnow()
        dataset.status = DatasetStatus.COMPLETED
        db.commit()
        db.refresh(job)

        return GenerationResponse.model_validate(job)

    except HTTPException:
        raise
    except Exception as exc:
        job.status = GenerationStatus.FAILED
        dataset.status = DatasetStatus.FAILED
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Sentetik veri üretimi sırasında hata oluştu: {str(exc)}",
        )


@router.post(
    "/generate-scenario",
    response_model=GenerationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Senaryo Bazlı Üretim",
    description="Öntanımlı bankacılık senaryolarına göre sentetik veri üretir. "
    "12 farklı senaryo mevcuttur: bireysel, premium, riskli, dormant vb.",
    responses={
        400: {"model": ErrorResponse, "description": "Geçersiz senaryo tipi"},
    },
)
async def generate_scenario(
    request: ScenarioGenerateRequest,
    db: Session = Depends(get_db),
) -> GenerationResponse:
    """
    Senaryo bazlı sentetik veri üretimi.

    ScenarioGenerator servisi ile:
    - 12 öntanımlı bankacılık senaryosu
    - Müşteri → Hesap → İşlem zinciri
    - Senaryo bazlı parametreler (bakiye, kredi notu, segment)
    """
    try:
        from app.services.scenario_generator import ScenarioGenerator, ScenarioType

        generator = ScenarioGenerator()

        # Senaryo tipini bul
        scenario_type = None
        for st in ScenarioType:
            if st.value == request.scenario_type or st.name.lower() == request.scenario_type.lower():
                scenario_type = st
                break

        if not scenario_type:
            # Anahtar kelime ile ara
            matches = generator.find_scenario_by_keyword(request.scenario_type)
            if matches:
                scenario_type = matches[0]
            else:
                available = [st.value for st in ScenarioType]
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"Geçersiz senaryo tipi: '{request.scenario_type}'. "
                        f"Mevcut senaryolar: {', '.join(available)}"
                    ),
                )

        # Önce bir dataset kaydı oluştur (senaryo için)
        dataset = Dataset(
            name=f"scenario_{scenario_type.value}_{int(time.time())}",
            description=f"Senaryo bazlı üretim: {scenario_type.value}",
            status=DatasetStatus.GENERATING,
        )
        db.add(dataset)
        db.commit()
        db.refresh(dataset)

        # Üretim görevi oluştur
        job = GenerationJob(
            dataset_id=dataset.id,
            scenario_name=scenario_type.value,
            row_count=request.count,
            parameters={
                "scenario_type": scenario_type.value,
                "custom_config": request.custom_config,
                "output_format": request.output_format,
            },
            status=GenerationStatus.RUNNING,
        )
        db.add(job)
        db.commit()
        db.refresh(job)

        # Senaryo üretimi
        if request.custom_config:
            from app.services.scenario_generator import ScenarioConfig

            config = ScenarioConfig(**request.custom_config)
            result = generator.generate_custom_scenario(config, request.count)
        else:
            result = generator.generate_scenario(scenario_type, request.count)

        # Çıktıyı kaydet
        output_subdir = f"scenario_{scenario_type.value}_{job.id}"
        output_dir = OUTPUT_DIR / output_subdir

        if request.output_format == "csv":
            paths = generator.export_csv(result, str(output_dir))
        else:
            paths = generator.export_json(result, str(output_dir))

        # Birden fazla dosya üretiliyor; müşteri tablosunu ana dosya olarak kullan
        primary_key = "customers" if "customers" in paths else (next(iter(paths)) if paths else None)
        if not primary_key:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Üretim tamamlandı ancak çıktı dosyası oluşturulamadı.",
            )
        output_path = Path(paths[primary_key])

        job.status = GenerationStatus.COMPLETED
        job.output_path = str(output_path)
        job.completed_at = datetime.utcnow()
        dataset.status = DatasetStatus.COMPLETED
        db.commit()
        db.refresh(job)

        return GenerationResponse.model_validate(job)

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Senaryo üretimi sırasında hata oluştu: {str(exc)}",
        )


@router.post(
    "/generate-natural",
    response_model=NaturalLanguageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Doğal Dil ile Üretim",
    description="Doğal dil talebi ile sentetik veri üretir. "
    "Türkçe veya İngilizce metin girilerek LLM destekli üretim yapılır.",
    responses={
        400: {"model": ErrorResponse, "description": "Geçersiz talep metni"},
    },
)
async def generate_natural(
    request: NaturalLanguageRequest,
    db: Session = Depends(get_db),
) -> NaturalLanguageResponse:
    """
    Doğal dil ile sentetik veri üretimi.

    LLMService ile metin analiz edilir, ScenarioGenerator ile üretim yapılır:
    - "1000 premium müşteri üret" → ScenarioType.PREMIUM, count=1000
    - "Bakiyesi 100K üzeri olan müşteriler" → bakiye aralığı uygulanır
    """
    try:
        from app.services.llm_service import LLMService
        from app.services.scenario_generator import ScenarioGenerator, ScenarioType

        llm = LLMService()
        parsed = llm.parse_natural_language_request(request.text)

        # Senaryo ve sayı çıkar — parser "musteri_sayisi" döndürür
        scenario_name = parsed.get("senaryo", parsed.get("scenario_type", "bireysel"))
        count = parsed.get("musteri_sayisi", parsed.get("count", 1000))

        generator = ScenarioGenerator()

        # Senaryo tipini bul
        scenario_type = None
        for st in ScenarioType:
            if st.value == scenario_name or st.name.lower() == scenario_name.lower():
                scenario_type = st
                break

        if not scenario_type:
            matches = generator.find_scenario_by_keyword(scenario_name)
            scenario_type = matches[0] if matches else ScenarioType.BIREYSEL

        # Dataset ve Job oluştur
        dataset = Dataset(
            name=f"natural_{scenario_type.value}_{int(time.time())}",
            description=f"Doğal dil üretimi: {request.text[:100]}",
            status=DatasetStatus.GENERATING,
        )
        db.add(dataset)
        db.commit()
        db.refresh(dataset)

        job = GenerationJob(
            dataset_id=dataset.id,
            scenario_name=scenario_type.value,
            row_count=count,
            parameters={
                "original_text": request.text,
                "parsed_request": parsed,
                "output_format": request.output_format,
            },
            status=GenerationStatus.RUNNING,
        )
        db.add(job)
        db.commit()
        db.refresh(job)

        # Yaş ve hesap sayısı filtresi varsa config'i özelleştir
        from app.services.scenario_generator import SCENARIO_CONFIGS
        import copy
        yas_min = parsed.get("yas_min")
        yas_max = parsed.get("yas_max")
        hesap_sayisi = parsed.get("hesap_sayisi")
        has_overrides = yas_min is not None or yas_max is not None or hesap_sayisi is not None

        if has_overrides:
            base_config = SCENARIO_CONFIGS.get(scenario_type)
            custom_config = copy.copy(base_config) if base_config else None
            if custom_config:
                if yas_min is not None:
                    custom_config.yas_min = yas_min
                if yas_max is not None:
                    custom_config.yas_max = yas_max
                if hesap_sayisi is not None:
                    custom_config.hesap_sayisi_min = hesap_sayisi
                    custom_config.hesap_sayisi_max = hesap_sayisi
                result = generator.generate_custom_scenario(custom_config, count)
            else:
                result = generator.generate_scenario(scenario_type, count)
        else:
            # Üretim
            result = generator.generate_scenario(scenario_type, count)

        # Çıktıyı kaydet
        output_subdir = f"natural_{job.id}"
        output_dir = OUTPUT_DIR / output_subdir

        if request.output_format == "csv":
            paths = generator.export_csv(result, str(output_dir))
        else:
            paths = generator.export_json(result, str(output_dir))

        primary_key = "customers" if "customers" in paths else (next(iter(paths)) if paths else None)
        if not primary_key:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Üretim tamamlandı ancak çıktı dosyası oluşturulamadı.",
            )
        output_path = Path(paths[primary_key])

        job.status = GenerationStatus.COMPLETED
        job.output_path = str(output_path)
        job.completed_at = datetime.utcnow()
        dataset.status = DatasetStatus.COMPLETED
        db.commit()

        return NaturalLanguageResponse(
            parsed_request=parsed,
            job_id=job.id,
            status="completed",
            message=(
                f"Doğal dil talebi işlendi. Senaryo: {scenario_type.value}, "
                f"Adet: {count}. İndirmek için GET /api/v1/export/{job.id}"
            ),
        )

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Doğal dil ile üretim sırasında hata oluştu: {str(exc)}",
        )


# ═══════════════════════════════════════════════════════════════════════
# 5. VERİ SETİ SORGULAMA VE YÖNETİM
# ═══════════════════════════════════════════════════════════════════════


@router.get(
    "/datasets",
    response_model=DatasetListResponse,
    summary="Veri Seti Listesi",
    description="Tüm veri setlerini sayfalandırmalı olarak listeler.",
)
async def list_datasets(
    page: int = Query(1, ge=1, description="Sayfa numarası"),
    page_size: int = Query(20, ge=1, le=100, description="Sayfa başına öğe"),
    status_filter: Optional[str] = Query(
        None, alias="status", description="Durum filtresi (uploaded, analyzed, completed vb.)"
    ),
    db: Session = Depends(get_db),
) -> DatasetListResponse:
    """Tüm veri setlerini listele (sayfalandırmalı, filtrelenebilir)."""
    query = db.query(Dataset)

    if status_filter:
        try:
            ds_status = DatasetStatus(status_filter)
            query = query.filter(Dataset.status == ds_status)
        except ValueError:
            pass  # Geçersiz filtre — tümünü göster

    total = query.count()
    datasets = (
        query
        .order_by(Dataset.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return DatasetListResponse(
        items=[DatasetResponse.model_validate(ds) for ds in datasets],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/datasets/{dataset_id}",
    response_model=DatasetDetailResponse,
    summary="Veri Seti Detayı",
    description="Belirtilen veri setinin detaylı bilgilerini, kolon profillerini ve kurallarını döndürür.",
    responses={
        404: {"model": ErrorResponse, "description": "Veri seti bulunamadı"},
    },
)
async def get_dataset(
    dataset_id: int,
    db: Session = Depends(get_db),
) -> DatasetDetailResponse:
    """Veri seti detayını getir (profiller ve kurallar dahil)."""
    dataset = _get_dataset_or_404(dataset_id, db)

    profiles = (
        db.query(ColumnProfile)
        .filter(ColumnProfile.dataset_id == dataset_id)
        .all()
    )
    rules = (
        db.query(InferredRule)
        .filter(InferredRule.dataset_id == dataset_id)
        .all()
    )

    response = DatasetDetailResponse.model_validate(dataset)
    response.column_profiles = [
        ColumnProfileResponse.model_validate(p) for p in profiles
    ]
    response.inferred_rules = [
        RuleResponse.model_validate(r) for r in rules
    ]
    return response


@router.get(
    "/datasets/{dataset_id}/columns",
    response_model=list[ColumnProfileResponse],
    summary="Kolon Profilleri",
    description="Veri setine ait kolon profillerini ve istatistiklerini döndürür.",
    responses={
        404: {"model": ErrorResponse, "description": "Veri seti bulunamadı"},
    },
)
async def get_columns(
    dataset_id: int,
    db: Session = Depends(get_db),
) -> list[ColumnProfileResponse]:
    """Veri setinin kolon profillerini getir."""
    _get_dataset_or_404(dataset_id, db)

    profiles = (
        db.query(ColumnProfile)
        .filter(ColumnProfile.dataset_id == dataset_id)
        .all()
    )
    return [ColumnProfileResponse.model_validate(p) for p in profiles]


@router.get(
    "/datasets/{dataset_id}/rules",
    response_model=RuleListResponse,
    summary="Çıkarılan Kurallar",
    description="Veri seti için otomatik çıkarılan iş kurallarını listeler.",
    responses={
        404: {"model": ErrorResponse, "description": "Veri seti bulunamadı"},
    },
)
async def get_rules(
    dataset_id: int,
    active_only: bool = Query(True, description="Sadece aktif kuralları getir"),
    db: Session = Depends(get_db),
) -> RuleListResponse:
    """Veri setinin çıkarılan kurallarını getir."""
    _get_dataset_or_404(dataset_id, db)

    query = db.query(InferredRule).filter(
        InferredRule.dataset_id == dataset_id
    )
    if active_only:
        query = query.filter(InferredRule.is_active.is_(True))

    rules = query.all()
    return RuleListResponse(
        items=[RuleResponse.model_validate(r) for r in rules],
        total=len(rules),
    )


@router.get(
    "/datasets/{dataset_id}/relationships",
    response_model=list[RelationshipResponse],
    summary="Tablo İlişkileri",
    description="Veri seti ile ilişkili tablolar arası bağlantıları listeler.",
    responses={
        404: {"model": ErrorResponse, "description": "Veri seti bulunamadı"},
    },
)
async def get_relationships(
    dataset_id: int,
    db: Session = Depends(get_db),
) -> list[RelationshipResponse]:
    """Veri setinin ilişkilerini getir (kaynak veya hedef olarak)."""
    _get_dataset_or_404(dataset_id, db)

    rels = (
        db.query(TableRelationship)
        .filter(
            (TableRelationship.source_dataset_id == dataset_id)
            | (TableRelationship.target_dataset_id == dataset_id)
        )
        .all()
    )
    return [RelationshipResponse.model_validate(r) for r in rels]


@router.delete(
    "/datasets/{dataset_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Veri Seti Sil",
    description="Belirtilen veri setini ve ilişkili tüm verileri (profiller, kurallar, görevler) siler.",
    responses={
        404: {"model": ErrorResponse, "description": "Veri seti bulunamadı"},
    },
)
async def delete_dataset(
    dataset_id: int,
    db: Session = Depends(get_db),
) -> None:
    """Veri setini ve bağlı kayıtları sil (cascade)."""
    dataset = _get_dataset_or_404(dataset_id, db)

    # Dosyayı temizle
    if dataset.file_path and os.path.exists(dataset.file_path):
        try:
            os.remove(dataset.file_path)
        except OSError:
            pass  # Dosya silinememesi kritik değil

    db.delete(dataset)
    db.commit()


# ═══════════════════════════════════════════════════════════════════════
# 6. DIŞA AKTARIM VE İŞ TAKİBİ
# ═══════════════════════════════════════════════════════════════════════


@router.get(
    "/export/{job_id}",
    response_model=ExportResponse,
    summary="Üretilen Veriyi İndir",
    description="Tamamlanmış bir üretim görevinin çıktı dosyasını indirir. "
    "CSV, JSON veya SQL formatında.",
    responses={
        404: {"model": ErrorResponse, "description": "Görev bulunamadı"},
        409: {"model": ErrorResponse, "description": "Görev henüz tamamlanmadı"},
    },
)
async def export_data(
    job_id: int,
    format: Optional[str] = Query(
        None, description="İstenen format (csv, json, sql). Boş ise orijinal format."
    ),
    db: Session = Depends(get_db),
) -> ExportResponse:
    """Üretilen sentetik veriyi dışa aktar."""
    job = _get_job_or_404(job_id, db)

    if job.status != GenerationStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Üretim görevi henüz tamamlanmadı. Durum: {job.status.value}",
        )

    if not job.output_path or not os.path.exists(job.output_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Üretim çıktı dosyası bulunamadı. Dosya silinmiş olabilir.",
        )

    output_path = Path(job.output_path)
    file_size = output_path.stat().st_size

    # Satır sayısını hesapla
    row_count = job.row_count

    # Format dönüşümü gerekiyorsa
    if format and format != output_path.suffix.lstrip("."):
        try:
            df = pd.read_csv(str(output_path)) if output_path.suffix == ".csv" else pd.read_json(str(output_path))
            new_path = output_path.with_suffix(f".{format}")
            if format == "csv":
                df.to_csv(str(new_path), index=False)
            elif format == "json":
                df.to_json(str(new_path), orient="records", force_ascii=False)
            output_path = new_path
            file_size = output_path.stat().st_size
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Format dönüşümü başarısız: {str(exc)}",
            )

    return ExportResponse(
        job_id=job_id,
        format=output_path.suffix.lstrip("."),
        file_name=output_path.name,
        file_size=file_size,
        row_count=row_count,
        download_url=f"/api/v1/download/{output_path.relative_to(OUTPUT_DIR)}",
        message="Dosya indirmeye hazır",
    )


@router.get(
    "/jobs",
    response_model=JobListResponse,
    summary="Üretim Görevleri",
    description="Tüm sentetik veri üretim görevlerini sayfalandırmalı listeler.",
)
async def list_jobs(
    page: int = Query(1, ge=1, description="Sayfa numarası"),
    page_size: int = Query(20, ge=1, le=100, description="Sayfa başına öğe"),
    status_filter: Optional[str] = Query(
        None, alias="status", description="Durum filtresi (pending, running, completed vb.)"
    ),
    db: Session = Depends(get_db),
) -> JobListResponse:
    """Tüm üretim görevlerini listele."""
    query = db.query(GenerationJob)

    if status_filter:
        try:
            gen_status = GenerationStatus(status_filter)
            query = query.filter(GenerationJob.status == gen_status)
        except ValueError:
            pass

    total = query.count()
    jobs = (
        query
        .order_by(GenerationJob.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return JobListResponse(
        items=[JobResponse.model_validate(j) for j in jobs],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/jobs/{job_id}",
    response_model=JobResponse,
    summary="Görev Detayı",
    description="Belirtilen üretim görevinin detaylı bilgilerini döndürür.",
    responses={
        404: {"model": ErrorResponse, "description": "Görev bulunamadı"},
    },
)
async def get_job(
    job_id: int,
    db: Session = Depends(get_db),
) -> JobResponse:
    """Üretim görevi detayını getir."""
    job = _get_job_or_404(job_id, db)
    return JobResponse.model_validate(job)


# ═══════════════════════════════════════════════════════════════════════
# 7. SENARYO LİSTESİ
# ═══════════════════════════════════════════════════════════════════════


@router.get(
    "/scenarios",
    response_model=ScenarioListResponse,
    summary="Senaryo Listesi",
    description="Mevcut bankacılık senaryolarını ve varsayılan konfigürasyonlarını listeler.",
)
async def list_scenarios() -> ScenarioListResponse:
    """Kullanılabilir senaryoları listele."""
    try:
        from app.services.scenario_generator import ScenarioGenerator

        generator = ScenarioGenerator()
        scenarios_raw = generator.list_scenarios()

        scenarios = []
        for s in scenarios_raw:
            scenarios.append(
                ScenarioInfo(
                    name=s.get("name", ""),
                    description=s.get("description", ""),
                    default_config=s.get("config", {}),
                )
            )

        return ScenarioListResponse(
            scenarios=scenarios,
            total=len(scenarios),
        )
    except Exception:
        # Fallback: enum'dan basit liste
        from app.services.scenario_generator import ScenarioType

        scenarios = [
            ScenarioInfo(
                name=st.value,
                description=f"{st.value} bankacılık senaryosu",
                default_config={},
            )
            for st in ScenarioType
        ]
        return ScenarioListResponse(scenarios=scenarios, total=len(scenarios))


# ═══════════════════════════════════════════════════════════════════════
# 8. SAĞLIK KONTROLÜ VE İSTATİSTİKLER
# ═══════════════════════════════════════════════════════════════════════


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Sağlık Kontrolü",
    description="Platform sağlık durumunu kontrol eder. "
    "Veritabanı bağlantısı, LLM durumu ve uptime bilgisi döndürür.",
)
async def health_check(
    db: Session = Depends(get_db),
) -> HealthResponse:
    """Sistem sağlık kontrolü."""
    # Veritabanı kontrolü
    db_status = "disconnected"
    try:
        db.execute(sa_func.now())
        db_status = "connected"
    except Exception:
        db_status = "error"

    # LLM durumu
    llm_status = "not_configured"
    try:
        from app.services.llm_service import LLMService

        llm = LLMService()
        llm_status = llm.provider.value if hasattr(llm, "provider") else settings.LLM_PROVIDER
    except Exception:
        llm_status = "fallback"

    uptime = time.time() - _start_time

    return HealthResponse(
        status="healthy" if db_status == "connected" else "degraded",
        version=settings.VERSION,
        database=db_status,
        llm_provider=llm_status,
        uptime_seconds=round(uptime, 2),
    )


@router.get(
    "/stats",
    response_model=StatsResponse,
    summary="Platform İstatistikleri",
    description="Toplam veri seti, üretim görevi ve satır sayılarını döndürür.",
)
async def get_stats(
    db: Session = Depends(get_db),
) -> StatsResponse:
    """Platform genel istatistiklerini getir."""
    total_datasets = db.query(sa_func.count(Dataset.id)).scalar() or 0
    total_jobs = db.query(sa_func.count(GenerationJob.id)).scalar() or 0

    completed_jobs = (
        db.query(sa_func.count(GenerationJob.id))
        .filter(GenerationJob.status == GenerationStatus.COMPLETED)
        .scalar() or 0
    )
    failed_jobs = (
        db.query(sa_func.count(GenerationJob.id))
        .filter(GenerationJob.status == GenerationStatus.FAILED)
        .scalar() or 0
    )
    active_jobs = (
        db.query(sa_func.count(GenerationJob.id))
        .filter(GenerationJob.status.in_([GenerationStatus.PENDING, GenerationStatus.RUNNING]))
        .scalar() or 0
    )

    total_rows = (
        db.query(sa_func.sum(GenerationJob.row_count))
        .filter(GenerationJob.status == GenerationStatus.COMPLETED)
        .scalar() or 0
    )

    # Duruma göre dataset dağılımı
    status_counts = (
        db.query(Dataset.status, sa_func.count(Dataset.id))
        .group_by(Dataset.status)
        .all()
    )
    datasets_by_status = {
        s.value if hasattr(s, "value") else str(s): c
        for s, c in status_counts
    }

    # Ortalama üretim süresi
    avg_time = None
    try:
        completed = (
            db.query(GenerationJob)
            .filter(
                GenerationJob.status == GenerationStatus.COMPLETED,
                GenerationJob.completed_at.isnot(None),
            )
            .all()
        )
        if completed:
            durations = [
                (j.completed_at - j.created_at).total_seconds()
                for j in completed
                if j.completed_at and j.created_at
            ]
            if durations:
                avg_time = round(sum(durations) / len(durations), 2)
    except Exception:
        pass

    return StatsResponse(
        total_datasets=total_datasets,
        total_jobs=total_jobs,
        total_rows_generated=total_rows,
        completed_jobs=completed_jobs,
        failed_jobs=failed_jobs,
        active_jobs=active_jobs,
        datasets_by_status=datasets_by_status,
        average_generation_time=avg_time,
        platform_version=settings.VERSION,
    )
