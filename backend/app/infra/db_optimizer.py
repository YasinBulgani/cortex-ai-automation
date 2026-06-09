"""PostgreSQL Performance Optimizer & Monitoring Utilities

Provides:
- Index recommendation engine
- Query plan analysis
- Table statistics monitoring
- Automated optimization suggestions
- Performance baseline tracking
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class OptimizationLevel(Enum):
    """Optimization severity level."""
    CRITICAL = "🔴 CRITICAL"
    HIGH = "🟠 HIGH"
    MEDIUM = "🟡 MEDIUM"
    LOW = "🟢 LOW"


@dataclass
class IndexRecommendation:
    """Recommended index to improve performance."""
    table_name: str
    columns: list[str]
    index_type: str  # BTREE, BRIN, GIN, GIST
    est_improvement_pct: float  # Expected performance gain
    size_bytes: int
    seq_scan_count: int
    seq_scan_pct: float
    level: OptimizationLevel

    def sql(self) -> str:
        """Generate CREATE INDEX statement."""
        columns_str = ", ".join(self.columns)
        index_name = f"ix_{self.table_name}_{'_'.join(self.columns)}"
        return f"CREATE INDEX CONCURRENTLY {index_name} ON {self.table_name} ({columns_str});"


@dataclass
class TableStats:
    """Database table statistics."""
    table_name: str
    row_count: int
    dead_tuples: int
    dead_pct: float
    table_size_bytes: int
    index_size_bytes: int
    last_vacuum: Optional[datetime]
    last_analyze: Optional[datetime]
    seq_scan_count: int
    index_scan_count: int

    @property
    def needs_vacuum(self) -> bool:
        """Check if table needs vacuuming."""
        return self.dead_pct > 10

    @property
    def needs_analyze(self) -> bool:
        """Check if table statistics are stale."""
        if not self.last_analyze:
            return True
        age_hours = (datetime.utcnow() - self.last_analyze).total_seconds() / 3600
        return age_hours > 24 or self.dead_pct > 20


@dataclass
class QueryPlan:
    """Query execution plan analysis."""
    query: str
    plan_json: dict[str, Any]
    execution_time_ms: float
    planner_time_ms: float
    rows_returned: int
    rows_estimated: int
    seq_scans: int
    index_scans: int

    @property
    def has_seq_scan(self) -> bool:
        """Check if plan contains sequential scans."""
        return self.seq_scans > 0

    @property
    def plan_accuracy(self) -> float:
        """Row estimation accuracy (0-1, higher is better)."""
        if self.rows_estimated == 0:
            return 0.0
        return min(self.rows_returned, self.rows_estimated) / max(self.rows_returned, self.rows_estimated)


class DBOptimizer:
    """Database optimization engine."""

    def __init__(self, db: Session):
        """Initialize optimizer with DB session."""
        self.db = db

    def get_missing_indexes(self, seq_scan_threshold: int = 100) -> list[IndexRecommendation]:
        """Identify missing indexes based on sequential scan patterns.

        Args:
            seq_scan_threshold: Minimum seq_scan count to recommend index

        Returns:
            List of index recommendations sorted by impact
        """
        query = text("""
            SELECT
                schemaname,
                tablename,
                seq_scan,
                seq_tup_read,
                idx_scan,
                idx_tup_fetch,
                pg_total_relation_size(schemaname||'.'||tablename) as size_bytes,
                ROUND(100 * seq_scan / NULLIF(seq_scan + idx_scan, 0), 2) as seq_scan_pct
            FROM pg_stat_user_tables
            WHERE seq_scan > :threshold AND schemaname = 'public'
            ORDER BY seq_scan DESC;
        """)

        results = self.db.execute(query, {"threshold": seq_scan_threshold}).fetchall()
        recommendations = []

        for row in results:
            table = row[1]
            seq_scans = row[2]
            seq_scan_pct = row[7]
            size_bytes = row[6]

            # Determine severity level
            if seq_scan_pct > 70:
                level = OptimizationLevel.CRITICAL
                est_improvement = 50.0
            elif seq_scan_pct > 50:
                level = OptimizationLevel.HIGH
                est_improvement = 30.0
            elif seq_scan_pct > 30:
                level = OptimizationLevel.MEDIUM
                est_improvement = 15.0
            else:
                level = OptimizationLevel.LOW
                est_improvement = 5.0

            # Estimate index size (typically 10-20% of table size)
            est_index_size = int(size_bytes * 0.15)

            # Build recommendation
            rec = IndexRecommendation(
                table_name=table,
                columns=["project_id", "created_at"],  # Default pattern
                index_type="BTREE",
                est_improvement_pct=est_improvement,
                size_bytes=est_index_size,
                seq_scan_count=seq_scans,
                seq_scan_pct=seq_scan_pct,
                level=level,
            )
            recommendations.append(rec)

        return sorted(recommendations, key=lambda r: r.seq_scan_pct, reverse=True)

    def get_table_stats(self, table_name: Optional[str] = None) -> list[TableStats]:
        """Get statistics for user tables.

        Args:
            table_name: Optional specific table name; if None, get all tables

        Returns:
            List of table statistics
        """
        query = text("""
            SELECT
                t.tablename,
                t.n_live_tup,
                t.n_dead_tup,
                ROUND(100 * t.n_dead_tup / NULLIF(t.n_live_tup + t.n_dead_tup, 0), 2) as dead_pct,
                pg_total_relation_size('public.'||t.tablename) as table_size_bytes,
                pg_total_relation_size('public.'||t.tablename) - pg_relation_size('public.'||t.tablename) as idx_size_bytes,
                t.last_vacuum,
                t.last_analyze,
                t.seq_scan,
                t.idx_scan
            FROM pg_stat_user_tables t
            WHERE t.schemaname = 'public'
        """)

        if table_name:
            query = text(query.text + " AND t.tablename = :table_name")
            results = self.db.execute(query, {"table_name": table_name}).fetchall()
        else:
            results = self.db.execute(query).fetchall()

        stats = []
        for row in results:
            stat = TableStats(
                table_name=row[0],
                row_count=row[1] or 0,
                dead_tuples=row[2] or 0,
                dead_pct=row[3] or 0.0,
                table_size_bytes=row[4] or 0,
                index_size_bytes=row[5] or 0,
                last_vacuum=row[6],
                last_analyze=row[7],
                seq_scan_count=row[8] or 0,
                index_scan_count=row[9] or 0,
            )
            stats.append(stat)

        return stats

    def analyze_query(self, query_str: str, explain: bool = True) -> QueryPlan:
        """Analyze query execution plan.

        Args:
            query_str: SQL query to analyze
            explain: If True, use EXPLAIN ANALYZE (shows actual execution)

        Returns:
            Query plan analysis
        """
        plan_query = f"EXPLAIN (FORMAT JSON, ANALYZE {explain}, BUFFERS TRUE) {query_str}"

        try:
            result = self.db.execute(text(plan_query)).fetchone()
            plan_json = json.loads(result[0]) if result else {}

            # Extract statistics from plan
            plan = plan_json[0] if isinstance(plan_json, list) else plan_json

            seq_scans = self._count_node_type(plan, "Seq Scan")
            index_scans = self._count_node_type(plan, "Index Scan")

            plan_obj = QueryPlan(
                query=query_str[:200],  # First 200 chars
                plan_json=plan,
                execution_time_ms=plan.get("Execution Time", 0.0),
                planner_time_ms=plan.get("Planning Time", 0.0),
                rows_returned=plan.get("Actual Rows", 0),
                rows_estimated=plan.get("Plan Rows", 0),
                seq_scans=seq_scans,
                index_scans=index_scans,
            )
            return plan_obj
        except Exception as e:
            logger.error(f"Failed to analyze query: {e}")
            raise

    def recommend_indexes(self) -> list[IndexRecommendation]:
        """Get all index recommendations with estimated impact.

        Returns:
            Prioritized list of index recommendations
        """
        recommendations = self.get_missing_indexes()

        # Filter and prioritize
        critical = [r for r in recommendations if r.level == OptimizationLevel.CRITICAL]
        high = [r for r in recommendations if r.level == OptimizationLevel.HIGH]
        medium = [r for r in recommendations if r.level == OptimizationLevel.MEDIUM]

        # Sort by size (smaller indexes first for faster creation)
        critical.sort(key=lambda r: r.size_bytes)
        high.sort(key=lambda r: r.size_bytes)

        return critical + high + medium

    def get_cache_hit_ratio(self) -> dict[str, float]:
        """Get table and index cache hit ratios.

        Returns:
            Dict with table_hit_ratio and index_hit_ratio (0-1)
        """
        query = text("""
            SELECT
                'table' as type,
                ROUND(100.0 * sum(heap_blks_hit) / (sum(heap_blks_hit) + sum(heap_blks_read)), 2) as ratio
            FROM pg_statio_user_tables
            WHERE sum(heap_blks_read) > 0
            UNION ALL
            SELECT
                'index',
                ROUND(100.0 * sum(idx_blks_hit) / (sum(idx_blks_hit) + sum(idx_blks_read)), 2)
            FROM pg_statio_user_indexes
            WHERE sum(idx_blks_read) > 0;
        """)

        results = self.db.execute(query).fetchall()
        cache_hits = {}
        for row in results:
            cache_hits[f"{row[0]}_hit_ratio"] = (row[1] or 0) / 100.0

        return cache_hits

    def get_optimization_summary(self) -> dict[str, Any]:
        """Get comprehensive optimization summary.

        Returns:
            Dict with recommendations, stats, and baseline metrics
        """
        missing_indexes = self.get_missing_indexes()
        table_stats = self.get_table_stats()
        cache_hits = self.get_cache_hit_ratio()

        # Count issues by severity
        issues = {
            "critical": sum(1 for idx in missing_indexes if idx.level == OptimizationLevel.CRITICAL),
            "high": sum(1 for idx in missing_indexes if idx.level == OptimizationLevel.HIGH),
            "medium": sum(1 for idx in missing_indexes if idx.level == OptimizationLevel.MEDIUM),
        }

        # Count maintenance needs
        vacuum_needed = sum(1 for t in table_stats if t.needs_vacuum)
        analyze_needed = sum(1 for t in table_stats if t.needs_analyze)

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "missing_indexes": {
                "total": len(missing_indexes),
                "critical": issues["critical"],
                "high": issues["high"],
                "medium": issues["medium"],
                "recommendations": [
                    {
                        "table": idx.table_name,
                        "columns": idx.columns,
                        "est_improvement": f"{idx.est_improvement_pct}%",
                        "level": idx.level.value,
                    }
                    for idx in missing_indexes[:10]
                ],
            },
            "table_maintenance": {
                "vacuum_needed": vacuum_needed,
                "analyze_needed": analyze_needed,
                "total_tables": len(table_stats),
                "avg_dead_pct": sum(t.dead_pct for t in table_stats) / len(table_stats) if table_stats else 0,
            },
            "cache_hit_ratio": cache_hits,
            "next_actions": [
                f"Add {issues['critical']} CRITICAL indexes",
                f"Run VACUUM on {vacuum_needed} tables",
                f"Run ANALYZE on {analyze_needed} tables",
                "Monitor cache hit ratio (target: >99%)",
            ],
        }

    # ─────────────────────────────────────────────────────────────────────────────
    # Helper methods
    # ─────────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _count_node_type(plan: dict[str, Any], node_type: str) -> int:
        """Recursively count node types in query plan.

        Args:
            plan: Query plan dictionary
            node_type: Node type to count (e.g., "Seq Scan")

        Returns:
            Count of node type occurrences
        """
        count = 0

        if isinstance(plan, dict):
            if plan.get("Node Type") == node_type:
                count += 1

            # Recursively check Plans array
            if "Plans" in plan and isinstance(plan["Plans"], list):
                for subplan in plan["Plans"]:
                    count += DBOptimizer._count_node_type(subplan, node_type)

        return count
