"""
Agent Trio – Cortex AI için 3-Ajan Otonom Sistemi
==================================================
• IdeaAgent   → Yeni özellik/modül fikirleri üretir
• DevAgent    → Fikri Python/TS koduna dönüştürür
• TestAgent   → Kodu inceler, test yazar, rapor verir
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import AsyncIterator, Optional

import httpx

logger = logging.getLogger("agent_trio")

# ── Ollama Bağlantısı ──────────────────────────────────────────────────────
OLLAMA_BASE = "http://localhost:11434/api"

# Model öncelikleri (Cortex config ile uyumlu)
_MODEL_PRIORITY = [
    "qwen2.5:32b",
    "qwen2.5-coder:7b",
    "mistral:latest",
    "llama3.2:latest",
    "llama3:latest",
    "phi3:latest",
    "gemma2:latest",
]

_available_models: list[str] = []
_default_model: Optional[str] = None


async def _detect_models() -> list[str]:
    """Ollama'da yüklü modelleri tespit et."""
    global _available_models, _default_model
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get("http://localhost:11434/api/tags")
            if resp.status_code == 200:
                data = resp.json()
                names = [m["name"] for m in data.get("models", [])]
                _available_models = names
                # Öncelikli modeli seç
                for priority in _MODEL_PRIORITY:
                    for name in names:
                        if priority in name:
                            _default_model = name
                            return names
                # Hiçbiri yoksa ilkini al
                if names:
                    _default_model = names[0]
                return names
    except Exception as e:
        logger.warning(f"Ollama model tespiti başarısız: {e}")
    return []


def _pick_model(preferred: Optional[str] = None) -> str:
    if preferred and any(preferred in m for m in _available_models):
        for m in _available_models:
            if preferred in m:
                return m
    return _default_model or "mistral:latest"


async def _ollama_chat(
    model: str,
    messages: list[dict],
    temperature: float = 0.7,
    max_tokens: int = 2000,
) -> AsyncIterator[str]:
    """Ollama streaming chat – her chunk'u yield eder."""
    payload = {
        "model": model,
        "messages": messages,
        "stream": True,
        "options": {
            "temperature": temperature,
            "num_predict": max_tokens,
        },
    }
    async with httpx.AsyncClient(timeout=120) as client:
        async with client.stream("POST", f"{OLLAMA_BASE}/chat", json=payload) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line.strip():
                    continue
                try:
                    chunk = json.loads(line)
                    content = chunk.get("message", {}).get("content", "")
                    if content:
                        yield content
                    if chunk.get("done"):
                        break
                except json.JSONDecodeError:
                    continue


# ── Veri Yapıları ──────────────────────────────────────────────────────────

@dataclass
class Idea:
    title: str
    description: str
    module: str
    complexity: str  # "low" | "medium" | "high"
    tags: list[str] = field(default_factory=list)
    round_num: int = 0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class Implementation:
    idea: Idea
    code: str
    language: str
    file_path: str
    explanation: str
    round_num: int = 0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class TestReport:
    implementation: Implementation
    test_code: str
    bugs_found: list[str]
    improvements: list[str]
    coverage_estimate: int  # 0-100
    verdict: str  # "pass" | "fail" | "needs_work"
    round_num: int = 0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


# ── Ajan Sınıfları ────────────────────────────────────────────────────────


