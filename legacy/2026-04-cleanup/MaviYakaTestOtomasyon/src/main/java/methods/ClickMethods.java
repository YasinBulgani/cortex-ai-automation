package methods;

import org.openqa.selenium.By;
import org.openqa.selenium.WebElement;
import org.openqa.selenium.interactions.Actions;
import utilities.Driver;
import utilities.LoggerUtil;
import utilities.StepReporter;

import java.util.Map;

/**
 * ClickMethods:
 * Sayfadaki elementlere tıklama işlemlerini yönetir.
 * Standartlar:
 * - WaitMethods kullanır
 * - try–catch + log vardır
 * - Locator-driven çalışır
 * - StepReporter ile raporlama yapar
 */
public class ClickMethods {

    /**
     * Verilen locator key'e karşılık gelen elemente tıklar.
     *
     * @param elementKey JSON locator key
     * @param locators   locator map
     */
    public void clickOnElement(String elementKey, Map<String, By> locators) {

        // Kullanıcı dostu açıklama oluştur
        String stepDescription = StepReporter.createUserFriendlyDescription("tıklama", elementKey, null);
        String details = "Element anahtarı: " + elementKey;
        
        // Adımın başladığını raporla
        StepReporter.reportStepStart(stepDescription, details);

        LoggerUtil.logInfo("Clicking on element -> Key: " + elementKey);

        try {
            // Element yüklenene kadar bekle ve al
            WebElement element = WaitMethods.waitForElement(elementKey, locators);

            // Tıkla
            element.click();

            LoggerUtil.logInfo("Clicked successfully on element -> Key: " + elementKey);

            // Başarılı sonucu raporla
            StepReporter.reportStepSuccess(stepDescription, 
                "'" + elementKey + "' adlı elemana başarıyla tıklandı. İşlem tamamlandı.");

        } catch (Exception e) {
            LoggerUtil.logError(
                    "Failed to click on element -> Key: " + elementKey,
                    e
            );
            
            // Hata durumunu raporla
            StepReporter.reportStepError(stepDescription, 
                "'" + elementKey + "' adlı elemana tıklanamadı. Element bulunamadı veya tıklanamaz durumda.", e);
            
            // Test fail etsin
            throw e;
        }
    }

    /**
     * Verilen locator key'e karşılık gelen elemente çift tıklar.
     *
     * @param elementKey JSON locator key
     * @param locators   locator map
     */
    public void doubleClickOnElement(String elementKey, Map<String, By> locators) {
        String stepDescription = StepReporter.createUserFriendlyDescription("çift tıklama", elementKey, null);
        String details = "Element anahtarı: " + elementKey;
        StepReporter.reportStepStart(stepDescription, details);
        LoggerUtil.logInfo("Double clicking on element -> Key: " + elementKey);
        try {
            WebElement element = WaitMethods.waitForElement(elementKey, locators);
            new Actions(Driver.getDriver()).doubleClick(element).perform();
            LoggerUtil.logInfo("Double clicked successfully on element -> Key: " + elementKey);
            StepReporter.reportStepSuccess(stepDescription,
                "'" + elementKey + "' adlı elemana başarıyla çift tıklandı. İşlem tamamlandı.");
        } catch (Exception e) {
            LoggerUtil.logError("Failed to double click on element -> Key: " + elementKey, e);
            StepReporter.reportStepError(stepDescription,
                "'" + elementKey + "' adlı elemana çift tıklanamadı. Element bulunamadı veya tıklanamaz durumda.", e);
            throw e;
        }
    }

    /**
     * Verilen locator key'e karşılık gelen elemente sağ tıklar (context menu).
     *
     * @param elementKey JSON locator key
     * @param locators   locator map
     */
    public void rightClickOnElement(String elementKey, Map<String, By> locators) {
        String stepDescription = StepReporter.createUserFriendlyDescription("sağ tıklama", elementKey, null);
        String details = "Element anahtarı: " + elementKey;
        StepReporter.reportStepStart(stepDescription, details);
        LoggerUtil.logInfo("Right clicking on element -> Key: " + elementKey);
        try {
            WebElement element = WaitMethods.waitForElement(elementKey, locators);
            new Actions(Driver.getDriver()).contextClick(element).perform();
            LoggerUtil.logInfo("Right clicked successfully on element -> Key: " + elementKey);
            StepReporter.reportStepSuccess(stepDescription,
                "'" + elementKey + "' adlı elemana başarıyla sağ tıklandı. İşlem tamamlandı.");
        } catch (Exception e) {
            LoggerUtil.logError("Failed to right click on element -> Key: " + elementKey, e);
            StepReporter.reportStepError(stepDescription,
                "'" + elementKey + "' adlı elemana sağ tıklanamadı. Element bulunamadı veya tıklanamaz durumda.", e);
            throw e;
        }
    }
}
