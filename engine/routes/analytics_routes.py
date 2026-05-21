"""
Reporting & Analytics REST API Routes
"""

from flask import Blueprint, request, jsonify
import logging
import os
from typing import Dict, Any

from core.reporting_engine import (
    get_report_generator, TestRun, TestCase, TestStep, ReportFormat
)
from core.analytics_engine import get_analytics_engine

logger = logging.getLogger(__name__)

reporting_bp = Blueprint('reporting', __name__, url_prefix='/api/reporting')


@reporting_bp.route('/health', methods=['GET'])
def health():
    """Health check for reporting service"""
    return jsonify({
        'status': 'healthy',
        'service': 'reporting',
        'version': '1.0.0'
    })


@reporting_bp.route('/generate-report', methods=['POST'])
def generate_report():
    """
    Generate comprehensive test report

    Request JSON:
    {
        "test_run": {
            "run_id": "test-run-123",
            "environment": "staging",
            "browser": "chromium",
            "start_time": "2024-01-01T10:00:00",
            "end_time": "2024-01-01T10:15:00",
            "total_tests": 50,
            "passed": 45,
            "failed": 5,
            "skipped": 0,
            "duration_ms": 900000,
            "test_cases": [...]
        },
        "formats": ["html", "json"],
        "include_charts": true
    }
    """
    try:
        data = request.get_json()

        test_run_data = data.get('test_run')
        formats = data.get('formats', ['html', 'json'])
        include_charts = data.get('include_charts', True)

        if not test_run_data:
            return jsonify({'error': 'test_run object required'}), 400

        # Reconstruct test run object
        test_cases = []
        for tc_data in test_run_data.get('test_cases', []):
            steps = [
                TestStep(
                    name=s.get('name'),
                    status=s.get('status'),
                    duration_ms=s.get('duration_ms', 0),
                    timestamp=s.get('timestamp'),
                    error_message=s.get('error_message'),
                    screenshot_path=s.get('screenshot_path'),
                    logs=s.get('logs', [])
                )
                for s in tc_data.get('steps', [])
            ]

            test_case = TestCase(
                test_id=tc_data.get('test_id'),
                name=tc_data.get('name'),
                status=tc_data.get('status'),
                duration_ms=tc_data.get('duration_ms', 0),
                timestamp=tc_data.get('timestamp'),
                feature=tc_data.get('feature'),
                tags=tc_data.get('tags', []),
                steps=steps,
                attachments=tc_data.get('attachments', []),
                error_message=tc_data.get('error_message')
            )
            test_cases.append(test_case)

        test_run = TestRun(
            run_id=test_run_data.get('run_id'),
            environment=test_run_data.get('environment'),
            browser=test_run_data.get('browser'),
            start_time=test_run_data.get('start_time'),
            end_time=test_run_data.get('end_time'),
            total_tests=test_run_data.get('total_tests', 0),
            passed=test_run_data.get('passed', 0),
            failed=test_run_data.get('failed', 0),
            skipped=test_run_data.get('skipped', 0),
            duration_ms=test_run_data.get('duration_ms', 0),
            test_cases=test_cases,
            metrics=test_run_data.get('metrics', {})
        )

        # Generate reports
        generator = get_report_generator()
        report_paths = generator.generate_report(
            test_run,
            formats=formats,
            include_charts=include_charts
        )

        return jsonify({
            'success': True,
            'run_id': test_run.run_id,
            'reports': report_paths,
            'summary': {
                'total_tests': test_run.total_tests,
                'passed': test_run.passed,
                'failed': test_run.failed,
                'skipped': test_run.skipped,
                'success_rate': f"{test_run.success_rate:.2f}%",
                'duration_seconds': test_run.duration_ms / 1000
            }
        })

    except Exception as e:
        logger.error(f'Report generation failed: {e}', exc_info=True)
        return jsonify({
            'error': str(e),
            'success': False
        }), 500


@reporting_bp.route('/record-run', methods=['POST'])
def record_test_run():
    """
    Record test run metrics for analytics

    Request JSON:
    {
        "run_id": "test-run-123",
        "environment": "staging",
        "browser": "chromium",
        "total_tests": 50,
        "passed": 45,
        "failed": 5,
        "skipped": 0,
        "duration_ms": 900000
    }
    """
    try:
        data = request.get_json()

        run_id = data.get('run_id')
        environment = data.get('environment')
        browser = data.get('browser')
        total_tests = data.get('total_tests', 0)
        passed = data.get('passed', 0)
        failed = data.get('failed', 0)
        skipped = data.get('skipped', 0)
        duration_ms = data.get('duration_ms', 0)

        if not run_id:
            return jsonify({'error': 'run_id required'}), 400

        analytics = get_analytics_engine()
        analytics.record_test_run(
            run_id=run_id,
            environment=environment,
            browser=browser,
            total_tests=total_tests,
            passed=passed,
            failed=failed,
            skipped=skipped,
            duration_ms=duration_ms
        )

        success_rate = (passed / max(1, total_tests)) * 100

        return jsonify({
            'success': True,
            'run_id': run_id,
            'success_rate': f"{success_rate:.2f}%",
            'message': 'Test run recorded successfully'
        })

    except Exception as e:
        logger.error(f'Failed to record test run: {e}', exc_info=True)
        return jsonify({
            'error': str(e),
            'success': False
        }), 500


