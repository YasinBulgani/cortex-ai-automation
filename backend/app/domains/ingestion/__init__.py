"""Requirement ingestion — Jira / Confluence / direct-document webhook → AC extraction → event publish."""
from app.domains.ingestion.service import (
    AcceptanceCriterion,
    IngestedRequirement,
    clear,
    get_ingested,
    ingest_confluence_payload,
    ingest_jira_payload,
    ingest_text,
    list_ingested,
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
