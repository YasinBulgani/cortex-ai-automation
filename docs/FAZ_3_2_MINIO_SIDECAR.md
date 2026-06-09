# Faz 3.2: MinIO Sidecar (S3-compatible Storage)

**Tarih:** 2026-06-09
**Status:** Tamamlandı
**Bağlantı:** ADR-0018 (S3 artifact storage strategy)

## Özet

Faz 3.2, self-hosted S3-compatible artifact storage (MinIO) sidecar'ını entegre eder. Production'da multi-instance deployment için artifact depolamayı dağıtık hale getirir.

**Avantajlar:**
- ✅ External S3/AWS ihtiyacını ortadan kaldırır
- ✅ Tüm artifacts (test results, logs, screenshots) merkezi depoda
- ✅ Presigned URL'ler ile secure direct access
- ✅ Feature parity: AWS S3 ile uyumlu API

## Mimari

```
Backend (8000)  ─┐
Worker          ├─→ boto3 ──→ MinIO S3 API (9000) ──→ /data (persistent)
AI-Worker       ┘
```

**Özellikleri:**
- MinIO container: S3-compatible API server (port 9000)
- MinIO Console: Admin UI (port 9001 prod / 9001 dev)
- Bucket: `neurex-artifacts` (otomatik oluşturulur)
- Credentials: `MINIO_ROOT_USER` / `MINIO_ROOT_PASSWORD` env vars

## Değişiklikler

### 1. docker-compose.prod.yml

**MinIO servisi eklendi:**
```yaml
minio:
  image: minio/minio:RELEASE.2024-06-13T07-09-08Z
  environment:
    MINIO_ROOT_USER: ${MINIO_ROOT_USER:-minioadmin}
    MINIO_ROOT_PASSWORD: ${MINIO_ROOT_PASSWORD}  # Zorunlu
  volumes:
    - minio_data_prod:/data
  healthcheck: curl http://localhost:9000/minio/health/live
```

**MinIO Console servisi eklendi:**
```yaml
minio-console:
  image: minio/minio:RELEASE.2024-06-13T07-09-08Z
  depends_on:
    minio: service_healthy
```

**Backend environment (S3 config):**
```env
ARTIFACT_STORAGE_BACKEND=s3
S3_ENDPOINT_URL=http://minio:9000
S3_BUCKET=neurex-artifacts
S3_ACCESS_KEY_ID=${MINIO_ROOT_USER}
S3_SECRET_ACCESS_KEY=${MINIO_ROOT_PASSWORD}
S3_PREFIX=artifacts/
```

**Worker + AI-Worker:** Aynı S3 config'i alır.

### 2. backend/app/config.py

**Production defaults:**
```python
artifact_storage_backend: str = "s3" if _is_production_env() else "local"
s3_bucket: str = "neurex-artifacts"
s3_endpoint_url: str = "http://minio:9000"  # MinIO default
s3_access_key_id: str = ""  # → MINIO_ROOT_USER
s3_secret_access_key: str = ""  # → MINIO_ROOT_PASSWORD
```

### 3. backend/app/infra/storage.py

**S3Storage bucket initialization:**
```python
def __init__(self, ...):
    # ... boto3 client setup ...
    self._ensure_bucket_exists()  # NEW: Bucket creation on init

def _ensure_bucket_exists(self) -> None:
    """Idempotent bucket creation (MinIO-safe, AWS-compatible)"""
    # Checks if bucket exists → creates if missing → handles race conditions
```

**Mantığı:**
1. Backend/worker başladığında S3Storage instantiate edilir
2. _ensure_bucket_exists() çağrılır (once per process)
3. Bucket varsa: log "mevcut"
4. Bucket yoksa + MinIO: create_bucket() başarılı
5. AWS S3'de: bucket önceden mevcut olmalı
6. Race condition (concurrent creates): 409 BucketAlreadyExists handled

### 4. docker-compose.yml (dev)

**MinIO opsiyonel servisi eklendi:**
```yaml
minio:
  image: minio/minio:RELEASE.2024-06-13T07-09-08Z
  ports:
    - "9000:9000"
    - "9001:9001"
  environment:
    MINIO_ROOT_USER: minioadmin
    MINIO_ROOT_PASSWORD: miniosecretkey  # Dev default
  volumes:
    - minio_data:/data
```

Local'de S3 storage test etmek için:
```bash
docker compose up -d minio
# Browser: http://localhost:9001
```

### 5. Makefile

**Yeni target: make demo-with-minio**
```bash
make demo-with-minio           # Full stack + MinIO + seed
make demo-with-minio-down      # Stop
```

## Kullanım

### Production (.env)

```env
# S3/MinIO (Faz 3.2)
MINIO_ROOT_USER=your_admin_user
MINIO_ROOT_PASSWORD=your_secure_password_here
ARTIFACT_STORAGE_BACKEND=s3
S3_BUCKET=neurex-artifacts
S3_ENDPOINT_URL=http://minio:9000  # Internal network URL
```

