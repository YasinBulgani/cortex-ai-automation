"""
Ollama LLM client — pipeline agent'ları için lokal LLM.

Ollama lokal makinede koşar (http://localhost:11434), token gerekmez.
HFClient ile aynı interface (chat, achat, HFResponse).

Model tier mapping (projedeki mevcut modellere göre):
    fast      → llama3.1:8b           (hızlı, 4.9 GB)
    balanced  → qwen2.5:14b           (denge, 9 GB)
    powerful  → qwen2.5:32b           (en güçlü, 19 GB)
    coder     → qwen2.5-coder:7b      (kod odaklı, 4.7 GB)

Env:
    OLLAMA_HOST              http://localhost:11434 (default)
    OLLAMA_DEFAULT_MODEL     qwen2.5:14b (default)
    OLLAMA_POWERFUL_MODEL    qwen2.5:32b
    OLLAMA_FAST_MODEL        llama3.1:8b
    OLLAMA_CODER_MODEL       qwen2.5-coder:7b
    OLLAMA_TIMEOUT_S         180 (default — lokal LLM yavaş olabilir)
    OLLAMA_KEEP_ALIVE        -1 (bellekte tut; 0=anında boşalt; "5m"=5dk)
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


# Rol bazlı tier mapping (hf_client ile aynı)
ROLE_MODEL_TIER = {
    # Hızlı
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
    # Güçlü (kritik karar)
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
class OllamaConfig:
    """Ollama client konfigürasyonu."""

    host: str = "http://localhost:11434"
    default_model: str = "qwen2.5:14b"
    powerful_model: str = "qwen2.5:32b"
    fast_model: str = "llama3.1:8b"
    coder_model: str = "qwen2.5-coder:7b"
    timeout_s: int = 180
    max_retries: int = 3
    base_backoff_s: float = 2.0
    keep_alive: str = "-1"  # bellekte tut

    @classmethod
    def from_env(cls) -> "OllamaConfig":
        return cls(
            host=os.getenv("OLLAMA_HOST", cls.host).rstrip("/"),
            default_model=os.getenv("OLLAMA_DEFAULT_MODEL", cls.default_model),
            powerful_model=os.getenv("OLLAMA_POWERFUL_MODEL", cls.powerful_model),
            fast_model=os.getenv("OLLAMA_FAST_MODEL", cls.fast_model),
            coder_model=os.getenv("OLLAMA_CODER_MODEL", cls.coder_model),
            timeout_s=int(os.getenv("OLLAMA_TIMEOUT_S", "180")),
            max_retries=int(os.getenv("OLLAMA_MAX_RETRIES", "3")),
            base_backoff_s=float(os.getenv("OLLAMA_BACKOFF_S", "2.0")),
            keep_alive=os.getenv("OLLAMA_KEEP_ALIVE", "-1"),
        )

    def pick_model(self, role: Optional[str] = None, tier: Optional[str] = None) -> str:
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
class OllamaResponse:
    """Agent yanıtı — HFResponse ile aynı şekil."""

    content: str
    model: str
    role: Optional[str] = None
    tokens_used: Optional[int] = None
    latency_s: Optional[float] = None
    raw: Any = None
    parsed_json: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```", re.DOTALL)
_JSON_OBJ_RE = re.compile(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", re.DOTALL)


def _extract_json(text: str) -> Optional[Dict[str, Any]]:
    """Model yanıtından JSON bloğu çıkar."""
    if not text:
        return None
    m = _JSON_FENCE_RE.search(text)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    stripped = text.strip()
    if stripped.startswith("{") or stripped.startswith("["):
        try:
            return json.loads(stripped)
        except json.JSONDecodeError:
            pass
    m = _JSON_OBJ_RE.search(text)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            pass
    return None


class OllamaClient:
    """Ollama HTTP client (sync + async)."""

    def __init__(self, config: Optional[OllamaConfig] = None):
        self.config = config or OllamaConfig.from_env()

    # ─── sync ────────────────────────────────────────────────────────────────
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
    ) -> OllamaResponse:
        try:
            import requests  # type: ignore
        except ImportError as e:
            raise RuntimeError("requests required. pip install requests") from e

        chosen_model = model or self.config.pick_model(role=role, tier=tier)
        url = f"{self.config.host}/api/chat"
        # Ollama keep_alive: int (-1 = sonsuza kadar, 0 = hemen boşalt) veya duration string ("5m", "1h")
        ka_raw = self.config.keep_alive
        keep_alive: Any
        if ka_raw in ("-1", "0") or (isinstance(ka_raw, str) and ka_raw.lstrip("-").isdigit()):
            keep_alive = int(ka_raw)
        else:
            keep_alive = ka_raw  # "5m", "1h" gibi
        payload = {
            "model": chosen_model,
            "messages": messages,
            "stream": False,
            "keep_alive": keep_alive,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }
        if stop:
            payload["options"]["stop"] = stop

        attempt = 0
        start = time.time()
        last_err: Optional[Exception] = None
        while attempt < self.config.max_retries:
            try:
                r = requests.post(url, json=payload, timeout=self.config.timeout_s)
                r.raise_for_status()
                data = r.json()
                content = (data.get("message") or {}).get("content", "") or ""
                latency = time.time() - start
                resp = OllamaResponse(
                    content=content,
                    model=chosen_model,
                    role=role,
                    latency_s=latency,
                    raw=data,
                    tokens_used=data.get("eval_count"),
                )
                if parse_json:
                    resp.parsed_json = _extract_json(content)
                logger.info(
                    "Ollama chat ok role=%s model=%s latency=%.2fs tokens=%s",
                    role, chosen_model, latency, resp.tokens_used,
                )
                return resp
            except Exception as e:
                last_err = e
                attempt += 1
                backoff = self.config.base_backoff_s * (2 ** (attempt - 1))
                logger.warning(
                    "Ollama chat attempt %d/%d failed (%s); retry in %.1fs",
                    attempt, self.config.max_retries, type(e).__name__, backoff,
                )
                if attempt < self.config.max_retries:
                    time.sleep(backoff)
        raise RuntimeError(
            f"Ollama chat failed after {self.config.max_retries} attempts: {last_err}"
        )

    # ─── async ───────────────────────────────────────────────────────────────
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
    ) -> OllamaResponse:
        # Non-blocking thread executor (requests is sync)
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.chat(
                messages=messages, role=role, model=model, tier=tier,
                max_tokens=max_tokens, temperature=temperature,
                parse_json=parse_json, stop=stop,
            ),
        )


def ping() -> Dict[str, Any]:
    """Ollama reachable + model listesi."""
    try:
        import requests  # type: ignore
    except ImportError:
        return {"error": "requests package not installed"}

    cfg = OllamaConfig.from_env()
    status: Dict[str, Any] = {
        "host": cfg.host,
        "default_model": cfg.default_model,
        "powerful_model": cfg.powerful_model,
        "fast_model": cfg.fast_model,
        "coder_model": cfg.coder_model,
    }
    try:
        r = requests.get(f"{cfg.host}/api/version", timeout=3)
        r.raise_for_status()
        status["reachable"] = True
        status["version"] = r.json().get("version")
    except Exception as e:
        status["reachable"] = False
        status["error"] = f"not reachable: {e}"
        return status

    try:
        r = requests.get(f"{cfg.host}/api/tags", timeout=5)
        r.raise_for_status()
        models = [m["name"] for m in r.json().get("models", [])]
        status["installed_models"] = models
        # Hangi tier modelleri mevcut?
        tier_available = {
            "fast": cfg.fast_model in models,
            "balanced": cfg.default_model in models,
            "powerful": cfg.powerful_model in models,
            "coder": cfg.coder_model in models,
        }
        status["tier_available"] = tier_available
        status["tier_missing"] = [t for t, v in tier_available.items() if not v]

        # Quick chat test
        if cfg.fast_model in models:
            client = OllamaClient(cfg)
            try:
                resp = client.chat(
                    messages=[{"role": "user", "content": "Reply with just the word: pong"}],
                    tier="fast",
                    max_tokens=20,
                    temperature=0.0,
                )
                status["sample"] = resp.content[:100]
                status["sample_latency_s"] = resp.latency_s
            except Exception as e:
                status["sample_error"] = str(e)[:200]
    except Exception as e:
        status["models_error"] = str(e)[:200]

    return status


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    print(json.dumps(ping(), indent=2, default=str))
