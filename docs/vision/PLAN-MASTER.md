# Neurex QA — Master Plan v2

> **Doğrulanmış audit verisine dayalı.** Her sayfa fiilen incelendi.
> **Format:** Sprint planlaması + kabul kriterleri + endpoint kontratları + risk skoru

---

## 🔥 KRİTİK BULGULAR (Audit Sonuçları)

### 1000+ Satır "God Components" — 6 Adet
| Sayfa | Satır | Fetch | TODO | Risk |
|-------|-------|-------|------|------|
| `mobil-otomasyon` (global) | **1386** | 2 | **26** | 🔴 |
| `monkey` | 1314 | 1 | 0 | 🔴 |
| `mobile` (proje) | 1222 | 5 | 0 | 🟠 |
| `locators` | 1103 | 1 | 0 | 🟠 |
| `ide` | 1036 | ? | 0 | 🟠 |
| `api-testing` | 981 | 0 | 0 | 🟠 |
| `playwright-console` | 929 | **0** | 0 | 🔴 (no API) |

### "İçi Boş" Sayfalar — Hiç Fetch Yok
| Sayfa | Satır | Sorun |
|-------|-------|-------|
| `playwright-console` | 929 | 929 satır UI, 0 backend |
| `sifir-bilgi` | 733 | 733 satır UI, 0 backend |
| `chain-builder` | 490 | 0 fetch, statik |
| `ai-quality` | 367 | 0 fetch |
| `accessibility` | 161 | 0 fetch |
| `info` | 112 | Statik (OK olabilir) |
| `symbols` | 136 | 0 fetch |
| `onboarding` | 101 | 0 fetch (wizard yok) |
| `import` | 144 | 0 fetch |

### Tamamen Eksik
- `system/` — sayfa yok bile

---

## 🎯 ÖNCELİK MATRİSİ (Etki × Maliyet)

```
                     YÜKSEK ETKİ
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
   🥇 SPRINT 1            │       🥈 SPRINT 2-3
   ai-agents              │       api-testing refactor
   playwright-console     │       monkey refactor
   accessibility          │       mobil-otomasyon
   onboarding wizard      │       chain-builder
        │                 │                 │
DÜŞÜK ─┼─────────────────┼─────────────────┼─ YÜKSEK
MALİYET│                 │                 │  MALİYET
   🥉 SPRINT 1 ucu       │       🚫 ERTELE
   healing fix           │       sifir-bilgi
   environments fix      │       locators (1103 satır)
   prioritize fix        │       playwright-console
        │                 │                 │
        └─────────────────┼─────────────────┘
                          │
                     DÜŞÜK ETKİ
```

---

## 📅 SPRINT 1 (Hafta 1) — Hızlı Kazanım

**Hedef:** 5 sayfa demo→real, ortalama skor 6.5 → 7.5

### S1-T01: AI Agents → Real Backend [2 gün]
**Mevcut:** `/ai-agents` 95 satır, static `agents-data.ts`

**Aksiyonlar:**
```ts
// apps/web/lib/hooks/use-agents.ts (genişlet)
export function useAgentsCatalog() {
  return useQuery(['agents'], () => apiFetch<Agent[]>('/api/v1/agents-v2'));
}

export function useRunAgent() {
  return useMutation((input: {id: string, params: object}) =>
    apiFetch(`/api/v1/agents-v2/${input.id}/run`, { method: 'POST', json: input.params })
  );
}
```

**Kabul kriteri:**
- [ ] `/api/v1/agents-v2` 200 dönerse real liste gösterilir
- [ ] API down ise `agents-data.ts` fallback gösterilir
- [ ] "Run" butonu modal açar, parametre form'u render, sonuç gösterir
- [ ] `/ai-agents/[agentId]` detay sayfası: history + last run + prompt template
- [ ] TypeScript hata yok, vitest pass

**Endpoint:** `GET /api/v1/agents-v2`, `POST /api/v1/agents-v2/{id}/run`

**Risk:** 🟢 Düşük — backend mevcut

---

### S1-T02: Healing Dashboard [1 gün]
**Mevcut:** 172 satır, `useHealingStats` bağlı ama dar

**Aksiyonlar:**
- Timeline component: son 30 heal event'i (HealingTimeline.tsx)
- Pie chart: kategori breakdown (recharts)
- Success rate StatCard
- "Manuel Heal" drawer: kırık locator → text input → apply

