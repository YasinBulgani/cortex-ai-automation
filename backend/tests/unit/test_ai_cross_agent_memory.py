"""Unit tests for app.domains.ai.cross_agent_memory — in-memory cache layer.

Tests are fully self-contained: CrossAgentMemory uses an in-memory class-level
cache so no DB/Redis is needed. KnowledgeStore calls are mocked out.
Covers: reset, publish, query (filters), get_context_for_agent, stats,
_format_for_storage, _summarize_entry.
"""
from __future__ import annotations

import pytest
from unittest.mock import patch

try:
    from app.domains.ai.cross_agent_memory import CrossAgentMemory
    _IMPORT_OK = True
except ImportError:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="cross_agent_memory import failed")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _reset():
    """Reset class-level cache before and after each test."""
    CrossAgentMemory.reset(run_id="test-run-001", project_id=None)
    yield
    CrossAgentMemory.reset()


@pytest.fixture(autouse=True)
def _no_knowledge_store():
    """Silence KnowledgeStore writes so tests don't hit DB."""
    # The import happens inside the function body so we patch the source module
    with patch("app.domains.ai.knowledge_store.KnowledgeStore", create=True) as mock:
        mock.return_value.ingest.return_value = None
        yield


# ---------------------------------------------------------------------------
# reset
# ---------------------------------------------------------------------------

class TestReset:
    def test_clears_cache(self):
        CrossAgentMemory._cache["k"] = [{"test": True}]
        CrossAgentMemory.reset()
        assert CrossAgentMemory._cache == {}

    def test_sets_run_id(self):
        CrossAgentMemory.reset(run_id="run-42")
        assert CrossAgentMemory._run_id == "run-42"

    def test_run_id_none_by_default(self):
        CrossAgentMemory.reset()
        assert CrossAgentMemory._run_id is None


# ---------------------------------------------------------------------------
# publish
# ---------------------------------------------------------------------------

class TestPublish:
    def test_publish_stores_in_cache(self):
        CrossAgentMemory.publish(
            "DataAnalyst",
            "risk_finding",
            {"project_id": "proj-1", "risk_level": "high"},
        )
        results = CrossAgentMemory.query("proj-1")
        assert len(results) == 1
        assert results[0]["agent_name"] == "DataAnalyst"

    def test_publish_without_project_id_skipped(self):
        CrossAgentMemory.publish(
            "DataAnalyst",
            "risk_finding",
            {},  # no project_id
        )
        # Nothing should be in cache
        assert len(CrossAgentMemory._cache) == 0

    def test_publish_includes_timestamp(self):
        CrossAgentMemory.publish(
            "Analyzer",
            "analysis_complete",
            {"project_id": "proj-1"},
        )
        result = CrossAgentMemory.query("proj-1")[0]
        assert "timestamp" in result
        assert len(result["timestamp"]) > 0

    def test_publish_includes_tags(self):
        CrossAgentMemory.publish(
            "Sec",
            "risk_finding",
            {"project_id": "proj-1"},
            tags=["auth", "critical"],
        )
        result = CrossAgentMemory.query("proj-1")[0]
        assert "auth" in result["tags"]
        assert "critical" in result["tags"]

    def test_publish_multiple_entries_same_key(self):
        for _ in range(3):
            CrossAgentMemory.publish(
                "Agent",
                "test_generated",
                {"project_id": "proj-2"},
            )
        results = CrossAgentMemory.query("proj-2")
        assert len(results) == 3

    def test_publish_stores_run_id(self):
        CrossAgentMemory.reset(run_id="run-99")
        CrossAgentMemory.publish(
            "Agent",
            "analysis_complete",
            {"project_id": "proj-1"},
        )
        result = CrossAgentMemory.query("proj-1")[0]
        assert result["run_id"] == "run-99"


# ---------------------------------------------------------------------------
# query — filters
# ---------------------------------------------------------------------------

