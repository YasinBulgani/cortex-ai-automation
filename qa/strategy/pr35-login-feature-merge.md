# PR 35 — engine/features/Otomasyonlar/login.feature Merge Analizi

**Durum:** Plan onayı bekliyor (engineering team sahipliği).
**Karar:** Sil veya kanonik kabul et — aşağıdaki analiz.

## İki dosya karşılaştırması

| Özellik | `engine/Otomasyonlar/login.feature` | `e2e/bdd/features/auth/login.feature` |
|---|---|---|
| Satır sayısı | 42 | 37 |
| Dil directive | yok (EN) | `# language: tr` |
| Gherkin keyword | Feature / Background / Scenario | Özellik / Arka plan / Senaryo |
| Step pattern | `When kullanici "EpostaInput" alanina ... yazar` (locator-based) | `Ve "admin@example.com" emailini girer` (semantic) |
| Locator strategy | Locator key referansları (`EpostaInput`, `SifreInput`, `GirisYapButon`) | Semantic step definitions |
| Test data | Variable (`@username`, `@password`) | Hardcoded (`admin@example.com`) |
| Tag | `@ui @login @smoke @critical @positive` | `@auth @smoke @TC-AUTH-001` |
| Runner | engine pytest-bdd | Cucumber.mjs (Node) |
| QA TC link | yok | ✓ `@TC-AUTH-001`, `@TC-AUTH-002`, `@TC-AUTH-007` |
| Aktif kullanım | engine/steps/ Python defs | e2e/bdd/steps/ TS defs |

## Aynı iş, farklı yaklaşım

İki dosya da **aynı login akışını** test ediyor:
1. Başarılı giriş → projects sayfasına yönlendirme
2. Yanlış parola → hata mesajı
3. Boş form → validasyon

Ama **çok farklı yapıyla**:
- `engine/`: Locator-based DSL (`EpostaInput`, `SifreInput`) — selenium/playwright kompatible, ama selector value'lar başka bir yerde tanımlı
- `e2e/`: Semantic step defs ("emailini girer" / "sifresini girer") — Cucumber.mjs ile çalışan idiomatic BDD

## 3 seçenek

### Seçenek A — Engine'i sil (önerim)

`engine/features/Otomasyonlar/login.feature` silinir, kanonik kaynak `e2e/bdd/features/auth/login.feature` olur.

**Avantaj:**
- Tek source of truth
- Cucumber.mjs zaten kanonik (DEPRECATED.md'e göre)
- e2e/ tarafında @TC-* tag'leri zaten var
- Engine step defs (40 dosya) kısmı tamamen migrate edilince engine/features/ tamamen silinecek

**Engel:**
- `engine/steps/` `EpostaInput`, `SifreInput`, `GirisYapButon` locator key'leri kullanıyor — bunların başka feature'larda tanımı olabilir; silmek diğer engine testlerini etkilemez
- `engine/tests/` veya CI'da bu feature'a referans var mı kontrol edilmeli

**Ön kontrol:**
```bash
grep -r "Otomasyonlar/login" engine/ tests/
grep -r "EpostaInput\|SifreInput\|GirisYapButon" engine/steps/ engine/features/
```

### Seçenek B — Engine'i kanonik kabul et

`e2e/bdd/features/auth/login.feature` silinir, engine versiyonu kanonik olur.

**Avantaj:**
- Locator-based pattern daha test-otomasyon platformuna uygun (Cortex AI Automation kendisi locator yöneten ürün)

**Dezavantaj:**
- DEPRECATED.md tersine işlemiş olur
- Cucumber.mjs ekosistemini terk etmek
- @TC-* tag entegrasyonu kaybolur

**Önerilmiyor.**

### Seçenek C — Her ikisini de tut (katmanlı strateji)

`engine/` → "platform self-test" (kendi locator engine'ini test eder)
`e2e/` → "feature acceptance" (kullanıcı akışı doğru çalışıyor mu)

**Avantaj:**
- Her dosyanın farklı amacı net
- Çift kontrol katmanı

**Dezavantaj:**
- Maintenance maliyeti çift
- "Aynı bug iki yerde rapor" karışıklığı
- BDD best practice "single source of truth" prensibini ihlal eder

## Önerim: Seçenek A

Aşağıdaki sırayla:

1. **Ön kontrol** (10 dk):
   ```bash
   # Çalışan engine test mi referans veriyor?
   grep -rn "Otomasyonlar/login\|Otomasyonlar.login" engine/tests/ engine/conftest.py 2>/dev/null
   ```

2. **Eğer referans yoksa**: doğrudan sil
   ```bash
   git rm engine/features/Otomasyonlar/login.feature
   ```

3. **Eğer referans varsa**: önce o test'i e2e/bdd/'ye yönlendir, sonra sil

4. **CI'da** engine pytest yeşil olmalı

## Beklenen etki

- **Coverage**: değişmez (e2e/ versiyonu zaten qa/cases'e tag'li)
- **engine/features count**: 47 → 46 (-1)
- **Migration roadmap**: Aşama 1 (low-risk silme) kapsamına girer

## Sahip

- Ön kontrol: Engine team
- Silme PR'ı: QA + Engine team (çift review)
