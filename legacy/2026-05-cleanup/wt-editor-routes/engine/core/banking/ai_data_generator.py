"""
TestwrightAI Banking — AI-Powered Schema Analyzer & Data Generator
Uses LLM (Claude/OpenAI) to analyze DB schema and generate realistic Turkish banking test data.
Falls back to rule-based generation when no API key is available.
"""
import os
import re
import json
import random
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

# ── System prompt ────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """Sen kıdemli bir Türk bankacılık sistemi test veri uzmanısın.
Görevin:
1. Verilen veritabanı şemasını analiz etmek
2. Her tablonun iş amacını anlamak
3. BDDK/KVKK uyumlu, gerçekçi ama gerçek olmayan Türk bankacılık test verisi üretmek

Uzmanlıkların:
- Türk bankacılık sektörü terminolojisi ve iş kuralları
- ISO 13616 IBAN standardı, Luhn algoritması, TC Kimlik Mod-10
- Tablolar arası FK ilişkileri ve veri bütünlüğü
- BDDK yönetmelik gereklilikleri (temerrüt oranları, kredi limitleri, risk skorları)"""


def _build_analysis_prompt(schema_ddl: str) -> str:
    """Ask LLM to analyze the schema and infer business rules."""
    return f"""Aşağıdaki veritabanı şemasını analiz et ve iş kurallarını çıkar.

## ŞEMA:
```
{schema_ddl}
```

Şunları tespit et:
1. Her tablonun iş amacı (1 cümle)
2. Kritik iş kuralları (tarih mantığı, tutar limitleri, FK kısıtları)
3. Veri kalitesi gereksinimleri (hangi alanlar benzersiz olmalı, hangileri belirli değer aralıkları)
4. Türk bankacılığına özgü kural tespitleri

JSON formatında yanıt ver:
{{
  "table_purposes": {{"TABLO_ADI": "amaç açıklaması"}},
  "business_rules": ["kural 1", "kural 2", ...],
  "data_constraints": {{"TABLO.KOLON": "kısıt açıklaması"}},
  "turkish_banking_rules": ["BDDK kuralı 1", ...]
}}"""


def _build_generation_prompt(
    schema_ddl: str,
    analysis: dict,
    counts: Dict[str, int],
    extra_rules: str = ''
) -> str:
    """Build the data generation prompt."""
    table_list = '\n'.join(f"  - {t}: {n} satır" for t, n in counts.items())

    rules_section = ''
    if analysis:
        biz_rules = analysis.get('business_rules', [])
        tr_rules  = analysis.get('turkish_banking_rules', [])
        if biz_rules or tr_rules:
            rules_section = '\n## ANALİZ EDİLEN İŞ KURALLARI:\n'
            rules_section += '\n'.join(f'- {r}' for r in biz_rules + tr_rules)

    return f"""Aşağıdaki Türk bankacılık şeması için test verisi üret.

## VERİTABANI ŞEMASI:
```
{schema_ddl}
```
{rules_section}

## ÜRETİLECEK VERİ:
{table_list}

## ZORUNLU ALGORİTMİK KURALLAR:
1. TC Kimlik (11 hane): İlk 9 rakam rastgele (ilk rakam 1-9),
   d10 = (d1+d3+d5+d7+d9)×7 - (d2+d4+d6+d8)) mod 10,
   d11 = (d1+d2+...+d10) mod 10
2. VKN (10 hane): Tüm basamaklara checksum uygulanmalı
3. TR IBAN (26 karakter): TR + 2 kontrol hanesi + 5 banka kodu + 1 reserve + 16 hesap no
   Örnek geçerli format: TR330006100519786457841326
4. Kart (16 hane): Luhn algoritması — Troy prefix 9792, Visa 4xxx, MC 51-55xx
5. FK: child tablodaki FK kolonları, parent tablodaki gerçek PK değerlerine referans etmeli
6. Tarih mantığı: baslangic_tarihi < bitis_tarihi, her zaman geçerli tarihler
7. Tutar mantığı: kalan_borc ≤ ana_para, kullanilan_limit ≤ kart_limiti, bakiye ≥ 0
8. Türk telefonu: +905xx ile başlayan 13 karakterli numara
9. Email: gercekisim.soyisim99@gmail.com formatı{f'''

## EK İŞ KURALLARI:
{extra_rules}''' if extra_rules else ''}

