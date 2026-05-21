package methods;

import org.openqa.selenium.By;
import org.openqa.selenium.WebElement;
import org.openqa.selenium.support.ui.Select;
import utilities.Driver;
import utilities.LoggerUtil;
import utilities.StepReporter;

import java.util.List;
import java.util.Map;

/**
 * AssertionMethods:
 * Sayfadaki text değerlerini ve görünürlük durumlarını doğrulamak için kullanılır.
 */
public class AssertionMethods {

    /**
     * Elementin text'inin beklenen değerle eşleşip eşleşmediğini kontrol eder.
     *
     * @param elementKey     JSON locator key
     * @param expectedText   Cucumber'dan gelen beklenen değer
     * @param locators       locator map
     */
    public void verifyElementTextEquals(String elementKey, String expectedText, Map<String, By> locators) {

        String stepDescription = StepReporter.createUserFriendlyDescription("doğrulama", elementKey, expectedText);
        String details = "Element: " + elementKey + ", Beklenen metin: " + expectedText;
        
        StepReporter.reportStepStart(stepDescription, details);

        LoggerUtil.logInfo("Verifying text of element -> Key: " + elementKey + ", Expected: " + expectedText);

        try {
            // Elementi bekle ve al
            WebElement element = WaitMethods.waitForElement(elementKey, locators);

            String actualText = element.getText().trim();

            if (!actualText.equals(expectedText)) {
                // Türkçe assertion mesajı (Allure'da da görünecek)
                String turkishError = "Metin uyuşmazlığı! Beklenen: [" + expectedText + "] ama bulunan: [" + actualText + "]";
                throw new AssertionError(turkishError);
            }

            LoggerUtil.logInfo("Text verification PASSED -> Key: " + elementKey);

            StepReporter.reportStepSuccess(stepDescription, 
                "'" + elementKey + "' adlı elemanın metni doğrulandı. Beklenen değer: '" + expectedText + "' bulundu.");

        } catch (Exception e) {
            LoggerUtil.logError("Text verification FAILED -> Key: " + elementKey, e);
            
            StepReporter.reportStepError(stepDescription, 
                "'" + elementKey + "' adlı elemanın metni beklenen değerle eşleşmedi. Beklenen: '" + expectedText + "'", e);
            
            throw e;
        }
    }
    /**
     * Elementin sayfada görünür olup olmadığını kontrol eder.
     *
     * @param elementKey JSON locator key
     * @param locators   locator map
     */
    public void verifyElementIsVisible(String elementKey, Map<String, By> locators) {

        String stepDescription = "'" + elementKey + "' adlı elemanın sayfada görünür olduğu kontrol ediliyor";
        String details = "Element: " + elementKey;
        
        StepReporter.reportStepStart(stepDescription, details);

        LoggerUtil.logInfo("Verifying element is visible -> Key: " + elementKey);

        try {
            // I see the element: 20 sn timeout, 0,2 sn polling (diğer metodlar 10 sn kalır)
            WebElement element = WaitMethods.waitForElement(elementKey, locators, 20);

            // Ekstra garanti (wait zaten visible bekliyor ama assertion net olsun)
            if (!element.isDisplayed()) {
                throw new AssertionError("Element sayfada görünür değil -> Key: " + elementKey);
            }

            LoggerUtil.logInfo("Element is visible -> Key: " + elementKey);

            StepReporter.reportStepSuccess(stepDescription, 
                "'" + elementKey + "' adlı eleman sayfada görünür durumda. Kontrol başarılı.");

        } catch (Exception e) {
            LoggerUtil.logError(
                    "Visibility check FAILED -> Key: " + elementKey,
                    e
            );
            
            StepReporter.reportStepError(stepDescription, 
                "'" + elementKey + "' adlı eleman sayfada görünür değil veya bulunamadı.", e);
            
            throw e;
        }
    }

