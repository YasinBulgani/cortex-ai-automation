package recorder;

import com.microsoft.playwright.Browser;
import com.microsoft.playwright.BrowserContext;
import com.microsoft.playwright.BrowserType;
import com.microsoft.playwright.Page;
import com.microsoft.playwright.Playwright;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.concurrent.CountDownLatch;

/**
 * Entry point invoked from IntelliJ Run > "Recorder".
 *
 * Flow:
 *   1. Load RecorderConfig from -D system properties / env / file.
 *   2. Start the local HTTP server (default port 7700, falls back if busy).
 *   3. Launch Playwright Chromium and open the target URL.
 *   4. Inject recorder.js + recorder.css on every page via Page.addInitScript.
 *   5. User navigates the browser; recorder.js POSTs each event to /action.
 *   6. Stop comes from either the in-browser toolbar (POST /stop) or the
 *      IntelliJ Stop button (the JVM shutdown hook runs the same save flow).
 *
 * Stop paths:
 *   a) Browser toolbar     -> POST /stop -> stopSignal.complete()
 *   b) IntelliJ Stop       -> SIGTERM   -> shutdown hook calls persist()
 */
public class RecorderMain {

    public static void main(String[] args) {
        RecorderConfig cfg = RecorderConfig.fromSystem();
        System.out.println("=".repeat(60));
        System.out.println(" Cortex Recorder ");
        System.out.println("=".repeat(60));
        System.out.println(cfg);
        System.out.println("-".repeat(60));

        // 0. Pre-launch cleanup: kill any orphan Playwright Chromium processes
        //    from previous interrupted runs. Without this, each launch leaks
        //    a Chrome window on the user's machine.
        int killed = killOrphanedPlaywrightProcesses();
        if (killed > 0) {
            System.out.println("[Recorder] Cleaned up " + killed + " orphan Chromium process(es) from previous runs.");
        }

        // 1. HTTP server (fall back to next free port if requested one is busy)
        RecorderServer server;
        try {
            server = RecorderServer.bindAvailable(cfg.serverPort);
            if (server.port() != cfg.serverPort) {
                System.out.println("[Recorder] Port " + cfg.serverPort + " was busy, using " + server.port() + " instead.");
            }
            server.start();
        } catch (IOException e) {
            System.err.println("[Recorder] Failed to start HTTP server: " + e.getMessage());
            System.exit(1);
            return;
        }
        final int activePort = server.port();

        // 2. Shutdown hook — captures every exit path, including IntelliJ Stop
        CountDownLatch saved = new CountDownLatch(1);
        Runtime.getRuntime().addShutdownHook(new Thread(() -> {
            try {
                if (saved.getCount() > 0) {
                    System.out.println("\n[Recorder] Shutdown hook -> persist");
                    persist(cfg, server.getActions());
                    saved.countDown();
                }
            } catch (Exception e) {
                System.err.println("[Recorder] Error during shutdown: " + e.getMessage());
            }
        }, "recorder-shutdown"));

        // 3. Prepare recorder.js + recorder.css init script (with the actual port)
        String initScript;
        try {
            initScript = buildInitScript(cfg, activePort);
        } catch (IOException e) {
            System.err.println("[Recorder] recorder.js not found: " + e.getMessage());
            server.stop();
            System.exit(2);
            return;
        }

        // 4. Playwright + browser
        try (Playwright pw = Playwright.create()) {
            BrowserType bt = switch (cfg.browser) {
                case "firefox" -> pw.firefox();
                case "webkit"  -> pw.webkit();
                default        -> pw.chromium();
            };
            BrowserType.LaunchOptions launchOpts = new BrowserType.LaunchOptions()
                    .setHeadless(cfg.headless)
                    .setArgs(List.of(
                            "--start-maximized",
                            "--disable-blink-features=AutomationControlled",
                            // PNA: allow fetch() from https://cortex-test... to http://127.0.0.1:7700
                            "--disable-features=BlockInsecurePrivateNetworkRequests,PrivateNetworkAccessSendPreflights",
                            "--disable-site-isolation-trials"
                    ));

            try (Browser browser = bt.launch(launchOpts)) {
                // Extra shutdown hook for the browser specifically — try-with-resources
                // handles normal exits, but SIGKILL / IntelliJ Stop bypass it.
                final Browser finalBrowser = browser;
                Runtime.getRuntime().addShutdownHook(new Thread(() -> {
                    try {
                        if (finalBrowser != null) {
                            System.out.println("[Recorder] Shutdown hook -> closing browser");
                            finalBrowser.close();
                        }
                    } catch (Exception ignored) {}
                }, "cortex-browser-cleanup"));

                BrowserContext ctx = browser.newContext(new Browser.NewContextOptions()
                        .setViewportSize(cfg.viewportWidth, cfg.viewportHeight)
                        .setLocale("tr-TR"));

                // CDP bindings that bypass PNA/CORS — recorder.js calls these
                // instead of fetch() so private-network blocks never trigger.
                //
                // CRITICAL: bindings MUST be registered BEFORE addInitScript.
                // Otherwise on cross-origin navigations the binding may not be
                // available when recorder.js runs (we saw exactly this on the
                // about:blank → cortex-test transition).
                com.google.gson.Gson gson = new com.google.gson.Gson();

                ctx.exposeBinding("__cortexSend", (source, bindingArgs) -> {
                    if (bindingArgs == null || bindingArgs.length == 0) return java.util.Map.of("ok", false);
                    String json = gson.toJson(bindingArgs[0]);
                    RecordedAction a = gson.fromJson(json, RecordedAction.class);
                    int count = server.addAction(a);
                    return java.util.Map.of("ok", count >= 0, "count", Math.max(count, 0));
                });

                ctx.exposeBinding("__cortexUndo", (source, bindingArgs) -> {
                    int count = server.removeLastAction();
                    return java.util.Map.of("ok", true, "count", count);
                });

                ctx.exposeBinding("__cortexStop", (source, bindingArgs) -> {
                    System.out.println("[Recorder] /stop via CDP binding");
                    server.requestStop();
                    return java.util.Map.of("ok", true);
                });

                ctx.exposeBinding("__cortexStatus", (source, bindingArgs) ->
                        java.util.Map.of("ok", true, "count", server.getActions().size()));

                // Page scan: recorder.js calls this with a JSON-serializable snapshot
                ctx.exposeBinding("__cortexElements", (source, bindingArgs) -> {
                    if (bindingArgs == null || bindingArgs.length == 0) return java.util.Map.of("ok", false);
                    String json = gson.toJson(bindingArgs[0]);
                    server.setPageScan(json);
                    int count = 0;
                    try {
                        com.google.gson.JsonObject root = com.google.gson.JsonParser.parseString(json).getAsJsonObject();
                        if (root.has("count")) count = root.get("count").getAsInt();
                    } catch (Exception ignored) {}
                    System.out.println("[Recorder] page scan: " + count + " elements");
                    return java.util.Map.of("ok", true, "count", count);
                });

                // NOW (after bindings) add the init script so recorder.js sees them.
                ctx.addInitScript(initScript);

                Page page = ctx.newPage();
                // Bind the Page to the server so /perform endpoint can drive it
                server.setPlaywrightPage(page);

                // ── CONSOLE-BASED BACKUP CHANNEL ──────────────────────────
                // If __cortexSend binding fails (PNA/CORS/CSP/cross-origin
                // weirdness), recorder.js will console.log() the action with
                // a magic prefix. We intercept it here and store the action.
                // This is bullet-proof because console messages always flow
                // through CDP regardless of page security state.
                final com.google.gson.Gson consoleGson = new com.google.gson.Gson();
                page.onConsoleMessage(msg -> {
                    String text = msg.text();
                    if (text == null) return;
                    if (text.startsWith("__CORTEX_ACTION__")) {
                        String payload = text.substring("__CORTEX_ACTION__".length());
                        try {
                            RecordedAction a = consoleGson.fromJson(payload, RecordedAction.class);
                            int count = server.addAction(a);
                            System.out.println("[Recorder] console-channel action #" + count + " - " + a.type);
                        } catch (Exception e) {
                            System.err.println("[Recorder] console-channel parse fail: " + e.getMessage());
                        }
                    } else if (text.startsWith("__CORTEX_STOP__")) {
                        System.out.println("[Recorder] /stop via console channel");
                        server.requestStop();
                    } else if (text.startsWith("__CORTEX_UNDO__")) {
                        server.removeLastAction();
                    } else if (text.startsWith("__CORTEX_ELEMENTS__")) {
                        server.setPageScan(text.substring("__CORTEX_ELEMENTS__".length()));
                    }
                });

                // Belt-and-suspenders: re-inject recorder.js on every navigation.
                // page.evaluate expects an EXPRESSION (arrow function), but initScript
                // is a statement (IIFE). Pass it as a string argument and invoke via
                // indirect eval inside the arrow so it runs in global scope.
                final String safeReinject = initScript;
                page.onFrameNavigated((frame) -> {
                    if (frame != page.mainFrame()) return;
                    try {
                        page.evaluate(
                            "(scriptBody) => { try { (0, eval)(scriptBody); } " +
                            "catch (e) { console.error('[cortex-rec] eval failed:', e); throw e; } }",
                            safeReinject
                        );
                        System.out.println("[Recorder] re-inject after nav: " + frame.url() + " ✓");
                    } catch (Exception e) {
                        System.err.println("[Recorder] re-inject failed: " + e.getMessage());
                    }
                });

                page.navigate(cfg.targetUrl);
                try { page.bringToFront(); } catch (Exception ignored) {}

                // ── macOS / Windows APP-level activation ──────────────────
                // page.bringToFront() only brings the TAB front WITHIN the
                // Chromium app — if Chromium app itself is behind the user's
                // personal Chrome / IntelliJ, the user can't see it.
                //
                // On macOS we use AppleScript via osascript to actually
                // activate the Chromium application process.
                String osName = System.getProperty("os.name", "").toLowerCase();
                Runnable activateApp = () -> {
                    try {
                        if (osName.contains("mac")) {
                            // Try multiple app names — Playwright bundles its own Chromium.
                            for (String app : new String[]{"Chromium", "Google Chrome for Testing", "Google Chrome"}) {
                                try {
                                    Process p = new ProcessBuilder("osascript", "-e",
                                            "tell application \"" + app + "\" to activate").start();
                                    p.waitFor(1, java.util.concurrent.TimeUnit.SECONDS);
                                    if (p.exitValue() == 0) {
                                        System.out.println("[Recorder] macOS: activated " + app);
                                        return;
                                    }
                                } catch (Exception ignored) {}
                            }
                            // Fallback: by process name via System Events
                            try {
                                new ProcessBuilder("osascript", "-e",
                                        "tell application \"System Events\" to set frontmost of " +
                                        "(first process whose name contains \"Chromium\") to true").start()
                                    .waitFor(1, java.util.concurrent.TimeUnit.SECONDS);
                            } catch (Exception ignored) {}
                        } else if (osName.contains("win")) {
                            // Windows: use PowerShell + Win32 API via -Command
                            try {
                                String ps = "Add-Type -AssemblyName Microsoft.VisualBasic; " +
                                        "[Microsoft.VisualBasic.Interaction]::AppActivate('Chromium')";
                                new ProcessBuilder("powershell", "-Command", ps).start()
                                    .waitFor(1, java.util.concurrent.TimeUnit.SECONDS);
                            } catch (Exception ignored) {}
                        }
                    } catch (Exception ignored) {}
                };
                activateApp.run();  // initial

                // Aggressive focus-stealing for the first 30 seconds so the user
                // can't accidentally interact with their personal Chrome instead.
                // This addresses the #1 user-error: typing in the wrong browser.
                final Page focusPage = page;
                Thread focusKeeper = new Thread(() -> {
                    for (int i = 0; i < 15; i++) {  // 15 * 2s = 30s
                        try {
                            Thread.sleep(2000);
                            focusPage.bringToFront();
                            // Re-activate app every 6 seconds
                            if (i % 3 == 0) activateApp.run();
                        } catch (Exception ignored) { return; }
                    }
                }, "cortex-rec-focus");
                focusKeeper.setDaemon(true);
                focusKeeper.start();

                System.out.println("[Recorder] Browser launched. Recording started.");
                System.out.println("[Recorder] Target URL: " + cfg.targetUrl);
                System.out.println("[Recorder] ⚠  ÖNEMLİ: Sadece [REC] başlıklı yeni Chromium penceresinde işlem yap.");
                System.out.println("[Recorder]    Normal Chrome/Edge/Safari'de yaptığın hiçbir şey kayıt OLMAZ.");
                System.out.println("[Recorder] To finish: click 'Stop & Save' in-browser, or press IntelliJ Stop.");

                // Diagnostic: inline marker + iframe map + force-inject test
                try {
                    Thread.sleep(2500);
                    // 1) List all frames
                    System.out.println("[Recorder] Frames in page:");
                    for (var fr : page.frames()) {
                        System.out.println("  - " + (fr == page.mainFrame() ? "[MAIN]" : "[iframe]") + " " + fr.url());
                    }
                    // 2) Inline marker test — set a NEW marker from JAVA, read it back
                    Object diag = page.evaluate(
                        "() => {\n" +
                        "  document.documentElement.setAttribute('data-cortex-inline', 'set-from-java-' + Date.now());\n" +
                        "  return {\n" +
                        "    inlineMarker:  document.documentElement.getAttribute('data-cortex-inline'),\n" +
                        "    recMarker:     document.documentElement.getAttribute('data-cortex-recorder'),\n" +
                        "    hasSend:       typeof window.__cortexSend     === 'function',\n" +
                        "    hasScan:       typeof window.__cortexScan     === 'function',\n" +
                        "    hasDiag:       typeof window.__cortexDiag     === 'function',\n" +
                        "    hasElements:   typeof window.__cortexElements === 'function',\n" +
                        "    hasProbe:      !!document.getElementById('cortex-rec-probe'),\n" +
                        "    hasDebug:      !!document.getElementById('cortex-rec-debug'),\n" +
                        "    hasToolbar:    !!document.getElementById('cortex-rec-toolbar'),\n" +
                        "    topFrame:      window === top,\n" +
                        "    title:         document.title,\n" +
                        "    url:           location.href,\n" +
                        "    bodyChildCount: document.body ? document.body.children.length : 0,\n" +
                        "    iframeCount:   document.querySelectorAll('iframe').length\n" +
                        "  };\n" +
                        "}"
                    );
                    System.out.println("[Recorder] DIAGNOSTIC: " + diag);

                    // 3) If recorder.js didn't run in MAIN frame, FORCE inject via simpler eval
                    @SuppressWarnings("unchecked")
                    var diagMap = (java.util.Map<String, Object>) diag;
                    Boolean recMarkerNull = diagMap.get("recMarker") == null;
                    if (recMarkerNull) {
                        System.err.println("[Recorder] !!! recorder.js did NOT run in main frame !!!");
                        System.err.println("[Recorder] Attempting FORCE injection via new Function...");
                        try {
                            page.evaluate(
                                "(src) => { new Function(src)(); return 'forced'; }",
                                initScript
                            );
                            Thread.sleep(800);
                            Object diag2 = page.evaluate(
                                "() => ({ recMarker: document.documentElement.getAttribute('data-cortex-recorder'), hasScan: typeof window.__cortexScan === 'function', hasProbe: !!document.getElementById('cortex-rec-probe') })"
                            );
                            System.out.println("[Recorder] After FORCE inject: " + diag2);
                        } catch (Exception e2) {
                            System.err.println("[Recorder] FORCE inject failed: " + e2.getMessage());
                        }
                    }
                } catch (Exception e) {
                    System.err.println("[Recorder] Page diagnostic failed: " + e.getMessage());
                    e.printStackTrace();
                }

                // 5. Wait for stop signal
                try {
                    server.stopSignal().join();
                } catch (Exception ignored) {}

                // 6. Persist storage state (cookies + localStorage) for replay reuse
                try {
                    java.nio.file.Path stateDir = java.nio.file.Paths.get("src/test/resources/projects/cortex/storage-states");
                    java.nio.file.Files.createDirectories(stateDir);
                    String stateName = "recorder-" + System.currentTimeMillis() + ".json";
                    java.nio.file.Path statePath = stateDir.resolve(stateName);
                    ctx.storageState(new BrowserContext.StorageStateOptions().setPath(statePath));
                    System.out.println("[Recorder] storage state saved: " + statePath);
                    // Also save as 'latest.json' for convenient default use
                    java.nio.file.Files.copy(statePath, stateDir.resolve("latest.json"),
                            java.nio.file.StandardCopyOption.REPLACE_EXISTING);
                } catch (Exception e) {
                    System.err.println("[Recorder] storage state save failed: " + e.getMessage());
                }

                // 7. Persist (unless the shutdown hook already did it)
                if (saved.getCount() > 0) {
                    persist(cfg, server.getActions());
                    saved.countDown();
                }
            }
        } finally {
            server.stop();
        }
        System.out.println("[Recorder] Done.");
    }

