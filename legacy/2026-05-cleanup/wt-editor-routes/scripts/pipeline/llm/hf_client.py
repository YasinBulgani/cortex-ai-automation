"""
HuggingFace LLM client — pipeline agent'ları için.

Proje genelinde tek LLM sağlayıcısı HuggingFace Inference API (Serverless).
Ücretsiz katman yeterli (`https://huggingface.co/welcome` → token oluştur).

Özellikler:
    - huggingface_hub.InferenceClient tabanlı
    - Rol bazlı model seçimi (fast/balanced/powerful)
    - Token rate-limit retry (exponential backoff)
    - JSON çıktı parse (agent yanıtlarını yapılandırmak için)
    - Async + sync API
    - Trace/log (stage.sh ile uyumlu)

Env:
    HF_TOKEN            - read token (zorunlu, https://huggingface.co/settings/tokens)
    HF_DEFAULT_MODEL    - default model (default: mistralai/Mistral-7B-Instruct-v0.3)
    HF_POWERFUL_MODEL   - yüksek güç (default: meta-llama/Meta-Llama-3-70B-Instruct)
    HF_FAST_MODEL       - hızlı (default: Qwen/Qwen2.5-7B-Instruct)
    HF_CODER_MODEL      - kod üretimi (default: Qwen/Qwen2.5-Coder-7B-Instruct)
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════════════════════════

# Model tier mapping — rol bazlı seçim için
ROLE_MODEL_TIER = {
    # Hızlı / hafif
    "analyzer": "fast",
    "validator": "fast",
    "intake_triage": "fast",
    "dependency_watchdog": "fast",
    "conflict_resolver": "fast",
    "release_manager": "fast",
    "observer": "fast",
    # Dengeli
    "proposer": "balanced",
    "approver": "balanced",
    "product_validator": "balanced",
    "designer": "balanced",
    "code_reviewer": "balanced",
    "knowledge_curator": "balanced",
    "retrospective": "balanced",
    "a11y_auditor": "balanced",
    "performance_tester": "balanced",
    # Güçlü (kritik karar / üretim)
    "architect": "powerful",
    "security_reviewer": "powerful",
    "qa": "powerful",
    "integrator": "powerful",
    "promoter": "powerful",
    # Kod odaklı
    "frontend": "coder",
    "backend": "coder",
    "data_engineer": "coder",
    "devops": "coder",
}


@dataclass
class HFConfig:
    """HF client konfigürasyonu."""

    token: Optional[str] = None
    default_model: str = "mistralai/Mistral-7B-Instruct-v0.3"
    powerful_model: str = "meta-llama/Meta-Llama-3-70B-Instruct"
    fast_model: str = "Qwen/Qwen2.5-7B-Instruct"
    coder_model: str = "Qwen/Qwen2.5-Coder-7B-Instruct"
    timeout_s: int = 120
    max_retries: int = 3
    base_backoff_s: float = 2.0

    @classmethod
    def from_env(cls) -> "HFConfig":
        return cls(
            token=os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_TOKEN"),
            default_model=os.getenv("HF_DEFAULT_MODEL", cls.default_model),
            powerful_model=os.getenv("HF_POWERFUL_MODEL", cls.powerful_model),
            fast_model=os.getenv("HF_FAST_MODEL", cls.fast_model),
            coder_model=os.getenv("HF_CODER_MODEL", cls.coder_model),
            timeout_s=int(os.getenv("HF_TIMEOUT_S", "120")),
            max_retries=int(os.getenv("HF_MAX_RETRIES", "3")),
            base_backoff_s=float(os.getenv("HF_BACKOFF_S", "2.0")),
        )

    def pick_model(self, role: Optional[str] = None, tier: Optional[str] = None) -> str:
        """Rol veya tier'a göre model seç."""
        if tier is None and role is not None:
            tier = ROLE_MODEL_TIER.get(role, "balanced")
        if tier == "powerful":
            return self.powerful_model
        if tier == "fast":
            return self.fast_model
        if tier == "coder":
            return self.coder_model
        return self.default_model


@dataclass
class HFResponse:
    """Agent yanıtı."""

    content: str
    model: str
    role: Optional[str] = None
    tokens_used: Optional[int] = None
    latency_s: Optional[float] = None
    raw: Any = None
    parsed_json: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


# ═══════════════════════════════════════════════════════════════════════════════
# CLIENT
# ═══════════════════════════════════════════════════════════════════════════════