## ÇIKTI (SADECE JSON — başka metin, markdown veya açıklama ekleme):
{{
  "TABLO_ADI": [
    {{"KOLON1": değer1, "KOLON2": "değer2"}},
    ...
  ]
}}

ÖNEMLİ NOTLAR:
- PK kolonlar: 1'den başlayarak sıralı integer
- FK kolonlar: parent tablodaki gerçek PK değerlerini kullan
- NULL olabilir kolonlara %20 oranında null koy (zorunlu alanlar hariç)
- Türkçe isim, şehir, adres kullan
- Veri çeşitliliği sağla — her satır farklı olmalı"""


OLLAMA_BASE_URL = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
OLLAMA_DEFAULT_MODEL = os.getenv('OLLAMA_MODEL', 'llama3.1:latest')


def _detect_ollama() -> Optional[str]:
    """Ollama çalışıyor mu? Çalışıyorsa en iyi modeli döndür."""
    try:
        import urllib.request
        with urllib.request.urlopen(f'{OLLAMA_BASE_URL}/api/tags', timeout=2) as r:
            data = json.loads(r.read())
        models = [m['name'] for m in data.get('models', [])]
        if not models:
            return None
        # Öncelik sırası: llama3.1 > llama3 > mistral > diğer
        for preferred in ['llama3.1:latest', 'llama3:latest', 'mistral:latest']:
            if preferred in models:
                return preferred
        return models[0]  # İlk modeli kullan
    except Exception:
        return None


def _get_llm_client():
    """
    Sırayla dene:
    1. Anthropic API key (ANTHROPIC_API_KEY)
    2. OpenAI API key (OPENAI_API_KEY)
    3. Ollama yerel (localhost:11434)
    """
    # 1. Anthropic
    key = os.getenv('ANTHROPIC_API_KEY') or os.getenv('CLAUDE_API_KEY')
    if key and not key.startswith('sk-place'):  # placeholder key'leri atla
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=key)
            return client, 'claude-3-5-haiku-20241022', 'anthropic'
        except ImportError:
            logger.warning("anthropic paketi yüklü değil: pip install anthropic")

    # 2. OpenAI
    key = os.getenv('OPENAI_API_KEY')
    if key and not key.startswith('sk-place'):
        try:
            import openai
            client = openai.OpenAI(api_key=key)
            return client, 'gpt-4o-mini', 'openai'
        except ImportError:
            logger.warning("openai paketi yüklü değil: pip install openai")

    # 3. Ollama (yerel — API key gerektirmez)
    ollama_model = _detect_ollama()
    if ollama_model:
        try:
            import openai
            # Ollama, OpenAI-uyumlu API sunar
            client = openai.OpenAI(
                api_key='ollama',          # Ollama API key istemez, dummy değer
                base_url=f'{OLLAMA_BASE_URL}/v1',
            )
            logger.info(f"Ollama bulundu: {ollama_model}")
            return client, ollama_model, 'ollama'
        except ImportError:
            # openai kütüphanesi yoksa direkt HTTP kullan
            return 'ollama_http', ollama_model, 'ollama_http'

    return None, None, None


def _call_llm(client, model: str, provider: str, system: str, user: str, max_tokens: int = 4096) -> str:
    if provider == 'anthropic':
        msg = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=[{'role': 'user', 'content': user}]
        )
        return msg.content[0].text

    elif provider in ('openai', 'ollama'):
        resp = client.chat.completions.create(
            model=model,
            max_tokens=max_tokens,
            messages=[
                {'role': 'system', 'content': system},
                {'role': 'user',   'content': user},
            ],
            temperature=0.7,
        )
        return resp.choices[0].message.content

    elif provider == 'ollama_http':
        # openai paketi yoksa Ollama REST API'yi direkt çağır
        import urllib.request
        payload = json.dumps({
            'model':   model,
            'prompt':  f"{system}\n\n{user}",
            'stream':  False,
            'options': {'temperature': 0.7, 'num_predict': max_tokens},
        }).encode()
        req = urllib.request.Request(
            f'{OLLAMA_BASE_URL}/api/generate',
            data=payload,
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        with urllib.request.urlopen(req, timeout=120) as r:
            result = json.loads(r.read())
        return result.get('response', '')

    raise RuntimeError(f"Bilinmeyen LLM provider: {provider}")


def _parse_json(raw: str) -> dict:
    """Extract JSON dict from LLM response (tolerates markdown fences)."""
    # Strip markdown code fences
    clean = re.sub(r'```(?:json)?\s*\n?', '', raw).strip()
    clean = re.sub(r'```\s*$', '', clean).strip()
    # Find outermost { }
    start = clean.find('{')
    end   = clean.rfind('}') + 1
    if start == -1:
        raise ValueError("LLM yanıtında JSON bulunamadı")
    return json.loads(clean[start:end])


def _fix_algorithmic_fields(data: dict, schema_dict: dict) -> dict:
    """
    LLM bazen TC Kimlik, IBAN, kart numarası gibi algoritmik alanları yanlış üretir.
    Bu fonksiyon onları doğrulayıp geçersizleri yeniden üretir.
    """
    try:
        from banking.generators.identity   import generate_tc_kimlik, validate_tc_kimlik, generate_vkn, validate_vkn
        from banking.generators.account    import generate_tr_iban, validate_tr_iban, TR_BANK_CODES
        from banking.generators.card       import generate_card_number, luhn_check
        from banking.db_schema_reader      import infer_generator
    except ImportError:
        return data

    for tname, rows in data.items():
        if not rows: continue
        tdef    = schema_dict.get(tname, {})
        columns = tdef.get('columns', []) if isinstance(tdef, dict) else []

        # Build generator map for this table
        gen_map = {}
        for col in columns:
            if isinstance(col, dict):
                gen_map[col['name']] = col.get('generator', '')
            else:
                gen_map[getattr(col,'name','')] = getattr(col,'generator','')

        for row in rows:
            for col_name, val in list(row.items()):
                if val is None: continue
                gen = gen_map.get(col_name, infer_generator(col_name, 'TEXT'))

                if gen == 'tc_kimlik':
                    if not validate_tc_kimlik(str(val)):
                        row[col_name] = generate_tc_kimlik()
                elif gen == 'vkn':
                    if not validate_vkn(str(val)):
                        row[col_name] = generate_vkn()
                elif gen == 'iban':
                    s = str(val).replace(' ', '')
                    if not validate_tr_iban(s):
                        bk = random.choice(list(TR_BANK_CODES.keys()))
                        row[col_name] = generate_tr_iban(bk)
                elif gen == 'card_number':
                    s = str(val).replace(' ', '').replace('-', '')
                    if not luhn_check(s):
                        row[col_name] = generate_card_number('troy')
    return data


def _enforce_fk_integrity(data: dict, schema_dict: dict) -> dict:
    """Ensure FK columns reference actual generated PK values."""
    # Build pool of generated PKs
    pk_pools: Dict[str, list] = {}
    for tname, rows in data.items():
        if not rows: continue
        tdef = schema_dict.get(tname, {})
        pk_cols = tdef.get('pk_columns', []) if isinstance(tdef, dict) else []
        if pk_cols:
            pk_pools[tname] = [r.get(pk_cols[0]) for r in rows if r.get(pk_cols[0]) is not None]

    # Fix any broken FK references
    for tname, rows in data.items():
        tdef = schema_dict.get(tname, {})
        fk_cols = tdef.get('fk_columns', []) if isinstance(tdef, dict) else []
        for fk in fk_cols:
            col_name  = fk.get('column')
            ref_table = fk.get('ref_table')
            pool = pk_pools.get(ref_table, [])
            if pool:
                for row in rows:
                    if row.get(col_name) not in pool:
                        row[col_name] = random.choice(pool)
    return data


class AIDataGenerator:
    """
    AI-powered database-aware test data generator.
    1. Connects to DB and reads schema
    2. Sends schema to LLM for business rule analysis
    3. LLM generates realistic test data following schema + rules
    4. Falls back to rule-based generation if no API key
    """

    def __init__(self, preferred_model: Optional[str] = None):
        self.client, self.model, self.provider = _get_llm_client()
        if preferred_model and self.provider in ('ollama', 'ollama_http'):
            self.model = preferred_model  # kullanıcı belirli bir Ollama modeli seçebilir
        self.has_llm = self.client is not None
        self._last_analysis: Optional[dict] = None

    @staticmethod
    def get_available_providers() -> dict:
        """Kullanılabilir LLM sağlayıcı ve modellerini döndürür."""
        providers = {}

        # Anthropic
        key = os.getenv('ANTHROPIC_API_KEY') or os.getenv('CLAUDE_API_KEY')
        providers['anthropic'] = {
            'available': bool(key and not key.startswith('sk-place')),
            'models': ['claude-3-5-haiku-20241022', 'claude-3-5-sonnet-20241022'],
            'label': '☁️ Anthropic Claude',
            'requires_key': True,
        }

        # OpenAI
        key = os.getenv('OPENAI_API_KEY')
        providers['openai'] = {
            'available': bool(key and not key.startswith('sk-place')),
            'models': ['gpt-4o-mini', 'gpt-4o'],
            'label': '☁️ OpenAI GPT',
            'requires_key': True,
        }

        # Ollama
        ollama_model = _detect_ollama()
        if ollama_model:
            try:
                import urllib.request
                with urllib.request.urlopen(f'{OLLAMA_BASE_URL}/api/tags', timeout=2) as r:
                    data = json.loads(r.read())
                ollama_models = [m['name'] for m in data.get('models', [])]
            except Exception:
                ollama_models = [ollama_model]
            providers['ollama'] = {
                'available': True,
                'models': ollama_models,
                'default_model': ollama_model,
                'label': '🦙 Ollama (Yerel — API key gerekmez)',
                'requires_key': False,
                'base_url': OLLAMA_BASE_URL,
            }
        else:
            providers['ollama'] = {
                'available': False,
                'models': [],
                'label': '🦙 Ollama (Yüklü değil)',
                'requires_key': False,
            }

        return providers

    def analyze_schema(self, schema_ddl: str) -> dict:
        """
        Ask LLM to analyze schema and extract business rules.
        Returns analysis dict (or empty dict if no LLM).
        """
        if not self.has_llm:
            return {}
        try:
            prompt = _build_analysis_prompt(schema_ddl)
            raw    = _call_llm(self.client, self.model, self.provider, SYSTEM_PROMPT, prompt, 1024)
            result = _parse_json(raw)
            self._last_analysis = result
            return result
        except Exception as e:
            logger.error(f"Schema analysis error: {e}")
            return {}

    def generate(
        self,
        schema_dict: dict,
        schema_ddl: str,
        counts: Dict[str, int],
        extra_rules: str = '',
        analysis: Optional[dict] = None,
        seed: Optional[int] = None,
    ) -> dict:
        """
        Generate test data for the given schema tables.

        Returns:
        {
            'data':     {table_name: [rows...]},
            'method':   'ai' | 'fallback',
            'analysis': analysis_dict,
            'model':    model_name or None,
            'message':  human-readable status
        }
        """
        if seed is not None:
            random.seed(seed)

        if not self.has_llm:
            return self._fallback(schema_dict, counts, "LLM API key bulunamadı.")

        # Use provided or previously cached analysis
        if analysis is None:
            analysis = self._last_analysis or {}

        try:
            prompt = _build_generation_prompt(schema_ddl, analysis, counts, extra_rules)
            raw    = _call_llm(self.client, self.model, self.provider, SYSTEM_PROMPT, prompt, 4096)
            data   = _parse_json(raw)

            # Post-process: fix FKs
            data = _fix_algorithmic_fields(data, schema_dict)  # TC/IBAN/Luhn doğrula+düzelt
            data = _enforce_fk_integrity(data, schema_dict)    # FK bütünlüğü

            # Trim/pad to requested counts
            for tname, requested in counts.items():
                if tname in data:
                    rows = data[tname]
                    if len(rows) > requested:
                        data[tname] = rows[:requested]
                    elif len(rows) < requested and rows:
                        # Duplicate and vary last rows to fill count
                        while len(data[tname]) < requested:
                            extra = dict(rows[-1])
                            data[tname].append(extra)

            return {
                'data':     data,
                'method':   'ai',
                'analysis': analysis,
                'model':    f'{self.provider}/{self.model}',
                'message':  f'LLM ({self.provider}/{self.model}) ile üretildi',
            }
        except Exception as e:
            logger.error(f"AI generation error: {e}")
            return self._fallback(schema_dict, counts, f'LLM hatası ({e}). Kural tabanlı üretim kullanıldı.')

    def _fallback(self, schema_dict: dict, counts: Dict[str, int], reason: str) -> dict:
        from banking.schema_aware_generator import SchemaAwareGenerator
        gen  = SchemaAwareGenerator(schema_dict)
        data = gen.generate_all(counts)
        return {
            'data':     data,
            'method':   'fallback',
            'analysis': {},
            'model':    None,
            'message':  reason,
        }
