# Smart Step Builder — Tam Uygulama Planı

**Hazırlanma:** 2026-04-17
**Özellik:** AI destekli, parametreli, BDD uyumlu adım yazma sistemi
**Kapsam:** Backend (2 yeni model + migration + 9 endpoint + AI servis) + Frontend (6 yeni component) + 4 sayfa entegrasyonu
**Toplam Süre:** ~12 iş günü (4 sprint + 2 ek gün eksikler için)

---

## 🎯 VİZYON

Kullanıcı adım yazarken:
1. AI projenin geçmiş senaryolarından öğrenip **cümlecik önerir** (dropdown + sağ panel)
2. Herhangi bir kelimeye tıklayıp **"Parametre yap"** der → `[yasin]` chip'e dönüşür
3. Chip'e tıklayınca **veri kaynağı** seçer: 🎲 Random / 📊 Excel / 🗄 DB
4. Bu yapı projenin **her adım yazılan yerinde** çalışır

---

## 📐 MİMARİ ÖZET

```
SmartStepInput (merkezi component)
├── StepTextEditor       → yazma alanı + kelimeye tıklama
├── ParameterChip        → [değer] görünümü, tıklanınca kaynak menüsü
├── DataSourcePopover    → Random / Excel / DB seçici
├── SuggestionDropdown   → yazarken AI öneri dropdown
└── SuggestionPanel      → sağ taraf sabit öneri paneli

Backend
├── TspmStepPhrase       → AI cümlecik kütüphanesi (proje bazlı)
├── TspmExcelUpload      → yüklenen Excel dosyaları [EKSİK GİDERİLDİ]
├── TspmStepParameter    → adım parametreleri + kaynak referansları
└── step_suggestion_service.py → AI öneri + use_count yönetimi
```

---

## 🔴 SPRINT A — Backend Altyapı
**Süre:** 3 gün (6. eksik dahil edildi)

---

### A1 — Yeni Modeller

#### `TspmStepPhrase` — AI Cümlecik Kütüphanesi
```python
# backend/app/domains/tspm/models.py

class TspmStepPhrase(Base):
    __tablename__ = "tspm_step_phrases"

    id:         Mapped[str]      = mapped_column(UUID, primary_key=True, default=uuid4)
    project_id: Mapped[str]      = mapped_column(ForeignKey("tspm_projects.id", ondelete="CASCADE"))
    text:       Mapped[str]      = mapped_column(String(500))   # "kullanıcı [url] adresine gider"
    category:   Mapped[str]      = mapped_column(String(16))    # given | when | then | action
    use_count:  Mapped[int]      = mapped_column(default=0)     # AI öğrenme skoru
    source:     Mapped[str]      = mapped_column(String(32))    # ai_generated | user_defined | seed
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    updated_at: Mapped[datetime] = mapped_column(onupdate=func.now())

    project: Mapped["TspmProject"] = relationship(back_populates="step_phrases")
```

#### `TspmExcelUpload` — Excel Dosya Kaydı ✅ EKSİK GİDERİLDİ
```python
class TspmExcelUpload(Base):
    __tablename__ = "tspm_excel_uploads"

    id:          Mapped[str]      = mapped_column(UUID, primary_key=True, default=uuid4)
    project_id:  Mapped[str]      = mapped_column(ForeignKey("tspm_projects.id", ondelete="CASCADE"))
    filename:    Mapped[str]      = mapped_column(String(255))   # orijinal dosya adı
    stored_path: Mapped[str]      = mapped_column(String(500))   # disk/S3 yolu
    columns:     Mapped[dict]     = mapped_column(JSON)          # {"A": "isim", "B": "email", ...}
    row_count:   Mapped[int]                                      # kaç satır var
    file_size:   Mapped[int]                                      # byte cinsinden
    created_at:  Mapped[datetime] = mapped_column(default=func.now())

    project: Mapped["TspmProject"] = relationship(back_populates="excel_uploads")
```

