# language: tr
@approvals @regression
Özellik: Onay Kuyrugu
  AI tarafindan uretilen taslaklar onay kuyrugundan gecirilir.

  Arka plan:
    Diyelim ki kullanici sisteme giris yapmistir
    Ve aktif bir proje secilmistir

  Senaryo: Onay listesi goruntulenir
    Diyelim ki kullanici onaylar sayfasindadir
    Ozaman onay listesi goruntulenir

  @critical
  Senaryo: Onay kabul edilir
    Diyelim ki kullanici onaylar sayfasindadir
    Ve bekleyen bir onay secilmistir
    Ozaman onayla butonuna tiklar
    Ve onay basariyla kabul edilir

  Senaryo: Onay reddedilir
    Diyelim ki kullanici onaylar sayfasindadir
    Ve bekleyen bir onay secilmistir
    Ozaman reddet butonuna tiklar
    Ve onay basariyla reddedilir
