package playwright;

import com.microsoft.playwright.Locator;
import com.microsoft.playwright.Page;
import com.microsoft.playwright.PlaywrightException;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardOpenOption;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.function.Consumer;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * E20 — Locator self-healing wrapper.
 *
 * Wraps a Playwright action so that, on a {@link PlaywrightException}
 * (typically a "TimeoutError: locator.click: Timeout 30000ms exceeded"),
 * we:
 *   1. Capture the current page DOM (truncated).
 *   2. POST it to the Flask {@code /api/cortex/locator/suggest} endpoint
 *      together with the original failing selector and key.
 *   3. Read back a ranked list of alternative selectors.
 *   4. Try each suggestion above the confidence threshold, in order.
 *   5. Log the winning replacement to {@code target/self-heal/suggestions.ndjson}
 *      so the engineer can promote it into the locator JSON next sprint.
 *
 * The whole flow is opt-in via system property:
 *   -Dcortex.selfheal=true
 * Off by default — first-pass tests stay deterministic; self-heal kicks in
 * only when explicitly asked, so flaky-pass behaviour can be detected.
 *
 * Thread-safety: stateless static methods. The HTTP call uses {@code HttpURLConnection}
 * directly (no extra deps), with a hard 15-second timeout to keep the test run bounded.
 */
public final class SelfHeal {

    private SelfHeal() {}

    private static final String ENABLED_PROP = "cortex.selfheal";
    private static final String ENDPOINT_PROP = "cortex.selfheal.endpoint";
    private static final String DEFAULT_ENDPOINT = "http://127.0.0.1:5001/api/cortex/locator/suggest";
    private static final int MIN_CONFIDENCE = 70; // skip low-confidence guesses
    private static final int CONNECT_TIMEOUT_MS = 5_000;
    private static final int READ_TIMEOUT_MS = 60_000; // matches Ollama side
    private static final int MAX_DOM_BYTES = 12_000;   // server truncates at 8K; leave headroom

    private static final Path LOG_FILE = Paths.get("target/self-heal/suggestions.ndjson");

    /** Returns {@code true} when {@code -Dcortex.selfheal=true} was passed. */
    public static boolean enabled() {
        return Boolean.parseBoolean(System.getProperty(ENABLED_PROP, "false"));
    }

    /**
     * Run {@code action} against the locator for {@code key}; if it throws a
     * {@link PlaywrightException} and self-heal is enabled, ask the AI for
     * suggestions and retry with each.
     *
     * @param actionLabel  short name used in the side-channel log ("click", "fill", ...)
     * @param key          the locator key as it appears in the JSON map
     * @param locators     the current map (a winning suggestion does NOT mutate it in-place;
     *                     mutations need explicit promotion to keep tests reproducible)
     * @param scenarioCtx  optional context — Cucumber scenario name, step text, etc.
     * @param action       callback that takes the resolved {@link Locator} and performs the
     *                     interaction (click, fill, hover...)
     * @throws PlaywrightException re-thrown if self-heal is disabled or no suggestion works
     */
    public static void attempt(String actionLabel,
                               String key,
                               Map<String, String> locators,
                               String scenarioCtx,
                               Consumer<Locator> action) {
        Locator primary = PlaywrightFactory.page().locator(locators.get(key)).first();
        try {
            action.accept(primary);
            return;
        } catch (PlaywrightException original) {
            if (!enabled()) throw original;
            // ↓ self-heal path
            String originalSel = locators.get(key);
            List<Suggestion> suggestions = suggestFromAi(key, originalSel, scenarioCtx);
            for (Suggestion s : suggestions) {
                if (s.confidence < MIN_CONFIDENCE) continue;
                try {
                    Locator candidate = PlaywrightFactory.page().locator(s.selector).first();
                    action.accept(candidate);
                    logHeal(actionLabel, key, originalSel, s, scenarioCtx, /*success*/true, null);
                    return;
                } catch (PlaywrightException retry) {
                    logHeal(actionLabel, key, originalSel, s, scenarioCtx, /*success*/false,
                            retry.getMessage());
                }
            }
            throw original; // every candidate failed; surface the original error
        }
    }

    // ------------------------------------------------------------------
    // AI bridge
    // ------------------------------------------------------------------

