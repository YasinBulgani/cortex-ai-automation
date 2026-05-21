# language: tr
@scenarios @regression
Özellik: Senaryo Yonetimi
  Kullanicilar test senaryolari olusturabilir ve yonetebilir.

  Arka plan:
    Diyelim ki kullanici sisteme giris yapmistir
    Ve aktif bir proje secilmistir

  Senaryo: Yeni senaryo olusturma
    Diyelim ki kullanici senaryolar sayfasindadir
    Ve yeni senaryo butonuna tiklar
    Ve senaryo basligini "Login Testi" olarak girer
    Ozaman kaydet butonuna tiklar
    Ve senaryo basariyla olusturulur

  Senaryo: Senaryo arama
    Diyelim ki kullanici senaryolar sayfasindadir
    Ve arama kutusuna "Login" yazar
    Ozaman filtrelenmis senaryo listesi goruntulenir

  Senaryo: Senaryo silme
    Diyelim ki kullanici senaryolar sayfasindadir
    Ve mevcut bir senaryo secilmistir
    Ozaman sil butonuna tiklar
    Ve silme onay dialogu goruntulenir