class TestQuery:
    def test_empty_cache_returns_empty(self):
        assert CrossAgentMemory.query("proj-1") == []

    def test_empty_project_id_returns_empty(self):
        CrossAgentMemory.publish("A", "ev", {"project_id": "proj-1"})
        assert CrossAgentMemory.query("") == []

    def test_project_isolation(self):
        CrossAgentMemory.publish("A", "ev", {"project_id": "proj-A"})
        CrossAgentMemory.publish("B", "ev", {"project_id": "proj-B"})
        results_a = CrossAgentMemory.query("proj-A")
        results_b = CrossAgentMemory.query("proj-B")
        assert len(results_a) == 1
        assert results_a[0]["agent_name"] == "A"
        assert len(results_b) == 1
        assert results_b[0]["agent_name"] == "B"

    def test_event_type_filter(self):
        CrossAgentMemory.publish("A", "risk_finding", {"project_id": "proj-1"})
        CrossAgentMemory.publish("A", "quality_score", {"project_id": "proj-1"})
        results = CrossAgentMemory.query("proj-1", event_types=["risk_finding"])
        assert len(results) == 1
        assert results[0]["event_type"] == "risk_finding"

    def test_exclude_agent_filter(self):
        CrossAgentMemory.publish("AgentA", "ev", {"project_id": "proj-1"})
        CrossAgentMemory.publish("AgentB", "ev", {"project_id": "proj-1"})
        results = CrossAgentMemory.query("proj-1", exclude_agent="AgentA")
        assert all(r["agent_name"] != "AgentA" for r in results)
        assert len(results) == 1

    def test_tag_filter_at_least_one_match(self):
        CrossAgentMemory.publish("A", "ev", {"project_id": "p"}, tags=["auth"])
        CrossAgentMemory.publish("B", "ev", {"project_id": "p"}, tags=["transfer"])
        results = CrossAgentMemory.query("p", tags=["auth"])
        assert len(results) == 1
        assert results[0]["agent_name"] == "A"

    def test_limit_applied(self):
        for i in range(10):
            CrossAgentMemory.publish("A", "ev", {"project_id": "proj-1"})
        results = CrossAgentMemory.query("proj-1", limit=5)
        assert len(results) == 5

    def test_results_sorted_newest_first(self):
        CrossAgentMemory.publish("A", "ev", {"project_id": "proj-1"})
        CrossAgentMemory.publish("B", "ev", {"project_id": "proj-1"})
        results = CrossAgentMemory.query("proj-1")
        # Most recent should be first
        ts = [r["timestamp"] for r in results]
        assert ts == sorted(ts, reverse=True)


# ---------------------------------------------------------------------------
# get_context_for_agent
# ---------------------------------------------------------------------------

class TestGetContextForAgent:
    def test_empty_memory_returns_empty_string(self):
        result = CrossAgentMemory.get_context_for_agent("MyAgent", "proj-1")
        assert result == ""

    def test_returns_string(self):
        CrossAgentMemory.publish("OtherAgent", "risk_finding", {"project_id": "proj-1", "summary": "Critical auth issue"})
        result = CrossAgentMemory.get_context_for_agent("MyAgent", "proj-1")
        assert isinstance(result, str)

    def test_excludes_requesting_agent(self):
        CrossAgentMemory.publish("MyAgent", "ev", {"project_id": "proj-1"})
        CrossAgentMemory.publish("OtherAgent", "ev", {"project_id": "proj-1", "summary": "test"})
        result = CrossAgentMemory.get_context_for_agent("MyAgent", "proj-1")
        # Should not include MyAgent's own entries
        assert "OtherAgent" in result
        assert result.count("MyAgent") == 0 or "DIGER" in result

    def test_max_chars_respected(self):
        # Publish many entries
        for i in range(20):
            CrossAgentMemory.publish(
                "Agent",
                "analysis_complete",
                {"project_id": "proj-1", "summary": "x" * 200},
            )
        result = CrossAgentMemory.get_context_for_agent("OtherAgent", "proj-1", max_chars=500)
        assert len(result) <= 600  # some tolerance for header


# ---------------------------------------------------------------------------
# stats
# ---------------------------------------------------------------------------

