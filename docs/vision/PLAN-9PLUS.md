# Neurex QA — 9+ Kalite Hedefli Derinlikli Yeniden Mimarileme

> **Not:** Bu plan pragmatik kestirme yapmaz. Mimari, frontend, backend ve production olgunluğunda hepsi 9/10+ hedeflenir. Süre kısıtı yoktur. Doğru olanı yapmak öncelikli.

---

## 0. Bugünkü Durum vs Hedef

| Boyut | Bugün | Hedef | Açık |
|-------|-------|-------|------|
| Mimari | 6/10 | **9.5/10** | 3 backend → 1, monorepo, DDD, event-driven |
| Frontend | 8/10 | **9.5/10** | RSC, Server Actions, Lighthouse 100, Storybook |
| Backend | 5/10 | **9.5/10** | Async-first, CQRS, repository pattern, gRPC internal |
| Production | 4/10 | **9.5/10** | mTLS, secret mgmt, APM, k8s + helm, DR plan |
| Test | 1/10 | **9/10** | Unit + integration + e2e + visual + load |
| Güvenlik | 4/10 | **9.5/10** | httpOnly auth, CSRF, RBAC, SOC2 trail, pen-test |
| Veri | 5/10 | **9/10** | Migrations, partitioning, backup PITR, read replicas |
| Erişilebilirlik | 7/10 | **9/10** | WCAG 2.2 AA tam, screen reader test, motor-impair |
| i18n | 3/10 | **9/10** | TR/EN/AR, RTL, ICU MessageFormat |
| Gözlemlenebilirlik | 2/10 | **9/10** | OpenTelemetry, traces + metrics + logs unified |

---

## 1. North Star — Ne Olmak İstiyoruz

Şu cümleyi 1 yıl içinde gerçeklemek:

> **Neurex QA, AI-native bir QA operasyon merkezi — Linear / Stripe / Vercel seviyesinde polish, Datadog / GitLab seviyesinde derinlik, Cypress / Playwright seviyesinde test özelliği. Bir QA ekibinin bilmesi gereken her şey burada, ve AI 7/24 yardımcı.**

Bu hedefin somut karşılığı:
- **TTI < 800ms** (median), **Lighthouse 100/100** tüm sayfalarda
- **API p99 < 150ms** (read), **< 500ms** (write)
- **%99.95 uptime** (8h/yıl downtime tolerated)
- **<100ms time-to-AI-first-token**
- **0 known critical security issue**
- **WCAG 2.2 AA** tam uyum + AAA hedef
- **3 dil** (TR/EN/AR) + RTL
- **Single binary deployment** opsiyonu (self-hosted için)

---

## 2. Mimari Yeniden Yapılanma

### 2.1 Backend Konsolidasyonu — 3 Servis → 1 + 1 Worker

```
ÖNCE                          SONRA
─────                          ─────
FastAPI :8000  (backend)       FastAPI :8000  (api)
Flask   :5001  (engine)   →    └─ engine module
FastAPI :8080  (ai-gateway)    └─ ai-gateway module
                               └─ uvicorn + uvloop
                               
                               Celery worker pool (async tasks)
                               └─ Redis broker
                               └─ test execution
                               └─ ai inference offloading
```

**Migration Stratejisi:**
1. **Hafta 1-2**: Flask Engine'i FastAPI'ye port et. Aynı route'lar, aynı response shape.
2. **Hafta 2-3**: ai-gateway'i `backend/app/services/ai/` altına taşı. Internal call (Python function) yap.
3. **Hafta 3-4**: API consumer'ları güncelle, backwards-compat şim'leri kaldır.
4. **Hafta 5+**: Celery worker pool kur, uzun süren işleri (test runs, AI batch) buraya kaydır.

**Net kazanım:** 
- 3 ops point → 1 ops point
- Inter-service auth (X-Internal-Key) yok → Python function call
- Single Python version, single deps, single deploy

### 2.2 Domain-Driven Design — Bounded Context'ler

Backend'i şu context'lere böl:

```
services/api/src/
├─ contexts/
│  ├─ identity/              # Kimlik, RBAC, oturum
│  │  ├─ domain/
│  │  │  ├─ user.py          # Aggregate root
│  │  │  ├─ role.py
│  │  │  └─ session.py
│  │  ├─ application/        # Use cases
│  │  │  ├─ login.py
│  │  │  └─ rotate_token.py
│  │  ├─ infrastructure/
│  │  │  ├─ user_repo.py     # SQLAlchemy
│  │  │  └─ jwt_service.py
│  │  └─ api/
│  │     └─ routes.py
│  ├─ projects/              # Proje yaşam döngüsü
│  ├─ scenarios/             # Senaryo CRUD + versiyon
│  ├─ execution/             # Koşu/test run engine
│  ├─ ai/                    # AI orchestration
│  ├─ data/                  # Sentetik veri
│  └─ reporting/             # Raporlama, analitik
├─ shared/
│  ├─ kernel/                # Value objects, base aggregate
│  ├─ events/                # Event bus, domain events
│  └─ outbox/                # Outbox pattern (event reliability)
└─ adapters/
   ├─ db/                    # SQLAlchemy 2.0 typed
   ├─ cache/                 # Redis
   ├─ queue/                 # Celery
   └─ telemetry/             # OpenTelemetry
```

