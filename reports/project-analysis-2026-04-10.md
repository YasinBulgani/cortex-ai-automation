# BGTS Monorepo Komple Analiz Raporu

Tarih: 2026-04-10
Kapsam: `/Users/yasin_bulgan/Desktop/BGTS_Test_Donusum`
Yöntem: Dizin envanteri, boyut analizi, manifest/compose/startup incelemesi, referans taraması, sınırlı çalıştırma doğrulamaları

## 1. Yönetici Özeti

Bu depo tek bir uygulama değil; aynı kökte birlikte yaşayan birden fazla ürün, test motoru, sentetik veri denemesi, framework, örnek proje, rapor çıktısı ve yerel çalışma alanı kopyasından oluşan büyük bir monorepo/mega-workspace.

Bugün itibarıyla ana ürün hattı fiilen şu çekirdek etrafında dönüyor:

- `apps/web` → Next.js dashboard
- `backend` → FastAPI ana API
- `engine` → Flask test otomasyon motoru
- `e2e` + `playwright.config.ts` → ana Playwright E2E suite
- `ai-gateway` → AI gateway mikroservisi
- `docker-compose.yml` + `start-all.sh` + `Makefile` → ana çalışma akışı

Buna karşılık depoda ciddi miktarda tekrar, arşiv, generated output ve tool-local kopya var:

- `.claude/worktrees/` tek başına yaklaşık `13G`
- `ai-test-automation/` yaklaşık `784M`, çoğu `jarvis/venv`
- `backend/banking-data/` ile `synthetic-data/banking/` pratikte aynı içerik
- `backend/synthetic-data-v4/` ile `synthetic-data/platform-v4/` neredeyse aynı kaynak
- `frameworks/Test_Template/` kaynak kod yerine büyük ölçüde rapor/artifact içeriyor
- `test-automation-workspace/` fiilen boş
- `ai-test-pipeline/` fiilen sadece `__pycache__`

Sonuç: Repo teknik olarak zengin ama operasyonel olarak dağınık. Kaynak koddan çok kopya veri, cache, build çıktısı ve eski deneme/merge kalıntısı taşıyor.

## 2. Kök Envanter

Kökte görülen ana alanlar:

- Ürün: `apps/`, `backend/`, `engine/`, `ai-gateway/`
- Test: `e2e/`, `api-tests/`, `frameworks/`, `tests/`
- Veri/sentetik veri: `synthetic-data/`, `backend/banking-data/`
- Legacy/deneysel: `ai-engine/`, `ai-test-automation/`, `ai-test-pipeline/`, `NexusQATestOtomasyon/`
- Çıktılar/doküman: `reports/`, `docs/`, `collections/`, sunum ve plan dosyaları
- Generated örnekler: `scaffolded_projects/`
- Tool-local meta alanlar: `.claude/`, `.cursor/`, `.vscode/`

## 3. Boyut Dağılımı

Öne çıkan dizin boyutları:

| Dizin | Boyut | Yorum |
|---|---:|---|
| `backend/` | `808M` | Büyük kısmı legacy synthetic-data ve banking frontend çıktıları |
| `ai-test-automation/` | `784M` | Neredeyse tamamen `jarvis/venv` |
| `synthetic-data/` | `542M` | mostlyAI exportları + banking frontend |
| `apps/web/` | `532M` | Büyük kısmı `.next` ve `node_modules` |
| `engine/` | `308M` | Büyük kısmı `.venv` |
| `NexusQATestOtomasyon/` | `86M` | Java test suite + rapor/artifact |
| `frameworks/` | `62M` | Özellikle `Test_Template/` şişkin |
| `scaffolded_projects/` | `19M` | Üretilmiş örnek projeler |

Gizli ama çok büyük alan:

| Dizin | Boyut | Yorum |
|---|---:|---|
| `.claude/` | `13G` | Tamamı tool-local worktree kopyaları |
| `.claude/worktrees/` | `13G` | 16 ayrı çalışma kopyası |

## 4. Ana Çalışan Ürün Hattı

### 4.1 Ana runtime akışı

`docker-compose.yml`, `start-all.sh`, `Makefile` ve kök `package.json` üzerinden doğrulanan ana runtime bileşenleri:

- `postgres`
- `redis`
- `backend`
- `worker`
- `engine`
- `web`
- `ai-gateway`

Bu, depodaki kanonik ürün yolunun şu olduğunu gösteriyor:

1. `apps/web` kullanıcı arayüzü
2. `backend` iş kuralları ve REST API
3. `engine` otomasyon motoru
4. `ai-gateway` model sağlayıcıları için gateway
5. `e2e/` bu bütünleşik yapıyı test ediyor

