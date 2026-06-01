# Premium Test Flow & Scenario Management Platform — Ürün Özeti

## Vizyon

Kurumsal test ekipleri için **kaynaklardan gereksinim çıkarımı → AI ile senaryo taslağı → onay kuyruğu → senaryo havuzu → akış ve regresyon → execution ve dashboard** zincirini tek üründe yönetmek. **AI önerir; kullanıcı onaylar ve kaydeder.**

## Hedef kullanıcı

Test liderleri, kalite mühendisleri ve otomasyon ekipleri; çok projeli, denetlenebilir ve veri yoğun arayüzden kaçınan kurumsal kullanım.

## Bilgi mimarisi (IA)

| Alan | Route (Next.js) | Amaç |
|------|-----------------|------|
| Giriş | `/login` | JWT tabanlı oturum; kurumsal tek sütun form. |
| Projeler | `/projects` | Proje kartları / liste; boş durum ve arşiv filtresi. |
| Proje özeti | `/p/[projectId]` | Metrik kartları, son aktivite, hızlı aksiyonlar. |
| Senaryolar | `/p/[projectId]/scenarios` | Arama, filtre, çoklu seçim, bulk işlemler. |
| Senaryo detay | `/p/[projectId]/scenarios/[id]` | Tam sayfa detay; versiyon / audit paneli. |
| Senaryo oluştur/düzenle | `/p/[projectId]/scenarios/new`, `.../edit/[id]` | Tek sayfa form + önizleme. |
| Onaylar | `/p/[projectId]/approvals` | Kuyruk; split view: kaynak ↔ AI taslağı. |
| İçe aktarma | `/p/[projectId]/import` | Kaynak seçimi, yükleme, durum ve log. |
| Neurex Management | `/p/[projectId]/management` | Manuel test repository, test plan/run, tester atama ve kalite raporları. |

Faz 2+: akış editörü (`/flows`), execution (`/executions`), asistan, gelişmiş RBAC. Manuel QA operasyonu için Neurex Management ayrı ürün yüzeyi olarak büyür; senaryo tasarımı Studio/TSPM tarafında, manuel koşum hafızası Management tarafında tutulur.

## Temel kullanıcı akışları

1. **Proje oluştur** → üye davet (ileride) → dashboard’tan senaryo veya import başlat.
2. **Dosya içe aktar** → n8n pipeline (extract → generate) → onay kuyruğuna düşen taslaklar.
3. **Onay** → approve / reject / düzenleme ile senaryo havuzuna yazım.
4. **Senaryo yönetimi** → liste, arama, bulk export; detayda versiyon geçmişi.

## Tasarım dili

Bol beyaz alan, güçlü tipografi, tek birincil aksiyon rengi, düşük gürültü. Dark/light tema `apps/web` içinde CSS değişkenleri ile (`--bg`, `--fg`, `--accent`, …).

## API yüzeyi (özet)

Premium domain REST API, mevcut legacy rotalarla çakışmaması için **`/api/v1/tspm/*`** altında toplanır: projeler, senaryolar (bulk), onaylar, importlar, `POST .../ai/runs`, imzalı `POST .../webhooks/n8n/...` callback’leri.

Neurex Management için manuel test operasyon API'si ayrı prefix kullanır: **`/api/v1/test-management/*`**. Bu sınır test case repository, test plan/cycle/run, execution evidence, defect link ve manuel QA raporlarını kapsar.

## MVP kapsamı (Faz 1)

Auth (mevcut JWT), proje CRUD, senaryo CRUD + arama/filtre stub, onay kuyruğu ve split view, import stub + durum, `ai_runs` kaydı ve n8n durum güncellemesi, Next.js shell ve smoke E2E.
