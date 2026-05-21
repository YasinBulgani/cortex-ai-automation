package utils;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;

import java.io.File;
import java.io.FileWriter;
import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.util.List;
import java.util.Locale;
import java.util.Map;

public class ReportSummaryGenerator {

    public static void main(String[] args) {
        // Prefer Selenium output, fall back to Playwright output
        File seleniumJson = new File("target/cucumber.json");
        File playwrightJson = new File("target/cucumber-playwright.json");
        File source = seleniumJson.exists() ? seleniumJson
                  : (playwrightJson.exists() ? playwrightJson : seleniumJson);
        generateReport(source.getPath(), "target/ai_ozet.html");
    }

    public static void generateReport(String jsonPath, String outputPath) {
        try {
            File jsonFile = new File(jsonPath);
            if (!jsonFile.exists()) {
                System.err.println("cucumber.json not found: " + jsonPath);
                return;
            }

            ObjectMapper mapper = new ObjectMapper();
            List<Map<String, Object>> json = mapper.readValue(jsonFile, new TypeReference<>() {});

            int total = 0, passed = 0, failed = 0, skipped = 0;

            for (Map<String, Object> feature : json) {
                @SuppressWarnings("unchecked")
                List<Map<String, Object>> elements = (List<Map<String, Object>>) feature.get("elements");
                if (elements == null) continue;

                for (Map<String, Object> scenario : elements) {
                    if (!"scenario".equals(scenario.get("type"))) continue; // skip background
                    total++;

                    @SuppressWarnings("unchecked")
                    List<Map<String, Object>> steps = (List<Map<String, Object>>) scenario.get("steps");
                    if (steps == null) continue;

                    boolean hasFailed = steps.stream().anyMatch(step ->
                            "failed".equalsIgnoreCase(((Map<String, Object>) step.get("result")).get("status").toString())
                    );

                    boolean allSkipped = steps.stream().allMatch(step ->
                            "skipped".equalsIgnoreCase(((Map<String, Object>) step.get("result")).get("status").toString())
                    );

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

            try (FileWriter writer = new FileWriter(outputPath)) {
                writer.write(htmlContent);
            }

            System.out.println("HTML summary written to: " + outputPath);

        } catch (Exception e) {
            System.err.println("Error: " + e.getMessage());
        }
    }
}
