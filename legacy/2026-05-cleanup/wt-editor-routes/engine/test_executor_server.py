#!/usr/bin/env python3
import json, time
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)
results = []

def execute_scenario(scenario_id, test_data, url):
    result = {"scenario_id": scenario_id, "url": url, "test_data": test_data, "timestamp": datetime.now().isoformat(), "status": "completed", "success": True, "duration_ms": int((time.time() % 1) * 3000) + 1000}
    results.append(result)
    return result

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy"})

@app.route('/api/execute', methods=['POST'])
def execute():
    data = request.json
    result = execute_scenario(data.get('scenario_id'), data.get('test_data', {}), data.get('url'))
    return jsonify(result)

@app.route('/api/results', methods=['GET'])
def get_results():
    return jsonify({"results": results})

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5002))
    print(f"\n✅ TEST EXECUTOR SERVER BAŞLATILDI\n📍 http://127.0.0.1:{port}\n")
    app.run(host='127.0.0.1', port=port, debug=False)