#### `TspmStepParameter` — Adım Parametreleri
```python
class TspmStepParameter(Base):
    __tablename__ = "tspm_step_parameters"

    id:          Mapped[str] = mapped_column(UUID, primary_key=True, default=uuid4)
    step_id:     Mapped[str] = mapped_column(String(100))  # hangi adıma ait
    step_type:   Mapped[str] = mapped_column(String(32))   # manual_step | scenario_step
    word:        Mapped[str] = mapped_column(String(200))  # orijinal kelime "yasin"
    position:    Mapped[int]                                # cümle içindeki karakter pozisyonu
    source_type: Mapped[str] = mapped_column(String(16))   # random | excel | db | static
    # random → random_type alanı kullanılır
    # excel  → excel_upload_id + excel_column kullanılır
    # db     → test_data_set_id + test_data_field kullanılır
    random_type:       Mapped[Optional[str]]  # name | email | phone | number | uuid | date
    excel_upload_id:   Mapped[Optional[str]]  = mapped_column(ForeignKey("tspm_excel_uploads.id"))
    excel_column:      Mapped[Optional[str]]  # hangi sütun: "A" veya "isim"
    test_data_set_id:  Mapped[Optional[str]]  = mapped_column(ForeignKey("tspm_test_data_sets.id"))
    test_data_field:   Mapped[Optional[str]]  # hangi alan: "username"
```

---

### A2 — Migration ✅ EKSİK GİDERİLDİ (parametre storage format)

```python
# backend/alembic/versions/20260417_0001_add_smart_step_builder.py

def upgrade():
    # 1. Yeni tablolar
    op.create_table("tspm_step_phrases", ...)
    op.create_table("tspm_excel_uploads", ...)
    op.create_table("tspm_step_parameters", ...)

    # 2. Mevcut action alanı dönüşümü — plain text korunur
    # action: "arama kısmına yasin yazılır"  (orijinal)
    # action_template: "arama kısmına [yasin] yazılır"  (parametreli versiyon)
    # TspmStepParameter tablosu hangi kelimenin parametre olduğunu tutar

    op.add_column("manual_test_steps",
        sa.Column("action_template", sa.String(1000), nullable=True)
    )
    # Not: action_template NULL ise parametre yoktur, action alanı kullanılır
    # action_template doluysa parametreli versiyon kullanılır

    # Benzer şekilde scenario step tablosuna da ekle:
    op.add_column("tspm_scenario_steps",
        sa.Column("step_template", sa.String(1000), nullable=True)
    )
```

**Parametre Storage Mantığı:**
```
DB'de saklanan:
  action          = "arama kısmına yasin yazılır"   ← orijinal (geri dönüş için)
  action_template = "arama kısmına [yasin] yazılır" ← parametreli versiyon

TspmStepParameter:
  step_id    = manual_step_id
  word       = "yasin"
  position   = 15              ← "arama kısmına " → 15. karakter
  source_type = "db"
  test_data_set_id = "..."
  test_data_field  = "username"
```

---

### A3 — Endpoint'ler (9 adet)

```
# Cümlecik Kütüphanesi
GET  /api/v1/tspm/projects/{id}/step-phrases?q=kullanıcı&category=when
     → Arama + kategori filtrelemesi, use_count sıralaması

POST /api/v1/tspm/projects/{id}/step-phrases
     Body: { text, category }
     → Kullanıcı tanımlı cümlecik ekle

POST /api/v1/tspm/projects/{id}/step-phrases/{phrase_id}/use
     → use_count +1, seçim anında tetiklenir  ← EKSİK GİDERİLDİ (#6)

POST /api/v1/tspm/projects/{id}/step-phrases/ai-suggest
     Body: { partial_text: "kullanıcı gir..." }
     → AI: proje geçmişi + TspmStepPhrase'den öneri döner

# Excel Yönetimi  ← EKSİK GİDERİLDİ (#1)
GET  /api/v1/tspm/projects/{id}/excel-uploads
     → Önceden yüklenmiş Excel listesi (id, filename, columns, row_count)

POST /api/v1/tspm/projects/{id}/excel-uploads
     multipart/form-data: file
     → Excel yükle, sütunları parse et, TspmExcelUpload kaydı oluştur

GET  /api/v1/tspm/projects/{id}/excel-uploads/{file_id}/preview
     → İlk 5 satır önizleme

# Parametre Yönetimi
GET  /api/v1/tspm/step-parameters/{step_id}?step_type=manual_step
     → Adıma ait tüm parametreler

POST /api/v1/tspm/step-parameters
     Body: { step_id, step_type, word, position, source_type, ...kaynak_alanları }
     → Parametre kaydet

PUT  /api/v1/tspm/step-parameters/{id}
     → Parametre güncelle (kaynak değiştirme)

DELETE /api/v1/tspm/step-parameters/{id}
     → Parametre sil (kelime plain text'e döner)
```

