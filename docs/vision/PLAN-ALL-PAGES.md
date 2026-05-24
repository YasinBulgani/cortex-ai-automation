# Neurex QA — Tüm Sayfalar İçin Detaylı Geliştirme Planı

> **Kapsam:** 50+ sayfa, 4 ana kategori (Global, Proje, Auth, Standalone)
> **Hedef:** Her sayfa 9/10 — gerçek API + iyi UX + temiz kod
> **Süre tahmini:** Faz 1: 1 hafta · Faz 2-4: ~3 hafta

---

## ÖZET DURUM

| Kategori | Sayı | İyi | Kısmi | Eksik |
|----------|------|-----|-------|-------|
| Global   | 16   | 10  | 4     | 2     |
| Proje    | 33   | 19  | 10    | 4     |
| Auth     | 4    | 3   | 1     | 0     |
| Backend  | 3 ctx | 3  | 0     | 0     |

---

## FAZ 1 — Hızlı Kazanımlar (3-5 gün)

### 1.1 AI Agents Hub (`/ai-agents`)
**Mevcut:** 95 satır, sadece statik `agents-data.ts` array
**Sorun:** Backend'de `/api/v1/agents-v2` var ama UI bağlı değil

**Yapılacak:**
- `useAgentsCatalog()` hook'u ekle → `GET /api/v1/agents-v2`
- Real agent listesi + statik fallback (offline mod)
- "Run Agent" butonu → `POST /api/v1/agents-v2/{id}/run` + result modal
- Filtering: kategori, durum (active/beta/experimental), son çalışma
- Search: kategoride sıralı arama
- Agent detay sayfası: `/ai-agents/[agentId]` (yeni)
  - Çalışma geçmişi, parametreler, son sonuç, prompt template

**Dosyalar:**
- `apps/web/app/(dashboard)/ai-agents/page.tsx` (revize)
- `apps/web/app/(dashboard)/ai-agents/[agentId]/page.tsx` (yeni)
- `apps/web/lib/hooks/use-agents.ts` (`useAgentsCatalog`, `useRunAgent`)

---

### 1.2 DSL Catalog (`/dsl-catalog`)
**Mevcut:** 10 satır wrapper — `<DslCatalogView />` çağırıyor
**Sorun:** Component yüklü ama global sayfa minimal — semantic arama yok

**Yapılacak:**
- DslCatalogView içinde tab eklendi mi kontrol: "All / Recent / Project-specific"
- Semantic arama: `POST /api/v1/dsl/search` (vektör arama)
- Action editör: kopyala butonu + "Test Et" inline runner
- Versiyon geçmişi drawer
- Git commit/PR flow (Bitbucket entegrasyonu)

**Dosyalar:**
- `apps/web/components/dsl/DslCatalogView.tsx`
- `apps/web/components/dsl/DslSearchBar.tsx` (yeni — semantic)
- `apps/web/components/dsl/DslVersionDrawer.tsx` (yeni)

---

### 1.3 Healing Dashboard (`/p/[id]/healing`)
**Mevcut:** 172 satır, hook bağlı ama UI dar
**Yapılacak:**
- Timeline view: son 30 healing event'i
- Kategori breakdown: pie chart (timeout 23%, auth 18%, vs.)
- Locator self-heal başarı oranı (% kaç locator otomatik düzeldi)
- "Manual Heal" butonu: kırık locator'ı manuel düzelt
- Hook: `useHealingHistory()` + `useApplyHeal()`

---

### 1.4 Prioritize Page (`/p/[id]/prioritize`)
**Mevcut:** 299 satır, hook bağlı (`usePrioritizedTests`)
**Yapılacak:**
- Risk matrix görselleştirme (likelihood × impact)
- "Optimal Suite" butonu: AI önerisi → top 20 test
- Test seçimi → tek tıkla run queue
- Filter: severity, last_run, owner
- Trend chart: priorty değişim son 14 gün

---

### 1.5 Environments Page (`/p/[id]/environments`)
**Mevcut:** 536 satır, hook bağlı (`useEnvironments`)
**Yapılacak:**
- Env karşılaştırma view (dev/staging/prod yan yana)
- Secret detection: gizli değişkenleri otomatik maskele
- Env'ler arası clone: "Production → Staging kopyala"
- Test connection button: `POST /api/v1/environments/{id}/test`
- Export/import: `.env` dosyası, JSON, Vault

