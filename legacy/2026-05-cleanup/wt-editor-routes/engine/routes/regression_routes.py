
from flask import Blueprint, request, jsonify
from core.db import (
    create_regression_set, delete_regression_set, 
    add_feature_to_set, remove_feature_from_set, get_regression_sets
)

regression_bp = Blueprint('regression', __name__)

@regression_bp.route("/api/regression-sets", methods=["GET"])
def list_regression_sets():
    return jsonify(get_regression_sets())

@regression_bp.route("/api/regression-sets", methods=["POST"])
def new_regression_set():
    name = (request.json or {}).get("name")
    if not name: return jsonify({"error": "İsim gerekli"}), 400
    if create_regression_set(name): return jsonify({"ok": True})
    return jsonify({"error": "Aynı isimli set zaten var"}), 400

@regression_bp.route("/api/regression-sets/<int:set_id>", methods=["DELETE"])
def remove_regression_set(set_id):
    delete_regression_set(set_id)
    return jsonify({"ok": True})

@regression_bp.route("/api/regression-sets/<int:set_id>/features", methods=["POST"])
def add_feature_to_reg_set(set_id):
    fname = (request.json or {}).get("feature_name")
    if not fname: return jsonify({"error": "Feature adı gerekli"}), 400
    add_feature_to_set(set_id, fname)
    return jsonify({"ok": True})

@regression_bp.route("/api/regression-sets/<int:set_id>/features/<feature_name>", methods=["DELETE"])
def remove_feature_from_reg_set(set_id, feature_name):
    remove_feature_from_set(set_id, feature_name)
    return jsonify({"ok": True})
