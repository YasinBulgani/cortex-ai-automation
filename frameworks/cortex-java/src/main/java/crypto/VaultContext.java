package crypto;

/**
 * Thread-local holder for the {@link FeatureVault} that is active during the
 * current scenario execution.
 *
 * <h3>Lifecycle</h3>
 * <pre>
 *   // Cucumber @Before hook — set at scenario start:
 *   VaultContext.set(new FeatureVault(scenarioFeatureName));
 *
 *   // Step definition — resolve automatically:
 *   String pwd = DecryptUtil.decryptPasswordByAlias(alias);
 *
 *   // Cucumber @After hook — clear to avoid cross-scenario leakage:
 *   VaultContext.clear();
 * </pre>
 *
 * <h3>Fallback</h3>
 * {@link #get()} never returns {@code null} — if no vault has been set for
 * the current thread it returns a no-op stub that delegates everything to
 * {@link PasswordManager} (the global store).  This keeps existing tests that
 * do not use per-feature vaults working without any changes.
 */
public final class VaultContext {

    private VaultContext() {}

    /** Sentinel stub used when no feature-level vault is active. */
    private static final FeatureVault GLOBAL_ONLY = new FeatureVault("__global__") {
        /** Override: global vault has no local aliases — always fall back. */
        @Override public String  getPassword(String alias) { return crypto.PasswordManager.getPassword(alias); }
        @Override public boolean containsLocal(String alias) { return false; }
        @Override public boolean contains(String alias) { return crypto.PasswordManager.contains(alias); }
        @Override public boolean exists() { return false; }
    };

    private static final ThreadLocal<FeatureVault> HOLDER = ThreadLocal.withInitial(() -> GLOBAL_ONLY);

    /**
     * Sets the vault for the current thread.
     *
     * @param vault the {@link FeatureVault} for the scenario about to run;
     *              must not be {@code null}.
     */
    public static void set(FeatureVault vault) {
        if (vault == null) throw new IllegalArgumentException("vault must not be null");
        HOLDER.set(vault);
    }

    /**
     * Returns the vault for the current thread.
     * Guaranteed non-null — returns the global-only stub if none is set.
     */
    public static FeatureVault get() {
        return HOLDER.get();
    }

    /**
     * Clears the vault for the current thread, resetting it to the global-only stub.
     * Should be called from a Cucumber {@code @After} hook.
     */
    public static void clear() {
        HOLDER.set(GLOBAL_ONLY);
    }

    /**
     * Convenience — returns {@code true} if a feature-level vault (not the stub)
     * is active on the current thread.
     */
    public static boolean hasFeatureVault() {
        return HOLDER.get() != GLOBAL_ONLY;
    }
}
