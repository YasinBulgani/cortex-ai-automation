# 📐 Frontend Tasarım Karar Belgesi
**Management & QA Ekranları için**

**Tarih:** 2026-06-09  
**Durum:** 🔴 Onay Beklemede  
**Toplam Tasarım Sorunu:** 13+  
**Etkilenen Ekranlar:** 7

---

## 🎯 ÖN SÖZCÜ

Bu belge **Management Module** ve **QA Module** ekranlarındaki tasarım ve UX sorunlarını detaylı olarak listeler. Her sorun için:
- ✅ Mevcut durum ve problem
- ✅ Tasarım çözümü (mockup notları)
- ✅ Frontend teknik değişiklik
- ✅ Efor ve risk
- ✅ Onay durumu

---

## 📋 EKRAN: Case Detail Page

**Dosya:** `apps/web/app/(dashboard)/p/[projectId]/management/cases/[caseId]/page.tsx`  
**Sorumlu Bileşen:** `CaseDetailDrawer.tsx` (1095 satır)

### 🔴 SORUN #1: Lazy Tab Loading Yok

**DURUM:**
```
Şu anda: 6 sekme (Details, Steps, Evidence, Comments, Defects, History)
- Tümü sayfanın ilk yüklenmesinde fetch + render
- CaseDetailDrawer 1095 satır — hepsi initial bundle'da
- Sekme değişimi = full component re-render
```

**PROBLEM:**
- ⏱️ İlk sayfa yüklenmesi yavaş (Details + History ikisi de heavy)
- 📦 Bundle size gereksiz şişiyor
- ♻️ Tab switch'te RAM waste (unused tab data memory'de)

**TASARIM ÇÖZÜMÜ:**

| Sekme | Load Türü | Neden |
|-------|-----------|-------|
| **Details** | Immediate | Critical, user ilk açıyor |
| **History** | Immediate | Often accessed |
| **Steps** | Lazy | Large component, ~300 lines |
| **Evidence** | Lazy | Media heavy, fetch slow |
| **Comments** | Lazy | Thread loading can defer |
| **Defects** | Lazy | Related data, optional |

**FRONTEND DEĞİŞİKLİK:**

```tsx
// apps/web/.../management/_components/case-detail/
├─ CaseDetailDrawer.tsx (orchestrator)
├─ tabs/
│  ├─ CaseDetailsTab.tsx     (eager)
│  ├─ CaseHistoryTab.tsx     (eager)
│  ├─ CaseStepsTab.tsx       (lazy)
│  ├─ CaseEvidenceTab.tsx    (lazy)
│  ├─ CaseCommentsTab.tsx    (lazy)
│  └─ CaseDefectsTab.tsx     (lazy)
└─ CaseDetailSkeleton.tsx    (fallback)

// CaseDetailDrawer.tsx
const [activeTab, setActiveTab] = useState('details')

const CaseDetailsTab = lazy(() => import('./tabs/CaseDetailsTab'))
const CaseHistoryTab = lazy(() => import('./tabs/CaseHistoryTab'))
const CaseStepsTab = lazy(() => import('./tabs/CaseStepsTab'))
// ...

<Suspense fallback={<CaseDetailSkeleton />}>
  {activeTab === 'details' && <CaseDetailsTab caseId={caseId} />}
  {activeTab === 'steps' && <CaseStepsTab caseId={caseId} />}
  // ...
</Suspense>
```

**ONAY GEREKLI Mİ:** ❌ Hayır — hemen uygulanabilir  
**EFOR:** ⏱️ 6 saat (4 lazy tab oluştur, Suspense wire)  
**RİSK:** 🟢 Düşük (backward compatible)

---

### 🟡 SORUN #2: Form Validasyonları Scattered

**DURUM:**
```
Şu anda:
- Step title validation: CaseStepsTab.tsx'de
- Field validation: individual component'lerde
- Custom rules: useCallback hook'larda
- Error display: conditional render'larda
-> Type safety yok, test difficult
```