---

## FAZ 2 — Orta Önceli (5-7 gün)

### 2.1 API Testing (`/p/[id]/api-testing`) — REFACTOR
**Mevcut:** 981 satır tek dosyada
**Sorun:** Çok büyük, sürdürülebilir değil

**Yapılacak:**
- Dosyayı parçala:
  ```
  api-testing/
  ├── page.tsx                 (200 satır — orchestration)
  ├── components/
  │   ├── EndpointList.tsx     (200 satır)
  │   ├── RequestBuilder.tsx   (200 satır)
  │   ├── ResponseViewer.tsx   (150 satır)
  │   ├── TestCaseTable.tsx    (150 satır)
  │   └── AiGenerateModal.tsx  (100 satır)
  ```
- Postman-style request builder UX
- Response diff: 2 farklı çalıştırma karşılaştır
- Curl + Postman export
- Save to Postman Collection

---

### 2.2 Monkey Testing (`/p/[id]/monkey`) — REFACTOR
**Mevcut:** 1314 satır — projedeki en büyük dosya
**Yapılacak:**
- Parçala: `MonkeySession.tsx`, `MonkeyConfig.tsx`, `MonkeyResults.tsx`, `MonkeyHeatmap.tsx`
- Real-time monkey runner (WebSocket)
- Action heatmap: hangi UI elementine kaç kez tıklandı
- Crash report otomatik aggregator
- Session replay (rrweb integration)

---

### 2.3 Recorder Page (`/p/[id]/recorder`)
**Yapılacak:**
- Playwright Codegen entegrasyonu
- Browser launch button → record session → BDD'ye çevir
- Selector intelligence: AI ile robust locator önerisi
- Video kaydı + adım adım timeline

---

### 2.4 Manual Testing (`/p/[id]/manual`)
**Yapılacak:**
- Test case checklist runner
- Defect log integration
- Screenshot upload + annotation
- Test cycle: progress bar (12/45 tamamlandı)

---

### 2.5 Locators Page (`/p/[id]/locators`)
**Yapılacak:**
- Locator inventory: tüm test'lerde kullanılan locator'lar
- Fragility score: hangileri sık değişiyor?
- Bulk rename
- AI locator hardener: kırılgan locator'ı dayanıklı hale getir

---

### 2.6 Accessibility (`/p/[id]/accessibility`)
**Yapılacak:**
- WCAG 2.1 AA + AAA tarama
- axe-core entegrasyonu
- Per-page accessibility score
- Issue list: severity, element selector, fix önerisi
- Heatmap: hangi sayfaların a11y skoru düşük

---

### 2.7 Security (`/p/[id]/security`)
**Yapılacak:**
- OWASP Top 10 otomatik tarama
- ZAP entegrasyonu
- Vulnerability detayı + remediation
- Compliance dashboard (SOC 2, ISO 27001)

---

## FAZ 3 — Yeni Sayfalar (5-7 gün)

### 3.1 Notifications Center (`/notifications`)
- Tüm bildirimler (run failed, healing applied, scheduled run)
- Filter: read/unread, severity
- Real-time WebSocket
- Subscribe: Slack, Discord, Teams, email
- Bildirim kuralları: "Failed run + production → Slack"

### 3.2 Audit Log (`/admin/audit`)
- Tüm sistem aksiyonları (kim, ne zaman, ne yaptı)
- Filter: actor, action, resource
- Export CSV/JSON
- Compliance için zorunlu

### 3.3 Billing (`/admin/billing`)
- Plan: Free/Pro/Enterprise
- Usage: senaryo, run, AI token
- Invoice geçmişi
- Stripe entegrasyonu
- Tenant-level limit