---

### A4 — AI Öneri Servisi + use_count Mekanizması ✅ EKSİK GİDERİLDİ (#6)

```python
# backend/app/domains/tspm/step_suggestion_service.py

def suggest_phrases(project_id: str, partial_text: str, limit: int = 8) -> list[dict]:
    """
    Öneri sıralaması:
    1. TspmStepPhrase tablosunda partial_text içeren kayıtlar (use_count DESC)
    2. Projenin mevcut senaryo adımlarından fuzzy match
    3. Manuel test adımlarından fuzzy match
    4. Yukarıdakilerin yetersiz kaldığı durumda AI completion (Claude)
    """
    phrases = db.query(TspmStepPhrase).filter(
        TspmStepPhrase.project_id == project_id,
        TspmStepPhrase.text.ilike(f"%{partial_text}%")
    ).order_by(TspmStepPhrase.use_count.desc()).limit(limit).all()

    if len(phrases) < 3:
        # Mevcut senaryo + manuel adımlardan fuzzy
        existing = _collect_existing_steps(project_id)
        matches = _fuzzy_match(partial_text, existing)
        phrases += matches

    if len(phrases) < 3:
        # AI tamamlama
        ai_suggestions = _ai_complete(project_id, partial_text)
        # AI önerilerini otomatik kaydet (source="ai_generated", use_count=0)
        _save_ai_suggestions(project_id, ai_suggestions)
        phrases += ai_suggestions

    return phrases[:limit]


def increment_use_count(phrase_id: str) -> None:
    """
    Kullanıcı bir cümleciği seçtiğinde çağrılır.
    Frontend: SuggestionDropdown'da seçim → POST .../step-phrases/{id}/use
    """
    db.query(TspmStepPhrase).filter_by(id=phrase_id).update(
        {TspmStepPhrase.use_count: TspmStepPhrase.use_count + 1}
    )
    db.commit()
```

---

### A5 — Seed Data Servisi ✅ EKSİK GİDERİLDİ (#4)

```python
# backend/app/domains/tspm/step_seed_service.py

SEED_PHRASES = {
    "given": [
        "kullanıcı [url] adresinde",
        "kullanıcı giriş yapmış durumda",
        "uygulama açık",
        "kullanıcı [sayfa] sayfasında",
        "[veri] veritabanında mevcut",
    ],
    "when": [
        "[element]'e tıklar",
        "[alan]'a [değer] yazar",
        "[buton] butonuna basar",
        "formu doldurur ve gönderir",
        "[url] adresine gider",
        "[menü] menüsünü açar",
        "[değer] seçer",
        "sayfayı yeniler",
    ],
    "then": [
        "[mesaj] mesajı görünür",
        "sayfa [url]'ye yönlendirilir",
        "[element] görünür",
        "[element] görünmez",
        "[değer] gösterilir",
        "işlem başarıyla tamamlanır",
        "hata mesajı gösterilmez",
    ],
    "action": [
        "[url] adresine gidilir",
        "[alan] alanına [değer] yazılır",
        "[buton] butonuna tıklanır",
        "[element] görünür olduğu doğrulanır",
        "beklenir [süre] saniye",
        "sayfa yenilenir",
    ],
}

def seed_step_phrases(project_id: str) -> int:
    """
    Yeni proje oluşturulduğunda otomatik çağrılır.
    Zaten kayıt varsa atlar (idempotent).
    """
    existing = db.query(TspmStepPhrase).filter_by(project_id=project_id).count()
    if existing > 0:
        return 0

    count = 0
    for category, phrases in SEED_PHRASES.items():
        for text in phrases:
            db.add(TspmStepPhrase(
                project_id=project_id,
                text=text,
                category=category,
                use_count=0,
                source="seed"
            ))
            count += 1
    db.commit()
    return count

# Çağrı yeri: projects router → POST /projects → proje oluşturulunca seed_step_phrases(new_project.id)
```

