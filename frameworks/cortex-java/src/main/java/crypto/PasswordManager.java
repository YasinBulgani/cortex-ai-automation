package crypto;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.util.Properties;

public class PasswordManager {
    private static final Properties properties = new Properties();
    private static final String PASSWORD_PATH = "src/main/resources/password.properties";

    static {
        File f = new File(PASSWORD_PATH);
        if (f.exists()) {
            try (FileInputStream fis = new FileInputStream(f)) {
                properties.load(fis);
            } catch (IOException e) {
                // Corrupt or unreadable file — log and continue with empty properties.
                // Throwing here crashes the JVM at class-load time (e.g. during a
                // fresh-clone recorder run before the file has been created), which is
                // far worse than starting with an empty credential store.
                System.err.println("[PasswordManager] WARNING: could not read " + PASSWORD_PATH
                        + ": " + e.getMessage() + " — starting with empty credential store.");
            }
        } else {
            // File absent on a fresh clone / CI environment — expected, not an error.
            System.out.println("[PasswordManager] " + PASSWORD_PATH
                    + " not found — starting with empty credential store (will be created on first save).");
        }
    }

    public static String getPassword(String alias) {
        return properties.getProperty("encrypted.password." + alias);
    }

    public static synchronized void setPassword(String alias, String encryptedValue) {
        properties.setProperty("encrypted.password." + alias, encryptedValue);
    }

    public static boolean contains(String alias) {
        return properties.containsKey("encrypted.password." + alias);
    }

    /**
     * Atomically persists the in-memory credential store to disk.
     *
     * <p>Write strategy:
     * <ol>
     *   <li>Serialize to a {@code .tmp} sibling file in the same directory.</li>
     *   <li>Atomically rename (move) the temp file over the target using
     *       {@link java.nio.file.Files#move} with {@code REPLACE_EXISTING} +
     *       {@code ATOMIC_MOVE}. On POSIX file systems this is a single
     *       {@code rename(2)} syscall — readers never see a half-written file.
     *       On Windows (FAT/NTFS) the JVM falls back to a non-atomic copy-then-delete
     *       if the FS doesn't support it, which is still much safer than
     *       direct {@link FileOutputStream} truncation.</li>
     * </ol>
     *
     * <p>The method is {@code synchronized} so concurrent recorder threads
     * (shutdown hook + stop-signal path) cannot interleave writes.</p>
     */
    public static synchronized void save() {
        Path target = Path.of(PASSWORD_PATH);
        Path tmp    = target.resolveSibling(target.getFileName() + ".tmp");
        try {
            // Ensure parent directory exists (handles fresh-clone where
            // src/main/resources/ might not yet contain password.properties).
            Files.createDirectories(target.getParent());
            try (FileOutputStream out = new FileOutputStream(tmp.toFile())) {
                properties.store(out, "Managed by PasswordManager — do not edit manually");
            }
            Files.move(tmp, target,
                    StandardCopyOption.REPLACE_EXISTING,
                    StandardCopyOption.ATOMIC_MOVE);
        } catch (IOException e) {
            // Best-effort cleanup of the temp file.
            try { Files.deleteIfExists(tmp); } catch (IOException ignored) {}
            throw new RuntimeException("❌ Failed to save password.properties: " + e.getMessage(), e);
        }
    }

    public static String getRaw(String key) {
        return properties.getProperty(key);
    }

    /**
     * Returns a comma-separated list of the short alias names currently stored
     * (the {@code encrypted.password.} prefix is stripped for readability).
     * Used in error messages so the developer can immediately see what aliases
     * exist without having to open the file manually.
     *
     * <p>Returns {@code "(none)"} when the store is empty.</p>
     */
    public static String listAliases() {
        String prefix = "encrypted.password.";
        java.util.List<String> aliases = properties.stringPropertyNames().stream()
                .filter(k -> k.startsWith(prefix))
                .map(k -> k.substring(prefix.length()))
                .sorted()
                .collect(java.util.stream.Collectors.toList());
        return aliases.isEmpty() ? "(none)" : String.join(", ", aliases);
    }

}

