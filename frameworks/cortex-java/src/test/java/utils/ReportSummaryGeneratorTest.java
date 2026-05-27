package utils;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Unit tests for ReportSummaryGenerator.generateReport.
 *
 * Uses synthetic minimal Cucumber JSON to avoid a live Maven Surefire run.
 * No browser involvement — pure file I/O + JSON parsing.
 */
class ReportSummaryGeneratorTest {

    @Test
    void missing_json_does_not_throw(@TempDir Path tmp) {
        // Should log+return cleanly, not throw
        Path missing = tmp.resolve("not_there.json");
        Path output  = tmp.resolve("out.html");
        assertDoesNotThrow(() -> ReportSummaryGenerator.generateReport(
                missing.toAbsolutePath().toString(),
                output.toAbsolutePath().toString()
        ));
        // Output should NOT be written when input is missing
        assertFalse(Files.exists(output), "No output expected when input is absent");
    }

    @Test
    void generates_html_table_for_all_passed(@TempDir Path tmp) throws IOException {
        Path json   = writeCucumberJson(tmp, cucumberJson1Scenario("passed"));
        Path output = tmp.resolve("out.html");

        ReportSummaryGenerator.generateReport(
                json.toAbsolutePath().toString(),
                output.toAbsolutePath().toString()
        );

        assertTrue(Files.exists(output), "Output file should be created");
        String content = Files.readString(output, StandardCharsets.UTF_8);
        assertTrue(content.contains("<table"), "Should contain table markup");
        // total=1, passed=1, failed=0, skipped=0
        assertTrue(content.contains(">1<"), "Passed count should be 1");
        assertTrue(content.contains(">0<"), "Failed count should be 0");
    }

    @Test
    void generates_html_table_for_failed_scenario(@TempDir Path tmp) throws IOException {
        Path json   = writeCucumberJson(tmp, cucumberJson1Scenario("failed"));
        Path output = tmp.resolve("out.html");

        ReportSummaryGenerator.generateReport(
                json.toAbsolutePath().toString(),
                output.toAbsolutePath().toString()
        );

        String content = Files.readString(output, StandardCharsets.UTF_8);
        assertTrue(content.contains("<table"));
        // total=1, passed=0, failed=1, skipped=0 — verify table exists
        assertTrue(content.contains("Başarısız Testler"), "Should have Turkish failed label");
    }

    @Test
    void empty_json_array_produces_zero_counts(@TempDir Path tmp) throws IOException {
        Path json   = writeCucumberJson(tmp, "[]");
        Path output = tmp.resolve("out.html");

        ReportSummaryGenerator.generateReport(
                json.toAbsolutePath().toString(),
                output.toAbsolutePath().toString()
        );

        String content = Files.readString(output, StandardCharsets.UTF_8);
        assertTrue(content.contains("<table"));
        assertFalse(content.isEmpty());
    }

    @Test
    void step_without_result_node_does_not_throw(@TempDir Path tmp) throws IOException {
        // Verifies the null guard: step entry with no "result" key must not cause NPE.
        String json = """
                [
                  {
                    "id": "feature1",
                    "name": "Sample Feature",
                    "elements": [
                      {
                        "id": "scenario1",
                        "name": "Sample Scenario",
                        "type": "scenario",
                        "steps": [
                          { "name": "step with no result node" }
                        ]
                      }
                    ]
                  }
                ]
                """;
        Path jsonPath = writeCucumberJson(tmp, json);
        Path output   = tmp.resolve("out.html");
        assertDoesNotThrow(() -> ReportSummaryGenerator.generateReport(
                jsonPath.toAbsolutePath().toString(),
                output.toAbsolutePath().toString()
        ), "Missing result node must not throw NPE");
        assertTrue(Files.exists(output), "Output must still be written");
    }

