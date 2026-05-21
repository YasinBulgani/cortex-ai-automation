# BGTS UI Recording Locator Strategy

> Kapsamlı locator stratejisi, element envanteri, page object planı, xpath fallback listesi ve recording-ready event modeli.

---

## 1. Locator Öncelik Stratejisi

### 1.1 Seçici Öncelik Hiyerarşisi (Stability Index)

| Öncelik | Seçici Tipi | Stabilite | Kullanım Alanı | Örnek |
|---------|-------------|-----------|----------------|-------|
| **P0** | `data-testid` | ★★★★★ | Tüm interaktif elementler | `[data-testid="login-submit-btn"]` |
| **P1** | `getByRole` + accessible name | ★★★★★ | Butonlar, linkler, form alanları | `getByRole("button", { name: "Giriş Yap" })` |
| **P2** | `getByLabel` | ★★★★☆ | Form input'ları | `getByLabel("E-posta")` |
| **P3** | `#id` | ★★★★☆ | Benzersiz id taşıyan elementler | `#email`, `#password` |
| **P4** | `aria-label` | ★★★★☆ | Icon butonları, SVG | `[aria-label="Kullanıcı menüsü"]` |
| **P5** | `getByPlaceholder` | ★★★☆☆ | Label olmayan inputlar | `getByPlaceholder("Ara")` |
| **P6** | `name` attribute | ★★★☆☆ | Form alanları | `[name="email"]` |
| **P7** | `getByText` | ★★☆☆☆ | Statik metinler (son çare) | `getByText("Projeler")` |
| **P8** | CSS class-based | ★★☆☆☆ | Sadece yapısal sorgularda | `.react-flow` |
| **P9** | XPath (fallback) | ★☆☆☆☆ | Diğerleri başarısız olduğunda | `//table//tr[contains(.,'Senaryo')]` |

### 1.2 Seçici Kuralları

- **KURAL 1**: Her interaktif UI elementi `data-testid` taşımalı.
- **KURAL 2**: E2E testlerde `getByRole` > `getByLabel` > `data-testid` sırası tercih edilir.
- **KURAL 3**: Engine BDD testlerinde `object_repository` üzerinden isim çözümlemesi kullanılır.
- **KURAL 4**: XPath yalnızca tablo/liste traversal veya dinamik içerik durumlarında kullanılır.
- **KURAL 5**: CSS class selector'lar Tailwind nedeniyle **kullanılmaz** (utility class'lar kırılgan).
- **KURAL 6**: Text selector'lar i18n değişikliğine duyarlıdır — yalnızca `data-testid` yoksa kullanılır.

### 1.3 Naming Convention (data-testid)

```
{screen}-{element-type}-{identifier}
```

| Bileşen | Format | Örnek |
|---------|--------|-------|
| Sayfa konteyner | `{screen}-page` | `login-page` |
| Form | `{screen}-form` | `login-form` |
| Input | `{screen}-input-{field}` | `login-input-email` |
| Button | `{screen}-btn-{action}` | `login-btn-submit` |
| Link | `{screen}-link-{target}` | `sidebar-link-scenarios` |
| Table | `{screen}-table` | `scenarios-table` |
| Table Row | `{screen}-row-{identifier}` | `scenarios-row-{id}` |
| Modal | `{screen}-modal-{name}` | `scenarios-modal-confirm` |
| Checkbox | `{screen}-check-{name}` | `scenarios-check-select` |
| Dropdown | `{screen}-select-{name}` | `executions-select-status` |

---

## 2. Ekran Bazlı Element Envanteri

### 2.1 Login Ekranı (`/login`)

