"""LLM Integration Service Layer — Core business logic for 10 MVP features."""

import asyncio
import hashlib
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID, uuid4

from sqlalchemy import and_, desc, func, or_
from sqlalchemy.orm import Session

from app.core.logger import get_logger
from app.infra.database import get_db

from .models import (
    RAGVectorStore,
    RAGRetrievalLog,
    ModelRoutingConfig,
    HallucinationScore,
    ApprovalQueue,
    LLMAuditLog,
    CostTrackingRecord,
    BudgetAlert,
    RateLimitQuota,
    RateLimitEvent,
    StreamingSession,
    ToolDefinition,
    ToolCall,
    FineTuningDataset,
    FineTuningJob,
    TaskTypeEnum,
    ApprovalStatus,
    ConfidenceLevel,
)

logger = get_logger(__name__)


# ============================================================================
# Feature 1: RAG Foundation Service
# ============================================================================


class RAGService:
    """Vector DB and retrieval management (Feature 1)."""

    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id
        self._embeddings = None  # Lazy-load embedding model

    async def _get_embeddings(self):
        """Lazy-load embedding model (OpenAI, HuggingFace, or local)."""
        if self._embeddings is None:
            try:
                # Use sentence-transformers for local embeddings
                from sentence_transformers import SentenceTransformer
                self._embeddings = SentenceTransformer("all-MiniLM-L6-v2")
            except ImportError:
                logger.warning("sentence-transformers not installed, using OpenAI")
                # Fallback: Use OpenAI embeddings
                from openai import AsyncOpenAI
                client = AsyncOpenAI()
                self._embeddings = client
        return self._embeddings

    async def store_vector(
        self,
        namespace: str,
        source_type: str,
        document_text: str,
        metadata: Dict[str, Any],
        source_id: Optional[str] = None,
    ) -> str:
        """Store document with embedding in vector DB (Feature 1)."""
        try:
            embedder = await self._get_embeddings()
            # Generate embedding
            if hasattr(embedder, "encode"):
                embedding = embedder.encode(document_text).tolist()
            else:
                # OpenAI fallback
                response = await embedder.embeddings.create(
                    input=document_text,
                    model="text-embedding-3-small",
                )
                embedding = response.data[0].embedding

            # Store in DB
            vector = RAGVectorStore(
                id=str(uuid4()),
                tenant_id=self.tenant_id,
                namespace=namespace,
                source_type=source_type,
                source_id=source_id,
                document_text=document_text,
                metadata=metadata,
                embedding=embedding,
            )
            self.db.add(vector)
            self.db.commit()

            logger.info(f"Stored vector {vector.id} for namespace={namespace}")
            return vector.id
        except Exception as e:
            logger.error(f"Failed to store vector: {e}")
            self.db.rollback()
            raise

    async def retrieve(
        self,
        query: str,
        namespaces: List[str] = None,
        top_k: int = 5,
        min_similarity: float = 0.7,
    ) -> List[Dict[str, Any]]:
        """Retrieve similar documents from vector DB (Feature 1)."""
        start = time.time()
        try:
            if not namespaces:
                namespaces = ["test_cases"]

            embedder = await self._get_embeddings()
            # Generate query embedding
            if hasattr(embedder, "encode"):
                query_embedding = embedder.encode(query).tolist()
            else:
                response = await embedder.embeddings.create(
                    input=query, model="text-embedding-3-small"
                )
                query_embedding = response.data[0].embedding

            # Search in vector DB using cosine similarity
            vectors = self.db.query(RAGVectorStore).filter(
                and_(
                    RAGVectorStore.tenant_id == self.tenant_id,
                    RAGVectorStore.namespace.in_(namespaces),
                )
            ).all()

            # Compute similarity scores
            results = []
            for vec in vectors:
                similarity = self._cosine_similarity(query_embedding, vec.embedding)
                if similarity >= min_similarity:
                    results.append(
                        {
                            "id": vec.id,
                            "source_type": vec.source_type,
                            "source_id": vec.source_id,
                            "document_text": vec.document_text,
                            "similarity": similarity,
                            "metadata": vec.metadata,
                        }
                    )

            # Sort and limit
            results.sort(key=lambda x: x["similarity"], reverse=True)
            results = results[:top_k]

            # Log retrieval
            latency = time.time() - start
            log = RAGRetrievalLog(
                id=str(uuid4()),
                tenant_id=self.tenant_id,
                query=query,
                namespaces=namespaces,
                top_k=top_k,
                results_count=len(results),
                latency_ms=latency * 1000,
            )
            self.db.add(log)
            self.db.commit()

            return results
        except Exception as e:
            logger.error(f"RAG retrieval failed: {e}")
            raise

    @staticmethod
    def _cosine_similarity(a: List[float], b: List[float]) -> float:
        """Compute cosine similarity between two vectors."""
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x**2 for x in a) ** 0.5
        norm_b = sum(y**2 for y in b) ** 0.5
        return dot / (norm_a * norm_b) if norm_a and norm_b else 0.0


