"""
magic_test_routes.py — API Routes for Magical Test Case Tool
Provides endpoints for AI-powered test case generation, monkey testing, and strategy analysis.
"""
from flask import Blueprint, request, jsonify, Response
import logging
from datetime import datetime
import json

from core.test_case_manager import TestCaseManager
from core.ai_engine import AIEngine
from core.page_inspector import PageInspector
from core.browser import BrowserEngine
from playwright.sync_api import sync_playwright

logger = logging.getLogger(__name__)

magic_test_bp = Blueprint('magic_test', __name__, url_prefix='/api/magic')
test_case_manager = TestCaseManager()

@magic_test_bp.route('/generate-test-cases', methods=['POST'])
def generate_test_cases():
    """
    Generate test cases with AI explanations from a URL.
    
    Request body:
    {
        "url": "https://example.com/login",
        "goals": "Test login functionality with valid and invalid credentials",
        "count": 5
    }
    
    Response:
    {
        "status": "success",
        "test_cases": [
            {
                "test_id": "test_abc123",
                "title": "Valid Login Test",
                "steps": [...],
                "explanations": [...],
                "risk_level": "low"
            }
        ]
    }
    """
    try:
        data = request.get_json()
        url = data.get('url')
        goals = data.get('goals', 'General testing')
        count = data.get('count', 5)
        
        if not url:
            return jsonify({'error': 'URL is required'}), 400
        
        # Playwright ile sayfayı aç ve analiz et
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()

            try:
                page.goto(url, wait_until='domcontentloaded', timeout=30000)
                page.wait_for_timeout(2000)  # JS yüklenmesini bekle

                inspector = PageInspector(page)
                page_summary = inspector.get_summary_text()
                page_type = inspector.detect_page_type()
                form_fields = inspector.get_form_fields_with_validation()

                # Sayfa tipini hedeflere ekle
                enriched_goals = f"{goals}\n[Sayfa Tipi: {page_type}]\n[Form Alanları: {len(form_fields)} alan bulundu]"

                # AI ile test senaryoları üret
                ai_engine = AIEngine()
                test_cases_data = ai_engine.generate_test_cases_with_explanations(
                    url=url,
                    page_context=page_summary,
                    goals=enriched_goals,
                    count=count
                )

                # Test senaryolarını veritabanına kaydet
                generated_cases = []
                for tc in test_cases_data:
                    test_id = test_case_manager.create_test_case(
                        url=url,
                        title=tc.get('title', 'Test Senaryosu'),
                        steps=tc.get('steps', []),
                        explanations=tc.get('explanations', []),
                        description=tc.get('description'),
                        risk_level=tc.get('risk_level', 'medium'),
                        tags=tc.get('tags', [page_type])
                    )
                    generated_cases.append({
                        'test_id': test_id,
                        'title': tc.get('title', 'Test Senaryosu'),
                        'risk_level': tc.get('risk_level', 'medium'),
                        'step_count': len(tc.get('steps', []))
                    })

                return jsonify({
                    'status': 'success',
                    'page_type': page_type,
                    'test_cases': generated_cases,
                    'total': len(generated_cases),
                    'timestamp': datetime.utcnow().isoformat()
                }), 201

            finally:
                context.close()
                browser.close()
    
    except Exception as e:
        logger.error(f"Error generating test cases: {str(e)}")
        return jsonify({'error': str(e)}), 500

