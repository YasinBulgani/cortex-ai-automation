# TestwrightAI Rebranding — Deployment Checklist

> Bu belge, `BGTS Test Dönüşüm` → `TestwrightAI` rebranding'inin uygulandığı
> bir ortama (dev / staging / prod) geçiş için yapılması gerekenleri sıralar.
> Commit'ler: Faz 1 (7e3e5bf), Faz 2 (42e89d6), Faz 3 (e416c1f), Faz 4 (bu).

---

## 1. Geliştirici Makinaları (dev)

### 1.1 Kod pull ve temizlik
```bash
git pull origin feat/dsl-consolidation
docker compose down
docker volume rm bgts_test_donusum_pgdata 2>/dev/null || true   # OPSİYONEL: temiz DB ile başlamak için
```

### 1.2 `.env` dosyanı güncelle
Aşağıdaki değişken adlarını güncelle (varsa):

| Eski | Yeni |
|------|------|
| `BGTS_API_URL` | `TWAI_API_URL` |
| `BGTS_ADMIN_EMAIL` | `TWAI_ADMIN_EMAIL` |
| `BGTS_ADMIN_PASSWORD` | `TWAI_ADMIN_PASSWORD` |
| `BGTS_DSL_PILOT` | `TWAI_DSL_PILOT` |
| `BGTS_ENABLE_AI_STACK` | `TWAI_ENABLE_AI_STACK` |
| `BGTS_ENABLE_OPEN_WEBUI` | `TWAI_ENABLE_OPEN_WEBUI` |
| `BGTS_OLLAMA_HOST` | `TWAI_OLLAMA_HOST` |
| `BGTS_OLLAMA_WARM_MODELS` | `TWAI_OLLAMA_WARM_MODELS` |
| `BGTS_BACKEND_URL` | `TWAI_BACKEND_URL` |

Ayrıca:
- `DATABASE_URL`: `bgts_user:bgts_pass` → `twai_user:twai_pass`, `/bgts_db` → `/twai_db`
- `ENGINE_INTERNAL_KEY`: eğer `bgts-internal-key-change-me` ise `twai-internal-key-change-me`
- `BROWSERSTACK_PROJECT`: "BGTS Nexus QA" → "TestwrightAI Visium Operations"

### 1.3 Container'ları yeniden başlat
```bash
docker compose up -d
docker ps --format 'table {{.Names}}\t{{.Status}}'
# Beklenen: twai_postgres, twai_redis, twai_backend, twai_engine, twai_web, nexusqa_ai_gateway
```

Not: Eski `bgts_*` container'lar Docker cache'inde kalabilir.
`docker rm -f bgts_postgres bgts_redis bgts_backend bgts_engine bgts_worker bgts_web` ile kaldırılabilir.

### 1.4 DB Rebrand (veri saklanacaksa)
Eğer üstteki adımda volume'u sıfırlamadıysan:

```bash
# Sadece postgres açık olsun
docker compose down
docker compose up -d postgres

# Rename scripti
PGHOST=127.0.0.1 PGSUPERUSER=postgres PGSUPERPASS=postgres ./scripts/rebrand-db.sh

# Her şey çalışsın
docker compose up -d
```

Rollback gerekirse: `./scripts/rebrand-db.sh --rollback`

### 1.5 Smoke test
```bash
curl http://localhost:8000/health        # {"status":"ok","service":"testwright-ai-backend"}
curl http://localhost:5001/health        # {"status":"ok","service":"testwright-ai-automation-engine"}
open http://localhost:3000               # TestwrightAI UI
open http://localhost:8000/docs          # OpenAPI → "TestwrightAI Platform API"
```

---

## 2. macOS LaunchDaemons (Ollama + Watchdog servisleri)

```bash
# Eski plist'leri kaldır
sudo launchctl unload /Library/LaunchDaemons/com.bgts.ollama.plist 2>/dev/null || true
sudo launchctl unload /Library/LaunchDaemons/com.bgts.watchdog.plist 2>/dev/null || true
sudo rm -f /Library/LaunchDaemons/com.bgts.*.plist

# Yenilerini yükle
sudo cp scripts/com.testwrightai.ollama.plist /Library/LaunchDaemons/
sudo cp scripts/com.testwrightai.watchdog.plist /Library/LaunchDaemons/
sudo launchctl load /Library/LaunchDaemons/com.testwrightai.ollama.plist
sudo launchctl load /Library/LaunchDaemons/com.testwrightai.watchdog.plist

# Doğrula
sudo launchctl list | grep testwrightai
```

