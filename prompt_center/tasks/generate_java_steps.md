Görev:
Verilen Gherkin adımları için Java step definition'ları üret.

Kurallar:
- Önce mevcut step'lerin yeniden kullanımını hedefle; gerçekten yeni step gerekiyorsa üret.
- Method isimleri okunabilir ve çakışmasız olsun.
- Parametreler step metni ile birebir uyumlu olsun.
- Gömülü magic value ve kırılgan locator ekleme.
- Kod mevcut MaviYaka framework stiline uygun, derlenebilir ve sade olsun.

Format:
```java
// StepDefinitions — AI Generated
import io.cucumber.java.tr.*;

public class [ModuleName]Steps {
    @Eğer("...")
    public void ...() {
        // implement
    }
}
```
Yanıt yalnızca Java kodu olsun.
