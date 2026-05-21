#!/usr/bin/env python3
"""Test Executor Simulator (port 5002).

UYARI — BU SERVİS GERÇEK TEST ÇALIŞTIRMAZ.
=========================================

Bu küçük Flask uygulaması eski bir demo kalıntısıdır ve gerçek Playwright /
pytest koşumu yapmaz; her isteğe deterministik sabit bir "başarılı" sonuç
döndürür. Üretim test koşumu için `engine/app.py` içindeki
`/api/run` ve `/api/nexus/run` endpoint'lerini kullanın
(`engine/routes/runner_routes.py`).

Bu dosya şu amaçlarla korunmuştur:
  * UI tarafındaki eski bağımlılıkların kırılmaması
  * Offline / demo ortamlarda hızlı sağlık kontrolü

Yanıtlar artık `simulated: true` bayrağı taşır; böylece çağıran taraf bu
sonucun gerçek bir çalıştırma olmadığını algılayabilir. Yeni kodlardan bu
servis çağrılmamalıdır; ilgili takvimde kaldırılacaktır.

Kaldırma takvimi: Faz 5 refactor (2026-Q3) — bkz. `legacy/README.md`.
"""
from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timezone
from typing import Any

from flask import Flask, jsonify, request
from flask_cors import CORS

logger = logging.getLogger("test_executor_server")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

app = Flask(__name__)
CORS(app)

# Bellek-içi sonuç listesi (demo amaçlı; restart'ta kaybolur).
_results: list[dict[str, Any]] = []

_DEPRECATION_NOTICE = (
    "test_executor_server.py simülasyon servisidir. Gerçek koşum için "
    "engine/app.py → /api/run veya /api/nexus/run kullanın."
)


def _simulate_scenario(scenario_id: str | None, test_data: Any, url: str | None) -> dict[str, Any]:
    """Deterministik sahte koşum sonucu üretir.

    Gerçek tarayıcı açmaz, hiçbir assert çalıştırmaz. Sadece çağıran tarafa
    hızlı bir "ok" akışı sağlamak için kullanılabilir (örn. UI demo).
    """
    return {
        "scenario_id": scenario_id,
        "url": url,
        "test_data": test_data,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "completed",
        "success": True,
        # Gerçek süre değil — saniyenin ondalık kısmından türetilmiş sahte metrik.
        "duration_ms": int((time.time() % 1) * 3000) + 1000,
        # Kritik bayrak: tüketiciler bu sonucun simüle edildiğini bilmeli.
        "simulated": True,
        "notice": _DEPRECATION_NOTICE,
    }


@app.route("/health", methods=["GET"])
def health():
    return jsonify(
        {
            "status": "healthy",
            "simulated": True,
            "notice": _DEPRECATION_NOTICE,
        }
    )


@app.route("/api/execute", methods=["POST"])
def execute():
    data = request.get_json(silent=True) or {}
    result = _simulate_scenario(
        scenario_id=data.get("scenario_id"),
        test_data=data.get("test_data", {}),
        url=data.get("url"),
    )
    _results.append(result)
    logger.warning("Simulated execution served (scenario_id=%s)", result["scenario_id"])
    return jsonify(result)


@app.route("/api/results", methods=["GET"])
def get_results():
    return jsonify(
        {
            "results": _results,
            "simulated": True,
            "notice": _DEPRECATION_NOTICE,
        }
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5002))
    # Hangi durumda başlatıldığını loglarda net göster.
    logger.warning("=" * 64)
    logger.warning("TEST EXECUTOR SIMULATOR (DEPRECATED) — port %s", port)
    logger.warning(_DEPRECATION_NOTICE)
    logger.warning("=" * 64)
    app.run(host="127.0.0.1", port=port, debug=False)