| Element | Tip | Mevcut Locator | Önerilen data-testid | Stabilite |
|---------|-----|----------------|----------------------|-----------|
| Logo SVG | Image | `svg[aria-label='BGTEST']` | `login-logo` | ★★★★☆ |
| Platform başlık | Text | `getByText("Test Intelligence Platform")` | `login-subtitle` | ★★★☆☆ |
| Sayfa başlığı | Heading | `getByText("Giriş Yap")` | `login-heading` | ★★★☆☆ |
| E-posta input | Input | `getByLabel("E-posta")` / `#email` | `login-input-email` | ★★★★★ |
| Şifre input | Input | `getByLabel("Şifre")` / `#password` | `login-input-password` | ★★★★★ |
| Beni hatırla | Checkbox | `getByText("Beni hatırla")` | `login-check-remember` | ★★☆☆☆ |
| Şifremi unuttum | Button | `getByText("Şifremi unuttum")` | `login-btn-forgot` | ★★☆☆☆ |
| Giriş butonu | Button | `getByRole("button", { name: "Giriş Yap" })` | `login-btn-submit` | ★★★★★ |
| Hata mesajı | Alert | `getByText(/hatalı\|geçersiz/)` | `login-alert-error` | ★★☆☆☆ |
| Kayıt yönlendirme | Text | `getByText("Hesabınız yok mu?")` | `login-text-register` | ★★☆☆☆ |
| Footer | Text | `getByText(/BGTEST.*hakları/)` | `login-footer` | ★★☆☆☆ |

### 2.2 Projeler Ekranı (`/projects`)

| Element | Tip | Mevcut Locator | Önerilen data-testid | Stabilite |
|---------|-----|----------------|----------------------|-----------|
| Sayfa başlığı | Heading | `getByText("Projeler")` | `projects-heading` | ★★★☆☆ |
| Proje adı input | Input | `getByPlaceholder("Örn. Ödeme API")` | `projects-input-name` | ★★★☆☆ |
| Açıklama input | Input | `getByPlaceholder("Kısa açıklama")` | `projects-input-desc` | ★★★☆☆ |
| Oluştur butonu | Button | `getByRole("button", { name: "Oluştur" })` | `projects-btn-create` | ★★★★★ |
| Proje kartları | Link | `getByRole("link", { name: projectName })` | `projects-card-{id}` | ★★★★☆ |
| Boş durum mesajı | Text | `getByText("Henüz proje yok")` | `projects-empty` | ★★☆☆☆ |

### 2.3 Proje Dashboard (`/p/{projectId}`)

| Element | Tip | Mevcut Locator | Önerilen data-testid | Stabilite |
|---------|-----|----------------|----------------------|-----------|
| Sayfa başlığı | Heading | `getByText("Proje özeti")` | `dashboard-heading` | ★★★☆☆ |
| Stat kartları | Link | `getByText("Senaryolar")` etc. | `dashboard-stat-{metric}` | ★★★★☆ |
| Yeni senaryo link | Link | `getByText("Yeni senaryo")` | `dashboard-action-new-scenario` | ★★☆☆☆ |
| Dosya içe aktar link | Link | `getByText("Dosya içe aktar")` | `dashboard-action-import` | ★★☆☆☆ |
| Onay kuyruğu link | Link | `getByText("Onay kuyruğu")` | `dashboard-action-approvals` | ★★☆☆☆ |
| Execution başlat | Link | `getByText("Execution başlat")` | `dashboard-action-new-exec` | ★★☆☆☆ |

### 2.4 Sidebar / AppShell (Global)