---

### A6 — Execution Sırasında Parametre Çözümü ✅ EKSİK GİDERİLDİ (#5)

```python
# backend/app/domains/tspm/parameter_resolver.py

def resolve_step_parameters(step_id: str, step_type: str) -> dict[str, str]:
    """
    Koşu başlamadan önce çağrılır.
    Tüm [parametre] → gerçek değer map'i döner.

    Örnek çıktı:
    {
      "yasin": "Ahmet Yılmaz",    ← DB'den
      "email": "test@ornek.com",  ← Excel'den (1. satır)
      "url":   "https://test.com" ← static
    }
    """
    params = db.query(TspmStepParameter).filter_by(
        step_id=step_id, step_type=step_type
    ).all()

    resolved = {}
    for p in params:
        if p.source_type == "random":
            resolved[p.word] = _generate_random(p.random_type)
        elif p.source_type == "excel":
            resolved[p.word] = _fetch_from_excel(p.excel_upload_id, p.excel_column)
        elif p.source_type == "db":
            resolved[p.word] = _fetch_from_test_data(p.test_data_set_id, p.test_data_field)
        elif p.source_type == "static":
            resolved[p.word] = p.word

    return resolved


def apply_parameters(template: str, resolved: dict[str, str]) -> str:
    """
    "arama kısmına [yasin] yazılır" + {"yasin": "Ahmet"} 
    → "arama kısmına Ahmet yazılır"
    """
    result = template
    for word, value in resolved.items():
        result = result.replace(f"[{word}]", value)
    return result

# Entegrasyon noktası:
# backend/app/domains/tspm/test_runner_service.py → launch_run() içinde
# her adım için:
#   resolved = resolve_step_parameters(step.id, "manual_step")
#   actual_action = apply_parameters(step.action_template or step.action, resolved)
#   engine'e actual_action gönderilir
```

---

## 🟡 SPRINT B — Parametre Sistemi (Frontend)
**Süre:** 3 gün

### B1 — `ParameterChip` Component
**Dosya:** `apps/web/components/smart-step/ParameterChip.tsx`

```tsx
// Görünüm örnekleri:
// static  → [yasin]          ← gri, köşeli parantez
// random  → [yasin 🎲]       ← amber
// excel   → [yasin 📊]       ← green
// db      → [yasin 🗄]       ← blue

interface ParameterChipProps {
  word: string;
  sourceType?: "random" | "excel" | "db" | "static";
  sourceRef?: string;
  onSourceChange: (type: SourceType, ref: SourceRef) => void;
  onRemove: () => void;  // chip kaldırılınca plain text'e döner
}

const SOURCE_STYLES = {
  static:  "border-slate-600 bg-slate-800 text-slate-300",
  random:  "border-amber-500/40 bg-amber-500/10 text-amber-300",
  excel:   "border-emerald-500/40 bg-emerald-500/10 text-emerald-300",
  db:      "border-blue-500/40 bg-blue-500/10 text-blue-300",
};
```

### B2 — `DataSourcePopover` Component
**Dosya:** `apps/web/components/smart-step/DataSourcePopover.tsx`

