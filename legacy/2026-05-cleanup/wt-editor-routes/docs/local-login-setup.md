# Yerel Giriş ve API Kurulumu — Planlama Rehberi

Bu doküman, tarayıcıdan **admin girişinin** (`admin@example.com` / `admin123`) çalışması için gerekli sırayı, doğrulamaları ve sorun giderme adımlarını tanımlar. “Failed to fetch” / “Sunucuya ulaşılamıyor” gibi hataların kök nedeni çoğunlukla **backend’e ulaşılamaması**dır; kullanıcı adı/şifre ancak API ayakta olduktan sonra anlamlıdır.

---

## 1. Amaç ve başarı ölçütleri

| Hedef | Kabul kriteri |
|--------|----------------|
| Web üzerinden giriş | `POST /api/v1/auth/login` → 200 ve `access_token` |
| Tutarlı adresler | Frontend’in `NEXT_PUBLIC_API_BASE` değeri ile backend’in dinlediği host:port **aynı** |
| Tekrarlanabilir kurulum | Yeni geliştirici README + bu doküman ile aynı adımları izleyebilir |

---

## 2. Mimari bağımlılık sırası

```text
PostgreSQL  →  FastAPI (:8000)  →  Tarayıcı → Next.js (:3000) → fetch(API_BASE)
```

- Next.js, istemci tarafında **doğrudan** `NEXT_PUBLIC_API_BASE` adresine istek atar.
- Backend çalışmıyorsa tarayıcı ağ hatası verir; bu **kimlik doğrulama hatası değildir**.

---

## 3. Hızlı uygulama akışı

İlk kez kurulum yapıyorsanız en pratik sıra:

### 3.1 Backend'i ayağa kaldır

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
PYTHONPATH=. python scripts/seed.py
uvicorn app.main:app --reload --port 8000
```

Ayrı terminalde doğrula:

```bash
curl -s http://127.0.0.1:8000/health

curl -s -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"admin123"}'
```

### 3.2 Frontend'i ayağa kaldır

```bash
cd apps/web
cp .env.local.example .env.local
npm install
npm run dev
```

`apps/web/.env.local` içinde en az şu değer olmalı:

```dotenv
NEXT_PUBLIC_API_BASE=http://127.0.0.1:8000
```

Sonra tarayıcıda:

```text
http://localhost:3000/login
```

Not:
- `localhost` ve `127.0.0.1` farki cookie/oturum davranisini etkileyebilir. Mümkünse tek host kullanın.
- Frontend `NEXT_PUBLIC_API_BASE` ile backend gerçek portu birebir aynı olmalı.

### 3.3 Hızlı smoke kontrolü

1. `http://127.0.0.1:8000/health` yanıt veriyor mu?
2. `POST /api/v1/auth/login` token dönüyor mu?
3. Frontend login isteği gerçekten `127.0.0.1:8000` adresine mi gidiyor?
4. Başarılı girişten sonra `/projects` sayfasına yönleniyor mu?

---

## 4. Faz planı

### Faz A — Veritabanı ve ortam

| Adım | Görev | Doğrulama |
|------|--------|------------|
| A1 | PostgreSQL erişilebilir (Docker Compose veya yerel) | Bağlantı / konteyner sağlık |
| A2 | `DATABASE_URL` backend’in beklediği şema ve kullanıcı ile uyumlu | Kök `.env` veya `backend` ortamı tek kaynak olmalı |
| A3 | (İhtiyaç varsa) Redis ve diğer bağımlılıklar | Proje README / docker-compose ile hizalı |

### Faz B — Backend (FastAPI)

| Adım | Görev | Doğrulama |
|------|--------|------------|
| B1 | `cd backend`, venv, `pip install -r requirements.txt` | — |
| B2 | `alembic upgrade head` | Şema güncel |
| B3 | `PYTHONPATH=. python scripts/seed.py` | Konsolda seed onayı; varsayılan admin oluşur |
| B3\* | Mevcut DB’de admin parolası uyuşmuyorsa | `SEED_RESET_ADMIN_PASSWORD=1` ile seed (parola `SEED_ADMIN_PASSWORD` veya varsayılan `admin123`) |
| B4 | `uvicorn app.main:app --reload --port 8000` | Süreç çalışıyor |
| B5 | `curl -s http://127.0.0.1:8000/health` | `{"status":"ok","service":"bgts-backend"}` |
| B6 | Login API | Aşağıdaki `curl` ile `access_token` |

Örnek login doğrulaması:

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"admin123"}'
```

### Faz C — Frontend (Next.js)

| Adım | Görev | Doğrulama |
|------|--------|------------|
| C1 | `cd apps/web`, `npm install` | — |
| C2 | `apps/web/.env.local` oluştur | `apps/web/.env.local.example` dosyasını kopyalayın; `NEXT_PUBLIC_API_BASE=http://127.0.0.1:8000` |
| C3 | `npm run dev` (monorepo kökünden: `npm run web:dev`) | `http://localhost:3000` açılır |
| C4 | Giriş denemesi | Hata durumunda mesajlar: `apps/web/app/login/page.tsx` (ağ hatalarında Türkçe açıklama) |

**Önemli:** Yalnızca repo kökündeki `.env` dosyası, Next.js tarafından **otomatik yüklenmeyebilir**; `apps/web/.env.local` kullanımı önerilir.

### Faz D — Uçtan uca kontrol listesi

Sırayla işaretleyin:

1. [ ] `GET http://127.0.0.1:8000/health` başarılı  
2. [ ] Yukarıdaki `curl` login `access_token` ve gerekirse `refresh_token` döndürüyor  
3. [ ] Tarayıcıda `/login` → giriş → `/projects` yönlendirmesi  
4. [ ] DevTools → Network: login isteğinin gittiği URL’nin `NEXT_PUBLIC_API_BASE` ile aynı olduğunu doğrulayın  

