package playwright.stepdefs;

import playwright.PwLocatorReader;

import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Per-thread locator map for parallel runs. Each thread keeps its own
 * scenario's locators isolated from other threads.
 */
public class PwConfigSteps {

    private static final ThreadLocal<Map<String, String>> LOCATORS = new ThreadLocal<>();

    public static Map<String, String> getLocators() {
        Map<String, String> m = LOCATORS.get();
        if (m == null) {
            m = new ConcurrentHashMap<>();
            LOCATORS.set(m);
        }
        return m;
    }

    public static void loadLocators(String dir, String featureName) {
        Map<String, String> map = PwLocatorReader.read(dir, featureName);
        LOCATORS.set(map);
    }

    public static void clear() {
        LOCATORS.remove();
    }
}
