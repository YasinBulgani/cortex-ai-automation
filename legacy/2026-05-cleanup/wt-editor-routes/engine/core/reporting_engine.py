"""
Advanced Test Reporting Engine
Comprehensive reporting with multiple formats and analytics
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
import sqlite3
from enum import Enum

logger = logging.getLogger(__name__)


class ReportFormat(Enum):
    """Supported report formats"""
    HTML = "html"
    JSON = "json"
    PDF = "pdf"
    MARKDOWN = "markdown"
    CSV = "csv"


class TestStatus(Enum):
    """Test execution statuses"""
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    PENDING = "pending"
    ERROR = "error"


@dataclass
class TestStep:
    """Individual test step result"""
    name: str
    status: str
    duration_ms: float
    timestamp: str
    error_message: Optional[str] = None
    screenshot_path: Optional[str] = None
    logs: List[str] = field(default_factory=list)


@dataclass
class TestCase:
    """Complete test case with steps"""
    test_id: str
    name: str
    status: str
    duration_ms: float
    timestamp: str
    feature: str
    tags: List[str]
    steps: List[TestStep] = field(default_factory=list)
    attachments: List[Dict[str, str]] = field(default_factory=list)
    error_message: Optional[str] = None


@dataclass
class TestRun:
    """Complete test run with all cases"""
    run_id: str
    environment: str
    browser: str
    start_time: str
    end_time: str
    total_tests: int
    passed: int
    failed: int
    skipped: int
    duration_ms: float
    test_cases: List[TestCase] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)

    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage"""
        if self.total_tests == 0:
            return 0.0
        return (self.passed / self.total_tests) * 100

    @property
    def failure_rate(self) -> float:
        """Calculate failure rate percentage"""
        if self.total_tests == 0:
            return 0.0
        return (self.failed / self.total_tests) * 100