class IdeaAgent:
    """Cortex AI platformu için yaratıcı özellik fikirleri üretir."""

    NAME = "💡 Fikir Ajanı"
    SYSTEM_PROMPT = """Sen Cortex AI Automation platformu için yaratıcı bir ürün tasarımcısısın.
Cortex platformu: AI destekli test otomasyonu, sentetik veri üretimi, DSL yorumlama,
agent orchestration, quality assurance ve banking compliance modülleri içeriyor.

Görevin: Her seferinde yenilikçi, uygulanabilir ve gerçekten faydalı bir özellik/modül fikri üret.
Fikirler Türk fintech/bankacılık sektörüne odaklı olsun.

SADECE JSON formatında yanıt ver:
{
  "title": "özellik adı",
  "description": "150-200 kelimelik detaylı açıklama",
  "module": "backend domain adı (örn: fraud_detection)",
  "complexity": "low|medium|high",
  "tags": ["tag1", "tag2", "tag3"],
  "user_story": "kullanıcı hikayesi",
  "acceptance_criteria": ["kriter1", "kriter2"]
}"""

    def __init__(self):
        self.model = _pick_model("qwen2.5")
        self.history: list[dict] = []
        self._previous_ideas: list[str] = []

    async def generate(self, round_num: int, event_queue: asyncio.Queue) -> Idea:
        prev = ", ".join(self._previous_ideas[-5:]) if self._previous_ideas else "henüz yok"
        
        user_msg = f"""Round {round_num} için yeni bir fikir üret.
Daha önce üretilen fikirler (tekrar etme): {prev}

Aşağıdaki kategorilerden birini seç:
- AI/ML model entegrasyonu
- Güvenlik ve compliance
- Test otomasyon geliştirmesi
- Analitik dashboard
- Kullanıcı deneyimi
- Performans optimizasyonu
- Yeni API entegrasyonu

JSON formatında yanıtla."""

        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            *self.history[-4:],
            {"role": "user", "content": user_msg},
        ]

        await event_queue.put({
            "type": "agent_thinking",
            "agent": self.NAME,
            "round": round_num,
            "message": "Yeni özellik fikri üretiliyor...",
        })

        full_response = ""
        async for chunk in _ollama_chat(self.model, messages, temperature=0.9, max_tokens=800):
            full_response += chunk
            await event_queue.put({
                "type": "agent_streaming",
                "agent": self.NAME,
                "round": round_num,
                "chunk": chunk,
            })

        self.history.append({"role": "user", "content": user_msg})
        self.history.append({"role": "assistant", "content": full_response})

        # JSON parse
        idea_data = _extract_json(full_response)
        title = idea_data.get("title", f"Özellik #{round_num}")
        self._previous_ideas.append(title)

        idea = Idea(
            title=title,
            description=idea_data.get("description", full_response[:300]),
            module=idea_data.get("module", "unknown"),
            complexity=idea_data.get("complexity", "medium"),
            tags=idea_data.get("tags", []),
            round_num=round_num,
        )

        await event_queue.put({
            "type": "idea_complete",
            "agent": self.NAME,
            "round": round_num,
            "idea": {
                "title": idea.title,
                "description": idea.description,
                "module": idea.module,
                "complexity": idea.complexity,
                "tags": idea.tags,
            },
        })
        return idea


class DevAgent:
    """Fikri gerçek kod olarak implement eder."""

    NAME = "💻 Geliştirici Ajanı"
    SYSTEM_PROMPT = """Sen Cortex AI Automation platformu için senior bir Python/TypeScript geliştiricisisin.
Stack: FastAPI, SQLAlchemy, Pydantic, Next.js, TypeScript, Playwright, Redis, PostgreSQL.

Görevin: Verilen özellik fikrini gerçekten çalışan, production-ready kod olarak implement et.
• FastAPI route + Pydantic schema + SQLAlchemy model yapısını kullan
• Type hints kullan
• Docstring ekle
• Error handling yap
• Güvenlik best practice'lerini uygula

SADECE JSON formatında yanıt ver:
{
  "language": "python|typescript",
  "file_path": "backend/app/domains/{module}/router.py",
  "code": "...tam kod buraya...",
  "explanation": "implementasyon açıklaması",
  "dependencies": ["dep1", "dep2"],
  "env_vars": ["VAR1", "VAR2"]
}"""

    def __init__(self):
        self.model = _pick_model("qwen2.5-coder")
        self.history: list[dict] = []

    async def implement(self, idea: Idea, round_num: int, event_queue: asyncio.Queue) -> Implementation:
        user_msg = f"""Aşağıdaki özelliği implement et:

**Başlık:** {idea.title}
**Modül:** {idea.module}
**Karmaşıklık:** {idea.complexity}
**Açıklama:** {idea.description}
**Etiketler:** {', '.join(idea.tags)}

FastAPI backend kodu yaz. Şunları içersin:
1. Pydantic request/response schemaları
2. SQLAlchemy model (gerekiyorsa)
3. FastAPI router ve endpoint'ler
4. Service layer logic
5. Error handling

JSON formatında yanıtla."""

        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            *self.history[-2:],
            {"role": "user", "content": user_msg},
        ]

        await event_queue.put({
            "type": "agent_thinking",
            "agent": self.NAME,
            "round": round_num,
            "message": f"'{idea.title}' implement ediliyor...",
        })

        full_response = ""
        async for chunk in _ollama_chat(self.model, messages, temperature=0.2, max_tokens=2500):
            full_response += chunk
            await event_queue.put({
                "type": "agent_streaming",
                "agent": self.NAME,
                "round": round_num,
                "chunk": chunk,
            })

        self.history.append({"role": "user", "content": user_msg})
        self.history.append({"role": "assistant", "content": full_response})

        impl_data = _extract_json(full_response)
        code = impl_data.get("code", full_response)

        impl = Implementation(
            idea=idea,
            code=code,
            language=impl_data.get("language", "python"),
            file_path=impl_data.get("file_path", f"backend/app/domains/{idea.module}/router.py"),
            explanation=impl_data.get("explanation", ""),
            round_num=round_num,
        )

        await event_queue.put({
            "type": "impl_complete",
            "agent": self.NAME,
            "round": round_num,
            "implementation": {
                "file_path": impl.file_path,
                "language": impl.language,
                "code_preview": impl.code[:500] + "..." if len(impl.code) > 500 else impl.code,
                "explanation": impl.explanation,
                "lines": len(impl.code.splitlines()),
            },
        })
        return impl


