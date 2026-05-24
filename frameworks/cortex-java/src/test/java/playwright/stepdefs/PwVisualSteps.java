package playwright.stepdefs;

import com.microsoft.playwright.Page;
import com.microsoft.playwright.options.LoadState;
import io.cucumber.java.en.Then;
import playwright.PlaywrightFactory;

import javax.imageio.ImageIO;
import java.awt.image.BufferedImage;
import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;

/**
 * Visual regression step definitions (E26 fix).
 *
 * <h3>Usage</h3>
 * <pre>{@code
 *   Then visual snapshot matches "login-form"
 *   Then visual snapshot matches "dashboard-home" with threshold 5
 * }</pre>
 *
 * <h3>Behavior</h3>
 * <ul>
 *   <li>Baseline lookup: {@code src/test/resources/visual-baselines/<safe-feature>/<name>.png}</li>
 *   <li>First run with no baseline: screenshot is SAVED as the baseline and the
 *       step passes (so green CI on initial commit). A warning is logged.</li>
 *   <li>Subsequent runs: take screenshot, count differing pixels, fail if the
 *       percentage exceeds threshold (default 1%, override via step arg).</li>
 *   <li>On diff: writes BOTH the actual screenshot and a side-by-side diff
 *       PNG to {@code target/visual-diffs/<run>/<name>_{actual,diff}.png}.</li>
 * </ul>
 *
 * <h3>Pixel-diff algorithm</h3>
 * RGB Manhattan distance per pixel with tolerance 10 (anti-aliasing noise).
 * Sum of differing pixels / total pixels → diff percentage. Cheap but
 * effective for layout regressions; not subpixel-perfect (use threshold).
 */
public class PwVisualSteps {

    private static final double DEFAULT_THRESHOLD_PCT = 1.0;
    private static final int    PIXEL_TOLERANCE = 10;  // per-channel
    private static final Path   BASELINE_DIR = Paths.get("src/test/resources/visual-baselines");
    private static final Path   DIFF_DIR     = Paths.get("target/visual-diffs");

    @Then("visual snapshot matches {string}")
    public void snapshotMatches(String name) {
        compareOrSaveBaseline(name, DEFAULT_THRESHOLD_PCT);
    }

    @Then("visual snapshot matches {string} with threshold {int}")
    public void snapshotMatchesWithThreshold(String name, Integer thresholdPct) {
        compareOrSaveBaseline(name, thresholdPct.doubleValue());
    }

    private void compareOrSaveBaseline(String name, double thresholdPct) {
        Page page = PlaywrightFactory.page();
        if (page == null) {
            throw new IllegalStateException("Playwright Page null — recorder context aktif değil");
        }

        // Wait for network to settle so layout doesn't flicker
        try { page.waitForLoadState(LoadState.NETWORKIDLE,
                new Page.WaitForLoadStateOptions().setTimeout(5000)); }
        catch (Exception ignored) {}

        byte[] currentBytes = page.screenshot(new Page.ScreenshotOptions().setFullPage(true));

        String safeName = name.replaceAll("[^A-Za-z0-9_-]", "_");
        Path baseline = BASELINE_DIR.resolve(safeName + ".png");

        if (!Files.exists(baseline)) {
            try {
                Files.createDirectories(baseline.getParent());
                Files.write(baseline, currentBytes);
                System.out.println("[visual] Baseline yok — yeni baseline kaydedildi: " + baseline);
                System.out.println("[visual] Sonraki çalıştırmalarda bu baseline ile karşılaştırılacak.");
                return;
            } catch (IOException e) {
                throw new RuntimeException("Baseline yazılamadı: " + baseline, e);
            }
        }

        // Compare
        try {
            byte[] expectedBytes = Files.readAllBytes(baseline);
            BufferedImage expected = ImageIO.read(new ByteArrayInputStream(expectedBytes));
            BufferedImage actual   = ImageIO.read(new ByteArrayInputStream(currentBytes));

            if (expected == null || actual == null) {
                throw new AssertionError("Görüntü decode edilemedi (PNG bozuk?)");
            }

            DiffResult diff = computeDiff(expected, actual);
            double diffPct = (diff.diffPixels / (double) diff.totalPixels) * 100.0;

            if (diffPct > thresholdPct) {
                Path diffOut = saveDiffArtifacts(safeName, currentBytes, diff.diffImage);
                throw new AssertionError(String.format(
                        "Visual regression: '%s' baseline'dan %%%.2f farklı (eşik: %%%.2f)\n" +
                        "  Baseline : %s\n" +
                        "  Diff PNG : %s",
                        name, diffPct, thresholdPct, baseline, diffOut));
            }
            System.out.printf("[visual] %s ✓ baseline match (%.3f%% diff, threshold %.1f%%)%n",
                    name, diffPct, thresholdPct);
        } catch (IOException e) {
            throw new RuntimeException("Visual compare hata: " + e.getMessage(), e);
        }
    }

    private record DiffResult(int diffPixels, int totalPixels, BufferedImage diffImage) {}

    private static DiffResult computeDiff(BufferedImage a, BufferedImage b) {
        int w = Math.min(a.getWidth(), b.getWidth());
        int h = Math.min(a.getHeight(), b.getHeight());
        BufferedImage diff = new BufferedImage(w, h, BufferedImage.TYPE_INT_RGB);
        int diffCount = 0;

        for (int y = 0; y < h; y++) {
            for (int x = 0; x < w; x++) {
                int ca = a.getRGB(x, y);
                int cb = b.getRGB(x, y);
                int dr = Math.abs(((ca >> 16) & 0xFF) - ((cb >> 16) & 0xFF));
                int dg = Math.abs(((ca >>  8) & 0xFF) - ((cb >>  8) & 0xFF));
                int db = Math.abs( (ca        & 0xFF) -  (cb        & 0xFF));
                if (dr + dg + db > PIXEL_TOLERANCE * 3) {
                    // Highlight diff in red
                    diff.setRGB(x, y, 0xFF0000);
                    diffCount++;
                } else {
                    // Grey-out matching pixels for clarity
                    int lum = (((ca >> 16) & 0xFF) + ((ca >> 8) & 0xFF) + (ca & 0xFF)) / 3;
                    diff.setRGB(x, y, (lum << 16) | (lum << 8) | lum);
                }
            }
        }
        return new DiffResult(diffCount, w * h, diff);
    }

    private static Path saveDiffArtifacts(String name, byte[] actualBytes, BufferedImage diffImage) throws IOException {
        String ts = LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyy-MM-dd_HHmmss"));
        Path outDir = DIFF_DIR.resolve(ts);
        Files.createDirectories(outDir);
        Path actualOut = outDir.resolve(name + "_actual.png");
        Path diffOut   = outDir.resolve(name + "_diff.png");
        Files.write(actualOut, actualBytes);
        ImageIO.write(diffImage, "png", diffOut.toFile());
        return diffOut;
    }
}
