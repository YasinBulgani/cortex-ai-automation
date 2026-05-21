package methods;

import org.openqa.selenium.By;
import org.openqa.selenium.JavascriptExecutor;
import org.openqa.selenium.WebElement;
import utilities.Driver;
import utilities.LoggerUtil;
import utilities.StepReporter;

import java.util.Map;

/**
 * ScrollMethods:
 * Sayfa üzerinde scroll işlemlerini yönetir.
 */
public class ScrollMethods {

    /**
     * Verilen locator key'e karşılık gelen element
     * görünür olana kadar sayfayı scroll eder.
     *
     * @param elementKey JSON locator key
     * @param locators   locator map
     */
    public void scrollToElement(String elementKey, Map<String, By> locators) {

        String stepDescription = StepReporter.createUserFriendlyDescription("kaydırma", elementKey, null);
        String details = "Element: " + elementKey;
        
        StepReporter.reportStepStart(stepDescription, details);

        LoggerUtil.logInfo("Scrolling to element -> Key: " + elementKey);

        try {
            // Element yüklenene kadar bekle
            WebElement element = WaitMethods.waitForElement(elementKey, locators);

            // JavaScript ile elemente scroll
            JavascriptExecutor js = (JavascriptExecutor) Driver.getDriver();
            js.executeScript("arguments[0].scrollIntoView({block:'center'});", element);

            LoggerUtil.logInfo("Scrolled successfully to element -> Key: " + elementKey);

            StepReporter.reportStepSuccess(stepDescription, 
                "Sayfa '" + elementKey + "' adlı elemana kadar başarıyla kaydırıldı.");

        } catch (Exception e) {
            LoggerUtil.logError(
                    "Failed to scroll to element -> Key: " + elementKey,
                    e
            );
            
            StepReporter.reportStepError(stepDescription, 
                "Sayfa '" + elementKey + "' adlı elemana kaydırılamadı. Element bulunamadı.", e);
            
            throw e;
        }
    }

    /**
     * Sayfayı en üste kaydırır.
     */
    public void scrollToTop() {
        String stepDescription = "Sayfa en üste kaydırılıyor";
        String details = "Scroll to top";
        StepReporter.reportStepStart(stepDescription, details);
        LoggerUtil.logInfo("Scrolling to top");
        try {
            JavascriptExecutor js = (JavascriptExecutor) Driver.getDriver();
            js.executeScript("window.scrollTo(0, 0);");
            LoggerUtil.logInfo("Scrolled to top successfully");
            StepReporter.reportStepSuccess(stepDescription, "Sayfa en üste kaydırıldı.");
        } catch (Exception e) {
            LoggerUtil.logError("Failed to scroll to top", e);
            StepReporter.reportStepError(stepDescription, "Sayfa en üste kaydırılamadı.", e);
            throw e;
        }
    }

    /**
     * Sayfayı en alta kaydırır.
     */
    public void scrollToBottom() {
        String stepDescription = "Sayfa en alta kaydırılıyor";
        String details = "Scroll to bottom";
        StepReporter.reportStepStart(stepDescription, details);
        LoggerUtil.logInfo("Scrolling to bottom");
        try {
            JavascriptExecutor js = (JavascriptExecutor) Driver.getDriver();
            js.executeScript("window.scrollTo(0, document.body.scrollHeight);");
            LoggerUtil.logInfo("Scrolled to bottom successfully");
            StepReporter.reportStepSuccess(stepDescription, "Sayfa en alta kaydırıldı.");
        } catch (Exception e) {
            LoggerUtil.logError("Failed to scroll to bottom", e);
            StepReporter.reportStepError(stepDescription, "Sayfa en alta kaydırılamadı.", e);
            throw e;
        }
    }

    /**
     * Sayfayı verilen piksel kadar yatay ve dikey kaydırır.
     *
     * @param x yatay piksel (pozitif sağa, negatif sola)
     * @param y dikey piksel (pozitif aşağı, negatif yukarı)
     */
    public void scrollBy(int x, int y) {
        String stepDescription = "Sayfa " + x + " px yatay, " + y + " px dikey kaydırılıyor";
        String details = "Scroll by x=" + x + ", y=" + y;
        StepReporter.reportStepStart(stepDescription, details);
        LoggerUtil.logInfo("Scrolling by x=" + x + ", y=" + y);
        try {
            JavascriptExecutor js = (JavascriptExecutor) Driver.getDriver();
            js.executeScript("window.scrollBy(" + x + ", " + y + ");");
            LoggerUtil.logInfo("Scrolled by successfully");
            StepReporter.reportStepSuccess(stepDescription, "Sayfa belirtilen miktarda kaydırıldı.");
        } catch (Exception e) {
            LoggerUtil.logError("Failed to scroll by", e);
            StepReporter.reportStepError(stepDescription, "Sayfa kaydırılamadı.", e);
            throw e;
        }
    }
}