**Her context kendi modelini, kendi service'ini, kendi route'unu içerir. Cross-context iletişim sadece domain event'leri üzerinden.**

### 2.3 CQRS — Command / Query Separation

Yazma ve okuma yollarını ayır:

```python
# COMMAND tarafı — domain logic, validation, events
@dataclass
class CreateScenarioCommand:
    project_id: ProjectId
    title: str
    description: str
    actor: UserId

class CreateScenarioHandler:
    async def handle(self, cmd: CreateScenarioCommand) -> ScenarioId:
        # Aggregate yükle, business rule uygula
        project = await self.repo.get(cmd.project_id)
        scenario = project.create_scenario(cmd.title, cmd.description, cmd.actor)
        await self.repo.save(project)
        await self.event_bus.publish(scenario.events)
        return scenario.id

# QUERY tarafı — optimize edilmiş read modeller
@dataclass
class ScenarioListView:
    id: str
    title: str
    last_run_at: datetime | None
    pass_rate: float | None

class ScenarioListQuery:
    async def execute(self, project_id: str, filters: Filters) -> list[ScenarioListView]:
        # Doğrudan denormalized read model'den (Postgres view, materialized view)
        return await self.read_db.fetch_all(...)
```

**Faydası:**
- Read query'leri write modellerinden bağımsız optimize edilir
- Materialized view'lar + indexler doğrudan UI ihtiyacına göre
- API'nin response shape'i istemci ihtiyacını yansıtır, DB shape'ini değil

### 2.4 Event-Driven Architecture

Tüm cross-context iletişim **domain event'leri** üzerinden:

```python
# Domain event
@dataclass(frozen=True)
class ScenarioCreated:
    scenario_id: str
    project_id: str
    actor: str
    occurred_at: datetime

# Subscriber'lar bağımsız context'lerden
@subscribe(ScenarioCreated)
async def index_for_search(event: ScenarioCreated):
    await search_service.index(event.scenario_id)

@subscribe(ScenarioCreated)
async def update_dashboard_counter(event: ScenarioCreated):
    await metrics.increment('scenarios_created', project_id=event.project_id)

@subscribe(ScenarioCreated)
async def notify_team(event: ScenarioCreated):
    await notifications.send(...)
```

**Altyapı:**
- **Outbox pattern**: Event'ler önce DB'ye yazılır (transaction içinde), sonra publisher worker bunları broker'a (Redis/RabbitMQ) iter. Garantili teslimat.
- **Idempotent handler'lar**: Aynı event 2× gelirse problem olmaz.
- **Dead letter queue**: Başarısız event'ler kayıp olmaz.

### 2.5 Monorepo (Turborepo)

```
neurex-qa/
├─ apps/
│  ├─ web/                   # Next.js 14 (RSC ağırlıklı)
│  ├─ docs/                  # Nextra-based dev docs
│  └─ storybook/             # Component showcase
├─ services/
│  ├─ api/                   # Consolidated FastAPI
│  └─ worker/                # Celery worker
├─ packages/
│  ├─ design-system/         # @neurex/design-system
│  │  ├─ tokens/             # Design tokens (JSON + TS + CSS)
│  │  ├─ primitives/         # Avatar, Tooltip, Button, ...
│  │  ├─ patterns/           # StatCard, EmptyState, ...
│  │  └─ themes/             # Light, Dark, Per-product
│  ├─ contracts/             # OpenAPI-generated TS types
│  ├─ ai-sdk/                # @neurex/ai (LLM router + tools)
│  ├─ dsl/                   # @neurex/dsl (test DSL parser)
│  └─ tsconfig/              # Shared tsconfig
├─ infra/
│  ├─ docker/                # Dockerfile'lar
│  ├─ k8s/                   # Helm charts
│  ├─ terraform/             # Infra as code
│  └─ scripts/               # Deploy, backup, migration
├─ tests/
│  ├─ e2e/                   # Playwright cross-app
│  ├─ load/                  # k6 load tests
│  └─ visual/                # Chromatic / Percy
└─ turbo.json                # Turborepo cache config
```

**Turborepo faydaları:**
- Incremental builds (sadece değişen paketi build et)
- Cache her şey (test, lint, build, type-check)
- Remote cache (vercel/aws s3) ile CI 3× hızlı
- Parallel pipeline'lar

---

## 3. Frontend Derinleştirme

### 3.1 React Server Components Migration

**Bugün:** Her sayfa `"use client"`. SPA gibi davranıyor.

**Hedef:** Sayfaların %80'i server component, sadece interactive bölgeler client.

**Strateji:**
```tsx
// app/(dashboard)/portfolio/page.tsx — SERVER component
import { getProjects } from "@/lib/data/projects";
import { ProjectListClient } from "./_client";  // ✨ Sadece arama/filter client

export default async function PortfolioPage() {
  const projects = await getProjects();  // Server'da fetch, JS sıfır
  return (
    <div>
      <h1>Projeler</h1>
      <ProjectListClient initialProjects={projects} />
    </div>
  );
}
```

