package crypto;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.util.LinkedHashSet;
import java.util.Properties;
import java.util.Set;
import java.util.stream.Collectors;

/**
 * Per-feature credential vault.
 *
 * <p>Each {@code .feature} file can have its own isolated credential store at
 * {@code src/test/resources/credentials/<featureName>.vault.properties}.
 * When an alias is not found in the feature-level vault, lookups automatically
 * fall back to the global {@link PasswordManager} store so that shared
 * credentials do not need to be duplicated per feature.</p>
 *
 * <h3>Resolution order for {@link #getPassword(String)}</h3>
 * <ol>
 *   <li>Feature-level vault file (if it exists and contains the alias).</li>
 *   <li>Global {@code password.properties} via {@link PasswordManager}.</li>
 * </ol>
 *
 * <h3>Vault file naming convention</h3>
 * <pre>
 *   Feature file:  src/test/resources/features/checkout/guest_checkout.feature
 *   Vault file:    src/test/resources/credentials/guest_checkout.vault.properties
 * </pre>
 * Only the bare filename (without directory or extension) is used as the key.
 * This keeps the vault directory flat and easy to manage.
 *
 * <h3>Thread safety</h3>
 * {@link #setPassword} and {@link #save} are {@code synchronized} on the
 * vault instance.  Each feature test gets its own {@code FeatureVault}
 * instance via {@link VaultContext}, so contention is minimal.
 */
public class FeatureVault {

    /** Root directory for all per-feature vault files. */
    public static final String VAULT_DIR = "src/test/resources/credentials";

    private static final String VAULT_SUFFIX = ".vault.properties";

    private final String featureName;
    private final Path   vaultPath;
    private final Properties properties = new Properties();
    private boolean loaded = false;

    /**
     * Creates a vault scoped to the given feature name.
     *
     * @param featureName bare name of the feature (no path, no extension),
     *                    e.g. {@code "guest_checkout"}.
     */
    public FeatureVault(String featureName) {
        this.featureName = featureName;
        this.vaultPath   = Path.of(VAULT_DIR, featureName + VAULT_SUFFIX);
        load();
    }

    /**
     * Derives a vault for a feature file path.
     *
     * @param featureFilePath path like {@code "src/test/resources/features/login.feature"}
     *                        or just {@code "login.feature"}.
     */
    public static FeatureVault forFile(String featureFilePath) {
        String raw = Path.of(featureFilePath).getFileName().toString();
        String name = raw.endsWith(".feature") ? raw.substring(0, raw.length() - ".feature".length()) : raw;
        return new FeatureVault(name);
    }

    // ── Load ─────────────────────────────────────────────────────────────────

    private synchronized void load() {
        File f = vaultPath.toFile();
        if (!f.exists()) {
            loaded = true; // empty vault — that is fine
            return;
        }
        try (FileInputStream fis = new FileInputStream(f)) {
            properties.load(fis);
            loaded = true;
        } catch (IOException e) {
            System.err.println("[FeatureVault:" + featureName + "] WARNING: could not read "
                    + vaultPath + ": " + e.getMessage());
            loaded = true;
        }
    }

    // ── Read ──────────────────────────────────────────────────────────────────

    /**
     * Returns the encrypted password for {@code alias} from this vault,
     * or falls back to the global {@link PasswordManager} store.
     *
     * @return the encrypted value string, or {@code null} if absent in both stores.
     */
    public String getPassword(String alias) {
        String key = "encrypted.password." + alias;
        String val = properties.getProperty(key);
        if (val != null) return val;
        // Fall back to global vault.
        return PasswordManager.getPassword(alias);
    }

    /** {@code true} if the alias exists in this feature vault (not falling back). */
    public boolean containsLocal(String alias) {
        return properties.containsKey("encrypted.password." + alias);
    }

    /** {@code true} if the alias exists in this vault OR the global store. */
    public boolean contains(String alias) {
        return containsLocal(alias) || PasswordManager.contains(alias);
    }

    // ── Write ─────────────────────────────────────────────────────────────────

    /**
     * Stores an encrypted password in this feature-level vault (in memory only).
     * Call {@link #save()} to persist to disk.
     */
    public synchronized void setPassword(String alias, String encryptedValue) {
        properties.setProperty("encrypted.password." + alias, encryptedValue);
    }

    /**
     * Atomically persists this vault's in-memory state to disk.
     *
     * <p>Uses the same {@code .tmp} + {@code ATOMIC_MOVE} strategy as
     * {@link PasswordManager#save()} so readers never see a half-written file.</p>
     */
    public synchronized void save() {
        Path tmp = vaultPath.resolveSibling(vaultPath.getFileName() + ".tmp");
        try {
            Files.createDirectories(vaultPath.getParent());
            try (FileOutputStream out = new FileOutputStream(tmp.toFile())) {
                properties.store(out,
                        "Per-feature vault for [" + featureName + "] — managed by FeatureVault");
            }
            Files.move(tmp, vaultPath,
                    StandardCopyOption.REPLACE_EXISTING,
                    StandardCopyOption.ATOMIC_MOVE);
        } catch (IOException e) {
            try { Files.deleteIfExists(tmp); } catch (IOException ignored) {}
            throw new RuntimeException(
                    "❌ Failed to save vault for feature [" + featureName + "]: " + e.getMessage(), e);
        }
    }

    // ── Inspection ────────────────────────────────────────────────────────────

    /** Returns the feature name this vault is scoped to. */
    public String getFeatureName() { return featureName; }

    /** Returns the path to the vault file (may not exist yet). */
    public Path getVaultPath() { return vaultPath; }

    /** Returns {@code true} if the vault file exists on disk. */
    public boolean exists() { return vaultPath.toFile().exists(); }

    /**
     * Returns the alias names stored <em>locally</em> in this vault
     * (does not include global fallback aliases).
     */
    public Set<String> localAliases() {
        String prefix = "encrypted.password.";
        return properties.stringPropertyNames().stream()
                .filter(k -> k.startsWith(prefix))
                .map(k -> k.substring(prefix.length()))
                .sorted()
                .collect(Collectors.toCollection(LinkedHashSet::new));
    }

    /**
     * Human-readable comma-separated list of local aliases (for error messages).
     * Returns {@code "(none)"} when this vault is empty.
     */
    public String listLocalAliases() {
        Set<String> a = localAliases();
        return a.isEmpty() ? "(none)" : String.join(", ", a);
    }

    @Override
    public String toString() {
        return "FeatureVault[" + featureName + ", path=" + vaultPath
                + ", localAliases=" + listLocalAliases() + "]";
    }
}
