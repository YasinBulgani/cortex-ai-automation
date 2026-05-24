# language: tr
@import @regression
Özellik: Ice Aktarma
  Dis kaynaklardan test senaryolari ice aktarilir.

  Arka plan:
    Diyelim ki kullanici sisteme giris yapmistir
    Ve aktif bir proje secilmistir

  @TC-IMP-002
  Senaryo: Ice aktarma sayfasi acilir
    Diyelim ki kullanici ice aktarma sayfasindadir
    Ozaman ice aktarma formu goruntulenir

  @critical @TC-IMP-001
  Senaryo: Dosya yukleyerek ice aktarma
    Diyelim ki kullanici ice aktarma sayfasindadir
    Ve bir test dosyasi secer
    Ozaman yukle butonuna tiklar
    Ve ice aktarma basariyla tamamlanir

  @TC-IMP-003
  Senaryo: Gecersiz dosya ile ice aktarma
    Diyelim ki kullanici ice aktarma sayfasindadir
    Ve gecersiz bir dosya secer
    Ozaman yukle butonuna tiklar
    Ve hata mesaji goruntulenir