**Server Actions** (mutations):
```tsx
"use server";

export async function createProject(formData: FormData) {
  const name = formData.get("name");
  const project = await api.projects.create({ name });
  revalidatePath("/portfolio");
  return project;
}
```

**Streaming SSR:**
```tsx
<Suspense fallback={<StatsSkeleton />}>
  <Stats />  {/* Async server component */}
</Suspense>
<Suspense fallback={<ActivitySkeleton />}>
  <Activity />
</Suspense>
```

**Performans hedefleri:**
- Bundle size: **<150KB** gzipped per page
- TTI: **<800ms** median
- LCP: **<1.5s**
- INP: **<200ms**

### 3.2 Tasarım Sistemi Olgunlaşması

**packages/design-system/** olarak ayrı paket:

```
@neurex/design-system
├─ src/
│  ├─ tokens/                # Style Dictionary kaynağı
│  │  ├─ core.json           # Renk, spacing, typography
│  │  ├─ semantic.json       # Surface, fg, brand
│  │  └─ component.json      # Button, Input, Card değerleri
│  ├─ primitives/
│  │  ├─ Button/
│  │  │  ├─ Button.tsx
│  │  │  ├─ Button.stories.tsx     ← Storybook
│  │  │  ├─ Button.test.tsx        ← Vitest
│  │  │  ├─ Button.a11y.test.tsx   ← jest-axe
│  │  │  └─ Button.module.css      ← Scoped CSS
│  │  └─ ...
│  ├─ patterns/              # Compound components
│  │  ├─ DataTable/          # Sort + filter + virtualize + paginate
│  │  ├─ Form/               # React Hook Form + Zod entegre
│  │  ├─ Combobox/           # Radix + cmdk
│  │  └─ DashboardCard/      # Stat + Sparkline + Tooltip
│  ├─ icons/                 # Lucide subset + custom
│  └─ index.ts
├─ docs/                     # Bileşen kullanım docs (Storybook)
└─ package.json
```

**Style Dictionary** ile tokens single-source-of-truth:
- `tokens.json` → `tokens.css` (web) + `Tokens.swift` (mobile) + `tokens.kt` (android) + `tokens.json` (figma)

**Storybook:**
- Tüm bileşenlerin yaşayan dokümantasyonu
- Chromatic ile visual regression
- a11y addon (her bileşen WCAG-test)
- Interaction tests (jest-dom + testing-library)

### 3.3 Real-time & Collaboration

**Multi-user presence:**
```tsx
<PresenceProvider room={`project:${projectId}`}>
  <Editor />
  <CursorOverlay />     {/* Diğer kullanıcıların imleci */}
  <PresenceAvatars />   {/* Sağ üst: kim aktif */}
</PresenceProvider>
```

**Altyapı:** 
- **Yjs** veya **Liveblocks** CRDT
- WebSocket gateway backend'de
- Conflict resolution otomatik

**Live updates:**
- Senaryo listesi sayfasında biri yeni senaryo eklerse anlık görünür
- Test koşusu sırasında progress canlı akar (her step için event)
- Bildirimler push tabanlı (poll değil)

### 3.4 AI Derinleştirme

**Şu an:** Sağ panel sohbet + global komut.

**Hedef:** AI **her sayfaya gömülü**, görünmez asistan.

**Inline AI:**
```tsx
<ScenarioEditor>
  <AIInlineActions>
    <AISuggestStep />      {/* "Sonraki adım öner" */}
    <AIRewrite />          {/* Seçili metni iyileştir */}
    <AIExplain />          {/* "Bu satır ne yapar?" */}
  </AIInlineActions>
</ScenarioEditor>
```

**Smart suggestions:**
- Form alanı focuses → AI autocomplete önerir (kullanıcı geçmişine + proje contextine göre)
- Hata mesajı görünür → "🔧 Bu hatayı analiz et" butonu otomatik gelir
- 5 saniye inaktif → "Yardım gerekir mi?" pasif öneri

**Natural language navigation:**
```
Command palette'e yaz: "son hafta failed mobil testler"
                    ↓
        AI parse eder, filtre uygular, doğru sayfaya gider
