package crypto;

import config.ConfigManager;
import utils.DecryptUtil;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.*;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.stream.Stream;

/**
 * Pre-flight credential checker — Recorder #8.
 *
 * <p>Scans feature files for {@code I enter encrypted password alias "<alias>"}
 * steps and validates every referenced alias before the first scenario runs.
 * This surfaces missing or misconfigured credentials immediately — rather than
 * mid-suite, after wasting potentially hours of execution time.
 *
 * <h3>Validation rules per alias:</h3>
 * <ol>
 *   <li><b>{@code ${ENV:VAR_NAME}}</b> pattern — checks the env var is set and
 *       non-blank (no AES key required).</li>
 *   <li><b>Normal alias</b> — checks the alias exists in
 *       {@code password.properties} AND that the AES key is present (16 chars).
 *       Does NOT attempt actual decryption (that would require a round-trip and
 *       adds latency).</li>
 * </ol>
 *
 * <h3>Usage (wired into PwHooks @BeforeAll):</h3>
 * <pre>
 *   CredentialPreflightChecker.check("src/test/resources");
 * </pre>
 *
 * <h3>Severity modes:</h3>
 * <ul>
 *   <li>{@link Mode#WARN} — logs errors to stderr, does not abort the suite.
 *       Use during migration.</li>
 *   <li>{@link Mode#FAIL_FAST} (default) — throws {@link PreflightException}
 *       listing all failures so the suite fails before browser launch.</li>
 * </ul>
 */
public class CredentialPreflightChecker {

    // Step pattern: I enter encrypted password alias "ALIAS" into "FIELD"
    private static final Pattern ALIAS_STEP_PATTERN = Pattern.compile(
        "encrypted password alias\\s+\"([^\"]+)\"",
        Pattern.CASE_INSENSITIVE
    );

    private static final String ENV_PREFIX = "${ENV:";

    public enum Mode { WARN, FAIL_FAST }

    /** Thrown when FAIL_FAST mode finds credential problems. */
    public static class PreflightException extends RuntimeException {
        public PreflightException(String message) { super(message); }
    }

    // ── Public entry points ──────────────────────────────────────────────

    /**
     * Scan all {@code .feature} files under {@code featureRoot} and validate
     * referenced aliases. Uses {@link Mode#FAIL_FAST}.
     */
    public static void check(String featureRoot) {
        check(featureRoot, Mode.FAIL_FAST);
    }

    /**
     * Scan all {@code .feature} files under {@code featureRoot} and validate
     * referenced aliases.
     *
     * @param featureRoot root directory to scan (recursive)
     * @param mode        {@link Mode#WARN} or {@link Mode#FAIL_FAST}
     */
    public static void check(String featureRoot, Mode mode) {
        Set<String> aliases = collectAliases(featureRoot);
        if (aliases.isEmpty()) return;  // nothing to validate

        List<String> errors = new ArrayList<>();

        String aesKey = ConfigManager.getProperty("aes.key");
        boolean keyPresent = (aesKey != null && !aesKey.isBlank());
        boolean keyValid   = keyPresent && aesKey.length() == 16;

        for (String alias : aliases) {
            if (alias.startsWith(ENV_PREFIX) && alias.endsWith("}")) {
                // ${ENV:VAR_NAME} — check env var is set
                String varName = alias.substring(ENV_PREFIX.length(), alias.length() - 1);
                String val = System.getenv(varName);
                if (val == null || val.isBlank()) {
                    errors.add("  [ENV]  alias=\"" + alias + "\"  →  env var \"" + varName
                        + "\" is not set.\n"
                        + "         Fix: export " + varName + "=<password>  (or set in CI secrets)");
                }
            } else {
                // Normal alias — check password.properties entry
                String entry = PasswordManager.getPassword(alias);
                if (entry == null) {
                    errors.add("  [MISSING]  alias=\"" + alias + "\" not found in password.properties.\n"
                        + "             Known aliases: " + PasswordManager.listAliases() + "\n"
                        + "             Fix: re-record the scenario or run EncryptionManager manually.");
                } else if (!keyPresent) {
                    errors.add("  [NO KEY]  alias=\"" + alias + "\" found but CORTEX_AES_KEY is not set.\n"
                        + "            Fix: copy .env.example → .env and set CORTEX_AES_KEY=<16 chars>.");
                } else if (!keyValid) {
                    errors.add("  [BAD KEY]  alias=\"" + alias + "\": CORTEX_AES_KEY is "
                        + aesKey.length() + " chars (must be 16).\n"
                        + "             Fix: update CORTEX_AES_KEY in .env.");
                }
                // We intentionally skip actual decryption here — that's expensive and
                // requires a running cipher. A wrong key will surface at step execution with
                // the detailed message from DecryptUtil.decryptPasswordByAlias().
            }
        }

        if (errors.isEmpty()) {
            System.out.println("[Preflight] ✓ Credentials OK — " + aliases.size()
                + " alias(es) validated: " + aliases);
            return;
        }

        String report = "\n╔══ CREDENTIAL PREFLIGHT FAILED ═══════════════════════════════╗\n"
            + "║  The following credential aliases are misconfigured.          ║\n"
            + "║  Fix them before running the suite to avoid mid-run failures. ║\n"
            + "╚═══════════════════════════════════════════════════════════════╝\n"
            + String.join("\n\n", errors) + "\n";

        if (mode == Mode.WARN) {
            System.err.println("[Preflight] WARNING" + report);
        } else {
            throw new PreflightException(report);
        }
    }

    // ── Scanning ─────────────────────────────────────────────────────────

    /**
     * Walk {@code featureRoot} recursively, find all {@code .feature} files,
     * and return the set of unique alias strings referenced by password steps.
     */
    public static Set<String> collectAliases(String featureRoot) {
        Set<String> aliases = new LinkedHashSet<>();
        Path root = Paths.get(featureRoot);
        if (!Files.exists(root)) return aliases;

        try (Stream<Path> walk = Files.walk(root)) {
            walk.filter(p -> p.toString().endsWith(".feature"))
                .forEach(p -> {
                    try {
                        String content = Files.readString(p);
                        Matcher m = ALIAS_STEP_PATTERN.matcher(content);
                        while (m.find()) {
                            aliases.add(m.group(1));
                        }
                    } catch (IOException ignored) {}
                });
        } catch (IOException ignored) {}

        return aliases;
    }
}