| Element | Tip | Mevcut Locator | Önerilen data-testid | Stabilite |
|---------|-----|----------------|----------------------|-----------|
| Logo | Link | `Link href="/projects"` | `sidebar-logo` | ★★★★☆ |
| Projeler link | NavLink | `getByText("Projeler")` | `sidebar-link-projects` | ★★★☆☆ |
| Senaryolar link | NavLink | `getByText("Senaryolar")` | `sidebar-link-scenarios` | ★★★☆☆ |
| Gereksinimler link | NavLink | - | `sidebar-link-requirements` | ★★★☆☆ |
| Kapsam Matrisi link | NavLink | - | `sidebar-link-coverage` | ★★★☆☆ |
| Koşular link | NavLink | - | `sidebar-link-executions` | ★★★☆☆ |
| Analitik link | NavLink | - | `sidebar-link-analytics` | ★★★☆☆ |
| Zamanlayıcı link | NavLink | - | `sidebar-link-schedules` | ★★★☆☆ |
| Akışlar link | NavLink | - | `sidebar-link-flows` | ★★★☆☆ |
| Regresyon link | NavLink | - | `sidebar-link-regression` | ★★★☆☆ |
| Onaylar link | NavLink | - | `sidebar-link-approvals` | ★★★☆☆ |
| İçe aktar link | NavLink | - | `sidebar-link-import` | ★★★☆☆ |
| API Testleri link | NavLink | - | `sidebar-link-api-tests` | ★★★☆☆ |
| Test Verileri link | NavLink | - | `sidebar-link-test-data` | ★★★☆☆ |
| Entegrasyonlar link | NavLink | - | `sidebar-link-integrations` | ★★★☆☆ |
| Proje seçici | Component | - | `header-project-switcher` | ★★★★☆ |
| Bildirim zili | Button | - | `header-btn-notifications` | ★★★★☆ |
| Tema değiştirici | Button | - | `header-btn-theme` | ★★★★☆ |
| Kullanıcı menü butonu | Button | `[aria-label="Kullanıcı menüsü"]` | `header-btn-user-menu` | ★★★★☆ |
| Profil menü item | Link | `getByText("Profil")` | `user-menu-link-profile` | ★★★☆☆ |
| Bilgiler menü item | Link | `getByText("Bilgiler")` | `user-menu-link-info` | ★★★☆☆ |
| Çıkış menü item | Link | `getByText("Çıkış Yap")` | `user-menu-link-logout` | ★★★☆☆ |

### 2.5 Senaryolar Listesi (`/p/{projectId}/scenarios`)

| Element | Tip | Mevcut Locator | Önerilen data-testid | Stabilite |
|---------|-----|----------------|----------------------|-----------|
| Sayfa başlığı | Heading | `getByText("Senaryolar")` | `scenarios-heading` | ★★★☆☆ |
| Arama input | Input | `getByPlaceholder("Başlıkta ara…")` | `scenarios-input-search` | ★★★☆☆ |
| AI ile Üret butonu | Button | `getByText("AI ile Üret")` | `scenarios-btn-ai-generate` | ★★★☆☆ |
| Yeni senaryo butonu | Button | `getByText("Yeni senaryo")` | `scenarios-btn-new` | ★★★★☆ |
| Toplu sil butonu | Button | `getByText(/Seçilenleri sil/)` | `scenarios-btn-bulk-delete` | ★★★☆☆ |
| Senaryo tablosu | Table | `table` | `scenarios-table` | ★★★★☆ |
| Satır checkbox | Checkbox | `getByRole("checkbox")` | `scenarios-check-{id}` | ★★★★☆ |
| Senaryo linki | Link | `getByText(title)` | `scenarios-link-{id}` | ★★★★☆ |
| Boş durum | Text | `getByText("Kayıt yok")` | `scenarios-empty` | ★★☆☆☆ |

### 2.6 Senaryo Oluştur/Düzenle (`/p/{projectId}/scenarios/new`, `/scenarios/{id}`)

| Element | Tip | Mevcut Locator | Önerilen data-testid | Stabilite |
|---------|-----|----------------|----------------------|-----------|
| Başlık input | Input | `getByLabel("Başlık")` | `scenario-form-input-title` | ★★★★★ |
| Kaydet butonu | Button | `getByRole("button", { name: "Kaydet" })` | `scenario-form-btn-save` | ★★★★★ |

### 2.7 Koşular (`/p/{projectId}/executions`)

