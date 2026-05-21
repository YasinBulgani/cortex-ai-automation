# language: tr
@regression-sets @regression
Özellik: Regresyon Setleri
  Test senaryolari regresyon setlerine gruplanir ve yonetilir.

  Arka plan:
    Diyelim ki kullanici sisteme giris yapmistir
    Ve aktif bir proje secilmistir

  Senaryo: Regresyon seti listesi goruntulenir
    Diyelim ki kullanici regresyon sayfasindadir
    Ozaman regresyon seti listesi goruntulenir

  @critical
  Senaryo: Yeni regresyon seti olusturma
    Diyelim ki kullanici regresyon sayfasindadir
    Ve set adini "Sprint-1 Regresyon" olarak girer
    Ozaman set olustur butonuna tiklar
    Ve regresyon seti basariyla olusturulur

  Senaryo: AI ile regresyon onerisi
    Diyelim ki kullanici regresyon sayfasindadir
    Ozaman AI oner butonuna tiklar
    Ve AI onerisi goruntulenir