### 4.2 Aktif çekirdek modüller

| Modül | Durum | Gerekçe |
|---|---|---|
| `apps/web/` | Aktif ve gerekli | Compose içinde `web`, root npm scriptlerinde kullanılıyor |
| `backend/` | Aktif ve gerekli | Compose içinde `backend`, ana API |
| `engine/` | Aktif ve gerekli | Compose içinde `engine`, backend ile entegre |
| `ai-gateway/` | Aktif ve gerekli | Compose ve Makefile içinde doğrudan bağlı |
| `e2e/` | Aktif ve gerekli | Root Playwright config doğrudan bunu çalıştırıyor |
| `collections/` | Destekleyici | HTTP/Postman koleksiyonları mevcut |
| `reports/templates/` | Destekleyici | Şablon bazlı raporlama için gerekli |

## 5. Çekirdek Modül Detayı

### 5.1 Frontend: `apps/web`

Durum:

- Ana frontend
- `Next.js 14.2.21`
- Yaklaşık `62` route/layout/page seviyesi dosya
- Boyutın büyük kısmı:
  - `.next` → `251M`
  - `node_modules` → `279M`

Değerlendirme:

- Kaynak kod olarak gerekli
- Boyut şişkinliğinin büyük kısmı generated/build cache
- Repo içinde `.next` tutulması gereksiz

### 5.2 Backend: `backend`

Durum:

- Ana FastAPI servis
- `144` domain dosyası
- `44` test dosyası
- Domainler:
  - `agents`
  - `ai`
  - `artifacts`
  - `audit`
  - `auth`
  - `automation`
  - `catalog`
  - `cicd`
  - `jobs`
  - `n8n`
  - `notifications`
  - `rules`
  - `scaffold`
  - `tspm`

Değerlendirme:

- Gerçek ürün çekirdeği
- Ancak boyutın çoğu `app/` değil:
  - `banking-data/` → `335M`
  - `synthetic-data-v2/` → `215M`
  - `synthetic-data-v3/` → `119M`
  - `.venv` → `128M`
  - `synthetic-data-v4/` → `9.1M`

### 5.3 Engine: `engine`

Durum:

- Flask tabanlı otomasyon motoru
- `69` route dosyası
- `85` test dosyası
- Boyutın büyük kısmı:
  - `.venv` → `277M`
  - `datasets/sqlite` → `26M`

Değerlendirme:

- Ürün için gerekli
- Route kapsamı çok geniş; feature creep mevcut
- `engine/scripts/scaffold_project.py` ile ayrıca proje üretme sorumluluğu da taşıyor

### 5.4 E2E: `e2e`

Durum:

- Ana Playwright suite
- `19` adet `*.spec.ts`
- Root `playwright.config.ts` doğrudan bu dizini kullanıyor
- `backend`, `apps/web`, `engine` servislerini local webServer ile ayağa kaldırma mantığı var

Değerlendirme:

- Aktif ve gerekli
- Monorepo içindeki kanonik UI test katmanı bu

### 5.5 AI Gateway: `ai-gateway`

Durum:

- Ayrı FastAPI mikroservisi
- Compose ve Makefile içinde aktif
- Testleri mevcut (`tests/test_gateway.py`)

Değerlendirme:

- Ürün hattına bağlı
- Ayrı servis olarak tutulması makul

## 6. Test Stack Haritası

Depoda tek bir test stack yok; paralel yaşayan en az 5 ayrı test yaklaşımı var:

| Stack | Konum | Durum | Not |
|---|---|---|---|
| Ana ürün E2E | `e2e/` | Aktif | Root Playwright suite |
| Backend API testleri | `backend/tests/` | Aktif | FastAPI API/security/contract |
| Engine unit/integration/BDD | `engine/tests/` | Aktif ama sorunlu | Collection/import sorunları var |
| Ayrı Python API suite | `api-tests/` | Kısmen aktif | Kendi client/config yapısı var |
| TS Cucumber framework | `frameworks/playwright-cucumber-ts/` | Aktif destekleyici | Framework/scaffold rolünde |
| Java Selenium suite | `NexusQATestOtomasyon/`, `frameworks/selenium-cucumber-java/` | Legacy/ikili | İki ayrı Java suite aynı alanda yarışıyor |

Bu yapı güçlü ama dağınık. Hangi test stack'in “kanonik” olduğunun yazılı olarak sadeleştirilmesi gerekiyor.

## 7. Kullanılan / Aktif / Gerekli Alanlar

