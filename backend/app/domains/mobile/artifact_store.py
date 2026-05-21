"""Mobile artifact store.

Ilk surum local filesystem kullanir. API ve runner bu modulu kullanarak
ileride MinIO/S3 adapter'a gecisi tek yerde tutar.
"""
from __future__ import annotations

import hashlib
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .schemas import MobileArtifact


_SAFE_PART_RE = re.compile(r"[^a-zA-Z0-9_.-]+")


def _safe_part(value: str) -> str:
    cleaned = _SAFE_PART_RE.sub("_", value).strip("._")
    return cleaned or "artifact"


def _is_inside(child: Path, parent: Path) -> bool:
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def default_mobile_artifact_root() -> Path:
    raw = os.environ.get("MOBILE_ARTIFACTS_DIR")
    if raw:
        return Path(raw).expanduser().resolve()
    return (Path.cwd() / "data" / "artifacts" / "mobile").resolve()


class MobileArtifactStore:
    """Local artifact writer with path containment and sha256 metadata."""

    def __init__(self, root: Optional[Path] = None) -> None:
        self.root = (root or default_mobile_artifact_root()).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self._artifacts: dict[str, MobileArtifact] = {}

    def save_bytes(
        self,
        *,
        session_id: str,
        kind: str,
        data: bytes,
        step_seq: Optional[int] = None,
        extension: str = "bin",
        mime_type: str = "application/octet-stream",
    ) -> MobileArtifact:
        artifact_id = f"ma_{uuid.uuid4().hex[:12]}"
        session_dir = (self.root / _safe_part(session_id)).resolve()
        if not _is_inside(session_dir, self.root):
            raise ValueError("Artifact session path root disina cikiyor")
        session_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{artifact_id}_{_safe_part(kind)}.{_safe_part(extension.lstrip('.'))}"
        path = (session_dir / filename).resolve()
        if not _is_inside(path, session_dir):
            raise ValueError("Artifact path session root disina cikiyor")
        path.write_bytes(data)

        artifact = MobileArtifact(
            id=artifact_id,
            session_id=session_id,
            step_seq=step_seq,
            kind=kind,  # type: ignore[arg-type]
            path=str(path),
            mime_type=mime_type,
            size_bytes=len(data),
            sha256=hashlib.sha256(data).hexdigest(),
            created_at=datetime.now(timezone.utc),
        )
        self._artifacts[artifact.id] = artifact
        return artifact

    def save_text(
        self,
        *,
        session_id: str,
        kind: str,
        text: str,
        step_seq: Optional[int] = None,
        extension: str = "txt",
        mime_type: str = "text/plain; charset=utf-8",
    ) -> MobileArtifact:
        return self.save_bytes(
            session_id=session_id,
            kind=kind,
            data=text.encode("utf-8"),
            step_seq=step_seq,
            extension=extension,
            mime_type=mime_type,
        )

    def get(self, artifact_id: str) -> Optional[MobileArtifact]:
        return self._artifacts.get(artifact_id)

    def list_for_session(self, session_id: str) -> list[MobileArtifact]:
        return [a for a in self._artifacts.values() if a.session_id == session_id]


_store: Optional[MobileArtifactStore] = None


def get_artifact_store() -> MobileArtifactStore:
    global _store
    if _store is None:
        _store = MobileArtifactStore()
    return _store