### 3.4 Onboarding Wizard (`/onboarding/start`)
- 5 adım: workspace → project → first scenario → run → invite team
- Progress tracker
- Skip button (dev'ler için)
- Tutorial videos embed

### 3.5 Workspace Settings (`/admin/workspace`)
- Tenant ayarları (logo, isim, SSO)
- Üye yönetimi + roller
- API token'lar
- Webhook'lar

---

## FAZ 4 — Cross-Cutting İyileştirmeler (3-5 gün)

### 4.1 Tutarlı UX Pattern'leri
- **EmptyState:** Tüm boş listeler aynı bileşeni kullansın
- **LoadingState:** Skeleton'lar tutarlı
- **ErrorBoundary:** Her sayfada granular error handling
- **Toast:** Başarı/hata mesajları tek standartta
- **ConfirmDialog:** Silme aksiyonları için zorunlu

### 4.2 Accessibility (Sitewide)
- Skip nav linki
- Tüm interaktif öğelere keyboard navigation
- ARIA label tarama: missing alt, missing label
- Focus visible: tüm butonlarda ring-2

### 4.3 Performance
- Code splitting: her route ayrı bundle
- Image optimization: next/image kullan
- Virtualization: 100+ item listeler için
- Prefetch: hover'da link prefetch
- Service Worker: offline support

### 4.4 i18n
- Tüm string'ler `useTranslations()` ile (next-intl)
- TR/EN minimum
- Date/number formatting locale-aware
- RTL desteği (Arabic için altyapı)

### 4.5 Test Coverage
- E2E: Playwright — top 10 user flow
- Unit: Vitest — her hook + util
- Visual regression: Chromatic / Percy
- Hedef: %80 line coverage

---

## SAYFA-SAYFA DURUM TABLOSU

### Global Pages (`apps/web/app/(dashboard)/`)

| Sayfa | Mevcut | Durum | Yapılacak |
|-------|--------|-------|-----------|
| `page.tsx` (Dashboard) | 278 sat, 3 API | ✅ 8/10 | WebSocket real-time |
| `portfolio/` | 413 sat, 3 API | ✅ 9/10 | Bulk action |
| `task-drafts/` | AI modal | ✅ 9/10 | Tamamlandı |
| `flow-designer/` | template + create | ✅ 9/10 | Tamamlandı |
| `ai-agents/` | statik | ⚠️ 4/10 | **FAZ 1.1** |
| `dsl-catalog/` | wrapper | ⚠️ 5/10 | **FAZ 1.2** |
| `nexus-code/` | 680 sat, 1 API | ⚠️ 6/10 | Bitbucket flow + history |
| `mobil-otomasyon/` | bilinmiyor | ⚠️ ? | İnceleme gerek |
| `ai-quality/` | bilinmiyor | ⚠️ ? | İnceleme gerek |
| `ide/` | 1036 sat | ⚠️ 7/10 | Refactor + Ctrl+S |
| `admin/users/` | bilinmiyor | ⚠️ ? | İnceleme gerek |
| `profile/` | bilinmiyor | ⚠️ ? | İnceleme gerek |
| `info/` | bilinmiyor | ⚠️ ? | Sistem bilgi sayfası |
| `symbols/` | bilinmiyor | ⚠️ ? | İnceleme gerek |
| `system/` | bilinmiyor | ⚠️ ? | İnceleme gerek |
| `onboarding/` | mevcut | ⚠️ 6/10 | **FAZ 3.4** |

### Proje Pages (`/p/[projectId]/`)

| Sayfa | Mevcut | Durum | Yapılacak |
|-------|--------|-------|-----------|
| `scenarios/` | 420 sat, 4 API | ✅ 8/10 | Bulk action |
| `runs/` | 458 sat, 3 API | ✅ 8/10 | Live tail |
| `reports/` | 444 sat, 3 API | ✅ 8/10 | Custom rapor |
| `settings/` | 162 sat, 4 API | ✅ 8/10 | Webhook tab |
| `cicd/` | 495 sat, 5 API | ✅ 8/10 | Pipeline editor |
| `flaky/` | 404 sat, 3 API | ✅ 8/10 | Auto-quarantine |
| `test-data/` | 296 sat, 7 API | ✅ 9/10 | En çok bağlı |
| `flows/` | 146 sat, 3 API | ✅ 8/10 | Trigger logs |
| `visual/` | 201 sat, 4 API | ✅ 7/10 | Diff viewer |
| `synthetic/` | bilinmiyor | ⚠️ ? | İnceleme gerek |
| `import/` | bilinmiyor | ⚠️ ? | TestRail/Zephyr import |
| `requirements/` | bilinmiyor | ⚠️ ? | Trace matrix |
| `chain-builder/` | mevcut | ⚠️ ? | İnceleme gerek |
| `schedules/` | bilinmiyor | ⚠️ ? | Cron UI |
| `integrations/` | bilinmiyor | ⚠️ ? | Jira/Slack/n8n |
| `analysis/` | bilinmiyor | ⚠️ ? | RCA dashboard |
| `automation/` | bilinmiyor | ⚠️ ? | İnceleme gerek |
| `approvals/` | bilinmiyor | ⚠️ ? | Workflow review |
| `playwright-console/` | mevcut | ⚠️ ? | Live console |
| `monkey/` | 1314 sat ⚠️ | 🔴 5/10 | **FAZ 2.2 REFACTOR** |
| `api-testing/` | 981 sat ⚠️ | 🔴 6/10 | **FAZ 2.1 REFACTOR** |
| `environments/` | 536 sat | ⚠️ 6/10 | **FAZ 1.5** |
| `healing/` | 172 sat | ⚠️ 6/10 | **FAZ 1.3** |
| `prioritize/` | 299 sat | ⚠️ 6/10 | **FAZ 1.4** |
| `recorder/` | bilinmiyor | ⚠️ ? | **FAZ 2.3** |
| `manual/` | bilinmiyor | ⚠️ ? | **FAZ 2.4** |
| `locators/` | bilinmiyor | ⚠️ ? | **FAZ 2.5** |
| `accessibility/` | bilinmiyor | ⚠️ ? | **FAZ 2.6** |
| `security/` | bilinmiyor | ⚠️ ? | **FAZ 2.7** |
| `mobile/` + `mobile/history/` | mevcut | ⚠️ ? | İnceleme gerek |
| `privacy/` | mevcut | ✅ | Statik OK |
| `sifir-bilgi/` | mevcut | ⚠️ ? | Zero-knowledge prov? |

---

## BACKEND EKSİKLERİ

### Yeni Bounded Context'ler (FAZ 5+)
- `notifications/` — bildirim merkezi
- `billing/` — Stripe + kullanım sayaçları  
- `audit/` — sistem aktivite logu
- `integrations/` — Jira/Slack/n8n webhook
- `reporting/` — custom rapor builder

### Mevcut Context'leri Geliştir
- **Identity:** OAuth (Google, GitHub), SSO (SAML)
- **Projects:** SQL repository implementation
- **Scenarios:** Version control (her published bir versiyon)
- **Execution:** Distributed run (multi-worker), live tail WebSocket

---

## KAYIT TUTMA

Her faz sonunda:
1. `git commit` — mesaj `feat(faz-X): ...`
2. `npm test` — geçmeli
3. `npm run typecheck` — sıfır hata
4. Bu plan dosyasını güncelle (✅ → tamamlandı)

---

## ÖNCELİK BÖLÜMLEMESİ

```
Hafta 1 (FAZ 1 — Hızlı kazanım):
  Pzt: ai-agents
  Sal: dsl-catalog + healing  
  Çar: prioritize + environments
  Per: nexus-code + ide refactor
  Cum: cross-cutting (toast/empty/error)

Hafta 2 (FAZ 2 — Refactor):
  Pzt-Sal: api-testing parçala
  Çar-Per: monkey parçala
  Cum: recorder + manual

Hafta 3 (FAZ 2 + 3):
  Pzt-Sal: accessibility + security + locators
  Çar-Per: notifications + audit
  Cum: billing + onboarding wizard

Hafta 4 (FAZ 4 — Polish):
  Cross-cutting + tests + i18n
```

---

## METRIKLER

| Metrik | Şimdi | Hedef (4 hafta sonra) |
|--------|-------|----------------------|
| Real API'ye bağlı sayfa | ~25/50 | 50/50 |
| Test coverage | %15 | %70 |
| Lighthouse | 80 ort. | 95 ort. |
| 1000+ satır dosya | 2 | 0 |
| TypeScript hata | 0 | 0 (continue) |
| Sayfa average rating | 6.5/10 | 9/10 |

---

**Toplam iş kalemi:** ~120 görev
**Tahmini süre:** 4 hafta (1 dev), 2 hafta (2 dev paralel)
**Risk faktörü:** Düşük — modüler iş bölümü, her parça bağımsız