**Kabul kriteri:**
- [ ] `GET /api/v1/healing/events?limit=30` çağrılır
- [ ] Pie chart render
- [ ] Timeline'da her event'e tıklanır → detail drawer
- [ ] Mobile responsive

**Endpoint:** `GET /api/v1/healing/events`, `POST /api/v1/healing/apply`

**Risk:** 🟢 Düşük

---

### S1-T03: Environments Polish [1 gün]
**Mevcut:** 536 satır, hook bağlı

**Aksiyonlar:**
- Env karşılaştırma view: 3 sütunlu yan yana table (`<EnvCompareGrid />`)
- Secret detection: regex pattern matching (`password|token|secret|key`)
- Clone button: "Production → Staging" 
- Test connection: ping endpoint
- Export: `.env` text + JSON

**Kabul kriteri:**
- [ ] Yan yana 3 env karşılaştırma çalışır
- [ ] Secret değerler `••••••` ile maskelenir, "Reveal" toggle
- [ ] Clone confirm modal + success toast
- [ ] Test connection 200 = yeşil tick, error = kırmızı + hata

**Endpoint:** `POST /api/v1/environments/{id}/test`, `POST /api/v1/environments/{id}/clone`

**Risk:** 🟡 Orta — clone API yoksa backend ekle

---

### S1-T04: Prioritize Visual [1 gün]
**Mevcut:** 299 satır, hook bağlı

**Aksiyonlar:**
- Risk matrix scatter: likelihood (x) × impact (y), her test bir nokta
- "Optimal Suite" button → top 20 → bulk add to run queue
- Trend chart: priority değişim 14 gün
- Filter chips: severity, owner

**Kabul kriteri:**
- [ ] Scatter chart render (recharts)
- [ ] Multi-select → "Run Selected" buton aktif
- [ ] Trend chart line render

**Risk:** 🟢 Düşük

---

### S1-T05: Cross-Cutting UX [1 gün]
**Aksiyonlar:**
- `<EmptyState />` standartı: tüm boş listeler bunu kullansın
- `<LoadingSkeleton />` standartı
- `<ConfirmDialog />` zorunluluğu: tüm DELETE aksiyonları
- Toast unification: success/error/info/warning, 4s auto-dismiss
- Error boundary granular: her route layer'da

**Etki:** 50 sayfa için instant polish

---

## 📅 SPRINT 2 (Hafta 2) — Refactor + Boş Sayfalar

### S2-T06: API Testing Refactor [2 gün]
**Sorun:** 981 satır tek dosyada

**Hedef yapı:**
```
api-testing/
├── page.tsx                  200 satır (orchestration)
├── _components/
│   ├── EndpointTreeList.tsx  150
│   ├── RequestBuilder.tsx    200 (Postman-style)
│   ├── ResponseViewer.tsx    120 (syntax highlight)
│   ├── TestCaseTable.tsx     150
│   ├── AiGenerateModal.tsx   100
│   └── ImportSpecModal.tsx   80
└── _utils/
    ├── curl-export.ts
    └── postman-export.ts
```

**Yeni özellikler:**
- Curl + Postman + OpenAPI export
- Response diff (2 run karşılaştır)
- Save to Postman Collection
- Pre-request scripts (JS)

**Kabul kriteri:**
- [ ] Hiçbir dosya >250 satır
- [ ] Postman benzeri UX (sidebar tree + main panel + tabs)
- [ ] Vitest: her component bir test

**Risk:** 🟡 Orta — UX detayları

---

### S2-T07: Monkey Testing Refactor [2 gün]
**Sorun:** 1314 satır, 1 fetch

**Hedef yapı:**
```
monkey/
├── page.tsx                200 (orchestration)
├── _components/
│   ├── MonkeyConfig.tsx    150 (chaos params)
│   ├── MonkeySession.tsx   200 (live runner)
│   ├── MonkeyHeatmap.tsx   150 (click heatmap)
│   ├── CrashReport.tsx     100
│   └── SessionReplay.tsx   100 (rrweb)
└── _utils/
    └── chaos-policy.ts
```

**Yeni özellikler:**
- WebSocket live tail: her tıklama real-time
- Action heatmap: hangi element ne kadar tıklandı
- rrweb session replay
- Crash report aggregator

