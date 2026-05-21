"""
Visual AI API Routes
REST endpoints for AI-powered visual testing
"""

from flask import Blueprint, request, jsonify
import logging
import os
from typing import Dict, Any

from core.python.visual_ai import get_visual_ai_analyzer, SmartBaselineManager

logger = logging.getLogger(__name__)

visual_ai_bp = Blueprint('visual_ai', __name__, url_prefix='/api/visual-ai')


@visual_ai_bp.route('/health', methods=['GET'])
def health():
    """Health check for visual AI service"""
    return jsonify({
        'status': 'healthy',
        'service': 'visual_ai',
        'version': '1.0.0'
    })


@visual_ai_bp.route('/analyze', methods=['POST'])
def analyze_visual_difference():
    """
    Analyze visual difference between current and baseline images

    Request JSON:
    {
        "current_image": "/path/to/current.png",
        "baseline_image": "/path/to/baseline.png" (optional),
        "baseline_name": "screenshot_name"
    }
    """
    try:
        data = request.get_json()

        current_image = data.get('current_image')
        baseline_name = data.get('baseline_name', 'unknown')
        baseline_image = data.get('baseline_image')

        if not current_image:
            return jsonify({'error': 'current_image path required'}), 400

        # Use baseline_image if provided, otherwise try to find it
        if not baseline_image:
            baselines_dir = os.path.join(os.getcwd(), 'data', 'visual-baselines')
            baseline_image = os.path.join(baselines_dir, f'{baseline_name}.png')

        # Perform analysis
        analyzer = get_visual_ai_analyzer()
        analysis = analyzer.analyze_visual_difference(
            current_image,
            baseline_image,
            baseline_name
        )

        # Convert to JSON-serializable format
        anomalies_data = [
            {
                'type': a.type,
                'location': a.location,
                'severity': a.severity,
                'confidence': a.confidence,
                'description': a.description
            }
            for a in analysis.anomalies
        ]

        return jsonify({
            'success': True,
            'baseline_name': baseline_name,
            'similarity': float(analysis.similarity),
            'anomalies': anomalies_data,
            'has_anomalies': analysis.has_anomalies,
            'recommendations': analysis.recommendations,
            'should_update_baseline': analysis.should_update_baseline
        })

    except Exception as e:
        logger.error(f'Visual analysis failed: {e}', exc_info=True)
        return jsonify({
            'error': str(e),
            'success': False
        }), 500


@visual_ai_bp.route('/smart-update', methods=['POST'])
def smart_baseline_update():
    """
    Intelligently decide whether to update baseline

    Request JSON:
    {
        "baseline_name": "screenshot_name",
        "current_image": "/path/to/current.png",
        "baseline_image": "/path/to/baseline.png" (optional),
        "force": false
    }
    """
    try:
        data = request.get_json()

        baseline_name = data.get('baseline_name')
        current_image = data.get('current_image')
        baseline_image = data.get('baseline_image')
        force = data.get('force', False)

        if not baseline_name or not current_image:
            return jsonify({'error': 'baseline_name and current_image required'}), 400

        # Find baseline image
        if not baseline_image:
            baselines_dir = os.path.join(os.getcwd(), 'data', 'visual-baselines')
            baseline_image = os.path.join(baselines_dir, f'{baseline_name}.png')

        # Perform smart update analysis
        baselines_dir = os.path.dirname(baseline_image)
        manager = SmartBaselineManager(baselines_dir)
        result = manager.smart_update_baseline(
            baseline_name,
            current_image,
            baseline_image,
            force
        )

        return jsonify({
            'success': True,
            **result
        })

    except Exception as e:
        logger.error(f'Smart baseline update failed: {e}', exc_info=True)
        return jsonify({
            'error': str(e),
            'success': False
        }), 500


