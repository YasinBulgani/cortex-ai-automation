# BGTS AI Synthetic Data Platform (PostgreSQL MVP)

Bu klasör, AI destekli Sentetik Bankacılık Verisi üretmek için tasarlanmış yeni nesil modüler yapıdır. PostgreSQL asenkron veritabanı (asyncpg) üzerine kurulmuştur.

## Özellikler
1. `POST /api/data/analyze-and-infer`: Gelen CSV'yi okur, veri tiplerini tespit eder, PII/semantik alanları bulur ve otomatik senaryo kurallarını (Rule Inference) döndürür.
2. `POST /api/data/generate`: Kural motoruna göre satır satır sahte veri basar (`pandas`/`faker` tabanlıdır).
3. **Müşteri (Customer), Hesap (Account) ve İşlem (Transaction)** SQLAlchemy modelleri hazırdır.

## Nasıl Çalıştırılır?

### 1. PostgreSQL Veritabanını Başlatın
Eğer bilgisayarınızda Docker yüklü ise:
```bash
docker compose up -d
```
Eğer Docker yoksa, bilgisayarınıza PostgreSQL kurarak `.env` dosyasındaki `DATABASE_URL` değerini kendi veritabanınıza göre güncelleyin.

### 2. Python Ortamını Kurun
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. API'yi Başlatın
```bash
uvicorn app.main:app --reload --port 8000
```

Tarayıcınızdan `http://localhost:8000/docs` adresine giderek Endpoint'leri Swagger UI üzerinden denerbilir, veritabanı bağlantısının başarılı bir şekilde kurulduğunu test edebilirsiniz.
