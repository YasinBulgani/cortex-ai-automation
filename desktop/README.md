# TestwrightAI — Masaüstü Uygulaması (Demo)

Mevcut web tabanlı TestwrightAI platformunun **demo amaçlı masaüstü sürümü**.
Electron ile sarılmış ince bir kabuk olup, arka planda `docker compose` ile
tüm servisleri (PostgreSQL, Redis, Backend API, Engine, Frontend) ayağa
kaldırır ve Next.js arayüzünü native bir pencerede sunar.

> **Kapsam:** Bu bir demo POC'dir. Tek makinede, tek kullanıcı için tüm
> modülleri (TSPM, AI, Sentetik Veri) tek pakette sunar. Çoklu kullanıcı,
> merkezi denetim ve ekip senaryoları için ana web dağıtımını kullanın.

---

## Ön Koşullar

| Araç | Versiyon | Not |
|------|----------|-----|
| **Docker Desktop** | 4.0+ | Zorunlu — tüm servisler container olarak koşar |
| **Node.js** | 18+ | Electron + electron-builder için |
| **macOS / Windows / Linux** | — | İlk hedef: macOS (.dmg) |

---

## Mimari

```
┌──────────── TestwrightAI Desktop ────────────┐
│  Electron Shell (native pencere)             │
│   ├─ Splash screen (servis durumu)           │
│   └─ Main window → http://localhost:3000     │
├──────────────────────────────────────────────┤
│  Docker Compose (otomatik orkestrasyon)      │
│   ├─ postgres:5432                           │
│   ├─ redis:6379                              │
│   ├─ backend (FastAPI) :8000                 │
│   ├─ engine (Flask)   :5001                  │
│   └─ web (Next.js)    :3000                  │
└──────────────────────────────────────────────┘
```

**Başlatma akışı:**

1. Uygulama açılır → splash penceresi gösterilir
2. `docker compose up -d` tetiklenir, log canlı akar
3. Backend / Engine / Frontend health check'leri tamamlanır
4. Ana pencere açılır, splash kapanır
5. Uygulamadan çıkınca `docker compose down` otomatik çalışır

---

## Geliştirme

```bash
cd desktop
npm install
npm run dev
```

Varsayılan olarak `http://localhost:3000` yüklenir. Farklı bir frontend URL'si
kullanmak isterseniz:

```bash
TWAI_FRONTEND_URL=http://localhost:3001 npm run dev
```

### Sadece UI'ı test etmek (Docker olmadan)

Docker kontrolünü geçici atlamak için önce `apps/web`'de `npm run dev` koşun,
ardından masaüstü uygulamasını başlatın — splash yine health-check bekler,
fakat backend/engine olmayacağı için hata gösterilir. Demo akışının tamamını
görmek için Docker Desktop'ı açık tutun.

---

## Paketleme (Distribusion)

### macOS (.dmg)

```bash
cd desktop
npm run build:mac
# Çıktı: desktop/dist/TestwrightAI-0.1.0-arm64.dmg
#        desktop/dist/TestwrightAI-0.1.0-x64.dmg
```

### Windows (.exe)

```bash
npm run build:win
```

### Linux (AppImage)

```bash
npm run build:linux
```

`docker-compose.yml` otomatik olarak `extraResources` üzerinden pakete dahil
edilir; son kullanıcı sadece `.dmg`'yi yükler, içinden Docker'ı çalıştırır.

---

## Dizin Yapısı

```
desktop/
├── src/
│   ├── main.js        # Electron main process (orkestrasyon)
│   ├── preload.js     # contextBridge API (splash ↔ main)
│   └── splash.html    # Başlangıç ekranı (servis durumu + log)
├── assets/
│   ├── icon.png       # 1024x1024 kare ikon
│   ├── icon.icns      # macOS ikonu
│   └── icon-512.png   # Fallback
├── build/             # electron-builder kaynak klasörü
├── package.json
└── README.md
```

---

## Sınırlamalar

- **Docker zorunlu**: Demo kapsamı tek makinede tam sistem. Docker yoksa
  splash ekranda net hata mesajı ile Docker Desktop indirme linki sunulur.
- **İlk açılış yavaş**: İlk başlatmada imaj indirme ve DB migration'ları
  nedeniyle ~3-5 dakika sürebilir. Sonraki açılışlar ~20 saniyede tamamlanır.
- **API anahtarları**: `OPENAI_API_KEY` vb. demo makinesinde `.env` üzerinden
  okunur. Production dağıtımda asla bu modelle yapılmamalıdır.
- **Port çakışması**: 3000 / 8000 / 5001 / 5432 / 6379 portları boş olmalıdır.
