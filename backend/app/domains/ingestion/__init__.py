"""Requirement ingestion — Jira / Confluence / direct-document webhook → AC extraction → event publish."""
from app.domains.ingestion.service import (
    IngestedRequirement,
    AcceptanceCriterion,
    ingest_text,
    ingest_jira_payload,
    ingest_confluence_payload,
    list_ingested,
    get_ingested,
    clear,
)

__all__ = [
    "IngestedRequirement",
    "AcceptanceCriterion",
    "ingest_text",
    "ingest_jira_payload",
    "ingest_confluence_payload",
    "list_ingested",
    "get_ingested",
    "clear",
]
