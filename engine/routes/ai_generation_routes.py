"""
AI Test/BDD üretim endpoint'leri.

POST /api/ai/generate-test   — Doğal dil → test kodu
POST /api/ai/generate-bdd    — Doğal dil → Gherkin feature
"""
from flask import Blueprint, request, jsonify

ai_gen_bp = Blueprint("ai_generation", __name__, url_prefix="/api/ai")


def _get_gateway():
    from services import get_llm_gateway
    return get_llm_gateway()


def _check_feature(name: str):
    from services import is_feature_enabled
    if not is_feature_enabled(name):
        return jsonify({"error": f"'{name}' özelliği ai_config.yaml'da devre dışı"}), 503
    return None


@ai_gen_bp.route("/generate-test", methods=["POST"])
def generate_test():
    """Doğal dil gereksinimden test kodu üretir."""
    blocked = _check_feature("test_generation")
    if blocked:
        return blocked
    gw = _get_gateway()
    if not gw.available:
        return jsonify({"error": "LLM API anahtarı yapılandırılmamış"}), 503

    data = request.get_json(silent=True) or {}
    requirement = data.get("requirement", "").strip()
    if not requirement:
        return jsonify({"error": "requirement alanı zorunlu"}), 400

    try:
        from services.ai_test_generator import AITestGenerator
        generator = AITestGenerator(gateway=gw, model=data.get("model"))
        result = generator.generate_from_requirement(
            requirement=requirement,
            framework=data.get("framework", "pytest-bdd"),
            page_objects=data.get("page_objects"),
        )
        return jsonify({
            "framework": result.framework,
            "code": result.code,
            "file_path": result.file_path,
            "validation_passed": result.validation_passed,
            "validation_errors": result.validation_errors,
        })
    except Exception as exc:
        return jsonify({"error": f"Test üretimi başarısız: {exc}"}), 500


@ai_gen_bp.route("/generate-bdd", methods=["POST"])
def generate_bdd():
    """Doğal dil gereksinimden BDD Gherkin senaryosu üretir."""
    blocked = _check_feature("bdd_generation")
    if blocked:
        return blocked
    gw = _get_gateway()
    if not gw.available:
        return jsonify({"error": "LLM API anahtarı yapılandırılmamış"}), 503

    data = request.get_json(silent=True) or {}
    requirement = data.get("requirement", "").strip()
    if not requirement:
        return jsonify({"error": "requirement alanı zorunlu"}), 400

    try:
        from services.bdd_generator import BDDGenerator
        generator = BDDGenerator(gateway=gw, model=data.get("model"))
        result = generator.generate(requirement)
        return jsonify({
            "feature_content": result.feature_content,
            "step_definitions": result.step_definitions,
            "matched_existing_steps": result.matched_existing_steps,
            "new_steps_needed": result.new_steps_needed,
        })
    except Exception as exc:
        return jsonify({"error": f"BDD üretimi başarısız: {exc}"}), 500
