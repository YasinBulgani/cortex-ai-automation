# BGTS Open-Source AI Stack

Bu kurulum BGTS için kontrollü bir açık kaynak AI katmanı sağlar:

- Native `ollama` yerel model sunucusu
- `ai-gateway` üzerinden merkezi model erişimi
- Backend içinde sürekli çalışan `ops agent`
- `open-webui` ile yerel gözlem ve sohbet arayüzü

## Ne Kuruldu

- Backend içine periyodik sağlık kontrolü yapan `ops agent` eklendi.
- Agent, backend/engine/ai-gateway durumunu toplayıp AI özeti üretir.
- Son raporu markdown olarak disk üstüne yazar.
- Ayrı bir compose override ile `open-webui` servisi tanımlandı.

## Yerel Ön Koşul

Bu makinede native `ollama` zaten kurulu. Kontrol:

```bash
ollama --version
ollama list
curl http://127.0.0.1:11434/api/tags
```

Önerilen varsayılan model:

```bash
ollama pull llama3.1:8b
```

## Stack'i Başlatma

Klasik compose dosyasına AI override eklenir:

```bash
docker-compose -f docker-compose.yml -f docker-compose.ai.yml up -d ai-gateway backend open-webui
```

Repo içinden önerilen yol artık doğrudan başlangıç scriptidir:

```bash
./start-all.sh
./start-all.sh --ai-ui
make nexusqa-up
make nexusqa-up-ui
```

Varsayılan davranış:

- `./start-all.sh` AI stack'i dahil eder
- native `ollama` erişilebilir değilse otomatik açmayı dener
- `BGTS_OLLAMA_WARM_MODELS` içindeki modelleri `keep_alive=-1` ile sıcak tutar
- `open-webui` yalnızca `--ai-ui` veya `make nexusqa-up-ui` ile başlar

Open WebUI:

- URL: `http://localhost:3001`
- Ollama bağlantısı: `http://host.docker.internal:11434`

## Ops Agent

Backend ortam değişkenleri:

```bash
AI_BACKGROUND_ENABLED=true
AI_BACKGROUND_INTERVAL_SECONDS=900
AI_BACKGROUND_START_DELAY_SECONDS=60
AI_BACKGROUND_TARGETS=backend=http://backend:8000/health,engine=http://engine:5001/health,ai_gateway=http://ai-gateway:8080/ai/health
AI_BACKGROUND_REPORT_PATH=/app/data/ai-ops/latest.md
```

Endpoint'ler:

- `GET /api/v1/agents/ops/status`
- `POST /api/v1/agents/ops/run`
- `POST /api/v1/agents/ops/start`
- `POST /api/v1/agents/ops/stop`
- `GET /api/v1/agents/ops/report`

## Kapsam

İlk faz ajanı şunları yapar:

- Servis sağlık kontrolü
- AI özet raporu
- Periyodik izleme

Bilerek yapmaz:

- Kod yazıp merge etmek
- Testleri kendi kendine üretim ortamında koşturmak
- Deploy/migration tetiklemek

Bu sınır, sistemi güvenli biçimde devreye almak için seçildi.