**PROBLEM:**
- 🔴 TypeScript strict mode: any type casting
- 🧪 Unit test: validation logic test edilemiyor
- 🔄 Reuse: başka form'da tekrar yazma

**TASARIM ÇÖZÜMÜ:**

```tsx
// apps/web/lib/schemas/management/case-detail.ts
import { z } from 'zod'

export const caseDetailsSchema = z.object({
  name: z.string().min(3, 'Min 3 char').max(200),
  description: z.string().optional(),
  priority: z.enum(['low', 'medium', 'high']),
  status: z.enum(['draft', 'active', 'completed']),
  assignee: z.string().uuid('Geçerli user ID').nullable(),
  tags: z.array(z.string()).max(10),
})

export const caseStepSchema = z.object({
  sequence: z.number().int().positive(),
  action: z.string().min(1),
  expectedResult: z.string().min(1),
  data: z.record(z.unknown()).optional(),
})

export type CaseDetailsFormData = z.infer<typeof caseDetailsSchema>
export type CaseStepFormData = z.infer<typeof caseStepSchema>
```

```tsx
// CaseDetailsTab.tsx
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { caseDetailsSchema } from '@/lib/schemas/management/case-detail'

function CaseDetailsTab({ caseId }) {
  const { register, formState: { errors }, watch } = useForm({
    resolver: zodResolver(caseDetailsSchema),
    defaultValues: caseData,
  })

  return (
    <form>
      <input {...register('name')} />
      {errors.name && <span className="error">{errors.name.message}</span>}
    </form>
  )
}
```

**ONAY GEREKLI Mİ:** ❌ Hayır  
**EFOR:** ⏱️ 4 saat (schema yazımı, form integration)  
**RİSK:** 🟢 Düşük

---

### 🔴 SORUN #3: Metadata Sidebar — Responsive Kırılmış

**DURUM:**
```
Şu anda:
- Sidebar sabit genişlik (250px)
- Tablet (768px): sidebar drawer'ı overlap ediyor
- Mobile (375px): tümü vertical stack — sidebar okunmuyor
- Drawer padding: sabit, mobile'da cut-off
```

**PROBLEM:**
- 📱 iPad/mobile: açılmayan tab'lar (z-index issue)
- 🎨 Metadata illegible (7px text)
- ❌ Dark mode: sidebar shadow invisible

**TASARIM ÇÖZÜMÜ:**

```
Mobile (< 640px):
  ├─ Drawer: full-width
  ├─ Metadata: collapsible accordion
  └─ Tabs: full height

Tablet (640px - 1024px):
  ├─ Drawer: 90vw
  ├─ Metadata: side panel (200px, scrollable)
  └─ Tabs: responsive

Desktop (> 1024px):
  ├─ Drawer: 800px
  ├─ Metadata: sidebar (250px, sticky)
  └─ Tabs: standard
```

**FRONTEND DEĞIŞIKLIK:**
```tsx
// CaseDetailDrawer.tsx
<div className="flex flex-col md:flex-row gap-4">
  <div className="flex-1 md:order-2">
    {/* Tabs */}
  </div>

  <div className="md:w-[250px] md:order-1 md:sticky md:top-20">
    <Accordion>
      <AccordionItem title="Case Info">
        {/* Metadata cards */}
      </AccordionItem>
    </Accordion>
  </div>
</div>

// Tailwind utilities
@media (max-width: 640px) {
  .sidebar-metadata {
    padding: 0.5rem; // 8px instead of 16px
    font-size: 12px; // readable
  }
}
```

**ONAY GEREKLI Mİ:** ✅ **EVET — Tasarım onayı**  
(Responsive breakpoint'lerin finalize'ı lazım)

**EFOR:** ⏱️ 5 saat  
**RİSK:** 🟠 Orta (layout shift risk)

---

### 🟡 SORUN #4: Step Editing UX — No Drag & Drop Feedback

