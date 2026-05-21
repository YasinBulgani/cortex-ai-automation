package methods;

import org.openqa.selenium.By;
import org.openqa.selenium.WebElement;
import utilities.Driver;
import utilities.LoggerUtil;
import utilities.StepReporter;

import java.util.List;
import java.util.Map;

/**
 * RadioButtonMethods:
 * Radyo buton seçimi ve seçili değer doğrulama işlemlerini yönetir.
 * Grup locator'ı (örn. name) ile tüm radyolar bulunur, value'ya göre seçilir.
 */
public class RadioButtonMethods {

    /**
     * Radyo grubunda belirtilen value'ya sahip seçeneği seçer.
     * Locator key genelde grubun name'i veya grubu dönen bir locator'dır (findElements ile hepsi bulunur).
     *
     * @param groupOrKey JSON locator key (grup veya tek radyo)
     * @param value      Seçilecek radyonun value attribute değeri
     * @param locators   locator map
     */
    public void selectRadioByValue(String groupOrKey, String value, Map<String, By> locators) {
        String stepDescription = "'" + groupOrKey + "' grubunda '" + value + "' değeri seçiliyor";
        String details = "Grup/Key: " + groupOrKey + ", Value: " + value;
        StepReporter.reportStepStart(stepDescription, details);
        LoggerUtil.logInfo("Selecting radio by value -> Key: " + groupOrKey + ", Value: " + value);
        try {
            By locator = locators.get(groupOrKey);
            if (locator == null) {
                throw new RuntimeException("Locator not found for key: " + groupOrKey);
            }
            List<WebElement> radios = Driver.getDriver().findElements(locator);
            WebElement toClick = radios.stream()
                    .filter(el -> value != null && value.equals(el.getAttribute("value")))
                    .findFirst()
                    .orElse(null);
            if (toClick == null) {
                throw new AssertionError("Radyo buton bulunamadı: key=" + groupOrKey + ", value=" + value);
            }
            if (!toClick.isSelected()) {
                toClick.click();
            }
            LoggerUtil.logInfo("Radio selected successfully -> " + groupOrKey + ", value=" + value);
            StepReporter.reportStepSuccess(stepDescription,
                    "'" + groupOrKey + "' grubunda '" + value + "' değeri seçildi.");
        } catch (Exception e) {
            LoggerUtil.logError("Failed to select radio -> Key: " + groupOrKey + ", Value: " + value, e);
            StepReporter.reportStepError(stepDescription,
                    "Radyo buton seçilemedi.", e);
            throw e;
        }
    }

    /**
     * Radyo grubunda belirtilen value'ya sahip seçeneğin seçili olduğunu doğrular.
     *
     * @param groupOrKey JSON locator key (grup)
     * @param value      Beklenen seçili value
     * @param locators   locator map
     */
    public void verifyRadioSelected(String groupOrKey, String value, Map<String, By> locators) {
        String stepDescription = "'" + groupOrKey + "' grubunda '" + value + "' değerinin seçili olduğu kontrol ediliyor";
        String details = "Grup/Key: " + groupOrKey + ", Value: " + value;
        StepReporter.reportStepStart(stepDescription, details);
        LoggerUtil.logInfo("Verifying radio selected -> Key: " + groupOrKey + ", Value: " + value);
        try {
            By locator = locators.get(groupOrKey);
            if (locator == null) {
                throw new RuntimeException("Locator not found for key: " + groupOrKey);
            }
            List<WebElement> radios = Driver.getDriver().findElements(locator);
            WebElement selectedRadio = radios.stream()
                    .filter(WebElement::isSelected)
                    .findFirst()
                    .orElse(null);
            if (selectedRadio == null) {
                throw new AssertionError("Hiçbir radyo seçili değil -> Key: " + groupOrKey);
            }
            String actualValue = selectedRadio.getAttribute("value");
            if (!value.equals(actualValue)) {
                throw new AssertionError("Seçili radyo uyuşmazlığı! Beklenen value: [" + value + "] bulunan: [" + actualValue + "]");
            }
            LoggerUtil.logInfo("Radio selected verification PASSED -> " + groupOrKey);
            StepReporter.reportStepSuccess(stepDescription,
                    "'" + groupOrKey + "' grubunda '" + value + "' değeri seçili. Doğrulama başarılı.");
        } catch (Exception e) {
            LoggerUtil.logError("Radio selected verification FAILED -> Key: " + groupOrKey, e);
            StepReporter.reportStepError(stepDescription,
                    "Radyo seçili değer doğrulaması başarısız.", e);
            throw e;
        }
    }
}
