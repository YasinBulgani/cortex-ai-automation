package recorder;

import crypto.CredentialPreflightChecker;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Set;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Unit tests for {@link CredentialPreflightChecker}.
 *
 * We write synthetic .feature files to a temp dir and assert on the
 * collected aliases and the WARN/FAIL_FAST behaviour.
 */
class CredentialPreflightCheckerTest {

    @TempDir
    Path tmp;

    // ── Alias collection ─────────────────────────────────────────────────

    @Test
    void collectAliases_findsPasswordSteps(@TempDir Path dir) throws IOException {
        Files.writeString(dir.resolve("login.feature"),
            "Feature: Login\n"
            + "  Scenario: happy path\n"
            + "    When I enter encrypted password alias \"admin_password\" into \"pass\"\n"
        );
        Set<String> aliases = CredentialPreflightChecker.collectAliases(dir.toString());
        assertEquals(Set.of("admin_password"), aliases);
    }

    @Test
    void collectAliases_deduplicatesAcrossFiles(@TempDir Path dir) throws IOException {
        Files.writeString(dir.resolve("a.feature"),
            "When I enter encrypted password alias \"shared_pass\" into \"f\"\n");
        Files.writeString(dir.resolve("b.feature"),
            "When I enter encrypted password alias \"shared_pass\" into \"g\"\n"
            + "When I enter encrypted password alias \"other_pass\" into \"h\"\n");
        Set<String> aliases = CredentialPreflightChecker.collectAliases(dir.toString());
        assertEquals(Set.of("shared_pass", "other_pass"), aliases);
    }

    @Test
    void collectAliases_envPatternIncluded(@TempDir Path dir) throws IOException {
        Files.writeString(dir.resolve("ci.feature"),
            "When I enter encrypted password alias \"${ENV:CI_SECRET}\" into \"x\"\n");
        Set<String> aliases = CredentialPreflightChecker.collectAliases(dir.toString());
        assertTrue(aliases.contains("${ENV:CI_SECRET}"));
    }

    @Test
    void collectAliases_emptyDirReturnsEmpty(@TempDir Path dir) {
        Set<String> aliases = CredentialPreflightChecker.collectAliases(dir.toString());
        assertTrue(aliases.isEmpty());
    }

    @Test
    void collectAliases_nonexistentPathReturnsEmpty() {
        Set<String> aliases = CredentialPreflightChecker.collectAliases("/tmp/does_not_exist_xyz_99");
        assertTrue(aliases.isEmpty());
    }

    @Test
    void collectAliases_recursiveInSubdirectory(@TempDir Path dir) throws IOException {
        Path sub = dir.resolve("sub");
        Files.createDirectories(sub);
        Files.writeString(sub.resolve("deep.feature"),
            "When I enter encrypted password alias \"deep_alias\" into \"z\"\n");
        Set<String> aliases = CredentialPreflightChecker.collectAliases(dir.toString());
        assertTrue(aliases.contains("deep_alias"));
    }

    // ── ENV override validation ──────────────────────────────────────────

    @Test
    void check_envAlias_knownVar_doesNotThrow(@TempDir Path dir) throws IOException {
        // PATH is always set — use it as a CI secret stand-in
        Files.writeString(dir.resolve("env.feature"),
            "When I enter encrypted password alias \"${ENV:PATH}\" into \"pass\"\n");
        // Should not throw
        assertDoesNotThrow(() ->
            CredentialPreflightChecker.check(dir.toString(), CredentialPreflightChecker.Mode.FAIL_FAST));
    }

    @Test
    void check_envAlias_unsetVar_failFast_throws(@TempDir Path dir) throws IOException {
        Files.writeString(dir.resolve("env.feature"),
            "When I enter encrypted password alias \"${ENV:CORTEX_NONEXISTENT_VAR_XYZ}\" into \"pass\"\n");
        CredentialPreflightChecker.PreflightException ex = assertThrows(
            CredentialPreflightChecker.PreflightException.class,
            () -> CredentialPreflightChecker.check(dir.toString(),
                CredentialPreflightChecker.Mode.FAIL_FAST)
        );
        assertTrue(ex.getMessage().contains("CORTEX_NONEXISTENT_VAR_XYZ"));
    }

    @Test
    void check_envAlias_unsetVar_warnMode_doesNotThrow(@TempDir Path dir) throws IOException {
        Files.writeString(dir.resolve("env.feature"),
            "When I enter encrypted password alias \"${ENV:CORTEX_NONEXISTENT_VAR_XYZ}\" into \"pass\"\n");
        // Should NOT throw in WARN mode
        assertDoesNotThrow(() ->
            CredentialPreflightChecker.check(dir.toString(), CredentialPreflightChecker.Mode.WARN));
    }

    // ── Normal alias (no password.properties in test JVM, so alias will be missing) ─

    @Test
    void check_missingNormalAlias_failFast_throws(@TempDir Path dir) throws IOException {
        Files.writeString(dir.resolve("pw.feature"),
            "When I enter encrypted password alias \"totally_missing_alias_xyz\" into \"p\"\n");
        // password.properties won't have this entry → PreflightException
        CredentialPreflightChecker.PreflightException ex = assertThrows(
            CredentialPreflightChecker.PreflightException.class,
            () -> CredentialPreflightChecker.check(dir.toString(),
                CredentialPreflightChecker.Mode.FAIL_FAST)
        );
        assertTrue(ex.getMessage().contains("totally_missing_alias_xyz"));
    }

    @Test
    void check_emptyFeatureDir_doesNotThrow(@TempDir Path dir) {
        assertDoesNotThrow(() ->
            CredentialPreflightChecker.check(dir.toString(), CredentialPreflightChecker.Mode.FAIL_FAST));
    }
}
