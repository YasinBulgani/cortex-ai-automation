"""
jira_routes.py — Jira Entegrasyonu API
Prefix: /api/jira/

Endpoints:
  POST /api/jira/config          - Jira bağlantı ayarlarını kaydet
  GET  /api/jira/config          - Mevcut ayarları getir
  POST /api/jira/bugs/<id>/push  - Bug'ı Jira'ya aktar
  GET  /api/jira/projects        - Jira projelerini listele
  POST /api/jira/testcases/<id>/link - Test case'i Jira issue'ya bağla
"""

import os
import json
from pathlib import Path
from flask import Blueprint, request, jsonify, session

jira_bp = Blueprint('jira', __name__)

JIRA_CONFIG_PATH = Path("/tmp/jira_config.json")


def load_jira_config() -> dict:
    if JIRA_CONFIG_PATH.exists():
        try:
            return json.loads(JIRA_CONFIG_PATH.read_text())
        except Exception:
            pass
    return {}


def save_jira_config(config: dict):
    JIRA_CONFIG_PATH.write_text(json.dumps(config, indent=2))


def get_jira_client():
    """Jira API istemcisi döndürür. jira kütüphanesi yoksa None."""
    config = load_jira_config()
    if not config.get("url") or not config.get("email") or not config.get("token"):
        return None, "Jira yapılandırması eksik"
    try:
        from jira import JIRA
        client = JIRA(
            server=config["url"],
            basic_auth=(config["email"], config["token"])
        )
        return client, None
    except ImportError:
        return None, "jira kütüphanesi yüklü değil (pip install jira)"
    except Exception as e:
        return None, str(e)


# ─────────────────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────────────────

@jira_bp.route("/api/jira/config", methods=["GET"])
def jira_get_config():
    config = load_jira_config()
    # Token'ı maskele
    if config.get("token"):
        config["token"] = "***" + config["token"][-4:]
    return jsonify(config)


@jira_bp.route("/api/jira/config", methods=["POST"])
def jira_save_config():
    data = request.json or {}
    url = data.get("url", "").strip().rstrip("/")
    email = data.get("email", "").strip()
    token = data.get("token", "").strip()
    project_key = data.get("project_key", "").strip()

    if not url or not email or not token:
        return jsonify({"error": "url, email ve token zorunludur"}), 400

    save_jira_config({
        "url": url,
        "email": email,
        "token": token,
        "project_key": project_key
    })
    return jsonify({"ok": True})


@jira_bp.route("/api/jira/test-connection", methods=["POST"])
def jira_test_connection():
    client, err = get_jira_client()
    if err:
        return jsonify({"ok": False, "error": err}), 400
    try:
        me = client.myself()
        return jsonify({"ok": True, "user": me.get("displayName", me.get("name"))})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400


# ─────────────────────────────────────────────────────────────────────────────
# JIRA PROJECTS
# ─────────────────────────────────────────────────────────────────────────────

@jira_bp.route("/api/jira/projects", methods=["GET"])
def jira_list_projects():
    client, err = get_jira_client()
    if err:
        return jsonify({"error": err}), 400
    try:
        projects = client.projects()
        return jsonify([{"key": p.key, "name": p.name} for p in projects])
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─────────────────────────────────────────────────────────────────────────────
# BUG → JIRA TICKET
# ─────────────────────────────────────────────────────────────────────────────

@jira_bp.route("/api/jira/bugs/<int:bug_id>/push", methods=["POST"])
def jira_push_bug(bug_id):
    from core.db import get_bugs, update_bug_jira_key

    client, err = get_jira_client()
    if err:
        return jsonify({"error": err}), 400

    config = load_jira_config()
    project_key = (request.json or {}).get("project_key") or config.get("project_key")
    if not project_key:
        return jsonify({"error": "Jira proje anahtarı gerekli"}), 400

    bugs = get_bugs()
    bug = next((b for b in bugs if b["id"] == bug_id), None)
    if not bug:
        return jsonify({"error": "Bug bulunamadı"}), 404

    if bug.get("jira_key"):
        return jsonify({"error": f"Bu bug zaten Jira'ya aktarıldı: {bug['jira_key']}"}), 400

    severity_priority_map = {
        "Critical": "Highest",
        "High": "High",
        "Medium": "Medium",
        "Low": "Low"
    }
    priority = severity_priority_map.get(bug.get("severity", "Medium"), "Medium")

    try:
        issue = client.create_issue(fields={
            "project": {"key": project_key},
            "summary": bug["title"],
            "description": bug.get("description", ""),
            "issuetype": {"name": "Bug"},
            "priority": {"name": priority}
        })
        update_bug_jira_key(bug_id, issue.key)
        return jsonify({"ok": True, "jira_key": issue.key, "url": f"{config['url']}/browse/{issue.key}"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─────────────────────────────────────────────────────────────────────────────
# TEST CASE → JIRA ISSUE BAĞLANTISI
# ─────────────────────────────────────────────────────────────────────────────

@jira_bp.route("/api/jira/testcases/<int:tc_id>/link", methods=["POST"])
def jira_link_testcase(tc_id):
    """Test case'i mevcut bir Jira issue'ya bağlar (comment olarak)."""
    data = request.json or {}
    jira_key = data.get("jira_key", "").strip()
    if not jira_key:
        return jsonify({"error": "Jira issue key gerekli"}), 400

    client, err = get_jira_client()
    if err:
        return jsonify({"error": err}), 400

    from core.db import get_test_case
    tc = get_test_case(tc_id)
    if not tc:
        return jsonify({"error": "Test case bulunamadı"}), 404

    steps_text = "\n".join(
        [f"{i+1}. {s['action']} → {s['expected']}" for i, s in enumerate(tc.get("steps", []))]
    )
    comment = (
        f"*Test Case Bağlandı:* {tc['title']}\n"
        f"*Öncelik:* {tc.get('priority', 'P2')}\n\n"
        f"*Adımlar:*\n{steps_text}"
    )

    try:
        client.add_comment(jira_key, comment)
        return jsonify({"ok": True, "jira_key": jira_key})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─────────────────────────────────────────────────────────────────────────────
# TEST RUN SONUÇLARINI JIRA'YA SYNC
# ─────────────────────────────────────────────────────────────────────────────

@jira_bp.route("/api/jira/runs/<int:run_id>/sync", methods=["POST"])
def jira_sync_run(run_id):
    """Test run sonuçlarını özet olarak Jira issue'ya yorum ekler."""
    data = request.json or {}
    jira_key = data.get("jira_key", "").strip()
    if not jira_key:
        return jsonify({"error": "Jira issue key gerekli"}), 400

    client, err = get_jira_client()
    if err:
        return jsonify({"error": err}), 400

    from core.db import get_manual_test_run_results
    results = get_manual_test_run_results(run_id)

    status_counts = {}
    for r in results:
        s = r.get("status", "Not Run")
        status_counts[s] = status_counts.get(s, 0) + 1

    summary_lines = [f"*Test Run #{run_id} Sonuçları:*"]
    for status, count in status_counts.items():
        summary_lines.append(f"- {status}: {count}")

    failed = [r for r in results if r.get("status") == "Fail"]
    if failed:
        summary_lines.append("\n*Başarısız Test Case'ler:*")
        for r in failed[:10]:
            note = f" — {r['notes']}" if r.get("notes") else ""
            summary_lines.append(f"- {r['title']}{note}")

    try:
        client.add_comment(jira_key, "\n".join(summary_lines))
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