    /**
     * Combines recorder.js + recorder.css into a single init script.
     * NOTE: NO re-entry guard at wrapper level. Inner recorder.js has its own
     * __cortexRecorderActive check + heartbeat that re-applies the UI every 400ms.
     * This makes re-inject (via framenavigated handler) effective even after
     * React hydration strips our DOM mutations.
     */
    /**
     * Kill any orphan Playwright Chromium processes left over from previous
     * interrupted recorder runs. Playwright's bundled Chromium lives under
     * ~/Library/Caches/ms-playwright/ (Mac) or %USERPROFILE%\.cache\ms-playwright\
     * (Windows) or ~/.cache/ms-playwright/ (Linux). We match command-line
     * substrings to be safe (won't kill user's regular Chrome).
     *
     * @return number of processes killed (best-effort, not authoritative)
     */
    public static int killOrphanedPlaywrightProcesses() {
        String os = System.getProperty("os.name", "").toLowerCase();
        int killed = 0;
        try {
            if (os.contains("mac") || os.contains("nix") || os.contains("nux")) {
                // Match: any process whose command line contains "ms-playwright"
                // pkill returns 0=killed, 1=none-matched, 2/3=error. We treat 0 as success.
                String[] patterns = {
                    "ms-playwright.*[Cc]hromium",
                    "ms-playwright.*chrome-headless-shell",
                    "ms-playwright.*[Ff]irefox",
                    "ms-playwright.*[Ww]ebkit",
                };
                for (String p : patterns) {
                    try {
                        Process proc = new ProcessBuilder("pkill", "-f", p)
                                .redirectErrorStream(true).start();
                        if (proc.waitFor(3, java.util.concurrent.TimeUnit.SECONDS) && proc.exitValue() == 0) {
                            killed++;
                        }
                    } catch (Exception ignored) {}
                }
            } else if (os.contains("win")) {
                // PowerShell: find by CommandLine substring, then Stop-Process
                String ps = "$procs = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*ms-playwright*' }; " +
                            "$procs | ForEach-Object { try { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue } catch {} }; " +
                            "($procs | Measure-Object).Count";
                try {
                    Process proc = new ProcessBuilder("powershell", "-NoProfile", "-Command", ps)
                            .redirectErrorStream(true).start();
                    if (proc.waitFor(10, java.util.concurrent.TimeUnit.SECONDS)) {
                        byte[] out = proc.getInputStream().readAllBytes();
                        String s = new String(out).trim();
                        try { killed = Integer.parseInt(s.split("\\s+")[s.split("\\s+").length - 1]); }
                        catch (NumberFormatException ignored) {}
                    }
                } catch (Exception ignored) {}
            }
        } catch (Exception e) {
            System.err.println("[Recorder] killOrphanedPlaywrightProcesses warning: " + e.getMessage());
        }
        return killed;
    }

