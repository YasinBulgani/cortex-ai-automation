# Akis Bazli Kullanim Tasarimi

Bu dokuman, urunun tum yeteneklerini koruyup kullanim karmaasasini azaltmak icin onerilen yeni bilgi mimarisini tanimlar.

## Hedef

- Kullanici modul secmek yerine is akisini takip etsin.
- Tum ozellikler ulasilabilir kalsin ama ilk bakista karar yuku azaltilsin.
- Demo, onboarding ve gunluk kullanim ayni zihinsel model ile calissin.

## Yeni Ana Navigasyon

1. `Kesfet`
   - `Ice Aktar`
   - `Gereksinimler`
   - `Kapsam`
   - `Analiz`

2. `Tasarla`
   - `Senaryolar`
   - `AI Test Case`
   - `Onaylar`
   - `Is Akislari`

3. `Veri`
   - `Sentetik Veri`
   - `Test Verileri`

4. `Uret`
   - `Dokumandan Otomasyon`
   - `AI Otomasyon Uret`
   - `Manuel Testler`
   - `Otomasyonlar`
   - `Page Objects`
   - `Locator'lar`
   - `Kaydedici`
   - `Akislar`

5. `Calistir`
   - `API Testleri`
   - `Kosular`
   - `Kosu Gecmisi`
   - `Regresyon`
   - `Zamanlayici`
   - `CI/CD`
   - `Entegrasyonlar`

6. `Gozlemle`
   - `Raporlar`
   - `Analitik`
   - `AI Debug Rapor`
   - `Flaky Testler`
   - `Gorsel Regresyon`
   - `Erisilebilirlik`
   - `Monkey Test`

7. `Advanced`
   - `AI Asistan`
   - `Akis Sihirbazi`
   - `Ayarlar`

## Proje Giris Sayfasi

Proje ana sayfasi klasik dashboard olmaktan cikarak bir `Akis Merkezi` haline gelmelidir.

Her proje ana sayfasi:

- mevcut durum ozeti gostermeli
- onerilen bir sonraki adimi one cikarmali
- 6 akis kolonunu tek bakista gostererek kullaniciyi dogru sayfaya goturmeli

## Tasarim Ilkeleri

- Sol menude ilk seviyede en fazla 6 ana baslik gorunsun.
- Ayrik ama benzer isler ayni akis altinda toplansin.
- AI ayri bir modul degil, butun akislarin yardimci katmani gibi hissedilsin.
- Kullanici her ekranda "sonraki mantikli adim" baglantisi gorsun.

## Uygulama Sirasi

1. Sidebar'i akis bazli hale getir.
2. Proje ana sayfasini `Akis Merkezi`ne cevir.
3. Her akis sayfasina bir sonraki adim kutusu ekle.
4. `AI Asistan`i sag panel / yardimci cekmece modeline indir.