**Endpoint:** `WS /ws/monkey/{session_id}`, `GET /api/v1/monkey/sessions/{id}/heatmap`

**Risk:** 🟠 Yüksek — WebSocket altyapısı + rrweb integration

---

### S2-T08: Playwright Console (929 satır → real) [1 gün]
**Sorun:** 929 satır UI, sıfır fetch — kritik boş sayfa

**Aksiyonlar:**
- Backend endpoint: `POST /api/v1/playwright/exec` (Playwright MCP)
- Live console: xterm.js
- Screenshot capture: her command sonrası
- Session history: localStorage + backend

**Kabul kriteri:**
- [ ] Terminal-style command box
- [ ] `await page.goto(...)` execute olur
- [ ] Sonuç (screenshot + log) panelde
- [ ] Önceki komutlar history'de

**Risk:** 🔴 Yüksek — Playwright runner backend gerekli

---

### S2-T09: Onboarding Wizard [1 gün]
**Mevcut:** 101 satır, 0 fetch

**Aksiyonlar:**
- 5 adımlı wizard component:
  1. Workspace kur (isim, logo)
  2. İlk proje oluştur
  3. İlk senaryo (AI ile)
  4. İlk run (one-click)
  5. Takım davet et (email split)
- Progress dot tracker
- "Atla" butonu (her adımda)
- Tutorial video iframe

**Endpoint:** `POST /api/v1/onboarding/complete`

**Risk:** 🟢 Düşük

---

## 📅 SPRINT 3 (Hafta 3) — Yeni Sayfalar

### S3-T10: Notifications Center [2 gün]
**Yeni sayfa:** `/notifications`

**Features:**
- Inbox: run failed, heal applied, schedule executed
- Filter: read/unread, severity, source
- Real-time: WebSocket
- Rules: "Run failed + prod env → Slack"
- Subscriptions: Slack, Discord, Teams, email

**Backend (yeni):**
```
backend/app/contexts/notifications/
├── domain/
│   ├── notification.py (NotificationId, channel, severity)
│   ├── subscription.py
│   └── events.py
├── application/
│   ├── send_notification.py
│   ├── create_rule.py
│   └── queries.py
├── infrastructure/
└── api/
    └── notifications_router.py
```

**Kabul kriteri:**
- [ ] WebSocket connect, message gelir, badge artar
- [ ] Rule create → run failed event → Slack webhook test
- [ ] Mark all as read

---

### S3-T11: Audit Log [1 gün]
**Yeni sayfa:** `/admin/audit`