**DURUM:**
```
Şu anda:
- Step list: 1, 2, 3, ... sekans
- Drag & drop: no visual feedback
- No reorder confirmation
- Undo: not available
```

**PROBLEM:**
- 😕 User: step sırasını değiştirdi mi bilemedi
- ⚠️ No confirmation — accidental reorder riski
- 🔄 Undo yok — Ctrl+Z çalışmıyor

**TASARIM ÇÖZÜMÜ:**

```
Step Reorder Flow:
1. User drag starts
   → Visual feedback: source step fade, highlight
2. Drag over target
   → Insert line appears
3. Drop
   → Optimistic update (local state)
   → API call (server persist)
   → Success toast "Step 3 moved up"
4. Error on save
   → Revert + error toast "Failed to reorder"
   → Undo button available 3s

Keyboard:
- Alt+↑ / Alt+↓ step move
- Ctrl+Z undo
```

**FRONTEND DEĞIŞIKLIK:**
```tsx
// Use TanStack React Query + optimistic updates
const reorderMutation = useMutation({
  mutationFn: (newOrder) => apiCall.updateStepOrder(newOrder),
  onMutate: (newOrder) => {
    // Optimistic update
    queryClient.setQueryData(['case', caseId], old => ({
      ...old,
      steps: newOrder
    }))
  },
  onError: (err, newOrder, context) => {
    // Revert
    queryClient.setQueryData(['case', caseId], context.previous)
    showErrorToast('Failed to reorder steps')
  }
})
```

**ONAY GEREKLI Mİ:** ✅ **EVET — UX Flow Onayı**  
(Undo duration, keyboard shortcuts vs mouse-only)

**EFOR:** ⏱️ 7 saat  
**RİSK:** 🟠 Orta (API error handling)

---

## 📋 EKRAN: Defects List Page

**Dosya:** `apps/web/app/(dashboard)/p/[projectId]/management/defects/page.tsx`

### 🔴 SORUN #1: Filter UI Mobile-Broken

**DURUM:**
```
Şu anda:
- Filter bar horizontal: desktop-only
- Mobile (< 640px): sidebar sağ kaydı
- Filters: inline, 3 tanesi görmek lazım scroll
- Result count: bottom of page
```

**PROBLEM:**
- 📱 Mobile: user filter'ları görmeden scroll ettiğinde unutuyor
- 🔍 Search input: filter sidebar'a gizli
- ⚠️ Active filter count: görünmüyor

**TASARIM ÇÖZÜMÜ:**

```
Mobile Filter Pattern:
┌─────────────────────┐
│ [Search] [Filters↓] │  (sticky header)
│ Active: 3          │
└─────────────────────┘
│ Defect Card 1       │
│ Defect Card 2       │
└─────────────────────┘

Desktop Filter Pattern:
┌─────────────────────────────────────────┐
│ [Search] │ Status │ Priority │ Assigned  │
│ Active: 3                                │
└─────────────────────────────────────────┘
│ Table (defect-id, title, priority, ...) │
```

**FRONTEND DEĞIŞIKLIK:**
```tsx
// DefectsPage.tsx

<div className="space-y-4">
  {/* Sticky header for mobile */}
  <div className="sticky top-0 z-20 bg-white dark:bg-gray-900 pd-4">
    <div className="flex gap-2">
      <Input placeholder="Search defects..." />
      
      {/* Mobile: dropdown */}
      <DropdownMenu>
        <Button variant="outline" size="sm">
          Filters <Badge>{activeFiltersCount}</Badge>
        </Button>
        <DropdownMenuContent className="w-56">
          {/* Filter checkboxes */}
        </DropdownMenuContent>
      </DropdownMenu>

      {/* Desktop: inline filters */}
      <div className="hidden md:flex gap-2">
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectContent>...</SelectContent>
        </Select>
        {/* More filters */}
      </div>
    </div>
    
    {/* Active filters (collapsible) */}
    {activeFilters.length > 0 && (
      <div className="mt-2 flex flex-wrap gap-2">
        {activeFilters.map(f => (
          <Badge key={f} variant="secondary" closable onClick={() => removeFilter(f)}>
            {f}
          </Badge>
        ))}
      </div>
    )}
  </div>

  {/* Defect list — different view by device */}
  <div className="md:hidden">
    {/* Card view for mobile */}
    {defects.map(d => <DefectCard key={d.id} defect={d} />)}
  </div>

  <div className="hidden md:block">
    {/* Table view for desktop */}
    <DataTable columns={columns} data={defects} />
  </div>
</div>
```

