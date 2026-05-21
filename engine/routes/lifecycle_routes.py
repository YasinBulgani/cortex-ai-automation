from flask import Blueprint, request, jsonify
from core.ai_client import AIClient
import json

lifecycle_bp = Blueprint('lifecycle', __name__)
ai_client = AIClient()

@lifecycle_bp.route('/api/lifecycle/process-analyst', methods=['POST'])
def process_analyst():
    data = request.json
    text = data.get('text', '')
    
    if not text:
        return jsonify({"error": "No text provided"}), 400

    prompt = f"""
    Aşağıdaki analist maddesini/dökümanını analiz et:
    "{text}"
    
    Lütfen şunları çıkar:
    1. Kısa bir özet (max 10 kelime).
    2. Manuel test için gerekli adımlar (liste halinde).
    
    Yanıtı şu JSON formatında ver:
    {{
      "summary": "Özet buraya",
      "steps": ["Adım 1", "Adım 2", ...]
    }}
    """
    
    try:
        response_text = ai_client.ask(prompt)
        # JSON temizleme
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()
            
        result = json.loads(response_text)
        return jsonify(result)
    except Exception as e:
        return jsonify({
            "summary": "Hata oluştu",
            "steps": [f"Hata: {str(e)}"]
        })

@lifecycle_bp.route('/api/lifecycle/save', methods=['POST'])
def save_flow():
    # Gelecekte DB'ye kaydetmek için
    return jsonify({"status": "ok", "message": "Akış kaydedildi (Simüle edildi)"})