```

**AI cost transparency:**
- Her sayfada AI status chip "saniyede $0.002 harcadın"
- Project bazında AI bütçesi
- Provider routing (Groq hızlı/ucuz, Claude kaliteli)

### 3.5 Performans Detaylı

**Bundle optimizasyon:**
- Route-based code splitting (otomatik Next.js)
- Dynamic import lazy heavy comp'lar (ReactFlow, Monaco)
- Image: AVIF/WebP otomatik (next/image)
- Font: variable, subset, preload critical glyphs
- CSS: critical inline, rest async

**Cache stratejisi:**
- HTTP cache: ISR (Incremental Static Regeneration) statik sayfalar için
- TanStack Query: stale-while-revalidate, prefetch on hover
- Service Worker: offline-first navigation
- Browser cache: long max-age, content-hash naming

**Lighthouse hedefi: 100/100/100/100** (Performance + A11y + Best Practices + SEO)

### 3.6 i18n & RTL

**Library:** `next-intl` veya `next-i18next`

**Çeviri organizasyonu:**
```
locales/
├─ tr.json
├─ en.json
└─ ar.json
```

**Format:** ICU MessageFormat (plural, gender, datetime):
```json
{
  "scenarios.count": "{count, plural, =0 {senaryo yok} =1 {1 senaryo} other {# senaryo}}"
}
```

**RTL:** Tailwind `rtl:` prefix + logical properties (`ms-`/`me-` instead of `ml-`/`mr-`).

**Date/Number:** `Intl.DateTimeFormat`, `Intl.NumberFormat` (browser-native).

---

## 4. Backend Derinleştirme

### 4.1 Async-First Python

**SQLAlchemy 2.0 async** + **typed**:
```python
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

class Project(Base):
    __tablename__ = "projects"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255))
    
class ProjectRepo:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get(self, id: UUID) -> Project | None:
        return await self.session.scalar(
            select(Project).where(Project.id == id)
        )
```

**Connection pool tuning:**
- pool_size=20, max_overflow=10
- pool_pre_ping=True (lost connection detection)
- async_engine_cls=AsyncEngine

### 4.2 Caching Layers

**3 katman:**
1. **In-process** (Python `functools.lru_cache`) — config, constants
2. **Redis** — session, hot data (project list, user permissions)
3. **CDN** — public static assets, ISR pages

**Invalidation:**
- Domain event ile cache invalidate
- `ProjectUpdated` → Redis key `project:{id}` silinir
- Tag-based invalidation (tek anahtar üzerinden tüm bağlı cache'ler)

### 4.3 Background Jobs (Celery)

**Long-running işler workera kayar:**

```python
@celery.task(bind=True, max_retries=3)
def run_test_suite(self, project_id: str, scenario_ids: list[str]):
    try:
        runner = PlaywrightRunner(project_id)
        for sid in scenario_ids:
            self.update_state(state='RUNNING', meta={'current': sid})
            result = runner.run(sid)
            publish_event(TestExecuted(scenario_id=sid, result=result))
    except Exception as e:
        raise self.retry(exc=e, countdown=60)
```

**Queue separation:**
- `default` — normal işler
- `priority` — kritik (rate limit yüksek)
- `slow` — saatlerce sürebilen (test runs)
- `ai` — AI inference (provider rate limit gözeterek)

**Monitoring:** Flower (Celery dashboard) + Sentry.

### 4.4 API Design

**REST + GraphQL hibrit:**
- REST: kaynak CRUD, basit endpoint'ler
- GraphQL (`/graphql`): karmaşık nested query'ler (dashboard sayfası gibi)
- WebSocket (`/ws`): real-time events

**Tüm endpoint'ler:**
- OpenAPI 3.1 spec auto-generated
- Versionlanmış (`/api/v1/`, `/api/v2/`)
- Rate limited (slowapi, kullanıcı bazlı)
- Idempotent mutation'lar (Idempotency-Key header)
- ETag + If-None-Match (304 desteği)
- Pagination: cursor-based (offset değil)

**Type safety end-to-end:**
- Backend: Pydantic 2 + msgspec
- Contract: OpenAPI export
- Frontend: openapi-typescript ile auto-generate `@neurex/contracts`
- Frontend hook'ları typed: `useProject(id)` → `Project | undefined`

### 4.5 Database

**PostgreSQL 16:**
- Migrations: Alembic, branch-aware
- Partitioning: `executions` tablosu aylık partition (3157 proje çok run üretir)
- Indexes: covered indexes, partial indexes
- Materialized views: dashboard query'leri için
- pg_stat_statements + auto_explain (slow query detection)
- Read replica: read-heavy query'ler için
- Logical replication: warm standby

**Migration strategy:**
- Zero-downtime: 3-step pattern (add column nullable → backfill → make required)
- Forward-only (no migration rollback assumed in prod)
- Migration tests (her migration için)

**Backup:**
- PITR (Point-in-time recovery) — Postgres WAL
- Daily snapshot (S3)
- Restore drill quarterly

---

## 5. Production Readiness — 9+ Anlamı

### 5.1 Güvenlik

**Authentication:**
- **httpOnly + Secure + SameSite=Strict cookie**
- Access token (short, 15 dk) + Refresh token (long, 30 gün, rotating)
- Refresh token Postgres'te hashlenmiş, sadece yeni refresh oluşturulurken eski blacklist
- CSRF token double-submit pattern
- OAuth2 + SAML 2.0 (enterprise SSO) opsiyonu
- 2FA (TOTP) zorunlu admin için

**Authorization:**
- RBAC (Role-Based Access Control)
- Permission'lar fine-grained (`projects.read`, `scenarios.create`, `admin.users.write`)
- Backend her endpoint'te decorator ile check:
  ```python
  @router.post("/projects")
  @require_permission("projects.create")
  async def create_project(...): ...
  ```
- Frontend sadece UI gating (visual). Gerçek koruma backend.

**Network güvenliği:**
- TLS 1.3 her yerde
- HSTS preload
- CSP strict (no inline scripts)
- X-Frame-Options DENY
- mTLS service-to-service
- Cloudflare/AWS WAF önde

**Secret management:**
- Vault veya AWS Secrets Manager
- Secrets rotation otomatik (quarterly)
- Hiçbir secret git'te yok (gitleaks scan CI'da)
- Dev/staging/prod ayrı (no leak)

**Compliance:**
- GDPR: data export, deletion right, audit log
- SOC2 trail: tüm admin aksiyonu audit log'da
- Pen-test yıllık
- SAST (Snyk/Semgrep) + DAST (OWASP ZAP) CI'da

### 5.2 Gözlemlenebilirlik

**OpenTelemetry full stack:**
```
Frontend (Sentry + OTel browser SDK)
     ↓
