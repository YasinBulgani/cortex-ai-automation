# language: tr
@a11y @regression
Özellik: Erisilebilirlik (WCAG 2.1 AA)
  Tum sayfalar WCAG 2.1 AA standartlarina uygun olmalidir.

  Arka plan:
    Diyelim ki kullanici sisteme giris yapmistir

  Senaryo Taslagi: Sayfa erisilebilirlik kontrolu
    Diyelim ki kullanici "<sayfa>" a11y sayfasindadir
    Ozaman sayfa WCAG 2.1 AA standartlarina uygun olmalidir
    Ve sayfa klavye ile gezinilebilir olmalidir
    Ve tum resimlerde alt metni bulunmalidir

    Ornekler:
      | sayfa    |
      | login    |
      | projects |
