package recorder;

import com.google.gson.Gson;
import com.google.gson.JsonSyntaxException;
import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;

import java.io.IOException;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicBoolean;

/**
 * Embedded HTTP server (jdk.httpserver) used by the recorder.
 * recorder.js posts events here:
 *
 *   POST /action     -> { type, element, text, ... }
 *   POST /stop       -> user clicked the toolbar Stop button
 *   POST /undo       -> remove the last action
 *   GET  /status     -> { running, actions: N }
 *   GET  /actions    -> the full current list
 *
 * CORS is permissive (loopback only, intended for local IntelliJ runs).
 */
public class RecorderServer {

    private final HttpServer http;
    private final List<RecordedAction> actions = Collections.synchronizedList(new ArrayList<>());
    private final Gson gson = new Gson();
    private final CompletableFuture<Void> stopSignal = new CompletableFuture<>();
    private final int port;
    // E06: pause flag — when true, incoming /action events are silently discarded.
    private final AtomicBoolean paused = new AtomicBoolean(false);

    public RecorderServer(int port) throws IOException {
        this.port = port;
        this.http = HttpServer.create(new InetSocketAddress("127.0.0.1", port), 16);
        http.setExecutor(Executors.newFixedThreadPool(4));
        registerHandlers();
    }

    public void start() {
        http.start();
        System.out.println("[Recorder] HTTP server listening on http://127.0.0.1:" + port);
    }

    public void stop() {
        http.stop(0);
    }

    public CompletableFuture<Void> stopSignal() {
        return stopSignal;
    }

    public List<RecordedAction> getActions() {
        synchronized (actions) {
            return new ArrayList<>(actions);
        }
    }

    private volatile String latestPageScan = "null";   // raw JSON
    public void setPageScan(String json) {
        this.latestPageScan = json == null ? "null" : json;
    }
    public String getPageScan() { return latestPageScan; }

    // Reference to the Playwright Page so /perform can drive the browser
    private volatile com.microsoft.playwright.Page playwrightPage;
    public void setPlaywrightPage(com.microsoft.playwright.Page p) { this.playwrightPage = p; }
    public com.microsoft.playwright.Page getPlaywrightPage() { return playwrightPage; }

    /** Programmatic action insertion (used by Playwright exposeBinding callbacks). */
    public int addAction(RecordedAction a) {
        if (a == null || a.type == null) return -1;
        if (a.timestamp == null) a.timestamp = System.currentTimeMillis();
        synchronized (actions) {
            // Dedup: if last action has same type+timestamp (within 50ms) and
            // same element xpath, drop this duplicate. The recorder.js sends
            // each action via BOTH the CDP binding AND the console channel
            // for reliability; we collapse the duplicates here.
            if (!actions.isEmpty()) {
                RecordedAction last = actions.get(actions.size() - 1);
                if (last.type.equals(a.type)
                        && last.timestamp != null && a.timestamp != null
                        && Math.abs(a.timestamp - last.timestamp) < 50) {
                    boolean sameElement =
                            (last.element == null && a.element == null) ||
                            (last.element != null && a.element != null &&
                             java.util.Objects.equals(last.element.xpath, a.element.xpath));
                    if (sameElement) {
                        return actions.size();   // drop the duplicate
                    }
                }
            }
            actions.add(a);
            System.out.println("[Recorder] action #" + actions.size() + " - " + a.type
                    + (a.element != null && a.element.tag != null ? " <" + a.element.tag + ">" : ""));
            return actions.size();
        }
    }

    /** Programmatic last-action removal (used by toolbar undo via exposeBinding). */
    public int removeLastAction() {
        synchronized (actions) {
            if (actions.isEmpty()) return 0;
            actions.remove(actions.size() - 1);
            return actions.size();
        }
    }

    /** Signal stop from anywhere (toolbar binding, dashboard, etc.). */
    public void requestStop() {
        stopSignal.complete(null);
    }

    public int port() { return port; }

    /** If the requested port is busy, find the next free one (up to +10). */
    public static RecorderServer bindAvailable(int startPort) throws IOException {
        IOException last = null;
        for (int p = startPort; p < startPort + 10; p++) {
            try {
                return new RecorderServer(p);
            } catch (IOException e) {
                last = e;
            }
        }
        throw new IOException("All ports " + startPort + "-" + (startPort + 9) + " are busy", last);
    }

    /* --------------------------------------------------------------- */

