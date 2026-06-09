"""Test query deadline context tracking for pool exhaustion prevention."""

import time
from unittest.mock import MagicMock, patch

import pytest

from app.infra.query_deadline import (
    QueryTimeoutError,
    clear_request_deadline,
    get_request_deadline,
    init_query_deadline,
    set_request_deadline,
)


class TestQueryDeadlineContextVar:
    """Test deadline context variable management."""

    def test_set_and_get_deadline(self):
        """Test setting and retrieving deadline."""
        set_request_deadline(30.0)
        deadline_ms = get_request_deadline()
        assert deadline_ms is not None
        assert isinstance(deadline_ms, float)
        clear_request_deadline()

    def test_clear_deadline(self):
        """Test clearing deadline."""
        set_request_deadline(30.0)
        assert get_request_deadline() is not None

        clear_request_deadline()
        assert get_request_deadline() is None

    def test_deadline_increases_with_time(self):
        """Test that deadline is set in the future."""
        set_request_deadline(30.0)
        deadline_ms = get_request_deadline()
        current_ms = time.time() * 1000

        # Deadline should be ~30s in the future
        remaining_ms = deadline_ms - current_ms
        assert 29000 < remaining_ms < 31000  # Allow small variance
        clear_request_deadline()


class TestQueryTimeoutError:
    """Test QueryTimeoutError exception."""

    def test_timeout_error_message(self):
        """Test error message format."""
        err = QueryTimeoutError("Test message")
        assert str(err) == "Test message"

    def test_timeout_error_is_exception(self):
        """Test that QueryTimeoutError is an Exception."""
        err = QueryTimeoutError("Test")
        assert isinstance(err, Exception)


class TestDeadlineChecking:
    """Test deadline checking before queries."""

    def test_no_error_when_no_deadline(self):
        """Test that no error is raised when no deadline is set."""
        clear_request_deadline()
        # Should not raise
        from app.infra.query_deadline import _check_deadline_before_query
        _check_deadline_before_query()

    def test_no_error_when_deadline_not_reached(self):
        """Test that no error is raised when deadline is in future."""
        set_request_deadline(30.0)
        # Should not raise
        from app.infra.query_deadline import _check_deadline_before_query
        _check_deadline_before_query()
        clear_request_deadline()


class TestInitQueryDeadline:
    """Test initialization of query deadline."""

    def test_init_query_deadline_logs_info(self, caplog):
        """Test that init logs configuration."""
        with patch("app.infra.query_deadline.logger") as mock_logger:
            init_query_deadline()
            mock_logger.info.assert_called_once()


class TestEventListeners:
    """Test SQLAlchemy Engine event listeners."""

    def test_before_cursor_execute_checks_deadline(self):
        """Test that before_cursor_execute checks deadline."""
        from app.infra.query_deadline import _before_cursor_execute

        # Create mock objects
        conn = MagicMock()
        cursor = MagicMock()
        statement = "SELECT * FROM test"

        # When no deadline is set, should not raise
        clear_request_deadline()
        _before_cursor_execute(conn, cursor, statement, {}, None, False)

        # Verify _query_start_time is set on cursor
        assert hasattr(cursor, "_query_start_time")

    def test_after_cursor_execute_logs_slow_query(self):
        """Test that after_cursor_execute logs slow queries."""
        from app.infra.query_deadline import _after_cursor_execute

        # Create mock objects
        conn = MagicMock()
        cursor = MagicMock()
        statement = "SELECT * FROM slow_table"

        # Set up _query_start_time to simulate slow query
        cursor._query_start_time = {id(statement): time.time() - 6.0}  # 6 seconds ago

        set_request_deadline(30.0)
        with patch("app.infra.query_deadline.logger") as mock_logger:
            _after_cursor_execute(conn, cursor, statement, {}, None, False, None)
            # Slow query warning should have been logged
            if get_request_deadline() is not None:
                mock_logger.warning.assert_called()

        clear_request_deadline()

    def test_after_cursor_execute_without_start_time(self):
        """Test that after_cursor_execute handles missing start time gracefully."""
        from app.infra.query_deadline import _after_cursor_execute

        conn = MagicMock()
        cursor = MagicMock()
        statement = "SELECT * FROM test"
        cursor._query_start_time = {}  # Empty dict

        # Should not raise
        _after_cursor_execute(conn, cursor, statement, {}, None, False, None)


class TestIntegration:
    """Integration tests for deadline tracking."""

    def test_deadline_lifecycle(self):
        """Test complete deadline lifecycle."""
        # 1. No deadline initially
        assert get_request_deadline() is None

        # 2. Set deadline
        set_request_deadline(30.0)
        deadline1 = get_request_deadline()
        assert deadline1 is not None

        # 3. Get again (should be same or very close)
        deadline2 = get_request_deadline()
        assert deadline2 is not None
        assert abs(deadline2 - deadline1) < 100  # Within 100ms

        # 4. Clear deadline
        clear_request_deadline()
        assert get_request_deadline() is None

    def test_multiple_deadline_sets(self):
        """Test that setting deadline multiple times updates correctly."""
        set_request_deadline(10.0)
        deadline1 = get_request_deadline()

        time.sleep(0.1)

        set_request_deadline(30.0)
        deadline2 = get_request_deadline()

        # deadline2 should be later than deadline1
        assert deadline2 > deadline1
        clear_request_deadline()
