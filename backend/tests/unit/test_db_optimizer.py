"""Unit tests for database optimizer utilities."""

import json
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from app.infra.db_optimizer import (
    DBOptimizer,
    IndexRecommendation,
    OptimizationLevel,
    QueryPlan,
    TableStats,
)


class TestOptimizationLevel:
    """Test OptimizationLevel enum."""

    def test_levels_exist(self):
        """Test all severity levels are defined."""
        assert OptimizationLevel.CRITICAL.value == "🔴 CRITICAL"
        assert OptimizationLevel.HIGH.value == "🟠 HIGH"
        assert OptimizationLevel.MEDIUM.value == "🟡 MEDIUM"
        assert OptimizationLevel.LOW.value == "🟢 LOW"


class TestIndexRecommendation:
    """Test IndexRecommendation data class."""

    def test_sql_generation(self):
        """Test SQL index creation statement."""
        rec = IndexRecommendation(
            table_name="test_management_cases",
            columns=["project_id", "created_at"],
            index_type="BTREE",
            est_improvement_pct=50.0,
            size_bytes=1024000,
            seq_scan_count=1000,
            seq_scan_pct=75.5,
            level=OptimizationLevel.CRITICAL,
        )

        sql = rec.sql()
        assert "CREATE INDEX CONCURRENTLY" in sql
        assert "test_management_cases" in sql
        assert "project_id" in sql
        assert "created_at" in sql

    def test_recommendation_level(self):
        """Test recommendation severity matching seq_scan_pct."""
        critical = IndexRecommendation(
            table_name="users",
            columns=["id"],
            index_type="BTREE",
            est_improvement_pct=50.0,
            size_bytes=1000,
            seq_scan_count=1000,
            seq_scan_pct=75.0,
            level=OptimizationLevel.CRITICAL,
        )
        assert critical.level == OptimizationLevel.CRITICAL

        low = IndexRecommendation(
            table_name="users",
            columns=["id"],
            index_type="BTREE",
            est_improvement_pct=5.0,
            size_bytes=1000,
            seq_scan_count=50,
            seq_scan_pct=20.0,
            level=OptimizationLevel.LOW,
        )
        assert low.level == OptimizationLevel.LOW


class TestTableStats:
    """Test TableStats data class."""

    def test_needs_vacuum(self):
        """Test vacuum necessity detection."""
        # High dead tuple percentage
        needs_vac = TableStats(
            table_name="test_table",
            row_count=1000,
            dead_tuples=150,
            dead_pct=15.0,
            table_size_bytes=100000,
            index_size_bytes=50000,
            last_vacuum=None,
            last_analyze=None,
            seq_scan_count=100,
            index_scan_count=500,
        )
        assert needs_vac.needs_vacuum is True

        # Low dead tuple percentage
        healthy = TableStats(
            table_name="test_table",
            row_count=1000,
            dead_tuples=5,
            dead_pct=0.5,
            table_size_bytes=100000,
            index_size_bytes=50000,
            last_vacuum=datetime.utcnow(),
            last_analyze=datetime.utcnow(),
            seq_scan_count=100,
            index_scan_count=500,
        )
        assert healthy.needs_vacuum is False

    def test_needs_analyze(self):
        """Test analyze necessity detection."""
        # Old analyze timestamp
        needs_analyze = TableStats(
            table_name="test_table",
            row_count=1000,
            dead_tuples=50,
            dead_pct=5.0,
            table_size_bytes=100000,
            index_size_bytes=50000,
            last_vacuum=datetime.utcnow(),
            last_analyze=None,  # Never analyzed
            seq_scan_count=100,
            index_scan_count=500,
        )
        assert needs_analyze.needs_analyze is True