**ONAY GEREKLI Mİ:** ✅ **EVET — UI Pattern Onayı**  
(Card vs Table, filter positioning)

**EFOR:** ⏱️ 6 saat  
**RİSK:** 🟠 Orta

---

### 🔴 SORUN #2: Table Columns Hidden Mobile'da, Alternatif Yok

**DURUM:**
```
Şu anda:
- Desktop table: 7 column (id, title, priority, assignee, status, updated, actions)
- Mobile (< 640px): CSS hidden → user nothing sees
- Fallback: None
```

**PROBLEM:**
- ❌ Mobile users: en önemli bilgi (priority, assignee) görmüyor
- 📊 Context loss
- ⚠️ Action'lar: mobile'da impossible to perform

**TASARIM ÇÖZÜMÜ:**

```
Card-based Mobile View:
┌─────────────────────┐
│ [DEF-001]           │
│ Critical Security   │ ← Title bold
│                     │
│ 🔴 Critical         │ ← Priority badge
│ Assigned: John D    │
│ Updated: 2 days ago │
│                     │
│ [Edit] [More ▼]     │
└─────────────────────┘
```

**FRONTEND DEĞIŞIKLIK:**
```tsx
// DefectCard.tsx (new component)
function DefectCard({ defect }) {
  return (
    <Card className="p-4">
      <div className="flex justify-between items-start">
        <div>
          <h3 className="font-mono text-sm text-gray-500">{defect.id}</h3>
          <h2 className="font-bold text-lg">{defect.title}</h2>
        </div>
        <DropdownMenu>
          <Button variant="ghost" size="sm">⋮</Button>
          <DropdownMenuContent>
            <DropdownMenuItem onClick={() => editDefect(defect.id)}>
              Edit
            </DropdownMenuItem>
            {/* More actions */}
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      <div className="mt-4 space-y-2">
        <div className="flex justify-between">
          <PriorityBadge priority={defect.priority} />
          <span className="text-xs text-gray-500">
            {formatDate(defect.updatedAt)}
          </span>
        </div>
        <div className="text-sm text-gray-600">
          Assigned: {defect.assignee?.name || 'Unassigned'}
        </div>
      </div>
    </Card>
  )
}

// DefectsPage.tsx
<div className="md:hidden space-y-3">
  {defects.map(d => <DefectCard key={d.id} defect={d} />)}
</div>

<div className="hidden md:block">
  <DataTable columns={columns} data={defects} />
</div>
```

**ONAY GEREKLI Mİ:** ✅ **EVET — Design Decision**  
(Card layout final, field order)

**EFOR:** ⏱️ 8 saat (card component, responsive logic)  
**RİSK:** 🔴 Yüksek (mobile user journey significantly changes)

---

## 📋 EKRAN: Dashboard

**Dosya:** `apps/web/app/(dashboard)/p/[projectId]/management/dashboard/page.tsx` (1690 satır)

### 🔴 SORUN #1: Overloaded Dashboard — 40+ Components

**DURUM:**
```
Şu anda:
- Release checklist (widget)
- Flaky tests (widget)
- Review queue (widget)
- Defects summary (widget)
- Execution summary
- Trend chart
- QA metrics card
- ... + 33 more widgets
= 1690 satırda inline render
= Initial load: 8.5s (Lighthouse)
```

**PROBLEM:**
- 🧠 Cognitive load: user nerede başlayacak bilmiyor
- ⏱️ Page load: tüm widgetlar fetch + render
- 📦 Bundle: unused widget code sayfada

