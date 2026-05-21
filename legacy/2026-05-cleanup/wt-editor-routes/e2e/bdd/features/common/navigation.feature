# language: tr
@navigation @smoke
Özellik: Sayfa Navigasyonu
  Kullanicilar sidebar uzerinden tum sayfalara erisebilmelidir.

  Arka plan:
    Diyelim ki kullanici sisteme giris yapmistir
    Ve aktif bir proje secilmistir

  Senaryo Taslagi: Sidebar navigasyonu
    Diyelim ki kullanici herhangi bir sayfadadir
    Ozaman sidebar'da "<menu>" linkine tiklar
    Ve "<sayfa>" sayfasi yuklenir

    Ornekler:
      | menu        | sayfa      |
      | Senaryolar  | scenarios  |
      | Kosular     | executions |
      | Akislar     | flows      |
      | Onaylar     | approvals  |
      | Ice Aktar   | import     |
      | Regresyon   | regression |
