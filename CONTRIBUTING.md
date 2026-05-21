# Contributing to TestwrightAI

Bu dokümana hoş geldin. Amacı: projeye katkı sürecini net, tekrarlanabilir ve hızlı kılmak.

Bir sorunun olduğunda önce burayı oku, sonra `#engineering` kanalına sor.

## İçindekiler

- [İlk kurulum](#ilk-kurulum)
- [Günlük akış](#günlük-akış)
- [Branch & PR kuralları](#branch--pr-kuralları)
- [Commit mesajı stili](#commit-mesajı-stili)
- [Testler — "nereye yazarım?"](#testler--nereye-yazarım)
- [Mimari kararlar (ADR)](#mimari-kararlar-adr)
- [Legacy / arşiv politikası](#legacy--arşiv-politikası)
- [Kod stili & lint](#kod-stili--lint)
- [Yayınlama (release) akışı](#yayınlama-release-akışı)

---

## İlk kurulum

```bash
# 1. Repo'yu klonla
git clone https://github.com/YasinBulgani/BGTS-Test-Donusum.git
cd BGTS-Test-Donusum

# 2. .env hazırla
cp .env.example .env
# OPENAI_API_KEY, ANTHROPIC_API_KEY ekle

# 3. Pre-commit kancalarını kur (bir kez)
pip install pre-commit
pre-commit install

# 4. Altyapıyı ayağa kaldır
docker compose up -d postgres redis ai-gateway

# 5. Backend
cd backend
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# 6. Engine (ayrı terminal)
cd engine
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python app.py

# 7. Frontend (ayrı terminal)
cd apps/web
npm install && npm run dev
```

**Önkoşullar:** Docker + Compose v2, Python 3.11+, Node 20+.

---

## Günlük akış

```bash
# 1. main'den güncel branch aç
git checkout main && git pull
git checkout -b feat/<kısa-konu>

# 2. Değişikliğini yap, commit et
git add <files>
git commit -m "feat(<domain>): ..."
# pre-commit hook'ları otomatik çalışır

# 3. Test et
make test-smoke        # hızlı (~2 dk)
make test-backend-unit # backend değişikliği yaptıysan

# 4. Push + PR
git push -u origin HEAD
gh pr create
```

---

## Branch & PR kuralları

### Branch adı

| Prefix | Ne zaman | Örnek |
|---|---|---|
| `feat/` | Yeni özellik | `feat/tspm-bulk-import` |
| `fix/` | Bug fix | `fix/runner-timeout` |
| `refactor/` | Davranış değişmez, kod yeniden düzenleme | `refactor/engine-llm-proxy` |
| `chore/` | Bağımlılık, CI, tooling | `chore/upgrade-playwright` |
| `docs/` | Sadece dokümantasyon | `docs/adr-monorepo` |

### PR boyutu

- **İdeal:** < 400 satır diff
- **Maksimum:** 1000 satır (daha büyükse böl)
- **Her PR tek bir konu** — "refactor + fix + feature" karışık olmasın

### PR template (otomatik dolar, yoksa ekle)

```markdown
## Özet
<1-3 cümle>

## Değişen davranış
- Kullanıcı görünürü A → B
- API değişikliği: yok / eklenen endpoint / kırıcı

## Test planı
- [ ] `make test-smoke` yeşil
- [ ] İlgili unit test eklendi/güncellendi
- [ ] Migration varsa `alembic upgrade head` başarıyla çalıştı

## İlgili
- Jira: TWAI-###
- ADR: docs/adr/NNNN-...
```

### Onay politikası

- Normal PR: 1 onay
- Güvenlik-hassas (`/backend/app/domains/auth/`, `/.env.example`, `/infra/k8s/`): 2 onay
- `legacy/` altında değişiklik: **yasak** — CI guard reddeder
- `main` direct push: **yasak** — branch protection aktif

---

## Commit mesajı stili

[Conventional Commits](https://www.conventionalcommits.org/) izlenir:

```
<type>(<scope>): <kısa açıklama — imperative, lowercase>

<gövde — neden, nasıl, takas>

<footer — Closes #, ADR refs>
```

### Type'lar

`feat`, `fix`, `refactor`, `chore`, `docs`, `test`, `ci`, `perf`, `style`, `revert`.

### Örnekler

```
feat(tspm): bulk test case import — CSV parser + dry-run
fix(engine): runner timeout'u envden al — 300s sabit değer bug'ı
refactor(frontend,docs): cleanup + architecture contracts
chore(legacy): archive mostlyai data artifacts
docs(adr): establish ADR system with 5 foundational records
```

### Kötü örnekler

- ❌ `update` / `fix` / `wip`
- ❌ "Fixed bug." (emir kipi değil)
- ❌ Çok uzun tek satır (< 72 karakter hedefle)

---

## Testler — "nereye yazarım?"

Tek kaynak: [`docs/testing/TEST_STRATEGY.md`](docs/testing/TEST_STRATEGY.md)

Hızlı karar:

```
Ne test ediyorsun?
├─ Python fonksiyon, DB/HTTP yok    → backend/tests/unit/  veya engine/tests/unit/
├─ Backend endpoint (DB + auth)      → backend/tests/integration/
├─ Engine endpoint                   → engine/tests/integration/
├─ API kontrat                       → api-tests/contracts/
├─ Frontend component                → apps/web/app/__tests__/
├─ Full user journey                 → e2e/
├─ BDD senaryo                       → frameworks/playwright-cucumber-ts/features/
└─ Yük/stres                         → performance-tests/
```

Her teste marker ver: `smoke`, `regression`, `slow`, `ai`, `requires_db`, `requires_redis`.

Detay: [ADR-0005](docs/adr/0005-test-taksonomisi.md)

---

## Mimari kararlar (ADR)

Geri dönüşü pahalı bir karar aldıysan (DB şeması, auth, API şekli, kütüphane) bir ADR yaz:

```bash
cp docs/adr/0001-monorepo-yapisi.md docs/adr/NNNN-senin-konun.md
# düzenle, PR'a ekle, indeksi güncelle (docs/adr/README.md)
```

Mevcut ADR'lar:

- [0001](docs/adr/0001-monorepo-yapisi.md) — Monorepo yapısı
- [0002](docs/adr/0002-engine-vs-backend-ayirimi.md) — Engine vs Backend ayrı kalıyor
- [0003](docs/adr/0003-synthetic-data-konsolidasyonu.md) — Synthetic-data v4 ana platform
- [0004](docs/adr/0004-legacy-silme-politikasi.md) — Legacy 6 ay saklama
- [0005](docs/adr/0005-test-taksonomisi.md) — Test katmanları

**ADR yazmalısın:**
- Yeni kütüphane/framework seçtin
- 2+ meşru alternatif arasından birini tercih ettin
- DB şeması değişti
- Auth/auth akışına dokundun

**ADR yazmazsın:**
- Bug fix, küçük refactor, kod stili, bağımlılık bump

---

## Legacy / arşiv politikası

[ADR-0004](docs/adr/0004-legacy-silme-politikasi.md) — 6 ay saklama.

**Özetle:**

1. Kullanılmayan modülü silme, `legacy/<YYYY-MM-kampanya>/` altına `git mv` yap
2. `legacy/README.md`'yi güncelle (neden + hedef silme tarihi)
3. CI guard legacy/ altı değişiklikleri reddeder
4. 6 ay sonra `git rm -rf` — git history'de kalır

Geri almak için: `git mv legacy/... <eski-yol>` + restore ADR'ı yaz.

---

## Kod stili & lint

### Python

- **Formatter:** `ruff format` (repo kökünden `make format` veya pre-commit)
- **Linter:** `ruff check`
- **Type checker:** `mypy` (strict mode — `backend/app/domains/*/` altında zorunlu)
- **Docstring:** İngilizce, 1-satır özet + detay gerekirse

### TypeScript

- **Formatter:** Prettier (`.prettierrc`)
- **Linter:** ESLint + `@next/eslint-config-next`
- **Type:** Strict TS (`tsconfig.json` strict=true)

### Genel

- Her commit öncesi pre-commit çalışır (PII/Türkçe normalize/DSL guards)
- Fonksiyonlar küçük (tek sorumluluk, < 50 satır hedef)
- İsim konvansiyonu: `snake_case` (Python), `camelCase` (TS), `PascalCase` (sınıflar)
- Yorum yazma zorunluluğu yok; açık kod > ayrıntılı yorum. Ancak **ADR referansı** (`# ADR-0002`) ve **takas** yorumları değerli.

---

## Yayınlama (release) akışı

### Semver

`v<major>.<minor>.<patch>` — backward compat kırıcı = major.

### Release flow

```bash
# 1. Son main commit'i tag'le
git checkout main && git pull
git tag -a v0.5.0 -m "Release 0.5.0: legacy cleanup, engine proxy"
git push origin v0.5.0

# 2. Release notları (gh cli)
gh release create v0.5.0 --generate-notes

# 3. Deploy workflow otomatik tetiklenir (.github/workflows/deploy.yml)
```

---

## Yardım

- Teknik soru: `#engineering` Slack
- Mimari karar: ADR yaz + PR
- Acil prod sorunu: `#incidents` + on-call bildirimi
- Bu dokümanda eksik/yanlış: PR aç

---

## İlgili dokümanlar

- [README.md](README.md) — proje genel bakış
- [docs/adr/](docs/adr/) — mimari kararlar
- [docs/architecture/engine-backend-contract.md](docs/architecture/engine-backend-contract.md)
- [docs/testing/TEST_STRATEGY.md](docs/testing/TEST_STRATEGY.md)
- [legacy/README.md](legacy/README.md) — arşiv politikası