**TASARIM ÇÖZÜMÜ:**

```
Dashboard Tab Structure:

TAB 1: Overview (Default)
├─ Release Checklist (top)
├─ Execution Summary (top-right)
└─ Quick Actions (bottom)

TAB 2: Metrics
├─ Flaky Tests
├─ Test Coverage
├─ Pass Rate Trend
└─ DurationReport

TAB 3: QA Health
├─ Defect Summary
├─ Open Defects by Priority
├─ Defect Trend
└─ Assignee Workload

TAB 4: Team
├─ Tester Performance
├─ Task Distribution
└─ Burndown (if agile)

TAB 5: Settings
├─ Widget preferences
└─ Refresh interval
```

**FRONTEND DEĞIŞIKLIK:**
```tsx
// DashboardPage.tsx
const [activeTab, setActiveTab] = useState('overview')

const DashboardOverviewTab = lazy(() => import('./_components/tabs/OverviewTab'))
const DashboardMetricsTab = lazy(() => import('./_components/tabs/MetricsTab'))
const DashboardHealthTab = lazy(() => import('./_components/tabs/HealthTab'))
// ...

<Tabs value={activeTab} onValueChange={setActiveTab}>
  <TabsList>
    <TabsTrigger value="overview">Overview</TabsTrigger>
    <TabsTrigger value="metrics">Metrics</TabsTrigger>
    <TabsTrigger value="health">QA Health</TabsTrigger>
    <TabsTrigger value="team">Team</TabsTrigger>
  </TabsList>

  <TabsContent value={activeTab}>
    <Suspense fallback={<DashboardSkeleton />}>
      {activeTab === 'overview' && <DashboardOverviewTab />}
      {activeTab === 'metrics' && <DashboardMetricsTab />}
      {/* ... */}
    </Suspense>
  </TabsContent>
</Tabs>
```

**ONAY GEREKLI Mİ:** ✅ **EVET — MAJOR DESIGN CHANGE**  
(Tab order, widget grouping, default tab)