### Net aktif ve gerekli

- `apps/web`
- `backend`
- `engine`
- `e2e`
- `ai-gateway`
- `docker-compose.yml`
- `start-all.sh`
- `Makefile`
- `playwright.config.ts`
- `collections`
- `reports/templates`

### Aktif ama destekleyici / ikincil

- `api-tests`
- `frameworks/playwright-cucumber-ts`
- `scripts`
- `docs`
- `reports`
- `tools/aday-analizi`
- `tools/aday-degerlendirme`

### Kaynak koddan çok veri/artifact taşıyan ama tamamen gereksiz denemeyecek alanlar

- `engine/datasets`
- `synthetic-data/mostlyai-datasets`
- `synthetic-data/mostlyai-generators`
- `backend/banking-data` (işlevsel olarak kopya, ama veri referansı olabilir)

## 8. Kullanılmayan / Zayıf Bağlı / Temizlik Adayı Alanlar

### 8.1 Çok güçlü silme/taşıma adayı

| Yol | Durum | Gerekçe |
|---|---|---|
| `ai-test-pipeline/` | Neredeyse boş | Sadece `__pycache__` bulundu |
| `test-automation-workspace/` | Boş | Sadece `.DS_Store` var |
| `frameworks/Test_Template/` | Şablon artığı | Kaynak kod yok; büyük ölçüde rapor/IDE çıktısı |
| `apps/web/.next` | Build çıktısı | Kaynak değil |
| `apps/web/node_modules` | Bağımlılık cache | Kaynak değil |
| `backend/.venv` | Yerel ortam | Repoda tutulmamalı |
| `engine/.venv` | Yerel ortam | Repoda tutulmamalı |

### 8.2 Legacy veya kararsız sahiplikte

| Yol | Durum | Gerekçe |
|---|---|---|
| `ai-test-automation/` | Legacy/deneysel | Asıl içerik yerine dev sanal ortam ağırlıklı |
| `ai-engine/` | Deneysel/yardımcı | Runtime hattına bağlı değil, daha çok CLI/plan düzeyi |
| `NexusQATestOtomasyon/` | Legacy ama içerikli | Ayrı Java suite; root seviyede fazladan ağırlık |
| `frameworks/selenium-cucumber-java/` | Legacy ama içerikli | NexusQA ile aynı problem alanında |

### 8.3 Duplicate veya canonicalize edilmesi gereken alanlar

| Yol | Durum | Kanıt |
|---|---|---|
| `backend/banking-data` vs `synthetic-data/banking` | Doğrudan kopya | `diff -rq` boş döndü, `app/main.py` ve `package.json` birebir aynı |
| `backend/synthetic-data-v4` vs `synthetic-data/platform-v4` | Neredeyse aynı | Tek fark log ve venv; ana kaynak aynı |
| `engine/scripts/scaffold_project.py` vs `engine/scripts/legacy/scaffold_project.py` | Aynı script | İçerik fiilen duplicate |
| `NexusQATestOtomasyon` vs `frameworks/selenium-cucumber-java` | Yüksek örtüşme | Aynı teknoloji ve benzer dosya yapısı |

## 9. Generated / Çıktı / Cache / Yerel Meta Alanlar

Bu alanlar ürün kodundan çok çalışma artığı niteliğinde:

- `.claude/worktrees/` → yaklaşık `13G`, 16 worktree
- `apps/web/.next`
- `apps/web/node_modules`
- `backend/.venv`
- `engine/.venv`
- `NexusQATestOtomasyon/target`
- `api-tests/allure-results`
- `frameworks/playwright-cucumber-ts/logs`
- `frameworks/playwright-cucumber-ts/reports`
- `scaffolded_projects/*/.git`
- çok sayıda `__pycache__`, `.pytest_cache`

Not:

- `.claude/worktrees/` ürün deposunun parçası değil; Codex/Claude çalışma kopyaları
- Repo temizliği yapılacaksa en büyük kazanç burada

## 10. Scaffold ve Örnek Projeler

### `scaffolded_projects/`

Durum:

- Üretilmiş örnek/test projeleri
- Kendi `.git` dizinleri var
- `frameworks/playwright-cucumber-ts` ile yüksek benzerlik taşıyor

Değerlendirme:

- Ürün çekirdeği değil
- Demo/örnek/çıktı klasörü olarak tutulabilir
- Kök ürün repo kapsamında ayrı arşivlenmesi daha doğru olur

### `frameworks/playwright-cucumber-ts`

Durum:

- Gerçek bir framework/template
- `Makefile` içinde doğrudan çalıştırılıyor
- Scaffold edilen projelerin temeli gibi davranıyor

