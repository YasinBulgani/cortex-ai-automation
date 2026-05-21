# Nexus AI Autopilot Operasyon Notu

Bu not Nexus AI'nin enterprise/self-hosted kurulumda sürekli çalışan AI operasyon katmanı olarak nasıl devreye alınacağını açıklar.

## Varsayılan Güvenlik Kararı

- Backend varsayılan LLM sağlayıcısı `ollama`dır.
- `AI_LOCAL_ONLY=true` varsayılandır.
- AI Gateway varsayılan sağlayıcısı `ollama`dır.
- AI Gateway local-only modda sadece `ollama` ve etkinse `vllm` sağlayıcılarını zincire alır.
- OpenAI/Anthropic/Groq/Gemini gibi dış sağlayıcılar, müşteri verisi dışarı gitmesin diye varsayılan olarak devre dışıdır.

Cloud sağlayıcılar yalnızca bilinçli bir istisna olarak `AI_LOCAL_ONLY=false` ile açılmalıdır.

## Sürekli Autopilot

Autopilot worker varsayılan kapalı başlar. Manuel endpoint ve UI her zaman kullanılabilir.

Arka planda sıfır insan müdahalesi için:

```bash
export NEXUS_AUTOPILOT_ENABLED=true
export NEXUS_AUTOPILOT_BACKGROUND_MODE=observe
export NEXUS_AUTOPILOT_INTERVAL_SECONDS=900
export NEXUS_AUTOPILOT_START_DELAY_SECONDS=15
export NEXUS_AUTOPILOT_APPLY_SAFE_ACTIONS=true
```

Worker aktif olduğunda periyodik olarak aktif projeleri tarar, risk çıkarır, öneri üretir ve güvenli aksiyonları tetikler.

Varsayılan background modu `observe`dur. Bu mod sürekli risk ve öneri üretir, ağır QA orkestrasyonunu otomatik başlatmaz. UI veya API üzerinden `assist` ve `autonomous` modları manuel tetiklenebilir.

## Yerel LLM Önerisi

Ollama için önerilen başlangıç modelleri:

```bash
ollama pull qwen2.5:32b
ollama pull mistral:latest
ollama pull qwen2.5-coder:7b
```

Backend:

```bash
export AI_PROVIDER=ollama
export AI_LOCAL_ONLY=true
export OLLAMA_BASE_URL=http://localhost:11434/v1
```

AI Gateway:

```bash
export AI_PROVIDER=ollama
export AI_LOCAL_ONLY=true
export OLLAMA_BASE_URL=http://host.docker.internal:11434/v1
```

## vLLM Opsiyonu

Daha güçlü self-hosted model için:

```bash
export AI_PROVIDER=vllm
export AI_LOCAL_ONLY=true
export VLLM_ENABLED=true
export VLLM_BASE_URL=http://localhost:8000/v1
export VLLM_MODEL=Qwen/Qwen2.5-72B-Instruct
```

## Veritabanı

Autopilot çalışma geçmişi için migration uygulanmalıdır:

```bash
alembic upgrade head
```

Oluşan ana tablo:

- `tspm_autopilot_runs`

## API

- `GET /api/v1/ai/autopilot/status?project_id=...`
- `GET /api/v1/ai/autopilot/runs?project_id=...&limit=10`
- `POST /api/v1/ai/autopilot/run`

Manuel çalışma örneği:

```json
{
  "project_id": "PROJECT_ID",
  "mode": "autonomous",
  "apply_safe_actions": true,
  "trigger": "manual"
}
```

## Modlar

- `observe`: Sadece izler, risk ve öneri üretir.
- `assist`: Güvenli plan çıkarır ve destek aksiyonlarını hazırlar.
- `autonomous`: Güvenli aksiyonları otomatik başlatır.

İlk sürümde otomatik uygulama kapsamı kontrollüdür: QA planlama, güvenli QA döngüsü, bilgi hafızası güncelleme ve rota önerileri.

## Canlı Smoke ve CI

Lokal canlı doğrulama:

```bash
make nexusqa-smoke
```

Bu komut:

- Backend, Engine ve AI Gateway health kontrollerini doğrular.
- Demo kullanıcı ile login olup bir proje seçer.
- `observe` modunda Autopilot tetikler.
- Oluşan run kaydını `autopilot/runs` üzerinden doğrular.

CI tarafında aynı senaryo `ci.yml` içinde `nexusqa-runtime-smoke` job'ı ile çalışır.
