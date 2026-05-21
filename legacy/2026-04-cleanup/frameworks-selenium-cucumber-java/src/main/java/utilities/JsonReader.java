package utilities;

import com.google.gson.Gson;
import com.google.gson.reflect.TypeToken;
import org.openqa.selenium.By;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.*;

/**
 * JsonReader:
 * JSON formatında tutulan locator dosyalarını okuyarak
 * Selenium'un anlayacağı Map<String, By> yapısına dönüştürür.
 *
 * Bu class framework altyapısının bir parçasıdır.
 */
public class JsonReader {

    /**
     * Ortak locator dosyaları + feature'a özel locator dosyasını okur
     * ve hepsini tek bir Map içinde birleştirir.
     *
     * @param directoryPath locator json dosyalarının bulunduğu klasör
     * @param featureName   çalıştırılan feature ismi
     * @return Map<String, By> locator map'i
     */
    public static Map<String, By> readLocators(String directoryPath, String featureName) {

        Map<String, By> locatorMap = new HashMap<>();
        LoggerUtil.logInfo("Reading locators for feature: " + featureName);

        String commonLocatorConfig = ConfigReader.getCommonLocators();
        List<String> commonFiles = Arrays.stream(commonLocatorConfig.split(","))
                .map(String::trim)
                .filter(s -> !s.isEmpty())
                .collect(java.util.stream.Collectors.toList());

        for (String fileName : commonFiles) {
            Path filePath = Paths.get(directoryPath, fileName);
            loadJsonFile(filePath, locatorMap);
        }

        // Feature'a özel locator dosyası
        Path featureFilePath = Paths.get(directoryPath, featureName + ".json");
        loadJsonFile(featureFilePath, locatorMap);

        LoggerUtil.logInfo("Total locator count: " + locatorMap.size());
        return locatorMap;
    }

    /**
     * Tek bir JSON dosyasını okuyarak locator map'ine ekler.
     */
    private static void loadJsonFile(Path filePath, Map<String, By> locatorMap) {

        if (!Files.exists(filePath)) {
            LoggerUtil.logInfo("Locator file not found: " + filePath.getFileName());
            return;
        }

        try {
            LoggerUtil.logInfo("Loading locator file: " + filePath.getFileName());

            String jsonContent = Files.readString(filePath);

            List<Map<String, String>> rawLocators =
                    new Gson().fromJson(jsonContent,
                            new TypeToken<List<Map<String, String>>>() {}.getType());

            if (rawLocators == null) {
                LoggerUtil.logError("Locator file is empty or invalid JSON array: " + filePath.getFileName(), null);
                return;
            }

            for (Map<String, String> locator : rawLocators) {
                if (locator == null) {
                    LoggerUtil.logError("Skipping null locator entry in " + filePath.getFileName(), null);
                    continue;
                }
                String key = locator.get("key");
                String type = locator.get("type");
                String value = locator.get("value");

                if (key != null && type != null && value != null) {
                    locatorMap.put(key, createBy(type, value));
                } else {
                    LoggerUtil.logError("Invalid locator entry in " + filePath.getFileName(), null);
                }
            }

        } catch (IOException e) {
            LoggerUtil.logError("Failed to read locator file: " + filePath.getFileName(), e);
            throw new RuntimeException(e);
        }
    }

    /**
     * Locator tipine göre Selenium By nesnesi oluşturur.
     */
    private static By createBy(String type, String value) {

        switch (type.toLowerCase()) {
            case "id":
                return By.id(value);
            case "name":
                return By.name(value);
            case "xpath":
                return By.xpath(value);
            case "css":
                return By.cssSelector(value);
            case "class":
                // Selenium By.className() bileşik sınıf kabul etmez (boşluklu değer).
                // Birden fazla sınıf varsa CSS selector kullan: ".class1.class2.class3"
                if (value != null && value.contains(" ")) {
                    String cssClasses = "." + String.join(".", value.trim().split("\\s+"));
                    return By.cssSelector(cssClasses);
                }
                return By.className(value);
            case "tag":
                return By.tagName(value);
            case "linktext":
                return By.linkText(value);
            case "partiallinktext":
                return By.partialLinkText(value);
            default:
                throw new IllegalArgumentException("Unsupported locator type: " + type);
        }
    }
}