@magic_test_bp.route('/monkey-test', methods=['POST'])
def monkey_test():
    """
    Run monkey testing (exploratory testing) on a URL.
    
    Request body:
    {
        "url": "https://example.com",
        "mode": "smart",
        "iterations": 50,
        "timeout": 30
    }
    
    Modes: "random" (baseline), "smart" (AI-ranked), "hybrid"
    Streams progress via SSE.
    """
    def generate_stream():
        try:
            data = request.get_json()
            url = data.get('url')
            mode = data.get('mode', 'smart')
            iterations = data.get('iterations', 50)
            timeout = data.get('timeout', 30)
            
            if not url:
                yield f"data: {json.dumps({'error': 'URL is required'})}\n\n"
                return
            
            browser_engine = BrowserEngine()
            page = browser_engine.get_page(url)
            
            try:
                page.goto(url, wait_until='networkidle')
                
                # Monkey testing engine
                from core.monkey_test_engine import MonkeyTestEngine
                monkey_engine = MonkeyTestEngine()
                
                # Run monkey test with streaming
                for progress in monkey_engine.run_monkey_test_streamed(
                    page=page,
                    url=url,
                    mode=mode,
                    iterations=iterations,
                    timeout=timeout
                ):
                    yield f"data: {json.dumps(progress)}\n\n"
                
            finally:
                browser_engine.close_page(page)
        
        except Exception as e:
            logger.error(f"Error in monkey testing: {str(e)}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    return Response(generate_stream(), mimetype='text/event-stream')

@magic_test_bp.route('/analyze-test-strategy', methods=['POST'])
def analyze_test_strategy():
    """
    Analyze a page and recommend optimal testing strategy.
    
    Request body:
    {
        "url": "https://example.com/checkout"
    }
    
    Response:
    {
        "page_type": "checkout",
        "complexity_score": 7.5,
        "critical_elements": [...],
        "recommendations": [...],
        "best_practices": [...]
    }
    """
    try:
        data = request.get_json()
        url = data.get('url')
        
        if not url:
            return jsonify({'error': 'URL is required'}), 400
        
        # Playwright ile sayfayı analiz et
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()

            try:
                page.goto(url, wait_until='domcontentloaded', timeout=30000)
                page.wait_for_timeout(2000)

                inspector = PageInspector(page)
                page_summary = inspector.get_summary_text()
                page_type = inspector.detect_page_type()
                ranked_elements = inspector.get_interactive_elements_ranked()
                form_fields = inspector.get_form_fields_with_validation()

                # Sayfa bağlamını zenginleştir
                enriched_context = (
                    f"{page_summary}\n"
                    f"[Tespit Edilen Sayfa Tipi: {page_type}]\n"
                    f"[Önemli Elementler: {len(ranked_elements)} adet]\n"
                    f"[Form Alanları: {len(form_fields)} adet, "
                    f"Zorunlu: {sum(1 for f in form_fields if f.get('required'))}]"
                )

                # AI ile strateji analizi yap
                ai_engine = AIEngine()
                analysis = ai_engine.analyze_page_for_test_strategy(
                    url=url,
                    page_context=enriched_context
                )
                # page_type'ı detector'dan güncelle
                analysis['page_type'] = page_type
                analysis['detected_elements_count'] = len(ranked_elements)
                analysis['form_fields_count'] = len(form_fields)

                # Analizi veritabanına kaydet
                analysis_id = test_case_manager.record_strategy_analysis(
                    url=url,
                    page_type=analysis.get('page_type', page_type),
                    complexity_score=analysis.get('complexity_score', 5.0),
                    critical_elements=analysis.get('critical_elements', []),
                    recommendations=analysis.get('recommendations', []),
                    best_practices=analysis.get('best_practices', [])
                )

                return jsonify({
                    'status': 'success',
                    'analysis_id': analysis_id,
                    'analysis': analysis,
                    'timestamp': datetime.utcnow().isoformat()
                }), 200

            finally:
                context.close()
                browser.close()
    
    except Exception as e:
        logger.error(f"Error analyzing test strategy: {str(e)}")
        return jsonify({'error': str(e)}), 500

@magic_test_bp.route('/test-cases', methods=['GET'])
def list_test_cases():
    """
    List generated test cases with optional filtering.
    
    Query parameters:
    - url: Filter by URL
    - limit: Maximum results (default 50)
    """
    try:
        url = request.args.get('url')
        limit = request.args.get('limit', 50, type=int)
        
        test_cases = test_case_manager.list_test_cases(url=url, limit=limit)
        
        return jsonify({
            'status': 'success',
            'test_cases': test_cases,
            'total': len(test_cases)
        }), 200
    
    except Exception as e:
        logger.error(f"Error listing test cases: {str(e)}")
        return jsonify({'error': str(e)}), 500

@magic_test_bp.route('/test-cases/<test_id>', methods=['GET'])
def get_test_case(test_id):
    """
    Get detailed test case information including execution history.
    
    Returns:
    {
        "test_case": {...},
        "execution_history": [...]
    }
    """
    try:
        test_case = test_case_manager.get_test_case(test_id)
        
        if not test_case:
            return jsonify({'error': 'Test case not found'}), 404
        
        execution_history = test_case_manager.get_execution_history(test_id)
        
        return jsonify({
            'status': 'success',
            'test_case': test_case,
            'execution_history': execution_history,
            'total_executions': len(execution_history)
        }), 200
    
    except Exception as e:
        logger.error(f"Error getting test case: {str(e)}")
        return jsonify({'error': str(e)}), 500

@magic_test_bp.route('/test-cases/<test_id>/export', methods=['GET'])
def export_test_case(test_id):
    """
    Export test case to Gherkin format.
    
    Query parameters:
    - format: Export format (gherkin, json, default: gherkin)
    """
    try:
        export_format = request.args.get('format', 'gherkin')
        test_case = test_case_manager.get_test_case(test_id)
        
        if not test_case:
            return jsonify({'error': 'Test case not found'}), 404
        
        if export_format == 'gherkin':
            gherkin_content = test_case_manager.export_test_case_to_gherkin(test_id)
            return gherkin_content, 200, {'Content-Type': 'text/plain'}
        
        elif export_format == 'json':
            return jsonify({
                'status': 'success',
                'test_case': test_case
            }), 200
        
        else:
            return jsonify({'error': 'Invalid format'}), 400
    
    except Exception as e:
        logger.error(f"Error exporting test case: {str(e)}")
        return jsonify({'error': str(e)}), 500

def register_magic_test_routes(app):
    """Register magic test routes with Flask app."""
    app.register_blueprint(magic_test_bp)
    logger.info("Magic test routes registered successfully")