Backend (FastAPI OTel auto-instrument)
     ↓
DB (pg_stat + OTel SQL spans)
     ↓
Redis, Celery (OTel exporters)
     ↓
Collector → Jaeger (traces) + Prometheus (metrics) + Loki (logs)
     ↓
Grafana (unified dashboard)
```

**3 pillar:**
1. **Traces** — Request lifecycle, slow query detection
2. **Metrics** — RED method (Rate, Errors, Duration) per endpoint
3. **Logs** — Structured JSON, correlation ID

**Dashboards:**
- Overview: traffic, errors, latency
- Per-tenant: hangi proje en çok kullanıyor
- AI metrics: token kullanımı, provider hit ratio, cost
- DB: slow queries, connection pool, lock contention
- Business: signup, daily active, retention

**Alerting:**
- PagerDuty / Opsgenie
- SLO bazlı (error budget yandı → alert)
- 5dk içinde p99 > 500ms → warning
- 1dk içinde error rate > %2 → page

### 5.3 Deployment

**Containerization:**
- Distroless base images (saldırı yüzeyi minimum)
- Multi-stage build (50MB final image hedef)
- Non-root user
- Read-only root filesystem

**Kubernetes:**
- Helm chart (`charts/neurex-qa/`)
- Resource limits + requests
- HPA (Horizontal Pod Autoscaler) CPU + custom metric
- PDB (PodDisruptionBudget) availability
- NetworkPolicy (zero-trust internal)
- Init containers (DB migration)
- Liveness + readiness + startup probes

**CI/CD:**
- GitHub Actions
- PR → run tests + lint + type + security scans
- Merge → build images → push registry → deploy staging
- Manual approval → prod deploy (blue/green)
- Automatic rollback on health check fail
- Deploy time < 5dk hedef

**Feature flags:**
- LaunchDarkly veya PostHog
- A/B test infrastructure
- Kill switch her ana feature için
- Tenant bazlı rollout

### 5.4 Disaster Recovery

- **RPO 5dk** (Recovery Point Objective)
- **RTO 1sa** (Recovery Time Objective)
- Multi-region warm standby (eu-west + us-east)
- Quarterly DR drill (gerçekten failover yap)
- Data backup test (restore et, çalışıyor mu doğrula)
- Runbook yazılı her senaryo için

### 5.5 Documentation

- **Developer docs** (Nextra) — onboarding, ADR'ler, troubleshooting
- **User docs** — kullanıcı rehberi, video tutorial
- **API docs** — OpenAPI Swagger + ReDoc
- **Internal wiki** — runbook, on-call playbook
- **Changelog** — kullanıcıya görünür, ne değişti
- **Architecture diagrams** — C4 model (Context → Container → Component → Code)

---

## 6. Test Stratejisi

### 6.1 Test Piramidi

```
                  ▲
                 ╱ ╲
                ╱E2E╲           %5  — Playwright cross-browser
               ╱─────╲
              ╱integration╲      %20 — API contract, DB-up
             ╱─────────────╲
            ╱    component   ╲   %30 — RTL + Storybook
           ╱───────────────────╲
          ╱        unit         ╲ %45 — Vitest + pytest
         ╱───────────────────────╲
