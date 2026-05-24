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

    /**
     * Device emulation preset name (E25 fix — Mobile Testing).
     * One of: "Desktop" (default), "iPhone 14", "iPhone SE", "iPhone 14 Pro Max",
     *         "Pixel 7", "Galaxy S22", "iPad Pro 11", "iPad Pro 12.9".
     *
     * When set to anything other than "Desktop"/"none"/empty, PlaywrightFactory
     * applies viewport + userAgent + deviceScaleFactor + isMobile + hasTouch
     * from {@link DevicePresets}, overriding viewport.width / viewport.height.
     */
    public static String device() {
        String d = ConfigManager.getProperty("playwright.device", "");
        return (d == null || d.isBlank() || "none".equalsIgnoreCase(d)) ? "" : d;
    }

    /** True when device() is set to a real mobile/tablet preset. */
    public static boolean isMobileEmulation() {
        String d = device();
        return !d.isBlank() && !"Desktop".equalsIgnoreCase(d);
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