**EFOR:** ⏱️ 12 saat (4 tab component, refactor widget'lar)  
**RİSK:** 🔴 **YÜKSEKDeğişim** (breaking change — users expect old layout)

---

### 🟡 SORUN #2: SVG Charts Mobile'da Responsive Değil

**DURUM:**
```
Şu anda:
- Chart width: 100% (responsive)
- Font size: hardcoded 12px (unreadable on mobile)
- Legend: horizontal (wraps badly)
- Tooltip: fixed position (off-screen)
```

**PROBLEM:**
- 📱 iPad: chart text illegible
- 🎨 Legend: overlaps chart area

**TASARIM ÇÖZÜMÜ:**

```tsx
// Use Recharts (built-in responsive)
<ResponsiveContainer width="100%" height={300}>
  <LineChart data={data}>
    <CartesianGrid strokeDasharray="3 3" />
    <XAxis 
      dataKey="name" 
      fontSize={window.innerWidth < 640 ? 11 : 12}
      angle={window.innerWidth < 640 ? -45 : 0}
      height={window.innerWidth < 640 ? 80 : 30}
    />
    <Tooltip formatter={tooltipFormatter} />
    <Legend 
      wrapperStyle={{ paddingTop: '20px' }}
      layout={window.innerWidth < 640 ? 'vertical' : 'horizontal'}
    />
    <Line type="monotone" dataKey="value" />
  </LineChart>
</ResponsiveContainer>
```

**ONAY GEREKLI Mİ:** ❌ Hayır  
**EFOR:** ⏱️ 3 saat  
**RİSK:** 🟢 Düşük

---

### 🟡 SORUN #3: Quick Actions — 8 Buton, No Hierarchy

**DURUM:**
```
Şu anda:
┌────────────────────────────────────────┐
│ [Run Tests] [Create Case] [+ Step]     │
│ [View Report] [Export] [Settings] [?]  │
│ [Refres
h] [Schedule]                    │
└────────────────────────────────────────┘
```

**PROBLEM:**
- 🎯 CTA hierarchy: clear değil (tümü primary buton)
- 👥 User: hangiyi click edeceğini bilemedi
- 📱 Mobile: 8 button' açılmıyor

**TASARIM ÇÖZÜMÜ:**

```
Primary Actions (Desktop):
  [Run Tests] [Create Case]
  
Secondary (Desktop/Mobile dropdown):
  [More Actions ▼]
    ├─ Add Step
    ├─ View Report
    ├─ Export
    └─ Schedule

Tertiary:
  [Settings] [Help] [Refresh]  (far right, compact)
```

**FRONTEND DEĞIŞIKLIK:**
```tsx
<div className="flex gap-2 flex-wrap">
  <Button onClick={runTests}>Run Tests</Button>
  <Button variant="outline" onClick={createCase}>Create Case</Button>

  <DropdownMenu>
    <Button variant="outline">More ▼</Button>
    <DropdownMenuContent>
      <DropdownMenuItem onClick={addStep}>Add Step</DropdownMenuItem>
      <DropdownMenuItem onClick={viewReport}>View Report</DropdownMenuItem>
      <DropdownMenuItem onClick={exportData}>Export</DropdownMenuItem>
      <DropdownMenuItem onClick={schedule}>Schedule</DropdownMenuItem>
    </DropdownMenuContent>
  </DropdownMenu>

  <Button variant="ghost" size="sm" onClick={openSettings}>⚙️</Button>
  <Button variant="ghost" size="sm" onClick={openHelp}>?</Button>
</div>
```

**ONAY GEREKLI Mİ:** ✅ **EVET — CTA Hierarchy**  
(Primary vs secondary action order)

**EFOR:** ⏱️ 3 saat  
**RİSK:** 🟢 Düşük

---

## 📋 EKRAN: Members Page

**Dosya:** `apps/web/app/(dashboard)/p/[projectId]/management/members/page.tsx`

### 🟡 SORUN #1: Invite Modal — Role Selector Verbose

**DURUM:**
```
Şu anda:
- Role dropdown: 8 option (Tester, QA Lead, Manager, Admin, ...)
- Description: her role'ün altında paragraph
- Modal width: 500px (text wraps)
- Permissions: separate tab (user confused)
```

**PROBLEM:**
- 🧐 User: role farkları anlamıyor
- 📱 Mobile: modal 375px'te unreadable
- ❓ Permissions tab: separate — confusion

**TASARIM ÇÖZÜMÜ:**

```
Invite Modal v2:

┌──────────────────────┐
│ Invite Team Member   │
├──────────────────────┤
│                      │
│ Email: [______]      │
│                      │
│ Role:                │
│ ○ Tester             │ ← Simple icon + name
│   Run tests, view    │   (permissions inline)
│                      │
│ ○ QA Lead           │
│   Full test access   │
│                      │
│ ○ Manager           │
│   Project admin      │
│                      │
│ [Cancel] [Invite]    │
└──────────────────────┘
```

**FRONTEND DEĞIŞIKLIK:**
```tsx
const roles = [
  {
    id: 'tester',
    label: 'Tester',
    description: 'Run tests, view results',
    icon: '🧪',
  },
  {
    id: 'qa_lead',
    label: 'QA Lead',
    description: 'Full test access, manage team',
    icon: '👑',
  },
  {
    id: 'manager',
    label: 'Manager',
    description: 'Project admin, billing',
    icon: '⚙️',
  },
]

<RadioGroup value={selectedRole} onValueChange={setSelectedRole}>
  {roles.map(role => (
    <div key={role.id} className="flex items-start space-x-3 p-3 border rounded">
      <RadioGroupItem value={role.id} />
      <div>
        <p className="font-medium">{role.icon} {role.label}</p>
        <p className="text-sm text-gray-500">{role.description}</p>
      </div>
    </div>
  ))}
</RadioGroup>
```

**ONAY GEREKLI Mİ:** ❌ Hayır  
**EFOR:** ⏱️ 3 saat  
**RİSK:** 🟢 Düşük

---

### 🟡 SORUN #2: Role Dropdown Absolute Positioning Broken Mobile

**DURUM:**
```
Şu anda:
- Members table: role dropdown absolute position
- Mobile: dropdown off-screen
- No scrolling
```

**PROBLEM:**
- 📱 Mobile: dropdown invisible

**TASARIM ÇÖZÜMÜ:**
- Desktop: dropdown (popper.js)
- Mobile: modal dialog

**ONAY GEREKLI Mİ:** ❌ Hayır  
**EFOR:** ⏱️ 2 saat  
**RİSK:** 🟢 Düşük

---

## 📋 EKRAN: Admin Users Page

**Dosya:** `apps/web/app/(dashboard)/admin/users/page.tsx`

### 🟢 SORUN #1: Form Cramped, Inputs Unreadable Mobile

**DURUM:**
- Form width: 100% (mobile 375px)
- Input label + input: same line (wraps)
- Button: 100% width (finger target small)

**TASARIM ÇÖZÜMÜ:**
- Mobile: vertical stack, full-width input
- Desktop: label left, input right

**ONAY GEREKLI Mİ:** ❌ Hayır  
**EFOR:** ⏱️ 2 saat  
**RİSK:** 🟢 Düşük

---

### 🟢 SORUN #2: Table Contrast Poor, Card View Missing

**DURUM:**
- Table row: light gray (WCAG AA fail)
- Mobile: hidden columns, no fallback

**TASARIM ÇÖZÜMÜ:**
- Row: darker background
- Mobile: card view (same as defects)

**ONAY GEREKLI Mİ:** ❌ Hayır  
**EFOR:** ⏱️ 3 saat  
**RİSK:** 🟢 Düşük

---

## 📊 ÖZET: ONAY GEREKTIREN TASARIM KARARLARI

| # | Ekran | Sorun | Efor | Risk | Onay |
|---|-------|-------|------|------|------|
| 1 | Case Detail | Responsive metadata sidebar | 5h | 🟠 | ✅ |
| 2 | Case Detail | Step DnD + undo UX | 7h | 🟠 | ✅ |
| 3 | Defects | Mobile filter pattern | 6h | 🟠 | ✅ |
| 4 | Defects | Card view mobile | 8h | 🔴 | ✅ |
| 5 | Dashboard | Tab restructure | 12h | 🔴 | ✅ |
| 6 | Members | Invite modal redesign | 3h | 🟢 | ✅ |
| 7 | Members | Quick actions hierarchy | 3h | 🟢 | ✅ |

**Toplam Onay Gerektiren:** 7 karar  
**Toplam Efor:** 44 saat  
**Toplam Risk:** 2 Yüksek + 4 Orta + 1 Düşük

---

## ✅ HEMEN UYGULANABİLİR (Onay gerektirmez)

| # | Sorun | Efor |
|---|-------|------|
| 1 | Case Detail lazy tab loading | 6h |
| 2 | Case Detail form validation schema | 4h |
| 3 | Defects chart responsive | 3h |
| 4 | Admin form spacing | 2h |
| 5 | Admin table contrast | 3h |
| 6 | Members modal simple role | 3h |
| 7 | Members dropdown fix | 2h |

**Toplam:** 23 saat (3 gün)

---

## 🎯 SONRAKI ADIMLAR

1. **Bu tasarım kararlarını onaylat** (Product Manager, Design Lead)
2. **Hemen uygulanabilir** 7 sorunu planla (Sprint N)
3. **Onay gerektiren** 7 karar için mockup'lar oluştur
4. **User testing** (high-risk changes: #4, #5)
5. **Phased rollout** (feature flag)

---

**Hazırlayanlar:**  
- UI/UX Designer (6 uzman rol analiziyle)
- Frontend Architect (implementasyon feasibility)
- QA Lead (testability perspective)

