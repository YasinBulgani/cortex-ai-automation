# ADR-0004: Legacy silme politikası (6 ay saklama)

**Durum:** Kabul edildi
**Tarih:** 2026-04-19
**Karar verenler:** @yasin_bulgan

## Bağlam

Eski modülleri (deneyler, v2/v3 sürümleri, kullanılmayan projeler) silmek gerekiyor ama:

- **Silmek yerine arşivle**: Gerektiğinde geri almak istiyoruz
- **Sonsuza kadar tutmak pahalı**: Git clone şişer, aktif kod ile tarihsel kod karışır
- **Karar yüküne son**: "Silelim mi, tutalım mı?" yerine otomatik kural

README'de "Silinmeye Aday Modüller" tablosu 12 ay önce eklenmişti. Kimse silmedi çünkü net tetikleyici yoktu.

## Karar

**Üç aşamalı saklama politikası:**

### Aşama 1: Aktif (yaşayan kod)
- `backend/`, `engine/`, `apps/web/`, `synthetic-data/platform-v4/`, vs.
- CI'dan geçer, testleri vardır, deploy'lanır.

### Aşama 2: Legacy (arşiv, okuma modu)
- `legacy/<YYYY-MM>-<kampanya>/<modül>/`
- **6 ay** tutulur
- CI koruması: PR legacy/ altına yazamaz (read-only)
- Geri almak isteyen `git mv` ile aktif'e taşır, ADR yazar

### Aşama 3: Silinmiş (sadece git history'de)
- 6 ay sonra `git rm -rf legacy/<YYYY-MM>-*`
- Geri almak için `git log --all` + `git checkout <commit> -- <path>`

## Kampanya yapısı

Her arşiv kampanyası kendi tarihli alt-dizinine gider:

```
legacy/
├── README.md                    # Genel politika
├── 2026-04-cleanup/             # Bu kampanya
│   ├── ai-engine/
│   ├── MaviYakaTestOtomasyon/
│   ├── ...
└── 2026-10-cleanup/             # Gelecek kampanyalar
```

## Arşivleme kriterleri

Bir modül `legacy/`'ye girer eğer şunların hepsi doğruysa:

1. `rg -l "<modül_yolu>" --glob '!legacy/**' --glob '!docs/history/**'` → boş veya sadece README/reports
2. `docker-compose*.yml` içinde servis olarak tanımlı değil
3. `Makefile`, `package.json`, `pyproject.toml`, `.github/workflows/` içinde build/test hedefi yok
4. Son 90 gün içinde commit yok (veya yalnızca otomatik commit)

## Geri alma prosedürü

```bash
# 1. Yeni branch aç
git checkout -b restore/<modül-adı>

# 2. Modülü geri taşı
git mv legacy/2026-04-cleanup/<modül> <orijinal-yol>

# 3. Neden geri alındığını ADR'a yaz
echo "..." > docs/adr/NNNN-restore-<modül>.md

# 4. PR aç, review iste
```

## Silme prosedürü (6 ay sonra)

```bash
# Örnek: 2026-10-19'da 2026-04-cleanup'ı sil
git checkout main
git pull
git checkout -b chore/purge-2026-04-legacy
git rm -rf legacy/2026-04-cleanup/
git commit -m "chore: purge 2026-04 legacy archive (6 month retention expired)"
git push -u origin chore/purge-2026-04-legacy
# PR aç, 1 onay al, merge et
```

## Alternatifler

### A. Direkt sil, git history yeterli
**Red sebebi:** `git log --all --diff-filter=D` zorlaştırıcı — yeni gelen developer "eskiden bir modül vardı ama sildim" bilgisine ulaşamaz. Arşiv, keşfedilebilir bir üst katman.

### B. Ayrı archive repo'ya taşı
**Red sebebi:** İki repo yönetim maliyeti. Yalnızca 6 ay için tutulan şey için abartı.

### C. Git LFS / submodule
**Red sebebi:** Bunlar canlı veri için uygun. Ölü kod için değil.

## Sonuçlar

### Olumlu
- "Silelim mi?" yerine net tetikleyici (tarih)
- Geri alınabilirlik — 6 ay yeterli emniyet marjı
- Aktif kod ile tarihsel kod birbirine karışmaz
- Yeni developer `legacy/README.md`'yi okuyunca tarihçeyi anlar

### Olumsuz / takas
- 6 ay × 1 yıl 2 kampanya × ~300 MB = 600 MB şişkinlik (geçici)
- Disiplin gerekli: silme takvimine takvimde yer açmak lazım
- `legacy/` içinden kimse bir şey çalıştırmamalı → CI guard gerekli

### Takip işleri
- [x] `legacy/` dizin yapısı + README (2026-04-19)
- [x] 2026-04-cleanup kampanyası (9 modül arşivlendi)
- [ ] CI guard: `legacy/` altında yapılan değişiklik PR'ı reddeder
- [ ] Takvim hatırlatıcısı: 2026-10-19'da 2026-04-cleanup'ı sil
- [ ] Bir sonraki temizlik kampanyası: 2026-10 civarı

## İlgili

- [legacy/README.md](../../legacy/README.md)
- [ADR-0003](0003-synthetic-data-konsolidasyonu.md)