# ============================================================================
# Feature 2: Model Routing Service
# ============================================================================


class ModelRoutingService:
    """Task-to-model mapping and cost optimization (Feature 2)."""

    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id

    def configure_routing(
        self,
        task_type: str,
        primary_model: str,
        fallback_models: List[str],
        cost_budget_usd: float,
        max_tokens: int = 2048,
        temperature: float = 0.7,
    ) -> str:
        """Configure model routing for a task type (Feature 2)."""
        existing = self.db.query(ModelRoutingConfig).filter(
            and_(
                ModelRoutingConfig.tenant_id == self.tenant_id,
                ModelRoutingConfig.task_type == task_type,
            )
        ).first()

        if existing:
            existing.primary_model = primary_model
            existing.fallback_models = fallback_models
            existing.cost_budget_usd = cost_budget_usd
            existing.max_tokens = max_tokens
            existing.temperature = temperature
            config_id = existing.id
        else:
            config = ModelRoutingConfig(
                id=str(uuid4()),
                tenant_id=self.tenant_id,
                task_type=task_type,
                primary_model=primary_model,
                fallback_models=fallback_models,
                cost_budget_usd=cost_budget_usd,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            self.db.add(config)
            config_id = config.id

        self.db.commit()
        logger.info(f"Configured routing for task_type={task_type}")
        return config_id

    def select_model(self, task_type: str) -> Tuple[str, List[str], Dict[str, Any]]:
        """Select primary and fallback models for task (Feature 2)."""
        config = self.db.query(ModelRoutingConfig).filter(
            and_(
                ModelRoutingConfig.tenant_id == self.tenant_id,
                ModelRoutingConfig.task_type == task_type,
                ModelRoutingConfig.enabled == True,
            )
        ).first()

        if config:
            return config.primary_model, config.fallback_models, {
                "max_tokens": config.max_tokens,
                "temperature": config.temperature,
                "budget": config.cost_budget_usd,
            }

        # Default fallback routing
        defaults = {
            TaskTypeEnum.CODER: ("qwen2.5-coder:7b", ["llama3.1:8b", "gpt-4-turbo"], {}),
            TaskTypeEnum.ANALYST: ("qwen2.5:14b", ["claude-3.5-sonnet", "gpt-4-turbo"], {}),
            TaskTypeEnum.FAST: ("llama3.1:8b", ["ollama-default"], {}),
        }
        return defaults.get(task_type, ("llama3.1:8b", [], {}))


# ============================================================================
# Feature 3: Hallucination Detection Service
# ============================================================================


class HallucinationDetectionService:
    """Confidence scoring and fact-checking (Feature 3)."""

    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id
        self.rag = RAGService(db, tenant_id)

    async def check_hallucinations(
        self,
        text: str,
        context: Optional[str] = None,
        llm_call_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Check text for hallucinations (Feature 3)."""
        try:
            # Extract confidence from text (e.g., via keyword analysis, ML model)
            confidence_score = await self._compute_confidence(text, context)
            confidence_level = self._map_to_level(confidence_score)

            # Fact-check against KB
            fact_check_passed = None
            fact_check_details = None
            kb_match_score = None

            if context:
                fact_results = await self._fact_check(text, context)
                fact_check_passed = all(r.get("verified", False) for r in fact_results)
                fact_check_details = fact_results
                kb_match_score = sum(r.get("confidence", 0) for r in fact_results) / len(
                    fact_results
                ) if fact_results else 0

            # Flag uncertainties
            uncertainty_flags = self._extract_uncertainty_flags(text)

            # Store score
            if llm_call_id:
                score = HallucinationScore(
                    id=str(uuid4()),
                    tenant_id=self.tenant_id,
                    llm_call_id=llm_call_id,
                    confidence_score=confidence_score,
                    confidence_level=confidence_level,
                    fact_check_passed=fact_check_passed,
                    fact_check_details=fact_check_details,
                    uncertainty_flags=uncertainty_flags,
                    kb_match_score=kb_match_score,
                )
                self.db.add(score)
                self.db.commit()

            return {
                "confidence_score": confidence_score,
                "confidence_level": confidence_level,
                "fact_check_passed": fact_check_passed,
                "uncertainty_flags": uncertainty_flags,
                "kb_match_score": kb_match_score,
                "recommendation": self._get_recommendation(
                    confidence_score, fact_check_passed, uncertainty_flags
                ),
            }
        except Exception as e:
            logger.error(f"Hallucination check failed: {e}")
            raise

    async def _compute_confidence(self, text: str, context: Optional[str]) -> float:
        """Compute confidence score (0.0-1.0) (Feature 3)."""
        # Simple heuristic: check for common hallucination indicators
        hallucination_markers = [
            "I don't know",
            "unclear",
            "possibly",
            "maybe",
            "might be",
            "could be",
        ]

        score = 1.0
        for marker in hallucination_markers:
            if marker.lower() in text.lower():
                score -= 0.1

        # Check length and structure
        if len(text.split()) < 5:
            score -= 0.2  # Very short responses are suspicious

        return max(0.0, min(1.0, score))

    async def _fact_check(self, text: str, context: str) -> List[Dict[str, Any]]:
        """Fact-check against context (Feature 3)."""
        # Use RAG to check claims against KB
        claims = self._extract_claims(text)
        results = []

        for claim in claims:
            relevant_docs = await self.rag.retrieve(claim, top_k=3, min_similarity=0.6)
            verified = len(relevant_docs) > 0
            confidence = (
                max(doc["similarity"] for doc in relevant_docs) if relevant_docs else 0
            )

            results.append(
                {
                    "claim": claim,
                    "verified": verified,
                    "confidence": confidence,
                    "sources": [doc.get("source_id") for doc in relevant_docs],
                }
            )

        return results

    def _extract_claims(self, text: str) -> List[str]:
        """Extract factual claims from text (Feature 3)."""
        # Simple sentence splitting
        sentences = text.split(".")
        return [s.strip() for s in sentences if len(s.strip()) > 10][:5]

    def _extract_uncertainty_flags(self, text: str) -> List[str]:
        """Extract uncertainty indicators (Feature 3)."""
        flags = []

        if "contradiction" in text.lower():
            flags.append("contradiction")
        if "uncertain" in text.lower() or "unclear" in text.lower():
            flags.append("unverifiable")
        if text.count("?") > 2:
            flags.append("too_many_questions")

        return flags

    @staticmethod
    def _map_to_level(score: float) -> str:
        """Map confidence score to level (Feature 3)."""
        if score >= 0.85:
            return ConfidenceLevel.HIGH
        elif score >= 0.70:
            return ConfidenceLevel.MEDIUM
        else:
            return ConfidenceLevel.LOW

    @staticmethod
    def _get_recommendation(
        confidence: float, fact_check: Optional[bool], flags: List[str]
    ) -> str:
        """Recommend action (Feature 3)."""
        if confidence < 0.6 or fact_check is False or len(flags) > 2:
            return "reject"
        elif confidence < 0.75 or fact_check is None or len(flags) > 0:
            return "review_required"
        else:
            return "approve"


# ============================================================================
# Feature 4: Approval Workflow Service
# ============================================================================


class ApprovalWorkflowService:
    """Human-in-loop approval (Feature 4)."""

    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id

    def create_approval(
        self,
        user_id: str,
        feature_type: str,
        ai_suggestion: Dict[str, Any],
        priority: int = 5,
    ) -> str:
        """Queue AI suggestion for approval (Feature 4)."""
        queue_item = ApprovalQueue(
            id=str(uuid4()),
            tenant_id=self.tenant_id,
            user_id=user_id,
            feature_type=feature_type,
            ai_suggestion=ai_suggestion,
            status=ApprovalStatus.PENDING,
            priority=priority,
        )
        self.db.add(queue_item)
        self.db.commit()

        logger.info(f"Created approval {queue_item.id} for feature={feature_type}")
        return queue_item.id

    def list_pending_approvals(
        self, limit: int = 50, offset: int = 0
    ) -> Tuple[int, List[Dict[str, Any]]]:
        """List pending approvals sorted by priority (Feature 4)."""
        query = self.db.query(ApprovalQueue).filter(
            and_(
                ApprovalQueue.tenant_id == self.tenant_id,
                ApprovalQueue.status == ApprovalStatus.PENDING,
            )
        )

        total = query.count()
        items = (
            query.order_by(desc(ApprovalQueue.priority))
            .limit(limit)
            .offset(offset)
            .all()
        )

        return total, [
            {
                "id": item.id,
                "feature_type": item.feature_type,
                "ai_suggestion": item.ai_suggestion,
                "priority": item.priority,
                "created_at": item.created_at,
            }
            for item in items
        ]

    def approve_item(self, approval_id: str, reviewer_id: str, notes: str = "") -> None:
        """Approve an item (Feature 4)."""
        item = self.db.query(ApprovalQueue).filter(
            ApprovalQueue.id == approval_id
        ).first()

        if item:
            item.status = ApprovalStatus.APPROVED
            item.reviewer_id = reviewer_id
            item.review_notes = notes
            item.approved_at = datetime.utcnow()
            self.db.commit()

            logger.info(f"Approved {approval_id}")

    def reject_item(self, approval_id: str, reviewer_id: str, notes: str = "") -> None:
        """Reject an item (Feature 4)."""
        item = self.db.query(ApprovalQueue).filter(
            ApprovalQueue.id == approval_id
        ).first()

        if item:
            item.status = ApprovalStatus.REJECTED
            item.reviewer_id = reviewer_id
            item.review_notes = notes
            item.approved_at = datetime.utcnow()
            self.db.commit()

            logger.info(f"Rejected {approval_id}")


# ============================================================================
# Feature 5: Audit Logging Service
# ============================================================================


class AuditLoggingService:
    """Complete audit trail (Feature 5)."""

    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id

    def log_llm_call(
        self,
        user_id: str,
        feature_type: str,
        task_type: str,
        model_used: str,
        prompt_text: str,
        response_text: str,
        tokens_input: int,
        tokens_output: int,
        latency_ms: float,
        cost_usd: float,
    ) -> str:
        """Log LLM call for audit (Feature 5)."""
        log = LLMAuditLog(
            id=str(uuid4()),
            tenant_id=self.tenant_id,
            user_id=user_id,
            feature_type=feature_type,
            task_type=task_type,
            model_used=model_used,
            prompt_text=prompt_text,
            response_text=response_text,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            latency_ms=latency_ms,
            cost_usd=cost_usd,
            user_action="pending",
        )
        self.db.add(log)
        self.db.commit()

        return log.id

    def record_user_action(
        self, log_id: str, action: str, feedback: Optional[str] = None
    ) -> None:
        """Record user action on logged call (Feature 5)."""
        log = self.db.query(LLMAuditLog).filter(LLMAuditLog.id == log_id).first()

        if log:
            log.user_action = action
            log.user_feedback = feedback
            self.db.commit()

    def query_audit_logs(
        self,
        feature_type: Optional[str] = None,
        model_used: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Query audit logs (Feature 5)."""
        query = self.db.query(LLMAuditLog).filter(
            LLMAuditLog.tenant_id == self.tenant_id
        )

        if feature_type:
            query = query.filter(LLMAuditLog.feature_type == feature_type)
        if model_used:
            query = query.filter(LLMAuditLog.model_used == model_used)
        if start_date:
            query = query.filter(LLMAuditLog.created_at >= start_date)
        if end_date:
            query = query.filter(LLMAuditLog.created_at <= end_date)

        logs = query.order_by(desc(LLMAuditLog.created_at)).limit(limit).all()

        return [
            {
                "id": log.id,
                "feature_type": log.feature_type,
                "task_type": log.task_type,
                "model_used": log.model_used,
                "tokens_input": log.tokens_input,
                "tokens_output": log.tokens_output,
                "latency_ms": log.latency_ms,
                "cost_usd": log.cost_usd,
                "user_action": log.user_action,
                "created_at": log.created_at,
            }
            for log in logs
        ]


# ============================================================================
# Feature 6: Cost Tracking Service
# ============================================================================


class CostTrackingService:
    """Token count and budget management (Feature 6)."""

    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id

    def record_cost(
        self, user_id: str, model_name: str, tokens_input: int, tokens_output: int
    ) -> float:
        """Record request cost (Feature 6)."""
        cost_usd = self._calculate_cost(model_name, tokens_input, tokens_output)

        record = CostTrackingRecord(
            id=str(uuid4()),
            tenant_id=self.tenant_id,
            user_id=user_id,
            model_name=model_name,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            cost_usd=cost_usd,
            date=datetime.utcnow(),
        )
        self.db.add(record)
        self.db.commit()

        # Check budget
        self._check_budget_alert()

        return cost_usd

    def get_cost_summary(
        self, period: str = "month"
    ) -> Dict[str, Any]:
        """Get cost summary (Feature 6)."""
        if period == "month":
            start_date = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        elif period == "week":
            start_date = datetime.utcnow() - timedelta(days=7)
        elif period == "day":
            start_date = datetime.utcnow() - timedelta(days=1)
        else:
            start_date = datetime.utcnow() - timedelta(days=365)

        records = self.db.query(CostTrackingRecord).filter(
            and_(
                CostTrackingRecord.tenant_id == self.tenant_id,
                CostTrackingRecord.date >= start_date,
            )
        ).all()

        total_cost = sum(r.cost_usd for r in records)
        total_tokens = sum(r.tokens_input + r.tokens_output for r in records)

        # Model breakdown
        model_breakdown = {}
        for record in records:
            if record.model_name not in model_breakdown:
                model_breakdown[record.model_name] = 0
            model_breakdown[record.model_name] += record.cost_usd

        return {
            "period": period,
            "total_cost_usd": total_cost,
            "total_tokens": total_tokens,
            "request_count": len(records),
            "avg_cost_per_request": total_cost / len(records) if records else 0,
            "model_breakdown": model_breakdown,
        }

    def get_budget_status(self) -> Dict[str, Any]:
        """Get current budget status (Feature 6)."""
        today = datetime.utcnow()
        month = today.strftime("%Y-%m")

        alert = self.db.query(BudgetAlert).filter(
            and_(BudgetAlert.tenant_id == self.tenant_id, BudgetAlert.month == month)
        ).first()

        if not alert:
            # Create default $1000/month budget
            alert = BudgetAlert(
                id=str(uuid4()),
                tenant_id=self.tenant_id,
                month=month,
                monthly_budget_usd=1000.0,
                current_spend_usd=0.0,
            )
            self.db.add(alert)
            self.db.commit()

        # Update current spend
        month_start = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        records = self.db.query(CostTrackingRecord).filter(
            and_(
                CostTrackingRecord.tenant_id == self.tenant_id,
                CostTrackingRecord.date >= month_start,
            )
        ).all()
        current_spend = sum(r.cost_usd for r in records)
        alert.current_spend_usd = current_spend
        self.db.commit()

        return {
            "month": month,
            "monthly_budget_usd": alert.monthly_budget_usd,
            "current_spend_usd": current_spend,
            "remaining_usd": max(0, alert.monthly_budget_usd - current_spend),
            "percentage_used": (current_spend / alert.monthly_budget_usd * 100)
            if alert.monthly_budget_usd > 0
            else 0,
            "alert_triggered": current_spend > (alert.monthly_budget_usd * alert.alert_threshold_pct / 100),
        }

    def _check_budget_alert(self) -> None:
        """Check if budget alert should be sent (Feature 6)."""
        status = self.get_budget_status()

        if status["alert_triggered"]:
            logger.warning(
                f"Tenant {self.tenant_id} budget alert: "
                f"{status['current_spend_usd']:.2f} / {status['monthly_budget_usd']:.2f}"
            )

    @staticmethod
    def _calculate_cost(model_name: str, tokens_input: int, tokens_output: int) -> float:
        """Calculate cost based on model and tokens (Feature 6)."""
        # Pricing per 1M tokens (as of 2024)
        pricing = {
            "gpt-4-turbo": (0.01, 0.03),
            "gpt-4": (0.03, 0.06),
            "claude-3.5-sonnet": (0.003, 0.015),
            "claude-opus": (0.015, 0.075),
            "qwen2.5:14b": (0.0, 0.0),  # Self-hosted
            "llama3.1:8b": (0.0, 0.0),  # Self-hosted
            "gemini-pro": (0.0005, 0.0015),
            "mixtral-8x7b": (0.0, 0.0),  # Self-hosted
        }

        input_price, output_price = pricing.get(model_name, (0.001, 0.003))
        return (tokens_input * input_price + tokens_output * output_price) / 1_000_000


# ============================================================================
# Feature 7: Rate Limiting Service
# ============================================================================


class RateLimitingService:
    """Per-user/org quota enforcement (Feature 7)."""

    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id
        self._request_history = {}  # In-memory for now; use Redis in production

    def get_or_create_quota(self, user_id: Optional[str] = None) -> RateLimitQuota:
        """Get or create rate limit quota (Feature 7)."""
        quota = self.db.query(RateLimitQuota).filter(
            and_(
                RateLimitQuota.tenant_id == self.tenant_id,
                RateLimitQuota.user_id == user_id,
            )
        ).first()

        if not quota:
            quota = RateLimitQuota(
                id=str(uuid4()),
                tenant_id=self.tenant_id,
                user_id=user_id,
                requests_per_minute=10,
                requests_per_hour=500,
                requests_per_day=5000,
                concurrent_requests_limit=5,
            )
            self.db.add(quota)
            self.db.commit()

        return quota

    def check_limit(self, user_id: str, limit_type: str = "rpm") -> Tuple[bool, Optional[str]]:
        """Check if user is within limits (Feature 7)."""
        quota = self.get_or_create_quota(user_id)

        if not quota.enabled:
            return True, None

        key = f"{self.tenant_id}:{user_id}"
        now = datetime.utcnow()

        if key not in self._request_history:
            self._request_history[key] = []

        # Clean old requests
        cutoff_times = {
            "rpm": now - timedelta(minutes=1),
            "rph": now - timedelta(hours=1),
            "rpd": now - timedelta(days=1),
        }

        history = [
            ts
            for ts in self._request_history[key]
            if ts > cutoff_times.get(limit_type, now)
        ]
        self._request_history[key] = history

        # Check limits
        limits = {
            "rpm": quota.requests_per_minute,
            "rph": quota.requests_per_hour,
            "rpd": quota.requests_per_day,
        }

        if len(history) >= limits.get(limit_type, 1000):
            # Log event
            event = RateLimitEvent(
                id=str(uuid4()),
                tenant_id=self.tenant_id,
                user_id=user_id,
                limit_type=limit_type,
            )
            self.db.add(event)
            self.db.commit()

            return False, limit_type

        self._request_history[key].append(now)
        return True, None

    def get_limit_status(self, user_id: str) -> Dict[str, int]:
        """Get current limit status (Feature 7)."""
        quota = self.get_or_create_quota(user_id)
        key = f"{self.tenant_id}:{user_id}"
        now = datetime.utcnow()

        history = self._request_history.get(key, [])
        rpm_count = len([ts for ts in history if ts > now - timedelta(minutes=1)])
        rph_count = len([ts for ts in history if ts > now - timedelta(hours=1)])
        rpd_count = len([ts for ts in history if ts > now - timedelta(days=1)])

        return {
            "rpm_remaining": max(0, quota.requests_per_minute - rpm_count),
            "rph_remaining": max(0, quota.requests_per_hour - rph_count),
            "rpd_remaining": max(0, quota.requests_per_day - rpd_count),
            "concurrent_active": 0,  # Would track from streaming sessions
            "concurrent_limit": quota.concurrent_requests_limit,
        }


# ============================================================================
# Features 8-10: Streaming, Function Calling, Fine-Tuning Services
# ============================================================================
# (Abbreviated for brevity; full implementation follows same patterns)


class StreamingService:
    """SSE token streaming (Feature 8)."""

    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id

    def create_streaming_session(
        self, user_id: str, feature_type: str, model_used: str
    ) -> str:
        """Create streaming session (Feature 8)."""
        request_id = str(uuid4())[:8]
        session = StreamingSession(
            id=str(uuid4()),
            tenant_id=self.tenant_id,
            user_id=user_id,
            request_id=request_id,
            feature_type=feature_type,
            model_used=model_used,
        )
        self.db.add(session)
        self.db.commit()
        return session.id


class FunctionCallingService:
    """Tool definition and execution (Feature 9)."""

    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id

    def define_tool(
        self,
        tool_name: str,
        description: str,
        input_schema: Dict[str, Any],
        output_schema: Dict[str, Any],
        execution_handler: str,
    ) -> str:
        """Define a tool for function calling (Feature 9)."""
        tool = ToolDefinition(
            id=str(uuid4()),
            tenant_id=self.tenant_id,
            tool_name=tool_name,
            description=description,
            input_schema=input_schema,
            output_schema=output_schema,
            execution_handler=execution_handler,
        )
        self.db.add(tool)
        self.db.commit()
        return tool.id


class FineTuningService:
    """Dataset prep and training (Feature 10)."""

    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id

    def create_dataset(
        self, name: str, task_type: str, description: Optional[str] = None
    ) -> str:
        """Create fine-tuning dataset (Feature 10)."""
        dataset = FineTuningDataset(
            id=str(uuid4()),
            tenant_id=self.tenant_id,
            name=name,
            task_type=task_type,
            description=description,
        )
        self.db.add(dataset)
        self.db.commit()
        return dataset.id
