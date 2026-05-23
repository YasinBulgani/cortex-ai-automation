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
        // Desktop (default — no emulation)
        register(new Device("Desktop", 1440, 900, 1.0,
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                + "(KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
                false, false));

        // iPhone family
        register(new Device("iPhone 14", 390, 844, 3.0,
                "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 "
                + "(KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
                true, true));
        register(new Device("iPhone SE", 375, 667, 2.0,
                "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 "
                + "(KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1",
                true, true));
        register(new Device("iPhone 14 Pro Max", 430, 932, 3.0,
                "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 "
                + "(KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
                true, true));

        // Android family
        register(new Device("Pixel 7", 412, 915, 2.625,
                "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 "
                + "(KHTML, like Gecko) Chrome/127.0.0.0 Mobile Safari/537.36",
                true, true));
        register(new Device("Galaxy S22", 360, 780, 3.0,
                "Mozilla/5.0 (Linux; Android 13; SM-S901B) AppleWebKit/537.36 "
                + "(KHTML, like Gecko) Chrome/127.0.0.0 Mobile Safari/537.36",
                true, true));

        // Tablets
        register(new Device("iPad Pro 11", 834, 1194, 2.0,
                "Mozilla/5.0 (iPad; CPU OS 16_0 like Mac OS X) AppleWebKit/605.1.15 "
                + "(KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
                true, true));
        register(new Device("iPad Pro 12.9", 1024, 1366, 2.0,
                "Mozilla/5.0 (iPad; CPU OS 16_0 like Mac OS X) AppleWebKit/605.1.15 "
                + "(KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
                true, true));
    }

    private static void register(Device d) {
        REGISTRY.put(d.name().toLowerCase().replace(" ", "-"), d);
        REGISTRY.put(d.name(), d);  // also lookup by original case
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
                "Desktop", "iPhone 14", "iPhone SE", "iPhone 14 Pro Max",
                "Pixel 7", "Galaxy S22", "iPad Pro 11", "iPad Pro 12.9"
        };
    }

    private DevicePresets() {}
}
