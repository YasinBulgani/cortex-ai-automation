package recorder;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;

/**
 * Alternative recorder entry point that delegates ALL UI/capture work to
 * Playwright's built-in codegen tool. The Inspector window runs as its own
 * Electron-based process, so React / SPA hydration on the recorded page
 * cannot remove it — fixing the entire class of "toolbar disappears"
 * bugs of the legacy in-page recorder.
 *
 * <p>Flow:
 * <ol>
 *   <li>Spawn {@code playwright codegen --target=playwright-test -o /tmp/cortex-codegen-*.ts URL}</li>
 *   <li>User records via the Inspector window. Stop = close the Inspector.</li>
 *   <li>This process resumes, reads the generated .ts file.</li>
 *   <li>{@link CodegenConverter} → {@link ActionTranslator} → {@link FeatureWriter}
 *       produces the .feature + locator JSON, exactly as the legacy recorder did.</li>
 * </ol>
 *
 * <p>Run via Maven: {@code ./mvnw -Precorder-codegen compile exec:java}
 */
public class CodegenRecorder {

    public static void main(String[] args) throws Exception {
        RecorderConfig cfg = RecorderConfig.fromSystem();

        System.out.println("=".repeat(60));
        System.out.println(" Cortex Recorder (Playwright Codegen)");
        System.out.println("=".repeat(60));
        System.out.println(cfg);
        System.out.println("-".repeat(60));

        String pwBin = resolvePlaywrightBinary();
        if (pwBin == null) {
            System.err.println("[Recorder] 'playwright' binary bulunamadi.");
            System.err.println("[Recorder] Kurulum: npm install -g playwright");
            System.exit(2);
            return;
        }

        Path outFile = Files.createTempFile("cortex-codegen-", ".spec.ts");

        List<String> cmd = new ArrayList<>();
        cmd.add(pwBin);
        cmd.add("codegen");
        cmd.add("--target=playwright-test");
        cmd.add("-o");
        cmd.add(outFile.toAbsolutePath().toString());
        if (cfg.browser != null && !cfg.browser.isBlank()) {
            cmd.add("--browser=" + cfg.browser);
        }
        if (cfg.targetUrl != null && !cfg.targetUrl.isBlank()) {
            cmd.add(cfg.targetUrl);
        }

        System.out.println("[Recorder] Spawning: " + String.join(" ", cmd));
        System.out.println("[Recorder] Output (geçici): " + outFile);
        System.out.println("");
        System.out.println("=".repeat(60));
        System.out.println(" Inspector penceresi acildi.");
        System.out.println("   - Chromium'da senaryoyu gez.");
        System.out.println("   - Inspector'da Record/Stop/Pick element/Assert/Wait kullan.");
        System.out.println("   - Bittiginde Inspector'i KAPAT (X) — kayit otomatik kaydedilir.");
        System.out.println("=".repeat(60));

        ProcessBuilder pb = new ProcessBuilder(cmd);
        pb.inheritIO();
        Process p = pb.start();

        // Ensure we shut codegen down cleanly if THIS JVM is killed (IntelliJ
        // Stop, Ctrl-C, etc.). Otherwise the Inspector window orphans.
        Process finalP = p;
        Runtime.getRuntime().addShutdownHook(new Thread(() -> {
            if (finalP.isAlive()) {
                System.out.println("[Recorder] Shutdown — codegen alt sürecini kapatıyorum.");
                finalP.destroy();
            }
        }, "codegen-cleanup"));

        int exit = p.waitFor();
        if (exit != 0) {
            System.err.println("[Recorder] codegen exit code: " + exit + " (kayit yine de okunmayı denenecek)");
        }

        if (!Files.exists(outFile) || Files.size(outFile) == 0) {
            System.err.println("[Recorder] Codegen ciktisi yok ya da bos: " + outFile);
            System.err.println("[Recorder] Inspector'da hicbir aksiyon kayit olmamis. Cikiliyor.");
            System.exit(3);
            return;
        }

        String content = Files.readString(outFile, StandardCharsets.UTF_8);
        System.out.println("\n[Recorder] " + content.length() + " bayt codegen ciktisi okunuyor...");

        List<RecordedAction> actions = new CodegenConverter().parse(content);
        System.out.println("[Recorder] " + actions.size() + " aksiyon parse edildi.");

        if (actions.isEmpty()) {
            System.err.println("[Recorder] Persist edilecek aksiyon yok.");
            System.err.println("[Recorder] Ham codegen ciktisi: " + outFile + " (incelemek icin saklandı)");
            return;
        }

        try {
            var tr = new ActionTranslator().translate(actions);
            var result = new FeatureWriter(cfg).write(tr);
            System.out.println("=".repeat(60));
            System.out.println(" RECORDING COMPLETE ");
            System.out.println("=".repeat(60));
            System.out.println(" Feature:  " + result.featureFile());
            System.out.println(" Locator:  " + result.locatorFile());
            System.out.println(" Actions:  " + result.actionCount());
            System.out.println(" Locators: " + result.locatorCount());
            System.out.println(" Ham:      " + outFile);
            System.out.println("=".repeat(60));
            System.out.println(" Cukucumber + Playwright runner ile calistir:");
            System.out.println("   mvn test -Dcucumber.features=" + result.featureFile());
            System.out.println("=".repeat(60));
        } catch (Exception e) {
            System.err.println("[Recorder] Artifaktlar yazilamadi: " + e.getMessage());
            e.printStackTrace();
        }
    }

    /** Find the playwright CLI binary. Tries PATH and common Homebrew locations. */
    private static String resolvePlaywrightBinary() {
        String[] candidates = {
            "/opt/homebrew/bin/playwright",
            "/usr/local/bin/playwright",
            "/usr/bin/playwright",
        };
        for (String c : candidates) {
            if (Files.isExecutable(Path.of(c))) return c;
        }
        // Fallback: rely on PATH.
        try {
            Process p = new ProcessBuilder("which", "playwright")
                    .redirectErrorStream(true).start();
            byte[] bytes = p.getInputStream().readAllBytes();
            p.waitFor();
            String out = new String(bytes, StandardCharsets.UTF_8).trim();
            if (!out.isEmpty() && Files.isExecutable(Path.of(out))) return out;
        } catch (IOException | InterruptedException ignored) {}
        return null;
    }
}
