package utilities;

import org.openqa.selenium.By;
import java.util.Map;

/**
 * LocatorManager
 *
 * Bu class, JSON dosyalarından okunan locator bilgilerini
 * test boyunca hafızada (cache) tutar.
 *
 * Amaç:
 * - JsonReader her step'te tekrar çalışmasın
 * - Locator'lar merkezi bir noktadan yönetilsin
 *
 * Bu bir Step class DEĞİLDİR.
 * Framework altyapısının bir parçasıdır.
 */
public class LocatorManager {

    /**
     * JSON dosyalarından okunan tüm locator'lar burada tutulur.
     * Static tanımlanmasının sebebi:
     * - Tüm testler boyunca tek bir instance kullanmak
     */
    private static Map<String, By> locators;

    /**
     * Locator map'ini döner.
     *
     * Step Definition ve Methods class'ları
     * bu metodu kullanarak locator'lara erişir.
     *
     * @return Map<String, By> locator listesi
     */
    public static Map<String, By> getLocators() {

        // Eğer locator'lar yüklenmediyse test durdurulur
        if (locators == null) {
            throw new RuntimeException(
                    "Locators not loaded! " +
                            "loadLocators() methodu testten önce çağrılmalıdır."
            );
        }
        return locators;
    }

    /**
     * JSON locator dosyalarını yükler.
     *
     * Bu method:
     * - Test başlamadan önce
     * - SADECE 1 KERE
     * çağrılmalıdır.
     *
     * @param directoryPath locator JSON dosyalarının bulunduğu klasör
     * @param featureName   çalıştırılan feature ismi
     */
    public static void loadLocators(String directoryPath, String featureName) {

        // JsonReader aracılığıyla locator'ları oku
        locators = JsonReader.readLocators(directoryPath, featureName);

        // Okunan locator'lar boşsa test fail edilir
        if (locators == null || locators.isEmpty()) {
            throw new RuntimeException(
                    "Locators map is empty! " +
                            "JSON dosyalarını kontrol et: " + directoryPath
            );
        }
    }
}
