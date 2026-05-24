# BGTS Test Dönüşüm — Test Verisi Hazırlama Rehberi

**Doküman Versiyonu:** 1.0  
**Tarih:** 2026-04-03

---

## 1. Test Ortamı Kurulumu

### Ön Gereksinimler

```
PostgreSQL :5432 (docker compose up -d postgres)
Redis      :6379 (docker compose up -d redis)
Backend    :8000 (uvicorn app.main:app --reload --port 8000)
Frontend   :3000 (npm run dev — apps/web)
```

### Seed Çalıştırma

```bash
cd backend
source .venv/bin/activate
export PYTHONPATH=.

# 1. Admin kullanıcı + roller
python scripts/seed.py
# Çıktı: admin@example.com / admin123

# 2. TSPM demo verileri (projeler, senaryolar, akışlar)
python scripts/seed_tspm.py

# 3. Sentetik veri demo (veri setleri, kurallar)
python scripts/seed_demo.py
```

---

## 2. Kullanıcı Test Verileri

### Varsayılan Kullanıcılar

| E-posta | Parola | Rol | Amaç |
|---------|--------|-----|------|
| `admin@example.com` | `admin123` | admin | Tam yetkili test |
| `operator@test.com` | `test123` | operator | CRUD test (oluşturulmalı) |
| `viewer@test.com` | `test123` | viewer | Sadece okuma testi (oluşturulmalı) |
| `disabled@test.com` | `test123` | — | Devre dışı hesap testi (oluşturulmalı, is_active=False) |

### Kullanıcı Oluşturma API (Admin token ile)

```bash
# Operator kullanıcı oluşturma
curl -X POST http://127.0.0.1:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "operator@test.com",
    "password": "test123",
    "password_confirm": "test123",
    "first_name": "Test",
    "last_name": "Operator"
  }'
```

---

## 3. Proje Test Verileri

### Minimum Veri Seti (Smoke Test)

| Proje | Senaryo Sayısı | Koşu | Gereksinim | Regresyon Seti |
|-------|---------------|------|------------|----------------|
| Smoke Proje | 3 | 1 | 2 | 1 |

### Orta Ölçekli Veri Seti (Fonksiyonel Test)

| Proje | Senaryo | Koşu | Gereksinim | Regresyon | Zamanlama | Akış | Onay |
|-------|---------|------|------------|-----------|-----------|------|------|
| Payment API | 20 | 5 | 10 | 3 | 2 | 2 | 5 |
| Auth Module | 15 | 3 | 8 | 2 | 1 | 1 | 3 |
| Empty Project | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

### Büyük Ölçekli Veri Seti (Performans Test)

| Proje | Senaryo | Koşu | Gereksinim |
|-------|---------|------|------------|
| Performance Test | 1000 | 100 | 200 |

---

## 4. API ile Veri Oluşturma Scriptleri

### Token Alma

```bash
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"admin123"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
```

### Proje Oluşturma

```bash
PROJECT_ID=$(curl -s -X POST http://127.0.0.1:8000/api/v1/tspm/projects \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Test Projesi","description":"E2E test verisi"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "Project ID: $PROJECT_ID"
```

### Senaryo Oluşturma

```bash
SCENARIO_ID=$(curl -s -X POST "http://127.0.0.1:8000/api/v1/tspm/projects/$PROJECT_ID/scenarios" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title":"Login Başarılı Senaryo",
    "description":"Geçerli kullanıcı girişi",
    "status":"draft",
    "steps":[
      {"order":1,"keyword":"Given","text":"Kullanıcı login sayfasında"},
      {"order":2,"keyword":"When","text":"Geçerli bilgilerle giriş yapıyor"},
      {"order":3,"keyword":"Then","text":"Dashboard görüntülenir"}
    ]
  }' | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "Scenario ID: $SCENARIO_ID"
```

### Gereksinim Oluşturma ve Bağlama

```bash
REQ_ID=$(curl -s -X POST "http://127.0.0.1:8000/api/v1/tspm/projects/$PROJECT_ID/requirements" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"external_id":"REQ-001","title":"Login fonksiyonu","priority":"high"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

curl -s -X POST "http://127.0.0.1:8000/api/v1/tspm/projects/$PROJECT_ID/scenarios/$SCENARIO_ID/requirements" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"requirement_ids\":[\"$REQ_ID\"]}"
```

### Koşu Oluşturma ve Sonuç Güncelleme

```bash
EXEC_DATA=$(curl -s -X POST "http://127.0.0.1:8000/api/v1/tspm/projects/$PROJECT_ID/executions" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"name\":\"Test Koşusu\",\"scenario_ids\":[\"$SCENARIO_ID\"]}")
EXEC_ID=$(echo $EXEC_DATA | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "Execution ID: $EXEC_ID"
```

### Test Veri Seti Oluşturma

```bash
curl -s -X POST "http://127.0.0.1:8000/api/v1/tspm/projects/$PROJECT_ID/test-data" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name":"Login Verileri",
    "columns":[{"name":"email"},{"name":"password"},{"name":"expected"}],
    "rows":[
      {"email":"admin@example.com","password":"admin123","expected":"success"},
      {"email":"wrong@test.com","password":"wrong","expected":"fail"},
      {"email":"","password":"admin123","expected":"validation_error"}
    ]
  }'
```

---

## 5. Veritabanı Temizleme

### Tüm Test Verisini Sıfırlama

```bash
docker compose down -v
docker compose up -d postgres redis
sleep 5
cd backend
source .venv/bin/activate
alembic upgrade head
PYTHONPATH=. python scripts/seed.py
```

### Sadece TSPM Verisini Temizleme

```sql
TRUNCATE tspm_projects CASCADE;
```

---

## 6. Test Veri Durumları Matrisi

| Durum | Açıklama | Kullanıldığı Testler |
|-------|----------|---------------------|
| Boş proje | Senaryo, koşu, gereksinim yok | TC-1602, Dashboard empty state |
| Senaryo var, koşu yok | Senaryolar mevcut ama hiç çalıştırılmamış | TC-0904, Regresyon önerisi |
| Koşular var, sonuçlar pending | Koşu oluşturulmuş ama sonuçlar güncellenmemiş | TC-0602 |
| Koşular tamamlanmış | Passed/failed sonuçlar mevcut | TC-0701, TC-0702, Trend |
| Flaky senaryolar | Aynı senaryo farklı koşularda passed/failed | TC-0702, Flaky test |
| Tam kapsam | Tüm gereksinimler senaryoya bağlı | TC-1004, Coverage 100% |
| Kısmi kapsam | Bazı gereksinimler bağlantısız | TC-1005, Coverage gaps |
| Versiyonlanmış senaryolar | En az 2 versiyon mevcut | TC-0308, Diff |
| Veri bağlamalı senaryolar | Test veri seti + binding mevcut | TC-1203, Expanded |
