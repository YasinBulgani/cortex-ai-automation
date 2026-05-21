@api @bdd @TS-04
Feature: BDD Senaryo Uretimi
  Analiz dokumanindan AI ile Gherkin formatinda BDD senaryolari
  uretilir ve veritabanina kaydedilir.

  Arka plan: Proje hazir
    Given kullanici oturum acmis
    And bir test projesi olusturulmus

  # -- TC-0401 --
  @high @positive @TC-0401
  Scenario: Gecerli analiz metninden BDD senaryolari uretilir
    When asagidaki analiz metni ile BDD uretim istegi gonderilir:
      """
      Kullanici sisteme giris yapabilmeli,
      hatali giriste 3 deneme sonra hesap kilitlenmeli.
      """
    Then HTTP yanit kodu 200 olmalidir
    And yanit "scenarios" listesi bos olmamalidir

  # -- TC-0402 --
  @medium @boundary @TC-0402
  Scenario: 10 karakterden kisa analiz metni reddedilir
    When "Kisa" analiz metni ile BDD uretim istegi gonderilir
    Then HTTP yanit kodu 422 olmalidir

  # -- TC-0403 --
  @low @boundary @TC-0403
  Scenario: Tam 10 karakterlik analiz metni kabul edilir
    When "1234567890" analiz metni ile BDD uretim istegi gonderilir
    Then HTTP yanit kodu 200 olmalidir

  # -- TC-0404 --
  @high @positive @TC-0404
  Scenario: Uretilen BDD senaryolari veritabanina kaydedilir
    Given BDD senaryolari basariyla uretilmis
    When uretilen senaryolar kaydetme istegi ile gonderilir
    Then HTTP yanit kodu 201 olmalidir
    And kaydedilen tum senaryolar "draft" statusunde olmalidir
