package methods;

import org.openqa.selenium.By;
import org.openqa.selenium.OutputType;
import org.openqa.selenium.TakesScreenshot;
import org.openqa.selenium.WebElement;
import utilities.Driver;
import utilities.LoggerUtil;
import utilities.StepReporter;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.Map;

/**
 * ScreenshotMethods:
 * Sayfa veya element ekran görüntüsü alır.
 * Görseller proje kökündeki screenshot klasörüne kaydedilir.
 */
public class ScreenshotMethods {

    private static final DateTimeFormatter FORMAT = DateTimeFormatter.ofPattern("yyyyMMdd_HHmmss");

    private static String getScreenshotDir() {
        String dir = System.getProperty("user.dir") + "/screenshot";
        Path path = Paths.get(dir);
        if (!Files.exists(path)) {
            try {
                Files.createDirectories(path);
            } catch (IOException e) {
                throw new RuntimeException("Screenshot klasörü oluşturulamadı: " + dir, e);
            }
        }
        return dir;
    }

    /**
     * Tüm sayfanın ekran görüntüsünü alır ve kaydeder.
     *
     * @param name Dosya adı (uzantı eklenmez; zaman damgası eklenir)
     */
    public void takeScreenshot(String name) {
        String safeName = (name != null && !name.isEmpty()) ? name.replaceAll("[^a-zA-Z0-9_-]", "_") : "screenshot";
        String stepDescription = "Ekran görüntüsü alınıyor: " + safeName;
        String details = "Dosya adı: " + safeName;
        StepReporter.reportStepStart(stepDescription, details);
        LoggerUtil.logInfo("Taking screenshot -> " + safeName);
        try {
            TakesScreenshot ts = (TakesScreenshot) Driver.getDriver();
            byte[] bytes = ts.getScreenshotAs(OutputType.BYTES);
            String fileName = safeName + "_" + LocalDateTime.now().format(FORMAT) + ".png";
            Path filePath = Paths.get(getScreenshotDir(), fileName);
            try {
                Files.write(filePath, bytes);
            } catch (IOException io) {
                throw new RuntimeException("Ekran görüntüsü dosyaya yazılamadı: " + filePath, io);
            }
            LoggerUtil.logInfo("Screenshot saved -> " + filePath);
            StepReporter.reportStepSuccess(stepDescription,
                    "Ekran görüntüsü kaydedildi: " + filePath.toAbsolutePath());
        } catch (Exception e) {
            LoggerUtil.logError("Failed to take screenshot -> " + safeName, e);
            StepReporter.reportStepError(stepDescription, "Ekran görüntüsü alınamadı.", e);
            throw e;
        }
    }

    /**
     * Belirtilen elementin ekran görüntüsünü alır ve kaydeder.
     *
     * @param elementKey JSON locator key
     * @param locators   locator map
     */
    public void takeScreenshotOfElement(String elementKey, Map<String, By> locators) {
        String stepDescription = "'" + elementKey + "' adlı elemanın ekran görüntüsü alınıyor";
        String details = "Element: " + elementKey;
        StepReporter.reportStepStart(stepDescription, details);
        LoggerUtil.logInfo("Taking screenshot of element -> Key: " + elementKey);
        try {
            WebElement element = WaitMethods.waitForElement(elementKey, locators);
            byte[] bytes = element.getScreenshotAs(OutputType.BYTES);
            String safeName = elementKey.replaceAll("[^a-zA-Z0-9_-]", "_");
            String fileName = safeName + "_" + LocalDateTime.now().format(FORMAT) + ".png";
            Path filePath = Paths.get(getScreenshotDir(), fileName);
            try {
                Files.write(filePath, bytes);
            } catch (IOException io) {
                throw new RuntimeException("Element ekran görüntüsü dosyaya yazılamadı: " + filePath, io);
            }
            LoggerUtil.logInfo("Element screenshot saved -> " + filePath);
            StepReporter.reportStepSuccess(stepDescription,
                    "'" + elementKey + "' adlı elemanın ekran görüntüsü kaydedildi: " + filePath.toAbsolutePath());
        } catch (Exception e) {
            LoggerUtil.logError("Failed to take screenshot of element -> Key: " + elementKey, e);
            StepReporter.reportStepError(stepDescription,
                    "'" + elementKey + "' adlı elemanın ekran görüntüsü alınamadı.", e);
            throw e;
        }
    }
}