---

## 3. /etc/hosts (Nginx kullanıyorsan)

```bash
sudo sed -i '' 's/bgts.local/testwright-ai.local/g' /etc/hosts
sudo sed -i '' 's/api.bgts.local/api.testwright-ai.local/g' /etc/hosts
sudo sed -i '' 's/ai.bgts.local/ai.testwright-ai.local/g' /etc/hosts
```

Örnek yeni entry:
```
127.0.0.1  testwright-ai.local api.testwright-ai.local ai.testwright-ai.local
```

---

## 4. Kubernetes (staging/prod)

```bash
# Namespace zaten mevcutsa:
kubectl delete namespace bgts      # veri kaybı: önce backup al!

# Veya secrets'ı rename et (namespace silmeden):
kubectl get secret bgts-secrets -n bgts -o yaml | \
  sed 's/bgts-secrets/testwright-ai-secrets/g; s/namespace: bgts/namespace: testwright-ai/g' | \
  kubectl apply -f -

# Yeni manifestleri apply et
kubectl apply -f infra/k8s/deployment.yaml
kubectl apply -f infra/k8s/service.yaml

# Doğrula
kubectl get pods,svc,ingress -n testwright-ai
```

---

## 5. GitHub Actions

Workflow dosyaları yeniden adlandırıldı:
- `.github/workflows/bgts-e2e.yml` → `testwright-ai-e2e.yml`
- `.github/workflows/bgts-scheduled.yml` → `testwright-ai-scheduled.yml`

**Önemli:** Eğer `main` branch'inde bu workflow'lar çalışıyorsa, rename
GitHub UI'da "not found" hatası verebilir. Branch protection rules'da eski
adla olan required checks varsa, yeni adla güncellemen gerekir.

---

## 6. External Dış Servisler (kullanıcı aksiyonu)

| Servis | Aksiyon |
|--------|---------|
| **BrowserStack** | Yeni project adı: `TestwrightAI Visium Operations` (eski: `BGTS Nexus QA`) — BrowserStack dashboard'unda da elle güncelle |
| **Jira** | `project_key = "BGTS"` kullanıcı konfigürasyonu olduğu için dokunulmadı. Gerekirse TSPM Integrations sayfasından güncelle |
| **GitHub Repo** | Opsiyonel: repo adını `BGTS_Test_Donusum` → `testwright-ai` olarak rename et (`DSL_GIT_GITHUB_REPO` env otomatik güncellenmez — manuel) |
| **Sentry** | `apps/web/next.config.mjs` `org: "bgts"` olarak bırakıldı (Sentry hesap adı) — gerekirse Sentry'de org rename yap |

---

## 7. Dokunulmayanlar (Bilinçli tercih)

Aşağıdakiler **runtime state veya dış bağımlılık** sebebiyle değişmedi:

- `localStorage` key'leri: `bgts_active_project`, `bgts_persona_focus`, `bgts_product_family_focus`, `bgts_pending_schema`, `bgts_schema_templates`
- Custom DOM event'leri: `bgts-persona-changed`, `bgts-product-family-changed`
- Redis key prefix'leri: `bgts:auth:revoked-access:`, `bgts:auth:password-reset:`
- APScheduler job ID: `bgts-ai-ops-agent`, `bgts_schedule_{id}`
- Logger namespace'leri: `bgts.security`, `bgts.audit`
- Python step dosya adları: `engine/steps/bgts_*_steps.py` (DSL katalog bağımlılığı)
- Proje kök klasör adı: `BGTS_Test_Donusum` (kullanıcı manuel rename etmeli)
- macOS launchctl reverse-DNS: `com.testwrightai.*` (yeni); eski `com.bgts.*` unload gerekir
- `docs/project-history/` altındaki tarihsel dokümanlar
- `ai-engine/`, `test-automation-workspace/` gibi "silinmeye aday" modüller

---

## 8. Rollback

Rebranding'i tümüyle geri almak isterse:

```bash
# Commit'leri geri al
git revert e416c1f      # Faz 3
git revert 42e89d6      # Faz 2 (DSL WIP dahil — DİKKAT)
git revert 7e3e5bf      # Faz 1

# DB rollback
./scripts/rebrand-db.sh --rollback

# .env ve /etc/hosts geri al (yukarıdaki 1.2 ve 3. adımları tersine uygula)
```

---

*Bu checklist, rebranding Faz 4 ile birlikte oluşturulmuştur — 2026-04-17*
