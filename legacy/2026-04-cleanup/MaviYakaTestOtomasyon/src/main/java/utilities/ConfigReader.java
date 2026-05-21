package utilities;

import java.io.FileInputStream;
import java.io.IOException;
import java.util.Properties;

public class ConfigReader {

    private static Properties properties;

    static {
        try {
            String path = "src/test/resources/config.properties";
            FileInputStream input = new FileInputStream(path);

            properties = new Properties();
            properties.load(input);

            input.close();
        } catch (IOException e) {
            throw new RuntimeException("config.properties dosyası okunamadı");
        }
    }

    public static String get(String key) {
        return properties.getProperty(key);
    }

    /**
     * Domain ve ortam bilgisine göre URL'i döner.
     * Format: url.{domain}.{env} (örn: url.plus.test, url.girit.prod)
     * 
     * @return domain ve ortam bazlı URL
     */
    public static String getUrl() {
        // Domain bilgisini al
        String domain = System.getProperty("data.domain");
        if (domain == null || domain.isBlank()) {
            String configDomain = get("data.domain");
            if (configDomain != null && !configDomain.isBlank()) {
                domain = configDomain;
            }
        }
        if (domain == null || domain.isBlank()) {
            domain = "girit";
        }

        // Ortam bilgisini al
        String environment = System.getProperty("data.env");
        if (environment == null || environment.isBlank()) {
            String configEnv = get("data.env");
            if (configEnv != null && !configEnv.isBlank()) {
                environment = configEnv;
            }
        }
        if (environment == null || environment.isBlank()) {
            environment = "test";
        }

        // URL key'i: url.{domain}.{env}
        String urlKey = "url." + domain + "." + environment;
        String url = get(urlKey);

        if (url == null || url.isBlank()) {
            throw new RuntimeException(
                "URL bulunamadı. Config'de '" + urlKey + "' anahtarı tanımlı değil. " +
                "(Domain: " + domain + ", Ortam: " + environment + ")"
            );
        }

        LoggerUtil.logInfo("URL okundu: " + url + " (Domain: " + domain + ", Ortam: " + environment + ")");
        return url;
    }
}