    private static List<Suggestion> suggestFromAi(String key, String originalSelector, String ctx) {
        try {
            Page page = PlaywrightFactory.page();
            String dom = page.content();
            if (dom.length() > MAX_DOM_BYTES) {
                dom = dom.substring(0, MAX_DOM_BYTES) + "\n<!-- ...truncated... -->";
            }
            String endpoint = System.getProperty(ENDPOINT_PROP, DEFAULT_ENDPOINT);
            String body = "{"
                    + "\"key\":" + jsonString(key) + ","
                    + "\"original_selector\":" + jsonString(originalSelector == null ? "" : originalSelector) + ","
                    + "\"dom_snippet\":" + jsonString(dom) + ","
                    + "\"context\":" + jsonString(ctx == null ? "" : ctx)
                    + "}";
            HttpURLConnection conn = (HttpURLConnection) new URL(endpoint).openConnection();
            conn.setRequestMethod("POST");
            conn.setRequestProperty("Content-Type", "application/json; charset=utf-8");
            conn.setConnectTimeout(CONNECT_TIMEOUT_MS);
            conn.setReadTimeout(READ_TIMEOUT_MS);
            conn.setDoOutput(true);
            try (OutputStream os = conn.getOutputStream()) {
                os.write(body.getBytes(StandardCharsets.UTF_8));
            }
            int code = conn.getResponseCode();
            if (code != 200) return List.of();
            StringBuilder sb = new StringBuilder();
            try (BufferedReader r = new BufferedReader(
                    new InputStreamReader(conn.getInputStream(), StandardCharsets.UTF_8))) {
                String line;
                while ((line = r.readLine()) != null) sb.append(line);
            }
            return parseSuggestions(sb.toString());
        } catch (Exception e) {
            System.err.println("[SelfHeal] AI call failed: " + e.getMessage());
            return List.of();
        }
    }

    /**
     * Pull suggestion objects out of the Flask JSON response without dragging
     * in a JSON library — the shape is small and stable, so a couple of regex
     * passes keep us dep-free.
     */
    private static List<Suggestion> parseSuggestions(String payload) {
        List<Suggestion> out = new ArrayList<>();
        Pattern obj = Pattern.compile(
                "\\{[^\\{]*?\"selector\"\\s*:\\s*\"((?:[^\"\\\\]|\\\\.)*)\"" +
                "[^\\{]*?\"type\"\\s*:\\s*\"([^\"]+)\"" +
                "[^\\{]*?\"confidence\"\\s*:\\s*(\\d+)" +
                "[^\\{]*?\"why\"\\s*:\\s*\"((?:[^\"\\\\]|\\\\.)*)\"[^\\}]*?\\}",
                Pattern.DOTALL);
        Matcher m = obj.matcher(payload);
        while (m.find()) {
            out.add(new Suggestion(
                    unescape(m.group(1)),
                    m.group(2),
                    Integer.parseInt(m.group(3)),
                    unescape(m.group(4))));
        }
        return out;
    }

    private static String unescape(String s) {
        return s.replace("\\\"", "\"").replace("\\\\", "\\").replace("\\n", "\n");
    }

    private static String jsonString(String s) {
        StringBuilder sb = new StringBuilder("\"");
        for (int i = 0; i < s.length(); i++) {
            char c = s.charAt(i);
            switch (c) {
                case '"': sb.append("\\\""); break;
                case '\\': sb.append("\\\\"); break;
                case '\n': sb.append("\\n"); break;
                case '\r': sb.append("\\r"); break;
                case '\t': sb.append("\\t"); break;
                default:
                    if (c < 0x20) sb.append(String.format("\\u%04x", (int) c));
                    else sb.append(c);
            }
        }
        sb.append('"');
        return sb.toString();
    }

    // ------------------------------------------------------------------
    // Side-channel log — ndjson, one object per line
    // ------------------------------------------------------------------

    private static synchronized void logHeal(String action,
                                             String key,
                                             String original,
                                             Suggestion s,
                                             String ctx,
                                             boolean success,
                                             String errorIfAny) {
        try {
            Files.createDirectories(LOG_FILE.getParent());
            String line = "{"
                    + "\"ts\":" + jsonString(Instant.now().toString()) + ","
                    + "\"action\":" + jsonString(action) + ","
                    + "\"key\":" + jsonString(key) + ","
                    + "\"original\":" + jsonString(original == null ? "" : original) + ","
                    + "\"suggestion\":" + jsonString(s.selector) + ","
                    + "\"type\":" + jsonString(s.type) + ","
                    + "\"confidence\":" + s.confidence + ","
                    + "\"why\":" + jsonString(s.why) + ","
                    + "\"context\":" + jsonString(ctx == null ? "" : ctx) + ","
                    + "\"success\":" + success
                    + (errorIfAny == null ? "" : ",\"error\":" + jsonString(errorIfAny.split("\n")[0]))
                    + "}\n";
            Files.writeString(LOG_FILE, line,
                    StandardOpenOption.CREATE,
                    StandardOpenOption.APPEND);
        } catch (Exception ignored) {
            // Logging failure must not break the test run.
        }
    }

    static final class Suggestion {
        final String selector;
        final String type;
        final int confidence;
        final String why;
        Suggestion(String selector, String type, int confidence, String why) {
            this.selector = selector;
            this.type = type;
            this.confidence = confidence;
            this.why = why;
        }
    }
}
