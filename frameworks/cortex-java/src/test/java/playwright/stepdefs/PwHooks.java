package playwright.stepdefs;

import com.microsoft.playwright.Page;
import io.cucumber.java.After;
import io.cucumber.java.Before;
import io.cucumber.java.Scenario;
import playwright.PlaywrightFactory;

import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;

/**
 * Cucumber lifecycle (Playwright variant).
 *
 * Per scenario:
 *   @Before -> PlaywrightFactory.openContextAndPage()
 *              + load locator JSON (matched by feature name)
 *   @After  -> on failure: screenshot; then closeContext()
 */
public class PwHooks {

    @Before
    public void setUp(Scenario scenario) {
        PlaywrightFactory.openContextAndPage(scenario.getName());
        String featureFile = scenario.getId();      // .../cortex/login.feature:5
        String featureName = extractFeatureName(featureFile);
        PwConfigSteps.loadLocators("src/main/resources/locators", featureName);
    }

    @After
    public void tearDown(Scenario scenario) {
        try {
            if (scenario.isFailed()) {
                Page p = PlaywrightFactory.page();
                String ts = LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyyMMdd_HHmmss"));
                String safe = scenario.getName().replaceAll("[^A-Za-z0-9-_.]", "_");
                Path out = Paths.get("screenshots/playwright").resolve(safe + "_" + ts + ".png");
                Files.createDirectories(out.getParent());
                byte[] png = p.screenshot(new Page.ScreenshotOptions().setPath(out).setFullPage(true));
                scenario.attach(png, "image/png", "failed:" + scenario.getName());
            }
        } catch (Exception ignored) {}
        PlaywrightFactory.closeContext(scenario.getName(), scenario.isFailed());
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
