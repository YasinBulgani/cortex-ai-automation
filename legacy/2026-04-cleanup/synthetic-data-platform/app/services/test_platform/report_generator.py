"""
ReportGenerator — Dashboard / JSON / HTML Raporlama

Test çalışma sonuçlarından özet rapor ve dashboard verisi üretir.
"""
from __future__ import annotations
import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class TrendPoint:
    date: str
    pass_rate: float
    total: int


@dataclass
class TestReport:
    report_id: str
    suite_name: str
    generated_at: str
    summary: Dict[str, Any]
    trend_data: List[TrendPoint]
    failed_tests: List[Dict[str, Any]]
    top_failures: List[str]
    recommendations: List[str]
    html_content: Optional[str] = None
    json_content: Optional[str] = None


class ReportGenerator:
    """Test çalışma sonuçlarından çoklu formatta rapor üretir."""

    def generate(self, execution_summary, suite_name: str = "Test Suite") -> TestReport:
        """
        ExecutionSummary'den rapor üretir.

        Args:
            execution_summary: ExecutionEngine.run_suite() çıktısı
            suite_name: Rapor başlığı

        Returns:
            TestReport
        """
        report_id = str(uuid.uuid4())[:8]
        generated_at = time.strftime("%Y-%m-%dT%H:%M:%S")

        # Özet istatistikler
        total = getattr(execution_summary, "total", 0)
        passed = getattr(execution_summary, "passed", 0)
        failed = getattr(execution_summary, "failed", 0)
        skipped = getattr(execution_summary, "skipped", 0)
        pass_rate = getattr(execution_summary, "pass_rate", 0.0)
        duration = getattr(execution_summary, "total_duration_seconds", 0.0)

        summary = {
            "total": total,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "error": getattr(execution_summary, "error", 0),
            "pass_rate": pass_rate,
            "pass_rate_pct": f"{pass_rate * 100:.1f}%",
            "duration_seconds": duration,
            "status": "PASSED" if failed == 0 else "FAILED",
        }

        # Başarısız testler
        results = getattr(execution_summary, "results", [])
        failed_tests = [
            {
                "id": r.test_case_id,
                "status": r.status,
                "error": r.error_message or "",
                "duration": r.duration_seconds,
            }
            for r in results
            if str(getattr(r, "status", "")).lower() in {"failed", "error"}
        ]

        top_failures = list({r["error"][:80] for r in failed_tests if r["error"]})[:5]
        trend = self._mock_trend(pass_rate)
        recommendations = self._build_recommendations(summary, failed_tests)

        html = self._render_html(suite_name, summary, failed_tests, generated_at)
        json_content = json.dumps({"report_id": report_id, "summary": summary, "failed": failed_tests}, ensure_ascii=False, indent=2)

        return TestReport(
            report_id=report_id,
            suite_name=suite_name,
            generated_at=generated_at,
            summary=summary,
            trend_data=trend,
            failed_tests=failed_tests,
            top_failures=top_failures,
            recommendations=recommendations,
            html_content=html,
            json_content=json_content,
        )

    def _mock_trend(self, current_pass_rate: float) -> List[TrendPoint]:
        """Son 7 günlük örnek trend verisi üretir."""
        import random, datetime
        points = []
        for i in range(7, 0, -1):
            d = (datetime.date.today() - datetime.timedelta(days=i)).isoformat()
            rate = min(1.0, max(0.0, current_pass_rate + random.uniform(-0.1, 0.1)))
            points.append(TrendPoint(date=d, pass_rate=round(rate, 3), total=random.randint(20, 50)))
        return points

    def _build_recommendations(self, summary: dict, failed_tests: list) -> List[str]:
        recs = []
        if summary["pass_rate"] < 0.8:
            recs.append("Geçme oranı %80 altında — acil inceleme gerekiyor.")
        if summary["skipped"] > summary["total"] * 0.2:
            recs.append("Atlanan test oranı yüksek — bağımlılıkları kontrol edin.")
        if len(failed_tests) > 5:
            recs.append("Çok sayıda başarısız test var — ortak kök nedeni araştırın.")
        if not recs:
            recs.append("Test sonuçları iyi görünüyor. Düzenli çalışmaya devam edin.")
        return recs

    def _render_html(self, name: str, summary: dict, failed: list, ts: str) -> str:
        status_color = "#28a745" if summary["status"] == "PASSED" else "#dc3545"
        failed_rows = "".join(
            f"<tr><td>{r['id']}</td><td style='color:red'>{r['status']}</td><td>{r['error'][:60]}</td></tr>"
            for r in failed[:10]
        ) or "<tr><td colspan='3'>Başarısız test yok</td></tr>"

        return f"""<!DOCTYPE html>
<html lang="tr"><head><meta charset="UTF-8"><title>{name} — Test Raporu</title>
<style>body{{font-family:sans-serif;margin:20px}}table{{border-collapse:collapse;width:100%}}
th,td{{border:1px solid #ddd;padding:8px;text-align:left}}th{{background:#f2f2f2}}</style></head>
<body>
<h1>{name}</h1>
<p>Oluşturulma: {ts}</p>
<h2 style="color:{status_color}">{summary['status']} — Geçme Oranı: {summary['pass_rate_pct']}</h2>
<table><tr><th>Toplam</th><th>Geçti</th><th>Başarısız</th><th>Atlandı</th><th>Süre</th></tr>
<tr><td>{summary['total']}</td><td>{summary['passed']}</td><td>{summary['failed']}</td>
<td>{summary['skipped']}</td><td>{summary['duration_seconds']}s</td></tr></table>
<h3>Başarısız Testler</h3>
<table><tr><th>Test ID</th><th>Durum</th><th>Hata</th></tr>{failed_rows}</table>
</body></html>"""
