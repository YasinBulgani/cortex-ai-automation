
from flask import Blueprint, request, jsonify
from core.db import (
    create_manual_test, delete_manual_test, add_manual_step, delete_manual_step,
    update_manual_step_status, update_manual_test_status, get_manual_tests
)

manual_bp = Blueprint('manual', __name__)

@manual_bp.route("/api/manual-tests", methods=["GET"])
def get_manual_tests_api():
    return jsonify(get_manual_tests())

@manual_bp.route("/api/manual-tests", methods=["POST"])
def post_manual_test():
    title = (request.json or {}).get("title")
    if not title: return jsonify({"error": "Başlık gerekli"}), 400
    test_id = create_manual_test(title)
    return jsonify({"ok": True, "id": test_id})

@manual_bp.route("/api/manual-tests/<int:test_id>", methods=["DELETE"])
def del_manual_test(test_id):
    delete_manual_test(test_id)
    return jsonify({"ok": True})

@manual_bp.route("/api/manual-tests/<int:test_id>", methods=["PUT"])
def put_manual_test_status(test_id):
    status = (request.json or {}).get("status")
    update_manual_test_status(test_id, status)
    return jsonify({"ok": True})

@manual_bp.route("/api/manual-tests/<int:test_id>/steps", methods=["POST"])
def post_manual_step(test_id):
    data = request.json or {}
    action = data.get("action")
    expected = data.get("expected")
    if not action or not expected: return jsonify({"error": "Aksiyon ve beklenen sonuç zorunludur"}), 400
    add_manual_step(test_id, action, expected)
    return jsonify({"ok": True})

@manual_bp.route("/api/manual-test-steps/<int:step_id>", methods=["DELETE"])
def del_manual_step(step_id):
    delete_manual_step(step_id)
    return jsonify({"ok": True})

@manual_bp.route("/api/manual-test-steps/<int:step_id>", methods=["PUT"])
def put_manual_step_status(step_id):
    status = (request.json or {}).get("status")
    update_manual_step_status(step_id, status)
    return jsonify({"ok": True})

@manual_bp.route("/api/generate-manual-from-doc", methods=["POST"])
def generate_manual_from_doc():
    if 'file' not in request.files:
        return jsonify({"error": "Dosya yüklenmedi"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "Dosya adı boş"}), 400
    
    content = ""
    if file.filename.lower().endswith(('.pdf', '.docx')):
        return jsonify({"error": "PDF veya DOCX desteği (.txt kullanın)"}), 400
    else:
        try:
            content = file.stream.read().decode('utf-8', errors='ignore')
        except Exception as e:
            return jsonify({"error": str(e)}), 500
            
    from core.ai_engine import get_ai_engine
    engine = get_ai_engine()
    try:
        tests = engine.extract_manual_tests_from_text(content)
        count = 0
        for t in tests:
            test_id = create_manual_test(t.get('title', 'İsimsiz Test'))
            for s in t.get('steps', []):
                add_manual_step(test_id, s.get('action', '-'), s.get('expected', '-'))
            count += 1
        return jsonify({"ok": True, "count": count})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
