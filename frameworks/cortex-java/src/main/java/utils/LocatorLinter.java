package utils;

import com.google.gson.Gson;
import com.google.gson.reflect.TypeToken;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.regex.Pattern;
import java.util.stream.Stream;

/**
 * Scans locator JSON files and reports anti-patterns.
 *
 * CLI usage:
 *   mvn exec:java -Dexec.mainClass=utils.LocatorLinter
 *   mvn exec:java -Dexec.mainClass=utils.LocatorLinter \
 *       -Dexec.args="src/main/resources/locators src/test/resources/projects"
 *
 * Output: warnings to stdout + exit code (0 clean, 1 has errors).
 *
 * Detected patterns:
 *   - Absolute XPath (/html/body/...)
 *   - Auto-generated id (:r0:, mui-12, ant-1)
 *   - Index-based selectors ([3], [last()])
 *   - Dynamic CSS classes (tooltipstered, pulseWarning, hover, active)
 *   - Selectors longer than 150 chars
 *   - Duplicate key warning (info level: now interpreted as MultiBy fallback)
 */
public final class LocatorLinter {

    public enum Severity { INFO, WARN, ERROR }

    public record Issue(Severity sev, Path file, String key, String value, String message) {}

    private static final Pattern AUTO_ID =
            Pattern.compile("(:r[a-z0-9]+:|mui-\\d+|ant-\\d+|ng-tns-c\\d+|MuiAutocomplete-[a-z]+-\\d+)");
    private static final Pattern DYNAMIC_CLASS =
            Pattern.compile("(tooltipstered|pulseWarning|pulse|hover|active|focused|selected|sa-icon\\s+sa-warning\\s+pulse)");
    private static final Pattern INDEX_BASED =
            Pattern.compile("\\[\\s*\\d+\\s*\\]|last\\(\\s*\\)");
    private static final int LONG_LIMIT = 150;

    public static void main(String[] args) {
        List<Path> targets = new ArrayList<>();
        if (args.length == 0) {
            targets.add(Paths.get("src/main/resources/locators"));
            targets.add(Paths.get("src/test/resources/projects"));
            targets.add(Paths.get("src/test/resources/shared"));
            targets.add(Paths.get("src/test/resources/recordings"));
        } else {
            for (String a : args) targets.add(Paths.get(a));
        }

        List<Issue> issues = new ArrayList<>();
        for (Path root : targets) lintTree(root, issues);

        report(issues);
        System.exit(issues.stream().anyMatch(i -> i.sev == Severity.ERROR) ? 1 : 0);
    }

    public static List<Issue> lintTree(Path root, List<Issue> sink) {
        if (!Files.exists(root)) return sink;
        try (Stream<Path> walk = Files.walk(root)) {
            walk.filter(p -> p.toString().endsWith(".json")).forEach(p -> lintFile(p, sink));
        } catch (IOException e) {
            System.err.println("[LocatorLinter] Failed to walk " + root + ": " + e.getMessage());
        }
        return sink;
    }

    public static void lintFile(Path file, List<Issue> sink) {
        try {
            String content = Files.readString(file);
            List<Map<String, String>> raw = new Gson()
                    .fromJson(content, new TypeToken<List<Map<String, String>>>() {}.getType());
            if (raw == null) return;

            Set<String> seenKeys = new HashSet<>();
            for (Map<String, String> entry : raw) {
                // _comment / _README / _note / _example — doc-only entries
                boolean isComment = entry.keySet().stream().allMatch(k -> k.startsWith("_"));
                if (isComment) continue;

                String key = entry.get("key");
                String type = entry.get("type");
                String value = entry.get("value");

                // Shadow locator schema (hostSelector + innerSelector) — different format
                if (entry.containsKey("hostSelector") && entry.containsKey("innerSelector")) {
                    continue;
                }

                if (key == null || type == null || value == null) {
                    sink.add(new Issue(Severity.ERROR, file, key, value, "key/type/value missing"));
                    continue;
                }

                // Duplicate key (now interpreted as MultiBy fallback, info only)
                if (!seenKeys.add(key)) {
                    sink.add(new Issue(Severity.INFO, file, key, value,
                            "Key repeated -> treated as fallback locator"));
                }

                // XPath-specific checks
                if ("xpath".equalsIgnoreCase(type)) {
                    if (value.startsWith("/html") || value.startsWith("/body") || value.startsWith("/*[")) {
                        sink.add(new Issue(Severity.WARN, file, key, value,
                                "Absolute XPath (breaks on any DOM change) -> use relative attribute-based"));
                    }
                    if (INDEX_BASED.matcher(value).find() && !value.contains("normalize-space") && !value.contains("contains")) {
                        sink.add(new Issue(Severity.WARN, file, key, value,
                                "Index-based position ([N]) is fragile -> use attribute/text match"));
                    }
                }

                // Dynamic class inside CSS / id / xpath
                if (DYNAMIC_CLASS.matcher(value).find()) {
                    sink.add(new Issue(Severity.WARN, file, key, value,
                            "Dynamic class (tooltipster/pulse/active/hover) -> depends on JS state, unstable"));
                }

                // Auto-generated id
                if (AUTO_ID.matcher(value).find()) {
                    sink.add(new Issue(Severity.WARN, file, key, value,
                            "Auto-generated id (React/MUI/Angular) -> changes on every render"));
                }

                // Long selector
                if (value.length() > LONG_LIMIT) {
                    sink.add(new Issue(Severity.WARN, file, key, value,
                            "Selector too long (" + value.length() + " chars) -> refactor"));
                }

                // type 'xpath' that could be written as a simple CSS id selector
                if ("xpath".equalsIgnoreCase(type) && value.matches("^//[a-z]+\\[@id=['\"]\\w+['\"]\\]$")) {
                    sink.add(new Issue(Severity.INFO, file, key, value,
                            "This XPath can be expressed as a '#id' CSS selector"));
                }
            }
        } catch (Exception e) {
            sink.add(new Issue(Severity.ERROR, file, null, null, "JSON parse error: " + e.getMessage()));
        }
    }

    private static void report(List<Issue> issues) {
        if (issues.isEmpty()) {
            System.out.println("[LocatorLinter] All locator files are clean.");
            return;
        }
        long errors = issues.stream().filter(i -> i.sev == Severity.ERROR).count();
        long warns  = issues.stream().filter(i -> i.sev == Severity.WARN).count();
        long infos  = issues.stream().filter(i -> i.sev == Severity.INFO).count();

        System.out.println("=".repeat(78));
        System.out.printf(" LocatorLinter report: %d ERROR / %d WARN / %d INFO%n", errors, warns, infos);
        System.out.println("=".repeat(78));

        Path lastFile = null;
        for (Issue i : issues) {
            if (!i.file.equals(lastFile)) {
                System.out.println("\n " + i.file);
                lastFile = i.file;
            }
            String marker = switch (i.sev) {
                case ERROR -> "[ERR]";
                case WARN  -> "[!]";
                case INFO  -> "[i]";
            };
            System.out.printf("   %s key='%s'%n", marker, i.key);
            System.out.printf("       %s%n", i.message);
            if (i.value != null) {
                String shown = i.value.length() > 90 ? i.value.substring(0, 90) + "..." : i.value;
                System.out.printf("       -> %s%n", shown);
            }
        }
        System.out.println();
    }
}