@reporting_bp.route('/record-failure', methods=['POST'])
def record_failed_test():
    """
    Record a failed test

    Request JSON:
    {
        "test_name": "test_home_page_loads",
        "run_id": "test-run-123",
        "error_message": "Element not found",
        "duration_ms": 5000
    }
    """
    try:
        data = request.get_json()

        test_name = data.get('test_name')
        run_id = data.get('run_id')
        error_message = data.get('error_message')
        duration_ms = data.get('duration_ms', 0)

        if not test_name or not run_id:
            return jsonify({'error': 'test_name and run_id required'}), 400

        analytics = get_analytics_engine()
        analytics.record_failed_test(
            test_name=test_name,
            run_id=run_id,
            error_message=error_message,
            duration_ms=duration_ms
        )

        return jsonify({
            'success': True,
            'test_name': test_name,
            'message': 'Failed test recorded'
        })

    except Exception as e:
        logger.error(f'Failed to record failure: {e}', exc_info=True)
        return jsonify({
            'error': str(e),
            'success': False
        }), 500


@reporting_bp.route('/analytics/trends', methods=['GET'])
def get_trends():
    """
    Get metric trends

    Query parameters:
    - metric_name: Optional specific metric
    - hours: Lookback period (default: 24)
    """
    try:
        metric_name = request.args.get('metric_name')
        hours = int(request.args.get('hours', 24))

        analytics = get_analytics_engine()
        trends = analytics.analyze_trends(metric_name, hours)

        trends_data = {
            metric: {
                'current_value': trend.current_value,
                'previous_value': trend.previous_value,
                'direction': trend.direction,
                'change_percentage': f"{trend.change_percentage:.2f}%",
                'data_points': [
                    {
                        'timestamp': p.timestamp,
                        'value': p.value,
                        'run_id': p.run_id
                    }
                    for p in trend.data_points
                ]
            }
            for metric, trend in trends.items()
        }

        return jsonify({
            'success': True,
            'lookback_hours': hours,
            'trends': trends_data
        })

    except Exception as e:
        logger.error(f'Failed to get trends: {e}', exc_info=True)
        return jsonify({
            'error': str(e),
            'success': False
        }), 500


@reporting_bp.route('/analytics/risk-assessment', methods=['GET'])
def get_risk_assessment():
    """
    Get risk assessment for test suite

    Query parameters:
    - hours: Lookback period (default: 24)
    """
    try:
        hours = int(request.args.get('hours', 24))

        analytics = get_analytics_engine()
        risk = analytics.assess_risk(hours)

        return jsonify({
            'success': True,
            'risk_assessment': {
                'level': risk.level,
                'score': risk.score,
                'failing_tests': risk.failing_tests,
                'unstable_tests': risk.unstable_tests,
                'regression_risk': f"{risk.regression_risk:.2f}%",
                'recommendations': risk.recommendations
            }
        })

    except Exception as e:
        logger.error(f'Failed to assess risk: {e}', exc_info=True)
        return jsonify({
            'error': str(e),
            'success': False
        }), 500


@reporting_bp.route('/analytics/predictions', methods=['GET'])
def get_predictions():
    """
    Get failure predictions

    Query parameters:
    - days: Lookback period for analysis (default: 7)
    """
    try:
        days = int(request.args.get('days', 7))

        analytics = get_analytics_engine()
        predictions = analytics.predict_failures(days)

        return jsonify({
            'success': True,
            'lookback_days': days,
            'predictions': predictions
        })

    except Exception as e:
        logger.error(f'Failed to generate predictions: {e}', exc_info=True)
        return jsonify({
            'error': str(e),
            'success': False
        }), 500


@reporting_bp.route('/analytics/performance', methods=['GET'])
def get_performance_trends():
    """
    Get performance trends

    Query parameters:
    - hours: Lookback period (default: 24)
    """
    try:
        hours = int(request.args.get('hours', 24))

        analytics = get_analytics_engine()
        performance = analytics.get_performance_trends(hours)

        return jsonify({
            'success': True,
            'lookback_hours': hours,
            'performance': performance
        })

    except Exception as e:
        logger.error(f'Failed to get performance trends: {e}', exc_info=True)
        return jsonify({
            'error': str(e),
            'success': False
        }), 500


@reporting_bp.route('/analytics/report', methods=['GET'])
def get_analytics_report():
    """Get comprehensive analytics report"""
    try:
        analytics = get_analytics_engine()
        report = analytics.generate_analytics_report()

        export_format = request.args.get('export', 'json')
        filepath = analytics.export_analytics(report, export_format)

        return jsonify({
            'success': True,
            'report_id': report.run_id,
            'timestamp': report.timestamp,
            'export_path': filepath,
            'risk_level': report.risk_assessment.level,
            'trends_summary': {
                metric: {
                    'direction': trend.direction,
                    'change': f"{trend.change_percentage:.2f}%"
                }
                for metric, trend in report.trends.items()
            },
            'recommendations': report.risk_assessment.recommendations
        })

    except Exception as e:
        logger.error(f'Failed to generate analytics report: {e}', exc_info=True)
        return jsonify({
            'error': str(e),
            'success': False
        }), 500


# Error handlers

@reporting_bp.errorhandler(400)
def bad_request(error):
    """Handle bad requests"""
    return jsonify({
        'error': 'Bad request',
        'message': str(error),
        'success': False
    }), 400


@reporting_bp.errorhandler(500)
def internal_error(error):
    """Handle internal errors"""
    logger.error(f'Internal error: {error}', exc_info=True)
    return jsonify({
        'error': 'Internal server error',
        'message': str(error),
        'success': False
    }), 500


def register_reporting_routes(app):
    """Register reporting routes with Flask app"""
    app.register_blueprint(reporting_bp)
    logger.info('Reporting routes registered')