class TestStats:
    def test_empty_cache_returns_zero_total(self):
        stats = CrossAgentMemory.stats("proj-1")
        assert stats["total_entries"] == 0

    def test_empty_project_id_returns_empty(self):
        stats = CrossAgentMemory.stats("")
        assert stats["total_entries"] == 0
        assert stats["project_id"] is None

    def test_counts_entries_correctly(self):
        CrossAgentMemory.publish("A", "risk_finding", {"project_id": "proj-1"})
        CrossAgentMemory.publish("A", "quality_score", {"project_id": "proj-1"})
        CrossAgentMemory.publish("B", "analysis_complete", {"project_id": "proj-1"})
        stats = CrossAgentMemory.stats("proj-1")
        assert stats["total_entries"] == 3

    def test_by_agent_breakdown(self):
        CrossAgentMemory.publish("AgentX", "ev", {"project_id": "p"})
        CrossAgentMemory.publish("AgentX", "ev", {"project_id": "p"})
        CrossAgentMemory.publish("AgentY", "ev", {"project_id": "p"})
        stats = CrossAgentMemory.stats("p")
        assert stats["by_agent"]["AgentX"] == 2
        assert stats["by_agent"]["AgentY"] == 1

    def test_by_event_type_breakdown(self):
        CrossAgentMemory.publish("A", "risk_finding", {"project_id": "p"})
        CrossAgentMemory.publish("B", "risk_finding", {"project_id": "p"})
        CrossAgentMemory.publish("C", "quality_score", {"project_id": "p"})
        stats = CrossAgentMemory.stats("p")
        assert stats["by_event_type"]["risk_finding"] == 2
        assert stats["by_event_type"]["quality_score"] == 1

    def test_top_tags_aggregated(self):
        CrossAgentMemory.publish("A", "ev", {"project_id": "p"}, tags=["auth", "critical"])
        CrossAgentMemory.publish("B", "ev", {"project_id": "p"}, tags=["auth"])
        stats = CrossAgentMemory.stats("p")
        assert stats["top_tags"]["auth"] == 2
        assert stats["top_tags"]["critical"] == 1

    def test_run_id_in_stats(self):
        CrossAgentMemory.reset(run_id="run-test-42")
        stats = CrossAgentMemory.stats("proj-1")
        assert stats["run_id"] == "run-test-42"

    def test_project_isolation_in_stats(self):
        CrossAgentMemory.publish("A", "ev", {"project_id": "proj-A"})
        CrossAgentMemory.publish("B", "ev", {"project_id": "proj-B"})
        stats_a = CrossAgentMemory.stats("proj-A")
        assert stats_a["total_entries"] == 1


# ---------------------------------------------------------------------------
# _format_for_storage
# ---------------------------------------------------------------------------

class TestFormatForStorage:
    def test_returns_string(self):
        entry = {
            "agent_name": "TestAgent",
            "event_type": "risk_finding",
            "data": {"risk_level": "high", "endpoint": "/api/transfer"},
            "tags": ["transfer", "auth"],
        }
        result = CrossAgentMemory._format_for_storage(entry)
        assert isinstance(result, str)

    def test_includes_agent_name(self):
        entry = {"agent_name": "MyAgent", "event_type": "ev", "data": {}, "tags": []}
        result = CrossAgentMemory._format_for_storage(entry)
        assert "MyAgent" in result

    def test_includes_tags(self):
        entry = {"agent_name": "A", "event_type": "ev", "data": {}, "tags": ["auth", "critical"]}
        result = CrossAgentMemory._format_for_storage(entry)
        assert "auth" in result


# ---------------------------------------------------------------------------
# _summarize_entry
# ---------------------------------------------------------------------------

class TestSummarizeEntry:
    def test_extracts_summary_field(self):
        entry = {"agent_name": "A", "event_type": "ev", "data": {"summary": "Critical issue"}}
        result = CrossAgentMemory._summarize_entry(entry)
        assert "Critical issue" in result

    def test_truncates_long_value(self):
        entry = {"agent_name": "A", "event_type": "ev", "data": {"summary": "x" * 200}}
        result = CrossAgentMemory._summarize_entry(entry)
        assert len(result) <= 200  # truncated

    def test_empty_data_returns_string(self):
        entry = {"agent_name": "A", "event_type": "ev", "data": {}}
        result = CrossAgentMemory._summarize_entry(entry)
        assert isinstance(result, str)

    def test_non_dict_data_stringified(self):
        entry = {"agent_name": "A", "event_type": "ev", "data": ["item1", "item2"]}
        result = CrossAgentMemory._summarize_entry(entry)
        assert isinstance(result, str)
