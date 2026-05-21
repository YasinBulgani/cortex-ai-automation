from typing import Any, Dict, Optional

from pydantic import BaseModel


class GenerationJobCreate(BaseModel):
    dataset_version_id: str
    rule_set_id: Optional[str] = None


class GenerationJobOut(BaseModel):
    id: str
    dataset_version_id: str
    rule_set_id: Optional[str]
    status: str
    rq_job_id: Optional[str]
    error_message: Optional[str]
    created_at: object
    updated_at: object


class JobEventOut(BaseModel):
    id: str
    job_id: str
    ts: object
    level: str
    message: str
    payload: Optional[Dict[str, Any]]


class ArtifactOut(BaseModel):
    id: str
    job_id: str
    mime_type: str
    size_bytes: int
    created_at: object
