## Aday Değerlendirme - Oturum Kayıt Yapısı

Bu proje, bir aday ile görüşmeye başladığınızda **oturum klasörü** oluşturup (varsa) **mikrofondan ses kaydı** alacak şekilde tasarlanmıştır.

### Gereksinimler

- **Java**: JDK 17+ (makinende zaten var görünüyor)
- **ffmpeg (opsiyonel ama önerilir)**: Ses kaydı için kullanılır
- **LLM (opsiyonel)**: Oturum sonrası notları özetlemek için OpenAI uyumlu bir API (ör. OpenAI)

macOS’ta kurulum (Homebrew ile):

```bash
brew install ffmpeg
```

> `ffmpeg` kurulu değilse uygulama oturumu açar ama kayıt başlatamaz; ekrana kurulum mesajı yazar.

LLM için (OpenAI örneği):

```bash
export OPENAI_API_KEY="senin-api-anahtarın"
# opsiyonel:
export OPENAI_MODEL="gpt-4.1-mini"
export OPENAI_BASE_URL="https://api.openai.com/v1/chat/completions"
```

### Kullanım

Proje kökünde:

```bash
cd "/Users/yasin_bulgan/IdeaProjects/Aday Degerlendirme"
```

Oturum başlat:

```bash
java -cp src Main start "Ada Lovelace"
```

- Oturum klasörü `data/` altında oluşur.
- Kayıt başladıysa, Enter’a basınca durur ve dosyalar klasörde kalır.
- Görüşme bitince, eğer `OPENAI_API_KEY` tanımlıysa, LLM’den kısa bir değerlendirme özeti alınır ve
  - ekrana yazılır,
  - oturum klasöründe `llm_summary.md` ve `llm_raw_response.json` dosyalarına kaydedilir.

### Oluşan yapı (örnek)

- `data/2026-01-20_14-32-10_ada-lovelace/`
  - `session.json`
  - `notes.md`
  - `audio/`
    - `mic.wav` (ffmpeg varsa)