@visual_ai_bp.route('/report', methods=['POST'])
def generate_report():
    """
    Generate visual analysis report

    Request JSON:
    {
        "analysis": {...},  # Analysis object from /analyze
        "baseline_name": "screenshot_name"
    }
    """
    try:
        data = request.get_json()

        analysis = data.get('analysis')
        baseline_name = data.get('baseline_name', 'unknown')

        if not analysis:
            return jsonify({'error': 'analysis object required'}), 400

        analyzer = get_visual_ai_analyzer()

        # Create report object from analysis data
        class AnalysisReport:
            def __init__(self, data):
                self.similarity = data.get('similarity', 0)
                self.anomalies = [
                    type('Anomaly', (), {
                        'type': a['type'],
                        'severity': a['severity'],
                        'description': a['description']
                    })()
                    for a in data.get('anomalies', [])
                ]
                self.recommendations = data.get('recommendations', [])

        analysis_obj = AnalysisReport(analysis)
        report = analyzer.generate_analysis_report(analysis_obj, baseline_name)

        return jsonify({
            'success': True,
            'baseline_name': baseline_name,
            'report': report
        })

    except Exception as e:
        logger.error(f'Report generation failed: {e}', exc_info=True)
        return jsonify({
            'error': str(e),
            'success': False
        }), 500


@visual_ai_bp.route('/baseline-status', methods=['GET'])
def get_baseline_status():
    """
    Get status of a baseline

    Query parameters:
    - baseline_name: Name of the baseline
    - baselines_dir: Optional directory (default: data/visual-baselines)
    """
    try:
        baseline_name = request.args.get('baseline_name')
        baselines_dir = request.args.get('baselines_dir')

        if not baseline_name:
            return jsonify({'error': 'baseline_name required'}), 400

        if not baselines_dir:
            baselines_dir = os.path.join(os.getcwd(), 'data', 'visual-baselines')

        manager = SmartBaselineManager(baselines_dir)
        status = manager.get_baseline_status(baseline_name)

        return jsonify({
            'success': True,
            'baseline_name': baseline_name,
            **status
        })

    except Exception as e:
        logger.error(f'Failed to get baseline status: {e}', exc_info=True)
        return jsonify({
            'error': str(e),
            'success': False
        }), 500


@visual_ai_bp.route('/statistics', methods=['GET'])
def get_statistics():
    """Get visual AI service statistics"""
    try:
        analyzer = get_visual_ai_analyzer()

        return jsonify({
            'success': True,
            'service': 'visual_ai',
            'analyzer': {
                'anomaly_detection_threshold': analyzer.anomaly_detection_threshold,
                'color_shift_threshold': analyzer.color_shift_threshold,
                'layout_change_threshold': analyzer.layout_change_threshold
            }
        })

    except Exception as e:
        logger.error(f'Failed to get statistics: {e}', exc_info=True)
        return jsonify({
            'error': str(e),
            'success': False
        }), 500


@visual_ai_bp.route('/config', methods=['GET'])
def get_config():
    """Get visual AI configuration"""
    return jsonify({
        'success': True,
        'config': {
            'service': 'visual_ai',
            'features': [
                'perceptual_similarity',
                'anomaly_detection',
                'color_shift_detection',
                'layout_change_detection',
                'element_visibility_detection',
                'smart_baseline_management',
                'analysis_reporting'
            ],
            'thresholds': {
                'anomaly_detection': 0.80,
                'color_shift': 30,
                'layout_change': 0.15
            }
        }
    })


# Error handlers

@visual_ai_bp.errorhandler(400)
def bad_request(error):
    """Handle bad requests"""
    return jsonify({
        'error': 'Bad request',
        'message': str(error),
        'success': False
    }), 400


@visual_ai_bp.errorhandler(500)
def internal_error(error):
    """Handle internal errors"""
    logger.error(f'Internal error: {error}', exc_info=True)
    return jsonify({
        'error': 'Internal server error',
        'message': str(error),
        'success': False
    }), 500


def register_visual_ai_routes(app):
    """Register visual AI routes with Flask app"""
    app.register_blueprint(visual_ai_bp)
    logger.info('Visual AI routes registered')
