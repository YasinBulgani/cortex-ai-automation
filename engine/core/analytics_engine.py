"""
Test Analytics & Trend Analysis Engine
Predictive analytics and historical trend tracking
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
import sqlite3
from enum import Enum
import statistics

logger = logging.getLogger(__name__)


class TrendDirection(Enum):
    """Trend direction indicators"""
    IMPROVING = "improving"
    DEGRADING = "degrading"
    STABLE = "stable"


class RiskLevel(Enum):
    """Risk assessment levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class MetricPoint:
    """Single metric data point"""
    timestamp: str
    value: float
    run_id: str


@dataclass
class Trend:
    """Metric trend analysis"""
    metric_name: str
    current_value: float
    previous_value: Optional[float]
    direction: str
    change_percentage: float
    data_points: List[MetricPoint] = field(default_factory=list)


@dataclass
class RiskAssessment:
    """Risk assessment for test suite"""
    level: str
    score: float  # 0-100
    failing_tests: List[str]
    unstable_tests: List[str]
    regression_risk: float
    recommendations: List[str]


@dataclass
class TestAnalytics:
    """Complete analytics data"""
    run_id: str
    timestamp: str
    trends: Dict[str, Trend]
    risk_assessment: RiskAssessment
    metrics: Dict[str, Any]
    predictions: Dict[str, Any]