| Element | Tip | Mevcut Locator | Önerilen data-testid | Stabilite |
|---------|-----|----------------|----------------------|-----------|
| Koşum Adı input | Input | `getByLabel("Koşum Adı")` | `execution-input-name` | ★★★★☆ |
| Senaryo checkboxları | Checkbox | `getByRole("checkbox", { name: /.../ })` | `execution-check-scenario-{id}` | ★★★★☆ |
| Başlat butonu | Button | `getByRole("button", { name: "Başlat" })` | `execution-btn-start` | ★★★★★ |

### 2.8 Akışlar (`/p/{projectId}/flows`)

| Element | Tip | Mevcut Locator | Önerilen data-testid | Stabilite |
|---------|-----|----------------|----------------------|-----------|
| Yeni akış butonu | Button | `getByRole("button", { name: /yeni akış/ })` | `flows-btn-new` | ★★★★☆ |
| Ad input | Input | `getByLabel("Ad")` | `flows-input-name` | ★★★★☆ |
| Kaydet butonu | Button | `getByRole("button", { name: "Kaydet" })` | `flows-btn-save` | ★★★★★ |
| Flow editör canvas | Canvas | `[data-testid='flow-editor'], .react-flow` | `flow-editor` | ★★★★★ |

### 2.9 Regresyon (`/p/{projectId}/regression`)

| Element | Tip | Mevcut Locator | Önerilen data-testid | Stabilite |
|---------|-----|----------------|----------------------|-----------|
| Yeni set butonu | Button | `getByRole("button", { name: /yeni/ })` | `regression-btn-new` | ★★★★☆ |
| Ad input | Input | `getByLabel("Ad")` | `regression-input-name` | ★★★★☆ |
| Senaryo checkboxları | Checkbox | `getByRole("checkbox")` | `regression-check-scenario-{id}` | ★★★☆☆ |
| Kaydet butonu | Button | `getByRole("button", { name: "Kaydet" })` | `regression-btn-save` | ★★★★★ |
| AI Önerisi butonu | Button | `getByRole("button", { name: /öner/ })` | `regression-btn-suggest` | ★★★☆☆ |

### 2.10 Onaylar (`/p/{projectId}/approvals`)

| Element | Tip | Mevcut Locator | Önerilen data-testid | Stabilite |
|---------|-----|----------------|----------------------|-----------|
| Sayfa başlığı | Heading | `getByText("Onaylar")` | `approvals-heading` | ★★★☆☆ |
| Onayla butonu | Button | `getByRole("button", { name: "Onayla" })` | `approvals-btn-approve` | ★★★★☆ |
| Reddet butonu | Button | `getByRole("button", { name: "Reddet" })` | `approvals-btn-reject` | ★★★★☆ |
| Durum badge | Badge | `getByText(/onaylandı/)` | `approvals-status-{id}` | ★★☆☆☆ |

### 2.11 İçe Aktarma (`/p/{projectId}/import`)

| Element | Tip | Mevcut Locator | Önerilen data-testid | Stabilite |
|---------|-----|----------------|----------------------|-----------|
| Dosya input | Input | `input[type="file"]` | `import-input-file` | ★★★★☆ |
| Yükle butonu | Button | `getByRole("button", { name: /yükle/ })` | `import-btn-upload` | ★★★★☆ |
| Başarı mesajı | Alert | `getByText(/başarı/)` | `import-alert-success` | ★★☆☆☆ |

---

## 3. Page Object Model Planı

### 3.1 Mimari

```
e2e/
├── pages/                       # Playwright TS Page Objects
│   ├── base.page.ts             # Temel page object (tüm sayfalar miras alır)
│   ├── login.page.ts
│   ├── projects.page.ts
│   ├── project-dashboard.page.ts
│   ├── scenarios-list.page.ts
│   ├── scenario-form.page.ts
│   ├── executions.page.ts
│   ├── execution-detail.page.ts
│   ├── flows.page.ts
│   ├── flow-editor.page.ts
│   ├── regression.page.ts
│   ├── approvals.page.ts
│   ├── import.page.ts
│   └── components/              # Paylaşılan bileşenler
│       ├── sidebar.component.ts
│       ├── header.component.ts
│       ├── user-menu.component.ts
│       ├── confirm-dialog.component.ts
│       └── data-table.component.ts
├── helpers/
│   └── auth.ts                  # Mevcut (değişmez)
├── fixtures/
│   └── pages.fixture.ts         # Playwright fixture — page injection
└── *.spec.ts                    # Test dosyaları
```