    @Test
    void background_element_is_not_counted_as_scenario(@TempDir Path tmp) throws IOException {
        // Elements with type="background" must be skipped by the counter —
        // they are setup steps, not test scenarios.
        String json = """
                [
                  {
                    "id": "feature1",
                    "name": "Feature With Background",
                    "elements": [
                      {
                        "id": "bg1",
                        "name": "Background",
                        "type": "background",
                        "steps": [
                          { "name": "setup step", "result": { "status": "passed" } }
                        ]
                      },
                      {
                        "id": "scenario1",
                        "name": "Actual Scenario",
                        "type": "scenario",
                        "steps": [
                          { "name": "real step", "result": { "status": "passed" } }
                        ]
                      }
                    ]
                  }
                ]
                """;
        Path jsonPath = writeCucumberJson(tmp, json);
        Path output   = tmp.resolve("out.html");

        ReportSummaryGenerator.generateReport(
                jsonPath.toAbsolutePath().toString(),
                output.toAbsolutePath().toString()
        );

        String content = Files.readString(output, StandardCharsets.UTF_8);
        // total must be 1 (background is not counted); passed must be 1
        assertTrue(content.contains(">1<"),
                "Total count should be 1 (background element must not be counted): " + content);
    }

    @Test
    void all_skipped_scenario_is_counted_as_skipped(@TempDir Path tmp) throws IOException {
        Path json   = writeCucumberJson(tmp, cucumberJson1Scenario("skipped"));
        Path output = tmp.resolve("out.html");

        ReportSummaryGenerator.generateReport(
                json.toAbsolutePath().toString(),
                output.toAbsolutePath().toString()
        );

        String content = Files.readString(output, StandardCharsets.UTF_8);
        assertTrue(Files.exists(output), "Output file must be written");
        assertTrue(content.contains("<table"));
        assertTrue(content.contains("Atlanan Testler"), "Should have Turkish skipped label");
    }

    @Test
    void feature_with_null_elements_does_not_throw(@TempDir Path tmp) throws IOException {
        // A feature entry with no "elements" key must be silently skipped.
        String json = """
                [
                  {
                    "id": "empty_feature",
                    "name": "Empty Feature"
                  }
                ]
                """;
        Path jsonPath = writeCucumberJson(tmp, json);
        Path output   = tmp.resolve("out.html");

        assertDoesNotThrow(() -> ReportSummaryGenerator.generateReport(
                jsonPath.toAbsolutePath().toString(),
                output.toAbsolutePath().toString()
        ), "Feature with null elements must not throw NPE");
        assertTrue(Files.exists(output), "Output must still be created");
    }

    @Test
    void output_is_written_as_utf8_with_turkish_chars(@TempDir Path tmp) throws IOException {
        Path json   = writeCucumberJson(tmp, cucumberJson1Scenario("passed"));
        Path output = tmp.resolve("out.html");

        ReportSummaryGenerator.generateReport(
                json.toAbsolutePath().toString(),
                output.toAbsolutePath().toString()
        );

        // File must be readable as UTF-8 and contain Turkish characters
        String content = Files.readString(output, StandardCharsets.UTF_8);
        assertTrue(content.contains("Başarılı") || content.contains("Toplam"),
                "Output must contain Turkish characters readable in UTF-8");
    }

    // ── helpers ──────────────────────────────────────────────

    private Path writeCucumberJson(Path dir, String content) throws IOException {
        Path path = dir.resolve("cucumber.json");
        Files.writeString(path, content, StandardCharsets.UTF_8);
        return path;
    }

    /**
     * Minimal Cucumber JSON with one scenario whose single step has the given status.
     */
    private String cucumberJson1Scenario(String stepStatus) {
        return """
                [
                  {
                    "id": "feature1",
                    "name": "Sample Feature",
                    "elements": [
                      {
                        "id": "scenario1",
                        "name": "Sample Scenario",
                        "type": "scenario",
                        "steps": [
                          {
                            "name": "I do something",
                            "result": { "status": "%s" }
                          }
                        ]
                      }
                    ]
                  }
                ]
                """.formatted(stepStatus);
    }
}
