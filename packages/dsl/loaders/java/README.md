# BGTS DSL Java Loader

Java (Cucumber JVM) tarafı Python/TypeScript'ten farklı: step registration
derleme zamanında annotation taramayla gerçekleşir. Runtime'da YAML'dan
dinamik kayıt mümkün değildir.

## Çözüm: Code Generation

[`generate_java_steps.py`](../../scripts/generate_java_steps.py) script'i YAML
katalogu okuyup, her kategoriye/kategorilere göre Java step sınıfları üretir.

### Kullanım

```bash
make dsl-java-gen                              # tümünü üret
make dsl-java-gen CATEGORY=ui                  # sadece UI kategorisi
```

Üretilen dosyalar:
  frameworks/selenium-cucumber-java/src/test/java/stepdefinitions/generated/
  ├── GeneratedUiSteps.java
  ├── GeneratedApiSteps.java
  └── ...

Üretilen sınıflar gerçek implementasyon değil, **katalogdaki alias'ları
mevcut step method'larına yönlendiren ek `@When/@Given/@Then` annotation'lar**
sunar. Mevcut `ClickSteps.java` vb. dosyalar değiştirilmez.

### Çalışma Prensibi

YAML katalogda bir action şöyle tanımlıysa:

```yaml
- id: click_on_element
  implementations:
    java:
      class: stepdefinitions.ClickSteps
      method: clickOnElement
      source_file: frameworks/.../ClickSteps.java
  aliases:
    en: ["I click on {string}"]
    tr: ["{string} elementine tıklarım"]
```

Generator `GeneratedClickSteps.java` üretir:

```java
public class GeneratedClickSteps {
    private final ClickSteps delegate = new ClickSteps();

    @When("I click on {string}")
    public void clickOnElement_en_0(String key) { delegate.clickOnElement(key); }

    @When("{string} elementine tıklarım")
    public void clickOnElement_tr_0(String key) { delegate.clickOnElement(key); }
}
```

Böylece **tek bir Java implementation** farklı TR/EN alias'larla kullanılabilir.
