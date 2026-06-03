"""
Recorder routes — Flask engine'den port edilmiş.

ÖNCE (Flask):
  /engine/routes/recorder_routes.py — Blueprint, port 5001

SONRA (FastAPI):
  /backend/app/engine/routes/recorder.py — APIRouter, port 8000 (consolidated)
"""
from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Annotated, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/recorder", tags=["engine", "recorder"])

# ─── In-memory oturum deposu ─────────────────────────────────────────────────

_active_sessions: dict[str, Any] = {}


def _get_recorder(session_id: str) -> Any:
    return _active_sessions.get(session_id)


# ─── Schemas ─────────────────────────────────────────────────────────────────

class StartRecordingBody(BaseModel):
    name: str = Field(..., min_length=1)
    domain: str = "default"
    base_url: str = ""


class ActionBody(BaseModel):
    action_type: str = Field(..., min_length=1)
    selector: str = ""
    value: str = ""
    selector_type: str = "css"
    element_name: str = ""
    element_info: Optional[dict] = None
    metadata: dict = Field(default_factory=dict)


class GenerateCodeBody(BaseModel):
    session_path: str = Field(..., min_length=1)
    format: str = "playwright"
    class_name: str = ""
    feature_title: str = ""


class GenerateDownloadBody(BaseModel):
    session_path: str = Field(..., min_length=1)
    format: str = "playwright"


# ─── Settings stub — gerçek config'den alınacak ──────────────────────────────

class _Settings:
    """Geçici placeholder. Migration tamamlanınca app.config.settings kullanılacak."""
    BASE_DIR: Path = Path(__file__).resolve().parents[5]  # repo root

_settings = _Settings()


# ─── Oturum Yönetimi ─────────────────────────────────────────────────────────

