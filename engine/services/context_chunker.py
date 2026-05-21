"""
Engine — Context Chunker

Büyük dokümanları (PRD, spec, test geçmişi) yerel model context window'una
sığacak şekilde böler ve LLM ile özetleyerek birleştirir.

Strateji:
  1. Token tahmini: len(text) // 4  (yaklaşık, tiktoken gerektirmez)
  2. Sığıyorsa → doğrudan gönder
  3. Sığmıyorsa → paragraph/cümle sınırlarından böl
  4. Her chunk'ı özetle (LLM çağrısı)
  5. Özetleri birleştirip final analiz isteğini gönder

Kullanım:
    chunker = ContextChunker(gateway, model="qwen2.5:14b")
    result = chunker.analyze(document_text, task_prompt)
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

from .llm_gateway import LLMGateway

logger = logging.getLogger(__name__)

# Güvenli input token limiti — context window'un %75'i
# Açık kaynak 7b–14b modeller için ~8k token → 6k safe limit
_SAFE_TOKEN_LIMIT = 6_000
_CHUNK_TOKEN_SIZE = 3_000   # Her chunk ~3k token
_CHARS_PER_TOKEN  = 4        # Yaklaşık karakter/token oranı


def _estimate_tokens(text: str) -> int:
    return len(text) // _CHARS_PER_TOKEN


@dataclass
class ChunkedResult:
    final_output: str
    chunk_count: int
    total_estimated_tokens: int
    summaries: list[str] = field(default_factory=list)
    was_chunked: bool = False


class ContextChunker:
    """Büyük metin → chunk+summarize → birleştirilmiş analiz."""

    SUMMARIZE_SYSTEM = """\
Sen bir doküman özetleyicisisin. Verilen metni şu kurallara göre özetle:
- Tüm önemli bilgileri ve gereksinimleri koru
- Test edilebilir davranışları ve iş kurallarını kaydetme
- Kısa ve yoğun yaz — gereksiz açıklama ekleme
- Türkçe yaz
"""

    MERGE_SYSTEM = """\
