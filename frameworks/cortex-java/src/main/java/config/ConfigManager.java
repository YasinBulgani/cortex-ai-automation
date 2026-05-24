package config;

import java.io.*;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.Properties;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Configuration manager.
 *
 * Read order (first hit wins for a key):
 *   1) System property -Dkey=value
 *   2) Environment variable (KEY_NAME, key converted to UPPER_SNAKE)
 *   3) .env file in the project root (KEY=VALUE per line)
 *   4) src/main/resources/config.properties on classpath, with filesystem fallback
 *
 * Values support ${ENV:VAR} and ${ENV:VAR:default} placeholders so the
 * properties file can stay free of secrets.
 */
public class ConfigManager {

    private static final Properties properties = new Properties();
    private static final Properties envFile = new Properties();
    private static final String CONFIG_RESOURCE = "config.properties";
    private static final String CONFIG_FS_FALLBACK = "src/main/resources/config.properties";
    private static final String ENV_FILE = ".env";

    private static final Pattern PLACEHOLDER =
            Pattern.compile("\\$\\{ENV:([A-Z0-9_]+)(?::([^}]*))?}");

    static {
        loadEnvFile();
        loadEnvSpecificFile();   // E23 fix: env-specific override
        loadProperties();
    }

    private static void loadEnvFile() {
        loadEnvFileFrom(Paths.get(ENV_FILE));
    }

    /**
     * E23 fix — multi-environment support.
     *
     * When {@code -Dcortex.env=staging} is passed (or {@code CORTEX_ENV=staging}
     * in env vars), this loads <code>.env.staging</code> if present, with values
     * overriding the generic <code>.env</code> file.
     *
     * Resolution order (high to low):
     *   1. -D / env var (always wins)
     *   2. .env.&lt;active-env&gt; (env-specific, this method)
     *   3. .env (generic, loadEnvFile)
     *   4. config.properties (loadProperties)
     */
    private static void loadEnvSpecificFile() {
        String activeEnv = System.getProperty("cortex.env",
                System.getenv().getOrDefault("CORTEX_ENV", ""));
        if (activeEnv == null || activeEnv.isBlank()) return;
        Path envPath = Paths.get(".env." + activeEnv);
        if (!Files.exists(envPath)) {
            System.err.println("WARN: cortex.env=" + activeEnv
                    + " ama " + envPath + " bulunamadı");
            return;
        }
        System.out.println("[Config] Loading env-specific overrides: " + envPath);
        loadEnvFileFrom(envPath);
    }

    private static void loadEnvFileFrom(Path envPath) {
        if (!Files.exists(envPath)) return;
        try (BufferedReader br = Files.newBufferedReader(envPath)) {
            String line;
            while ((line = br.readLine()) != null) {
                line = line.trim();
                if (line.isEmpty() || line.startsWith("#")) continue;
                int eq = line.indexOf('=');
                if (eq <= 0) continue;
                String k = line.substring(0, eq).trim();
                String v = line.substring(eq + 1).trim();
                if (v.length() >= 2
                        && ((v.startsWith("\"") && v.endsWith("\""))
                                || (v.startsWith("'") && v.endsWith("'")))) {
                    v = v.substring(1, v.length() - 1);
                }
                envFile.setProperty(k, v);
            }
        } catch (IOException e) {
            System.err.println("WARN: cannot read " + envPath + ": " + e.getMessage());
        }
    }

    private static void loadProperties() {
        InputStream in = ConfigManager.class.getClassLoader().getResourceAsStream(CONFIG_RESOURCE);
        if (in != null) {
            try (in) {
                properties.load(in);
                return;
            } catch (IOException e) {
                System.err.println("WARN: classpath config.properties unreadable, trying fs fallback");
            }
        }
        try (FileInputStream fis = new FileInputStream(CONFIG_FS_FALLBACK)) {
            properties.load(fis);
        } catch (IOException e) {
            System.err.println("ERROR: config.properties not found (neither classpath nor fs)");
            throw new RuntimeException(e);
        }
    }

    /** Resolve ${ENV:VAR} and ${ENV:VAR:default} placeholders against env file -> OS env. */
    private static String resolve(String value) {
        if (value == null) return null;
        Matcher m = PLACEHOLDER.matcher(value);
        StringBuilder sb = new StringBuilder();
        while (m.find()) {
            String var = m.group(1);
            String def = m.group(2);
            String resolved = envFile.getProperty(var);
            if (resolved == null) resolved = System.getenv(var);
            if (resolved == null) resolved = def;
            if (resolved == null) resolved = "";
            m.appendReplacement(sb, Matcher.quoteReplacement(resolved));
        }
        m.appendTail(sb);
        return sb.toString();
    }

    public static String getProperty(String key) {
        // 1) -Dkey=value
        String sys = System.getProperty(key);
        if (sys != null && !sys.isEmpty()) return sys;
        // 2) environment as UPPER_SNAKE
        String envKey = key.toUpperCase().replace('.', '_').replace('-', '_');
        String env = System.getenv(envKey);
        if (env != null && !env.isEmpty()) return env;
        // 3) .env file
        String fileVal = envFile.getProperty(envKey);
        if (fileVal == null) fileVal = envFile.getProperty(key);
        if (fileVal != null && !fileVal.isEmpty()) return fileVal;
        // 4) config.properties (with placeholder substitution)
        return resolve(properties.getProperty(key));
    }

    public static String getProperty(String key, String defaultValue) {
        String v = getProperty(key);
        return (v == null || v.isEmpty()) ? defaultValue : v;
    }

    public static int getInt(String key, int defaultValue) {
        try { return Integer.parseInt(getProperty(key)); }
        catch (Exception e) { return defaultValue; }
    }

    public static boolean getBoolean(String key, boolean defaultValue) {
        String v = getProperty(key);
        return v == null ? defaultValue : Boolean.parseBoolean(v);
    }

    public static boolean containsKey(String key) {
        return properties.containsKey(key) || System.getenv(key) != null || System.getProperty(key) != null;
    }

    public static void setProperty(String key, String value) {
        properties.setProperty(key, value);
    }

    public static void save() {
        try (FileOutputStream output = new FileOutputStream(CONFIG_FS_FALLBACK)) {
            properties.store(output, "Updated by ConfigManager.save()");
        } catch (IOException e) {
            throw new RuntimeException("Failed to save config.properties", e);
        }
    }
}