    /**
     * JSON locator key ile belirtilen elementin sayfada OLMADIĞINI doğrular.
     * Element bulunursa assertion fırlatır.
     */
    public void verifyElementNotExists(String elementKey, Map<String, By> locators) {

        String stepDescription = "'" + elementKey + "' adlı elemanın sayfada olmadığı kontrol ediliyor";
        String details = "Element: " + elementKey;
        
        StepReporter.reportStepStart(stepDescription, details);

        LoggerUtil.logInfo("Verifying element does NOT exist -> Key: " + elementKey);

        try {
            By locator = locators.get(elementKey);
            if (locator == null) {
                LoggerUtil.logError("Locator not found for key: " + elementKey, null);
                throw new AssertionError("Locator bulunamadı -> Key: " + elementKey);
            }

            // Elementin DOM'da olup olmadığını kontrol et (görünür olması gerekmez)
            List<WebElement> elements = Driver.getDriver().findElements(locator);

            // Eğer element bulunduysa hata fırlat
            if (!elements.isEmpty()) {
                int count = elements.size();
                String errorMsg = "Element sayfada bulundu! Key: " + elementKey + ", Bulunan element sayısı: " + count;
                LoggerUtil.logError(errorMsg, null);
                throw new AssertionError(errorMsg);
            }

            LoggerUtil.logInfo("Element does not exist on page -> Key: " + elementKey);

            StepReporter.reportStepSuccess(stepDescription, 
                "'" + elementKey + "' adlı eleman sayfada bulunmadı. Kontrol başarılı.");

        } catch (AssertionError e) {
            StepReporter.reportStepError(stepDescription, 
                "'" + elementKey + "' adlı eleman sayfada bulundu (bulunmaması gerekiyordu).", e);
            throw e;
        } catch (Exception e) {
            LoggerUtil.logError(
                    "Error while verifying element does not exist -> Key: " + elementKey,
                    e
            );
            
            StepReporter.reportStepError(stepDescription, 
                "'" + elementKey + "' adlı eleman kontrol edilirken hata oluştu.", e);
            
            throw e;
        }
    }

    /**
     * Elementin text'inin belirtilen alt metni içerip içermediğini kontrol eder.
     *
     * @param elementKey       JSON locator key
     * @param expectedSubtext  Aranacak alt metin
     * @param locators         locator map
     */
    public void verifyElementContainsText(String elementKey, String expectedSubtext, Map<String, By> locators) {
        String stepDescription = StepReporter.createUserFriendlyDescription("içerik doğrulama", elementKey, expectedSubtext);
        String details = "Element: " + elementKey + ", Aranan metin: " + expectedSubtext;
        StepReporter.reportStepStart(stepDescription, details);
        LoggerUtil.logInfo("Verifying element contains text -> Key: " + elementKey + ", Subtext: " + expectedSubtext);
        try {
            WebElement element = WaitMethods.waitForElement(elementKey, locators);
            String actualText = element.getText().trim();
            if (!actualText.contains(expectedSubtext)) {
                String turkishError = "Metin içermiyor! Aranan: [" + expectedSubtext + "], Bulunan: [" + actualText + "]";
                throw new AssertionError(turkishError);
            }
            LoggerUtil.logInfo("Contains text verification PASSED -> Key: " + elementKey);
            StepReporter.reportStepSuccess(stepDescription,
                "'" + elementKey + "' adlı elemanın metni '" + expectedSubtext + "' içeriyor. Doğrulama başarılı.");
        } catch (Exception e) {
            LoggerUtil.logError("Contains text verification FAILED -> Key: " + elementKey, e);
            StepReporter.reportStepError(stepDescription,
                "'" + elementKey + "' adlı elemanın metni '" + expectedSubtext + "' içermiyor.", e);
            throw e;
        }
    }

    /**
     * Elementin etkin (tıklanabilir/yazılabilir) olduğunu doğrular.
     */
    public void verifyElementIsEnabled(String elementKey, Map<String, By> locators) {
        String stepDescription = "'" + elementKey + "' adlı elemanın etkin olduğu kontrol ediliyor";
        String details = "Element: " + elementKey;
        StepReporter.reportStepStart(stepDescription, details);
        LoggerUtil.logInfo("Verifying element is enabled -> Key: " + elementKey);
        try {
            WebElement element = WaitMethods.waitForElement(elementKey, locators);
            if (!element.isEnabled()) {
                throw new AssertionError("Element etkin değil (disabled) -> Key: " + elementKey);
            }
            LoggerUtil.logInfo("Element is enabled -> Key: " + elementKey);
            StepReporter.reportStepSuccess(stepDescription,
                "'" + elementKey + "' adlı eleman etkin. Kontrol başarılı.");
        } catch (Exception e) {
            LoggerUtil.logError("Enabled check FAILED -> Key: " + elementKey, e);
            StepReporter.reportStepError(stepDescription,
                "'" + elementKey + "' adlı eleman etkin değil veya bulunamadı.", e);
            throw e;
        }
    }

