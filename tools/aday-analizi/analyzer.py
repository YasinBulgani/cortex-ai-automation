# -*- coding: utf-8 -*-
"""
OpenAI ile görüşme notlarının analizi ve analiz.json kaydı.
"""
import json
from pathlib import Path

from openai import OpenAI

from .config import ANALIZ_DOSYASI, OPENAI_API_KEY, OPENAI_MODEL


# Yapılandırılabilir prompt; JSON alanları net tanımlı
ANALIZ_PROMPT = """
Aşağıdaki görüşme notlarına göre SADE ve NET bir değerlendirme yap.

ÇIKTI FORMAT (yalnızca aşağıdaki JSON'u doldur, başka metin yazma):
{{
  "genel_degerlendirme": "kısa özet (1-2 cümle)",
  "guclu_yonler": ["madde1", "madde2", ...],
  "riskler": ["madde1", "madde2", ...],
  "seviye_tahmini": "Junior" | "Mid" | "Senior",
  "karar_onerisi": "Olumlu" | "Beklemede" | "Olumsuz"
}}

Kurallar:
- guclu_yonler ve riskler en az 1, en fazla 5 madde.
- seviye_tahmini sadece: Junior, Mid veya Senior.
- karar_onerisi sadece: Olumlu, Beklemede veya Olumsuz.
- Yanıtında SADECE geçerli JSON olsun, açıklama ekleme.

Görüşme Notları:
---
{notlar}
---
"""


def _get_client() -> OpenAI:
    if not OPENAI_API_KEY:
        raise ValueError(
            "OPENAI_API_KEY ortam değişkeni tanımlı değil. "
            ".env dosyası veya ortam değişkeni ile verin."
        )
    return OpenAI(api_key=OPENAI_API_KEY)


def chatgpt_analiz_et(notlar: str, model: str | None = None) -> dict:
    """
    Görüşme notlarını OpenAI ile analiz eder; yapılandırılmış dict döner.
    """
    client = _get_client()
    m = model or OPENAI_MODEL
    prompt = ANALIZ_PROMPT.format(notlar=notlar)

    response = client.chat.completions.create(
        model=m,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = (response.choices[0].message.content or "").strip()

    # JSON blok çıkar (markdown code block içinde gelirse)
    if raw.startswith("```"):
        lines = raw.split("\n")
        # ```json ... ``` veya ``` ... ```
        start = 1 if lines[0].startswith("```") else 0
        end = next((i for i, L in enumerate(lines) if L.strip() == "```" and i > 0), len(lines))
        raw = "\n".join(lines[start:end])

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"yorum": raw, "parse_hatasi": True}


def analiz_kaydet(aday_path: Path, analiz: dict, dosya_adi: str | None = None) -> Path:
    """
    Analizi aday klasörüne analiz.json (veya verilen ad) olarak kaydeder.
    """
    ad = dosya_adi or ANALIZ_DOSYASI
    analiz_dosyasi = aday_path / ad
    analiz_dosyasi.write_text(
        json.dumps(analiz, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return analiz_dosyasi