class TestAgent:
    """Kodu inceler, test yazar ve kalite raporu üretir."""

    NAME = "🧪 Test Ajanı"
    SYSTEM_PROMPT = """Sen Cortex AI Automation platformu için senior bir QA mühendisisin.
Test araçları: pytest, httpx TestClient, Playwright, unittest.mock.

Görevin: Verilen kodu kritik gözle incele, testler yaz ve kapsamlı rapor hazırla.
• Unit testler yaz (pytest)
• Edge case'leri bul
• Security vulnerability'leri tespit et
• Performance sorunlarını işaretle
• Code quality yorumu yap

SADECE JSON formatında yanıt ver:
{
  "test_code": "...pytest test kodu...",
  "bugs_found": ["bug1", "bug2"],
  "security_issues": ["issue1"],
  "improvements": ["öneri1", "öneri2"],
  "coverage_estimate": 75,
  "verdict": "pass|fail|needs_work",
  "summary": "genel değerlendirme"
}"""

    def __init__(self):
        self.model = _pick_model("mistral")
        self.history: list[dict] = []

    async def test(self, impl: Implementation, round_num: int, event_queue: asyncio.Queue) -> TestReport:
        code_preview = impl.code[:3000] if len(impl.code) > 3000 else impl.code

        user_msg = f"""Aşağıdaki kodu incele ve test et:

**Özellik:** {impl.idea.title}
**Dosya:** {impl.file_path}
**Dil:** {impl.language}

```{impl.language}
{code_preview}
```

**Açıklama:** {impl.explanation}

Şunları yap:
1. Pytest unit testleri yaz
2. Bug ve güvenlik açıklarını listele
3. İyileştirme öneriler sun
4. Verdict ver: pass/fail/needs_work

JSON formatında yanıtla."""

        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            *self.history[-2:],
            {"role": "user", "content": user_msg},
        ]

        await event_queue.put({
            "type": "agent_thinking",
            "agent": self.NAME,
            "round": round_num,
            "message": f"Kod analiz ediliyor ve testler yazılıyor...",
        })

        full_response = ""
        async for chunk in _ollama_chat(self.model, messages, temperature=0.3, max_tokens=2000):
            full_response += chunk
            await event_queue.put({
                "type": "agent_streaming",
                "agent": self.NAME,
                "round": round_num,
                "chunk": chunk,
            })

        self.history.append({"role": "user", "content": user_msg})
        self.history.append({"role": "assistant", "content": full_response})

        report_data = _extract_json(full_response)

        report = TestReport(
            implementation=impl,
            test_code=report_data.get("test_code", ""),
            bugs_found=report_data.get("bugs_found", []) + report_data.get("security_issues", []),
            improvements=report_data.get("improvements", []),
            coverage_estimate=int(report_data.get("coverage_estimate", 60)),
            verdict=report_data.get("verdict", "needs_work"),
            round_num=round_num,
        )

        await event_queue.put({
            "type": "test_complete",
            "agent": self.NAME,
            "round": round_num,
            "report": {
                "verdict": report.verdict,
                "bugs_found": report.bugs_found,
                "improvements": report.improvements,
                "coverage_estimate": report.coverage_estimate,
                "summary": report_data.get("summary", ""),
                "test_preview": report.test_code[:400] + "..." if len(report.test_code) > 400 else report.test_code,
            },
        })
        return report


# ── Yardımcı Fonksiyonlar ─────────────────────────────────────────────────

def _extract_json(text: str) -> dict:
    """Metinden JSON bloğu çıkarmaya çalışır."""
    import re
    # ```json ... ``` bloğu ara
    for pattern in [r"```json\s*([\s\S]*?)\s*```", r"```\s*([\s\S]*?)\s*```"]:
        match = re.search(pattern, text)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
    # Direkt JSON dene
    try:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(text[start:end])
    except json.JSONDecodeError:
        pass
    return {}