    private void registerHandlers() {
        http.createContext("/action",  this::handleAction);
        http.createContext("/stop",    this::handleStop);
        http.createContext("/status",  this::handleStatus);
        http.createContext("/actions", this::handleListActions);
        http.createContext("/undo",    this::handleUndo);
        http.createContext("/inject",  this::handleInject);
        http.createContext("/last-element", this::handleLastElement);
        http.createContext("/elements",  this::handleElements);
        http.createContext("/perform",   this::handlePerform);
        http.createContext("/cleanup",   this::handleCleanup);
        // E06: pause / resume recording
        http.createContext("/pause",     this::handlePause);
        http.createContext("/resume",    this::handleResume);
    }

    /**
     * Kill orphan Playwright Chromium processes (best-effort).
     * Useful when user reports stale browser windows from previous runs.
     */
    private void handleCleanup(HttpExchange ex) throws IOException {
        if (preflight(ex)) return;
        try {
            int killed = RecorderMain.killOrphanedPlaywrightProcesses();
            System.out.println("[Recorder] /cleanup -> killed " + killed + " orphan process(es)");
            respond(ex, 200, "{\"ok\":true,\"killed\":" + killed + "}");
        } catch (Exception e) {
            String msg = e.getMessage() == null ? "unknown" : e.getMessage();
            respond(ex, 500, "{\"ok\":false,\"error\":\"" + msg.replace("\"", "'") + "\"}");
        }
    }

    private void handleElements(HttpExchange ex) throws IOException {
        if (preflight(ex)) return;
        respond(ex, 200, latestPageScan);
    }

    /**
     * Remote-control endpoint: dashboard tells JVM "click this element" or
     * "type into this field". JVM uses Playwright Page API to actually do it.
     *
     * body: {
     *   action: "click" | "fill" | "hover" | "scroll" | "press" | "navigate",
     *   selector?: string,    // CSS or "xpath=..."
     *   text?: string,
     *   url?: string,
     *   timeoutMs?: number
     * }
     */
    private void handlePerform(HttpExchange ex) throws IOException {
        if (preflight(ex)) return;
        if (!"POST".equalsIgnoreCase(ex.getRequestMethod())) {
            respond(ex, 405, "{\"error\":\"POST required\"}");
            return;
        }
        com.microsoft.playwright.Page page = playwrightPage;
        if (page == null) {
            respond(ex, 503, "{\"error\":\"Playwright Page not bound yet\"}");
            return;
        }
        try {
            String body = new String(ex.getRequestBody().readAllBytes(), StandardCharsets.UTF_8);
            com.google.gson.JsonObject root = com.google.gson.JsonParser.parseString(body).getAsJsonObject();
            String action   = root.has("action")   ? root.get("action").getAsString()   : "";
            String selector = root.has("selector") ? root.get("selector").getAsString() : null;
            String text     = root.has("text")     ? root.get("text").getAsString()     : null;
            String url      = root.has("url")      ? root.get("url").getAsString()      : null;
            int timeoutMs   = root.has("timeoutMs")? root.get("timeoutMs").getAsInt()   : 5000;

            // For "frame.locator()" we treat 'xpath=...' as XPath, else CSS
            com.microsoft.playwright.Locator loc = (selector != null && !selector.isBlank())
                    ? page.locator(selector).first()
                    : null;

            // Set default timeout for this op
            com.microsoft.playwright.Locator.ClickOptions clickOpts = new com.microsoft.playwright.Locator.ClickOptions().setTimeout(timeoutMs);
            com.microsoft.playwright.Locator.FillOptions  fillOpts  = new com.microsoft.playwright.Locator.FillOptions().setTimeout(timeoutMs);
            com.microsoft.playwright.Locator.HoverOptions hoverOpts = new com.microsoft.playwright.Locator.HoverOptions().setTimeout(timeoutMs);

            String result;
            long start = System.currentTimeMillis();
            switch (action) {
                case "click":
                    if (loc == null) { respond(ex, 400, "{\"error\":\"selector required\"}"); return; }
                    loc.click(clickOpts);
                    result = "clicked";
                    break;
                case "fill":
                    if (loc == null) { respond(ex, 400, "{\"error\":\"selector required\"}"); return; }
                    loc.fill(text == null ? "" : text, fillOpts);
                    result = "filled with: " + (text == null ? "(empty)" : text);
                    break;
                case "hover":
                    if (loc == null) { respond(ex, 400, "{\"error\":\"selector required\"}"); return; }
                    loc.hover(hoverOpts);
                    result = "hovered";
                    break;
                case "scroll":
                    if (loc == null) { respond(ex, 400, "{\"error\":\"selector required\"}"); return; }
                    loc.scrollIntoViewIfNeeded(new com.microsoft.playwright.Locator.ScrollIntoViewIfNeededOptions().setTimeout(timeoutMs));
                    result = "scrolled into view";
                    break;
                case "press":
                    if (loc != null) loc.press(text == null ? "Enter" : text, new com.microsoft.playwright.Locator.PressOptions().setTimeout(timeoutMs));
                    else page.keyboard().press(text == null ? "Enter" : text);
                    result = "pressed " + text;
                    break;
                case "navigate":
                    if (url == null) { respond(ex, 400, "{\"error\":\"url required\"}"); return; }
                    page.navigate(url);
                    result = "navigated to " + url;
                    break;
                default:
                    respond(ex, 400, "{\"error\":\"unknown action: " + action + "\"}");
                    return;
            }
            long elapsed = System.currentTimeMillis() - start;
            System.out.println("[Recorder] perform " + action + " · " + (selector != null ? selector : url) + " · " + elapsed + "ms");
            respond(ex, 200, "{\"ok\":true,\"action\":\"" + action + "\",\"result\":\""
                    + result.replace("\"", "'") + "\",\"elapsedMs\":" + elapsed + "}");
        } catch (com.microsoft.playwright.TimeoutError te) {
            String msg = te.getMessage() == null ? "timeout" : te.getMessage().split("\n")[0];
            respond(ex, 408, "{\"ok\":false,\"error\":\"" + msg.replace("\"", "'") + "\"}");
        } catch (Exception e) {
            String msg = e.getMessage() == null ? e.getClass().getSimpleName() : e.getMessage().split("\n")[0];
            respond(ex, 500, "{\"ok\":false,\"error\":\"" + msg.replace("\"", "'") + "\"}");
        }
    }