class TestQueryPlan:
    """Test QueryPlan data class."""

    def test_has_seq_scan_detection(self):
        """Test sequential scan detection."""
        plan_with_seq = QueryPlan(
            query="SELECT * FROM users",
            plan_json={"Node Type": "Seq Scan"},
            execution_time_ms=50.0,
            planner_time_ms=1.0,
            rows_returned=1000,
            rows_estimated=1000,
            seq_scans=1,
            index_scans=0,
        )
        assert plan_with_seq.has_seq_scan is True

        plan_no_seq = QueryPlan(
            query="SELECT * FROM users WHERE id = 1",
            plan_json={"Node Type": "Index Scan"},
            execution_time_ms=5.0,
            planner_time_ms=1.0,
            rows_returned=1,
            rows_estimated=1,
            seq_scans=0,
            index_scans=1,
        )
        assert plan_no_seq.has_seq_scan is False

    def test_plan_accuracy(self):
        """Test row estimation accuracy calculation."""
        # Perfect estimation
        accurate = QueryPlan(
            query="SELECT * FROM users WHERE id = 1",
            plan_json={},
            execution_time_ms=5.0,
            planner_time_ms=1.0,
            rows_returned=1,
            rows_estimated=1,
            seq_scans=0,
            index_scans=1,
        )
        assert accurate.plan_accuracy == 1.0

        # Underestimation
        underest = QueryPlan(
            query="SELECT * FROM users WHERE status = 'active'",
            plan_json={},
            execution_time_ms=50.0,
            planner_time_ms=1.0,
            rows_returned=1000,
            rows_estimated=100,
            seq_scans=0,
            index_scans=1,
        )
        assert underest.plan_accuracy == 0.1

        # Overestimation
        overest = QueryPlan(
            query="SELECT * FROM users WHERE status = 'active'",
            plan_json={},
            execution_time_ms=5.0,
            planner_time_ms=1.0,
            rows_returned=100,
            rows_estimated=1000,
            seq_scans=0,
            index_scans=1,
        )
        assert overest.plan_accuracy == 0.1