@router.post("/start", status_code=status.HTTP_200_OK)
def start_recording(body: StartRecordingBody):
    """Yeni bir kayıt oturumu başlatır."""
    try:
        from core.test_recorder import TestRecorder  # type: ignore[import]
        session_id = str(uuid.uuid4())[:8]
        recorder = TestRecorder(name=body.name, domain=body.domain, base_url=body.base_url)
        recorder.start()
        _active_sessions[session_id] = recorder
        return {
            "ok": True,
            "session_id": session_id,
            "name": body.name,
            "domain": body.domain,
        }
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post("/{session_id}/stop")
def stop_recording(session_id: str):
    """Kayıt oturumunu durdurur ve JSON dosyasına kaydeder."""
    recorder = _get_recorder(session_id)
    if not recorder:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Oturum bulunamadı")
    try:
        session = recorder.stop()
        saved_path = recorder.save_session()
        _active_sessions.pop(session_id, None)
        return {
            "ok": True,
            "session_id": session_id,
            "saved_path": saved_path,
            "action_count": len(session.actions),
        }
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post("/{session_id}/pause")
def pause_recording(session_id: str):
    """Aktif kayıt oturumunu duraklatır."""
    recorder = _get_recorder(session_id)
    if not recorder:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Oturum bulunamadı")
    try:
        recorder.pause()
        return {"ok": True, "session_id": session_id, "paused": True}
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post("/{session_id}/resume")
def resume_recording(session_id: str):
    """Duraklatılmış kayıt oturumunu devam ettirir."""
    recorder = _get_recorder(session_id)
    if not recorder:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Oturum bulunamadı")
    try:
        recorder.resume()
        return {"ok": True, "session_id": session_id, "paused": False}
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.get("/{session_id}/status")
def recording_status(session_id: str):
    """Aktif bir kayıt oturumunun anlık durumunu döner."""
    recorder = _get_recorder(session_id)
    if not recorder:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Oturum bulunamadı")
    try:
        session = recorder.session
        return {
            "ok": True,
            "session_id": session_id,
            "paused": recorder.is_paused,
            "action_count": len(session.actions),
            "name": session.name,
            "domain": session.domain,
        }
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.get("/sessions")
def list_sessions(domain: Optional[str] = Query(default=None)):
    """Kaydedilmiş oturumları listeler. domain query param ile filtrelenebilir."""
    try:
        records_dir = _settings.BASE_DIR / "recordings"
        records_dir.mkdir(exist_ok=True)
        sessions = []
        for f in sorted(records_dir.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                if domain and data.get("domain") != domain:
                    continue
                sessions.append({
                    "file": f.name,
                    "path": str(f),
                    "name": data.get("name", f.stem),
                    "domain": data.get("domain", ""),
                    "action_count": len(data.get("actions", [])),
                    "started_at": data.get("started_at", ""),
                })
            except Exception:
                continue
        return {"ok": True, "sessions": sessions, "count": len(sessions)}
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.delete("/sessions/{session_file:path}", status_code=status.HTTP_200_OK)
def delete_session(session_file: str):
    """Kaydedilmiş bir oturumu siler."""
    records_dir = _settings.BASE_DIR / "recordings"
    target = (records_dir / session_file).resolve()
    # Güvenlik: sadece recordings dizinindeki dosyalar
    try:
        target.relative_to(records_dir.resolve())
    except ValueError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Geçersiz dosya yolu")
    if not target.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dosya bulunamadı")
    try:
        target.unlink()
        return {"ok": True}
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


# ─── Aksiyon Ekleme ──────────────────────────────────────────────────────────

@router.post("/{session_id}/action")
def add_action(session_id: str, body: ActionBody):
    """Aktif oturuma aksiyon ekler."""
    try:
        from core.test_recorder import RecordedAction  # type: ignore[import]
        recorder = _get_recorder(session_id)
        if not recorder:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aktif oturum bulunamadı")
        action = recorder._recorder.record(
            action_type=body.action_type,
            selector=body.selector,
            value=body.value,
            selector_type=body.selector_type,
            element_info=body.element_info,
            metadata=body.metadata,
        )
        if body.element_name:
            action.element_name = body.element_name
        return {
            "ok": True,
            "action": action.to_dict(),
            "total_actions": len(recorder.session.actions),
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.get("/{session_id}/actions")
def get_actions(session_id: str):
    """Aktif oturumdaki tüm aksiyonları döner."""
    recorder = _get_recorder(session_id)
    if not recorder:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Oturum bulunamadı")
    try:
        actions = [a.to_dict() for a in recorder.session.actions]
        return {"ok": True, "actions": actions, "count": len(actions)}
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


# ─── Kod Üretimi ─────────────────────────────────────────────────────────────

@router.post("/generate")
def generate_code(body: GenerateCodeBody):
    """Kaydedilmiş oturumdan kod üretir."""
    try:
        from core.test_recorder import TestRecorder  # type: ignore[import]
        p = Path(body.session_path)
        if not p.exists():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Oturum dosyası bulunamadı")
        recorder = TestRecorder.load_session(p)
        fmt = body.format

        if fmt == "playwright":
            return {"ok": True, "code": recorder.to_playwright(), "format": "playwright"}
        elif fmt == "cucumber":
            return {"ok": True, "code": recorder.to_cucumber(feature_title=body.feature_title), "format": "cucumber"}
        elif fmt == "pom_python":
            return {"ok": True, "code": recorder.to_pom_python(), "format": "pom_python"}
        elif fmt == "pom_java":
            return {"ok": True, "code": recorder.to_pom_java(), "format": "pom_java"}
        elif fmt == "locators":
            return {"ok": True, "locators": recorder.to_locators(), "format": "locators"}
        elif fmt == "pom_typescript":
            from core.pom_ts_generator import POMTypeScriptGenerator  # type: ignore[import]
            gen = POMTypeScriptGenerator()
            code = gen.from_session(recorder.session.to_dict(), class_name=body.class_name)
            return {"ok": True, "code": code, "format": "pom_typescript"}
        elif fmt == "all":
            files = recorder.save_all()
            return {"ok": True, "files": files, "format": "all"}
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Bilinmeyen format: {fmt}")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post("/generate/download")
def generate_and_download(body: GenerateDownloadBody):
    """Kod üretir ve doğrudan dosya olarak indirir."""
    import tempfile

    try:
        from core.test_recorder import TestRecorder  # type: ignore[import]
        p = Path(body.session_path)
        if not p.exists():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Oturum dosyası bulunamadı")
        recorder = TestRecorder.load_session(p)
        fmt = body.format
        ext_map = {
            "playwright": (".py",      "text/x-python"),
            "cucumber":   (".feature", "text/plain"),
            "pom_python": (".py",      "text/x-python"),
            "pom_java":   (".java",    "text/x-java"),
            "locators":   (".json",    "application/json"),
        }
        if fmt not in ext_map:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Bilinmeyen format: {fmt}")
        ext, mime = ext_map[fmt]

        if fmt == "playwright":
            content = recorder.to_playwright()
        elif fmt == "cucumber":
            content = recorder.to_cucumber()
        elif fmt == "pom_python":
            content = recorder.to_pom_python()
        elif fmt == "pom_java":
            content = recorder.to_pom_java()
        else:  # locators
            content = json.dumps(recorder.to_locators(), indent=2, ensure_ascii=False)

        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=ext, delete=False, encoding="utf-8")
        tmp.write(content)
        tmp.flush()
        tmp.close()

        fname = f"{recorder.name}_{fmt}{ext}"
        return FileResponse(
            path=tmp.name,
            media_type=mime,
            filename=fname,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


# ─── Locator Yönetimi ────────────────────────────────────────────────────────

@router.get("/locators/{domain}")
def list_locators(domain: str):
    """Domain'e ait mevcut locator dosyalarını listeler."""
    try:
        loc_dir = _settings.BASE_DIR / "locators" / domain
        if not loc_dir.exists():
            return {"ok": True, "locators": [], "count": 0}
        files = []
        for f in sorted(loc_dir.glob("*_locators.json")):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                files.append({
                    "file": f.name,
                    "path": str(f),
                    "element_count": len(data),
                })
            except Exception:
                continue
        return {"ok": True, "locators": files, "count": len(files)}
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.get("/locators/{domain}/{filename:path}")
def get_locators(domain: str, filename: str):
    """Belirli bir locator dosyasının içeriğini döner."""
    loc_dir = _settings.BASE_DIR / "locators" / domain
    target = (loc_dir / filename).resolve()
    try:
        target.relative_to(loc_dir.resolve())
    except ValueError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Geçersiz dosya yolu")
    if not target.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dosya bulunamadı")
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
        return {"ok": True, "locators": data, "file": filename}
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))
