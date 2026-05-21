# ADR — {{ID}}: {{TITLE}}

> **Status:** Proposed | Accepted | Superseded  
> **Input:** proposal.md (onaylı seçenek)  
> **By:** architect-{{agent_id}} on {{date}}  
> **Paralel:** design.md (designer aynı anda çalışıyor/çalıştı)

---

## Context

<Problem + approver'ın onayladığı yön. 2-3 paragraf.>

---

## Decision

<Ne yapacağız — 1-2 cümle net karar>

---

## Scope

**Etkilenen katmanlar:**
- [ ] Frontend (`apps/web/`)
- [ ] Backend (`backend/`)
- [ ] Engine (`engine/`)
- [ ] Infra (`docker-compose*.yml`, `.github/workflows/`)
- [ ] Database (migration)
- [ ] Docs

---

## Data Flow

```
[Client] → GET /api/v1/navigation
  → [Router: navigation.py]
    → [Service: navigation_service.py]
      → [DB: navigation_menu table]
    ← Response
  ← 200 { "items": [...] }
```

Veya sequence diagram (mermaid/ascii).

---

## API Contract (varsa)

### Yeni endpoint: `GET /api/v1/navigation`

**Request:**
```http
GET /api/v1/navigation
Authorization: Bearer <token>
```

**Response 200:**
```json
{
  "items": [
    { "id": "dashboard", "label_key": "nav.dashboard", "href": "/dashboard", "icon": "home" }
  ]
}
```

**Errors:**
- 401 unauthorized
- 500 server error

---

## Data Model (varsa)

### Yeni tablo: `navigation_menu`

```sql
CREATE TABLE navigation_menu (
  id           UUID PRIMARY KEY,
  key          VARCHAR(64) UNIQUE NOT NULL,
  label_key    VARCHAR(128) NOT NULL,
  href         VARCHAR(255) NOT NULL,
  icon         VARCHAR(64),
  parent_id    UUID REFERENCES navigation_menu(id),
  display_order INTEGER NOT NULL DEFAULT 0,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_nav_parent ON navigation_menu(parent_id);
```

Migration: `backend/alembic/versions/<timestamp>_{{ID}}.py`

---

## State Management (FE)

- **Server state:** React Query, key: `['navigation']`, stale-time: 5 min
- **Client state:** yok (server-driven)
- **Persistence:** yok (her session fresh fetch)

---

## Module / File Layout

```
backend/app/domains/navigation/
  ├── router.py      # GET /api/v1/navigation
  ├── service.py     # fetch_menu, order items
  ├── schemas.py     # NavigationItem, NavigationResponse
  └── models.py      # SQLAlchemy model

apps/web/
  ├── components/ui/navigation-menu.tsx   # yeni
  ├── lib/hooks/use-navigation.ts         # React Query hook
  └── app/(dashboard)/layout.tsx          # kullanım
```

---

## Test Strategy

| Seviye | Ne | Nerede |
|---|---|---|
| Unit | `service.fetch_menu` — order, parent-child | `backend/tests/navigation/test_service.py` |
| Integration | `GET /api/v1/navigation` auth+response | `backend/tests/navigation/test_router.py` |
| FE unit | `useNavigation` hook cache davranışı | `apps/web/__tests__/use-navigation.test.ts` |
| E2E | Sidebar'dan dashboard'a navigate | `e2e/navigation/sidebar.spec.ts` |
| A11y E2E | Keyboard-only navigation | `e2e/a11y/sidebar.spec.ts` |

---

## Breaking Changes

- [ ] Var — açıkla + rollout plan
- [x] Yok — backward compatible

---

## Rollout Plan

1. Backend deploy (endpoint + migration)
2. Feature flag: `FF_NEW_NAVIGATION=1` default off
3. FE deploy, flag off durumda eski menü, on durumda yeni
4. Canary: %10 kullanıcı 1 gün
5. Genel aç

Feature flag dosyası: `backend/app/domains/feature_flags/` + FE `use-feature-flag.ts`

---

## Alternatives Considered

- **Seçenek A (minimum):** Hardcoded menu — reddedildi, CMS dinamikliği lazım
- **Seçenek C (ideal):** Full CMS entegrasyonu — reddedildi, efor L+ ve bu scope için overkill

---

## Risks & Mitigations

| Risk | Olasılık | Etki | Mitigation |
|---|---|---|---|
| Migration başarısız | düşük | yüksek | Staging'de test, down migration hazır |
| Cache invalidation race | orta | orta | ETag + revalidate on mutate |
| A11y regresyonu | düşük | yüksek | E2E a11y test, manual screen reader check |

---

## Open Questions

- [ ] Cache TTL 5 dk mı 15 mi? (benchmark sonrası karar)
- [ ] Soft delete mi hard mi? (CMS ekibi onayı)

---

[pipeline: architect {{ID}}]
