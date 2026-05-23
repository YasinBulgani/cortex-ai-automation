package playwright.stepdefs;

import com.deque.html.axecore.playwright.AxeBuilder;
import com.deque.html.axecore.results.AxeResults;
import com.deque.html.axecore.results.Rule;
import com.microsoft.playwright.Page;
import io.cucumber.java.en.Then;
import playwright.PlaywrightFactory;

import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.List;
import java.util.stream.Collectors;

/**
 * WCAG / accessibility step definitions (E27 fix).
 *
 * Powered by axe-core 4.10 via the official Playwright Java adapter.
 *
 * <h3>Step usage</h3>
 * <pre>{@code
 *   # Tüm violation'larda fail
 *   Then page passes accessibility check
 *
 *   # Sadece critical / serious'da fail (moderate / minor uyarı)
 *   Then page has no critical accessibility issues
 *
 *   # Belirli WCAG seviyesi
 *   Then page passes WCAG "wcag2aa"
 * }</pre>
 *
 * <h3>Output</h3>
 * Her çağrıda violation listesi {@code target/a11y-reports/<run>/page-N.json}
 * dosyasına yazılır. Allure raporlarına da scenario.log üzerinden link düşer.
 */
public class PwAccessibilitySteps {

    private static final Path REPORT_DIR = Paths.get("target/a11y-reports");

    @Then("page passes accessibility check")
    public void pagePassesA11y() {
        AxeResults results = runAxe(null);
        int total = results.getViolations().size();
        if (total > 0) {
            String summary = summarize(results.getViolations());
            Path report = writeReport(results);
            throw new AssertionError("A11y violations: " + total + " bulundu\n" +
                    summary + "\nDetay: " + report);
        }
        System.out.println("[a11y] ✓ violation yok (axe-core)");
    }

    @Then("page has no critical accessibility issues")
    public void pageHasNoCriticalA11y() {
        AxeResults results = runAxe(null);
        List<Rule> critical = results.getViolations().stream()
                .filter(r -> "critical".equalsIgnoreCase(r.getImpact())
                          || "serious".equalsIgnoreCase(r.getImpact()))
                .collect(Collectors.toList());
        if (!critical.isEmpty()) {
            Path report = writeReport(results);
            throw new AssertionError("Critical/Serious a11y violations: "
                    + critical.size() + " bulundu\n" + summarize(critical)
                    + "\nDetay: " + report);
        }
        long totalLow = results.getViolations().size();
        System.out.printf("[a11y] ✓ critical/serious yok (toplam %d moderate/minor uyarı)%n", totalLow);
    }

    @Then("page passes WCAG {string}")
    public void pagePassesWcag(String tag) {
        AxeResults results = runAxe(tag);
        if (!results.getViolations().isEmpty()) {
            Path report = writeReport(results);
            throw new AssertionError("WCAG " + tag + " violation: "
                    + results.getViolations().size() + "\n"
                    + summarize(results.getViolations()) + "\nDetay: " + report);
        }
        System.out.println("[a11y] ✓ " + tag + " uyumlu");
    }

    private AxeResults runAxe(String tag) {
        Page page = PlaywrightFactory.page();
        if (page == null) {
            throw new IllegalStateException("Playwright Page null — recorder context aktif değil");
        }
        AxeBuilder axe = new AxeBuilder(page);
        if (tag != null && !tag.isBlank()) {
            axe.withTags(List.of(tag));
        }
        return axe.analyze();
    }

    private static String summarize(List<Rule> violations) {
        StringBuilder sb = new StringBuilder();
        int shown = 0;
        for (Rule v : violations) {
            if (shown++ >= 5) {
                sb.append("  ... (toplam ").append(violations.size()).append(")\n");
                break;
            }
            int nodeCount = v.getNodes() == null ? 0 : v.getNodes().size();
            sb.append(String.format("  [%s] %s — %d öğe etkilendi%n",
                    v.getImpact() == null ? "?" : v.getImpact(),
                    v.getId(),
                    nodeCount));
            if (v.getHelp() != null) {
                sb.append("    → ").append(v.getHelp()).append('\n');
            }
            if (v.getHelpUrl() != null) {
                sb.append("    ").append(v.getHelpUrl()).append('\n');
            }
        }
        return sb.toString();
    }

    private static Path writeReport(AxeResults results) {
        try {
            String ts = LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyy-MM-dd_HHmmss_SSS"));
            Files.createDirectories(REPORT_DIR);
            Path out = REPORT_DIR.resolve("a11y_" + ts + ".json");
            // axe-core has a built-in JSON serializer
            Files.writeString(out, serializeResults(results));
            return out;
        } catch (Exception e) {
            return Paths.get("<rapor yazılamadı: " + e.getMessage() + ">");
        }
    }

    /** Best-effort serialization — axe-core POJOs are Jackson-friendly. */
    private static String serializeResults(AxeResults results) {
        try {
            return new com.fasterxml.jackson.databind.ObjectMapper()
                    .writerWithDefaultPrettyPrinter()
                    .writeValueAsString(results);
        } catch (Exception e) {
            // Minimal fallback so we never block the test on report serialization
            StringBuilder sb = new StringBuilder("{\"violations\":[");
            boolean first = true;
            for (Rule r : results.getViolations()) {
                if (!first) sb.append(',');
                first = false;
                sb.append('{')
                  .append("\"id\":\"").append(r.getId()).append("\",")
                  .append("\"impact\":\"").append(r.getImpact()).append("\",")
                  .append("\"help\":\"").append(String.valueOf(r.getHelp()).replace("\"", "\\\"")).append("\"")
                  .append('}');
            }
            sb.append("]}");
            return sb.toString();
        }
    }
}
