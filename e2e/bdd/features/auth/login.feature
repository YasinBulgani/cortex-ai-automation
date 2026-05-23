# language: tr
@auth @smoke
Özellik: Kullanici Girisi
  Kullanicilar email ve sifre ile sisteme giris yapabilmelidir.

  @TC-AUTH-001
  Senaryo: Basarili giris
    Diyelim ki kullanici giris sayfasindadir
    Ve "admin@example.com" emailini girer
    Ve "admin123" sifresini girer
    Ozaman giris butonuna tiklar
    Ve kullanici projeler sayfasina yonlendirilir

  @TC-AUTH-002
  Senaryo: Hatali sifre ile giris
    Diyelim ki kullanici giris sayfasindadir
    Ve "admin@example.com" emailini girer
    Ve "yanlis_sifre" sifresini girer
    Ozaman giris butonuna tiklar
    Ve hata mesaji goruntulenir

  @TC-AUTH-007
  Senaryo: Bos form gonderme
    Diyelim ki kullanici giris sayfasindadir
    Ozaman giris butonuna tiklar
    Ve hata mesaji goruntulenir

  Senaryo Taslagi: Farkli kullanici rolleri ile giris
    Diyelim ki kullanici giris sayfasindadir
    Ve "<email>" emailini girer
    Ve "<sifre>" sifresini girer
    Ozaman giris butonuna tiklar
    Ve kullanici projeler sayfasina yonlendirilir

    Ornekler:
      | email              | sifre    |
      | admin@example.com  | admin123 |
