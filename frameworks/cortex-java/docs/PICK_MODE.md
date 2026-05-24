# Pick Mode — Element Seçim Rehberi

Cortex Recorder, sayfadan bir elementi yakalayıp ona locator key + assertion / click / fill atamak için **tek bir resmi yola** sahiptir: **Dashboard'daki QuickAddPanel**.

## Resmi Yol: QuickAddPanel

Recorder çalışırken modal'ın sağ tarafında **"Hızlı Ekle"** ve **"Sayfa Elementleri"** tab'ları görünür.

### Sayfa Elementleri Tab'ı
- Aktif sayfada tespit edilen tüm tıklanabilir/yazılabilir elementlerin listesi
- Her elementin yanında:
  - 👆 Tıkla
  - 📝 Metin yaz
  - 👁 Görünür (assertion)
  - 📋 Metin içerir (assertion)
- Tıklama tek-aksiyon olarak feature'a eklenir

### Hızlı Ekle Tab'ı
- Bekleme adımları (1/2/5/10 saniye)
- Doğrulama: son tıklanan element için "Görünür" veya "Metin içerir"
- Navigasyon: Yenile, Geri
- Serbest: Yorum, Manuel Gherkin satırı

## Eski Yöntemler (Kullanma)

Aşağıdaki yöntemler **deprecated** edildi veya gönülsüz olarak deneysel:

### ❌ In-page Chromium Toolbar
Eski `recorder.js` Chromium içine "ELEMENT SEÇ" butonu enjekte ediyordu. Modern React/SPA siteler bu DOM'u silebildiği için **güvenilir değil**. Toolbar görünse bile her zaman çalışmıyor.

**Yaklaşım:** Bu UI'ı görsen bile **dashboard'daki QuickAddPanel'ı tercih et.**

### ❌ Playwright Codegen Inspector
Eğer "🤖 Playwright Codegen" backend'ini seçtiysen, Inspector penceresinde de Pick element seçeneği var. Bu kullanılabilir AMA dashboard QuickAddPanel'la **state senkronu yok** — kayıt sonunda Codegen JS çıktısı parse edilip Gherkin'e çevrilir.

**Yaklaşım:** Codegen kullanıyorsan Inspector'ı kullan, Custom Recorder kullanıyorsan QuickAddPanel'ı.

## Pick Edilen Elementin Locator'ı Nasıl Üretilir?

`LocatorBuilder.java` öncelik sırasıyla:
1. `data-testid` / `data-test-id` / `data-cy` / `data-qa`
2. `id` (CSS escape ile)
3. `name` attribute
4. `aria-label`
5. Visible text + role (button, link için)
6. `placeholder`
7. CSS path (en sona, fallback)
8. XPath (mutlak fallback)

Aynı element birden fazla yakalandığında **aynı locator key** kullanılır (`email`, `email`, `email` — `_2`, `_3` suffix yok artık, bu sezonda fixlendi).

## Sık Sorulan Sorular

**S: QuickAddPanel'da elementim görünmüyor?**
Y: Sayfa scan'i 800ms throttle edildi. "🔄 Yenile" butonuna bas veya bir aksiyon yap (click/scroll), tekrar tara.

**S: Aynı element için farklı locator alternatifleri görmek istiyorum.**
Y: `cortex lint` komutu çalıştır — LocatorLinter mevcut tüm alternatifleri raporlar.

**S: Pick ettiğim element gerçekten unique mi?**
Y: QuickAddPanel pick öncesi `locator-candidates` endpoint'ini çağırır — birden fazla eşleşme varsa uyarır.
