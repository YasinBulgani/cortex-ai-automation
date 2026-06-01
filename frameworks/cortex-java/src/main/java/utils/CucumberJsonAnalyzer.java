package utils;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import kong.unirest.HttpResponse;
import kong.unirest.Unirest;

import java.io.File;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Paths;

import static utils.LoggerUtil.logError;
import static utils.LoggerUtil.logInfo;

/**
 * Post-run AI analysis tool: parses the Cucumber JSON report, sends each
 * failed step to the configured classifier endpoint, and writes a summary to
 * {@code target/ai_analysis.txt}.
 *
 * <p>Run standalone after {@code mvn test}:
 * {@code mvn exec:java -Dexec.mainClass=utils.CucumberJsonAnalyzer}
 *
 * <p>JSON library: Jackson (consolidated from org.json for consistency with
 * the rest of the framework).
 */
public class CucumberJsonAnalyzer {

    private static final ObjectMapper MAPPER = new ObjectMapper();

    /**
     * AI classifier endpoint. Override at runtime:
     * <ul>
     *   <li>{@code -Dai.analyzer.url=http://my-server:5001/classify_error}</li>
     *   <li>or via env var {@code AI_ANALYZER_URL}</li>
     * </ul>
     * Defaults to {@code localhost:5001} for local dev only.
     */
    private static final String AI_ENDPOINT = resolveEndpoint();

    private static String resolveEndpoint() {
        String prop = System.getProperty("ai.analyzer.url");
        if (prop != null && !prop.isBlank()) return prop;
        String env = System.getenv("AI_ANALYZER_URL");
        if (env != null && !env.isBlank()) return env;
        return "http://localhost:5001/classify_error";
    }

    /**
     * Entry point for post-run AI analysis: reads {@code target/cucumber.json}, sends
     * failed scenarios to the AI classifier endpoint, and writes results to
     * {@code target/ai_analysis.txt}. Designed to be invoked as a Maven exec plugin step.
     */
    public static void main(String[] args) {
        try {
            Files.deleteIfExists(Paths.get("target/ai_analysis.txt"));

            File jsonFile = new File("target/cucumber.json");
            if (!jsonFile.exists()) {
                logInfo("JSON report not found: target/cucumber.json");
                return;
            }

            JsonNode root = MAPPER.readTree(jsonFile);
            StringBuilder fullCommentary = new StringBuilder();

            for (JsonNode feature : root) {
                JsonNode elements = feature.get("elements");
                if (elements == null || !elements.isArray()) continue;

                for (JsonNode scenario : elements) {
                    String scenarioName = textOrEmpty(scenario, "name");
                    JsonNode steps = scenario.get("steps");
                    if (steps == null || !steps.isArray()) continue;

                    for (JsonNode step : steps) {
                        String stepName = textOrEmpty(step, "name");
                        JsonNode result = step.get("result");
                        if (result == null) continue;

                        String status = textOrEmpty(result, "status");
                        if (!"failed".equals(status)) continue;

                        String error = textOrEmpty(result, "error_message");
                        String cleanedError = error.contains("\n")
                                ? error.substring(0, error.indexOf('\n'))
                                : error;

                        // Build request body with Jackson
                        ObjectNode requestBody = MAPPER.createObjectNode();
                        requestBody.put("error_message", cleanedError);
                        requestBody.put("scenario", scenarioName);
                        requestBody.put("step", stepName);

                        HttpResponse<String> response = Unirest.post(AI_ENDPOINT)
                                .header("Content-Type", "application/json")
                                .body(MAPPER.writeValueAsString(requestBody))
                                .asString();

                        JsonNode aiResult = MAPPER.readTree(response.getBody());
                        String kategori = textOrEmpty(aiResult, "predicted_label");
                        String onerisi  = textOrEmpty(aiResult, "suggestion");

                        fullCommentary.append("Scenario:   ").append(scenarioName).append("\n");
                        fullCommentary.append("Step:       ").append(stepName).append("\n");
                        fullCommentary.append("Error:      ").append(cleanedError).append("\n");
                        fullCommentary.append("AI label:   ").append(kategori).append("\n");
                        fullCommentary.append("Suggestion: ").append(onerisi).append("\n\n");

                        Thread.sleep(1500); // API rate-limit buffer (intentional fixed delay)
                    }
                }
            }

            Files.writeString(Paths.get("target/ai_analysis.txt"), fullCommentary.toString(),
                    StandardCharsets.UTF_8);
            logInfo("AI annotations written to target/ai_analysis.txt");

        } catch (Exception e) {
            logError("CucumberJsonAnalyzer failed", e);
        }
    }

    private static String textOrEmpty(JsonNode node, String field) {
        JsonNode f = node.get(field);
        return (f != null && !f.isNull()) ? f.asText() : "";
    }
}
