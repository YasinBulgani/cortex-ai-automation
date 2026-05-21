package methods;

import org.openqa.selenium.By;
import org.openqa.selenium.WebElement;
import utilities.LoggerUtil;
import utilities.StepReporter;

import java.util.Map;

/**
 * CheckboxMethods:
 * Checkbox işaretleme, kaldırma ve seçili durum doğrulama işlemlerini yönetir.
 * Locator-driven, StepReporter ve LoggerUtil ile uyumludur.
 */
public class CheckboxMethods {

    /**
     * Checkbox'ı işaretler (seçili değilse tıklar).
     *
     * @param elementKey JSON locator key
     * @param locators   locator map
     */
    public void checkCheckbox(String elementKey, Map<String, By> locators) {
        String stepDescription = "'" + elementKey + "' adlı checkbox işaretleniyor";
        String details = "Element: " + elementKey;
        StepReporter.reportStepStart(stepDescription, details);
        LoggerUtil.logInfo("Checking checkbox -> Key: " + elementKey);
        try {
            WebElement element = WaitMethods.waitForElement(elementKey, locators);
            if (!element.isSelected()) {
                element.click();
            }
            LoggerUtil.logInfo("Checkbox checked successfully -> Key: " + elementKey);
            StepReporter.reportStepSuccess(stepDescription,
                    "'" + elementKey + "' adlı checkbox işaretlendi.");
        } catch (Exception e) {
            LoggerUtil.logError("Failed to check checkbox -> Key: " + elementKey, e);
            StepReporter.reportStepError(stepDescription,
                    "'" + elementKey + "' adlı checkbox işaretlenemedi.", e);
            throw e;
        }
    }

    /**
     * Checkbox'ın işaretini kaldırır (seçiliyse tıklar).
     *
     * @param elementKey JSON locator key
     * @param locators   locator map
     */
    public void uncheckCheckbox(String elementKey, Map<String, By> locators) {
        String stepDescription = "'" + elementKey + "' adlı checkbox işareti kaldırılıyor";
        String details = "Element: " + elementKey;
        StepReporter.reportStepStart(stepDescription, details);
        LoggerUtil.logInfo("Unchecking checkbox -> Key: " + elementKey);
        try {
            WebElement element = WaitMethods.waitForElement(elementKey, locators);
            if (element.isSelected()) {
                element.click();
            }
            LoggerUtil.logInfo("Checkbox unchecked successfully -> Key: " + elementKey);
            StepReporter.reportStepSuccess(stepDescription,
                    "'" + elementKey + "' adlı checkbox işareti kaldırıldı.");
        } catch (Exception e) {
            LoggerUtil.logError("Failed to uncheck checkbox -> Key: " + elementKey, e);
            StepReporter.reportStepError(stepDescription,
                    "'" + elementKey + "' adlı checkbox işareti kaldırılamadı.", e);
            throw e;
        }
    }

    /**
     * Checkbox'ın işaretli olduğunu doğrular.
     *
     * @param elementKey JSON locator key
     * @param locators   locator map
     */
    public void verifyCheckboxIsChecked(String elementKey, Map<String, By> locators) {
        String stepDescription = "'" + elementKey + "' adlı checkbox'ın işaretli olduğu kontrol ediliyor";
        String details = "Element: " + elementKey;
        StepReporter.reportStepStart(stepDescription, details);
        LoggerUtil.logInfo("Verifying checkbox is checked -> Key: " + elementKey);
        try {
            WebElement element = WaitMethods.waitForElement(elementKey, locators);
            if (!element.isSelected()) {
                throw new AssertionError("Checkbox işaretli değil (beklenen: işaretli) -> Key: " + elementKey);
            }
            LoggerUtil.logInfo("Checkbox is checked -> Key: " + elementKey);
            StepReporter.reportStepSuccess(stepDescription,
                    "'" + elementKey + "' adlı checkbox işaretli. Doğrulama başarılı.");
        } catch (Exception e) {
            LoggerUtil.logError("Checkbox checked verification FAILED -> Key: " + elementKey, e);
            StepReporter.reportStepError(stepDescription,
                    "'" + elementKey + "' adlı checkbox işaretli değil.", e);
            throw e;
        }
    }

    /**
     * Checkbox'ın işaretsiz olduğunu doğrular.
     *
     * @param elementKey JSON locator key
     * @param locators   locator map
     */
    public void verifyCheckboxIsUnchecked(String elementKey, Map<String, By> locators) {
        String stepDescription = "'" + elementKey + "' adlı checkbox'ın işaretsiz olduğu kontrol ediliyor";
        String details = "Element: " + elementKey;
        StepReporter.reportStepStart(stepDescription, details);
        LoggerUtil.logInfo("Verifying checkbox is unchecked -> Key: " + elementKey);
        try {
            WebElement element = WaitMethods.waitForElement(elementKey, locators);
            if (element.isSelected()) {
                throw new AssertionError("Checkbox işaretli (beklenen: işaretsiz) -> Key: " + elementKey);
            }
            LoggerUtil.logInfo("Checkbox is unchecked -> Key: " + elementKey);
            StepReporter.reportStepSuccess(stepDescription,
                    "'" + elementKey + "' adlı checkbox işaretsiz. Doğrulama başarılı.");
        } catch (Exception e) {
            LoggerUtil.logError("Checkbox unchecked verification FAILED -> Key: " + elementKey, e);
            StepReporter.reportStepError(stepDescription,
                    "'" + elementKey + "' adlı checkbox işaretsiz değil.", e);
            throw e;
        }
    }
}
