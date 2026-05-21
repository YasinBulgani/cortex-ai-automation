package methods;

import org.openqa.selenium.By;
import org.openqa.selenium.WebElement;
import utilities.LoggerUtil;
import utilities.ScenarioContext;
import utilities.StepReporter;

import java.util.Map;

/**
 * ContextMethods:
 * Senaryo içinde bir elementin değerini veya attribute'unu key ile saklar.
 * ScenarioContext kullanır; aynı senaryoda sonraki adımlarda bu key ile okunabilir.
 */
public class ContextMethods {

    /**
     * Elementin metnini (getText) verilen key ile senaryo context'ine kaydeder.
     *
     * @param elementKey  JSON locator key (değerin alınacağı element)
     * @param storageKey  Saklama anahtarı (sonra "value stored under storageKey" ile okunur)
     * @param locators   locator map
     */
    public void saveElementTextAs(String elementKey, String storageKey, Map<String, By> locators) {
        String stepDescription = "'" + elementKey + "' adlı elemanın metni '" + storageKey + "' anahtarı ile saklanıyor";
        String details = "Element: " + elementKey + ", Key: " + storageKey;
        StepReporter.reportStepStart(stepDescription, details);
        LoggerUtil.logInfo("Saving element text to context -> Element: " + elementKey + ", Key: " + storageKey);
        try {
            WebElement element = WaitMethods.waitForElement(elementKey, locators);
            String value = element.getText().trim();
            ScenarioContext.put(storageKey, value);
            LoggerUtil.logInfo("Value saved to context -> Key: " + storageKey);
            StepReporter.reportStepSuccess(stepDescription,
                    "'" + storageKey + "' anahtarı ile değer saklandı: " + (value.length() > 50 ? value.substring(0, 50) + "..." : value));
        } catch (Exception e) {
            LoggerUtil.logError("Failed to save element text to context -> Key: " + storageKey, e);
            StepReporter.reportStepError(stepDescription, "Değer saklanamadı.", e);
            throw e;
        }
    }

    /**
     * Elementin belirtilen attribute değerini verilen key ile senaryo context'ine kaydeder.
     *
     * @param elementKey    JSON locator key
     * @param attributeName attribute adı (value, href, placeholder vb.)
     * @param storageKey   Saklama anahtarı
     * @param locators      locator map
     */
    public void saveElementAttributeAs(String elementKey, String attributeName, String storageKey, Map<String, By> locators) {
        String stepDescription = "'" + elementKey + "' adlı elemanın '" + attributeName + "' değeri '" + storageKey + "' anahtarı ile saklanıyor";
        String details = "Element: " + elementKey + ", Attribute: " + attributeName + ", Key: " + storageKey;
        StepReporter.reportStepStart(stepDescription, details);
        LoggerUtil.logInfo("Saving element attribute to context -> Element: " + elementKey + ", Attr: " + attributeName + ", Key: " + storageKey);
        try {
            WebElement element = WaitMethods.waitForElement(elementKey, locators);
            String value = element.getAttribute(attributeName);
            if (value != null) {
                value = value.trim();
            } else {
                value = "";
            }
            ScenarioContext.put(storageKey, value);
            LoggerUtil.logInfo("Attribute value saved to context -> Key: " + storageKey);
            StepReporter.reportStepSuccess(stepDescription,
                    "'" + storageKey + "' anahtarı ile değer saklandı.");
        } catch (Exception e) {
            LoggerUtil.logError("Failed to save attribute to context -> Key: " + storageKey, e);
            StepReporter.reportStepError(stepDescription, "Değer saklanamadı.", e);
            throw e;
        }
    }
}