```
┌─────────────────────────────────┐
│  Veri Kaynağı Seç               │
├─────────────────────────────────┤
│  🎲 Random Üret                 │
│     Tip: [İsim ▾]               │
│     → İsim / E-posta / Telefon  │
│       Sayı / UUID / Tarih       │
├─────────────────────────────────┤
│  📊 Excel'den Al                │
│     ┌──────────────────────┐    │
│     │ rapor-q1.xlsx        │    │
│     │ kullanicilar.xlsx ✓  │    │
│     └──────────────────────┘    │
│     Sütun: [isim ▾]             │
│     + Yeni Excel Yükle          │
├─────────────────────────────────┤
│  🗄 Test Verisi (DB)            │
│     Set: [Kullanıcılar ▾]       │
│     Alan: [username ▾]          │
│                    [Önizle]     │
├─────────────────────────────────┤
│           [İptal] [Kaydet]      │
└─────────────────────────────────┘
```

### B3 — `StepTextEditor` Component
**Dosya:** `apps/web/components/smart-step/StepTextEditor.tsx`

```
Kelimeye tıklama → context menu:
┌──────────────────────┐
│  📌 Parametre yap    │
│  ─────────────────  │
│  ✂️  Kes              │
│  📋 Kopyala          │
└──────────────────────┘

Render mantığı:
"arama kısmına [yasin] yazılır"
→ parse ile split:
  ["arama kısmına ", <ParameterChip word="yasin"/>, " yazılır"]

Tıklanabilir kelimeler:
  <span
    onClick={() => showContextMenu(word, position)}
    className="cursor-pointer hover:bg-slate-700/50 rounded px-0.5"
  >
    {word}
  </span>
```

---

## 🟢 SPRINT C — AI Öneri Sistemi (Frontend)
**Süre:** 3 gün

### C1 — `SuggestionDropdown` Component
**Dosya:** `apps/web/components/smart-step/SuggestionDropdown.tsx`

```
Kullanıcı "kullanıcı gi" yazınca (300ms debounce):
┌────────────────────────────────────────┐
│  🤖 AI Önerileri                       │
├────────────────────────────────────────┤
│  When  kullanıcı giriş sayfasına gider │  ← Tab/Enter seç
│  When  kullanıcı [email] ile giriş     │  ← [..] parametreli
│  When  kullanıcı geçersiz bilgi girer  │
│  Given kullanıcı giriş yapmış durumda  │
│  ─────────────────────────────────── │
│  + Yeni cümlecik olarak kaydet         │
└────────────────────────────────────────┘

Davranış:
- Tab / Enter → seç + use_count +1 (POST .../use)
- Esc → kapat
- ↑↓ ok tuşları → navigasyon
- Seçilen cümlecikteki [parametreler] otomatik ParameterChip'e dönüşür
```

### C2 — `SuggestionPanel` Component
**Dosya:** `apps/web/components/smart-step/SuggestionPanel.tsx`

```
Sağ sabit panel (input focus olunca açılır):
┌──────────────────────────┐
│  💡 Önerilen Adımlar     │
│  ──────────────────────  │
│  GIVEN                   │
│  · kullanıcı [url]'de    │
│  · giriş yapılmış        │
│                          │
│  WHEN                    │
│  · [alan]'a tıklar       │
│  · [metin] yazar         │
│  · butona basar          │
│                          │
│  THEN                    │
│  · [mesaj] görünür       │
│  · [url]'ye gider        │
│  ──────────────────────  │
│  ACTION                  │
│  · [url]'e gidilir       │
│  · [alan]'a [değer]      │
│    yazılır               │
│  ──────────────────────  │
│  [+ Cümlecik Ekle]       │
│  [📖 Tümünü Gör]         │
└──────────────────────────┘

Responsive davranış:
- Geniş ekran → sağda sabit panel
- Dar ekran (<768px) → panel yok, sadece dropdown
```

### C3 — `SmartStepInput` Ana Component
**Dosya:** `apps/web/components/smart-step/SmartStepInput.tsx`