Sana bir dokümanın birden fazla bölümünün özeti verilecek.
Bu özetleri bütünleştirerek istenen görevi gerçekleştir.
Bölümler arasında tutarlılığı koru, tekrar eden bilgileri birleştir.
"""

    def __init__(
        self,
        gateway: LLMGateway,
        model: str | None = None,
        safe_token_limit: int = _SAFE_TOKEN_LIMIT,
        chunk_size: int = _CHUNK_TOKEN_SIZE,
    ):
        self.gateway = gateway
        self.model = model or "qwen2.5:14b"
        self.safe_token_limit = safe_token_limit
        self.chunk_size = chunk_size

    def analyze(self, document: str, task_prompt: str, task_system: str = "") -> ChunkedResult:
        """
        Büyük dokümanı analiz et.

        Args:
            document:    Ham doküman metni.
            task_prompt: LLM'e gönderilecek asıl görev talimatı.
            task_system: Görev için system prompt (opsiyonel).

        Returns:
            ChunkedResult — final LLM çıktısı + metadata.
        """
        total_tokens = _estimate_tokens(document)
        logger.info(
            "ContextChunker: ~%d token, limit=%d",
            total_tokens, self.safe_token_limit,
        )

        if total_tokens <= self.safe_token_limit:
            # Context window'a sığıyor — doğrudan gönder
            output = self._call_task(document, task_prompt, task_system)
            return ChunkedResult(
                final_output=output,
                chunk_count=1,
                total_estimated_tokens=total_tokens,
                was_chunked=False,
            )

        # Chunk + summarize pipeline
        chunks = self._split_into_chunks(document)
        logger.info("ContextChunker: %d chunk'a bölündü", len(chunks))

        summaries: list[str] = []
        for i, chunk in enumerate(chunks, start=1):
            logger.debug("Chunk %d/%d özetleniyor (%d token)...", i, len(chunks), _estimate_tokens(chunk))
            summary = self._summarize_chunk(chunk, i, len(chunks))
            summaries.append(summary)

        merged = self._merge_summaries(summaries)
        output = self._call_task(merged, task_prompt, task_system or self.MERGE_SYSTEM)

        return ChunkedResult(
            final_output=output,
            chunk_count=len(chunks),
            total_estimated_tokens=total_tokens,
            summaries=summaries,
            was_chunked=True,
        )

    # ── internal ─────────────────────────────────────────────────────────────

    def _split_into_chunks(self, text: str) -> list[str]:
        """
        Metni paragraph/cümle sınırlarından chunk'lara böl.
        Kelime ortasından kesmez.
        """
        max_chars = self.chunk_size * _CHARS_PER_TOKEN

        # Önce paragrafları bul
        paragraphs = re.split(r"\n{2,}", text)

        chunks: list[str] = []
        current: list[str] = []
        current_len = 0

        for para in paragraphs:
            para_len = len(para)
            if current_len + para_len > max_chars and current:
                chunks.append("\n\n".join(current))
                current = []
                current_len = 0

            # Tek paragraf chunk'tan büyükse cümle cümle böl
            if para_len > max_chars:
                sentences = re.split(r"(?<=[.!?])\s+", para)
                for sent in sentences:
                    sent_len = len(sent)
                    if current_len + sent_len > max_chars and current:
                        chunks.append("\n\n".join(current))
                        current = []
                        current_len = 0
                    current.append(sent)
                    current_len += sent_len
            else:
                current.append(para)
                current_len += para_len

        if current:
            chunks.append("\n\n".join(current))

        return [c.strip() for c in chunks if c.strip()]

    def _summarize_chunk(self, chunk: str, idx: int, total: int) -> str:
        """Tek chunk'ı özetle."""
        messages = [
            {"role": "system", "content": self.SUMMARIZE_SYSTEM},
            {
                "role": "user",
                "content": (
                    f"Doküman Bölümü {idx}/{total}:\n\n{chunk}\n\n"
                    "Bu bölümü özetle. Test edilebilir gereksinimleri ve iş kurallarını koru."
                ),
            },
        ]
        try:
            resp = self.gateway.complete(messages, model=self.model, temperature=0.1, max_tokens=1500)
            return resp.content
        except Exception as exc:
            logger.warning("Chunk %d özetlenemedi: %s — ham metin kullanılıyor", idx, exc)
            return chunk[:max(500, self.chunk_size * _CHARS_PER_TOKEN // 4)]

    def _merge_summaries(self, summaries: list[str]) -> str:
        """Tüm özetleri tek bir birleşik özet haline getir."""
        numbered = "\n\n".join(f"--- Bölüm {i+1} Özeti ---\n{s}" for i, s in enumerate(summaries))
        merge_tokens = _estimate_tokens(numbered)

        # Özetler de büyükse sadece birleştir (LLM çağrısı yapmadan)
        if merge_tokens > self.safe_token_limit:
            logger.warning(
                "Birleştirilmiş özetler hâlâ büyük (%d token) — LLM merge atlanıyor",
                merge_tokens,
            )
            return numbered

        messages = [
            {"role": "system", "content": self.MERGE_SYSTEM},
            {
                "role": "user",
                "content": f"Aşağıdaki bölüm özetlerini tek tutarlı bir özete birleştir:\n\n{numbered}",
            },
        ]
        try:
            resp = self.gateway.complete(messages, model=self.model, temperature=0.1, max_tokens=2000)
            return resp.content
        except Exception as exc:
            logger.warning("Özet birleştirme başarısız: %s — sayısal birleştirme kullanılıyor", exc)
            return numbered

    def _call_task(self, context: str, task_prompt: str, task_system: str) -> str:
        """Final görev isteğini LLM'e gönder."""
        messages: list[dict] = []
        if task_system:
            messages.append({"role": "system", "content": task_system})
        messages.append({
            "role": "user",
            "content": f"{task_prompt}\n\nDoküman/Bağlam:\n{context}",
        })
        resp = self.gateway.complete(messages, model=self.model, temperature=0.2, max_tokens=4000)
        return resp.content
