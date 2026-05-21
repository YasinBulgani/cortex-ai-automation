package utils;

import config.ConfigManager;
import kong.unirest.HttpResponse;
import kong.unirest.Unirest;
import org.json.JSONArray;
import org.json.JSONObject;

import java.io.File;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Paths;

public class CucumberJsonAnalyzer {

    private static final String AI_URL = ConfigManager.getProperty(
            "ai.service.url", "http://localhost:5001") + "/classify_error";

    public static void main(String[] args) {
        try {
            Files.deleteIfExists(Paths.get("target/ai_yorum.txt"));

            File jsonFile = new File("target/cucumber.json");
            if (!jsonFile.exists()) {
                System.out.println("JSON report not found: target/cucumber.json");
                return;
            }

            String jsonContent = Files.readString(jsonFile.toPath());
            JSONArray root = new JSONArray(jsonContent);

            StringBuilder fullCommentary = new StringBuilder();

            for (Object featureObj : root) {
                JSONObject feature = (JSONObject) featureObj;
                JSONArray elements = feature.optJSONArray("elements");
                if (elements == null) continue;

                for (Object scenarioObj : elements) {
                    JSONObject scenario = (JSONObject) scenarioObj;
                    String scenarioName = scenario.optString("name");
                    JSONArray steps = scenario.optJSONArray("steps");
                    if (steps == null) continue;

                    for (Object stepObj : steps) {
                        JSONObject step = (JSONObject) stepObj;
                        String stepName = step.optString("name");
                        JSONObject result = step.optJSONObject("result");

                        if (result != null && "failed".equals(result.optString("status"))) {
                            String error = result.optString("error_message");

                            // Keep only the first line of the error message
                            String cleanedError = error.split("\n")[0];

                            // POST to Flask AI service
                            JSONObject requestBody = new JSONObject();
                            requestBody.put("error_message", cleanedError);
                            requestBody.put("scenario", scenarioName);
                            requestBody.put("step", stepName);

                            HttpResponse<String> response = Unirest.post(AI_URL)
                                    .header("Content-Type", "application/json")
                                    .body(requestBody.toString())
                                    .asString();

                            JSONObject aiResult = new JSONObject(response.getBody());
                            String category = aiResult.optString("predicted_label");
                            String suggestion = aiResult.optString("suggestion");

                            fullCommentary.append("Scenario:   ").append(scenarioName).append("\n");
                            fullCommentary.append("Step:       ").append(stepName).append("\n");
                            fullCommentary.append("Error:      ").append(cleanedError).append("\n");
                            fullCommentary.append("AI label:   ").append(category).append("\n");
                            fullCommentary.append("Suggestion: ").append(suggestion).append("\n\n");

                            Thread.sleep(1500); // be gentle on the API
                        }
                    }
                }
            }

            Files.writeString(Paths.get("target/ai_yorum.txt"), fullCommentary.toString(), StandardCharsets.UTF_8);
            System.out.println("AI commentary written to target/ai_yorum.txt");

        } catch (Exception e) {
            e.printStackTrace();
        }
    }
}
