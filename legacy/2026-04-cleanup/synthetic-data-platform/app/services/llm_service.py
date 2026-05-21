"""
LLM/AI Entegrasyon Servisi — LLMService Modulu.

Dogal dil ile veri talebi, akilli siniflandirma ve kural onerisi saglar.
OpenAI, Anthropic ve Ollama API destegi ile LLM entegrasyonu sunar.
LLM erisimi yoksa regex+keyword tabanli fallback ile calisir.

Kullanim:
    service = LLMService()

    # Dogal dil ile veri talebi
    config = service.parse_natural_language_request(
        "500 premium musteri uret, kredi notu 1200 ustu olsun"
    )

    # Kolon siniflandirma
    sem_type = service.classify_column_with_llm("musteri_adi", ["Ali", "Veli"])

    # Kural onerisi
    rules = service.suggest_rules_with_llm(column_profiles)
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from app.config import settings
from app.services.column_classifier import SemanticType

logger = logging.getLogger(__name__)


# =====================================================================
# LLM Provider Tanimlari
# =====================================================================


class LLMProvider(str, Enum):
    """Desteklenen LLM saglayicilari."""

    OPENAI = "openai"           # OpenAI GPT-4 / GPT-3.5
    ANTHROPIC = "anthropic"     # Anthropic Claude
    OLLAMA = "ollama"           # Yerel Ollama (Llama, Mistral vb.)
    FALLBACK = "fallback"       # LLM yok — regex/keyword tabanli


# =====================================================================
# Prompt Sablonlari (Turkce)
# =====================================================================


PARSE_REQUEST_PROMPT = """Sen bir bankacilik sentetik veri uretim asistanisin.
Kullanicinin dogal dildeki talebini yapilandirilmis bir JSON formatina donustur.

Talep: {request_text}

Asagidaki JSON formatinda yanit ver (sadece JSON, baska bir sey yazma):
{{
    "senaryo": "<bireysel|premium|maas|yuksek_bakiyeli|kredi_karti_gecikmeli|cok_islem|dormant|riskli|ticari|yeni_musteri|emekli|ogrenci|custom>",
    "musteri_sayisi": <sayi>,
    "min_bakiye": <sayi veya null>,
    "max_bakiye": <sayi veya null>,
    "kredi_skoru_min": <sayi veya null>,
    "kredi_skoru_max": <sayi veya null>,
    "segment": "<segment veya null>",
    "yas_min": <sayi veya null>,
    "yas_max": <sayi veya null>,
    "ozel_kurallar": {{}}
}}

Onemli:
- Sayi belirtilmemisse musteri_sayisi icin 1000 kullan
- Senaryo belirtilmemisse "bireysel" kullan
- Sadece belirtilen degerleri doldur, gerisi null olsun
"""

CLASSIFY_COLUMN_PROMPT = """Sen bir bankacilik veri analisti sin.
Asagidaki kolon adini ve ornek degerleri inceleyerek semantik tipini belirle.

Kolon adi: {column_name}
Ornek degerler: {sample_values}

Olasi tipler: person_name, first_name, last_name, full_name, birth_date, age,
national_id, customer_id, account_id, iban, account_number, credit_card,
phone, email, address, city, district, segment, customer_type, account_type,
account_status, transaction_type, balance, amount, currency, credit_score,
card_limit, transaction_date, maturity_date, branch_code, channel,
interest_rate, unknown

Sadece tip adini yaz, baska bir sey yazma.
Tip: """

SUGGEST_RULES_PROMPT = """Sen bir bankacilik veri kalite uzmanisin.
Asagidaki kolon profillerini inceleyerek veri uretim kurallari oner.

Kolon profilleri:
{column_profiles_json}

Her kolon icin uygun kurallari JSON formatinda oner:
[
    {{
        "column_name": "<kolon_adi>",
        "rule_type": "<range|enum|regex|distribution|not_null|unique|length>",
        "rule_definition": {{}},
        "confidence": <0.0-1.0>,
        "aciklama": "<Turkce aciklama>"
    }}
]

Sadece JSON formatinda yanit ver.
"""

DESCRIBE_COLUMN_PROMPT = """Sen bir bankacilik veri dokumantasyon uzmanisin.
Asagidaki kolon bilgilerini inceleyerek kisa ve acik bir Turkce aciklama yaz.

Kolon adi: {column_name}
Istatistikler: {stats_json}