    private void handleAction(HttpExchange ex) throws IOException {
        if (preflight(ex)) return;
        if (!"POST".equalsIgnoreCase(ex.getRequestMethod())) { respond(ex, 405, "{\"error\":\"POST required\"}"); return; }
        // E06: discard events while paused
        if (paused.get()) {
            respond(ex, 200, "{\"ok\":true,\"discarded\":true,\"paused\":true,\"count\":" + actions.size() + "}");
            return;
        }
        try {
            String body = new String(ex.getRequestBody().readAllBytes(), StandardCharsets.UTF_8);
            RecordedAction a = gson.fromJson(body, RecordedAction.class);
            if (a == null || a.type == null) { respond(ex, 400, "{\"error\":\"type missing\"}"); return; }
            if (a.timestamp == null) a.timestamp = System.currentTimeMillis();
            actions.add(a);
            System.out.println("[Recorder] action #" + actions.size() + " - " + a.type
                    + (a.element != null && a.element.tag != null ? " <" + a.element.tag + ">" : "")
                    + (a.text != null && !a.text.isBlank() ? " text=\"" + truncate(a.text) + "\"" : "")
            );
            respond(ex, 200, "{\"ok\":true,\"count\":" + actions.size() + "}");
        } catch (JsonSyntaxException e) {
            respond(ex, 400, "{\"error\":\"JSON parse error\"}");
        }
    }

    private void handlePause(HttpExchange ex) throws IOException {
        if (preflight(ex)) return;
        paused.set(true);
        System.out.println("[Recorder] ⏸ PAUSED — incoming events will be discarded.");
        respond(ex, 200, "{\"ok\":true,\"paused\":true,\"actions\":" + actions.size() + "}");
    }

    private void handleResume(HttpExchange ex) throws IOException {
        if (preflight(ex)) return;
        paused.set(false);
        System.out.println("[Recorder] ▶ RESUMED — recording continues.");
        respond(ex, 200, "{\"ok\":true,\"paused\":false,\"actions\":" + actions.size() + "}");
    }

    private void handleStop(HttpExchange ex) throws IOException {
        if (preflight(ex)) return;
        System.out.println("[Recorder] /stop triggered (toolbar)");
        respond(ex, 200, "{\"ok\":true}");
        stopSignal.complete(null);
    }

    private void handleStatus(HttpExchange ex) throws IOException {
        if (preflight(ex)) return;
        respond(ex, 200, "{\"running\":true,\"paused\":" + paused.get() + ",\"actions\":" + actions.size() + "}");
    }

    private void handleListActions(HttpExchange ex) throws IOException {
        if (preflight(ex)) return;
        synchronized (actions) {
            respond(ex, 200, gson.toJson(actions));
        }
    }

