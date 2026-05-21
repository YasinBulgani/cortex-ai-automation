# Visium 10/10 UX Refactor Plani

Bu planin amaci yeni ozellik eklemek degil, urunu daha az karar yoran ve daha hizli ilerleten hale getirmektir.

## Kuzey Yildizi

Her ekranda kullanici 3 saniye icinde su uc seyi anlamalidir:

- Hangi urun lensindeyim?
- Bu ekranin ana amaci ne?
- Bir sonraki dogru adim ne?

## Temel Ilkeler

- `Urun` birinci katman olsun.
- `Akis` ikinci katman olsun.
- `Persona` yalnizca yardimci filtre olarak kalsin.
- `Advanced` gunluk kullanicinin ilk gorunumunden uzak tutulsun.
- Her ekranda tek ana CTA baskin olsun.
- Kart yogunlugu azaltilsin; ayni anda karar verdiren 3-4 bloktan fazlasi gorunmesin.

## Hedef Bilgi Mimarisı

1. `Visium Home`
   - once urun secimi
   - sonra proje veya yeni kurulum

2. `Akis Merkezi`
   - secili urun
   - onerilen sonraki adim
   - 3 temel KPI
   - sadece ilgili akis kartlari

3. `Akis Ekranlari`
   - tek is
   - kisa baglam
   - sonraki adim baglantisi

4. `Advanced`
   - uzman araclari
   - deneysel alanlar
   - operasyonel detaylar

## Ekran Bazli Refactor Sirasi

### Faz 1

- Proje dashboard'ini sadeleştir.
- Secili urunu dashboard'un birincil baglami yap.
- Tam urun ailesi grid'ini kompakt urun lensine indir.
- KPI kartlarini 3 adede dusur.
- Akis kartlarini secili urun ve persona odagina gore sinirla.

### Faz 2

- `new-project` wizard'ini daha agresif kosullu hale getir.
- Secilen urunde gereksiz step'leri gorunmez yap.
- Web olmayan urunlerde web otomasyon dilini ikinci plana al.
- Data ve Service tarafinda alan-spesifik rehber metinlerini guclendir.

### Faz 3

- Ana akis ekranlarini tek amaç prensibiyle rafine et.
- `import`, `scenarios`, `test-data`, `automation-gen`, `executions`, `reports`
- Her sayfada ayni yapisal header dili kullan.
- Saglam bos durumlar ve tek ana CTA ekle.

### Faz 4

- `Advanced` ve yan araclari yeniden paketle.
- Kaydedici, locator, page object, healing, monkey, visual gibi alanlari uzman paketine cek.
- Varsayilan sidebarda sadece sik kullanilan yollar kalsin.

## Kaldirilacak veya Birlesecek Yuzeyler

- Ayni anda hem tam urun ailesi grid'i hem tam persona paneli gosterilmemeli.
- Dashboard'ta ozet, urunler, akislar, istatistikler ve hizli aksiyonlar esit agirlikta olmamali.
- Kullaniciya ait olmayan uzman araclari ilk seviyede gorunmemeli.

## Basari Olcutleri

- Yeni kullanici ilk 2 dakikada dogru akis adimina ulasabiliyor.
- Demo sirasinda anlatim moduller uzerinden degil akis uzerinden yapiliyor.
- Dashboard'tan sonraki tiklama sayisi azaliyor.
- Ekipler farkli urun lenslerine gecse bile ayni cekirdek zihinsel modeli koruyor.

## Uygulama Disiplini

- Her refactor adiminda once yogunluk azaltilsin, sonra yeni detay geri eklensin.
- Yeni kart eklemek yerine mevcut kart birlestirme tercih edilsin.
- Her ekranda en baskin tek CTA sorgulansin.