Değerlendirme:

- Silinmemeli
- Ama “ana ürün” gibi değil, “framework/template” gibi konumlandırılmalı

## 11. Synthetic Data Alanı

Synthetic-data tarafı kendi içinde 4 ayrı katmana ayrılmış durumda:

| Yol | Durum | Not |
|---|---|---|
| `synthetic-data/platform-v4` | Güncel kaynak | Hafif ve temiz |
| `backend/synthetic-data-v4` | Kopya | Aynı kaynak + local venv/log |
| `synthetic-data/platform` | Daha büyük eski platform | Kendi testleri, docker dosyaları, frontend'i var |
| `backend/synthetic-data-v2` | Legacy | DB dump içeriyor |
| `backend/synthetic-data-v3` | Legacy | Ara sürüm |
| `backend/synthetic-data-bgtsflow` | Legacy | Küçük bir varyant |

Ek olarak:

- `synthetic-data/mostlyai-datasets` → `101M`
- `synthetic-data/mostlyai-generators` → `101M`

Bunlar kod değil; export/artifact veri alanı.

## 12. Dokümantasyon ve Plan Dosyaları

Durum:

- `docs/` altında yaklaşık `102` dosya
- Kökte çok sayıda plan/rapor/sunum dosyası var

Değerlendirme:

- Teknik bağlam açısından değerli
- Ama kök dizinde fazla belge yoğunluğu var
- `docs/archive/` veya `docs/plans/` gibi alt gruplama repo okunabilirliğini artırır

## 13. Doğrulanmış Teknik Sorunlar

Analiz sırasında doğrulanan önemli sorunlar:

1. `apps/web` production build kırık
   - `apps/web/app/(dashboard)/p/[projectId]/workflows/page.tsx` içinde bozuk import var

2. Root npm scriptleri `python` kullanıyor
   - Bu makinede `python` yok, `python3` ve venv interpreter'ları var
   - `package.json` ile `Makefile` tutarlı değil

3. `apps/web` lint akışı interaktif
   - ESLint config yok
   - `next lint` CI-benzeri doğrulama yerine setup prompt açıyor

4. `engine` test toplama kırık
   - Duplicate test basename'leri var
   - `pythonpath = .` eksik olduğu için `services.*` importları düşüyor

5. `backend` test venv'i eksik/yarım
   - `.venv` mevcut ama `pytest` kurulu değil
   - `requirements-dev.txt` pytest içeriyor, ortam drift var

## 14. Sadeleştirme Önerisi

### Korunacak kanonik ürün hattı

- `apps/web`
- `backend`
- `engine`
- `ai-gateway`
- `e2e`
- `collections`
- `reports/templates`

### Ayrı paket/örnek/framework olarak konumlandırılacaklar

- `frameworks/playwright-cucumber-ts`
- `api-tests`
- `tools/*`
- `scaffolded_projects/*`

### Birleştirilecek veya tekilleştirilecekler

- `backend/banking-data` ile `synthetic-data/banking` → tek kaynak seç
- `backend/synthetic-data-v4` ile `synthetic-data/platform-v4` → tek kaynak seç
- `NexusQATestOtomasyon` ile `frameworks/selenium-cucumber-java` → tek canonical Java suite seç
- `engine/scripts/scaffold_project.py` ile `engine/scripts/legacy/scaffold_project.py` → tek dosya bırak

### Arşiv/silme adayı

- `ai-test-pipeline`
- `test-automation-workspace`
- `frameworks/Test_Template`
- `ai-test-automation` (önce gerçekten gerekli özgün kod var mı kontrol et)
- kullanılmayan v2/v3/bgtsflow synthetic-data kopyaları

### Git dışına çıkarılması gerekenler

- `.claude/worktrees`
- `.next`
- `node_modules`
- `.venv`
- `target`
- `allure-results`
- yerel log ve report artefact'ları

## 15. Nihai Karar Cümlesi

Bu repo şu anda “tek ürün monorepo” görünümünden çok “ürün + framework + legacy + generated output + local worktree deposu” görünümünde. Çekirdek ürün net şekilde var, ama onun etrafında büyük miktarda tarihsel ve üretilmiş ağırlık birikmiş.

En hızlı kazanım için önerilen sıra:

1. Cache/artifact temizliği
2. duplicate sentetik veri klasörlerinin tekilleştirilmesi
3. Java test suite sahipliğinin netleştirilmesi
4. legacy AI dizinlerinin arşivlenmesi
5. test/build doğrulama akışlarının yeniden yeşile çekilmesi