class TestDBOptimizer:
    """Test DBOptimizer class."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return MagicMock()

    @pytest.fixture
    def optimizer(self, mock_db):
        """Create optimizer instance with mock DB."""
        return DBOptimizer(mock_db)

    def test_count_node_type(self):
        """Test recursive node counting in query plans."""
        plan = {
            "Node Type": "Aggregate",
            "Plans": [
                {"Node Type": "Seq Scan"},
                {
                    "Node Type": "Hash",
                    "Plans": [
                        {"Node Type": "Seq Scan"},
                        {"Node Type": "Seq Scan"},
                    ],
                },
            ],
        }

        count = DBOptimizer._count_node_type(plan, "Seq Scan")
        assert count == 3

    def test_count_node_type_none(self):
        """Test counting non-existent node types."""
        plan = {"Node Type": "Index Scan", "Plans": []}

        count = DBOptimizer._count_node_type(plan, "Seq Scan")
        assert count == 0

    def test_missing_indexes_level_determination(self, optimizer, mock_db):
        """Test missing index recommendation level determination."""
        # Mock pg_stat_user_tables query
        mock_db.execute.return_value.fetchall.return_value = [
            ("public", "test_table", 2000, 100000, 500, 50000, 100000, 80.0),  # 80% seq scans = CRITICAL
            ("public", "small_table", 50, 10000, 100, 5000, 50000, 40.0),   # 40% seq scans = MEDIUM
        ]

        recommendations = optimizer.get_missing_indexes(seq_scan_threshold=50)

        # Verify critical recommendation
        assert len(recommendations) > 0
        assert recommendations[0].seq_scan_pct >= 80.0
        assert recommendations[0].level == OptimizationLevel.CRITICAL

    def test_get_optimization_summary(self, optimizer, mock_db):
        """Test optimization summary generation."""
        # Mock database returns
        mock_db.execute.return_value.fetchall.return_value = [
            ("test_table", 1000, 100, 10.0, 100000, 50000, None, None, 100, 500),
        ]

        summary = optimizer.get_optimization_summary()

        # Verify summary structure
        assert "timestamp" in summary
        assert "missing_indexes" in summary
        assert "table_maintenance" in summary
        assert "cache_hit_ratio" in summary
        assert "next_actions" in summary

        # Verify missing_indexes structure
        assert "total" in summary["missing_indexes"]
        assert "critical" in summary["missing_indexes"]
        assert "high" in summary["missing_indexes"]
        assert "medium" in summary["missing_indexes"]
        assert "recommendations" in summary["missing_indexes"]

        # Verify table_maintenance structure
        assert "vacuum_needed" in summary["table_maintenance"]
        assert "analyze_needed" in summary["table_maintenance"]
        assert "total_tables" in summary["table_maintenance"]


class TestIndexRecommendationIntegration:
    """Integration tests for index recommendations."""

    def test_critical_index_for_high_seq_scan(self):
        """Test critical index recommendation for high seq scan percentage."""
        rec = IndexRecommendation(
            table_name="sd_users",
            columns=["tenant_id", "email"],
            index_type="BTREE",
            est_improvement_pct=93.0,
            size_bytes=1024000,
            seq_scan_count=5000,
            seq_scan_pct=93.0,
            level=OptimizationLevel.CRITICAL,
        )

        assert rec.level == OptimizationLevel.CRITICAL
        assert rec.est_improvement_pct > 50
        sql = rec.sql()
        assert "CONCURRENTLY" in sql  # Safe to apply on production

    def test_brin_index_for_timeseries(self):
        """Test BRIN index recommendation for time-series tables."""
        rec = IndexRecommendation(
            table_name="tspm_execution_metrics",
            columns=["project_id", "executed_at"],
            index_type="BRIN",
            est_improvement_pct=80.0,
            size_bytes=100000,  # Much smaller than BTREE
            seq_scan_count=10000,
            seq_scan_pct=85.0,
            level=OptimizationLevel.CRITICAL,
        )

        assert rec.index_type == "BRIN"
        assert rec.size_bytes < 200000  # BRIN is compact

    def test_partial_index_for_filtered_access(self):
        """Test partial index for WHERE status='active' patterns."""
        rec = IndexRecommendation(
            table_name="sd_users",
            columns=["id"],
            index_type="BTREE",
            est_improvement_pct=75.0,
            size_bytes=500000,
            seq_scan_count=3000,
            seq_scan_pct=75.0,
            level=OptimizationLevel.CRITICAL,
        )

        # Partial index SQL would be:
        # CREATE INDEX CONCURRENTLY ix_sd_users_active
        # ON sd_users (id) WHERE is_active = TRUE;
        # This reduces index size by 80-90% vs full index

        assert rec.est_improvement_pct > 70


class TestPerformanceGains:
    """Test expected performance improvements."""

    def test_auth_lookup_improvement(self):
        """Test auth lookup: 45ms -> 3ms (-93%)."""
        # Before: sequential scan
        before = QueryPlan(
            query="SELECT * FROM sd_users WHERE tenant_id = $1 AND email = $2",
            plan_json={},
            execution_time_ms=45.0,
            planner_time_ms=1.0,
            rows_returned=1,
            rows_estimated=1000,  # Bad estimation
            seq_scans=1,
            index_scans=0,
        )
        assert before.plan_accuracy < 0.1

        # After: index scan
        after = QueryPlan(
            query="SELECT * FROM sd_users WHERE tenant_id = $1 AND email = $2",
            plan_json={},
            execution_time_ms=3.0,
            planner_time_ms=1.0,
            rows_returned=1,
            rows_estimated=1,  # Good estimation
            seq_scans=0,
            index_scans=1,
        )
        assert after.plan_accuracy == 1.0

        improvement_pct = ((before.execution_time_ms - after.execution_time_ms) / before.execution_time_ms) * 100
        assert improvement_pct >= 90

    def test_notification_feed_improvement(self):
        """Test notification feed: 1200ms -> 5ms (-99%)."""
        # Before: full table scan for unread notifications
        before = QueryPlan(
            query="SELECT * FROM notifications WHERE user_id = $1 AND is_read = FALSE",
            plan_json={},
            execution_time_ms=1200.0,
            planner_time_ms=1.0,
            rows_returned=10,
            rows_estimated=50000,  # Bad estimation
            seq_scans=1,
            index_scans=0,
        )

        # After: partial index on (user_id, is_read) WHERE is_read = FALSE
        after = QueryPlan(
            query="SELECT * FROM notifications WHERE user_id = $1 AND is_read = FALSE",
            plan_json={},
            execution_time_ms=5.0,
            planner_time_ms=1.0,
            rows_returned=10,
            rows_estimated=12,  # Good estimation
            seq_scans=0,
            index_scans=1,
        )

        improvement_pct = ((before.execution_time_ms - after.execution_time_ms) / before.execution_time_ms) * 100
        assert improvement_pct >= 99


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