```tsx
interface SmartStepInputProps {
  value: string;                           // action metni
  template?: string;                        // action_template (parametreli)
  parameters: StepParameter[];              // mevcut parametreler
  onChange: (text: string, template: string) => void;
  onParametersChange: (params: StepParameter[]) => void;
  projectId: string;
  showPanel?: boolean;                      // sağ panel açık/kapalı
  placeholder?: string;
  stepType: "manual_step" | "scenario_step"; // hangi tablo
  stepId?: string;                          // kayıtlı adım ID'si
}

// Klavye kısayolları:
// Ctrl+Space → öneri dropdown'ı manuel aç
// @ veya /   → öneri dropdown'ı tetikle
// Tab        → öneri seç
// Esc        → dropdown kapat
```

### C4 — Index Export
**Dosya:** `apps/web/components/smart-step/index.ts`
```ts
export { SmartStepInput } from "./SmartStepInput";
export { ParameterChip } from "./ParameterChip";
export { SuggestionPanel } from "./SuggestionPanel";
export type { StepParameter, SourceType } from "./types";
```

---

## 🔵 SPRINT D — Entegrasyon
**Süre:** 2 gün

### D1 — `/manual` sayfası
```tsx
// apps/web/app/(dashboard)/p/[projectId]/manual/page.tsx
// ManualTestStep ekleme/düzenleme formunda:

// ÖNCE:
<input value={stepForm.action} onChange={...} />

// SONRA:
<SmartStepInput
  value={stepForm.action}
  template={stepForm.action_template}
  parameters={stepForm.parameters}
  projectId={projectId}
  stepType="manual_step"
  stepId={editingStep?.id}
  showPanel={true}
  placeholder="Adım eylemini yazın..."
  onChange={(text, template) =>
    setStepForm(p => ({ ...p, action: text, action_template: template }))
  }
  onParametersChange={(params) =>
    setStepForm(p => ({ ...p, parameters: params }))
  }
/>
```

### D2 — `/scenarios` sayfası
Senaryo adımı yazma alanı → `SmartStepInput` (stepType="scenario_step")

### D3 — `/automation-gen` sayfası
Test case adım alanları → `SmartStepInput` (showPanel=true)

### D4 — `/nl-test-gen` ve `/qa-orchestrator`
Prompt yazma alanları → `SmartStepInput` (showPanel=false, sadece dropdown)

---

## 🟣 SPRINT E — Cümlecik Yönetim Sayfası ✅ EKSİK GİDERİLDİ (#3)
**Süre:** 2 gün

**Yeni sayfa:** `apps/web/app/(dashboard)/p/[projectId]/step-library/page.tsx`

```
┌─────────────────────────────────────────────────────┐
│  📚 Adım Kütüphanesi                  [+ Ekle]       │
├──────────┬──────────────────────────────────────────┤
│ GIVEN(12)│  Filtre: [Tümü ▾]  Arama: [...........]  │
│ WHEN (28)│  ─────────────────────────────────────── │
│ THEN (19)│  kullanıcı [url] adresinde        🤖 45↑ │
│ ACTION(8)│  kullanıcı giriş yapmış           🤖 32↑ │
│          │  [alan]'a [değer] yazar            👤 18↑ │
│          │  [element]'e tıklar                🤖 12↑ │
│          │  ...                                      │
│          │                          [Düzenle] [Sil] │
└──────────┴──────────────────────────────────────────┘

Göstergeler:
  🤖 = AI üretildi   👤 = Kullanıcı ekledi   🌱 = Seed
  45↑ = use_count (45 kez kullanıldı)
```

**Sidebar'a ekleme:**
`product.ts` → `PROJECT_NAV_DEFINITIONS`'a:
```ts
{ key: "step-library", path: "step-library", segment: "step-library",
  label: "Adım Kütüphanesi", group: "Tasarla", productIds: ["studio", "web"] }
```

---

## 📊 TAM DOSYA LİSTESİ

