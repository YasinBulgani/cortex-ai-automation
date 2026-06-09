# Neurex Database Schema & ER Diagram

**Last Updated:** 2026-06-09  
**Database:** PostgreSQL 16 with pgvector extension  
**RLS Strategy:** Row Level Security per tenant_id  
**Migrations:** Alembic (60+ versions)

---

## Quick Overview

### Connection Details
- **Host:** postgres (Docker) or configured DB_HOST
- **Port:** 5432
- **Database:** syndata_db
- **Extension:** pgvector (AI embeddings)

### Core Tables (60+ total)

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `organizations` | Tenant root | id, name, subscription_plan |
| `users` | User accounts | id, email, tenant_id, password_hash |
| `projects` | Workspaces | id, tenant_id, name, status |
| `test_cases` | Test suite | id, project_id, title, priority, automation_status |
| `test_runs` | Execution records | id, project_id, status, passed_count, failed_count |
| `test_run_results` | Individual results | id, test_run_id, test_case_id, status |
| `defects` | Bugs | id, project_id, severity, status, jira_issue_key |
| `automations` | Test workflows | id, project_id, type, script_content, status |
| `api_tests` | API test suite | id, project_id, method, endpoint |
| `audit_logs` | All operations | id, tenant_id, user_id, action, entity_type |

### Multi-Tenancy (RLS)

Every table has `tenant_id` column. PostgreSQL Row Level Security automatically filters by tenant:

```sql
CREATE POLICY org_isolation ON test_cases
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);
```

Backend sets context per request:
```python
await session.execute(
    text("SET app.current_tenant_id = :tenant_id"),
    {"tenant_id": current_user.tenant_id}
)
```

### Indexes

Performance indexes automatically created by migrations:
- Tenant isolation: `(tenant_id, project_id)` on all main tables
- Time-series: `created_at DESC` for reports
- Foreign keys: `(test_run_id)`, `(test_case_id)` on results
- Vector search: `ivfflat` on `test_cases.embedding`

### Key Constraints

- Primary key: UUID (v4)
- Foreign keys: CASCADE where appropriate, RESTRICT for critical
- Unique: `(tenant_id, email)` on users, etc
- Soft deletes: `deleted_at` column on all entities

---

## Entity Relationships

```
organizations (root)
  ├─► users (tenant members)
  ├─► teams
  │   └─► team_members
  ├─► projects
  │   ├─► test_cases
  │   │   ├─► test_case_steps
  │   │   ├─► test_case_tags
  │   │   └─► test_case_metrics
  │   ├─► test_runs
  │   │   └─► test_run_results
  │   ├─► automations
  │   │   ├─► automation_runs
  │   │   └─► automation_schedules
  │   ├─► api_tests
  │   ├─► defects
  │   └─► webhooks
  └─► audit_logs
```

---

## Migrations

### Running Migrations
```bash
# Upgrade to latest
alembic upgrade head

# Check status
alembic current

# View history
alembic history
```

### Recent Migrations (as of 2026-06-09)
- `20260609_0005_composite_indexes.py` — Performance indexes
- `20260609_0004_cascade_and_audit_fixes.py` — Referential integrity
- `20260609_0003_expand_cost_usd_precision.py` — Billing precision
- `20260609_0001_rls_new_mgmt_tables.py` — Management domain tables

---

## Vector Storage (pgvector)

AI-driven test case similarity search:

```sql
CREATE INDEX idx_test_cases_embedding ON test_cases 
  USING ivfflat (embedding vector_cosine_ops) 
  WITH (lists = 100);
```

Usage:
```python
async def find_similar_cases(embedding, limit=5):
    result = await session.execute(
        text("""
            SELECT id, title, embedding <-> :embedding AS distance
            FROM test_cases
            ORDER BY distance LIMIT :limit
        """),
        {"embedding": embedding, "limit": limit}
    )
    return result.fetchall()
```

---

## Backup & Recovery

**Production Backups:**
- Frequency: Daily at 2 AM UTC
- Retention: 30 days
- Type: Full + incremental (pg_dump + WAL)
- Storage: S3 encrypted

**Restore Procedure:**
```bash
pg_restore -h postgres -U neurex_user -d syndata_db < backup.sql
```

---

For detailed schema documentation, indexes, constraints, and common queries, see **docs/02_DATABASE_SCHEMA_FULL.md**