    private static String buildInitScript(RecorderConfig cfg, int activePort) throws IOException {
        String js  = readResource("/recorder/recorder.js");
        String css = readResource("/recorder/recorder.css");
        return """
                (function(){
                  window.__CORTEX_RECORDER_PORT__ = %d;
                  window.__CORTEX_RECORDER_CSS__ = %s;
                  %s
                })();
                """.formatted(activePort, jsString(css), js);
    }

    private static String readResource(String path) throws IOException {
        var in = RecorderMain.class.getResourceAsStream(path);
        if (in == null) {
            // If the classpath lookup fails (target/classes missing), fall back to source path
            Path fsFallback = Path.of("src/main/resources" + path);
            if (Files.exists(fsFallback)) {
                return Files.readString(fsFallback, StandardCharsets.UTF_8);
            }
            throw new IOException("Resource not found: " + path);
        }
        return new String(in.readAllBytes(), StandardCharsets.UTF_8);
    }

    /** Escape into a JS string literal. */
    private static String jsString(String s) {
        return "\"" + s.replace("\\", "\\\\")
                       .replace("\"", "\\\"")
                       .replace("\n", "\\n")
                       .replace("\r", "")
                       .replace("\t", "\\t") + "\"";
    }

    /** Run ActionTranslator + FeatureWriter to persist artifacts. */
    private static void persist(RecorderConfig cfg, List<RecordedAction> actions) {
        if (actions.isEmpty()) {
            System.out.println("[Recorder] No actions captured — nothing was written.");
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
            System.out.println("=".repeat(60));
            System.out.println(" Run with:");
            System.out.println("   mvn test -Dcucumber.features=" + result.featureFile());
            System.out.println(" or via .run/PlaywrightTests.run.xml.");
        } catch (Exception e) {
            System.err.println("[Recorder] Failed to write artifacts: " + e.getMessage());
            e.printStackTrace();
        }
    }
}
