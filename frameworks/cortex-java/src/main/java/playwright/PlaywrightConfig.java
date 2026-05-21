package playwright;

import config.ConfigManager;

/**
 * Configuration wrapper for the Playwright runner.
 * Values resolve via -D / env / config.properties (in that order).
 */
public final class PlaywrightConfig {

    public static String baseUrl() {
        return ConfigManager.getProperty("cortex.url",
               ConfigManager.getProperty("base.url",
               "https://cortex-test.bgtsai.com/"));
    }

    public static String browser() {
        return ConfigManager.getProperty("playwright.browser", "chromium");
    }

    public static boolean headless() {
        return ConfigManager.getBoolean("playwright.headless", false);
    }

    public static int slowMo() {
        return ConfigManager.getInt("playwright.slow.mo", 0);
    }

    public static int viewportWidth() {
        return ConfigManager.getInt("playwright.viewport.width", 1440);
    }

    public static int viewportHeight() {
        return ConfigManager.getInt("playwright.viewport.height", 900);
    }

    public static int defaultTimeoutMs() {
        return ConfigManager.getInt("playwright.timeout.ms", 15000);
    }

    public static boolean videoEnabled() {
        return ConfigManager.getBoolean("playwright.video", false);
    }

    public static boolean traceEnabled() {
        return ConfigManager.getBoolean("playwright.trace", false);
    }

    private PlaywrightConfig() {}
}
