"""
AI Client - LLM entegrasyonu (multi-provider).

Providers:
    - ollama (VARSAYILAN) — lokal LLM, token gerekmez, en hızlı
    - huggingface — cloud, ücretsiz tier
    - openai/anthropic — backward compat via services.llm_gateway

Env:
    LLM_PROVIDER           = ollama | huggingface | openai | anthropic  (default: ollama)
    OLLAMA_HOST            = http://localhost:11434
    OLLAMA_DEFAULT_MODEL   = qwen2.5:14b (default)
    HF_TOKEN               = HuggingFace read token
    HF_DEFAULT_MODEL       = HF model slug
    OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL  — legacy
    ANTHROPIC_API_KEY       — legacy
"""
import json
import logging
import os
import threading as _threading
from typing import Any, Dict, List, Optional

from config.settings import settings

logger = logging.getLogger(__name__)


class AIClient:
    """Multi-provider AI client. Varsayılan: Ollama (lokal)."""

    def __init__(self, provider: Optional[str] = None):
        """AI Client'i başlat."""
        self.provider = (
            provider
            or os.getenv("LLM_PROVIDER")
            or getattr(settings, "LLM_PROVIDER", None)
            or "ollama"
        ).lower()

        # Backward-compat field'lar (OpenAI)
        self.api_key = settings.OPENAI_API_KEY
        self.base_url = settings.OPENAI_BASE_URL
        self.model = settings.OPENAI_MODEL

        # Ollama config (varsayılan)
        self.ollama_host = (
            os.getenv("OLLAMA_HOST")
            or getattr(settings, "OLLAMA_HOST", "http://localhost:11434")
        ).rstrip("/")
        self.ollama_model = (
            os.getenv("OLLAMA_DEFAULT_MODEL")
            or getattr(settings, "OLLAMA_DEFAULT_MODEL", "qwen2.5:14b")
        )
        self.ollama_keep_alive = (
            os.getenv("OLLAMA_KEEP_ALIVE")
            or getattr(settings, "OLLAMA_KEEP_ALIVE", "-1")
        )

        # HF config (alternatif)
        self.hf_token = (
            os.getenv("HF_TOKEN")
            or os.getenv("HUGGINGFACE_TOKEN")
            or getattr(settings, "HF_TOKEN", "")
        )
        self.hf_model = (
            os.getenv("HF_DEFAULT_MODEL")
            or getattr(settings, "HF_DEFAULT_MODEL", "mistralai/Mistral-7B-Instruct-v0.3")
        )

        self._hf_client = None  # lazy

    # ── HuggingFace ───────────────────────────────────────────────────────────
    def _get_hf_client(self):
        if self._hf_client is not None:
            return self._hf_client
        try:
            from huggingface_hub import InferenceClient  # type: ignore
        except ImportError as e:
            raise RuntimeError(
                "huggingface_hub not installed. Run: pip install huggingface_hub"
            ) from e
        if not self.hf_token:
            logger.warning(
                "HF_TOKEN not set. Get one at https://huggingface.co/settings/tokens"
            )
        self._hf_client = InferenceClient(token=self.hf_token, timeout=120)
        return self._hf_client

    def _complete_hf(self, prompt: str, max_tokens: int, temperature: float) -> str:
        client = self._get_hf_client()
        try:
            resp = client.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                model=self.hf_model,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            return resp.choices[0].message.content or ""
        except Exception as e:
            logger.error("HF completion failed: %s", e)
            return f"Error: {e}"

    # ── Ollama (VARSAYILAN) ──────────────────────────────────────────────────
    def _ollama_keep_alive(self):
        ka = self.ollama_keep_alive
        if ka in ("-1", "0") or (isinstance(ka, str) and ka.lstrip("-").isdigit()):
            return int(ka)
        return ka

    def _complete_ollama(self, prompt: str, max_tokens: int, temperature: float) -> str:
        try:
            import requests  # type: ignore
        except ImportError as e:
            raise RuntimeError("requests required. pip install requests") from e
        url = f"{self.ollama_host}/api/chat"
        payload = {
            "model": self.ollama_model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "keep_alive": self._ollama_keep_alive(),
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        try:
            r = requests.post(url, json=payload, timeout=180)
            r.raise_for_status()
            data = r.json()
            return (data.get("message") or {}).get("content", "") or ""
        except Exception as e:
            logger.error("Ollama completion failed: %s", e)
            return f"Error: {e}"

    # ── OpenAI (legacy) ──────────────────────────────────────────────────────
    def _complete_openai(self, prompt: str, max_tokens: int, temperature: float) -> str:
        try:
            from services import get_llm_gateway

            response = get_llm_gateway().complete(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature,
            )
            return response.content or ""
        except Exception as e:
            logger.error("OpenAI completion failed: %s", e)
            return f"Error: {e}"

    # ── Public API ───────────────────────────────────────────────────────────
    def complete(self, prompt: str, max_tokens: int = 2000, temperature: float = 0.7) -> str:
        """Text completion request gönder (provider'a göre yönlendirilir)."""
        if self.provider == "ollama":
            return self._complete_ollama(prompt, max_tokens, temperature)
        if self.provider == "huggingface":
            return self._complete_hf(prompt, max_tokens, temperature)
        if self.provider == "openai":
            return self._complete_openai(prompt, max_tokens, temperature)
        if self.provider == "anthropic":
            return f"Error: anthropic provider not yet implemented"
        return f"Error: unknown LLM_PROVIDER={self.provider}"

    def chat(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 2000,
        temperature: float = 0.3,
        model: Optional[str] = None,
    ) -> str:
        """Multi-turn chat."""
        if self.provider == "ollama":
            try:
                import requests  # type: ignore
            except ImportError as e:
                raise RuntimeError("requests required. pip install requests") from e
            url = f"{self.ollama_host}/api/chat"
            payload = {
                "model": model or self.ollama_model,
                "messages": messages,
                "stream": False,
                "keep_alive": self._ollama_keep_alive(),
                "options": {"temperature": temperature, "num_predict": max_tokens},
            }
            try:
                r = requests.post(url, json=payload, timeout=180)
                r.raise_for_status()
                data = r.json()
                return (data.get("message") or {}).get("content", "") or ""
            except Exception as e:
                logger.error("Ollama chat failed: %s", e)
                return f"Error: {e}"
        if self.provider == "huggingface":
            client = self._get_hf_client()
            resp = client.chat_completion(
                messages=messages,
                model=model or self.hf_model,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            return resp.choices[0].message.content or ""
        if self.provider == "openai":
            try:
                from services import get_llm_gateway

                resp = get_llm_gateway().complete(
                    model=model or self.model,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
                return resp.content or ""
            except Exception as e:
                logger.error("OpenAI chat failed: %s", e)
                return f"Error: {e}"
        return self.complete(messages[-1]["content"] if messages else "", max_tokens, temperature)

    def analyze_text(self, text: str) -> dict:
        """Metni analiz et (NLP)."""
        prompt = f"""Aşağıdaki metni analiz et ve JSON formatında döndür:
"{text}"

Analiz et:
1. Ana tema/amaç
2. Anahtar noktalar (bullet points)
3. Duygu analizi (positive/negative/neutral)
4. Yazım hatası ve öneriler

JSON formatında döndür.
"""
        result_text = self.complete(prompt)
        try:
            return json.loads(result_text)
        except Exception:
            return {"raw": result_text}

    def ping(self) -> Dict[str, Any]:
        """Sanity check."""
        status: Dict[str, Any] = {"provider": self.provider}
        if self.provider == "ollama":
            status["host"] = self.ollama_host
            status["model"] = self.ollama_model
        elif self.provider == "huggingface":
            status["token_set"] = bool(self.hf_token)
            status["model"] = self.hf_model
            if not self.hf_token:
                status["error"] = "HF_TOKEN missing"
                return status
        try:
            r = self.complete("Reply just: pong", max_tokens=10, temperature=0.0)
            status["reachable"] = True
            status["sample"] = r[:100]
        except Exception as e:
            status["reachable"] = False
            status["error"] = str(e)[:300]
        return status


# Thread-safe singleton
_ai_client = None
_ai_client_lock = _threading.Lock()


def get_ai_client() -> AIClient:
    """Global AI Client instance'ını thread-safe olarak al."""
    global _ai_client
    if _ai_client is None:
        with _ai_client_lock:
            if _ai_client is None:
                _ai_client = AIClient()
    return _ai_client


def reset_ai_client() -> None:
    """Singleton'ı reset (env değiştiğinde)."""
    global _ai_client
    with _ai_client_lock:
        _ai_client = None
