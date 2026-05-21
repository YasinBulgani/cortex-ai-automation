# language: tr
@auth @smoke
Özellik: Kullanici Girisi
  Kullanicilar email ve sifre ile sisteme giris yapabilmelidir.

  Senaryo: Basarili giris
    Diyelim ki kullanici giris sayfasindadir
    Ve "admin@example.com" emailini girer
    Ve "admin123" sifresini girer
    Ozaman giris butonuna tiklar
    Ve kullanici projeler sayfasina yonlendirilir

  Senaryo: Hatali sifre ile giris
    Diyelim ki kullanici giris sayfasindadir
    Ve "admin@example.com" emailini girer
    Ve "yanlis_sifre" sifresini girer
    Ozaman giris butonuna tiklar
    Ve hata mesaji goruntulenir

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
