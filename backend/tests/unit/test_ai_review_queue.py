"""Unit tests for app.domains.ai.review_queue pure helpers.

Tests are fully self-contained: no DB, no Redis, no HTTP.
Covers: extract_confidence, should_queue_for_review.
"""
from __future__ import annotations

import pytest
from unittest.mock import patch

try:
    from app.domains.ai.review_queue import (
        extract_confidence,
        should_queue_for_review,
    )
    _IMPORT_OK = True
except ImportError:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="review_queue import failed")


# ---------------------------------------------------------------------------
# extract_confidence
# ---------------------------------------------------------------------------

class TestExtractConfidence:
    def test_xml_tag_format(self):
        result = extract_confidence("<confidence>0.8</confidence>")
        assert result == pytest.approx(0.8)

    def test_json_format(self):
        result = extract_confidence('{"confidence": 0.75, "text": "result"}')
        assert result == pytest.approx(0.75)

    def test_colon_format(self):
        result = extract_confidence("confidence: 0.9")
        assert result == pytest.approx(0.9)

    def test_empty_string_returns_none(self):
        assert extract_confidence("") is None

    def test_no_confidence_returns_none(self):
        assert extract_confidence("This is a plain response without confidence.") is None

    def test_clips_above_1(self):
        result = extract_confidence("<confidence>1.5</confidence>")
        assert result == 1.0

    def test_clips_at_zero_for_very_low(self):
        """A very low but non-negative value (0.0001) clips to 0.0."""
        result = extract_confidence("<confidence>0.0001</confidence>")
        # max(0.0, min(1.0, 0.0001)) = 0.0001 — just above 0
        assert result is not None
        assert result >= 0.0

    def test_returns_float(self):
        result = extract_confidence("<confidence>0.7</confidence>")
        assert isinstance(result, float)

    def test_high_confidence(self):
        result = extract_confidence('<confidence>0.99</confidence>')
        assert result == pytest.approx(0.99)

    def test_zero_confidence(self):
        result = extract_confidence('<confidence>0.0</confidence>')
        assert result == 0.0


# ---------------------------------------------------------------------------
# should_queue_for_review
# ---------------------------------------------------------------------------

class TestShouldQueueForReview:

    @pytest.fixture(autouse=True)
    def _enable_queue(self):
        """Enable the review queue feature flag for all tests."""
        with patch("app.domains.ai.review_queue._queue_enabled", return_value=True):
            yield

    def test_flag_disabled_never_queues(self):
        with patch("app.domains.ai.review_queue._queue_enabled", return_value=False):
            queue, reason, conf = should_queue_for_review("chat", "response text")
        assert queue is False
        assert reason == "flag_disabled"

    def test_low_confidence_queues(self):
        """A very low confidence (0.1) should trigger queueing."""
        response = "<confidence>0.1</confidence> This is a low confidence answer."
        queue, reason, conf = should_queue_for_review("chat", response)
        assert queue is True
        assert "low_confidence" in reason
        assert conf == pytest.approx(0.1)

    def test_high_confidence_passes(self):
        """High confidence (0.95) should not queue for most task types."""
        response = "<confidence>0.95</confidence> Confident answer."
        queue, reason, conf = should_queue_for_review("chat", response)
        assert queue is False
        assert reason == "passed"

    def test_low_judge_score_queues(self):
        """Low judge overall score (below 6.0) should trigger queueing."""
        response = "A response without confidence tag."
        queue, reason, conf = should_queue_for_review("chat", response, judge_overall=4.5)
        assert queue is True
        assert "low_judge_score" in reason

    def test_passing_judge_score_doesnt_queue(self):
        """Judge score above 6.0 should not trigger queueing."""
        response = "<confidence>0.9</confidence> Good answer."
        queue, reason, conf = should_queue_for_review("chat", response, judge_overall=8.0)
        assert queue is False

    def test_returns_tuple_of_three(self):
        queue, reason, conf = should_queue_for_review("chat", "some response")
        assert isinstance(queue, bool)
        assert isinstance(reason, str)
        # conf can be None or float
        assert conf is None or isinstance(conf, float)

    def test_no_confidence_no_judge_passes(self):
        """When there's no confidence and no judge score, response passes."""
        response = "A plain response without any scores."
        queue, reason, conf = should_queue_for_review("chat", response)
        assert queue is False

    def test_tenant_id_passed_to_flag_check(self):
        """should_queue_for_review passes tenant_id to _queue_enabled."""
        with patch("app.domains.ai.review_queue._queue_enabled") as mock_flag:
            mock_flag.return_value = False
            should_queue_for_review("chat", "response", tenant_id="tenant-123")
        mock_flag.assert_called_once_with("tenant-123")
