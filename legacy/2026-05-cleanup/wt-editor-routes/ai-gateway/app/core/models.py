"""
Nexus QA — AI Gateway Pydantic Modelleri
Tüm istek/yanıt şemaları burada tanımlanır.
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field


class ProviderName(str, Enum):
    VLLM = "vllm"        # Self-hosted, açık kaynak (Qwen/Llama/Mistral vb.)
    GROQ = "groq"
    GEMINI = "gemini"
    OLLAMA = "ollama"
    G4F = "g4f"
    AUTO = "auto"  # Otomatik fallback zinciri kullan


class TaskType(str, Enum):
    """AI görev türleri — prompt şablonu seçimi için."""
    ANALYZE_DOCUMENT = "analyze_document"       # Analist dokümanı analizi
    GENERATE_TEST_CASES = "generate_test_cases"  # Test case üretimi
    GENERATE_GHERKIN = "generate_gherkin"        # Gherkin feature dosyası
    GENERATE_JAVA_STEPS = "generate_java_steps"  # Java step definitions
    GENERATE_PLAYWRIGHT = "generate_playwright"  # Playwright kod üretimi
    SUGGEST_REGRESSION = "suggest_regression"    # Regresyon seti önerisi
    DEBUG_TEST = "debug_test"                    # Hatalı test debug
    CHAT = "chat"                                # Genel sohbet


class Message(BaseModel):
    role: str = Field(..., description="system | user | assistant")
    content: str = Field(..., description="Mesaj içeriği")



# JSON çıktısı gerektiren task type'lar — bu görevlerde json_mode otomatik aktif olur
JSON_TASK_TYPES: frozenset[str] = frozenset({
    TaskType.ANALYZE_DOCUMENT,
    TaskType.GENERATE_TEST_CASES,
    TaskType.SUGGEST_REGRESSION,
    TaskType.DEBUG_TEST,
})


class AIRequest(BaseModel):
    """AI Gateway'e gelen standart istek."""
    task_type: TaskType = Field(TaskType.CHAT, description="Görev türü")
    messages: list[Message] = Field(..., description="Mesaj geçmişi")
    provider: ProviderName = Field(ProviderName.AUTO, description="Kullanılacak sağlayıcı")
    temperature: float = Field(0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(4000, ge=1, le=8192)
    stream: bool = Field(False, description="Streaming yanıt")
    json_mode: bool = Field(False, description="JSON formatında yanıt zorla")
    # Görev tipi için belirli bir model zorlamak (ör. Ollama'da qwen2.5-coder)
    model_override: Optional[str] = Field(None, description="Sağlayıcı-specific model adı override")
    # Metadata — hangi projeden geldiği
    project_id: Optional[str] = None
    correlation_id: Optional[str] = None

    def model_post_init(self, __context: Any) -> None:
        """JSON task type'larda json_mode otomatik aktif edilir."""
        if self.task_type in JSON_TASK_TYPES:
            object.__setattr__(self, "json_mode", True)


class ProviderAttempt(BaseModel):
    """Bir sağlayıcı deneme kaydı."""
    provider: str
    success: bool
    error: Optional[str] = None
    latency_ms: int = 0
    tokens_used: int = 0


class AIResponse(BaseModel):
    """AI Gateway'den dönen standart yanıt."""
    content: str = Field(..., description="AI yanıtı")
    provider_used: str = Field(..., description="Yanıtı üreten sağlayıcı")
    model_used: str = Field(..., description="Kullanılan model adı")
    attempts: list[ProviderAttempt] = Field(default_factory=list)
    tokens_used: int = 0
    latency_ms: int = 0
    cached: bool = False
    correlation_id: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    providers: dict[str, bool]
    version: str


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
    providers_tried: list[str] = Field(default_factory=list)