### 3.2 Base Page

```typescript
// e2e/pages/base.page.ts
import { type Page, type Locator } from "@playwright/test";

export abstract class BasePage {
  constructor(protected readonly page: Page) {}

  abstract readonly url: string | RegExp;

  async goto() {
    if (typeof this.url === "string") {
      await this.page.goto(this.url);
    }
  }

  async waitForReady() {
    await this.page.waitForLoadState("domcontentloaded");
  }

  protected testId(id: string): Locator {
    return this.page.getByTestId(id);
  }

  protected role(role: string, options?: { name?: string | RegExp }): Locator {
    return this.page.getByRole(role as any, options);
  }

  protected label(text: string): Locator {
    return this.page.getByLabel(text);
  }
}
```

### 3.3 Sayfa Sınıfları Özeti

| Sınıf | Ekran | Locator Sayısı | Aksiyon Metotları |
|-------|-------|----------------|-------------------|
| `LoginPage` | `/login` | 11 | `fillEmail`, `fillPassword`, `submit`, `assertError`, `assertRedirectToProjects` |
| `ProjectsPage` | `/projects` | 6 | `createProject`, `clickProject`, `assertProjectVisible` |
| `ProjectDashboardPage` | `/p/{id}` | 8 | `getStatValue`, `clickQuickAction` |
| `ScenariosListPage` | `/p/{id}/scenarios` | 9 | `search`, `selectScenario`, `bulkDelete`, `gotoNew` |
| `ScenarioFormPage` | `/p/{id}/scenarios/new` | 3 | `fillTitle`, `save` |
| `ExecutionsPage` | `/p/{id}/executions` | 4 | `fillName`, `selectScenarios`, `start` |
| `FlowsPage` | `/p/{id}/flows` | 4 | `createFlow`, `clickFlow` |
| `FlowEditorPage` | `/p/{id}/flows/{fid}` | 2 | `assertCanvasVisible` |
| `RegressionPage` | `/p/{id}/regression` | 5 | `createSet`, `aiSuggest` |
| `ApprovalsPage` | `/p/{id}/approvals` | 4 | `approve`, `reject`, `assertStatus` |
| `ImportPage` | `/p/{id}/import` | 3 | `uploadFile`, `assertSuccess` |
| `SidebarComponent` | Global | 16 | `navigateTo(section)` |
| `HeaderComponent` | Global | 4 | `openUserMenu`, `switchProject`, `toggleTheme` |

---

## 4. XPath Fallback Listesi

XPath yalnızca **semantic locator bulunamadığında** ve **DOM yapısı traversal gerektirdiğinde** kullanılır.

### 4.1 Tablo İçi Element Erişimi

```xpath
# Senaryolar tablosunda belirli bir satırın checkbox'ı
//table[@data-testid='scenarios-table']//tr[contains(., '{title}')]//input[@type='checkbox']

# Senaryolar tablosunda belirli satırdaki durum sütunu
//table[@data-testid='scenarios-table']//tr[contains(., '{title}')]/td[3]

# Koşum detayında belirli senaryo sonucu
//div[@data-testid='execution-detail']//tr[contains(., '{scenarioTitle}')]//td[contains(@class, 'status')]
```

### 4.2 Dinamik Liste / Kart Erişimi

```xpath
# Proje kartında açıklama metni
//a[contains(., '{projectName}')]//p[contains(@class, 'muted')]

# Dashboard stat kartında değer
//a[contains(., '{label}')]//p[contains(@class, 'tabular-nums')]

# Onay listesinde belirli onay öğesi
//div[contains(., '{approvalTitle}')]/ancestor::div[contains(@class, 'border')]//button[contains(., 'Onayla')]
```