class HFClient:
    """Synchronous + async HuggingFace Inference client."""

    def __init__(self, config: Optional[HFConfig] = None):
        self.config = config or HFConfig.from_env()
        self._client = None  # lazy import
        self._async_client = None

    # ── Lazy imports (huggingface_hub opsiyonel) ──────────────────────────────
    def _ensure_client(self):
        if self._client is not None:
            return self._client
        try:
            from huggingface_hub import InferenceClient  # type: ignore
        except ImportError as e:
            raise RuntimeError(
                "huggingface_hub not installed. Run: pip install huggingface_hub"
            ) from e
        if not self.config.token:
            logger.warning(
                "HF_TOKEN not set. Get one: https://huggingface.co/settings/tokens"
            )
        self._client = InferenceClient(
            token=self.config.token,
            timeout=self.config.timeout_s,
        )
        return self._client

    def _ensure_async_client(self):
        if self._async_client is not None:
            return self._async_client
        try:
            from huggingface_hub import AsyncInferenceClient  # type: ignore
        except ImportError as e:
            raise RuntimeError(
                "huggingface_hub not installed. Run: pip install huggingface_hub"
            ) from e
        self._async_client = AsyncInferenceClient(
            token=self.config.token,
            timeout=self.config.timeout_s,
        )
        return self._async_client

    # ── Sync API ──────────────────────────────────────────────────────────────
    def chat(
        self,
        messages: List[Dict[str, str]],
        role: Optional[str] = None,
        model: Optional[str] = None,
        tier: Optional[str] = None,
        max_tokens: int = 2000,
        temperature: float = 0.3,
        parse_json: bool = False,
        stop: Optional[List[str]] = None,
    ) -> HFResponse:
        """Chat completion."""
        client = self._ensure_client()
        chosen_model = model or self.config.pick_model(role=role, tier=tier)

        attempt = 0
        start = time.time()
        last_err: Optional[Exception] = None
        while attempt < self.config.max_retries:
            try:
                raw = client.chat_completion(
                    messages=messages,
                    model=chosen_model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    stop=stop,
                )
                content = raw.choices[0].message.content or ""
                latency = time.time() - start
                resp = HFResponse(
                    content=content,
                    model=chosen_model,
                    role=role,
                    latency_s=latency,
                    raw=raw,
                )
                if parse_json:
                    resp.parsed_json = _extract_json(content)
                if hasattr(raw, "usage") and raw.usage:
                    resp.tokens_used = getattr(raw.usage, "total_tokens", None)
                logger.info(
                    "HF chat ok role=%s model=%s latency=%.2fs tokens=%s",
                    role, chosen_model, latency, resp.tokens_used,
                )
                return resp
            except Exception as e:
                last_err = e
                attempt += 1
                backoff = self.config.base_backoff_s * (2 ** (attempt - 1))
                logger.warning(
                    "HF chat attempt %d/%d failed (%s); retry in %.1fs",
                    attempt, self.config.max_retries, type(e).__name__, backoff,
                )
                if attempt < self.config.max_retries:
                    time.sleep(backoff)
        raise RuntimeError(
            f"HF chat failed after {self.config.max_retries} attempts: {last_err}"
        )

    # ── Async API ─────────────────────────────────────────────────────────────
    async def achat(
        self,
        messages: List[Dict[str, str]],
        role: Optional[str] = None,
        model: Optional[str] = None,
        tier: Optional[str] = None,
        max_tokens: int = 2000,
        temperature: float = 0.3,
        parse_json: bool = False,
        stop: Optional[List[str]] = None,
    ) -> HFResponse:
        """Async chat completion."""
        client = self._ensure_async_client()
        chosen_model = model or self.config.pick_model(role=role, tier=tier)

        attempt = 0
        start = time.time()
        last_err: Optional[Exception] = None
        while attempt < self.config.max_retries:
            try:
                raw = await client.chat_completion(
                    messages=messages,
                    model=chosen_model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    stop=stop,
                )
                content = raw.choices[0].message.content or ""
                latency = time.time() - start
                resp = HFResponse(
                    content=content,
                    model=chosen_model,
                    role=role,
                    latency_s=latency,
                    raw=raw,
                )
                if parse_json:
                    resp.parsed_json = _extract_json(content)
                if hasattr(raw, "usage") and raw.usage:
                    resp.tokens_used = getattr(raw.usage, "total_tokens", None)
                return resp
            except Exception as e:
                last_err = e
                attempt += 1
                backoff = self.config.base_backoff_s * (2 ** (attempt - 1))
                logger.warning(
                    "HF achat attempt %d/%d failed (%s); retry in %.1fs",
                    attempt, self.config.max_retries, type(e).__name__, backoff,
                )
                if attempt < self.config.max_retries:
                    await asyncio.sleep(backoff)
        raise RuntimeError(
            f"HF achat failed after {self.config.max_retries} attempts: {last_err}"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# UTILS
# ═══════════════════════════════════════════════════════════════════════════════

_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```", re.DOTALL)
_JSON_OBJ_RE = re.compile(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", re.DOTALL)


def _extract_json(text: str) -> Optional[Dict[str, Any]]:
    """Model yanıtından JSON bloğu çıkar."""
    if not text:
        return None
    # 1. Fenced JSON block
    m = _JSON_FENCE_RE.search(text)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    # 2. Try to parse whole text
    stripped = text.strip()
    if stripped.startswith("{") or stripped.startswith("["):
        try:
            return json.loads(stripped)
        except json.JSONDecodeError:
            pass
    # 3. Find outermost {...}
    m = _JSON_OBJ_RE.search(text)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            pass
    return None


# ═══════════════════════════════════════════════════════════════════════════════
# MODULE-LEVEL CONVENIENCE
# ═══════════════════════════════════════════════════════════════════════════════

_default_client: Optional[HFClient] = None


def get_client() -> HFClient:
    """Shared client getter."""
    global _default_client
    if _default_client is None:
        _default_client = HFClient()
    return _default_client


def ping() -> Dict[str, Any]:
    """Sanity check — token var mı, model erişilebilir mi?"""
    cfg = HFConfig.from_env()
    status: Dict[str, Any] = {
        "token_set": bool(cfg.token),
        "default_model": cfg.default_model,
        "powerful_model": cfg.powerful_model,
        "fast_model": cfg.fast_model,
        "coder_model": cfg.coder_model,
    }
    if not cfg.token:
        status["error"] = (
            "HF_TOKEN not set. Create a read token: "
            "https://huggingface.co/settings/tokens"
        )
        return status
    try:
        client = get_client()
        resp = client.chat(
            messages=[{"role": "user", "content": "ping"}],
            tier="fast",
            max_tokens=10,
        )
        status["reachable"] = True
        status["sample"] = resp.content[:100]
        status["latency_s"] = resp.latency_s
    except Exception as e:
        status["reachable"] = False
        status["error"] = str(e)[:300]
    return status


if __name__ == "__main__":
    import json as _json
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    print(_json.dumps(ping(), indent=2))
