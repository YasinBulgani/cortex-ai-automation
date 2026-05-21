"""
Test Kayıt ve Oynatma Modülü

Bu modül, test oturumlarını kaydeder, oturumları oynatır ve test adımlarını JSON formatında depolar.
Test adımlarının sekvensiyel kaydını sağlar ve oturumları yeniden üretebilir.
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict, field
from enum import Enum

import logging

logger = logging.getLogger(__name__)


class ActionType(str, Enum):
    """Test adım türleri."""
    CLICK = "click"
    TYPE = "type"
    NAVIGATE = "navigate"
    WAIT = "wait"
    SCREENSHOT = "screenshot"
    ASSERT = "assert"
    HOVER = "hover"
    SCROLL = "scroll"
    SELECT = "select"
    SUBMIT = "submit"


class AssertionType(str, Enum):
    """Onaylama türleri."""
    ELEMENT_VISIBLE = "element_visible"
    ELEMENT_HIDDEN = "element_hidden"
    TEXT_CONTAINS = "text_contains"
    VALUE_EQUALS = "value_equals"
    URL_EQUALS = "url_equals"
    ELEMENT_COUNT = "element_count"


@dataclass
class TestStep:
    """Test adımı veri sınıfı."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    action: ActionType = ActionType.CLICK
    selector: str = ""
    value: str = ""
    duration_ms: int = 0
    screenshot_path: Optional[str] = None
    assertion_type: Optional[AssertionType] = None
    assertion_expected: Optional[str] = None
    assertion_passed: bool = True
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TestSession:
    """Test oturumu veri sınıfı."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    started_at: Optional[str] = None
    ended_at: Optional[str] = None
    status: str = "created"  # created, recording, completed, failed
    steps: List[TestStep] = field(default_factory=list)
    total_duration_ms: int = 0
    success_rate: float = 100.0
    tags: List[str] = field(default_factory=list)


class TestRecorder:
    """
    Test oturumlarını kaydeden ve oynatılan sınıf.

    Adımlar JSON formatında sekvensiyel olarak depolanır ve
    oturumlar yeniden üretebilir.
    """

    def __init__(self, recordings_dir: str):
        """
        TestRecorder'ı başlatır.

        Args:
            recordings_dir: Kayıtların depolandığı dizin
        """
        self.recordings_dir = Path(recordings_dir)
        self.recordings_dir.mkdir(parents=True, exist_ok=True)

        self.current_session: Optional[TestSession] = None
        self.step_index = 0

        logger.info(f"TestRecorder başlatıldı - Dizin: {recordings_dir}")

    def start_recording(
        self,
        name: str,
        description: str = "",
        tags: List[str] = None
    ) -> str:
        """
        Yeni bir test oturumunun kaydını başlatır.

        Args:
            name: Test adı
            description: Test açıklaması
            tags: Test etiketleri

        Returns:
            Oturum ID'si
        """
        try:
            self.current_session = TestSession(
                name=name,
                description=description,
                started_at=datetime.now().isoformat(),
                status="recording",
                tags=tags or []
            )

            logger.info(f"Test kaydı başlatıldı - Adı: {name}, ID: {self.current_session.id}")
            return self.current_session.id

        except Exception as e:
            logger.error(f"Test kaydı başlatma hatası: {e}")
            raise

    def add_step(
        self,
        action: ActionType,
        selector: str = "",
        value: str = "",
        duration_ms: int = 0,
        screenshot_path: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Mevcut kaydedilen oturuma test adımı ekler.

        Args:
            action: Adım türü
            selector: CSS/XPath seçici
            value: Adımla ilişkili değer
            duration_ms: Adım süresi (ms)
            screenshot_path: Ekran görüntüsü dosya yolu
            metadata: Ek meta veriler

        Returns:
            Adım ID'si
        """
        try:
            if not self.current_session:
                raise RuntimeError("Aktif bir test oturumu yok")

            step = TestStep(
                action=action,
                selector=selector,
                value=value,
                duration_ms=duration_ms,
                screenshot_path=screenshot_path,
                metadata=metadata or {}
            )

            self.current_session.steps.append(step)
            self.current_session.total_duration_ms += duration_ms

            logger.debug(f"Adım eklendi - Türü: {action.value}, ID: {step.id}")
            return step.id

        except Exception as e:
            logger.error(f"Adım ekleme hatası: {e}")
            raise

    def add_assertion(
        self,
        assertion_type: AssertionType,
        expected_value: str,
        selector: str = ""
    ) -> str:
        """
        Mevcut adıma onaylama ekler.

        Args:
            assertion_type: Onaylama türü
            expected_value: Beklenen değer
            selector: Kontrol edilecek eleman seçici

        Returns:
            Adım ID'si
        """
        try:
            if not self.current_session or not self.current_session.steps:
                raise RuntimeError("Onaylama eklenecek adım yok")

            last_step = self.current_session.steps[-1]
            last_step.assertion_type = assertion_type
            last_step.assertion_expected = expected_value
            last_step.selector = selector or last_step.selector

            logger.debug(
                f"Onaylama eklendi - Türü: {assertion_type.value}, "
                f"Beklenen: {expected_value}"
            )
            return last_step.id

        except Exception as e:
            logger.error(f"Onaylama ekleme hatası: {e}")
            raise

    def stop_recording(self) -> TestSession:
        """
        Aktif test oturumunun kaydını durdurur.

        Returns:
            Tamamlanan test oturumu

        Raises:
            RuntimeError: Aktif oturum yoksa
        """
        try:
            if not self.current_session:
                raise RuntimeError("Aktif bir test oturumu yok")

            self.current_session.ended_at = datetime.now().isoformat()
            self.current_session.status = "completed"

            # Başarı oranını hesapla
            total_assertions = sum(
                1 for step in self.current_session.steps
                if step.assertion_type is not None
            )
            passed_assertions = sum(
                1 for step in self.current_session.steps
                if step.assertion_type and step.assertion_passed
            )

            if total_assertions > 0:
                self.current_session.success_rate = (passed_assertions / total_assertions) * 100
            else:
                self.current_session.success_rate = 100.0

            logger.info(
                f"Test kaydı durduruldu - Oturum: {self.current_session.name}, "
                f"Adım Sayısı: {len(self.current_session.steps)}, "
                f"Başarı Oranı: {self.current_session.success_rate:.2f}%"
            )

            return self.current_session

        except Exception as e:
            logger.error(f"Test kaydı durdurma hatası: {e}")
            raise

    def replay_session(
        self,
        session_id: str,
        callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        Kaydedilmiş bir test oturumunu oynatır.

        Args:
            session_id: Oynatılacak oturum ID'si
            callback: Her adım için çağrılacak geri arama fonksiyonu

        Returns:
            Oynatma sonuçları

        Raises:
            FileNotFoundError: Oturum dosyası bulunamazsa
        """
        try:
            session = self._load_session(session_id)

            results = {
                "session_id": session.id,
                "session_name": session.name,
                "total_steps": len(session.steps),
                "executed_steps": 0,
                "failed_steps": 0,
                "errors": [],
                "start_time": datetime.now().isoformat()
            }

            for step_index, step in enumerate(session.steps):
                try:
                    if callback:
                        callback(step)

                    results["executed_steps"] += 1

                    # Onaylama kontrol et
                    if step.assertion_type:
                        if not step.assertion_passed:
                            results["failed_steps"] += 1
                            results["errors"].append({
                                "step_id": step.id,
                                "step_index": step_index,
                                "error": f"Onaylama başarısız: {step.assertion_type.value}"
                            })

                except Exception as e:
                    results["failed_steps"] += 1
                    results["errors"].append({
                        "step_id": step.id,
                        "step_index": step_index,
                        "error": str(e)
                    })

            results["end_time"] = datetime.now().isoformat()
            results["success_rate"] = (
                ((results["total_steps"] - results["failed_steps"]) / results["total_steps"] * 100)
                if results["total_steps"] > 0 else 0
            )

            logger.info(
                f"Oturum oynatıldı - ID: {session_id}, "
                f"Başarı: {results['success_rate']:.2f}%"
            )
            return results

        except Exception as e:
            logger.error(f"Oturum oynatma hatası: {e}")
            raise

    def export_recording(
        self,
        session_id: str,
        export_format: str = "json",
        output_path: Optional[str] = None
    ) -> str:
        """
        Kaydedilmiş oturumu dışa aktarır.

        Args:
            session_id: Dışa aktarılacak oturum ID'si
            export_format: Dışa aktarma formatı (json, yaml)
            output_path: Çıkış dosya yolu (opsiyonel)

        Returns:
            Dışa aktarılan dosyanın yolu

        Raises:
            FileNotFoundError: Oturum bulunamazsa
            ValueError: Geçersiz format belirtilmişse
        """
        try:
            session = self._load_session(session_id)

            if output_path is None:
                output_path = str(
                    self.recordings_dir / f"{session.name}_{session.id}.{export_format}"
                )

            # Oturumu sözlüğe dönüştür
            session_dict = {
                "id": session.id,
                "name": session.name,
                "description": session.description,
                "created_at": session.created_at,
                "started_at": session.started_at,
                "ended_at": session.ended_at,
                "status": session.status,
                "total_duration_ms": session.total_duration_ms,
                "success_rate": session.success_rate,
                "tags": session.tags,
                "steps": [
                    {
                        "id": step.id,
                        "timestamp": step.timestamp,
                        "action": step.action.value,
                        "selector": step.selector,
                        "value": step.value,
                        "duration_ms": step.duration_ms,
                        "screenshot_path": step.screenshot_path,
                        "assertion_type": step.assertion_type.value if step.assertion_type else None,
                        "assertion_expected": step.assertion_expected,
                        "assertion_passed": step.assertion_passed,
                        "error_message": step.error_message,
                        "metadata": step.metadata
                    }
                    for step in session.steps
                ]
            }

            if export_format == "json":
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(session_dict, f, ensure_ascii=False, indent=2)
            else:
                raise ValueError(f"Desteklenmeyen format: {export_format}")

            logger.info(f"Oturum dışa aktarıldı - Dosya: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Dışa aktarma hatası: {e}")
            raise

    def import_recording(self, file_path: str) -> str:
        """
        Dışa aktarılan bir kaydı içe aktarır.

        Args:
            file_path: İçe aktarılacak dosyanın yolu

        Returns:
            İçe aktarılan oturum ID'si

        Raises:
            FileNotFoundError: Dosya bulunamazsa
            ValueError: Geçersiz dosya formatı
        """
        try:
            file_path = Path(file_path)

            if not file_path.exists():
                raise FileNotFoundError(f"Dosya bulunamadı: {file_path}")

            # Dosyayı oku
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Oturumu yeniden oluştur
            session = TestSession(
                id=data.get("id", str(uuid.uuid4())),
                name=data.get("name", ""),
                description=data.get("description", ""),
                created_at=data.get("created_at", datetime.now().isoformat()),
                started_at=data.get("started_at"),
                ended_at=data.get("ended_at"),
                status=data.get("status", "imported"),
                total_duration_ms=data.get("total_duration_ms", 0),
                success_rate=data.get("success_rate", 100.0),
                tags=data.get("tags", [])
            )

            # Adımları yeniden oluştur
            for step_data in data.get("steps", []):
                step = TestStep(
                    id=step_data.get("id", str(uuid.uuid4())),
                    timestamp=step_data.get("timestamp", datetime.now().isoformat()),
                    action=ActionType[step_data.get("action", "CLICK").upper()],
                    selector=step_data.get("selector", ""),
                    value=step_data.get("value", ""),
                    duration_ms=step_data.get("duration_ms", 0),
                    screenshot_path=step_data.get("screenshot_path"),
                    assertion_type=(
                        AssertionType[step_data.get("assertion_type").upper()]
                        if step_data.get("assertion_type") else None
                    ),
                    assertion_expected=step_data.get("assertion_expected"),
                    assertion_passed=step_data.get("assertion_passed", True),
                    error_message=step_data.get("error_message"),
                    metadata=step_data.get("metadata", {})
                )
                session.steps.append(step)

            # Oturumu kaydet
            session_file = self.recordings_dir / f"{session.id}.json"
            with open(session_file, 'w', encoding='utf-8') as f:
                json.dump(self._session_to_dict(session), f, ensure_ascii=False, indent=2)

            logger.info(f"Oturum içe aktarıldı - ID: {session.id}, Adımlar: {len(session.steps)}")
            return session.id

        except Exception as e:
            logger.error(f"İçe aktarma hatası: {e}")
            raise

    def list_recordings(self) -> List[Dict[str, Any]]:
        """
        Tüm kaydedilmiş oturumları listeler.

        Returns:
            Oturum bilgileri listesi
        """
        try:
            recordings = []

            for session_file in self.recordings_dir.glob("*.json"):
                try:
                    session = self._load_session(session_file.stem)
                    recordings.append({
                        "id": session.id,
                        "name": session.name,
                        "created_at": session.created_at,
                        "started_at": session.started_at,
                        "ended_at": session.ended_at,
                        "status": session.status,
                        "total_steps": len(session.steps),
                        "total_duration_ms": session.total_duration_ms,
                        "success_rate": session.success_rate,
                        "tags": session.tags
                    })
                except Exception as e:
                    logger.warning(f"Oturum yüklenirken hata: {session_file} - {e}")

            logger.info(f"Oturumlar listelendi - Toplam: {len(recordings)}")
            return recordings

        except Exception as e:
            logger.error(f"Oturumları listeleme hatası: {e}")
            raise

    def delete_recording(self, session_id: str) -> bool:
        """
        Kaydedilmiş oturumu siler.

        Args:
            session_id: Silinecek oturum ID'si

        Returns:
            Silme başarılı mı
        """
        try:
            session_file = self.recordings_dir / f"{session_id}.json"

            if not session_file.exists():
                raise FileNotFoundError(f"Oturum bulunamadı: {session_id}")

            session_file.unlink()

            logger.info(f"Oturum silindi - ID: {session_id}")
            return True

        except Exception as e:
            logger.error(f"Oturum silme hatası: {e}")
            raise

    # Yardımcı metodlar
    def _load_session(self, session_id: str) -> TestSession:
        """Oturumu dosyadan yükler."""
        session_file = self.recordings_dir / f"{session_id}.json"

        if not session_file.exists():
            raise FileNotFoundError(f"Oturum bulunamadı: {session_id}")

        with open(session_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        return self._dict_to_session(data)

    def _session_to_dict(self, session: TestSession) -> Dict:
        """Oturumu sözlüğe dönüştürür."""
        return {
            "id": session.id,
            "name": session.name,
            "description": session.description,
            "created_at": session.created_at,
            "started_at": session.started_at,
            "ended_at": session.ended_at,
            "status": session.status,
            "total_duration_ms": session.total_duration_ms,
            "success_rate": session.success_rate,
            "tags": session.tags,
            "steps": [
                {
                    "id": step.id,
                    "timestamp": step.timestamp,
                    "action": step.action.value,
                    "selector": step.selector,
                    "value": step.value,
                    "duration_ms": step.duration_ms,
                    "screenshot_path": step.screenshot_path,
                    "assertion_type": step.assertion_type.value if step.assertion_type else None,
                    "assertion_expected": step.assertion_expected,
                    "assertion_passed": step.assertion_passed,
                    "error_message": step.error_message,
                    "metadata": step.metadata
                }
                for step in session.steps
            ]
        }

    def _dict_to_session(self, data: Dict) -> TestSession:
        """Sözlükten oturum oluşturur."""
        session = TestSession(
            id=data.get("id", str(uuid.uuid4())),
            name=data.get("name", ""),
            description=data.get("description", ""),
            created_at=data.get("created_at", datetime.now().isoformat()),
            started_at=data.get("started_at"),
            ended_at=data.get("ended_at"),
            status=data.get("status", "imported"),
            total_duration_ms=data.get("total_duration_ms", 0),
            success_rate=data.get("success_rate", 100.0),
            tags=data.get("tags", [])
        )

        for step_data in data.get("steps", []):
            step = TestStep(
                id=step_data.get("id", str(uuid.uuid4())),
                timestamp=step_data.get("timestamp", datetime.now().isoformat()),
                action=ActionType[step_data.get("action", "CLICK").upper()],
                selector=step_data.get("selector", ""),
                value=step_data.get("value", ""),
                duration_ms=step_data.get("duration_ms", 0),
                screenshot_path=step_data.get("screenshot_path"),
                assertion_type=(
                    AssertionType[step_data.get("assertion_type").upper()]
                    if step_data.get("assertion_type") else None
                ),
                assertion_expected=step_data.get("assertion_expected"),
                assertion_passed=step_data.get("assertion_passed", True),
                error_message=step_data.get("error_message"),
                metadata=step_data.get("metadata", {})
            )
            session.steps.append(step)

        return session