```

### 6.2 Coverage Hedefleri

- **Domain logic**: %95+ (business kuralları test edilmemiş = bug)
- **API endpoints**: %90+
- **UI components**: %80+ (etkileşim odaklı)
- **E2E happy paths**: %100 (login, create scenario, run test)

### 6.3 Test Türleri

**Unit:**
- Frontend: Vitest + React Testing Library + jest-dom
- Backend: pytest + pytest-asyncio + factory_boy

**Component:**
- Storybook play functions (interaction tests)
- Chromatic visual regression

**Integration:**
- Frontend: API mock w/ MSW
- Backend: TestContainers (real Postgres + Redis)

**Contract:**
- Pact veya schemathesis (OpenAPI fuzz)
- Backend response uyumluluğu garanti

**E2E:**
- Playwright + multi-browser (Chromium, Firefox, WebKit)
- Tenant izolasyonu (her test kendi tenant'ı yaratır)
- Visual regression (her sayfanın critical view'ı)

**Load:**
- k6 (10k RPS hedef)
- Soak test (24 saat sabit yük)
- Spike test (10x ani artış)

**A11y:**
- jest-axe component testlerinde
- Pa11y CI sayfa-level
- VoiceOver / NVDA manual quarterly

**Security:**
- OWASP ZAP CI'da
- Snyk dependency scan
- Semgrep SAST
- gitleaks secret scan

---

## 7. Erişilebilirlik (WCAG 2.2 AA → AAA Hedef)

### 7.1 Klavye-only kullanılabilirlik

- **Her interactive element** Tab ile erişilebilir
- **Focus indicator** her zaman görünür (zaten ekledik)
- **Skip links** her ana bölüm için
- **Klavye trap yok** (modal'lardan Escape ile çık)
- **Klavye kısayolları** dokümante (`?` ile yardım)

### 7.2 Screen Reader

- **ARIA landmarks**: `<header>`, `<main>`, `<nav>`, `<aside>`
- **Semantic HTML** doğru (button vs div'e onclick)
- **Live regions**: `aria-live="polite"` toast'lar, `aria-live="assertive"` errors
- **Status announcements**: form submit sonrası "Kaydedildi" sesli
- **Image alt text** anlamlı (decorative ise `alt=""`)
- **Form errors** `aria-describedby` ile bağlı

### 7.3 Motor Bozukluk

- **Tıklanabilir alan min 44×44**
- **Drag alternative** (every drag has a button equivalent)
- **No timeout** veya extend opsiyonu
- **Touch + mouse + keyboard** her interaction çalışır

### 7.4 Görsel

- **Contrast WCAG AAA** (7:1 text, 4.5:1 large)
- **Color not sole indicator** (status badge'inde icon + text + renk)
- **Resize 200%** layout bozulmaz
- **Reduce motion** media query (zaten var)
- **High contrast mode** (zaten ekledik)
- **Dark mode** + Light mode (light eklenmeli)

### 7.5 Kognitif

- **Açık, basit dil** (TR sade)
- **Progress göstergeleri** uzun işlemler için
- **Onay diyalogu** geri alınamaz aksiyonlar için
- **Error recovery** her error mesajı çözüm önerir
- **Yardım her sayfada** (?ikonu, AI asistan)

---

## 8. Aşamalı Geçiş Planı

### Çeyrek 1 (Hafta 1-12)

**Tema: Sağlam temeller**

| Hafta | Faz | Çıktı |
|-------|-----|-------|
| 1-2 | Monorepo + Turborepo kur | Builds, caching, shared packages |
| 1-2 | `@neurex/design-system` çıkar | Tasarım sistemi ayrı paket |
| 3 | Storybook + Chromatic | Visual regression altyapısı |
| 4 | OpenAPI → @neurex/contracts | Type-safe FE/BE |
| 5-6 | Auth refactor (httpOnly cookie) | XSS açığı kapanır |
| 7-8 | Flask Engine → FastAPI port | 3 servis → 2 |
| 9-10 | AI Gateway internal modüle | 2 servis → 1 |
| 11-12 | Celery worker pool + outbox | Async iş altyapısı |

### Çeyrek 2 (Hafta 13-24)

**Tema: Backend olgunlaşması**

| Hafta | Faz | Çıktı |
|-------|-----|-------|
| 13-14 | DDD bounded context'ler | Identity, Projects, Scenarios |
| 15-16 | CQRS yapısı | Read/Write ayrımı |
| 17 | Event bus + Outbox | Domain event'ler |
| 18-19 | SQLAlchemy 2.0 typed + repos | Type-safe data access |
| 20 | Caching layers (Redis) | Hot data |
| 21-22 | Background jobs (Celery) | Test execution, AI batch |
| 23 | Rate limiting + idempotency | API hardening |
| 24 | OpenTelemetry full instrument | Traces visible |

### Çeyrek 3 (Hafta 25-36)

**Tema: Frontend devrimi**

| Hafta | Faz | Çıktı |
|-------|-----|-------|
| 25-26 | RSC migration başla (pages) | Server components |
| 27 | Server Actions (mutations) | Form'lar |
| 28 | Streaming SSR | Suspense boundary'ler |
| 29-30 | Real-time presence (Liveblocks) | Multi-user awareness |
| 31 | WebSocket gateway | Live updates |
| 32 | Inline AI everywhere | Editor + form alanlarda |
| 33 | Charts library (recharts) | Heatmap, sankey, timeline |
| 34 | i18n setup (TR/EN/AR) | next-intl |
| 35 | RTL desteği | Logical properties |
| 36 | Performance push (Lighthouse 100) | Bundle, image, cache |

### Çeyrek 4 (Hafta 37-48)

**Tema: Production-grade**

| Hafta | Faz | Çıktı |
|-------|-----|-------|
| 37 | k8s + Helm chart | Container orchestration |
| 38 | mTLS internal | Zero-trust |
| 39 | Vault secret management | Secrets rotation |
| 40 | Backup + PITR + DR drill | Felaketten kurtarma |
| 41-42 | E2E test full coverage | Playwright comprehensive |
| 43 | Load test (k6) | 10k RPS |
| 44 | Security audit (3rd party) | Pen-test, SAST, DAST |
| 45 | A11y audit (3rd party) | WCAG 2.2 AA cert |
| 46 | Feature flags (LaunchDarkly) | Safe rollout |
| 47 | Analytics + funnel (PostHog) | Product insights |
| 48 | Documentation final pass | Dev + user docs |

### Çeyrek 5+ (Hafta 49+)

**Tema: AI native, scale, polish**

- Multi-tenant izolasyon (Postgres RLS)
- Self-hosted opsiyon (single-binary)
- Plugin sistemi (3rd party DSL extension)
- Mobile app (React Native)
- Public API + webhook ecosystem
- Marketplace (test scenario template'leri paylaşılır)

---

## 9. Karar Kayıtları (ADR — Architecture Decision Records)

Aşağıdaki kararlar git'te `docs/adr/` altında YAML olarak tutulacak:

**ADR-001: Monorepo over Polyrepo**
- Karar: Turborepo monorepo
- Nedeni: Atomic cross-package değişiklik, shared paketler, single CI
- Alternatifler: Nx (rejected: kompleks), Lerna (rejected: maintenance), Polyrepo (rejected: sync zor)

**ADR-002: PostgreSQL only (no Mongo, no MySQL)**
- Karar: Postgres 16
- Nedeni: JSONB, partial index, FTS, partitioning, mature
- Alternatifler: MongoDB (rejected: relations), CockroachDB (rejected: prematüre)

**ADR-003: FastAPI over Django**
- Karar: FastAPI + uvicorn
- Nedeni: Async-first, OpenAPI native, type-safe (Pydantic 2)
- Alternatifler: Django (rejected: sync legacy), Litestar (rejected: smaller ecosystem)

**ADR-004: Next.js App Router over Pages Router**
- Karar: App Router + RSC
- Nedeni: Server Components, streaming, layouts, modern
- Alternatifler: Remix (rejected: smaller ecosystem), Solid (rejected: maturity)

**ADR-005: cmdk over building own**
- Karar: cmdk library
- Nedeni: Battle-tested, a11y built-in, small bundle
- Trade-off: External dep maintenance

**ADR-006: Liveblocks over self-hosted Yjs**
- Karar: Liveblocks (ilk fazda)
- Nedeni: Plug-and-play, presence + storage + history
- Migration path: Yjs self-host (Y2'de)

**ADR-007: Celery over RQ over Dramatiq**
- Karar: Celery
- Nedeni: Mature, Flower dashboard, Sentry integration
- Trade-off: Setup karmaşıklığı

**ADR-008: httpOnly cookie over localStorage JWT**
- Karar: httpOnly + Secure + SameSite cookie
- Nedeni: XSS koruması
- Trade-off: CSRF token gerekli, ama daha güvenli

**ADR-009: GraphQL only for complex reads**
- Karar: REST default + GraphQL `/graphql` endpoint
- Nedeni: REST simple, GraphQL where N+1 ortaya çıkar
- Alternatifler: REST only (rejected: dashboard query'leri zor), GraphQL only (rejected: cache complex)

**ADR-010: OpenTelemetry over vendor-specific**
- Karar: OTel + Jaeger + Prometheus + Loki
- Nedeni: Open standard, vendor lock-in yok
- Alternatifler: Datadog (rejected: cost), New Relic (rejected: vendor lock-in)

---

## 10. Stack Final Hali

### Frontend
- **Framework**: Next.js 14 App Router
- **UI**: React 18 + RSC
- **Styling**: Tailwind CSS + design tokens
- **State**: Zustand (UI) + TanStack Query (server)
- **Forms**: React Hook Form + Zod
- **Animations**: Framer Motion
- **Charts**: Recharts + Visx
- **Tables**: TanStack Table + react-virtual
- **Real-time**: Liveblocks → Yjs (eventually)
- **Testing**: Vitest + RTL + Playwright + Chromatic
- **Build**: Turborepo + SWC

### Backend
- **Language**: Python 3.12+
- **Framework**: FastAPI + uvicorn (uvloop)
- **ORM**: SQLAlchemy 2.0 (async, typed)
- **Validation**: Pydantic 2 + msgspec
- **Migrations**: Alembic
- **Queue**: Celery + Redis broker
- **Cache**: Redis (3 layer)
- **Search**: Postgres FTS → Meilisearch (Y2)
- **Events**: Redis Streams (outbox pattern)
- **AI**: Multi-provider router (Groq, Claude, Gemini, Ollama)
- **Testing**: pytest + pytest-asyncio + TestContainers

### Infrastructure
- **Container**: Docker (distroless)
- **Orchestration**: Kubernetes + Helm
- **IaC**: Terraform
- **Secrets**: HashiCorp Vault
- **Observability**: OpenTelemetry → Jaeger + Prometheus + Loki + Grafana
- **APM**: Sentry (frontend errors)
- **CI/CD**: GitHub Actions
- **Feature flags**: PostHog (analytics + flags)
- **CDN**: Cloudflare
- **DB hosting**: Crunchy Data / Supabase (managed Postgres)
- **Queue hosting**: Upstash Redis / managed
- **Storage**: S3-compatible (Cloudflare R2 / AWS S3)

### DevEx
- **Docs**: Nextra
- **Storybook**: ladle/Storybook
- **Visual regression**: Chromatic
- **API docs**: OpenAPI → Scalar / ReDoc
- **DB migrations**: Atlas (visual diff)
- **Local dev**: docker-compose + tilt
- **Linter**: biome (frontend) + ruff (backend)
- **Formatter**: biome + ruff format
- **Type check**: tsc + mypy strict

---

## 11. Hangi Şirket Olmak İstiyoruz?

**Aspirational benchmark'lar:**

| Şirket | Bizden Ne Öğreneceğiz |
|--------|----------------------|
| **Linear** | UX'in hızı, klavye, polish, micro-animasyon |
| **Stripe** | Dokümantasyon, developer experience, API tasarımı |
| **Vercel** | Performance obsession, Lighthouse, RSC mastery |
| **Notion** | Flexibility, kullanıcı kişiselleştirme |
| **Datadog** | Observability derinliği, dashboard zenginliği |
| **GitLab** | Open source, self-hosted opsiyon, plugin sistemi |
| **PostHog** | Product analytics, feature flag, in-product onboarding |
| **Sentry** | Error tracking quality, dev workflow |
| **Cypress** | Test platformu visualization |
| **Plaid** | Security trust, compliance reporting |

**Anti-pattern'ler (kaçınılan):**
- Salesforce — Mavi/bulut zerafetsiz UX
- Jira — Yüklenme süresi, complexity
- Generic SAP UIs — Aşırı dolu, modal-içinde-modal
- AWS Console — Tutarsızlık, eski sayfa karışımı

---

## 12. Başarı Kriterleri — 9+ Anlamı

Her boyut için somut, ölçülebilir kriterler:

### Mimari 9+
- ✅ Tek backend servisi
- ✅ Net DDD context'ler (en az 6)
- ✅ Event-driven cross-context
- ✅ CQRS read/write ayrımı
- ✅ Outbox pattern güvenilir delivery
- ✅ Monorepo + Turborepo cache
- ✅ Tip-güvenli FE/BE contract
- ✅ ADR'ler dokümante
- ✅ Async-first

### Frontend 9+
- ✅ Lighthouse 100/100/100/100
- ✅ Bundle <150KB per page
- ✅ TTI <800ms
- ✅ %80 RSC, %20 client
- ✅ Storybook'ta her component
- ✅ Visual regression CI
- ✅ Real-time multi-user
- ✅ i18n TR/EN/AR + RTL
- ✅ A11y WCAG 2.2 AA cert

### Backend 9+
- ✅ p99 < 150ms read, < 500ms write
- ✅ Async %100
- ✅ Type-safe (mypy strict)
- ✅ Test coverage >%85
- ✅ Event-driven, outbox-backed
- ✅ Rate limited + idempotent
- ✅ OpenAPI auto + contract-tested
- ✅ Celery queue separation
- ✅ Caching 3-layer

### Production 9+
- ✅ %99.95 uptime SLA
- ✅ TLS 1.3 + HSTS preload
- ✅ httpOnly auth + CSRF
- ✅ mTLS internal
- ✅ Vault secrets + rotation
- ✅ OTel full instrument
- ✅ k8s + HPA + PDB
- ✅ Blue/green deploy
- ✅ DR drill geçti
- ✅ Pen-test temiz

### Test 9+
- ✅ Unit %90+ coverage
- ✅ Integration %80+
- ✅ E2E happy paths %100
- ✅ Visual regression
- ✅ Load test 10k RPS
- ✅ A11y CI'da
- ✅ Security scan CI'da
- ✅ Contract test

### Güvenlik 9+
- ✅ OWASP Top 10 cover
- ✅ SOC2 trail
- ✅ GDPR uyumlu
- ✅ 3rd party pen-test temiz
- ✅ Bug bounty program
- ✅ Incident response plan

---

## 13. Sonsöz

Bu plan **pragmatik kısa yol almaz**. Hedef:

> "5 yıl sonra bile bakanın 'vay be, bu nasıl güzel kodlanmış' diyeceği bir sistem."

Her karar:
1. **Geri dönülemez** mi → Çok dikkat
2. **Geri dönülebilir** mi → Cesur ol, dene

Birinciler için ADR şart. İkinciler için spike kabul.

**Yapma listesi (zaman gelmedi):**
- Microservices (DDD context'ler yetiyor)
- Kafka (Redis Streams yeterli ilk faz)
- Kubernetes Mesh (Istio çoğunlukla overkill)
- Multi-cloud (vendor pricing devamına kadar gerek yok)

**Hedef**: 12 ay sonunda Linear + Stripe + Datadog hibridi bir platform.

İlk yapacak iş: **Çeyrek 1 Hafta 1-2 — Monorepo + Design System paket çıkarma.**
