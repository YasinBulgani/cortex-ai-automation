# Neurex API Reference & OpenAPI Documentation

**Last Updated:** 2026-06-09  
**Status:** Production-Ready  
**Version:** 1.0.0

---

## Quick Start

All endpoints use `/api/v1/` prefix. Base URL: `http://localhost:8000`

### Authentication
```bash
# 1. Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"admin123"}'

# 2. Use returned access_token in all requests
curl -X GET http://localhost:8000/api/v1/test-cases \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

### 53 Domains Available

Core domains: **auth, automation, test_management, test_execution, defects, api_testing, ai, ai_service, agents, cicd, nexus_repo, compliance, billing, management, coverage, jira, email, webhook, products, catalog, events, dsl, collaboration, artifact_storage, sso, privacy, audit, organizations, teams, projects, users, ...**

See full OpenAPI spec at: `GET /docs` (dev mode)

### Common Endpoints

```bash
# Test Management
GET    /api/v1/test-cases?page=1&limit=50
POST   /api/v1/test-cases
GET    /api/v1/test-cases/{id}
PATCH  /api/v1/test-cases/{id}
DELETE /api/v1/test-cases/{id}

# Test Execution
POST   /api/v1/runs
GET    /api/v1/runs/{id}
GET    /api/v1/runs/{id}/results

# Defects
POST   /api/v1/defects
GET    /api/v1/defects
PATCH  /api/v1/defects/{id}

# AI
POST   /api/v1/ai/generate-cases
POST   /api/v1/ai/analyze-failure
```

### Error Handling

All errors return JSON with status code + error details:
```json
{
  "detail": "Error message",
  "error_code": "ERROR_TYPE",
  "status_code": 400,
  "request_id": "correlation-uuid"
}
```

### Response Format

Paginated responses:
```json
{
  "data": [...],
  "pagination": {
    "total": 1500,
    "page": 1,
    "limit": 50,
    "total_pages": 30
  }
}
```

---

For comprehensive API documentation, see **docs/01_API_REFERENCE_FULL.md**