### 4.3 Sidebar Navigasyon (data-testid yoksa fallback)

```xpath
# Sidebar'da belirli bir navigasyon linki
//aside//nav//a[contains(., '{linkText}')]

# Aktif navigasyon linki
//aside//nav//a[contains(@class, 'bg-')]
```

### 4.4 Modal / Dialog

```xpath
# Onay dialogu içindeki buton
//div[@role='dialog']//button[contains(., 'Onayla')]

# Modal başlığı
//div[@role='dialog']//h2
```

### 4.5 Fallback Kuralları

| Durum | XPath Kullanımı | Tercih Edilen Alternatif |
|-------|-----------------|--------------------------|
| Tablo satır traversal | ✅ Kabul | `data-testid` row + cell |
| Nth-child erişim | ⚠️ Son çare | `data-testid` ile index |
| Text-based arama | ⚠️ Dikkatli | `getByText` veya `getByRole` |
| Parent-child ilişki | ✅ Kabul | Composite `data-testid` |
| CSS class filtresi | ❌ Yasaklı | Tailwind class'lar kırılgan |
| Position-based (`[1]`) | ⚠️ Dikkatli | `.first()` veya `nth()` |

---

## 5. Recording-Ready Event Model

### 5.1 Event-Action Şeması

Mevcut `RecordedAction` yapısını genişleten, recording-playback uyumlu event modeli:

```typescript
interface RecordingEvent {
  // Kimlik
  id: string;                          // UUID
  sessionId: string;                   // Kayıt oturumu ID

  // Zamanlama
  timestamp: number;                   // ms (oturum başlangıcından)
  wallClock: string;                   // ISO 8601

  // Olay Tipi
  eventType: EventType;

  // Hedef Element
  target: {
    selector: string;                  // Çözümlenen seçici
    selectorType: SelectorType;
    selectorChain: SelectorCandidate[]; // Tüm alternatif seçiciler
    tagName: string;
    elementName: string;               // Snake_case insan okunabilir
    boundingBox?: BoundingBox;         // x, y, width, height
    screenshot?: string;               // Base64 element screenshot
  };

  // Aksiyon Detayları
  action: {
    type: ActionType;
    value?: string;                    // Text input, URL, etc.
    key?: string;                      // Keyboard tuşu
    metadata?: Record<string, any>;
  };

  // Sayfa Bağlamı
  context: {
    url: string;
    title: string;
    viewport: { width: number; height: number };
    pageLoadState: "loading" | "domcontentloaded" | "networkidle";
  };

  // Assertion (opsiyonel)
  assertion?: {
    type: AssertionType;
    expected: string;
    actual?: string;
    passed?: boolean;
  };
}

type EventType =
  | "user_action"     // Kullanıcı etkileşimi
  | "navigation"      // Sayfa geçişi
  | "assertion"       // Doğrulama
  | "wait"            // Bekleme
  | "system";         // Otomatik (screenshot, vs.)

type ActionType =
  | "click" | "dblclick" | "rightclick"
  | "type" | "clear" | "fill"
  | "select" | "check" | "uncheck"
  | "hover" | "focus" | "blur"
  | "scroll" | "drag_drop"
  | "navigate" | "reload" | "go_back" | "go_forward"
  | "press_key" | "upload"
  | "screenshot" | "wait_for"
  | "assert_text" | "assert_visible" | "assert_url" | "assert_value";

type SelectorType = "testid" | "role" | "label" | "css" | "xpath" | "text";

type AssertionType = "text" | "visible" | "hidden" | "url" | "value" | "count" | "attribute";

interface SelectorCandidate {
  type: SelectorType;
  value: string;
  confidence: number;   // 0.0 — 1.0
  stable: boolean;
}

interface BoundingBox {
  x: number;
  y: number;
  width: number;
  height: number;
}
```

### 5.2 Selector Chain (Çoklu Seçici Zinciri)

