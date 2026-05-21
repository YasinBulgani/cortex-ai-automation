package methods;

import org.openqa.selenium.By;
import org.openqa.selenium.WebElement;
import org.openqa.selenium.interactions.Actions;
import utilities.Driver;
import utilities.LoggerUtil;
import utilities.StepReporter;

import java.util.Map;

/**
 * HoverMethods:
 * Element üzerine gelme (hover) işlemlerini yönetir.
 * Dropdown menü vb. senaryolarda kullanılır.
 */
public class HoverMethods {

    /**
     * Verilen elementin üzerine gelir (mouse over).
     *
     * @param elementKey JSON locator key
     * @param locators   locator map
     */
    public void hoverOverElement(String elementKey, Map<String, By> locators) {
        String stepDescription = "'" + elementKey + "' adlı elemanın üzerine geliniyor";
        String details = "Element: " + elementKey;
        StepReporter.reportStepStart(stepDescription, details);
        LoggerUtil.logInfo("Hovering over element -> Key: " + elementKey);
        try {
            WebElement element = WaitMethods.waitForElement(elementKey, locators);
            new Actions(Driver.getDriver()).moveToElement(element).perform();
            LoggerUtil.logInfo("Hover successful -> Key: " + elementKey);
            StepReporter.reportStepSuccess(stepDescription,
                    "'" + elementKey + "' adlı elemanın üzerine gelindi.");
        } catch (Exception e) {
            LoggerUtil.logError("Failed to hover over element -> Key: " + elementKey, e);
            StepReporter.reportStepError(stepDescription,
                    "'" + elementKey + "' adlı elemanın üzerine gelinemedi.", e);
            throw e;
        }
    }
}
