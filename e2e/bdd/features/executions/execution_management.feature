# language: tr
@executions @regression
Özellik: Test Kosulari Yonetimi
  Senaryolar test kosularina eklenir ve calistirilir.

  Arka plan:
    Diyelim ki kullanici sisteme giris yapmistir
    Ve aktif bir proje secilmistir

  @critical
  Senaryo: Kosu listesi goruntulenir
    Diyelim ki kullanici kosular sayfasindadir
    Ozaman kosu listesi goruntulenir

  @critical @TC-EXC-001
  Senaryo: Yeni kosu olusturma
    Diyelim ki kullanici kosular sayfasindadir
    Ve yeni kosu butonuna tiklar
    Ve kosu adini "Sprint-1 Kosusu" olarak girer
    Ozaman kosu baslat butonuna tiklar
    Ve kosu basariyla olusturulur

  Senaryo: Kosu detayi goruntulenir
    Diyelim ki kullanici kosular sayfasindadir
    Ve mevcut bir kosu secilmistir
    Ozaman kosu detay sayfasi goruntulenir
