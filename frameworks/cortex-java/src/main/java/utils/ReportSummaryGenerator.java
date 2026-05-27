package utils;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;

import java.io.File;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.util.List;
import java.util.Locale;
import java.util.Map;

/**
 * Reads a Cucumber JSON report and writes a human-readable HTML summary to a file.
 *
 * <p>Parses {@code cucumber.json} produced by the Cucumber HTML/JSON plugin, counts
 * total / passed / failed / skipped scenarios, and lists the results. The output is
 * written to {@code target/ai_ozet.html} by default and is also logged via
 * {@link LoggerUtil} for CI log visibility.
 *
 * <p>Can be run standalone via {@link #main(String[])} for ad-hoc report generation,
 * or called programmatically via {@link #generateReport(String, String)}.
 *
 * <p>Thread safety: all methods are static and stateless — safe for concurrent calls
 * with distinct file paths.
 */
public class ReportSummaryGenerator {

    public static void main(String[] args) {
        // Prefer Selenium output, fall back to Playwright output
        File seleniumJson   = new File("target/cucumber.json");
        File playwrightJson = new File("target/cucumber-playwright.json");
        File source = seleniumJson.exists() ? seleniumJson
                    : (playwrightJson.exists() ? playwrightJson : seleniumJson);
        generateReport(source.getPath(), "target/ai_ozet.html");
    }

    @SuppressWarnings("unchecked")
    public static void generateReport(String jsonPath, String outputPath) {
        try {
            File jsonFile = new File(jsonPath);
            if (!jsonFile.exists()) {
                LoggerUtil.logWarn("Cucumber JSON report not found: " + jsonPath);
                return;
            }

            ObjectMapper mapper = new ObjectMapper();
            List<Map<String, Object>> json = mapper.readValue(jsonFile, new TypeReference<>() {});

            int total = 0, passed = 0, failed = 0, skipped = 0;

            for (Map<String, Object> feature : json) {
                List<Map<String, Object>> elements =
                        (List<Map<String, Object>>) feature.get("elements");
                if (elements == null) continue;

                for (Map<String, Object> scenario : elements) {
                    if (!"scenario".equals(scenario.get("type"))) continue; // skip background
                    total++;

                    List<Map<String, Object>> steps =
                            (List<Map<String, Object>>) scenario.get("steps");
                    if (steps == null) continue;

                    boolean hasFailed = steps.stream().anyMatch(step -> {
                        Map<String, Object> res = (Map<String, Object>) step.get("result");
                        return res != null && "failed".equalsIgnoreCase(String.valueOf(res.get("status")));
                    });

                    boolean allSkipped = steps.stream().allMatch(step -> {
                        Map<String, Object> res = (Map<String, Object>) step.get("result");
                        return res != null && "skipped".equalsIgnoreCase(String.valueOf(res.get("status")));
                    });

                    if (hasFailed) {
                        failed++;
                    } else if (allSkipped) {
                        skipped++;
                    } else {
                        passed++;
                    }
                }
            }

            String date = LocalDate.now()
                    .format(DateTimeFormatter.ofPattern("d MMMM yyyy", new Locale("tr", "TR")));

            String htmlContent = """

                        <table role="presentation" class="summary-table">
                          <tr>
                            <td>Test Tarihi:</td>
                            <td id="table-date">%s</td>
                          </tr>
                          <tr>
                            <td>Toplam Test Senaryosu:</td>
                            <td>%d</td>
                          </tr>
                          <tr>
                            <td>Başarılı Testler:</td>
                            <td>%d</td>
                          </tr>
                          <tr>
                            <td>Başarısız Testler:</td>
                            <td>%d</td>
                          </tr>
                          <tr>
                            <td>Atlanan Testler:</td>
                            <td>%d</td>
                          </tr>
                        </table>
                """.formatted(date, total, passed, failed, skipped);

            Files.writeString(Paths.get(outputPath), htmlContent, StandardCharsets.UTF_8);
            LoggerUtil.logInfo("HTML özet raporu yazıldı: " + outputPath);

        } catch (Exception e) {
            LoggerUtil.logError("ReportSummaryGenerator başarısız oldu", e);
        }
    }
}
