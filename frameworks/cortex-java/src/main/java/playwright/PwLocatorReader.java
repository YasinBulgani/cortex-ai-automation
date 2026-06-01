package playwright;

import com.google.gson.Gson;
import com.google.gson.reflect.TypeToken;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Stream;

/**
 * Cortex-only locator loader for Playwright.
 *
 * Load order:
 *   1) shared/locators/common.json
 *   2) shared/locators/{featureName}.json
 *   3) projects/<X>/locators/common.json
 *   4) projects/<X>/locators/{featureName}.json
 *   5) recordings/locators/{featureName}.json
 *
 * Multi-locator support: when the same key appears in multiple entries,
 * the result is serialized as "MULTI||sel1||sel2||sel3".
 * PwCommonMethods.locator() turns that into a Locator.or() chain.
 */
public final class PwLocatorReader {

    public static final String MULTI_PREFIX = "MULTI||";
    public static final String MULTI_SEP    = "||";

    private static final Path SHARED     = Paths.get("src/test/resources/shared/locators");
    private static final Path PROJECTS   = Paths.get("src/test/resources/projects");
    private static final Path RECORDINGS = Paths.get("src/test/resources/recordings/locators");

    private PwLocatorReader() {}

    public static Map<String, String> read(String legacyDirIgnored, String featureName) {
        Map<String, List<String>> raw = new LinkedHashMap<>();

        loadFile(SHARED.resolve("common.json"), raw);
        loadFile(SHARED.resolve(featureName + ".json"), raw);
        loadFile(SHARED.resolve("shadow-locators.json"), raw);

        if (Files.isDirectory(PROJECTS)) {
            try (Stream<Path> projects = Files.list(PROJECTS)) {
                projects.filter(Files::isDirectory).forEach(pdir -> {
                    Path locDir = pdir.resolve("locators");
                    if (!Files.isDirectory(locDir)) return;
                    // Load common.json first, then EVERY *.json in the directory.
                    // This way related features (e.g. login-validation.feature) inherit
                    // login.json keys without duplication; same-key entries become MultiBy fallbacks.
                    loadFile(locDir.resolve("common.json"), raw);
                    try (Stream<Path> jsons = Files.list(locDir)) {
                        jsons.filter(p -> p.getFileName().toString().endsWith(".json"))
                             .filter(p -> !p.getFileName().toString().equals("common.json"))
                             .forEach(p -> loadFile(p, raw));
                    } catch (IOException ignored) {}
                });
            } catch (IOException ignored) {}
        }
        loadFile(RECORDINGS.resolve(featureName + ".json"), raw);

        Map<String, String> result = new HashMap<>();
        for (var entry : raw.entrySet()) {
            List<String> sels = entry.getValue();
            if (sels.size() == 1) {
                result.put(entry.getKey(), sels.get(0));
            } else {
                result.put(entry.getKey(), MULTI_PREFIX + String.join(MULTI_SEP, sels));
            }
        }
        return result;
    }

    private static void loadFile(Path file, Map<String, List<String>> out) {
        if (!Files.exists(file)) return;
        String content;
        try {
            content = Files.readString(file);
        } catch (IOException e) {
            throw new IllegalStateException(
                "[PwLocatorReader] Cannot read locator file " + file + " (permission/IO error). "
                + "Scenario would run with incomplete locators; failing fast.", e);
        }
        List<Map<String, String>> rawData;
        try {
            rawData = new Gson().fromJson(content, new TypeToken<List<Map<String, String>>>() {}.getType());
        } catch (Exception e) {
            throw new IllegalStateException(
                "[PwLocatorReader] Malformed JSON in locator file " + file + ": " + e.getMessage()
                + ". Scenario would run with missing keys; fix the file or remove it.", e);
        }
        if (rawData == null) return;
        for (Map<String, String> entry : rawData) {
            // _comment / _README docs entries
            if (entry.keySet().stream().allMatch(k -> k.startsWith("_"))) continue;
            if (entry.containsKey("hostSelector") && entry.containsKey("innerSelector")) continue;
            String key = entry.get("key");
            String type = entry.get("type");
            String value = entry.get("value");
            if (key == null || type == null || value == null) continue;
            out.computeIfAbsent(key, k -> new ArrayList<>())
               .add(toPlaywrightSelector(type, value));
        }
    }

    public static String toPlaywrightSelector(String type, String value) {
        return switch (type.toLowerCase()) {
            case "id"               -> "#" + value;
            case "name"             -> "[name='" + value.replace("'", "\\'") + "']";
            case "css"              -> value;
            case "xpath"            -> "xpath=" + value;
            case "class"            -> "." + value;
            case "tag"              -> value;
            case "linktext"         -> "text='" + value + "'";
            case "partiallinktext"  -> "text=" + value;
            default -> throw new IllegalArgumentException("Unknown locator type: " + type);
        };
    }

    public static boolean isMulti(String selector) {
        return selector != null && selector.startsWith(MULTI_PREFIX);
    }

    public static List<String> parseMulti(String selector) {
        if (!isMulti(selector)) return List.of(selector);
        return Arrays.asList(selector.substring(MULTI_PREFIX.length()).split("\\|\\|"));
    }
}
