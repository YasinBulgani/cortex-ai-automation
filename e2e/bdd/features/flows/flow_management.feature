# language: tr
@flows @regression
Özellik: Akis Editoru
  Akis diyagramlari olusturulur ve React Flow editoru ile duzenlenir.

  Arka plan:
    Diyelim ki kullanici sisteme giris yapmistir
    Ve aktif bir proje secilmistir

  Senaryo: Akis listesi goruntulenir
    Diyelim ki kullanici akislar sayfasindadir
    Ozaman akis listesi goruntulenir

  @critical @TC-FLW-001
  Senaryo: Yeni akis olusturma
    Diyelim ki kullanici akislar sayfasindadir
    Ve yeni akis butonuna tiklar
    Ve akis adini "Login Akisi" olarak girer
    Ozaman akis olustur butonuna tiklar
    Ve akis basariyla olusturulur
