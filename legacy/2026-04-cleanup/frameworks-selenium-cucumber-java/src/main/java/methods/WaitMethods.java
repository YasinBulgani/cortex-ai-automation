package methods;

import org.openqa.selenium.By;
import org.openqa.selenium.TimeoutException;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.WebElement;
import org.openqa.selenium.support.ui.ExpectedConditions;
import org.openqa.selenium.support.ui.FluentWait;
import utilities.Driver;
import utilities.LoggerUtil;
import utilities.StepReporter;

import java.time.Duration;
import java.util.Map;
import java.util.NoSuchElementException;

/**
 * WaitMethods:
 * Tek metod ile elementin yüklenmesini bekler.
 *
 * Varsayılan davranış:
 * - Element görünür olana kadar bekler
 * - Max 10 sn
 * - 200 ms polling (performanslı)
 */
public class WaitMethods {

    private static final int DEFAULT_VISIBLE_TIMEOUT_SECONDS = 10;
    private static final int POLLING_MILLIS = 200;

    /**
     * Locator key'e göre elementi bekler ve döner. Varsayılan 10 sn, 200 ms polling.
     *
     * @param elementKey JSON locator key
     * @param locators   locator map
     * @return WebElement
     */
    public static WebElement waitForElement(String elementKey, Map<String, By> locators) {
        return waitForElement(elementKey, locators, DEFAULT_VISIBLE_TIMEOUT_SECONDS);
    }

    /**
     * Locator key'e göre elementi belirtilen süreyle bekler. 200 ms polling.
     *
     * @param elementKey      JSON locator key
     * @param locators        locator map
     * @param timeoutSeconds  maksimum bekleme süresi (saniye)
     * @return WebElement
     */
    public static WebElement waitForElement(String elementKey, Map<String, By> locators, int timeoutSeconds) {
        if (!locators.containsKey(elementKey)) {
            locators.put(elementKey, By.xpath(elementKey));
        }

        By locator = locators.get(elementKey);
        if (locator == null) {
            throw new RuntimeException("Locator not found for key: " + elementKey);
        }

        WebDriver driver = Driver.getDriver();
        LoggerUtil.logInfo("Waiting for element to be visible -> Key: " + elementKey + ", timeout: " + timeoutSeconds + "s");

        try {
            FluentWait<WebDriver> wait = new FluentWait<>(driver)
                    .withTimeout(Duration.ofSeconds(timeoutSeconds))
                    .pollingEvery(Duration.ofMillis(POLLING_MILLIS))
                    .ignoring(NoSuchElementException.class);

            return wait.until(ExpectedConditions.visibilityOfElementLocated(locator));
        } catch (TimeoutException e) {
            LoggerUtil.logError("Timeout waiting for element -> Key: " + elementKey, e);
            throw e;
        } catch (Exception e) {
            LoggerUtil.logError("Error while waiting for element -> Key: " + elementKey, e);
            throw e;
        }
    }

    /**
     * Verilen süre kadar (saniye) bekler.
     * Step raporlaması ile kullanılır.
     *
     * @param seconds Beklenecek saniye
     */
    public void waitForSeconds(int seconds) {
        String stepDescription = seconds + " saniye bekleniyor";
        String details = "Bekleme süresi: " + seconds + " saniye";

        StepReporter.reportStepStart(stepDescription, details);
        LoggerUtil.logInfo("Waiting for " + seconds + " seconds");

        try {
            Thread.sleep(seconds * 1000L);
            LoggerUtil.logInfo("Wait completed successfully -> " + seconds + " seconds");
            StepReporter.reportStepSuccess(stepDescription,
                    seconds + " saniye bekleme tamamlandı.");
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            LoggerUtil.logError("Wait interrupted -> " + seconds + " seconds", e);
            StepReporter.reportStepError(stepDescription,
                    "Bekleme kesintiye uğradı.", e);
            throw new RuntimeException("Bekleme kesintiye uğradı.", e);
        }
    }

    /**
     * Element tıklanabilir olana kadar bekler (görünür ve enabled).
     *
     * @param elementKey JSON locator key
     * @param locators   locator map
     */
    public void waitForElementClickable(String elementKey, Map<String, By> locators) {
        String stepDescription = "'" + elementKey + "' adlı elemanın tıklanabilir olması bekleniyor";
        String details = "Element: " + elementKey;
        StepReporter.reportStepStart(stepDescription, details);
        LoggerUtil.logInfo("Waiting for element to be clickable -> Key: " + elementKey);
        try {
            if (!locators.containsKey(elementKey)) {
                locators.put(elementKey, By.xpath(elementKey));
            }
            By locator = locators.get(elementKey);
            if (locator == null) {
                throw new RuntimeException("Locator not found for key: " + elementKey);
            }
            FluentWait<WebDriver> wait = new FluentWait<>(Driver.getDriver())
                    .withTimeout(Duration.ofSeconds(10))
                    .pollingEvery(Duration.ofMillis(200))
                    .ignoring(NoSuchElementException.class);
            wait.until(ExpectedConditions.elementToBeClickable(locator));
            LoggerUtil.logInfo("Element is clickable -> Key: " + elementKey);
            StepReporter.reportStepSuccess(stepDescription,
                    "'" + elementKey + "' adlı eleman tıklanabilir. Bekleme tamamlandı.");
        } catch (Exception e) {
            LoggerUtil.logError("Timeout or error waiting for element to be clickable -> Key: " + elementKey, e);
            StepReporter.reportStepError(stepDescription,
                    "'" + elementKey + "' adlı eleman tıklanabilir olana kadar beklenirken hata oluştu.", e);
            throw e;
        }
    }

    /**
     * Element DOM'dan veya görünürlükten kaybolana kadar bekler.
     *
     * @param elementKey JSON locator key
     * @param locators   locator map
     */
    public void waitForElementToDisappear(String elementKey, Map<String, By> locators) {
        String stepDescription = "'" + elementKey + "' adlı elemanın kaybolması bekleniyor";
        String details = "Element: " + elementKey;
        StepReporter.reportStepStart(stepDescription, details);
        LoggerUtil.logInfo("Waiting for element to disappear -> Key: " + elementKey);
        try {
            By locator = locators.get(elementKey);
            if (locator == null) {
                throw new RuntimeException("Locator not found for key: " + elementKey);
            }
            FluentWait<WebDriver> wait = new FluentWait<>(Driver.getDriver())
                    .withTimeout(Duration.ofSeconds(10))
                    .pollingEvery(Duration.ofMillis(200))
                    .ignoring(NoSuchElementException.class);
            wait.until(ExpectedConditions.invisibilityOfElementLocated(locator));
            LoggerUtil.logInfo("Element disappeared -> Key: " + elementKey);
            StepReporter.reportStepSuccess(stepDescription,
                    "'" + elementKey + "' adlı eleman kayboldu. Bekleme tamamlandı.");
        } catch (Exception e) {
            LoggerUtil.logError("Timeout or error waiting for element to disappear -> Key: " + elementKey, e);
            StepReporter.reportStepError(stepDescription,
                    "'" + elementKey + "' adlı eleman kaybolana kadar beklenirken hata oluştu.", e);
            throw e;
        }
    }
}