Her kayıt anında element için **tüm olası seçiciler** hesaplanır ve güven skoruyla sıralanır:

```json
{
  "selectorChain": [
    { "type": "testid", "value": "[data-testid='login-btn-submit']", "confidence": 1.0, "stable": true },
    { "type": "role",   "value": "button[name='Giriş Yap']",       "confidence": 0.95, "stable": true },
    { "type": "css",    "value": "button.w-full[type='submit']",    "confidence": 0.6,  "stable": false },
    { "type": "xpath",  "value": "//form//button[@type='submit']",  "confidence": 0.5,  "stable": false }
  ]
}
```

Playback sırasında zincir baştan sona denenir — ilk eşleşen kullanılır. Bu **self-healing** sağlar.

### 5.3 Event Flow Diyagramı

```
[Browser Event] → [Event Interceptor] → [SmartSelectorEngine]
                                              ↓
                                    [Selector Chain Builder]
                                              ↓
                                    [RecordingEvent Object]
                                              ↓
                          ┌───────────────────┼───────────────────┐
                          ↓                   ↓                   ↓
                   [JSON Storage]     [WebSocket Push]     [Object Repository]
                                              ↓
                                     [Live Preview UI]
```

### 5.4 Recording Session Yaşam Döngüsü

```
POST /api/recorder/start
  → { sessionId, name, domain, base_url }

POST /api/recorder/{sessionId}/action  (her event için)
  → { event: RecordingEvent }

GET  /api/recorder/{sessionId}/actions (canlı izleme)
  → { events: RecordingEvent[] }

POST /api/recorder/{sessionId}/stop
  → { sessionPath, actionCount }

POST /api/recorder/generate
  → { format: "playwright" | "cucumber" | "pom_python" | "pom_java" | "locators" | "all" }
```

### 5.5 Playback Stratejisi

```
1. Event JSON yükle
2. Her event için:
   a. selectorChain üzerinden element bul (cascade)
   b. Bulunamazsa → self-healing: AI ile yeni selector öner
   c. action.type'a göre aksiyon çalıştır
   d. assertion varsa doğrula
   e. Sonucu kaydet (pass/fail/healed)
3. Rapor üret (Allure / HTML)
```

### 5.6 Self-Healing Locator Akışı

```
[Primary Selector] ─── found? ──→ ✅ Aksiyon çalıştır
        │ not found
        ↓
[Selector Chain] ─── iterate ──→ next candidate found? ──→ ✅ Aksiyon çalıştır + log heal
        │ all failed
        ↓
[AI Selector Recovery] ──→ DOM snapshot + element context → LLM → yeni selector öner
        │ found?
        ↓
   ✅ Aksiyon çalıştır + selector güncelle
   ❌ Test fail + screenshot + DOM dump
```

---

## 6. Uygulama Yol Haritası

### Faz 1 — Temel (1-2 hafta)
- [ ] Tüm UI bileşenlerine `data-testid` attribute'ları ekle
- [ ] `e2e/pages/` dizininde TypeScript Page Object'leri oluştur
- [ ] Mevcut e2e testlerini Page Object kullanacak şekilde refactor et
- [ ] `BasePage` + Sidebar/Header component sınıflarını implement et

### Faz 2 — Locator Repository (1 hafta)
- [ ] Engine `object_repository` tablosuna `selector_chain` JSON sütunu ekle
- [ ] `SmartSelectorEngine` selector chain desteği ekle
- [ ] Locator Registry API'yi güncelle (chain CRUD)

### Faz 3 — Recording Enhancement (2 hafta)
- [ ] `RecordingEvent` şemasını implement et
- [ ] Selector chain builder'ı recording akışına entegre et
- [ ] Self-healing playback mekanizmasını kur
- [ ] Canlı recording preview WebSocket desteği

### Faz 4 — AI & Raporlama (devam eden)
- [ ] AI-powered selector recovery
- [ ] Locator health dashboard
- [ ] Kırılgan locator otomatik tespiti
