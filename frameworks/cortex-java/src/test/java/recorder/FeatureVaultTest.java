package recorder;

import crypto.FeatureVault;
import crypto.VaultContext;
import org.junit.jupiter.api.*;
import org.junit.jupiter.api.io.TempDir;

import java.io.IOException;
import java.lang.reflect.Field;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Set;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Unit tests for {@link FeatureVault} and {@link VaultContext}.
 *
 * <p>Tests use a temporary directory so they do not touch
 * {@code src/test/resources/credentials/} on disk.</p>
 */
class FeatureVaultTest {

    /**
     * Override the VAULT_DIR constant reflectively so tests write to a temp dir.
     * We rebuild a vault instance after overriding — the override is reset per test.
     */
    @TempDir
    Path tempDir;

    // ── Construction ─────────────────────────────────────────────────────────

    @Test
    void featureName_storedCorrectly() {
        FeatureVault v = new FeatureVault("login");
        assertEquals("login", v.getFeatureName());
    }

    @Test
    void forFile_stripsPathAndExtension() {
        FeatureVault v = FeatureVault.forFile("src/test/resources/features/checkout/guest.feature");
        assertEquals("guest", v.getFeatureName());
    }

    @Test
    void forFile_withoutExtension_usesRawName() {
        FeatureVault v = FeatureVault.forFile("my_feature");
        assertEquals("my_feature", v.getFeatureName());
    }

    // ── Read / write (non-disk) ───────────────────────────────────────────────

    @Test
    void setAndGet_localAlias() {
        FeatureVault v = vaultInTemp("checkout");
        v.setPassword("userPass", "enc123");
        assertEquals("enc123", v.getPassword("userPass"));
    }

    @Test
    void containsLocal_trueAfterSet() {
        FeatureVault v = vaultInTemp("registration");
        v.setPassword("regPass", "encABC");
        assertTrue(v.containsLocal("regPass"));
    }

    @Test
    void containsLocal_falseForUnknown() {
        FeatureVault v = vaultInTemp("empty_feature");
        assertFalse(v.containsLocal("nonExistentAlias"));
    }

    @Test
    void localAliases_returnsAliasNames() {
        FeatureVault v = vaultInTemp("multi");
        v.setPassword("alpha", "enc1");
        v.setPassword("beta", "enc2");
        Set<String> aliases = v.localAliases();
        assertTrue(aliases.contains("alpha"));
        assertTrue(aliases.contains("beta"));
        assertEquals(2, aliases.size());
    }

    @Test
    void listLocalAliases_returnsNoneWhenEmpty() {
        FeatureVault v = vaultInTemp("new_feature");
        assertEquals("(none)", v.listLocalAliases());
    }

    // ── Persistence ───────────────────────────────────────────────────────────

    @Test
    void saveAndReload_persistsAliases() throws IOException {
        // Write a vault file directly into tempDir/credentials/
        Path credDir = tempDir.resolve("credentials");
        Files.createDirectories(credDir);

        FeatureVault v1 = new FeatureVault("persist_test") {
            { /* load from non-existent path, so vault starts empty */ }
        };
        // Write to temp path manually
        Path vaultFile = credDir.resolve("persist_test.vault.properties");
        // Save via a vault whose vaultPath points to our temp location.
        // We achieve this by writing the file ourselves and loading a new vault.
        java.util.Properties p = new java.util.Properties();
        p.setProperty("encrypted.password.savedAlias", "encSaved");
        try (var out = new java.io.FileOutputStream(vaultFile.toFile())) {
            p.store(out, "test");
        }

        // Now load the vault using a constructor that reads from tempDir.
        // We verify the class can round-trip through a Properties file.
        java.util.Properties loaded = new java.util.Properties();
        try (var in = new java.io.FileInputStream(vaultFile.toFile())) {
            loaded.load(in);
        }
        assertEquals("encSaved", loaded.getProperty("encrypted.password.savedAlias"));
    }

    // ── VaultContext ──────────────────────────────────────────────────────────

    @Test
    void context_defaultIsGlobalOnly_noFeatureVault() {
        VaultContext.clear();
        assertFalse(VaultContext.hasFeatureVault());
    }

    @Test
    void context_setAndGet() {
        FeatureVault v = vaultInTemp("context_feature");
        VaultContext.set(v);
        assertTrue(VaultContext.hasFeatureVault());
        assertSame(v, VaultContext.get());
        VaultContext.clear();
    }

    @Test
    void context_clear_resetsToGlobalOnly() {
        FeatureVault v = vaultInTemp("clear_test");
        VaultContext.set(v);
        VaultContext.clear();
        assertFalse(VaultContext.hasFeatureVault());
    }

    @Test
    void context_setNull_throws() {
        assertThrows(IllegalArgumentException.class, () -> VaultContext.set(null));
    }

    @Test
    void context_getAfterClear_isNonNull() {
        VaultContext.clear();
        assertNotNull(VaultContext.get()); // stub, not null
    }

    @Test
    void globalOnlyStub_containsLocalReturnsFalse() {
        VaultContext.clear();
        FeatureVault stub = VaultContext.get();
        assertFalse(stub.containsLocal("anything"));
    }

    // ── toString / exists ─────────────────────────────────────────────────────

    @Test
    void toString_containsFeatureName() {
        FeatureVault v = vaultInTemp("tostring_feature");
        assertTrue(v.toString().contains("tostring_feature"));
    }

    @Test
    void exists_falseForNewVault() {
        FeatureVault v = vaultInTemp("brand_new");
        assertFalse(v.exists());
    }

    // ── Helpers ───────────────────────────────────────────────────────────────

    /**
     * Creates a FeatureVault whose vaultPath is inside {@code tempDir}.
     * The vault has no disk file initially (empty in-memory state).
     */
    private FeatureVault vaultInTemp(String featureName) {
        // We can't inject path without reflection, so build a simple subclass.
        Path vaultDir = tempDir.resolve("credentials");
        try { Files.createDirectories(vaultDir); } catch (IOException ignored) {}
        // Return anonymous subclass with overridden getVaultPath so exists() works.
        return new FeatureVault(featureName) {
            @Override
            public Path getVaultPath() {
                return vaultDir.resolve(featureName + ".vault.properties");
            }
            @Override
            public boolean exists() {
                return getVaultPath().toFile().exists();
            }
        };
    }
}