| Dosya | Sprint | Tür | Açıklama |
|-------|--------|-----|----------|
| `backend/.../models.py` | A | Güncelleme | 3 yeni model |
| `backend/alembic/.../add_smart_step_builder.py` | A | Yeni | Migration (3 tablo + 2 sütun) |
| `backend/.../step_suggestion_service.py` | A | Yeni | AI öneri + use_count |
| `backend/.../parameter_resolver.py` | A | Yeni | Execution parametresi çözümü |
| `backend/.../step_seed_service.py` | A | Yeni | Başlangıç seed cümleleri |
| `backend/.../router.py` | A | Güncelleme | 9 yeni endpoint |
| `backend/.../test_runner_service.py` | A | Güncelleme | Parametre resolve entegrasyonu |
| `components/smart-step/types.ts` | B | Yeni | TypeScript tip tanımları |
| `components/smart-step/ParameterChip.tsx` | B | Yeni | [değer] chip component |
| `components/smart-step/DataSourcePopover.tsx` | B | Yeni | Kaynak seçici popover |
| `components/smart-step/StepTextEditor.tsx` | B | Yeni | Tıklanabilir metin editörü |
| `components/smart-step/SuggestionDropdown.tsx` | C | Yeni | AI öneri dropdown |
| `components/smart-step/SuggestionPanel.tsx` | C | Yeni | Sağ sabit panel |
| `components/smart-step/SmartStepInput.tsx` | C | Yeni | Ana wrapper component |
| `components/smart-step/index.ts` | C | Yeni | Export dosyası |
| `manual/page.tsx` | D | Güncelleme | SmartStepInput entegrasyonu |
| `scenarios/page.tsx` | D | Güncelleme | SmartStepInput entegrasyonu |
| `automation-gen/page.tsx` | D | Güncelleme | SmartStepInput entegrasyonu |
| `nl-test-gen/page.tsx` | D | Güncelleme | SmartStepInput (panel=false) |
| `step-library/page.tsx` | E | Yeni | Cümlecik yönetim sayfası |
| `lib/product.ts` | E | Güncelleme | step-library nav girişi |

**Toplam:** 7 backend dosyası + 14 frontend dosyası = **21 dosya**

---

## ⏱️ ÖZET TABLO

| Sprint | Süre | Ana Çıktı |
|--------|------|-----------|
| A — Backend Altyapı | 3 gün | 3 model, migration, 9 endpoint, AI servis, resolver, seed |
| B — Parametre Sistemi | 3 gün | ParameterChip + DataSourcePopover + StepTextEditor |
| C — AI Öneri | 3 gün | SuggestionDropdown + Panel + SmartStepInput |
| D — Entegrasyon | 2 gün | 4 sayfaya bağlama |
| E — Kütüphane UI | 2 gün | Cümlecik yönetim sayfası |
| **Toplam** | **~13 gün** | **Tam özellik** |

---

## 🎯 BAŞARI KRİTERLERİ

1. ✅ Adım yazarken 3 karakterden sonra AI önerisi dropdown açılır
2. ✅ Sağ panelde kategori bazlı cümlecikler listelenir
3. ✅ Herhangi kelimeye sağ tık → "Parametre yap" → `[kelime]` chip
4. ✅ Chip'e tıklayınca Random/Excel/DB seçici açılır
5. ✅ Excel listeden seçme + yeni yükleme çalışır
6. ✅ DB (test-data tablosu) entegrasyonu çalışır
7. ✅ Kullanılan cümlecikler use_count'u artırır, üste çıkar
8. ✅ Yeni projede seed cümlecikler otomatik yüklenir
9. ✅ Test koşulurken `[parametre]` → gerçek değere dönüşür
10. ✅ Adım Kütüphanesi sayfasından cümlecik ekle/düzenle/sil
11. ✅ Manual, Scenarios, Automation-gen, NL-test-gen sayfalarında çalışır
12. ✅ Dar ekranda (mobile) sadece dropdown gösterilir, panel gizlenir

---

*Kayıt: `docs/smart-step-builder-plan.md`*
*Uygulamaya başlamak için: "Sprint A başlat" de.*
