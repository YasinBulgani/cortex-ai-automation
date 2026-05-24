package playwright;

import com.microsoft.playwright.Browser;

import java.util.HashMap;
import java.util.Map;

/**
 * Device emulation presets (E25 fix — Mobile Testing).
 *
 * Playwright Java does not expose the {@code playwright.devices()} map cleanly
 * the way Node.js does, so we hardcode the most useful presets here. Each
 * preset captures viewport, deviceScaleFactor, userAgent, touch support, and
 * the {@code isMobile} flag (which affects layout-affecting media queries).
 *
 * Usage:
 *   Browser.NewContextOptions opts = DevicePresets.applyTo(
 *       new Browser.NewContextOptions(),
 *       "iPhone 14");
 */
public final class DevicePresets {

    public record Device(
            String name,
            int viewportWidth,
            int viewportHeight,
            double deviceScaleFactor,
            String userAgent,
            boolean isMobile,
            boolean hasTouch
    ) {}

    private static final Map<String, Device> REGISTRY = new HashMap<>();
    static {
        String UA_IOS = "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 "
                + "(KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1";
        String UA_IPAD = "Mozilla/5.0 (iPad; CPU OS 16_0 like Mac OS X) AppleWebKit/605.1.15 "
                + "(KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1";
        String UA_ANDROID = "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 "
                + "(KHTML, like Gecko) Chrome/127.0.0.0 Mobile Safari/537.36";
        String UA_DESKTOP = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                + "(KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36";

        // Desktop variants
        register(new Device("Desktop",      1440, 900,  1.0, UA_DESKTOP, false, false), "desktop");
        register(new Device("Laptop",       1366, 768,  1.0, UA_DESKTOP, false, false), "laptop");
        register(new Device("Desktop FHD",  1920, 1080, 1.0, UA_DESKTOP, false, false), "desktop-fhd");
        register(new Device("Desktop 4K",   3840, 2160, 2.0, UA_DESKTOP, false, false), "desktop-4k");

        // iPhone — multiple model versions sharing similar dimensions
        register(new Device("iPhone 13",         390, 844, 3.0, UA_IOS, true, true), "iphone-13");
        register(new Device("iPhone 14",         390, 844, 3.0, UA_IOS, true, true), "iphone-14");
        register(new Device("iPhone 14 Pro",     393, 852, 3.0, UA_IOS, true, true), "iphone-14-pro");
        register(new Device("iPhone 14 Pro Max", 430, 932, 3.0, UA_IOS, true, true), "iphone-14-pro-max");
        register(new Device("iPhone SE",         375, 667, 2.0, UA_IOS, true, true), "iphone-se");

        // Android phones
        register(new Device("Pixel 7",     412, 915, 2.625, UA_ANDROID, true, true), "pixel-7");
        register(new Device("Pixel 8",     412, 915, 2.625, UA_ANDROID, true, true), "pixel-8");
        register(new Device("Galaxy S22",  360, 780, 3.0,   UA_ANDROID, true, true), "galaxy-s22");
        register(new Device("Galaxy S23",  360, 780, 3.0,   UA_ANDROID, true, true), "galaxy-s23");
        register(new Device("Galaxy Fold", 280, 653, 3.0,   UA_ANDROID, true, true), "galaxy-fold");

        // Tablets
        register(new Device("iPad Mini",     768, 1024, 2.0, UA_IPAD, true, true), "ipad-mini");
        register(new Device("iPad Pro 11",   834, 1194, 2.0, UA_IPAD, true, true), "ipad-pro-11");
        register(new Device("iPad Pro 12.9", 1024, 1366, 2.0, UA_IPAD, true, true), "ipad-pro-12-9");
    }

    private static void register(Device d, String... aliases) {
        REGISTRY.put(d.name(), d);
        REGISTRY.put(d.name().toLowerCase().replace(" ", "-"), d);
        for (String a : aliases) REGISTRY.put(a, d);
    }

    /** Lookup a device by name or slug. Returns null if unknown. */
    public static Device lookup(String name) {
        if (name == null || name.isBlank()) return null;
        Device d = REGISTRY.get(name);
        if (d != null) return d;
        return REGISTRY.get(name.toLowerCase().replace(" ", "-"));
    }

    /** Apply device settings to a NewContextOptions. Returns the same instance. */
    public static Browser.NewContextOptions applyTo(Browser.NewContextOptions opts, String deviceName) {
        Device d = lookup(deviceName);
        if (d == null) return opts;
        return opts
                .setViewportSize(d.viewportWidth(), d.viewportHeight())
                .setDeviceScaleFactor(d.deviceScaleFactor())
                .setUserAgent(d.userAgent())
                .setIsMobile(d.isMobile())
                .setHasTouch(d.hasTouch());
    }

    /** Available device names (for the dashboard dropdown). */
    public static String[] availableNames() {
        return new String[]{
                "Desktop", "Laptop", "Desktop FHD", "Desktop 4K",
                "iPhone 13", "iPhone 14", "iPhone 14 Pro", "iPhone 14 Pro Max", "iPhone SE",
                "Pixel 7", "Pixel 8", "Galaxy S22", "Galaxy S23", "Galaxy Fold",
                "iPad Mini", "iPad Pro 11", "iPad Pro 12.9"
        };
    }

    private DevicePresets() {}
}