    /**
     * Elementin devre dışı (disabled) olduğunu doğrular.
     */
    public void verifyElementIsDisabled(String elementKey, Map<String, By> locators) {
        String stepDescription = "'" + elementKey + "' adlı elemanın devre dışı olduğu kontrol ediliyor";
        String details = "Element: " + elementKey;
        StepReporter.reportStepStart(stepDescription, details);
        LoggerUtil.logInfo("Verifying element is disabled -> Key: " + elementKey);
        try {
            WebElement element = WaitMethods.waitForElement(elementKey, locators);
            if (element.isEnabled()) {
                throw new AssertionError("Element etkin (disabled olması bekleniyordu) -> Key: " + elementKey);
            }
            LoggerUtil.logInfo("Element is disabled -> Key: " + elementKey);
            StepReporter.reportStepSuccess(stepDescription,
                "'" + elementKey + "' adlı eleman devre dışı. Kontrol başarılı.");
        } catch (Exception e) {
            LoggerUtil.logError("Disabled check FAILED -> Key: " + elementKey, e);
            StepReporter.reportStepError(stepDescription,
                "'" + elementKey + "' adlı eleman devre dışı değil veya bulunamadı.", e);
            throw e;
        }
    }

    /**
     * Elementin belirtilen attribute değerinin eşleşip eşleşmediğini kontrol eder.
     *
     * @param elementKey    JSON locator key
     * @param attributeName attribute adı (örn: href, value, placeholder)
     * @param expectedValue beklenen değer
     * @param locators      locator map
     */
    public void verifyElementAttributeEquals(String elementKey, String attributeName, String expectedValue, Map<String, By> locators) {
        String stepDescription = "'" + elementKey + "' adlı elemanın '" + attributeName + "' değeri '" + expectedValue + "' olarak kontrol ediliyor";
        String details = "Element: " + elementKey + ", Attribute: " + attributeName + ", Beklenen: " + expectedValue;
        StepReporter.reportStepStart(stepDescription, details);
        LoggerUtil.logInfo("Verifying attribute -> Key: " + elementKey + ", Attr: " + attributeName);
        try {
            WebElement element = WaitMethods.waitForElement(elementKey, locators);
            String actualValue = element.getAttribute(attributeName);
            if (actualValue == null) {
                actualValue = "";
            }
            if (!actualValue.trim().equals(expectedValue != null ? expectedValue.trim() : "")) {
                String turkishError = "Attribute uyuşmazlığı! " + attributeName + " beklenen: [" + expectedValue + "] bulunan: [" + actualValue + "]";
                throw new AssertionError(turkishError);
            }
            LoggerUtil.logInfo("Attribute verification PASSED -> Key: " + elementKey);
            StepReporter.reportStepSuccess(stepDescription,
                "'" + elementKey + "' adlı elemanın " + attributeName + " değeri doğrulandı.");
        } catch (Exception e) {
            LoggerUtil.logError("Attribute verification FAILED -> Key: " + elementKey, e);
            StepReporter.reportStepError(stepDescription,
                "'" + elementKey + "' adlı elemanın " + attributeName + " değeri beklenenle eşleşmedi.", e);
            throw e;
        }
    }

    /**
     * &lt;select&gt; elementinde seçili olan seçeneğin metninin beklenen değere eşit olduğunu doğrular.
     *
     * @param elementKey   JSON locator key (select elementi)
     * @param expectedText beklenen seçili metin
     * @param locators     locator map
     */
    public void verifySelectSelectedOptionEquals(String elementKey, String expectedText, Map<String, By> locators) {
        String stepDescription = "'" + elementKey + "' adlı listede seçili değerin '" + expectedText + "' olduğu kontrol ediliyor";
        String details = "Element: " + elementKey + ", Beklenen: " + expectedText;
        StepReporter.reportStepStart(stepDescription, details);
        LoggerUtil.logInfo("Verifying selected option -> Key: " + elementKey + ", Expected: " + expectedText);
        try {
            WebElement element = WaitMethods.waitForElement(elementKey, locators);
            Select select = new Select(element);
            WebElement selected = select.getFirstSelectedOption();
            String actualText = selected != null ? selected.getText().trim() : "";
            if (!actualText.equals(expectedText != null ? expectedText.trim() : "")) {
                String turkishError = "Seçili değer uyuşmazlığı! Beklenen: [" + expectedText + "] bulunan: [" + actualText + "]";
                throw new AssertionError(turkishError);
            }
            LoggerUtil.logInfo("Selected option verification PASSED -> Key: " + elementKey);
            StepReporter.reportStepSuccess(stepDescription,
                    "'" + elementKey + "' adlı listede seçili değer '" + expectedText + "' olarak doğrulandı.");
        } catch (Exception e) {
            LoggerUtil.logError("Selected option verification FAILED -> Key: " + elementKey, e);
            StepReporter.reportStepError(stepDescription,
                    "'" + elementKey + "' adlı listede seçili değer beklenenle eşleşmedi.", e);
            throw e;
        }
    }

}

