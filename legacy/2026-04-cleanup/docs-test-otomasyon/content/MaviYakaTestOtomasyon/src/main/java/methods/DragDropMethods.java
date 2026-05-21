package methods;

import org.openqa.selenium.By;
import org.openqa.selenium.WebElement;
import org.openqa.selenium.interactions.Actions;
import utilities.Driver;
import utilities.LoggerUtil;
import utilities.StepReporter;

import java.util.Map;

/**
 * DragDropMethods:
 * Sürükle-bırak (drag and drop) işlemlerini yönetir.
 */
public class DragDropMethods {

    /**
     * Kaynak elementi hedef elementin üzerine sürükleyip bırakır.
     *
     * @param sourceKey JSON locator key (kaynak)
     * @param targetKey JSON locator key (hedef)
     * @param locators  locator map
     */
    public void dragAndDrop(String sourceKey, String targetKey, Map<String, By> locators) {
        String stepDescription = "'" + sourceKey + "' adlı eleman '" + targetKey + "' adlı hedefe sürüklenip bırakılıyor";
        String details = "Kaynak: " + sourceKey + ", Hedef: " + targetKey;
        StepReporter.reportStepStart(stepDescription, details);
        LoggerUtil.logInfo("Drag and drop -> Source: " + sourceKey + ", Target: " + targetKey);
        try {
            WebElement source = WaitMethods.waitForElement(sourceKey, locators);
            WebElement target = WaitMethods.waitForElement(targetKey, locators);
            new Actions(Driver.getDriver()).dragAndDrop(source, target).perform();
            LoggerUtil.logInfo("Drag and drop successful");
            StepReporter.reportStepSuccess(stepDescription,
                    "'" + sourceKey + "' adlı eleman '" + targetKey + "' adlı hedefe başarıyla bırakıldı.");
        } catch (Exception e) {
            LoggerUtil.logError("Failed to drag and drop -> Source: " + sourceKey + ", Target: " + targetKey, e);
            StepReporter.reportStepError(stepDescription,
                    "Sürükle-bırak işlemi başarısız.", e);
            throw e;
        }
    }
}
