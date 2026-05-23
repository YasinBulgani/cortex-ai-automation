package playwright;

import com.microsoft.playwright.Browser;
import com.microsoft.playwright.BrowserContext;
import com.microsoft.playwright.BrowserType;
import com.microsoft.playwright.Page;
import com.microsoft.playwright.Playwright;
import com.microsoft.playwright.Tracing;

import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;

/**
 * Thread-local Playwright / Browser / Context / Page holder.
 *
 * The Cucumber JUnit Platform parallel runner runs each scenario on a
 * separate thread; each thread keeps its own Playwright instance and
 * browser context.
 *
 * Lifecycle:
 *   - Playwright + Browser are created lazily, once per thread (expensive resources)
 *   - BrowserContext + Page are re-created per scenario (@Before / @After)
 *
 * A JVM shutdown hook closes every per-thread resource on exit.
 */
public final class PlaywrightFactory {

    private static final ThreadLocal<Playwright>   PW       = new ThreadLocal<>();
    private static final ThreadLocal<Browser>      BROWSER  = new ThreadLocal<>();
    private static final ThreadLocal<BrowserContext> CTX    = new ThreadLocal<>();
    private static final ThreadLocal<Page>         PAGE     = new ThreadLocal<>();

    private static final ConcurrentHashMap<Long, Playwright> ALL_PW = new ConcurrentHashMap<>();
    private static final ConcurrentHashMap<Long, Browser>    ALL_BR = new ConcurrentHashMap<>();
    private static final AtomicLong scenarioCounter = new AtomicLong();

    static {
        Runtime.getRuntime().addShutdownHook(new Thread(PlaywrightFactory::shutdownAll, "pw-shutdown"));
    }

    private PlaywrightFactory() {}

    /* ============================================================ */
    /*  Thread-bound accessors                                       */
    /* ============================================================ */

    public static Page page() {
        Page p = PAGE.get();
        if (p == null) throw new IllegalStateException("PlaywrightFactory: page() was not opened. Did PwHooks @Before run?");
        return p;
    }

    public static BrowserContext context() {
        return CTX.get();
    }

    /** Switch the active page (e.g. after opening a new tab/window). */
    public static void setActivePage(Page page) {
        if (page == null) throw new IllegalArgumentException("page cannot be null");
        PAGE.set(page);
    }

    /* ============================================================ */
    /*  Scenario lifecycle                                           */
    /* ============================================================ */

    public static void openContextAndPage(String scenarioName) {
        // 1) per-thread Playwright + Browser (lazy, once)
        Playwright pw = PW.get();
        if (pw == null) {
            pw = Playwright.create();
            PW.set(pw);
            ALL_PW.put(Thread.currentThread().getId(), pw);
        }
        Browser br = BROWSER.get();
        if (br == null) {
            BrowserType bt = switch (PlaywrightConfig.browser()) {
                case "firefox" -> pw.firefox();
                case "webkit"  -> pw.webkit();
                default        -> pw.chromium();
            };
            br = bt.launch(new BrowserType.LaunchOptions()
                    .setHeadless(PlaywrightConfig.headless())
                    .setSlowMo(PlaywrightConfig.slowMo()));
            BROWSER.set(br);
            ALL_BR.put(Thread.currentThread().getId(), br);
        }

        // 2) per-scenario context + page
        Browser.NewContextOptions opts = new Browser.NewContextOptions()
                .setViewportSize(PlaywrightConfig.viewportWidth(), PlaywrightConfig.viewportHeight())
                .setLocale("tr-TR");

        // E25 fix — Mobile device emulation
        // If -Dplaywright.device=<name> is set, override viewport + apply
        // userAgent, deviceScaleFactor, isMobile, hasTouch from DevicePresets.
        String deviceName = PlaywrightConfig.device();
        if (!deviceName.isBlank()) {
            DevicePresets.Device dev = DevicePresets.lookup(deviceName);
            if (dev != null) {
                DevicePresets.applyTo(opts, deviceName);
                System.out.println("[PlaywrightFactory] Device emulation active: "
                        + dev.name() + " (" + dev.viewportWidth() + "x" + dev.viewportHeight()
                        + ", DPR=" + dev.deviceScaleFactor()
                        + ", mobile=" + dev.isMobile() + ")");
            } else {
                System.err.println("[PlaywrightFactory] Unknown device: '" + deviceName
                        + "' — falling back to desktop viewport. "
                        + "Use one of: " + String.join(", ", DevicePresets.availableNames()));
            }
        }

        if (PlaywrightConfig.videoEnabled()) {
            opts.setRecordVideoDir(Paths.get("target/playwright-videos"));
        }

        // E22: Load storage state (cookies + localStorage) if a saved file exists.
        // The recorder saves state after recording; subsequent runs reuse it to skip login.
        // Storage file location: recordings/<feature-name>/storage-state.json
        // Sensitivity: this file is git-ignored — do NOT commit session tokens.
        Path storageState = resolveStorageState(scenarioName);
        if (storageState != null) {
            opts.setStorageStatePath(storageState);
        }

        BrowserContext ctx = br.newContext(opts);
        ctx.setDefaultTimeout(PlaywrightConfig.defaultTimeoutMs());

        if (PlaywrightConfig.traceEnabled()) {
            ctx.tracing().start(new Tracing.StartOptions()
                    .setScreenshots(true)
                    .setSnapshots(true)
                    .setSources(false)
                    .setTitle(scenarioName));
        }

        Page page = ctx.newPage();
        CTX.set(ctx);
        PAGE.set(page);
    }

    public static void closeContext(String scenarioName, boolean failed) {
        Page page = PAGE.get();
        BrowserContext ctx = CTX.get();
        try {
            if (PlaywrightConfig.traceEnabled() && ctx != null) {
                long id = scenarioCounter.incrementAndGet();
                String safe = scenarioName == null ? "scenario" : scenarioName.replaceAll("[^A-Za-z0-9-_.]", "_");
                Path trace = Paths.get("target/playwright-traces/" + id + "_" + safe + ".zip");
                trace.getParent().toFile().mkdirs();
                ctx.tracing().stop(new Tracing.StopOptions().setPath(trace));
            }
        } catch (Exception ignored) {}
        try { if (page != null) page.close(); } catch (Exception ignored) {}
        try { if (ctx  != null) ctx.close();  } catch (Exception ignored) {}
        PAGE.remove();
        CTX.remove();
    }

    /**
     * E22: Find a storage-state.json for this scenario.
     * Looks for: recordings/<safe-scenario-name>/storage-state.json
     * Returns null if not found (so context is created without pre-loaded state).
     */
    private static Path resolveStorageState(String scenarioName) {
        if (scenarioName == null) return null;
        String safe = scenarioName.replaceAll("[^A-Za-z0-9_-]", "_").toLowerCase();
        Path candidate = Paths.get("recordings").resolve(safe).resolve("storage-state.json");
        if (Files.exists(candidate)) return candidate;
        // Also check generic "shared" storage state for suite-level pre-login
        Path shared = Paths.get("recordings/shared-storage-state.json");
        if (Files.exists(shared)) return shared;
        return null;
    }

    private static void shutdownAll() {
        ALL_BR.values().forEach(b -> { try { b.close(); } catch (Exception ignored) {} });
        ALL_PW.values().forEach(p -> { try { p.close(); } catch (Exception ignored) {} });
        ALL_BR.clear();
        ALL_PW.clear();
    }
}
