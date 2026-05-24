package playwright.stepdefs;

import com.microsoft.playwright.Page;
import io.cucumber.java.After;
import io.cucumber.java.AfterStep;
import io.cucumber.java.Before;
import io.cucumber.java.Scenario;
import playwright.PlaywrightFactory;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.UUID;
import java.util.concurrent.atomic.AtomicInteger;

/**
 * Cucumber lifecycle (Playwright variant).
 *
 * Per scenario:
 *   @Before     → PlaywrightFactory.openContextAndPage() + locator JSON load
 *   @AfterStep  → step screenshot → target/test-runs/<run-id>/step-NNN_<name>.png
 *   @After      → failure screenshot (embedded in report) + closeContext()
 *
 * Directory structure (E17 fix):
 *   target/test-runs/
 *     2026-05-22_10-37_<safe-name>_<uuid>/
 *       step-001_open-url.png
 *       step-002_FAILED_click-banner.png
 *       result.json  — { passed, duration_ms, steps }
 */
public class PwHooks {

    // Thread-local run dir and step counter so parallel scenarios stay isolated.
    private static final ThreadLocal<Path> RUN_DIR = new ThreadLocal<>();
    private static final ThreadLocal<AtomicInteger> STEP_CTR = new ThreadLocal<>();
    private static final ThreadLocal<Long> START_MS = new ThreadLocal<>();

    @Before
    public void setUp(Scenario scenario) {
        PlaywrightFactory.openContextAndPage(scenario.getName());
        String featureFile;
        try {
            featureFile = scenario.getUri().toString();
        } catch (Exception ignored) {
            featureFile = scenario.getId();
        }
        String featureName = extractFeatureName(featureFile);
        PwConfigSteps.loadLocators("src/main/resources/locators", featureName);

        // Create run-level directory
        String ts = LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyy-MM-dd_HH-mm"));
        String safe = scenario.getName().replaceAll("[^A-Za-z0-9_-]", "_").replaceAll("_+", "_");
        String uid = UUID.randomUUID().toString().substring(0, 8);
        Path runDir = Paths.get("target/test-runs").resolve(ts + "_" + safe + "_" + uid);
        try { Files.createDirectories(runDir); } catch (IOException ignored) {}
        RUN_DIR.set(runDir);
        STEP_CTR.set(new AtomicInteger(0));
        START_MS.set(System.currentTimeMillis());
    }

    @AfterStep
    public void afterStep(Scenario scenario) {
        try {
            Page p = PlaywrightFactory.page();
            if (p == null) return;
            int step = STEP_CTR.get().incrementAndGet();
            Path runDir = RUN_DIR.get();
            if (runDir == null) return;
            String status = scenario.isFailed() ? "FAILED_" : "";
            String fileName = String.format("step-%03d_%s%s.png", step, status,
                    scenario.getName().replaceAll("[^A-Za-z0-9_-]", "_").substring(0, Math.min(40, scenario.getName().length())));
            Path out = runDir.resolve(fileName);
            p.screenshot(new Page.ScreenshotOptions().setPath(out));
        } catch (Exception ignored) {}
    }

    @After
    public void tearDown(Scenario scenario) {
        long durationMs = System.currentTimeMillis() - (START_MS.get() != null ? START_MS.get() : 0L);
        try {
            if (scenario.isFailed()) {
                Page p = PlaywrightFactory.page();
                if (p != null) {
                    // Attach failure screenshot to Cucumber HTML report
                    byte[] png = p.screenshot(new Page.ScreenshotOptions().setFullPage(true));
                    scenario.attach(png, "image/png", "failed:" + scenario.getName());
                    Path runDir = RUN_DIR.get();
                    if (runDir != null) {
                        Path failShot = runDir.resolve("FAILURE_fullpage.png");
                        Files.write(failShot, png);
                        scenario.log("[screenshot] " + failShot);
                    }
                }
            }
        } catch (Exception ignored) {}

        // Write result.json summary
        try {
            Path runDir = RUN_DIR.get();
            if (runDir != null) {
                int steps = STEP_CTR.get() != null ? STEP_CTR.get().get() : 0;
                String json = String.format(
                    "{\"scenario\":\"%s\",\"passed\":%b,\"duration_ms\":%d,\"steps\":%d}",
                    scenario.getName().replace("\"", "\\\""),
                    !scenario.isFailed(), durationMs, steps);
                Files.write(runDir.resolve("result.json"), json.getBytes(StandardCharsets.UTF_8));
            }
        } catch (Exception ignored) {}

        PlaywrightFactory.closeContext(scenario.getName(), scenario.isFailed());
        RUN_DIR.remove();
        STEP_CTR.remove();
        START_MS.remove();
    }

    private static String extractFeatureName(String scenarioId) {
        try {
            int slash = scenarioId.lastIndexOf('/');
            String tail = (slash >= 0) ? scenarioId.substring(slash + 1) : scenarioId;
            int dot = tail.indexOf('.');
            return (dot > 0) ? tail.substring(0, dot) : tail;
        } catch (Exception e) {
            return "default";
        }
    }
}
