# Quick Start — Pipeline + HuggingFace + Canlı Dashboard

3 adımda: **kur → token al → dashboard'u aç → pipeline'ı başlat**.

---

## 1. Python deps (tek seferlik)

```bash
make pipeline-deps-install
# veya:
pip3 install -r scripts/pipeline/requirements.txt
```

**Yüklenenler:** `huggingface_hub`, `fastapi`, `uvicorn`, `pip-audit`

---

## 2. HuggingFace Token

1. https://huggingface.co/welcome → kayıt (ücretsiz)
2. https://huggingface.co/settings/tokens → **"Create new token"** → type: **Read** (fine-grained değil, legacy read yeterli)
3. Token'ı `.env`'e ekle:

```bash
echo 'HF_TOKEN=hf_xxxxxxxxxxxxxxxxxxxxxxxx' >> .env
# İsterseniz .env yerine shell:
export HF_TOKEN=hf_xxx
```

Opsiyonel: model tercihleri (default'lar yeterli, ama güçlü modeller bazen HF'de gated)
```bash
HF_DEFAULT_MODEL=mistralai/Mistral-7B-Instruct-v0.3     # varsayılan
HF_FAST_MODEL=Qwen/Qwen2.5-7B-Instruct
HF_POWERFUL_MODEL=meta-llama/Meta-Llama-3-70B-Instruct  # gated, erişim iste
HF_CODER_MODEL=Qwen/Qwen2.5-Coder-7B-Instruct
```

### Doğrula

```bash
make pipeline-hf-ping
```

Beklenen çıktı:
```json
{
  "token_set": true,
  "default_model": "mistralai/Mistral-7B-Instruct-v0.3",
  "reachable": true,
  "sample": "pong"
}
```

---

## 3. Canlı Dashboard başlat

```bash
make pipeline-dashboard
# → 🚀 Dashboard → http://127.0.0.1:8765
```

Tarayıcıda aç. Göreceğin şey:

- **Üst şerit:** HF status (yeşil=OK), SSE (live), Run status
- **Sol panel:** Item listesi (tıklayınca detay) + paralel koşum kontrolleri (Mode / Concurrent / Filter)
- **Orta panel:** Pipeline graph (seçili item'ın aşamaları renklenir: done=yeşil, waiting=sarı, in_progress=mavi, skipped=gri)
- **Sağ panel:** Canlı log stream (SSE) + Metrics (bottleneck) + Waiting heatmap

Auto-reload mode için geliştirirken:
```bash
make pipeline-dashboard-dev
```

---

## 4. Item oluştur → paralel koşumu başlat

### Opsiyon A — Dashboard üzerinden (önerilen)

1. Terminal'de bir item aç:
   ```bash
   make pipeline-init TYPE=GAP TITLE="Login sayfası responsive sorunu" \
     SCOPE="fe=true,be=false,data=false,infra=false,perf_sensitive=false"
   ```

2. Dashboard'da sol panelde **GAP-001** gözükecek. Tıkla → detay açılır.

3. Sol altta **Paralel koşumu başlat**:
   - Mode: `once` (bir tur) veya `watch` (daemon)
   - Concurrent: 3 (HF rate-limit için 3-4 güvenli)
   - **▶ Başlat** tıkla

4. Sağ panelde canlı log akışını izle:
   ```
   ━━━ Run started (mode=once, concurrent=3)
   ── Round 1 — 1 waiting
   ▶ GAP-001 · analyzer başladı
   ✓ GAP-001 · analyzer done (Qwen2.5-7B-Instruct 14.3s)
   ▶ GAP-001 · validator başladı
   ✓ GAP-001 · validator done decision=approve
   ...
   ```

5. Graph'ta aşama renkleri canlı güncelleniyor.

### Opsiyon B — Komut satırından

```bash
# Tek rol manuel
make pipeline-agent-run ID=GAP-001 ROLE=analyzer

# Tek item'ı full pipeline koş
make pipeline-run-single ID=GAP-001

# Tüm waiting'ler, tek tur
make pipeline-run-once CONCURRENT=3

# Daemon, idle olunca çık
make pipeline-run-watch CONCURRENT=3
```

---

## 5. Tipik akış

```
Dashboard açık ← arkada pipeline koşuyor ← HF LLM her rolü yazıyor ← artifacts commit ediliyor
```

1. `make pipeline-init ...` ile item aç
2. Dashboard'da gör
3. "Başlat" → pipeline başlar
4. Her rol HF modelinden yanıt aldıkça artifact dosyası `docs/ai/pipeline/items/<ID>/*.md` olarak yazılır
5. Decision rolleri (validator, approver, vb.) JSON karar döndürür, state.json otomatik güncellenir
6. Dep graph sayesinde paralel aşamalar eş zamanlı açılır
7. Scope flag'leri ile gereksiz aşamalar auto-skip
8. Sorunlu aşama yakalanırsa (confidence<0.7 veya reject) → `needs_human: true`, dashboard'da ⚠

---

## 6. Rol → Model tier mapping

| Tier | Model (default) | Roller |
|---|---|---|
| `fast` | Qwen2.5-7B-Instruct | analyzer, validator, intake_triage, dep_watchdog, release_manager, observer |
| `balanced` | Mistral-7B-Instruct-v0.3 | proposer, approver, product_validator, designer, code_reviewer, retrospective |
| `powerful` | Llama-3-70B-Instruct (gated) | architect, security_reviewer, qa, integrator, promoter |
| `coder` | Qwen2.5-Coder-7B-Instruct | frontend, backend, data_engineer, devops |

Gated modeller için HF'de erişim izni iste (model sayfasında "Request access"). Erişim yoksa `HF_POWERFUL_MODEL=mistralai/Mixtral-8x7B-Instruct-v0.1` gibi alternatif set edebilirsin.

---

## 7. Troubleshooting

### `HF_TOKEN not set`
→ `.env` dosyasına `HF_TOKEN=hf_...` ekle, shell'i yeniden aç veya `source .env && export HF_TOKEN`

### `401 Unauthorized` veya `402 Payment Required`
→ Ücretsiz tier limiti dolmuş olabilir. 1-2 saat bekle veya daha küçük model kullan:
```bash
HF_DEFAULT_MODEL=HuggingFaceH4/zephyr-7b-beta make pipeline-run-once
```

### `Model ... not available on provider`
→ Model HF Serverless'ta erişilebilir değil. Alternatif:
- https://huggingface.co/models?inference=warm → erişilebilir modelleri filtrele
- Set `HF_DEFAULT_MODEL`'e çalışan bir model slug

### Agent çok uzun konuşuyor (token limit aşımı)
→ `RUN_FLAGS` ile token azalt:
```bash
make pipeline-run-once RUN_FLAGS="--max-tokens 1500"
```

### Dashboard SSE bağlantısı kopuyor
→ Normal; `dashboard.js` otomatik 3 sn'de reconnect olur. SSE chip kırmızıysa server'ı yeniden başlat.

### "Pipeline takıldı" / agent crash
→ `make pipeline-status` ile durumu gör. Takılan stage için:
```bash
./scripts/pipeline/stage.sh orphan-reset <ID> <ROLE>
```

---

## 8. Güvenlik notları

- **Token'ı commit etme** — `.env` `.gitignore`'da olmalı (kontrolü unutma)
- Dashboard sadece `127.0.0.1` dinler (default) — LAN'a açmak için `HOST=0.0.0.0 make pipeline-dashboard`
- Agent LLM çıktıları repo'ya yazılır — insan review'u hala kıymetli
- Kritik rollere (security_reviewer, promoter) **düşük confidence** gelirse `needs_human: true` olur → insan devreye girer

---

## 9. Dosya haritası (yeni eklenenler)

```
scripts/pipeline/
  ├── llm/
  │   ├── __init__.py
  │   ├── hf_client.py          # HF InferenceClient wrapper
  │   └── prompts.py            # Rol kartı → LLM prompt
  ├── agent_runner.py           # Tek rol koşturucu
  ├── run_pipeline.py           # Paralel executor (once|watch|single)
  ├── dashboard/
  │   ├── server.py             # FastAPI + SSE
  │   └── static/
  │       ├── index.html
  │       ├── style.css
  │       └── dashboard.js
  └── requirements.txt

engine/core/ai_client.py        # Güncellendi: LLM_PROVIDER=huggingface default
engine/config/settings.py       # Güncellendi: HF_TOKEN, HF_*_MODEL
```

---

## 10. Sonraki adımlar

- Gerçek item üzerinde canlı koş (bir `GAP` aç, dashboard aç, başlat)
- Retro sonrası GROUNDING güncellemesi → `knowledge_curator` rol kartını oku
- Kendi rol kartlarını özelleştir: `docs/ai/pipeline/roles/*.md`
- Model tercihlerini `docs/ai/pipeline/stages.json`'da rol bazlı değiştir

**Takılırsa:** `docs/ai/pipeline/README.md` (ana rehber) + `.cursor/rules/pipeline-conductor.mdc` (orkestrasyon protokolü)
