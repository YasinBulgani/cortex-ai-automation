import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;

public class LlmClient {

    private final String apiKey;
    private final String baseUrl;
    private final String model;

    public LlmClient(String apiKey, String baseUrl, String model) {
        this.apiKey = apiKey;
        this.baseUrl = baseUrl;
        this.model = model;
    }

    public static LlmClient fromEnvOrNull() {
        String key = System.getenv("OPENAI_API_KEY");
        if (key == null || key.isBlank()) {
            return null;
        }
        String url = System.getenv().getOrDefault("OPENAI_BASE_URL", "https://api.openai.com/v1/chat/completions");
        String model = System.getenv().getOrDefault("OPENAI_MODEL", "gpt-4.1-mini");
        return new LlmClient(key, url, model);
    }

    public String summarizeSession(Session session) throws IOException, InterruptedException {
        String notes = Files.readString(session.notesFile(), StandardCharsets.UTF_8);

        String prompt = """
                Sen kıdemli bir teknik mülakat değerlendiricisisin.
                Aşağıdaki notlara göre adayın güçlü yönlerini, zayıf yönlerini ve devam kararı önerini Türkçe, kısa ve maddeli olarak özetle.

                Notlar:
                """ + "\n" + notes;

        String jsonBody = "{"
                + "\"model\":" + jsonString(model) + ","
                + "\"messages\":["
                + "{\"role\":\"system\",\"content\":\"You are a helpful assistant for interview evaluation.\"},"
                + "{\"role\":\"user\",\"content\":" + jsonString(prompt) + "}"
                + "]"
                + "}";

        HttpClient client = HttpClient.newHttpClient();
        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(baseUrl))
                .header("Authorization", "Bearer " + apiKey)
                .header("Content-Type", "application/json")
                .POST(HttpRequest.BodyPublishers.ofString(jsonBody))
                .build();

        HttpResponse<String> response = client.send(request, HttpResponse.BodyHandlers.ofString(StandardCharsets.UTF_8));

        String body = response.body();
        Files.writeString(session.baseDir().resolve("llm_raw_response.json"), body, StandardCharsets.UTF_8);

        String summary = extractFirstContent(body);
        if (summary == null || summary.isBlank()) {
            summary = "LLM yanıtı parse edilemedi, lütfen llm_raw_response.json dosyasına bakın.";
        }

        Files.writeString(session.baseDir().resolve("llm_summary.md"), summary, StandardCharsets.UTF_8);
        return summary;
    }

    private static String jsonString(String s) {
        return "\"" + s.replace("\\", "\\\\").replace("\"", "\\\"").replace("\n", "\\n") + "\"";
    }

    /**
     * Çok basit / kırılgan ama bağımsız bir parser:
     * response içinde ilk `"content":"...` alanını bulup içeriği döner.
     */
    private static String extractFirstContent(String body) {
        String marker = "\"content\":";
        int idx = body.indexOf(marker);
        if (idx < 0) return null;
        int startQuote = body.indexOf('"', idx + marker.length());
        if (startQuote < 0) return null;
        StringBuilder sb = new StringBuilder();
        boolean escape = false;
        for (int i = startQuote + 1; i < body.length(); i++) {
            char c = body.charAt(i);
            if (escape) {
                if (c == 'n') sb.append('\n');
                else sb.append(c);
                escape = false;
            } else if (c == '\\') {
                escape = true;
            } else if (c == '"') {
                break;
            } else {
                sb.append(c);
            }
        }
        return sb.toString().trim();
    }
}