class ReportGenerator:
    """Generate comprehensive test reports in multiple formats"""

    def __init__(self, output_dir: str = "./reports"):
        self.output_dir = output_dir
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        logger.info(f"ReportGenerator initialized with output dir: {output_dir}")

    def generate_report(
        self,
        test_run: TestRun,
        formats: List[str] = None,
        include_charts: bool = True
    ) -> Dict[str, str]:
        """
        Generate reports in multiple formats

        Args:
            test_run: Complete test run data
            formats: List of formats (html, json, pdf, markdown, csv)
            include_charts: Whether to include charts in HTML report

        Returns:
            Dictionary with format -> file path mappings
        """
        if formats is None:
            formats = ["html", "json"]

        results = {}

        for fmt in formats:
            try:
                if fmt == "html":
                    path = self._generate_html_report(test_run, include_charts)
                elif fmt == "json":
                    path = self._generate_json_report(test_run)
                elif fmt == "markdown":
                    path = self._generate_markdown_report(test_run)
                elif fmt == "csv":
                    path = self._generate_csv_report(test_run)
                elif fmt == "pdf":
                    path = self._generate_pdf_report(test_run)
                else:
                    logger.warning(f"Unknown format: {fmt}")
                    continue

                results[fmt] = path
                logger.info(f"Generated {fmt} report: {path}")
            except Exception as e:
                logger.error(f"Failed to generate {fmt} report: {e}")

        return results

    def _generate_html_report(
        self,
        test_run: TestRun,
        include_charts: bool = True
    ) -> str:
        """Generate comprehensive HTML report"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"report_{timestamp}.html"
        filepath = os.path.join(self.output_dir, filename)

        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Test Report - {test_run.run_id}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: #f5f5f5;
            color: #333;
        }}

        .container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }}

        header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 8px;
            margin-bottom: 30px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}

        header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
        }}

        header p {{
            font-size: 1.1em;
            opacity: 0.9;
        }}

        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}

        .metric {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            border-left: 4px solid #667eea;
        }}

        .metric.passed {{
            border-left-color: #10b981;
        }}

        .metric.failed {{
            border-left-color: #ef4444;
        }}

        .metric.skipped {{
            border-left-color: #f59e0b;
        }}

        .metric h3 {{
            font-size: 0.9em;
            color: #666;
            margin-bottom: 8px;
            text-transform: uppercase;
        }}

        .metric .value {{
            font-size: 2em;
            font-weight: bold;
            color: #333;
        }}

        .metric .percentage {{
            font-size: 0.9em;
            color: #999;
            margin-top: 8px;
        }}

        .charts {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}

        .chart {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}

        .chart h3 {{
            margin-bottom: 15px;
            color: #333;
        }}

        .test-results {{
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            overflow: hidden;
            margin-bottom: 30px;
        }}

        .test-results h2 {{
            background: #f8f9fa;
            padding: 15px 20px;
            color: #333;
            border-bottom: 1px solid #e9ecef;
        }}

        .test-case {{
            padding: 20px;
            border-bottom: 1px solid #e9ecef;
            transition: background 0.2s;
        }}

        .test-case:hover {{
            background: #f8f9fa;
        }}

        .test-case.passed {{
            border-left: 4px solid #10b981;
        }}

        .test-case.failed {{
            border-left: 4px solid #ef4444;
        }}

        .test-case-header {{
            display: flex;
            justify-content: space-between;
            align-items: start;
            margin-bottom: 10px;
        }}

        .test-case-name {{
            font-weight: 600;
            color: #333;
        }}

        .test-case-status {{
            padding: 4px 12px;
            border-radius: 4px;
            font-size: 0.85em;
            font-weight: 600;
        }}

        .test-case-status.passed {{
            background: #d1f3e0;
            color: #065f46;
        }}

        .test-case-status.failed {{
            background: #fee2e2;
            color: #991b1b;
        }}

        .test-case-status.skipped {{
            background: #fef3c7;
            color: #92400e;
        }}

        .test-case-meta {{
            font-size: 0.9em;
            color: #666;
            margin-bottom: 10px;
        }}

        .test-steps {{
            margin-top: 15px;
            background: #f8f9fa;
            border-radius: 4px;
            padding: 10px;
        }}

        .test-step {{
            padding: 8px;
            font-size: 0.9em;
            color: #666;
            border-left: 2px solid #ccc;
            margin: 5px 0;
            padding-left: 12px;
        }}

        .test-step.passed {{
            border-left-color: #10b981;
        }}

        .test-step.failed {{
            border-left-color: #ef4444;
            color: #991b1b;
        }}

        .error-message {{
            margin-top: 10px;
            padding: 10px;
            background: #fee2e2;
            border-left: 3px solid #ef4444;
            color: #991b1b;
            border-radius: 4px;
            font-size: 0.9em;
            font-family: 'Courier New', monospace;
        }}

        footer {{
            text-align: center;
            color: #999;
            font-size: 0.9em;
            padding: 20px;
            border-top: 1px solid #e9ecef;
            margin-top: 30px;
        }}

        .progress-bar {{
            width: 100%;
            height: 24px;
            background: #e9ecef;
            border-radius: 4px;
            overflow: hidden;
            margin: 10px 0;
        }}

        .progress-fill {{
            height: 100%;
            background: linear-gradient(90deg, #10b981 0%, #059669 100%);
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 0.85em;
            font-weight: 600;
        }}
    </style>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@3.9.1/dist/chart.min.js"></script>
</head>
<body>
    <div class="container">
        <header>
            <h1>Test Execution Report</h1>
            <p>Run ID: {test_run.run_id}</p>
            <p>Environment: {test_run.environment} | Browser: {test_run.browser}</p>
            <p>Executed: {test_run.start_time}</p>
        </header>

        <div class="summary">
            <div class="metric passed">
                <h3>Passed</h3>
                <div class="value">{test_run.passed}</div>
                <div class="percentage">{(test_run.passed/max(1,test_run.total_tests)*100):.1f}% of total</div>
            </div>

            <div class="metric failed">
                <h3>Failed</h3>
                <div class="value">{test_run.failed}</div>
                <div class="percentage">{(test_run.failed/max(1,test_run.total_tests)*100):.1f}% of total</div>
            </div>

            <div class="metric skipped">
                <h3>Skipped</h3>
                <div class="value">{test_run.skipped}</div>
                <div class="percentage">{(test_run.skipped/max(1,test_run.total_tests)*100):.1f}% of total</div>
            </div>

            <div class="metric">
                <h3>Total Tests</h3>
                <div class="value">{test_run.total_tests}</div>
                <div class="percentage">Duration: {test_run.duration_ms/1000:.2f}s</div>
            </div>
        </div>

        <div class="progress-bar">
            <div class="progress-fill" style="width: {test_run.success_rate:.1f}%">
                {test_run.success_rate:.1f}% Success
            </div>
        </div>

        {self._generate_charts_html() if include_charts else ""}

        <div class="test-results">
            <h2>Test Cases ({len(test_run.test_cases)})</h2>
            {self._generate_test_cases_html(test_run.test_cases)}
        </div>

        <footer>
            <p>Generated on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
            <p>TestwrightAI Test Automation Platform</p>
        </footer>
    </div>

    <script>
        {self._generate_chart_scripts(test_run)}
    </script>
</body>
</html>
        """

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html)

        return filepath

    def _generate_test_cases_html(self, test_cases: List[TestCase]) -> str:
        """Generate HTML for test cases"""
        html = ""
        for test_case in test_cases:
            steps_html = ""
            if test_case.steps:
                for step in test_case.steps:
                    steps_html += f"""
                    <div class="test-step {step.status}">
                        {step.name} ({step.duration_ms:.0f}ms)
                    </div>
                    """

            error_html = ""
            if test_case.error_message:
                error_html = f'<div class="error-message">{test_case.error_message}</div>'

            html += f"""
            <div class="test-case {test_case.status}">
                <div class="test-case-header">
                    <div class="test-case-name">{test_case.name}</div>
                    <div class="test-case-status {test_case.status}">{test_case.status.upper()}</div>
                </div>
                <div class="test-case-meta">
                    Feature: {test_case.feature} | Duration: {test_case.duration_ms:.0f}ms | Tags: {', '.join(test_case.tags)}
                </div>
                {f'<div class="test-steps">{steps_html}</div>' if steps_html else ''}
                {error_html}
            </div>
            """

        return html

    def _generate_charts_html(self) -> str:
        """Generate HTML for charts"""
        return """
        <div class="charts">
            <div class="chart">
                <h3>Test Results Distribution</h3>
                <canvas id="resultsChart"></canvas>
            </div>
            <div class="chart">
                <h3>Test Duration</h3>
                <canvas id="durationChart"></canvas>
            </div>
        </div>
        """

    def _generate_chart_scripts(self, test_run: TestRun) -> str:
        """Generate JavaScript for charts"""
        return f"""
        // Results chart
        const resultsCtx = document.getElementById('resultsChart').getContext('2d');
        new Chart(resultsCtx, {{
            type: 'doughnut',
            data: {{
                labels: ['Passed', 'Failed', 'Skipped'],
                datasets: [{{
                    data: [{test_run.passed}, {test_run.failed}, {test_run.skipped}],
                    backgroundColor: ['#10b981', '#ef4444', '#f59e0b'],
                    borderColor: '#fff',
                    borderWidth: 2
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: true,
                plugins: {{
                    legend: {{ position: 'bottom' }}
                }}
            }}
        }});

        // Duration chart
        const durationCtx = document.getElementById('durationChart').getContext('2d');
        const durations = {json.dumps([tc.duration_ms for tc in test_run.test_cases[:20]])};
        const labels = {json.dumps([tc.name[:30] for tc in test_run.test_cases[:20]])};

        new Chart(durationCtx, {{
            type: 'bar',
            data: {{
                labels: labels,
                datasets: [{{
                    label: 'Duration (ms)',
                    data: durations,
                    backgroundColor: '#667eea',
                    borderRadius: 4
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: true,
                indexAxis: 'y',
                plugins: {{
                    legend: {{ display: false }}
                }}
            }}
        }});
        """

    def _generate_json_report(self, test_run: TestRun) -> str:
        """Generate JSON report"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"report_{timestamp}.json"
        filepath = os.path.join(self.output_dir, filename)

        data = {
            "metadata": {
                "run_id": test_run.run_id,
                "environment": test_run.environment,
                "browser": test_run.browser,
                "start_time": test_run.start_time,
                "end_time": test_run.end_time,
                "generated_at": datetime.now().isoformat(),
            },
            "summary": {
                "total_tests": test_run.total_tests,
                "passed": test_run.passed,
                "failed": test_run.failed,
                "skipped": test_run.skipped,
                "success_rate": f"{test_run.success_rate:.2f}%",
                "failure_rate": f"{test_run.failure_rate:.2f}%",
                "duration_seconds": test_run.duration_ms / 1000,
            },
            "test_cases": [asdict(tc) for tc in test_run.test_cases],
            "metrics": test_run.metrics,
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, default=str)

        return filepath

    def _generate_markdown_report(self, test_run: TestRun) -> str:
        """Generate Markdown report"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"report_{timestamp}.md"
        filepath = os.path.join(self.output_dir, filename)

        md = f"""# Test Execution Report

**Run ID**: {test_run.run_id}
**Environment**: {test_run.environment}
**Browser**: {test_run.browser}
**Executed**: {test_run.start_time}

## Summary

| Metric | Value |
|--------|-------|
| Total Tests | {test_run.total_tests} |
| Passed | {test_run.passed} ({test_run.success_rate:.1f}%) |
| Failed | {test_run.failed} ({test_run.failure_rate:.1f}%) |
| Skipped | {test_run.skipped} |
| Duration | {test_run.duration_ms/1000:.2f}s |

## Test Cases

"""
        for test_case in test_run.test_cases:
            status_emoji = "✅" if test_case.status == "passed" else "❌" if test_case.status == "failed" else "⏭️"
            md += f"\n### {status_emoji} {test_case.name}\n\n"
            md += f"- **Status**: {test_case.status.upper()}\n"
            md += f"- **Feature**: {test_case.feature}\n"
            md += f"- **Duration**: {test_case.duration_ms:.0f}ms\n"
            md += f"- **Tags**: {', '.join(test_case.tags)}\n"

            if test_case.steps:
                md += "\n**Steps**:\n"
                for step in test_case.steps:
                    step_emoji = "✅" if step.status == "passed" else "❌"
                    md += f"- {step_emoji} {step.name} ({step.duration_ms:.0f}ms)\n"

            if test_case.error_message:
                md += f"\n```\n{test_case.error_message}\n```\n"

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(md)

        return filepath

    def _generate_csv_report(self, test_run: TestRun) -> str:
        """Generate CSV report"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"report_{timestamp}.csv"
        filepath = os.path.join(self.output_dir, filename)

        import csv

        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)

            # Header
            writer.writerow([
                "Test ID", "Test Name", "Feature", "Status", "Duration (ms)",
                "Timestamp", "Tags", "Error Message"
            ])

            # Data rows
            for test_case in test_run.test_cases:
                writer.writerow([
                    test_case.test_id,
                    test_case.name,
                    test_case.feature,
                    test_case.status,
                    f"{test_case.duration_ms:.0f}",
                    test_case.timestamp,
                    ";".join(test_case.tags),
                    test_case.error_message or ""
                ])

        return filepath

    def _generate_pdf_report(self, test_run: TestRun) -> str:
        """Generate PDF report (requires reportlab)"""
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.lib import colors
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"report_{timestamp}.pdf"
            filepath = os.path.join(self.output_dir, filename)

            doc = SimpleDocTemplate(filepath, pagesize=letter)
            story = []
            styles = getSampleStyleSheet()

            # Title
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=24,
                textColor=colors.HexColor('#667eea'),
                spaceAfter=30,
            )
            story.append(Paragraph("Test Execution Report", title_style))
            story.append(Spacer(1, 12))

            # Summary table
            summary_data = [
                ["Metric", "Value"],
                ["Run ID", test_run.run_id],
                ["Environment", test_run.environment],
                ["Browser", test_run.browser],
                ["Total Tests", str(test_run.total_tests)],
                ["Passed", f"{test_run.passed} ({test_run.success_rate:.1f}%)"],
                ["Failed", f"{test_run.failed} ({test_run.failure_rate:.1f}%)"],
                ["Skipped", str(test_run.skipped)],
                ["Duration", f"{test_run.duration_ms/1000:.2f}s"],
            ]

            summary_table = Table(summary_data, colWidths=[200, 200])
            summary_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#667eea')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ]))

            story.append(summary_table)
            story.append(PageBreak())

            doc.build(story)
            return filepath

        except ImportError:
            logger.warning("reportlab not installed, skipping PDF generation")
            return None


# Singleton instance
_report_generator: Optional[ReportGenerator] = None


def get_report_generator(output_dir: str = "./reports") -> ReportGenerator:
    """Get or create report generator instance"""
    global _report_generator
    if _report_generator is None:
        _report_generator = ReportGenerator(output_dir)
    return _report_generator


def reset_report_generator() -> None:
    """Reset report generator instance"""
    global _report_generator
    _report_generator = None
