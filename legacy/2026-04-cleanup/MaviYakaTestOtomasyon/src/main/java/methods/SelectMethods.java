package methods;

import org.openqa.selenium.By;
import org.openqa.selenium.WebElement;
import org.openqa.selenium.support.ui.Select;
import utilities.LoggerUtil;
import utilities.StepReporter;

import java.util.Map;

/**
 * SelectMethods:
 * Standart HTML &lt;select&gt; elementleri için seçim işlemlerini yönetir.
 * Locator-driven, StepReporter ve LoggerUtil ile uyumludur.
 */
public class SelectMethods {

    /**
     * Dropdown'dan görünen metne göre seçenek seçer.
     *
     * @param elementKey   JSON locator key (&lt;select&gt; elementi)
     * @param visibleText  Seçilecek seçeneğin görünen metni
     * @param locators     locator map
     */
    public void selectOptionByVisibleText(String elementKey, String visibleText, Map<String, By> locators) {
        String stepDescription = "'" + elementKey + "' adlı listeden '" + visibleText + "' seçiliyor";
        String details = "Element: " + elementKey + ", Seçenek: " + visibleText;
        StepReporter.reportStepStart(stepDescription, details);
        LoggerUtil.logInfo("Selecting by visible text -> Key: " + elementKey + ", Text: " + visibleText);
        try {
            WebElement element = WaitMethods.waitForElement(elementKey, locators);
            Select select = new Select(element);
            select.selectByVisibleText(visibleText);
            LoggerUtil.logInfo("Selected by visible text successfully -> Key: " + elementKey);
            StepReporter.reportStepSuccess(stepDescription,
                    "'" + elementKey + "' adlı listeden '" + visibleText + "' seçildi.");
        } catch (Exception e) {
            LoggerUtil.logError("Failed to select by visible text -> Key: " + elementKey, e);
            StepReporter.reportStepError(stepDescription,
                    "'" + elementKey + "' adlı listeden '" + visibleText + "' seçilemedi.", e);
            throw e;
        }
    }

    /**
     * Dropdown'dan value attribute değerine göre seçenek seçer.
     *
     * @param elementKey JSON locator key (&lt;select&gt; elementi)
     * @param value      Seçilecek seçeneğin value değeri
     * @param locators   locator map
     */
    public void selectOptionByValue(String elementKey, String value, Map<String, By> locators) {
        String stepDescription = "'" + elementKey + "' adlı listeden value '" + value + "' seçiliyor";
        String details = "Element: " + elementKey + ", Value: " + value;
        StepReporter.reportStepStart(stepDescription, details);
        LoggerUtil.logInfo("Selecting by value -> Key: " + elementKey + ", Value: " + value);
        try {
            WebElement element = WaitMethods.waitForElement(elementKey, locators);
            Select select = new Select(element);
            select.selectByValue(value);
            LoggerUtil.logInfo("Selected by value successfully -> Key: " + elementKey);
            StepReporter.reportStepSuccess(stepDescription,
                    "'" + elementKey + "' adlı listeden value '" + value + "' seçildi.");
        } catch (Exception e) {
            LoggerUtil.logError("Failed to select by value -> Key: " + elementKey, e);
            StepReporter.reportStepError(stepDescription,
                    "'" + elementKey + "' adlı listeden value '" + value + "' seçilemedi.", e);
            throw e;
        }
    }

    /**
     * Dropdown'da şu an seçili olan seçeneğin görünen metnini döner.
     *
     * @param elementKey JSON locator key (&lt;select&gt; elementi)
     * @param locators   locator map
     * @return Seçili seçeneğin metni
     */
    public String getSelectedOptionText(String elementKey, Map<String, By> locators) {
        WebElement element = WaitMethods.waitForElement(elementKey, locators);
        Select select = new Select(element);
        WebElement selected = select.getFirstSelectedOption();
        return selected != null ? selected.getText().trim() : "";
    }
}
