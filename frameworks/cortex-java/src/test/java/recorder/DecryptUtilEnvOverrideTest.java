package recorder;

import org.junit.jupiter.api.Test;
import utils.DecryptUtil;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Unit tests for DecryptUtil — ${ENV:VAR_NAME} CI override pattern.
 *
 * System.getenv() cannot be mocked easily in plain JUnit without Mockito or
 * PowerMock, so we test:
 *   1. An env var that IS set in the test process returns its value.
 *   2. An alias that does NOT match the ${ENV:...} pattern falls through to
 *      normal lookup (expected to throw alias-not-found, not env-not-set).
 *   3. A well-formed ${ENV:...} alias pointing to an unset var throws with a
 *      clear actionable message.
 */
class DecryptUtilEnvOverrideTest {

    // ── helper: most CI passwords are set; PATH is always present ────────
    private static final String ALWAYS_SET_VAR = "PATH";

    // ─────────────────────────────────────────────────────────────────────

    @Test
    void envOverride_knownEnvVar_returnsValue() throws Exception {
        // PATH is always set; use it as a stand-in for a real CI secret.
        String alias = "${ENV:" + ALWAYS_SET_VAR + "}";
        String result = DecryptUtil.decryptPasswordByAlias(alias);
        assertEquals(System.getenv(ALWAYS_SET_VAR), result,
            "ENV override should return the raw env var value without decryption");
    }

    @Test
    void envOverride_unsetVar_throwsWithActionableMessage() {
        String alias = "${ENV:CORTEX_CI_SECRET_THAT_DOES_NOT_EXIST_99}";
        IllegalArgumentException ex = assertThrows(IllegalArgumentException.class,
            () -> DecryptUtil.decryptPasswordByAlias(alias));

        assertTrue(ex.getMessage().contains("CORTEX_CI_SECRET_THAT_DOES_NOT_EXIST_99"),
            "Error message should contain the env var name");
        assertTrue(ex.getMessage().contains("export ") || ex.getMessage().contains("CI pipeline"),
            "Error message should contain fix instructions");
    }

    @Test
    void normalAlias_doesNotTriggerEnvPath() {
        // "recordedPassword" does not start with "${ENV:" — should attempt
        // password.properties lookup and throw alias-not-found, not env-not-set.
        Exception ex = assertThrows(Exception.class,
            () -> DecryptUtil.decryptPasswordByAlias("nonexistent_alias_xyz_for_test"));

        // Must NOT be the ENV-override error
        assertFalse(ex.getMessage().contains("environment variable"),
            "Normal alias lookup should not produce ENV override error");
        // Should contain alias-not-found wording
        assertTrue(ex.getMessage().contains("nonexistent_alias_xyz_for_test"),
            "Error should reference the queried alias");
    }

    @Test
    void nullAlias_doesNotTriggerEnvPath() {
        // null should bypass the ENV check and hit the PasswordManager path,
        // which returns null → alias-not-found
        assertThrows(Exception.class,
            () -> DecryptUtil.decryptPasswordByAlias(null));
    }

    @Test
    void envOverride_partialMatch_doesNotTrigger() throws Exception {
        // "${ENV:PATH" (missing closing brace) must NOT trigger ENV path
        Exception ex = assertThrows(Exception.class,
            () -> DecryptUtil.decryptPasswordByAlias("${ENV:PATH"));
        // This falls through to normal lookup — just verify no NPE/env-path message
        assertFalse(ex.getMessage() != null && ex.getMessage().contains("environment variable"),
            "Partial ENV pattern should not trigger ENV override");
    }
}