**Features:**
- Sistem aksiyonları tablosu (actor, action, resource, timestamp, ip)
- Filter: actor, action, date range, resource type
- Export CSV/JSON
- Tamper-evident: Merkle chain (zaten outbox event'lerinde var)

**Endpoint:** `GET /api/v1/audit/events?actor=&action=`

---

### S3-T12: Billing [2 gün]
**Yeni sayfa:** `/admin/billing`

**Features:**
- Plan card: current plan, usage progress bar
- Usage stats: scenario count, run count, AI token spend
- Invoice list + PDF download
- Plan upgrade modal (Stripe Checkout)
- Tenant-level limit warnings

**Backend (yeni):** `contexts/billing/` (Stripe wrapper)

**Risk:** 🟠 Stripe entegrasyonu, webhook gerekli

---

## 📅 SPRINT 4 (Hafta 4) — Polish + Test

### S4-T13: Sayfa Audit + Doldurma
Henüz incelenmemiş sayfalar:

| Sayfa | Mevcut | Plan |
|-------|--------|------|
| `mobil-otomasyon` | 1386 sat, 26 TODO | TODO'ları tek tek çöz veya delete |
| `chain-builder` | 490 sat, 0 fetch | API bağla / silinecek mi karar |
| `ai-quality` | 367 sat, 0 fetch | AI quality metrics dashboard |
| `accessibility` | 161 sat, 0 fetch | axe-core integration |
| `info` | 112 sat | Static sistem info OK |
| `symbols` | 136 sat | İncele, gerekirse sil |
| `sifir-bilgi` | 733 sat, 0 fetch | Zero-knowledge proof page — niş, ertele |
| `locators` | 1103 sat | Refactor + fragility score |
| `playwright-console` | 929 sat | S2-T08'de işlendi |
| `mobile` (proje) | 1222 sat, 5 fetch | Sadece refactor |
| `system` | YOK | Yeni sayfa: system health, env vars |

---

### S4-T14: i18n Migration [2 gün]
- next-intl install
- `apps/web/messages/tr.json` + `en.json`
- Tüm string'leri `t('key')`'e dönüştür (script ile)
- Language switcher (header)

---

### S4-T15: Test Coverage [2 gün]
- Playwright E2E: 10 critical flow
  1. Login → dashboard
  2. Create project
  3. Create scenario (AI mode)
  4. Run scenario
  5. View report
  6. Create environment
  7. Schedule run
  8. Reset password
  9. Invite team member
  10. Upgrade plan
- Vitest unit: tüm hook'lar + util'ler
- Coverage hedef: %70 line, %60 branch

---

## 📊 SAYFA-SAYFA DURUM (Doğrulanmış)

### Global (16 sayfa)

| # | Sayfa | Sat | Fetch | Skor | Aksiyon | Sprint |
|---|-------|-----|-------|------|---------|--------|
| 1 | `/` (Aktivite) | 278 | 3 | 8/10 | WebSocket | S3 |
| 2 | `portfolio` | 413 | 3 | 9/10 | Bulk action | S3 |
| 3 | `task-drafts` | 460 | 4 | 9/10 | ✅ Bitti | — |
| 4 | `flow-designer` | 273 | 2 | 9/10 | ✅ Bitti | — |
| 5 | `ai-agents` | 95 | 0 | 4/10 | Real API | **S1-T01** |
| 6 | `dsl-catalog` | 10 | 0 | 5/10 | Semantic search | S1 |
| 7 | `nexus-code` | 680 | 1 | 6/10 | History + diff | S2 |
| 8 | `mobil-otomasyon` | 1386 | 2 | 4/10 | TODO temizliği | **S4** |
| 9 | `ai-quality` | 367 | 0 | 5/10 | API bağla | S4 |
| 10 | `admin/users` | 178 | 2 | 7/10 | Role mgmt | S2 |
| 11 | `profile` | 314 | 2 | 7/10 | Avatar upload | S3 |
| 12 | `info` | 112 | 0 | 8/10 | Static OK | — |
| 13 | `symbols` | 136 | 0 | ?/10 | İncele | S4 |
| 14 | `system` | ❌YOK | - | 0/10 | Yeni sayfa | **S4** |
| 15 | `ide` | 1036 | ? | 7/10 | Refactor | S2 |
| 16 | `onboarding` | 101 | 0 | 5/10 | Wizard | **S2-T09** |

### Proje (33 sayfa)

| # | Sayfa | Sat | Fetch | Skor | Aksiyon | Sprint |
|---|-------|-----|-------|------|---------|--------|
| 1 | `scenarios` | 420 | 4 | 8/10 | Bulk | S3 |
| 2 | `scenarios/new` | ? | ? | ? | İncele | S4 |
| 3 | `scenarios/generate` | ? | ? | ? | AI gen | S2 |
| 4 | `scenarios/edit/[id]` | ? | ? | ? | İncele | S4 |
| 5 | `scenarios/[id]` | ? | ? | ? | İncele | S4 |
| 6 | `scenarios/[id]/versions` | ? | ? | ? | Diff view | S3 |
| 7 | `runs` | 458 | 3 | 8/10 | Live tail | S3 |
| 8 | `reports` | 444 | 3 | 8/10 | Custom report | S3 |
| 9 | `settings` | 162 | 4 | 8/10 | Webhook tab | S2 |
| 10 | `cicd` | 495 | 5 | 8/10 | Pipeline edit | S3 |
| 11 | `flaky` | 404 | 3 | 8/10 | Auto-quarantine | S3 |
| 12 | `test-data` | 296 | 7 | 9/10 | ✅ İyi | — |
| 13 | `flows` | 146 | 3 | 8/10 | Trigger logs | S3 |
| 14 | `flows/[flowId]` | ? | ? | ? | İncele | S4 |
| 15 | `visual` | 201 | 4 | 7/10 | Diff viewer | S2 |
| 16 | `synthetic` | 158 | 2 | 7/10 | İncele | S4 |
| 17 | `import` | 144 | 0 | 5/10 | TestRail/Zephyr | S3 |
| 18 | `requirements` | 337 | 2 | 7/10 | Trace matrix | S3 |
| 19 | `chain-builder` | 490 | 0 | 5/10 | API veya sil | **S4** |
| 20 | `schedules` | 715 | 9 | 8/10 | Refactor | S3 |
| 21 | `integrations` | 222 | 5 | 8/10 | İyi | S3 |
| 22 | `analysis` | 364 | 2 | 7/10 | RCA + AI | S3 |
| 23 | `automation` | 629 | 3 | 7/10 | Refactor | S3 |
| 24 | `approvals` | 354 | 2 | 7/10 | Workflow | S3 |
| 25 | `playwright-console` | 929 | **0** | 3/10 | Backend | **S2-T08** |
| 26 | `monkey` | 1314 | 1 | 5/10 | Refactor | **S2-T07** |
| 27 | `api-testing` | 981 | 0 | 6/10 | Refactor | **S2-T06** |
| 28 | `environments` | 536 | 0 | 6/10 | Polish | **S1-T03** |
| 29 | `healing` | 172 | 0 | 6/10 | Timeline+chart | **S1-T02** |
| 30 | `prioritize` | 299 | 0 | 6/10 | Risk matrix | **S1-T04** |
| 31 | `recorder` | 316 | 1 | 6/10 | Codegen | S2 |
| 32 | `manual` | 507 | 6 | 7/10 | Cycle UI | S3 |
| 33 | `locators` | 1103 | 1 | 5/10 | Refactor + fragility | **S4** |
| 34 | `accessibility` | 161 | 0 | 4/10 | axe-core | **S4** |
| 35 | `security` | 450 | 1hook | 6/10 | OWASP scan | S3 |
| 36 | `mobile` | 1222 | 5 | 7/10 | Refactor | S2 |
| 37 | `mobile/history` | ? | ? | ? | İncele | S4 |
| 38 | `sifir-bilgi` | 733 | 0 | 4/10 | Ertele | — |

---

## 🚦 GO/NO-GO KARARLARI

### Hemen Sil veya Erteleyelim:
- `sifir-bilgi` (733 sat, niş zero-knowledge): **ERTELE**
- `chain-builder` (490 sat, 0 fetch): **KARAR GEREK** — kullanıyor muyuz?

### Mutlaka Yapılacak:
- `mobil-otomasyon` 26 TODO temizliği
- `playwright-console` backend
- `monkey` + `api-testing` refactor

---

## 📈 BAŞARI METRİKLERİ

| Metrik | Şimdi | Sprint 1 | Sprint 2 | Sprint 3 | Sprint 4 |
|--------|-------|----------|----------|----------|----------|
| Real API bağlı sayfa | 25/50 | 30/50 | 36/50 | 44/50 | 48/50 |
| Ortalama skor | 6.5 | 7.2 | 7.8 | 8.4 | 9.0 |
| 1000+ satır dosya | 7 | 7 | 4 | 4 | 1 |
| TODO yorumu | 30+ | 25 | 15 | 5 | 0 |
| E2E test | 0 | 0 | 2 | 5 | 10 |
| Unit coverage | %15 | %25 | %40 | %55 | %70 |
| Lighthouse ort. | 80 | 85 | 88 | 92 | 95 |

---

## ⚙️ DEFINITION OF DONE (Her Görev İçin)

1. ✅ Kod yazıldı + linting temiz
2. ✅ TypeScript strict: 0 hata
3. ✅ Vitest unit test ≥1
4. ✅ Storybook story (UI component ise)
5. ✅ Empty state + loading state + error state
6. ✅ Mobile responsive (375px başlangıç)
7. ✅ A11y: keyboard navigation + ARIA
8. ✅ Toast/feedback eklendi
9. ✅ ConfirmDialog (destructive aksiyonda)
10. ✅ Git commit (semantic message)

---

## 🚀 BAŞLANGIÇ

**Hemen yapılacak (bu turn):**
1. Sprint 1'i başlat: **S1-T01 (AI Agents Real Backend)**
2. `useAgentsCatalog` hook yaz
3. UI gerçek API'ye bağla
4. Detay sayfası ekle
5. Commit + sonraki göreve geç

**Onay ister misin yoksa başlatayım mı?**
