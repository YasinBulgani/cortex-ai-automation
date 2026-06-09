# Neurex LLM AI Service - API Examples

## Authentication

All requests require JWT token in header:
```bash
Authorization: Bearer <your_jwt_token>
```

## Endpoints

### 1. Generate BDD Test Cases
**POST** `/api/v1/ai-service/generate-bdd`

Generate test cases from user story using LLM.

**Request:**
```bash
curl -X POST http://localhost:8000/api/v1/ai-service/generate-bdd \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "story": "As a user, I want to login with email and password",
    "project_id": "proj-001",
    "context": {
      "app_type": "web",
      "auth_method": "OAuth2"
    }
  }'
```

**Response (201 Created):**
```json
{
  "success": true,
  "test_cases": [
    {
      "scenario_name": "Successful login with valid credentials",
      "given": [
        "user is on login page",
        "user has valid email"
      ],
      "when": [
        "user enters email",
        "user enters correct password",
        "user clicks login button"
      ],
      "then": [
        "user is logged in",
        "user sees dashboard",
        "session token is stored"
      ],
      "priority": "high"
    },
    {
      "scenario_name": "Login fails with invalid password",
      "given": ["user is on login page"],
      "when": ["user enters wrong password", "user clicks login"],
      "then": ["error message displayed", "user not logged in"],
      "priority": "high"
    }
  ],
  "confidence_score": 0.92,
  "execution_time_ms": 2340
}
```

---

### 2. Improve Existing Test Case
**POST** `/api/v1/ai-service/improve-test`

Get suggestions to improve a test case.

**Request:**
```bash
curl -X POST http://localhost:8000/api/v1/ai-service/improve-test \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "test_case_id": "tc-001",
    "project_id": "proj-001"
  }'
```

**Response (200 OK):**
```json
{
  "success": true,
  "suggestions": [
    {
      "type": "clarity",
      "description": "Step descriptions are vague",
      "suggested_change": "Change 'user enters data' to 'user enters email address and password'",
      "priority": "high"
    },
    {
      "type": "coverage",
      "description": "Missing error path testing",
      "suggested_change": "Add scenario for invalid password attempt",
      "priority": "high"
    },
    {
      "type": "maintainability",
      "description": "Hardcoded test data",
      "suggested_change": "Use parameterized values for email/password",
      "priority": "medium"
    }
  ],
  "quality_score": 0.68
}
```

---

### 3. Suggest Missing Tests
**POST** `/api/v1/ai-service/suggest-missing-tests`

Analyze coverage and suggest missing test cases.

**Request:**
```bash
curl -X POST http://localhost:8000/api/v1/ai-service/suggest-missing-tests \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "proj-001",
    "min_confidence": 0.75
  }'
```

**Response (200 OK):**
```json
[
  {
    "scenario_name": "Login with SQL injection attempt",
    "description": "Test security against common SQL injection patterns",
    "suggestion_type": "missing_error_path",
    "coverage_impact": 0.12,
    "confidence_score": 0.89,
    "estimated_effort_hours": 2.5
  },
  {
    "scenario_name": "Login timeout after 30 minutes",
    "description": "Session expires and requires re-login",
    "suggestion_type": "missing_edge_case",
    "coverage_impact": 0.08,
    "confidence_score": 0.82,
    "estimated_effort_hours": 1.5
  }
]
```

---

### 4. Select Regression Suite
**POST** `/api/v1/ai-service/select-regression-suite`

Intelligently select tests to run based on code changes.

**Request:**
```bash
curl -X POST http://localhost:8000/api/v1/ai-service/select-regression-suite \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "proj-001",
    "code_changes": {
      "backend/auth/login.py": ["verify_password", "create_session"],
      "backend/auth/mfa.py": ["enable_mfa"]
    },
    "max_test_count": 50
  }'
```

**Response (200 OK):**
```json
{
  "success": true,
  "selected_test_ids": [
    "tc-login-001",
    "tc-login-002",
    "tc-mfa-001",
    "tc-session-001",
    "tc-token-refresh-001"
  ],
  "coverage_prediction": 0.87,
  "estimated_duration_minutes": 45
}
```

---

### 5. Analyze Defect (RCA)
**POST** `/api/v1/ai-service/analyze-defect`

Get root cause analysis for a defect.

**Request:**
```bash
curl -X POST http://localhost:8000/api/v1/ai-service/analyze-defect \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "defect_id": "def-001",
    "error_log": "TypeError: NoneType object is not subscriptable at auth/mfa.py:42 in enable_mfa()",
    "reproduction_steps": "1. Enable MFA in settings\n2. Attempt login\n3. Error occurs on MFA screen"
  }'
```

