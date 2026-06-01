package playwright;

import java.io.BufferedReader;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Optional;

/**
 * E23 — Environment profile loader for multi-environment test runs.
 *
 * Profile is selected by (first match wins):
 *   1. {@code -Dcortex.env=<name>} JVM property
 *   2. {@code CORTEX_ENV} OS environment variable
 *   3. Default: {@code "local"}
 *
 * The profile name maps to {@code config/environments/<name>.properties},
 * resolved relative to the working directory.  The file is plain
 * {@code key=value} (java.util.Properties syntax) — no YAML dep needed.
 *
 * Lookup is case-insensitive on the key (the file may use {@code base_url}
 * or {@code BASE_URL}; both resolve the same).  Values are returned as-is,
 * with leading/trailing whitespace trimmed.
 *
 * Typical use:
 *   String url = EnvironmentConfig.get("base_url")
 *                                 .orElse("https://default.example");
 *
 * The class is also wired into {@code PwCommonSteps.resolveEnv} so
 * {@code ${ENV:base_url}} placeholders in {@code .feature} files
 * automatically resolve through the active profile before falling back
 * to OS env vars.  Profile values trump OS env so a CI runner setting
 * a global {@code BASE_URL} cannot accidentally override the deliberate
 * choice of "this scenario runs against staging".
 */
public final class EnvironmentConfig {

    private EnvironmentConfig() {}

    private static final String ENV_PROP = "cortex.env";
    private static final String ENV_VAR  = "CORTEX_ENV";
    private static final String DEFAULT_ENV = "local";

    // Cached after first load. The whole config rarely changes during a JVM
    // lifetime; reloading on every lookup would be wasteful (and YAML/Properties
    // parse + I/O isn't free across 10K-step suites).
    private static volatile Map<String, String> cache;
    private static volatile String loadedFor;

    /**
     * Returns the currently active profile name (e.g. "staging").
     * Side-effect free: does not load the file.
     */
    public static String activeProfile() {
        String p = System.getProperty(ENV_PROP);
        if (p == null || p.isBlank()) p = System.getenv(ENV_VAR);
        if (p == null || p.isBlank()) p = DEFAULT_ENV;
        return p.trim();
    }

    /**
     * Look up a key in the active profile.
     * Returns an empty {@link Optional} if either the profile file does not
     * exist or the key is missing — callers decide whether to fall back
     * (to OS env, to a hard-coded default, or to fail loudly).
     */
    public static Optional<String> get(String key) {
        if (key == null || key.isBlank()) return Optional.empty();
        Map<String, String> cfg = load();
        String v = cfg.get(key.toLowerCase());
        return (v == null || v.isBlank()) ? Optional.empty() : Optional.of(v);
    }

    /** Snapshot of the active profile — for diagnostics, never modify. */
    public static Map<String, String> snapshot() {
        return Collections.unmodifiableMap(load());
    }

    private static Map<String, String> load() {
        String profile = activeProfile();
        Map<String, String> c = cache;
        if (c != null && profile.equals(loadedFor)) return c;
        synchronized (EnvironmentConfig.class) {
            c = cache;
            if (c != null && profile.equals(loadedFor)) return c;
            c = readProfileFile(profile);
            cache = c;
            loadedFor = profile;
            return c;
        }
    }

    private static Map<String, String> readProfileFile(String profile) {
        Map<String, String> result = new LinkedHashMap<>();
        Path file = Paths.get("config", "environments", profile + ".properties");
        if (!Files.exists(file)) {
            // Silent: missing file just means everything falls through to
            // OS env / defaults. This keeps fresh checkouts working with no
            // mandatory file setup.
            System.out.println("[EnvironmentConfig] profile '" + profile
                    + "' has no file at " + file + " — using OS env only");
            return result;
        }
        try (BufferedReader r = Files.newBufferedReader(file, StandardCharsets.UTF_8)) {
            String line;
            while ((line = r.readLine()) != null) {
                String trimmed = line.trim();
                if (trimmed.isEmpty() || trimmed.startsWith("#") || trimmed.startsWith("//")) continue;
                int eq = trimmed.indexOf('=');
                if (eq <= 0) continue; // skip malformed lines silently
                String key = trimmed.substring(0, eq).trim().toLowerCase();
                String value = trimmed.substring(eq + 1).trim();
                // Strip surrounding quotes if both sides match
                if (value.length() >= 2
                        && ((value.startsWith("\"") && value.endsWith("\""))
                         || (value.startsWith("'")  && value.endsWith("'")))) {
                    value = value.substring(1, value.length() - 1);
                }
                result.put(key, value);
            }
            System.out.println("[EnvironmentConfig] loaded " + result.size()
                    + " keys from profile '" + profile + "'");
        } catch (IOException e) {
            System.err.println("[EnvironmentConfig] read failed for " + file
                    + ": " + e.getMessage());
        }
        return result;
    }
}