**Launch:**
```bash
make prod-up
```

**MinIO Console:**
- URL: http://your-domain/minio-console (nginx reverse proxy)
- Login: MINIO_ROOT_USER / MINIO_ROOT_PASSWORD
- Bucket: `neurex-artifacts` (otomatik oluşturuldu)

### Local Development

**Seçenek A: Local MinIO + Backend**
```bash
docker compose up -d postgres redis minio backend
# MinIO: http://localhost:9001
# Backend S3 kullanıyor: http://minio:9000 (docker network)
```

**Seçenek B: Demo stack (tüm servisler)**
```bash
make demo-with-minio
# Includes: postgres, redis, backend, web, engine, minio, minio-console
```

## Test

### Artifact Upload via API

```bash
# 1. Login
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"admin123"}' \
  | jq -r .access_token)

# 2. Create automation run with artifact
ARTIFACT=$(curl -s -X POST http://localhost:8000/api/v1/automation/runs \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"project_id":"...","name":"test-run"}')

# 3. Upload artifact
curl -X PUT "http://localhost:8000/api/v1/automation/runs/{run_id}/artifacts/output.json" \
  -H "Authorization: Bearer $TOKEN" \
  --data-binary @output.json

# 4. Verify in MinIO console
# Browser: http://localhost:9001
# Bucket: neurex-artifacts
# Path: artifacts/automation/...
```

### Presigned URL Test

```bash
# Backend generates presigned URL
curl -s http://localhost:8000/api/v1/automation/artifacts/{key} \
  -H "Authorization: Bearer $TOKEN" \
  | jq .presigned_url

# Client can fetch directly (doesn't need auth)
curl -s $(jq -r .presigned_url <<< $(curl ...))
```

## Failover / Multi-instance

**Production'da replicated MinIO (Faz 3.3):**
```yaml
# Coming: MinIO distributed mode
# - Multiple MinIO nodes
# - Erasure coding (4+4 = 8 nodes recovery)
# - Shared storage backend (NFS/S3 gateway)
```

## Monitoring

**MinIO metrics (Prometheus):**
```bash
curl http://minio:9000/minio/prometheus/metrics
```

**Health check:**
```bash
curl http://minio:9000/minio/health/live
# 200 OK = ready
```

## Security

**Best practices:**
1. `MINIO_ROOT_PASSWORD` minimum 8 characters
2. Production'da strong password (alphanumeric + symbols)
3. MinIO console sadece internal network'ten erişilebilir
4. S3 credentials (MINIO_ROOT_USER/PASSWORD) env var'dan set
5. TLS/HTTPS: nginx reverse proxy ile handle (Faz 3.4)

## Fallback (Legacy)

**Dev'de local storage kullanmaya geri dönmek:**
```bash
ARTIFACT_STORAGE_BACKEND=local docker compose up backend
# Backend: /app/data/artifacts/ kullanır (no S3)
```

## Bilinen Sınırlamalar

1. **MinIO single-node:** production'da failure point
   - Çözüm (Faz 3.3): MinIO distributed + erasure coding
2. **Persistence:** volume-backed (host failure'da veri kaybı)
   - Çözüm (Faz 3.5): S3 gateway / NFS backend
3. **Replication:** yok (single MinIO instance)
   - Çözüm (Faz 3.3): Multi-node cluster

## Rollout

**Phase 1 (Current - Faz 3.2):**
- ✅ MinIO sidecar (single-node)
- ✅ Bucket auto-creation
- ✅ docker-compose.prod.yml integration
- ✅ S3 defaults in config

**Phase 2 (Faz 3.3):**
- MinIO distributed mode (4+ nodes)
- Erasure coding + recovery
- Nginx ingress integration

**Phase 3 (Faz 3.4):**
- TLS/HTTPS termination
- Cross-region replication (optional)

**Phase 4 (Faz 3.5):**
- NFS/EBS backend option
- Backup automation

## Referanslar

- [MinIO Quickstart](https://docs.min.io/docs/minio-quickstart-guide.html)
- [MinIO Docker](https://hub.docker.com/r/minio/minio/)
- [boto3 S3 Docs](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3.html)
- [ADR-0018: S3 Artifact Storage](../adr/ADR-0018-s3-artifact-storage.md)

---

**Kontrol Listesi:**
- [x] docker-compose.prod.yml: MinIO service + volume
- [x] docker-compose.yml: Optional MinIO (dev)
- [x] config.py: S3 defaults in production
- [x] storage.py: Bucket auto-creation
- [x] Makefile: demo-with-minio target
- [x] Environment variables documented
- [ ] (Faz 3.3) MinIO distributed mode
- [ ] (Faz 3.4) TLS/HTTPS reverse proxy