---

## 5. Varsayılan kimlik bilgileri

| Alan | Değer |
|------|--------|
| E-posta | `admin@example.com` |
| Parola | `admin123` |

Kaynak: `backend/scripts/seed.py` (`SEED_ADMIN_EMAIL`, `SEED_ADMIN_PASSWORD` ile override edilebilir).

Geliştirici hızlı giriş hesabı:

| Alan | Değer |
|------|--------|
| E-posta | `test@test.com` |
| Parola | `test` |

Bu hesap da `backend/scripts/seed.py` içinde seed edilir ve geliştirme ortamında hızlı doğrulama için kullanışlıdır.

---

## 6. Sorun giderme matrisi

| Gözlem | Olası neden | İlk aksiyon |
|--------|-------------|-------------|
| “Sunucuya ulaşılamıyor” / Failed to fetch | API kapalı veya yanlış port | B4–B5; `NEXT_PUBLIC_API_BASE` ile port eşleşmesi |
| HTTP 401, “E-posta veya parola hatalı” | Yanlış şifre veya DB’de farklı hash | B3\* ile parola sıfırlama veya seed |
| HTTP 403, hesap devre dışı | `is_active=false` | Kullanıcı kaydı / seed |
| Login başarılı görünüyor ama tekrar `/login` sayfasına dönüyor | Auth cookie yazılamadı veya middleware session göremiyor | Tarayıcı `Application > Cookies` altında `bgts_access_token`/`bgts_refresh_token` var mı kontrol edin; host ve protokol tutarlılığını doğrulayın |
| CORS hatası (konsol) | İzin verilen origin yok | Backend `CORS_ORIGINS` içinde `http://localhost:3000` |
| `connection refused` | Servis dinlemiyor veya yanlış IP | `127.0.0.1` vs `localhost` tutarlılığı |

---

## 7. Hızlı teşhis komutları

Backend süreci ve sağlık:

```bash
curl -i http://127.0.0.1:8000/health
curl -i http://127.0.0.1:8000/ready
```

Login API doğrudan testi:

```bash
curl -i -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","password":"test"}'
```

Frontend env kontrolü:

```bash
cd apps/web
rg "NEXT_PUBLIC_API_BASE" .env.local .env.local.example lib/api-client.ts
```

Port dinleme kontrolü:

```bash
lsof -nP -iTCP:8000 -sTCP:LISTEN
lsof -nP -iTCP:3000 -sTCP:LISTEN
```

---

## 8. E2E / farklı port notu

Playwright tarafında API tabanı tek kaynaktan yönetilir: `e2e/config/runtime.ts` (`API_BASE`, varsayılan `8875`). Manuel `uvicorn --port 8000` ile geliştirme yaparken E2E ortamı ile karışmaması için:

- uygulama geliştirme oturumunda `NEXT_PUBLIC_API_BASE=http://127.0.0.1:8000`,
- E2E oturumunda `API_BASE=http://127.0.0.1:8875`

değerlerini bilinçli ayırın.

---

## 9. Tahmini süre (ilk kurulum)

| Blok | Süre (kabaca) |
|------|----------------|
| PostgreSQL + env | 15–60 dk |
| Backend migrate + seed | 10–20 dk |
| Frontend `.env.local` + dev | 5–10 dk |
| Doğrulama | 10 dk |

---

## 10. İlgili dosyalar (referans)

| Konu | Yol |
|------|-----|
| Seed, admin, parola sıfırlama bayrağı | `backend/scripts/seed.py` |
| Login API | `backend/app/domains/auth/router.py` |
| Frontend giriş | `apps/web/app/login/page.tsx` |
| API tabanı | `apps/web/lib/api-client.ts` (`API_BASE`) |
| API re-export yardımcı dosyası | `apps/web/lib/api.ts` |
| Örnek Next env | `apps/web/.env.local.example` |
| Genel kurulum | `README.md` |

---

## 11. Süreç iyileştirme (opsiyonel)

- Yeni ekip üyesi onboarding’de bu checklist’i kullanın.  
- CI’da backend + migrate + kısa smoke login (API düzeyinde) düşünülebilir.  
- Parola sıfırlama sadece **geliştirme** ortamında `SEED_RESET_ADMIN_PASSWORD` ile kullanılmalı; üretimde farklı prosedür.

---

## 12. Auth onboarding hızlı kontrolü

Yeni ekip üyesi için 5 dakikalık doğrulama:

1. `POST /api/v1/auth/login` başarılı mı?
2. Tarayıcıda `bgts_access_token` ve `bgts_refresh_token` cookie'leri oluşuyor mu?
3. `apps/web/middleware.ts` public path dışında cookie yoksa `/login` yönlendirmesi yapıyor mu?
4. `apps/web/lib/api-client.ts` üzerinden yapılan isteklerde `credentials: include` aktif mi?
5. Login sonrası `/projects` yerine tekrar `/login` olursa host/protokol (`localhost` vs `127.0.0.1`, `http` vs `https`) farklılığı var mı?

Bu doküman, yerel giriş sorunlarını sistematik olarak çözmek için ana referanstır; güncelleme gerektiğinde bu dosyayı ve `README.md`’yi birlikte gözden geçirin.

---

## 13. Operasyonel referans seti

Yerel onboarding ve production parity için birlikte takip edin:

1. `README.md` (geliştirme başlangıcı)
2. `DEPLOYMENT_OPS_GUIDE.md` (staging/production runbook)
3. `docs/runtime-hardening-checklist.md` (runtime zorunlulukları)
4. `docs/dependency-governance.md` (dependency/sürüm yönetimi)