class AnalyticsEngine:
    """Advanced analytics and trend analysis"""

    def __init__(self, db_path: str = "./data/analytics.db"):
        self.db_path = db_path
        self._init_database()
        logger.info(f"AnalyticsEngine initialized with db: {db_path}")

    def _init_database(self) -> None:
        """Initialize analytics database"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Test runs table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS test_runs (
                run_id TEXT PRIMARY KEY,
                timestamp TEXT,
                environment TEXT,
                browser TEXT,
                total_tests INTEGER,
                passed INTEGER,
                failed INTEGER,
                skipped INTEGER,
                duration_ms REAL,
                success_rate REAL
            )
            """)

            # Metrics history
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS metrics_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT,
                metric_name TEXT,
                value REAL,
                timestamp TEXT,
                FOREIGN KEY (run_id) REFERENCES test_runs(run_id)
            )
            """)

            # Failed tests tracking
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS failed_tests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                test_name TEXT,
                run_id TEXT,
                timestamp TEXT,
                error_message TEXT,
                duration_ms REAL,
                FOREIGN KEY (run_id) REFERENCES test_runs(run_id)
            )
            """)

            # Test flakiness
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS test_flakiness (
                test_name TEXT PRIMARY KEY,
                failure_count INTEGER,
                total_runs INTEGER,
                flakiness_rate REAL,
                last_seen TEXT
            )
            """)

            conn.commit()

    def record_test_run(
        self,
        run_id: str,
        environment: str,
        browser: str,
        total_tests: int,
        passed: int,
        failed: int,
        skipped: int,
        duration_ms: float
    ) -> None:
        """Record test run metrics"""
        success_rate = (passed / total_tests * 100) if total_tests > 0 else 0

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT OR REPLACE INTO test_runs
            (run_id, timestamp, environment, browser, total_tests, passed, failed, skipped, duration_ms, success_rate)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                run_id,
                datetime.now().isoformat(),
                environment,
                browser,
                total_tests,
                passed,
                failed,
                skipped,
                duration_ms,
                success_rate
            ))

            # Record individual metrics
            self._record_metric(run_id, "success_rate", success_rate)
            self._record_metric(run_id, "failure_count", failed)
            self._record_metric(run_id, "test_duration", duration_ms)

            conn.commit()

        logger.info(f"Recorded test run: {run_id} (Success rate: {success_rate:.1f}%)")

    def _record_metric(self, run_id: str, metric_name: str, value: float) -> None:
        """Record individual metric"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO metrics_history (run_id, metric_name, value, timestamp)
            VALUES (?, ?, ?, ?)
            """, (run_id, metric_name, value, datetime.now().isoformat()))
            conn.commit()

    def record_failed_test(
        self,
        test_name: str,
        run_id: str,
        error_message: str,
        duration_ms: float
    ) -> None:
        """Record failed test"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO failed_tests (test_name, run_id, timestamp, error_message, duration_ms)
            VALUES (?, ?, ?, ?, ?)
            """, (test_name, run_id, datetime.now().isoformat(), error_message, duration_ms))
            conn.commit()

        # Update flakiness
        self._update_test_flakiness(test_name)

    def _update_test_flakiness(self, test_name: str) -> None:
        """Update test flakiness metrics"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Count failures and total runs
            cursor.execute("""
            SELECT COUNT(*) FROM failed_tests WHERE test_name = ?
            """, (test_name,))
            failure_count = cursor.fetchone()[0]

            cursor.execute("""
            SELECT COUNT(DISTINCT run_id) FROM (
                SELECT run_id FROM failed_tests WHERE test_name = ?
                UNION
                SELECT run_id FROM test_runs
            ) t
            """, (test_name,))
            total_runs = cursor.fetchone()[0]

            flakiness_rate = (failure_count / max(1, total_runs)) * 100

            cursor.execute("""
            INSERT OR REPLACE INTO test_flakiness
            (test_name, failure_count, total_runs, flakiness_rate, last_seen)
            VALUES (?, ?, ?, ?, ?)
            """, (test_name, failure_count, total_runs, flakiness_rate, datetime.now().isoformat()))

            conn.commit()

    def analyze_trends(self, metric_name: str = None, hours: int = 24) -> Dict[str, Trend]:
        """Analyze metric trends"""
        cutoff_time = datetime.now() - timedelta(hours=hours)

        trends = {}

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            if metric_name:
                metrics = [metric_name]
            else:
                cursor.execute("""
                SELECT DISTINCT metric_name FROM metrics_history
                WHERE timestamp > ? ORDER BY timestamp DESC
                """, (cutoff_time.isoformat(),))
                metrics = [row[0] for row in cursor.fetchall()]

            for metric in metrics:
                cursor.execute("""
                SELECT value, run_id, timestamp FROM metrics_history
                WHERE metric_name = ? AND timestamp > ?
                ORDER BY timestamp ASC
                """, (metric, cutoff_time.isoformat()))

                rows = cursor.fetchall()
                if not rows:
                    continue

                data_points = [
                    MetricPoint(
                        timestamp=row[2],
                        value=row[0],
                        run_id=row[1]
                    )
                    for row in rows
                ]

                values = [row[0] for row in rows]
                current_value = values[-1]
                previous_value = values[-2] if len(values) > 1 else None

                # Determine trend direction
                if previous_value is None:
                    direction = TrendDirection.STABLE.value
                    change_percentage = 0.0
                else:
                    change = current_value - previous_value
                    change_percentage = (change / max(1, previous_value)) * 100

                    if change_percentage > 5:
                        direction = TrendDirection.DEGRADING.value
                    elif change_percentage < -5:
                        direction = TrendDirection.IMPROVING.value
                    else:
                        direction = TrendDirection.STABLE.value

                trend = Trend(
                    metric_name=metric,
                    current_value=current_value,
                    previous_value=previous_value,
                    direction=direction,
                    change_percentage=change_percentage,
                    data_points=data_points
                )

                trends[metric] = trend

        return trends

    def assess_risk(self, hours: int = 24) -> RiskAssessment:
        """Assess test suite risk"""
        cutoff_time = datetime.now() - timedelta(hours=hours)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Get recent failed tests
            cursor.execute("""
            SELECT DISTINCT test_name FROM failed_tests
            WHERE timestamp > ?
            """, (cutoff_time.isoformat(),))
            failing_tests = [row[0] for row in cursor.fetchall()]

            # Get flaky tests (>30% failure rate)
            cursor.execute("""
            SELECT test_name FROM test_flakiness
            WHERE flakiness_rate > 30
            """)
            unstable_tests = [row[0] for row in cursor.fetchall()]

            # Calculate regression risk
            cursor.execute("""
            SELECT AVG(success_rate) FROM test_runs
            WHERE timestamp > ?
            """, (cutoff_time.isoformat(),))
            avg_success_rate = cursor.fetchone()[0] or 100.0

            # Calculate overall risk score
            risk_score = 100 - avg_success_rate  # 0-100 scale

            # Determine risk level
            if risk_score >= 80:
                risk_level = RiskLevel.CRITICAL.value
            elif risk_score >= 50:
                risk_level = RiskLevel.HIGH.value
            elif risk_score >= 20:
                risk_level = RiskLevel.MEDIUM.value
            else:
                risk_level = RiskLevel.LOW.value

            # Generate recommendations
            recommendations = self._generate_risk_recommendations(
                risk_level,
                failing_tests,
                unstable_tests,
                avg_success_rate
            )

        return RiskAssessment(
            level=risk_level,
            score=risk_score,
            failing_tests=failing_tests[:10],  # Top 10
            unstable_tests=unstable_tests[:10],
            regression_risk=max(0, 100 - avg_success_rate),
            recommendations=recommendations
        )

    def _generate_risk_recommendations(
        self,
        risk_level: str,
        failing_tests: List[str],
        unstable_tests: List[str],
        success_rate: float
    ) -> List[str]:
        """Generate risk mitigation recommendations"""
        recommendations = []

        if risk_level == RiskLevel.CRITICAL.value:
            recommendations.append("🚨 CRITICAL: Immediate investigation required")
            recommendations.append("Block deployment until success rate improves")

        if failing_tests:
            recommendations.append(f"Fix {len(failing_tests)} failing tests")
            if len(failing_tests) <= 5:
                recommendations.append(f"Priority tests: {', '.join(failing_tests[:3])}")

        if unstable_tests:
            recommendations.append(f"Stabilize {len(unstable_tests)} flaky tests")
            recommendations.append("Review test isolation and environment dependencies")

        if success_rate < 80:
            recommendations.append("Investigate root causes of failures")
            recommendations.append("Consider adding more diagnostic logging")

        if not recommendations:
            recommendations.append("✅ Test suite is healthy, continue monitoring")

        return recommendations

    def predict_failures(self, lookback_days: int = 7) -> Dict[str, Any]:
        """Predict likely failures based on patterns"""
        cutoff_time = datetime.now() - timedelta(days=lookback_days)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Get test failure frequency
            cursor.execute("""
            SELECT test_name, COUNT(*) as failure_count
            FROM failed_tests
            WHERE timestamp > ?
            GROUP BY test_name
            ORDER BY failure_count DESC
            """, (cutoff_time.isoformat(),))

            high_risk_tests = cursor.fetchall()

            # Predict failure probability
            cursor.execute("""
            SELECT AVG(success_rate) FROM test_runs
            WHERE timestamp > ?
            """, (cutoff_time.isoformat(),))

            avg_success = cursor.fetchone()[0] or 100.0
            base_failure_rate = 100 - avg_success

            predictions = {
                "probable_failures": [
                    {
                        "test_name": test_name,
                        "failure_history": failure_count,
                        "predicted_probability": min(100, base_failure_rate * (1 + (failure_count / 10)))
                    }
                    for test_name, failure_count in high_risk_tests[:5]
                ],
                "base_failure_rate": base_failure_rate,
                "confidence": "high" if len(high_risk_tests) > 5 else "medium" if len(high_risk_tests) > 0 else "low",
            }

            return predictions

    def get_performance_trends(self, hours: int = 24) -> Dict[str, Any]:
        """Analyze performance trends"""
        trends = self.analyze_trends("test_duration", hours)
        duration_trend = trends.get("test_duration")

        if duration_trend:
            avg_duration = statistics.mean([p.value for p in duration_trend.data_points])
            max_duration = max([p.value for p in duration_trend.data_points])
            min_duration = min([p.value for p in duration_trend.data_points])

            return {
                "average_duration_ms": avg_duration,
                "max_duration_ms": max_duration,
                "min_duration_ms": min_duration,
                "trend_direction": duration_trend.direction,
                "trend_change_percentage": duration_trend.change_percentage,
                "data_points": [
                    {"timestamp": p.timestamp, "value": p.value}
                    for p in duration_trend.data_points
                ]
            }

        return {}

    def generate_analytics_report(self) -> TestAnalytics:
        """Generate comprehensive analytics report"""
        run_id = f"analytics_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        trends = self.analyze_trends()
        risk = self.assess_risk()
        predictions = self.predict_failures()
        performance = self.get_performance_trends()

        metrics = {
            "performance": performance,
            "risk_assessment": {
                "level": risk.level,
                "score": risk.score,
                "regression_risk": risk.regression_risk,
            },
            "trending_metrics": {
                name: {
                    "current": trend.current_value,
                    "direction": trend.direction,
                    "change_percentage": trend.change_percentage
                }
                for name, trend in trends.items()
            }
        }

        return TestAnalytics(
            run_id=run_id,
            timestamp=datetime.now().isoformat(),
            trends=trends,
            risk_assessment=risk,
            metrics=metrics,
            predictions=predictions
        )

    def export_analytics(self, analytics: TestAnalytics, format: str = "json") -> str:
        """Export analytics to file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"analytics_{timestamp}.{format}"

        output_dir = "./reports"
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        filepath = os.path.join(output_dir, filename)

        if format == "json":
            data = {
                "run_id": analytics.run_id,
                "timestamp": analytics.timestamp,
                "trends": {
                    name: {
                        "current_value": trend.current_value,
                        "previous_value": trend.previous_value,
                        "direction": trend.direction,
                        "change_percentage": trend.change_percentage,
                    }
                    for name, trend in analytics.trends.items()
                },
                "risk_assessment": {
                    "level": analytics.risk_assessment.level,
                    "score": analytics.risk_assessment.score,
                    "failing_tests": analytics.risk_assessment.failing_tests,
                    "unstable_tests": analytics.risk_assessment.unstable_tests,
                    "regression_risk": analytics.risk_assessment.regression_risk,
                    "recommendations": analytics.risk_assessment.recommendations,
                },
                "metrics": analytics.metrics,
                "predictions": analytics.predictions,
            }

            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2, default=str)

        return filepath


# Singleton instance
_analytics_engine: Optional[AnalyticsEngine] = None


def get_analytics_engine(db_path: str = "./data/analytics.db") -> AnalyticsEngine:
    """Get or create analytics engine instance"""
    global _analytics_engine
    if _analytics_engine is None:
        _analytics_engine = AnalyticsEngine(db_path)
    return _analytics_engine


def reset_analytics_engine() -> None:
    """Reset analytics engine instance"""
    global _analytics_engine
    _analytics_engine = None