Aciklama (tek cumle, Turkce): """


# =====================================================================
# Anahtar Kelime Eslesme Tablolari (Fallback icin)
# =====================================================================


# Senaryo anahtar kelimeleri
_SCENARIO_KEYWORDS: dict[str, str] = {
    "bireysel": "bireysel",
    "standart": "bireysel",
    "normal": "bireysel",
    "premium": "premium",
    "vip": "premium",
    "platinum": "premium",
    "maas": "maas",
    "salary": "maas",
    "calisan": "maas",
    "yuksek bakiye": "yuksek_bakiyeli",
    "zengin": "yuksek_bakiyeli",
    "high balance": "yuksek_bakiyeli",
    "gecikmeli": "kredi_karti_gecikmeli",
    "gecikme": "kredi_karti_gecikmeli",
    "kredi karti": "kredi_karti_gecikmeli",
    "overdue": "kredi_karti_gecikmeli",
    "cok islem": "cok_islem",
    "aktif": "cok_islem",
    "yogun": "cok_islem",
    "dormant": "dormant",
    "hareketsiz": "dormant",
    "uykuda": "dormant",
    "pasif": "dormant",
    "riskli": "riskli",
    "risk": "riskli",
    "ticari": "ticari",
    "kurumsal": "ticari",
    "sirket": "ticari",
    "corporate": "ticari",
    "yeni": "yeni_musteri",
    "yeni musteri": "yeni_musteri",
    "emekli": "emekli",
    "retired": "emekli",
    "ogrenci": "ogrenci",
    "student": "ogrenci",
}

# Kolon adi → SemanticType eslesmesi (fallback siniflandirma icin)
_COLUMN_NAME_SEMANTIC_MAP: dict[str, str] = {
    "ad": "first_name",
    "soyad": "last_name",
    "isim": "first_name",
    "adi": "first_name",
    "soyadi": "last_name",
    "musteri_adi": "person_name",
    "musteri_no": "customer_id",
    "hesap_no": "account_id",
    "tckn": "national_id",
    "tc_kimlik": "national_id",
    "kimlik_no": "national_id",
    "iban": "iban",
    "telefon": "phone",
    "tel": "phone",
    "email": "email",
    "eposta": "email",
    "adres": "address",
    "sehir": "city",
    "il": "city",
    "ilce": "district",
    "bakiye": "balance",
    "tutar": "amount",
    "islem_tutari": "amount",
    "para_birimi": "currency",
    "doviz": "currency",
    "kredi_notu": "credit_score",
    "kredi_skoru": "credit_score",
    "dogum_tarihi": "birth_date",
    "yas": "age",
    "islem_tarihi": "transaction_date",
    "tarih": "transaction_date",
    "vade_tarihi": "maturity_date",
    "hesap_tipi": "account_type",
    "hesap_turu": "account_type",
    "hesap_durumu": "account_status",
    "islem_tipi": "transaction_type",
    "islem_turu": "transaction_type",
    "segment": "segment",
    "musteri_tipi": "customer_type",
    "sube_kodu": "branch_code",
    "sube": "branch_code",
    "kanal": "channel",
    "faiz_orani": "interest_rate",
    "faiz": "interest_rate",
    "kart_limiti": "card_limit",
    "limit": "card_limit",
    "kredi_karti": "credit_card",
    "kart_no": "credit_card",
    "hesap_numarasi": "account_number",
}


# =====================================================================
# Ana Sinif — LLMService
# =====================================================================


class LLMService:
    """
    LLM/AI Entegrasyon Servisi.

    Dogal dil isleme, kolon siniflandirma ve kural onerisi icin
    LLM API'lerini kullanir. LLM erisimi yoksa fallback mekanizmasi
    ile regex ve keyword tabanli islem yapar.

    Desteklenen LLM saglayicilari:
    - OpenAI (GPT-4, GPT-3.5-turbo)
    - Anthropic (Claude 3 Sonnet, Opus, Haiku)
    - Ollama (yerel modeller: Llama, Mistral vb.)
    - Fallback (LLM olmadan regex/keyword)

    Kullanim:
        service = LLMService()

        # Dogal dil → yapilandirilmis talep
        parsed = service.parse_natural_language_request(
            "1000 tane premium musteri olustur"
        )

        # Kolon siniflandirma
        sem_type = service.classify_column_with_llm(
            "musteri_adi", ["Ahmet Yilmaz", "Mehmet Demir"]
        )
    """

    def __init__(
        self,
        provider: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        endpoint: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> None:
        """
        LLMService baslatici.

        Parametreler verilmezse config.py'den okunur.
        Tum parametreler opsiyoneldir — fallback her zaman calisir.

        Args:
            provider: LLM saglayicisi (openai/anthropic/ollama/fallback)
            api_key: API anahtari
            model: Model adi
            endpoint: API endpoint URL'i (Ollama icin)
            temperature: Uretim sicakligi (0.0-1.0)
            max_tokens: Maksimum token sayisi
        """
        self._provider = LLMProvider(
            provider or getattr(settings, "LLM_PROVIDER", "fallback")
        )
        self._api_key = api_key or getattr(settings, "LLM_API_KEY", "")
        self._model = model or getattr(settings, "LLM_MODEL", "")
        self._endpoint = endpoint or getattr(settings, "LLM_ENDPOINT", "")
        self._temperature = temperature or getattr(
            settings, "LLM_TEMPERATURE", 0.1,
        )
        self._max_tokens = max_tokens or getattr(
            settings, "LLM_MAX_TOKENS", 2000,
        )

        # Provider gecerliligi kontrol et
        if self._provider != LLMProvider.FALLBACK and not self._api_key:
            logger.warning(
                "LLM provider '%s' secili ama API key yok — fallback'e dusulecek",
                self._provider.value,
            )
            self._provider = LLMProvider.FALLBACK

        logger.info(
            "LLMService baslatildi (provider=%s, model=%s)",
            self._provider.value, self._model or "N/A",
        )

    # -- Dogal Dil Talep Ayrıstirma ----------------------------------

    def parse_natural_language_request(
        self, text: str,
    ) -> dict[str, Any]:
        """
        Dogal dildeki veri talebini yapilandirilmis formata cevirir.

        Args:
            text: Kullanicinin dogal dildeki talebi
                  Ornek: "500 premium musteri uret, kredi notu 1200 ustu"

        Returns:
            Yapilandirilmis talep dict'i:
            {
                "senaryo": "premium",
                "musteri_sayisi": 500,
                "kredi_skoru_min": 1200,
                ...
            }
        """
        if not text or not text.strip():
            return self._default_request()

        # Oncelikle LLM dene
        if self._provider != LLMProvider.FALLBACK:
            try:
                result = self._parse_with_llm(text)
                if result:
                    logger.info("LLM ile talep ayristirildi: %s", result)
                    return result
            except Exception as exc:
                logger.warning(
                    "LLM talep ayristirma hatasi, fallback'e dusuldu: %s", exc,
                )

        # Fallback: regex + keyword
        return self._fallback_parse(text)

    # -- LLM ile Kolon Siniflandirma ----------------------------------

    def classify_column_with_llm(
        self,
        column_name: str,
        sample_values: list[Any],
    ) -> SemanticType:
        """
        LLM kullanarak kolon tipini siniflandirir.

        Args:
            column_name: Kolon adi
            sample_values: Ornek degerler listesi (en fazla 10)

        Returns:
            SemanticType enum degeri
        """
        # Oncelikle fallback ile dene (hizli)
        fallback_result = self._fallback_classify(column_name, sample_values)

        # LLM varsa ve fallback UNKNOWN donuyorsa LLM'e sor
        if (
            fallback_result == SemanticType.UNKNOWN
            and self._provider != LLMProvider.FALLBACK
        ):
            try:
                prompt = CLASSIFY_COLUMN_PROMPT.format(
                    column_name=column_name,
                    sample_values=str(sample_values[:10]),
                )
                response = self._call_llm(prompt)
                if response:
                    cleaned = response.strip().lower().replace(" ", "_")
                    try:
                        return SemanticType(cleaned)
                    except ValueError:
                        logger.debug(
                            "LLM bilinmeyen tip dondu: %s", cleaned,
                        )
            except Exception as exc:
                logger.warning(
                    "LLM kolon siniflandirma hatasi: %s", exc,
                )

        return fallback_result

    # -- LLM ile Kural Onerisi ---------------------------------------

    def suggest_rules_with_llm(
        self,
        column_profiles: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        LLM kullanarak kolon profilleri icin kural onerileri uretir.

        Args:
            column_profiles: Kolon profil bilgileri listesi
                Her profil: {"name": str, "dtype": str, "stats": dict, ...}

        Returns:
            Kural onerileri listesi:
            [{"column_name", "rule_type", "rule_definition", "confidence", "aciklama"}]
        """
        # Fallback kurallar
        fallback_rules = self._fallback_suggest_rules(column_profiles)

        # LLM varsa ek onerileri al
        if self._provider != LLMProvider.FALLBACK:
            try:
                profiles_json = json.dumps(
                    column_profiles[:20],  # Maks 20 kolon gonder
                    ensure_ascii=False,
                    indent=2,
                    default=str,
                )
                prompt = SUGGEST_RULES_PROMPT.format(
                    column_profiles_json=profiles_json,
                )
                response = self._call_llm(prompt)
                if response:
                    llm_rules = self._parse_json_response(response)
                    if isinstance(llm_rules, list):
                        # LLM kurallarini fallback ile birlestir
                        existing_keys = {
                            (r["column_name"], r["rule_type"])
                            for r in fallback_rules
                        }
                        for rule in llm_rules:
                            key = (
                                rule.get("column_name", ""),
                                rule.get("rule_type", ""),
                            )
                            if key not in existing_keys:
                                fallback_rules.append(rule)
                        logger.info(
                            "LLM %d ek kural onerdi", len(llm_rules),
                        )
            except Exception as exc:
                logger.warning(
                    "LLM kural onerisi hatasi: %s", exc,
                )

        return fallback_rules

    # -- LLM ile Kolon Aciklamasi ------------------------------------

    def generate_column_description(
        self,
        column_name: str,
        stats: dict[str, Any],
    ) -> str:
        """
        Kolon icin Turkce aciklama uretir.

        Args:
            column_name: Kolon adi
            stats: Kolon istatistikleri

        Returns:
            Turkce aciklama metni
        """
        # LLM ile dene
        if self._provider != LLMProvider.FALLBACK:
            try:
                prompt = DESCRIBE_COLUMN_PROMPT.format(
                    column_name=column_name,
                    stats_json=json.dumps(
                        stats, ensure_ascii=False, default=str,
                    ),
                )
                response = self._call_llm(prompt)
                if response and response.strip():
                    return response.strip()
            except Exception as exc:
                logger.warning(
                    "LLM aciklama uretim hatasi: %s", exc,
                )

        # Fallback: basit aciklama
        return self._fallback_describe(column_name, stats)

    # =================================================================
    # LLM API Wrapper'lari
    # =================================================================

    def _call_via_gateway(self, prompt: str) -> Optional[str]:
        """AI Gateway (Groq→Gemini→Ollama→g4f) üzerinden LLM çağrısı yapar."""
        try:
            import os, httpx  # type: ignore[import]
            gateway_url = os.environ.get("AI_GATEWAY_BASE_URL", "http://127.0.0.1:8080")
            internal_key = os.environ.get("GATEWAY_INTERNAL_KEY", "nexusqa-gateway-internal-key-change-me")

            # Önce gateway'in ayakta olup olmadığını kontrol et
            ping = httpx.get(f"{gateway_url}/ping", timeout=2.0)
            if ping.status_code != 200:
                return None

            resp = httpx.post(
                f"{gateway_url}/ai/complete",
                json={
                    "task_type": "chat",
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "Sen bir Türk bankacılık veri uzmanısın. "
                                "Yanıtlarını sadece istenen formatta ver."
                            ),
                        },
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": self._temperature,
                    "max_tokens": self._max_tokens,
                    "json_mode": True,
                },
                headers={"X-Internal-Key": internal_key, "Content-Type": "application/json"},
                timeout=30.0,
            )
            if resp.status_code == 200:
                data = resp.json()
                content = data.get("content", "")
                logger.debug("AI Gateway yanıtı alındı (%d karakter)", len(content))
                return content or None
        except Exception as exc:
            logger.debug("AI Gateway erişilemiyor: %s", exc)
        return None

    def _call_llm(self, prompt: str) -> Optional[str]:
        """
        LLM API çağrısı yapar.

        Öncelik: AI Gateway → Yapılandırılmış provider → None
        """
        # 1) AI Gateway dene (Groq→Gemini→Ollama→g4f fallback zinciri)
        result = self._call_via_gateway(prompt)
        if result:
            return result

        # 2) Yapılandırılmış provider
        if self._provider == LLMProvider.OPENAI:
            return self._call_openai(prompt)
        elif self._provider == LLMProvider.ANTHROPIC:
            return self._call_anthropic(prompt)
        elif self._provider == LLMProvider.OLLAMA:
            return self._call_ollama(prompt)
        else:
            return None

    def _call_openai(self, prompt: str) -> Optional[str]:
        """
        OpenAI API cagrisi.

        Gereksinim: pip install openai
        Ortam degiskeni: LLM_API_KEY

        Args:
            prompt: Gonderilecek prompt

        Returns:
            Model yaniti veya None
        """
        try:
            import openai

            client = openai.OpenAI(api_key=self._api_key)
            response = client.chat.completions.create(
                model=self._model or "gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Sen bir Turk bankacilik veri uzmanisin. "
                            "Yanitlarini sadece istenen formatta ver."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=self._temperature,
                max_tokens=self._max_tokens,
            )
            content = response.choices[0].message.content
            logger.debug("OpenAI yaniti alindi (%d karakter)", len(content or ""))
            return content

        except ImportError:
            logger.warning("openai paketi yuklu degil — pip install openai")
            return None
        except Exception as exc:
            logger.error("OpenAI API hatasi: %s", exc)
            return None

    def _call_anthropic(self, prompt: str) -> Optional[str]:
        """
        Anthropic Claude API cagrisi.

        Gereksinim: pip install anthropic
        Ortam degiskeni: LLM_API_KEY

        Args:
            prompt: Gonderilecek prompt

        Returns:
            Model yaniti veya None
        """
        try:
            import anthropic

            client = anthropic.Anthropic(api_key=self._api_key)
            response = client.messages.create(
                model=self._model or "claude-sonnet-4-20250514",
                max_tokens=self._max_tokens,
                messages=[
                    {"role": "user", "content": prompt},
                ],
                system=(
                    "Sen bir Turk bankacilik veri uzmanisin. "
                    "Yanitlarini sadece istenen formatta ver."
                ),
                temperature=self._temperature,
            )
            content = response.content[0].text
            logger.debug(
                "Anthropic yaniti alindi (%d karakter)", len(content or ""),
            )
            return content

        except ImportError:
            logger.warning(
                "anthropic paketi yuklu degil — pip install anthropic",
            )
            return None
        except Exception as exc:
            logger.error("Anthropic API hatasi: %s", exc)
            return None

    def _call_ollama(self, prompt: str) -> Optional[str]:
        """
        Ollama (yerel LLM) API cagrisi.

        Gereksinim: Ollama kurulu ve calisiyor olmali
        Varsayilan endpoint: http://localhost:11434

        Args:
            prompt: Gonderilecek prompt

        Returns:
            Model yaniti veya None
        """
        try:
            import urllib.request
            import urllib.error

            endpoint = self._endpoint or "http://localhost:11434"
            url = f"{endpoint}/api/generate"

            payload = json.dumps({
                "model": self._model or "llama3.2",
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": self._temperature,
                    "num_predict": self._max_tokens,
                },
            }).encode("utf-8")

            req = urllib.request.Request(
                url,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )

            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                content = data.get("response", "")
                logger.debug(
                    "Ollama yaniti alindi (%d karakter)", len(content),
                )
                return content

        except ImportError:
            logger.warning("urllib modulu bulunamadi")
            return None
        except Exception as exc:
            logger.error("Ollama API hatasi: %s", exc)
            return None

    # =================================================================
    # LLM ile Ayristirma
    # =================================================================

    def _parse_with_llm(self, text: str) -> Optional[dict[str, Any]]:
        """LLM kullanarak dogal dil talebini ayristirir."""
        prompt = PARSE_REQUEST_PROMPT.format(request_text=text)
        response = self._call_llm(prompt)

        if not response:
            return None

        parsed = self._parse_json_response(response)
        if isinstance(parsed, dict) and "senaryo" in parsed:
            return parsed

        return None

    # =================================================================
    # Fallback Mekanizmalari (LLM olmadan calisan)
    # =================================================================

    def _fallback_parse(self, text: str) -> dict[str, Any]:
        """
        Regex ve keyword tabanli dogal dil ayristirma.

        LLM olmadan calisir. Turkce ve Ingilizce anahtar kelimeleri
        tanir, sayilari cikarir, senaryo tipini belirler.

        Args:
            text: Kullanicinin dogal dildeki talebi

        Returns:
            Yapilandirilmis talep dict'i
        """
        text_lower = text.lower().strip()
        result = self._default_request()

        # 1. Sayi cikarma — musteri sayisi
        # Not: Önce "N hesabı" desenini tespit edip, ardından müşteri sayısını bul
        # Hesap sayısı: "2 hesabı olsun", "2 hesap olsun", "2 hesap"
        hesap_pattern = re.search(
            r"(\d+)\s*hesab[ıi]?(?:\s+olsun)?|(\d+)\s*hesap(?:\s+olsun)?",
            text_lower,
        )
        if hesap_pattern:
            val = hesap_pattern.group(1) or hesap_pattern.group(2)
            h = int(val)
            if 1 <= h <= 100:
                result["hesap_sayisi"] = h

        number_patterns = [
            r"(\d+)\s*(?:tane|adet|müşteri|musteri|kişi|kisi|kayıt|kayit|satır|satir)",
            r"(?:toplam|sayisi?|count)\s*[:=]?\s*(\d+)",
            r"^(\d+)\s",
            r"\s(\d+)$",
        ]
        for pattern in number_patterns:
            match = re.search(pattern, text_lower)
            if match:
                num = int(match.group(1))
                if 1 <= num <= 10_000_000:
                    result["musteri_sayisi"] = num
                    break

        # 2. Senaryo tipi esleme
        for keyword, scenario in sorted(
            _SCENARIO_KEYWORDS.items(), key=lambda x: len(x[0]), reverse=True,
        ):
            if keyword in text_lower:
                result["senaryo"] = scenario
                break

        # 3. Bakiye araligi cikarma
        bakiye_patterns = [
            r"(?:bakiye|balance)\s*(?:min(?:imum)?|en az)\s*[:=]?\s*([\d.,]+)",
            r"(?:min(?:imum)?)\s*bakiye\s*[:=]?\s*([\d.,]+)",
        ]
        for pattern in bakiye_patterns:
            match = re.search(pattern, text_lower)
            if match:
                val = self._parse_number(match.group(1))
                if val is not None:
                    result["min_bakiye"] = val
                break

        bakiye_max_patterns = [
            r"(?:bakiye|balance)\s*(?:max(?:imum)?|en fazla)\s*[:=]?\s*([\d.,]+)",
            r"(?:max(?:imum)?)\s*bakiye\s*[:=]?\s*([\d.,]+)",
        ]
        for pattern in bakiye_max_patterns:
            match = re.search(pattern, text_lower)
            if match:
                val = self._parse_number(match.group(1))
                if val is not None:
                    result["max_bakiye"] = val
                break

        # 4. Kredi notu araligi
        kredi_patterns = [
            r"kredi\s*(?:notu|skoru|puani)\s*(\d+)\s*(?:ustu|uzerinde|ve uzeri|'dan buyuk|\+)",
            r"kredi\s*(?:notu|skoru)\s*(?:min(?:imum)?)\s*[:=]?\s*(\d+)",
        ]
        for pattern in kredi_patterns:
            match = re.search(pattern, text_lower)
            if match:
                result["kredi_skoru_min"] = int(match.group(1))
                break

        kredi_max_patterns = [
            r"kredi\s*(?:notu|skoru|puani)\s*(\d+)\s*(?:alti|altinda)",
            r"kredi\s*(?:notu|skoru)\s*(?:max(?:imum)?)\s*[:=]?\s*(\d+)",
        ]
        for pattern in kredi_max_patterns:
            match = re.search(pattern, text_lower)
            if match:
                result["kredi_skoru_max"] = int(match.group(1))
                break

        # 5. Yas araligi
        # Önce "yaşı N olsun" / "yaş N" gibi tam eşitlik deseni
        yas_exact = re.search(r"yaş[ıi]?\s+(\d+)(?:\s+olsun)?", text_lower)
        if yas_exact:
            yas_val = int(yas_exact.group(1))
            result["yas_min"] = yas_val
            result["yas_max"] = yas_val
        else:
            yas_patterns = [
                r"(?:yaş|yas|age)\s*(?:min(?:imum)?|en az)\s*[:=]?\s*(\d+)",
                r"(\d+)\s*(?:yaş|yas|age)\s*(?:üstü|ustu|uzerinde)",
            ]
            for pattern in yas_patterns:
                match = re.search(pattern, text_lower)
                if match:
                    result["yas_min"] = int(match.group(1))
                    break

        yas_max_patterns = [
            r"(?:yaş|yas|age)\s*(?:max(?:imum)?|en fazla)\s*[:=]?\s*(\d+)",
            r"(\d+)\s*(?:yaş|yas|age)\s*(?:altı|alti|altinda)",
        ]
        for pattern in yas_max_patterns:
            match = re.search(pattern, text_lower)
            if match:
                result["yas_max"] = int(match.group(1))
                break

        # 6. Segment tespiti
        segment_keywords = {
            "bireysel": "Bireysel",
            "kobi": "KOBi",
            "ticari": "Ticari",
            "kurumsal": "Kurumsal",
            "platinum": "Platinum",
            "vip": "VIP",
        }
        for keyword, segment_val in segment_keywords.items():
            if keyword in text_lower:
                result["segment"] = segment_val
                break

        logger.info("Fallback ayristirma sonucu: %s", result)
        return result

    def _fallback_classify(
        self,
        column_name: str,
        sample_values: list[Any],
    ) -> SemanticType:
        """
        Keyword tabanli kolon siniflandirma (fallback).

        Args:
            column_name: Kolon adi
            sample_values: Ornek degerler

        Returns:
            SemanticType enum degeri
        """
        # Kolon adini normalize et
        normalized = (
            column_name.lower()
            .strip()
            .replace(" ", "_")
            .replace("-", "_")
        )

        # Dogrudan esleme
        if normalized in _COLUMN_NAME_SEMANTIC_MAP:
            type_str = _COLUMN_NAME_SEMANTIC_MAP[normalized]
            try:
                return SemanticType(type_str)
            except ValueError:
                pass

        # Alt-string esleme
        for key, type_str in _COLUMN_NAME_SEMANTIC_MAP.items():
            if key in normalized or normalized in key:
                try:
                    return SemanticType(type_str)
                except ValueError:
                    pass

        # Deger bazli sezgisel tespit
        if sample_values:
            str_vals = [str(v) for v in sample_values[:20] if v is not None]

            # TCKN deseni: 11 haneli sayi
            if all(re.match(r"^\d{11}$", v) for v in str_vals if v):
                return SemanticType.NATIONAL_ID

            # IBAN deseni: TR ile baslayan
            if all(
                re.match(r"^TR\d{24}$", v.replace(" ", ""))
                for v in str_vals if v
            ):
                return SemanticType.IBAN

            # Email deseni
            if all(re.match(r"^[^@]+@[^@]+\.[^@]+$", v) for v in str_vals if v):
                return SemanticType.EMAIL

            # Telefon deseni
            if all(
                re.match(r"^(\+90|0)?5\d{9}$", v.replace(" ", ""))
                for v in str_vals if v
            ):
                return SemanticType.PHONE

        return SemanticType.UNKNOWN

    def _fallback_suggest_rules(
        self,
        column_profiles: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Keyword tabanli kural onerisi (fallback).

        Kolon istatistiklerine gore temel kurallar olusturur.

        Args:
            column_profiles: Kolon profil bilgileri listesi

        Returns:
            Kural onerileri listesi
        """
        rules: list[dict[str, Any]] = []

        for profile in column_profiles:
            col_name = profile.get("name", "")
            dtype = profile.get("dtype", "string")
            stats = profile.get("stats", {})
            null_ratio = stats.get("null_ratio", 0.0)
            distinct_ratio = stats.get("distinct_ratio", 0.0)

            # NOT_NULL kurali
            if null_ratio < 0.01:
                rules.append({
                    "column_name": col_name,
                    "rule_type": "not_null",
                    "rule_definition": {"nullable": False},
                    "confidence": 0.90,
                    "aciklama": f"{col_name} kolonu bos deger icermemeli",
                })

            # UNIQUE kurali
            if distinct_ratio > 0.99:
                rules.append({
                    "column_name": col_name,
                    "rule_type": "unique",
                    "rule_definition": {"unique": True},
                    "confidence": 0.85,
                    "aciklama": f"{col_name} kolonu benzersiz degerler icermeli",
                })

            # RANGE kurali (sayisal)
            if dtype in ("integer", "float", "decimal"):
                min_val = stats.get("min")
                max_val = stats.get("max")
                if min_val is not None and max_val is not None:
                    rules.append({
                        "column_name": col_name,
                        "rule_type": "range",
                        "rule_definition": {
                            "min": min_val,
                            "max": max_val,
                        },
                        "confidence": 0.80,
                        "aciklama": (
                            f"{col_name} degerleri {min_val} ile {max_val} "
                            f"arasinda olmali"
                        ),
                    })

            # ENUM kurali (kategorik)
            unique_count = stats.get("unique_count", 0)
            if dtype == "string" and 2 <= unique_count <= 20:
                values = stats.get("most_common_values", [])
                if values:
                    rules.append({
                        "column_name": col_name,
                        "rule_type": "enum",
                        "rule_definition": {
                            "values": [v["value"] for v in values[:20]],
                        },
                        "confidence": 0.75,
                        "aciklama": (
                            f"{col_name} degerleri belirli bir kume icinden "
                            f"secilmeli ({unique_count} farkli deger)"
                        ),
                    })

        return rules

    def _fallback_describe(
        self,
        column_name: str,
        stats: dict[str, Any],
    ) -> str:
        """
        Basit kolon aciklamasi uretir (fallback).

        Args:
            column_name: Kolon adi
            stats: Kolon istatistikleri

        Returns:
            Turkce aciklama metni
        """
        dtype = stats.get("dtype", "bilinmiyor")
        null_ratio = stats.get("null_ratio", 0)
        unique_count = stats.get("unique_count", 0)

        parts: list[str] = [f"'{column_name}' kolonu ({dtype} tipinde)"]

        if unique_count:
            parts.append(f"{unique_count} benzersiz deger iceriyor")

        if null_ratio > 0:
            parts.append(f"%{null_ratio * 100:.1f} bos deger oranina sahip")

        min_val = stats.get("min")
        max_val = stats.get("max")
        if min_val is not None and max_val is not None:
            parts.append(f"deger araligi: {min_val} — {max_val}")

        return ", ".join(parts) + "."

    # =================================================================
    # Yardimci Metodlar
    # =================================================================

    @staticmethod
    def _default_request() -> dict[str, Any]:
        """Varsayilan talep yapisini dondurur."""
        return {
            "senaryo": "bireysel",
            "musteri_sayisi": 1000,
            "min_bakiye": None,
            "max_bakiye": None,
            "kredi_skoru_min": None,
            "kredi_skoru_max": None,
            "segment": None,
            "yas_min": None,
            "yas_max": None,
            "hesap_sayisi": None,
            "ozel_kurallar": {},
        }

    @staticmethod
    def _parse_number(text: str) -> Optional[float]:
        """
        Metin icerisindeki sayiyi cikarir.

        Turk sayı formatini da destekler (1.000.000,50 → 1000000.50).

        Args:
            text: Sayi iceren metin

        Returns:
            float degeri veya None
        """
        if not text:
            return None

        cleaned = text.strip()

        # Turk formati: 1.000.000,50
        if "," in cleaned and "." in cleaned:
            cleaned = cleaned.replace(".", "").replace(",", ".")
        elif "," in cleaned:
            cleaned = cleaned.replace(",", ".")

        # Sadece sayi olmayan karakterleri temizle
        cleaned = re.sub(r"[^\d.]", "", cleaned)

        try:
            return float(cleaned)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _parse_json_response(response: str) -> Any:
        """
        LLM yanitindan JSON cikarir.

        Yanit icerisindeki JSON blogunu bulur ve parse eder.
        Markdown code fence'lerini de destekler.

        Args:
            response: LLM yanit metni

        Returns:
            Parse edilmis JSON nesnesi veya None
        """
        if not response:
            return None

        text = response.strip()

        # Markdown code fence temizligi
        if text.startswith("```"):
            # ```json ... ``` veya ``` ... ```
            lines = text.split("\n")
            start_idx = 1 if lines[0].startswith("```") else 0
            end_idx = len(lines) - 1
            if lines[-1].strip() == "```":
                end_idx = len(lines) - 1
            text = "\n".join(lines[start_idx:end_idx])

        # JSON blogu bul ([ veya { ile baslayan)
        json_match = re.search(r"[\[{].*[\]}]", text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass

        # Dogrudan parse dene
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            logger.debug("JSON parse hatasi: %s", text[:200])
            return None

    # -- Provider Bilgisi ---------------------------------------------

    @property
    def provider(self) -> LLMProvider:
        """Aktif LLM provider'i dondurur."""
        return self._provider

    @property
    def is_llm_available(self) -> bool:
        """LLM erisimi var mi kontrol eder."""
        return self._provider != LLMProvider.FALLBACK

    def get_status(self) -> dict[str, Any]:
        """
        Servis durum bilgisini dondurur.

        Returns:
            Durum bilgisi dict'i
        """
        return {
            "provider": self._provider.value,
            "model": self._model or "N/A",
            "llm_available": self.is_llm_available,
            "endpoint": self._endpoint or "N/A",
            "temperature": self._temperature,
            "max_tokens": self._max_tokens,
        }
