package utilities;

import com.google.gson.Gson;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.Map;

/**
 * DataReader:
 * Test verilerini JSON dosyasından okur.
 * Domain ve ortam bazlı okuma desteği vardır.
 * Format: {domain}-{env}-data.json (örn: plus-test-data.json, girit-prod-data.json)
 * Basit key-value yapısı kullanır.
 */
public class DataReader {

    private static JsonObject data;

    static {
        loadData();
    }

    /**
     * Domain ve ortam bilgisini config'den alır.
     * İlgili data dosyasını yükler ({domain}-{env}-data.json formatında).
     */
    private static void loadData() {
        try {
            // Domain bilgisini al (system property veya config'den)
            String domain = System.getProperty("data.domain");
            if (domain == null || domain.isBlank()) {
                String configDomain = ConfigReader.get("data.domain");
                if (configDomain != null && !configDomain.isBlank()) {
                    domain = configDomain;
                }
            }
            // Eğer hala null ise varsayılan olarak "girit" kullan
            if (domain == null || domain.isBlank()) {
                domain = "girit";
            }

            // Ortam bilgisini al (system property veya config'den)
            String environment = System.getProperty("data.env");
            if (environment == null || environment.isBlank()) {
                String configEnv = ConfigReader.get("data.env");
                if (configEnv != null && !configEnv.isBlank()) {
                    environment = configEnv;
                }
            }
            // Eğer hala null ise varsayılan olarak "test" kullan
            if (environment == null || environment.isBlank()) {
                environment = "test";
            }

            // Ortak dosya adı: common-{env}-data.json
            String commonFileName = "common-" + environment + "-data.json";
            String commonPath = "src/test/resources/data/" + commonFileName;

            // Domain/ortam dosya adı: {domain}-{env}-data.json
            String fileName = domain + "-" + environment + "-data.json";
            String path = "src/test/resources/data/" + fileName;

            Path commonFilePath = Paths.get(commonPath);
            Path filePath = Paths.get(path);

            if (!Files.exists(filePath)) {
                throw new RuntimeException("Data dosyası bulunamadı: " + path +
                        " (Domain: " + domain + ", Ortam: " + environment + ")");
            }

            Gson gson = new Gson();
            JsonObject mergedData = new JsonObject();

            // 1) Domain/ortam dosyasını yükle
            String jsonContent = Files.readString(filePath);
            JsonObject domainData = gson.fromJson(jsonContent, JsonObject.class);
            if (domainData != null) {
                for (Map.Entry<String, JsonElement> entry : domainData.entrySet()) {
                    mergedData.add(entry.getKey(), entry.getValue());
                }
            }

            // 2) Ortak ortam dosyasını yükle (varsa) ve domain verilerinin üzerine yaz
            if (Files.exists(commonFilePath)) {
                String commonJsonContent = Files.readString(commonFilePath);
                JsonObject commonData = gson.fromJson(commonJsonContent, JsonObject.class);
                if (commonData != null) {
                    for (Map.Entry<String, JsonElement> entry : commonData.entrySet()) {
                        mergedData.add(entry.getKey(), entry.getValue());
                    }
                    LoggerUtil.logInfo("Ortak data dosyası yüklendi: " + commonFileName +
                            " (Ortam: " + environment + ")");
                }
            }

            data = mergedData;

            LoggerUtil.logInfo("Data dosyası yüklendi: " + fileName + " (Domain: " + domain + ", Ortam: " + environment + ")");
        } catch (IOException e) {
            throw new RuntimeException("Data dosyası okunamadı", e);
        }
    }

    /**
     * Yeni domain/ortam için veriyi yeniden yükler.
     * Çoklu domain çalıştırmasında her domain öncesi çağrılmalı.
     */
    public static void reloadForNewDomain(String domain, String environment) {
        System.setProperty("data.domain", domain);
        System.setProperty("data.env", environment);
        loadData();
    }

    /**
     * JSON dosyasından key'e göre değer döner.
     *
     * @param key JSON dosyasındaki anahtar
     * @return key'e karşılık gelen değer
     */
    public static String get(String key) {
        if (data == null || !data.has(key)) {
            throw new RuntimeException("Data dosyasında '" + key + "' anahtarı bulunamadı");
        }
        return data.get(key).getAsString();
    }
}
