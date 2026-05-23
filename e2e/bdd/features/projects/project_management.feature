# language: tr
@projects @regression
Özellik: Proje Yonetimi
  Kullanicilar proje olusturabilir, goruntuleyebilir ve yonetebilir.

  Arka plan:
    Diyelim ki kullanici sisteme giris yapmistir

  @TC-PRJ-001
  Senaryo: Yeni proje olusturma
    Diyelim ki kullanici projeler sayfasindadir
    Ve yeni proje formunu acar
    Ve proje adini "Test Projesi" olarak girer
    Ve proje aciklamasini "Otomasyon test projesi" olarak girer
    Ozaman proje olustur butonuna tiklar
    Ve proje basariyla olusturulur

  @TC-PRJ-002
  Senaryo: Proje listesi goruntuleme
    Diyelim ki kullanici projeler sayfasindadir
    Ozaman proje listesi goruntulenir

  Senaryo: Bos proje adi ile olusturma
    Diyelim ki kullanici projeler sayfasindadir
    Ve yeni proje formunu acar
    Ve proje adini "" olarak girer
    Ozaman proje olustur butonuna tiklar
    Ve hata mesaji goruntulenir
