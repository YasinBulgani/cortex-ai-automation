# Neurex LLM MVP - Deployment & Setup Guide

## Quick Start (Development)

```bash
# 1. Environment Setup
cp .env.example .env
# Edit .env and set:
# - POSTGRES_PASSWORD
# - JWT_SECRET_KEY
# - AI_PROVIDER=ollama (or your choice)

# 2. Start Docker services
docker compose up -d postgres redis

# 3. Run migrations
make migrate

# 4. Start backend
make backend-dev

# 5. Start frontend
make web-dev

# 6. (Optional) Start Ollama for local LLM
docker run -d -p 11434:11434 ollama/ollama
ollama pull qwen2.5:14b
```

## Architecture

```
Frontend (Next.js 3000)
    ↓
Backend (FastAPI 8000)
    ├─ ai_service domain (7 endpoints)
    ├─ LLM orchestrator
    ├─ RAG pipeline
    ├─ Validator
    └─ Database (PostgreSQL 5432)

Cache: Redis (6379)

LLM Fallback Chain:
1. Ollama (local, free) - http://ollama:11434
2. vLLM (self-hosted, free)
3. Groq (external, $0.0002-0.0006/1K)
4. OpenAI/Claude (premium)
5. Gemini (fallback)
```

## MVP Features (7 Endpoints)

✅ POST /api/v1/ai-service/generate-bdd
✅ POST /api/v1/ai-service/improve-test  
✅ POST /api/v1/ai-service/suggest-missing-tests
✅ POST /api/v1/ai-service/select-regression-suite
✅ POST /api/v1/ai-service/analyze-defect
✅ POST /api/v1/ai-service/generate-release-notes
✅ POST /api/v1/ai-service/validate-output

## Testing

```bash
# Unit tests
make test-unit

# Integration tests  
make test-backend

# Type check
make type-check

# Lint
make lint
```

## Security Checklist

- [ ] RLS enforced on all queries (tenant_id filtering)
- [ ] PII masking in RAG (emails → [EMAIL], tokens → [TOKEN])
- [ ] Approval workflow for code generation
- [ ] Audit logging complete (sd_ai_audit_log)
- [ ] Token budget enforcement (hard limits)
- [ ] Hallucination validation before deployment
- [ ] HTTPS enforced in production

## Cost Tracking

- Ollama: Free (local)
- Groq: $0.0002/1K input, $0.0006/1K output
- OpenAI GPT-4: $0.03/1K input, $0.06/1K output
- Claude: $0.015/1K input, $0.045/1K output
- Gemini: $0.0005/1K input, $0.0015/1K output

Estimated MVP monthly cost (1000 API calls/day):
- Ollama only: $0
- With Groq fallback: ~$30/month

## Monitoring

```bash
# Check API health
curl http://localhost:8000/api/v1/ai-service/health

# Monitor LLM calls
SELECT * FROM sd_ai_audit_log ORDER BY ts DESC LIMIT 10;

# Track costs
SELECT feature, SUM(cost_usd) as total FROM sd_ai_cost_log GROUP BY feature;
```

## Production Deployment

1. **Environment**: Set AI_PROVIDER to cloud (openai, groq, etc)
2. **Database**: Use managed PostgreSQL (RDS, CloudSQL)
3. **Cache**: Managed Redis (ElastiCache, MemoryStore)
4. **LLM**: Use API keys for fallback chain
5. **RAG**: Deploy Vector DB (Pinecone, Weaviate, or self-hosted)
6. **Monitoring**: Enable Sentry, OTel tracing
7. **Compliance**: Enable audit logging, data retention policies

## Rollback

If LLM issues occur:
- Set AI_PROVIDER=ollama + AI_LOCAL_ONLY=true (no external calls)
- Set AI_ROUTING_MODE=cost_optimized (skip expensive models)
- Disable specific features via feature flags

## Support

- Backend logs: `docker compose logs backend`
- LLM Gateway logs: `docker compose logs ai_gateway`  
- Database: `psql -h localhost -U neurex_user -d syndata_db`
