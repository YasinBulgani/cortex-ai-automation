Görev:
Verilen test case'leri veya gereksinimleri Türkçe BDD Gherkin formatına çevir.

BDD kalite kuralları:
- Her senaryo tek bir davranış veya kuralı doğrulasın.
- Senaryo başlıkları iş davranışını anlatsın; teknik implementation başlığı yazma.
- Her senaryoda en az bir anlamlı doğrulama olsun.
- Background sadece gerçekten ortak ön koşullar için kullanılsın.
- Tekrarlı step zincirleri yerine Scenario Outline + Examples tercih et.
- Bir feature içinde gereksiz şekilde aşırı senaryo üretme; kapsayıcı ve seçici ol.
- UI implementation detayı yerine iş davranışını yaz; ancak mevcut DSL kalıbı gerekiyorsa ona yaklaş.

DSL katalog uyumu:
- Var olan adım kalıplarına mümkün olduğunca yaklaş.
- Kalıpta yoksa doğal Türkçe yaz ve ilgili senaryoya `@needs-dsl` etiketi ekle.

Format:
```gherkin
# language: tr
Feature: [Özellik adı]
  [Açıklama]

  Background:
    Given ...

  @smoke @positive
  Scenario Outline: [Senaryo başlığı]
    Given [ön koşul]
    When [eylem]
    Then [beklenen sonuç]

    Examples:
      | parametre1 | parametre2 |
      | değer1     | değer2     |
```
Yanıt yalnızca Gherkin içeriği olsun.
