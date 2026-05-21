package recorder;

import java.io.FileInputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.Properties;

/**
 * Centralizes the recorder runtime parameters.
 *
 * Every value can be overridden via a -D system property or environment
 * variable. Designed to be driven from IntelliJ Run Configuration.
 */
public final class RecorderConfig {

    public final String targetUrl;
    public final int    serverPort;
    public final Path   outputDir;
    public final String featureName;
    public final String browser;          // chromium | firefox | webkit
    public final boolean headless;
    public final boolean autoOpen;        // whether to navigate to the URL on start
    public final int    viewportWidth;
    public final int    viewportHeight;

    private RecorderConfig(String targetUrl, int port, Path outputDir,
                           String featureName, String browser, boolean headless,
                           boolean autoOpen, int vw, int vh) {
        this.targetUrl     = targetUrl;
        this.serverPort    = port;
        this.outputDir     = outputDir;
        this.featureName   = featureName;
        this.browser       = browser;
        this.headless      = headless;
        this.autoOpen      = autoOpen;
        this.viewportWidth = vw;
        this.viewportHeight= vh;
    }

    private static final Properties FILE_PROPS = loadFile();

    private static Properties loadFile() {
        Properties p = new Properties();
        Path[] candidates = {
                Paths.get("recorder.properties"),
                Paths.get(System.getProperty("user.dir"), "recorder.properties"),
        };
        for (Path c : candidates) {
            if (Files.exists(c)) {
                try (FileInputStream in = new FileInputStream(c.toFile())) {
                    p.load(in);
                    System.out.println("[Recorder] Loaded config file: " + c.toAbsolutePath());
                    return p;
                } catch (Exception e) {
                    System.err.println("[Recorder] Failed to read " + c + ": " + e.getMessage());
                }
            }
        }
        return p;
    }

    public static RecorderConfig fromSystem() {
        String url      = prop("recorder.url",         "https://cortex-test.bgtsai.com/");
        int    port     = Integer.parseInt(prop("recorder.port", "7700"));
        String outDir   = prop("recorder.output.dir",  "src/test/resources/recordings");
        String name     = prop("recorder.feature.name", "");
        String browser  = prop("recorder.browser",     "chromium");
        boolean headless= Boolean.parseBoolean(prop("recorder.headless", "false"));
        boolean autoOpen= Boolean.parseBoolean(prop("recorder.auto.open", "true"));
        int vw          = Integer.parseInt(prop("recorder.viewport.width",  "1440"));
        int vh          = Integer.parseInt(prop("recorder.viewport.height", "900"));

        if (name == null || name.isBlank()) {
            String ts = LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyyMMdd_HHmmss"));
            name = "recorded_" + ts;
        }

        return new RecorderConfig(
                url, port, Paths.get(outDir).toAbsolutePath(),
                name, browser, headless, autoOpen, vw, vh
        );
    }

    /**
     * Resolution order:
     *   1) System property (-Drecorder.url=...)
     *   2) Environment variable (RECORDER_URL)
     *   3) recorder.properties file
     *   4) default
     */
    private static String prop(String key, String defaultValue) {
        String v = System.getProperty(key);
        if (v != null && !v.isBlank()) return v;
        String envKey = key.toUpperCase().replace('.', '_');
        v = System.getenv(envKey);
        if (v != null && !v.isBlank()) return v;
        v = FILE_PROPS.getProperty(key);
        if (v != null && !v.isBlank()) return v;
        return defaultValue;
    }

    @Override
    public String toString() {
        return """
                RecorderConfig {
                  targetUrl     = %s
                  serverPort    = %d
                  outputDir     = %s
                  featureName   = %s
                  browser       = %s
                  headless      = %s
                  autoOpen      = %s
                  viewport      = %dx%d
                }""".formatted(
                targetUrl, serverPort, outputDir, featureName,
                browser, headless, autoOpen, viewportWidth, viewportHeight);
    }
}