    /** Remove the last recorded action. */
    private void handleUndo(HttpExchange ex) throws IOException {
        if (preflight(ex)) return;
        if (!"POST".equalsIgnoreCase(ex.getRequestMethod())) { respond(ex, 405, "{\"error\":\"POST required\"}"); return; }
        synchronized (actions) {
            if (actions.isEmpty()) {
                respond(ex, 200, "{\"ok\":false,\"reason\":\"list empty\"}");
                return;
            }
            int idx = actions.size() - 1;
            RecordedAction removed = actions.remove(idx);
            System.out.println("[Recorder] /undo -> removed action #" + (idx + 1) + ": " + removed.type);
            respond(ex, 200, "{\"ok\":true,\"removed_index\":" + idx + ",\"count\":" + actions.size() + "}");
        }
    }

    /**
     * Inject an action from outside the browser (e.g. the dashboard quick-add panel).
     * If the request body contains useLastElement=true, the action's element field
     * is populated from the most recent action that had one.
     */
    private void handleInject(HttpExchange ex) throws IOException {
        if (preflight(ex)) return;
        if (!"POST".equalsIgnoreCase(ex.getRequestMethod())) { respond(ex, 405, "{\"error\":\"POST required\"}"); return; }
        try {
            String body = new String(ex.getRequestBody().readAllBytes(), StandardCharsets.UTF_8);
            com.google.gson.JsonObject root = com.google.gson.JsonParser.parseString(body).getAsJsonObject();
            boolean useLast = root.has("useLastElement") && root.get("useLastElement").getAsBoolean();
            RecordedAction action = gson.fromJson(root, RecordedAction.class);
            if (action == null || action.type == null || action.type.isBlank()) {
                respond(ex, 400, "{\"error\":\"type missing\"}");
                return;
            }
            if (action.timestamp == null) action.timestamp = System.currentTimeMillis();

            if (useLast && action.element == null) {
                synchronized (actions) {
                    for (int i = actions.size() - 1; i >= 0; i--) {
                        RecordedAction prev = actions.get(i);
                        if (prev.element != null) { action.element = prev.element; break; }
                    }
                }
                if (action.element == null) {
                    respond(ex, 400, "{\"error\":\"Henuz yakalanmis bir element yok\"}");
                    return;
                }
            }

            synchronized (actions) {
                actions.add(action);
                System.out.println("[Recorder] /inject -> " + action.type
                        + (action.element != null ? " on <" + action.element.tag + ">" : ""));
                respond(ex, 200, "{\"ok\":true,\"count\":" + actions.size() + "}");
            }
        } catch (Exception e) {
            respond(ex, 400, "{\"error\":\"" + e.getMessage().replace("\"", "'") + "\"}");
        }
    }

    /** Most recent captured element (to preview which element next assertions target). */
    private void handleLastElement(HttpExchange ex) throws IOException {
        if (preflight(ex)) return;
        synchronized (actions) {
            for (int i = actions.size() - 1; i >= 0; i--) {
                RecordedAction a = actions.get(i);
                if (a.element != null) {
                    respond(ex, 200, gson.toJson(a.element));
                    return;
                }
            }
        }
        respond(ex, 200, "null");
    }

    /* --------------------------------------------------------------- */

    /**
     * OPTIONS preflight + CORS headers (incl. Private Network Access).
     *
     * Chromium blocks fetch() from public-https sites to private-IP loopback
     * unless the target answers with "Access-Control-Allow-Private-Network: true"
     * on the CORS preflight. We send it on every response just to be safe.
     */
    private boolean preflight(HttpExchange ex) throws IOException {
        ex.getResponseHeaders().add("Access-Control-Allow-Origin", "*");
        ex.getResponseHeaders().add("Access-Control-Allow-Methods", "GET,POST,OPTIONS,DELETE");
        ex.getResponseHeaders().add("Access-Control-Allow-Headers",
                "Content-Type, Access-Control-Request-Private-Network");
        ex.getResponseHeaders().add("Access-Control-Allow-Private-Network", "true");
        ex.getResponseHeaders().add("Access-Control-Max-Age", "600");
        if ("OPTIONS".equalsIgnoreCase(ex.getRequestMethod())) {
            ex.sendResponseHeaders(204, -1);
            return true;
        }
        return false;
    }

    private void respond(HttpExchange ex, int status, String json) throws IOException {
        byte[] body = json.getBytes(StandardCharsets.UTF_8);
        ex.getResponseHeaders().set("Content-Type", "application/json; charset=utf-8");
        ex.sendResponseHeaders(status, body.length);
        try (OutputStream os = ex.getResponseBody()) {
            os.write(body);
        }
    }

    private static String truncate(String s) {
        return s.length() > 30 ? s.substring(0, 30) + "..." : s;
    }
}
