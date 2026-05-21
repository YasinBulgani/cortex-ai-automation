package methods;

import utilities.ConfigReader;
import utilities.Driver;
import utilities.LoggerUtil;
import utilities.StepReporter;

/**
 * NavigationMethods:
 * Sayfalar arası yönlendirme / URL açma işlemlerini merkezi yönetir.
 */
public class NavigationMethods {

    /**
     * Domain ve ortam bilgisine göre otomatik olarak URL'i alır ve sayfayı açar.
     * Config'deki data.domain ve data.env değerlerine göre ilgili URL'i okur.
     * Format: url.{domain}.{env} (örn: url.plus.test, url.girit.prod)
     *
     * Feature kullanımı:
     * Given I open the application url from config "url"
     * 
     * Not: "url" key'i özel bir key'dir ve domain+env kombinasyonu ile otomatik okunur.
     * Diğer config key'leri için normal get() metodu kullanılır.
     *
     * @param configKey config.properties içindeki anahtar (örn: "url")
     */
    public void openUrlFromConfig(String configKey) {

        String stepDescription = "Uygulama açılıyor (Config'den: " + configKey + ")";
        String details = "Config anahtarı: " + configKey;
        
        StepReporter.reportStepStart(stepDescription, details);

        LoggerUtil.logInfo("Opening URL from config -> Key: " + configKey);

        try {
            String url;
            
            // "url" key'i özel bir key'dir, domain+env kombinasyonu ile okunur
            if ("url".equals(configKey)) {
                url = ConfigReader.getUrl();
            } else {
                // Diğer key'ler için normal okuma
                url = ConfigReader.get(configKey);
                if (url == null || url.isBlank()) {
                    throw new RuntimeException(
                            "Config value is empty or null for key: " + configKey
                    );
                }
            }

            Driver.getDriver().get(url);

            LoggerUtil.logInfo(
                    "Successfully opened URL from config -> " + url
            );

            StepReporter.reportStepSuccess(stepDescription, 
                "Uygulama başarıyla açıldı. Config'den '" + configKey + "' anahtarı kullanıldı.");

        } catch (Exception e) {
            LoggerUtil.logError(
                    "Failed to open URL from config -> Key: " + configKey,
                    e
            );
            
            StepReporter.reportStepError(stepDescription, 
                "Uygulama açılamadı. Config dosyasında '" + configKey + "' anahtarı bulunamadı veya URL geçersiz.", e);
            
            // Test fail etsin diye hatayı yukarı fırlatıyoruz
            throw e;
        }
    }

    /**
     * Verilen URL'i direkt açar (config kullanmak istemezsen).
     *
     * @param url açılacak URL
     */
    public void openUrl(String url) {

        String stepDescription = StepReporter.createUserFriendlyDescription("navigasyon", "URL", url);
        String details = "Açılacak URL: " + url;
        
        StepReporter.reportStepStart(stepDescription, details);

        LoggerUtil.logInfo("Opening URL -> " + url);

        try {
            if (url == null || url.isBlank()) {
                throw new RuntimeException("URL is empty or null!");
            }

            Driver.getDriver().get(url);

            LoggerUtil.logInfo(
                    "Successfully opened URL -> " + url
            );

            StepReporter.reportStepSuccess(stepDescription, 
                "URL başarıyla açıldı: " + url);

        } catch (Exception e) {
            LoggerUtil.logError(
                    "Failed to open URL -> " + url,
                    e
            );
            
            StepReporter.reportStepError(stepDescription, 
                "URL açılamadı: " + url + ". Geçersiz URL veya bağlantı hatası.", e);
            
            // Test fail etsin
            throw e;
        }
    }

    /**
     * Tarayıcıda geri butonuna basar (önceki sayfaya döner).
     */
    public void goBack() {
        String stepDescription = "Tarayıcıda geri gidiliyor";
        String details = "Önceki sayfaya dönülüyor";
        StepReporter.reportStepStart(stepDescription, details);
        LoggerUtil.logInfo("Navigating back");
        try {
            Driver.getDriver().navigate().back();
            LoggerUtil.logInfo("Navigated back successfully");
            StepReporter.reportStepSuccess(stepDescription, "Önceki sayfaya başarıyla dönüldü.");
        } catch (Exception e) {
            LoggerUtil.logError("Failed to navigate back", e);
            StepReporter.reportStepError(stepDescription, "Geri gidilemedi.", e);
            throw e;
        }
    }

    /**
     * Tarayıcıda ileri butonuna basar.
     */
    public void goForward() {
        String stepDescription = "Tarayıcıda ileri gidiliyor";
        String details = "Sonraki sayfaya gidiliyor";
        StepReporter.reportStepStart(stepDescription, details);
        LoggerUtil.logInfo("Navigating forward");
        try {
            Driver.getDriver().navigate().forward();
            LoggerUtil.logInfo("Navigated forward successfully");
            StepReporter.reportStepSuccess(stepDescription, "İleri sayfaya başarıyla gidildi.");
        } catch (Exception e) {
            LoggerUtil.logError("Failed to navigate forward", e);
            StepReporter.reportStepError(stepDescription, "İleri gidilemedi.", e);
            throw e;
        }
    }

    /**
     * Mevcut sayfayı yeniler.
     */
    public void refreshPage() {
        String stepDescription = "Sayfa yenileniyor";
        String details = "Mevcut sayfa yenileniyor";
        StepReporter.reportStepStart(stepDescription, details);
        LoggerUtil.logInfo("Refreshing page");
        try {
            Driver.getDriver().navigate().refresh();
            LoggerUtil.logInfo("Page refreshed successfully");
            StepReporter.reportStepSuccess(stepDescription, "Sayfa başarıyla yenilendi.");
        } catch (Exception e) {
            LoggerUtil.logError("Failed to refresh page", e);
            StepReporter.reportStepError(stepDescription, "Sayfa yenilenemedi.", e);
            throw e;
        }
    }
}