**Response (200 OK):**
```json
{
  "success": true,
  "root_causes": [
    {
      "description": "Secret key not initialized when MFA enabled on new account",
      "likelihood": 0.92,
      "affected_components": ["auth/mfa.py", "auth/models.py"],
      "suggested_fix": "Initialize secret key before first use; add null check in enable_mfa()"
    },
    {
      "description": "Race condition between user creation and MFA setup",
      "likelihood": 0.45,
      "affected_components": ["auth/mfa.py", "auth/database.py"],
      "suggested_fix": "Use database transaction lock during MFA setup"
    }
  ],
  "confidence_score": 0.88,
  "similar_defect_ids": ["def-034", "def-089"]
}
```

---

### 6. Generate Release Notes
**POST** `/api/v1/ai-service/generate-release-notes`

Generate release notes from test results and fixes.

**Request:**
```bash
curl -X POST http://localhost:8000/api/v1/ai-service/generate-release-notes \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "proj-001",
    "version": "2.1.0",
    "fixed_defect_ids": ["def-001", "def-034", "def-089"],
    "new_features": [
      {
        "name": "MFA Support",
        "description": "Two-factor authentication via TOTP"
      },
      {
        "name": "Rate Limiting",
        "description": "API rate limiting to prevent abuse"
      }
    ]
  }'
```

**Response (201 Created):**
```json
{
  "success": true,
  "content": "# Release Notes — v2.1.0\n\n## New Features\n\n### Multi-Factor Authentication (MFA)\nUsers can now enable two-factor authentication using time-based one-time passwords (TOTP)...\n\n### API Rate Limiting\nProtect your application from abuse with intelligent rate limiting...\n\n## Bug Fixes\n\n- **Critical**: Fixed NoneType error in MFA setup (fixes #def-001)\n- **High**: Session timeout handling improved (fixes #def-034)\n- **Medium**: Email validation edge case resolved (fixes #def-089)\n\n## Known Issues\n\n- Rate limiting headers may not reflect in some proxy scenarios\n",
  "format": "markdown"
}
```

---

### 7. Validate Output (Hallucination Detection)
**POST** `/api/v1/ai-service/validate-output`

Validate LLM output for hallucinations and issues.

**Request:**
```bash
curl -X POST http://localhost:8000/api/v1/ai-service/validate-output \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "output_text": "Feature: Login\n  Scenario: User logs in\n    Given user on login page\n    When user enters email and password\n    Then user is logged in",
    "output_type": "bdd",
    "source_context": "Login feature with email/password authentication"
  }'
```

**Response (200 OK):**
```json
{
  "is_valid": true,
  "confidence_score": 0.94,
  "hallucination_risks": [],
  "recommendations": [
    "Output looks good!",
    "Consider adding error scenarios (invalid password, account locked)"
  ]
}
```

**Invalid output example:**
```json
{
  "is_valid": false,
  "confidence_score": 0.42,
  "hallucination_risks": [
    {
      "risk_type": "invalid_syntax",
      "description": "Missing 'Given' step in scenario",
      "severity": "high"
    },
    {
      "risk_type": "ungrounded_claim",
      "description": "References 'SMS authentication' not in context",
      "severity": "medium"
    }
  ],
  "recommendations": [
    "Fix Gherkin syntax errors before using",
    "Verify SMS authentication feature exists before testing"
  ]
}
```

---

## Error Responses

### 400 Bad Request
```json
{
  "detail": "Validation error: 'story' must be at least 10 characters"
}
```

### 401 Unauthorized
```json
{
  "detail": "Not authenticated. Token required."
}
```

### 403 Forbidden
```json
{
  "detail": "Insufficient permissions. Requires 'ai.generate' permission."
}
```

### 500 Internal Server Error
```json
{
  "detail": "LLM service error: All models failed. Check AI_PROVIDER configuration."
}
```

---

## Rate Limits

- Requests per minute: 60 (per user)
- Requests per hour: 1000 (per organization)
- Token budget per request: 2000 (input) + 2000 (output)

---

## Cost Tracking

All API calls are logged with token usage and cost:

```bash
# Check costs by feature
SELECT feature, COUNT(*) as calls, SUM(tokens_input + tokens_output) as total_tokens, 
       SUM(cost_usd) as total_cost 
FROM sd_ai_audit_log 
WHERE ts >= NOW() - INTERVAL '7 days'
GROUP BY feature;
```

---

## Testing with Docker

```bash
# Start services
docker compose up -d postgres redis

# Run backend
make backend-dev

# Get JWT token (replace with real credentials)
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "password"}'

# Copy token and use in Authorization header above
```

---

## Troubleshooting

**Q: Getting "All LLM models failed"**
- A: Check AI_PROVIDER env var and ensure LLM service is running
- If using Ollama: `docker run -d -p 11434:11434 ollama/ollama && ollama pull qwen2.5:14b`

**Q: Hallucination validator rejecting valid output**
- A: Check confidence_score threshold. Default is 0.7. Lower if too strict.

**Q: API calls are slow**
- A: Check which model is responding (in response). Ollama slower than Groq. Adjust AI_ROUTING_MODE to "cost_optimized" for speed.

**Q: High costs**
- A: Monitor sd_ai_cost_log table. Set AI_LOCAL_ONLY=true to use Ollama only (free).
