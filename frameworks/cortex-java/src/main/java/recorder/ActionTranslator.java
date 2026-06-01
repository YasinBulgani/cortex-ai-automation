package recorder;

import crypto.EncryptionManager;
import crypto.PasswordManager;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Translates the list of RecordedAction into Gherkin lines that match the
 * existing step-def phrases plus a locator pool.
 *
 * The produced feature file runs out-of-the-box with the existing Cucumber +
 * Selenium step defs (CommonSteps, InputSteps, etc.) and the Playwright runner.
 */
public class ActionTranslator {

    public record TranslationResult(
            List<String> gherkinLines,
            Map<String, Map<String, String>> locatorEntries
    ) {}

    /**
     * Slug derived from the recording's feature name (e.g. {@code recorded_20260524_163316}).
     * Used to build a session-unique default password alias so that recording
     * three different login scenarios doesn't cause the last one to silently
     * overwrite the first two in password.properties.
     *
     * <p>Null means "no context provided" — falls back to {@code "recordedPassword"}
     * for backward compatibility (unit tests that call the no-arg constructor).</p>
     */
    private final String featureSlug;

    /** Full constructor — use from {@link recorder.RecorderMain} to get collision-safe aliases. */
    public ActionTranslator(String featureSlug) {
        this.featureSlug = (featureSlug == null || featureSlug.isBlank()) ? null : featureSlug;
    }

    /** No-arg constructor kept for backward compatibility (tests, external callers). */
    public ActionTranslator() {
        this(null);
    }

    private final LocatorBuilder locatorBuilder = new LocatorBuilder();

    public TranslationResult translate(List<RecordedAction> actions) {
        // Seven-pass noise removal — order matters:
        //   0. recorder-injected UI elements      → drop entirely (cortex-* IDs)
        //   1. Consecutive fills on same element  → last value wins (keystroke noise)
        //   2. Consecutive clicks on same element → single click (banner double-tap, etc.)
        //   3. Click-then-fill on same input      → drop the click (focus-then-type)
        //   4. about:blank / chrome:// nav        → drop (Chromium boot noise)
        //   5. Consecutive same-URL navigates    → one (redirect/reinject duplicates)
        //   6. <a href> click + matching nav     → drop the nav (click-induced)
        actions = dropRecorderInternalActions(actions);
        actions = coalesceConsecutiveFills(actions);
        actions = coalesceConsecutiveClicks(actions);
        actions = dropFocusClicks(actions);
        actions = dropNoiseNavigates(actions);
        actions = coalesceConsecutiveNavigates(actions);
        actions = dropClickInducedNavigates(actions);

        List<String> lines = new ArrayList<>();
        Map<String, Map<String, String>> locators = new LinkedHashMap<>();

        for (RecordedAction a : actions) {
            if (a == null || a.type == null) continue;

            switch (a.type) {
                case "navigate" -> lines.add("    Given I open the recorded url \"" + a.url + "\"");
                case "wait"     -> lines.add("    * I wait for " + (a.seconds == null ? 1 : a.seconds) + " seconds");
                case "comment"  -> lines.add("    # " + nullToEmpty(a.text));
                case "click"    -> emitWithLocator(a, locators, lines,
                        loc -> "    When I click \"" + loc.key() + "\"");
                case "fill", "change" -> emitWithLocator(a, locators, lines, loc -> {
                    if (a.element != null && a.element.isPassword) {
                        String alias = (a.passwordAlias != null && !a.passwordAlias.isBlank())
                                ? a.passwordAlias
                                // Derive a session-unique alias from the feature slug so that
                                // recording N different login scenarios produces N distinct
                                // aliases (e.g. recorded_20260524_163316_password) instead of
                                // all colliding on "recordedPassword".
                                : (featureSlug != null ? featureSlug + "_password" : "recordedPassword");
                        // Persist the typed password under the alias so the generated test
                        // can actually decrypt at runtime. Without this, the recorder leaves
                        // the test in a broken state — the step references an alias that does
                        // not exist in password.properties, so DecryptUtil throws
                        // "No encrypted password found for alias".
                        persistPasswordForAlias(alias, nullToEmpty(a.text), lines);
                        return "    * I enter encrypted password alias \"" + alias + "\" into \"" + loc.key() + "\"";
                    }
                    return "    * I write \"" + nullToEmpty(a.text) + "\" into \"" + loc.key() + "\"";
                });
                case "press" -> {
                    String key = nullToEmpty(a.key).toUpperCase();
                    lines.add("    * I press \"" + key + "\"");
                }
                case "hover" -> emitWithLocator(a, locators, lines,
                        loc -> "    * I hover over \"" + loc.key() + "\"");
                case "scroll" -> emitWithLocator(a, locators, lines,
                        loc -> "    * I scroll to \"" + loc.key() + "\"");
                case "assert_visible" -> emitWithLocator(a, locators, lines,
                        loc -> "    Then I see \"" + loc.key() + "\"");
                case "assert_text" -> emitWithLocator(a, locators, lines,
                        loc -> "    Then I verify \"" + loc.key() + "\" contains \"" + nullToEmpty(a.text) + "\"");
                case "assert_value" -> emitWithLocator(a, locators, lines,
                        loc -> "    Then I verify \"" + loc.key() + "\" value is \"" + nullToEmpty(a.text) + "\"");
                case "custom" -> {
                    String t = nullToEmpty(a.text).trim();
                    if (!t.isEmpty()) {
                        // If user wrote a bare phrase, prefix with *
                        String prefix = t.matches("^(Given|When|Then|And|But|\\*)\\b.*") ? "" : "* ";
                        lines.add("    " + prefix + t);
                    }
                }
                case "reload" -> lines.add("    * I reload current page");
                case "back"   -> lines.add("    * I go back and see previous page");
                default -> lines.add("    # (unknown action) " + a.type);
            }
        }

        return new TranslationResult(lines, locators);
    }

    private void emitWithLocator(RecordedAction a,
                                 Map<String, Map<String, String>> locators,
                                 List<String> lines,
                                 java.util.function.Function<LocatorBuilder.Locator, String> stepFn) {
        if (a.element == null) {
            lines.add("    # (element info missing) " + a.type);
            return;
        }
        LocatorBuilder.Locator loc = locatorBuilder.build(a.element);

        // Reuse an existing locator key if (type, value) already maps to one.
        // Without this, the same DOM node ends up with keys email, email_2,
        // email_3 across multiple captures — same data, different keys.
        String reusedKey = null;
        for (Map.Entry<String, Map<String, String>> e : locators.entrySet()) {
            Map<String, String> v = e.getValue();
            if (loc.type().equals(v.get("type")) && loc.value().equals(v.get("value"))) {
                reusedKey = e.getKey();
                break;
            }
        }
        LocatorBuilder.Locator effective = (reusedKey != null)
                ? new LocatorBuilder.Locator(reusedKey, loc.type(), loc.value())
                : loc;

        if (reusedKey == null) {
            Map<String, String> entry = new LinkedHashMap<>();
            entry.put("key", loc.key());
            entry.put("type", loc.type());
            entry.put("value", loc.value());
            locators.put(loc.key(), entry);
        }
        lines.add(stepFn.apply(effective));
    }

    private static String nullToEmpty(String s) { return s == null ? "" : s; }

    /**
     * Collapse consecutive fill/change events that target the same element down
     * to the final value. Keystroke-by-keystroke noise removal — without this
     * the .feature looks like:
     * <pre>
     *   * I write "y" into "email"
     *   * I write "ya" into "email"
     *   * I write "yas" into "email"
     *   ... etc
     * </pre>
     * after this:
     * <pre>
     *   * I write "yasinbulgan1995@gmail.com" into "email"
     * </pre>
     */
    static List<RecordedAction> coalesceConsecutiveFills(List<RecordedAction> in) {
        if (in == null || in.size() <= 1) return in;
        List<RecordedAction> out = new ArrayList<>(in.size());
        for (RecordedAction a : in) {
            boolean isFill = a != null && ("fill".equals(a.type) || "change".equals(a.type));
            if (isFill && !out.isEmpty()) {
                RecordedAction prev = out.get(out.size() - 1);
                if (a.type.equals(prev.type) && sameElement(prev.element, a.element)) {
                    // Same element, same action type → keep the LATER one (newest text).
                    out.set(out.size() - 1, a);
                    continue;
                }
            }
            out.add(a);
        }
        return out;
    }

    /**
     * Heuristic element identity check. Returns true if two ElementInfo records
     * describe the same DOM node. We can't use cssPath alone because
     * recorder.js sometimes regenerates path indices between events.
     */
    static boolean sameElement(RecordedAction.ElementInfo a, RecordedAction.ElementInfo b) {
        if (a == null || b == null) return false;
        // Strongest signals first.
        if (eq(a.dataTestId, b.dataTestId) && a.dataTestId != null) return true;
        if (eq(a.id,         b.id)         && a.id         != null) return true;
        if (eq(a.xpath,      b.xpath)      && a.xpath      != null) return true;
        if (eq(a.cssPath,    b.cssPath)    && a.cssPath    != null) return true;
        // Name + tag is a reasonable form-input signal.
        if (eq(a.name, b.name) && a.name != null && eq(a.tag, b.tag)) return true;
        // ariaLabel match on form-like tags.
        if (eq(a.ariaLabel, b.ariaLabel) && a.ariaLabel != null && eq(a.tag, b.tag)) return true;
        return false;
    }

    private static boolean eq(String x, String y) {
        return x == null ? y == null : x.equals(y);
    }

    /**
     * Drop consecutive click events on the same element. Banner close buttons,
     * accidental double-clicks, and focus events fired through onclick produce
     * pairs/triples of click actions that all do the same thing.
     */
    static List<RecordedAction> coalesceConsecutiveClicks(List<RecordedAction> in) {
        if (in == null || in.size() <= 1) return in;
        List<RecordedAction> out = new ArrayList<>(in.size());
        for (RecordedAction a : in) {
            if (a != null && "click".equals(a.type) && !out.isEmpty()) {
                RecordedAction prev = out.get(out.size() - 1);
                if ("click".equals(prev.type) && sameElement(prev.element, a.element)) {
                    continue; // drop the duplicate
                }
            }
            out.add(a);
        }
        return out;
    }

    /**
     * Drop a click that immediately precedes a fill/change on the same
     * input-like element. The click is just the focus event; the fill itself
     * implies the focus.
     */
    static List<RecordedAction> dropFocusClicks(List<RecordedAction> in) {
        if (in == null || in.size() <= 1) return in;
        List<RecordedAction> out = new ArrayList<>(in.size());
        for (int i = 0; i < in.size(); i++) {
            RecordedAction a = in.get(i);
            if (a != null && "click".equals(a.type) && i + 1 < in.size()) {
                RecordedAction next = in.get(i + 1);
                if (next != null && ("fill".equals(next.type) || "change".equals(next.type))
                        && sameElement(a.element, next.element)
                        && isInputLike(a.element)) {
                    continue; // drop the focus click
                }
            }
            out.add(a);
        }
        return out;
    }

    private static boolean isInputLike(RecordedAction.ElementInfo e) {
        if (e == null) return false;
        if ("input".equals(e.tag) || "textarea".equals(e.tag) || "select".equals(e.tag)) return true;
        if (e.role != null) {
            String r = e.role;
            return r.equals("textbox") || r.equals("combobox") || r.equals("searchbox");
        }
        return false;
    }

    /**
     * Drop browser-internal navigates: about:blank (Chromium boot), chrome://*
     * (internal pages), and data: URIs. None of these are part of the test
     * scenario.
     */
    static List<RecordedAction> dropNoiseNavigates(List<RecordedAction> in) {
        if (in == null) return in;
        List<RecordedAction> out = new ArrayList<>(in.size());
        for (RecordedAction a : in) {
            if (a != null && "navigate".equals(a.type) && a.url != null) {
                String u = a.url;
                if (u.equals("about:blank") || u.startsWith("chrome://")
                        || u.startsWith("chrome-extension://")
                        || u.startsWith("data:") || u.equals("about:srcdoc")) {
                    continue;
                }
            }
            out.add(a);
        }
        return out;
    }

    /**
     * Two navigates to the same URL in a row → keep one. Comes from
     * recorder.js's re-inject-after-nav handler firing twice for SPA
     * pushState + actual nav, and from server-side redirects that resolve
     * to the same canonical URL.
     */
    static List<RecordedAction> coalesceConsecutiveNavigates(List<RecordedAction> in) {
        if (in == null || in.size() <= 1) return in;
        List<RecordedAction> out = new ArrayList<>(in.size());
        for (RecordedAction a : in) {
            if (a != null && "navigate".equals(a.type) && a.url != null && !out.isEmpty()) {
                RecordedAction prev = out.get(out.size() - 1);
                if ("navigate".equals(prev.type) && a.url.equals(prev.url)) {
                    continue;
                }
            }
            out.add(a);
        }
        return out;
    }

    /**
     * If a click on an &lt;a href&gt; (or anything with an href attribute) is
     * immediately followed by a navigate to the same URL, drop the navigate
     * — clicking the link IS the navigation, so the explicit step is
     * redundant. Conservative match: relative hrefs are accepted only if the
     * absolute navigate URL ends with them.
     */
    static List<RecordedAction> dropClickInducedNavigates(List<RecordedAction> in) {
        if (in == null || in.size() <= 1) return in;
        List<RecordedAction> out = new ArrayList<>(in.size());
        for (RecordedAction a : in) {
            if (a != null && "navigate".equals(a.type) && a.url != null && !out.isEmpty()) {
                RecordedAction prev = out.get(out.size() - 1);
                if ("click".equals(prev.type) && prev.element != null
                        && prev.element.href != null
                        && hrefMatchesNav(prev.element.href, a.url)) {
                    continue;
                }
            }
            out.add(a);
        }
        return out;
    }

    private static boolean hrefMatchesNav(String href, String navUrl) {
        if (href == null || navUrl == null) return false;
        String n = normalizeUrl(navUrl);
        String h = normalizeUrl(href);
        if (n.equals(h)) return true;
        // Relative href → match if absolute nav URL ends with it.
        if (h.startsWith("/") && n.endsWith(h)) return true;
        return false;
    }

    private static String normalizeUrl(String u) {
        if (u == null) return "";
        int hash = u.indexOf('#');
        if (hash >= 0) u = u.substring(0, hash);
        while (u.length() > 1 && u.endsWith("/")) u = u.substring(0, u.length() - 1);
        return u;
    }

    /**
     * Drop actions whose target is part of the recorder's own injected UI
     * (probe, debug overlay, big banner, pick mode helpers). These elements
     * only exist while the recorder.js script is live; at replay time they
     * are absent, so any captured click against them is doomed to fail.
     * Identified by IDs / dataset attributes that start with the
     * {@code cortex-} or {@code cortex-rec-} prefixes.
     */
    static List<RecordedAction> dropRecorderInternalActions(List<RecordedAction> in) {
        if (in == null) return in;
        List<RecordedAction> out = new ArrayList<>(in.size());
        for (RecordedAction a : in) {
            if (a != null && isRecorderInternal(a.element)) continue;
            out.add(a);
        }
        return out;
    }

    private static boolean isRecorderInternal(RecordedAction.ElementInfo e) {
        if (e == null) return false;
        String id = e.id == null ? "" : e.id;
        if (id.startsWith("cortex-rec-") || id.equals("cortex-rec-toolbar")
                || id.equals("cortex-rec-debug") || id.equals("cortex-rec-debug-text")
                || id.equals("cortex-rec-probe") || id.equals("cortex-rec-err")
                || id.equals("cortex-rec-toast") || id.equals("cortex-rec-anim")
                || id.equals("cortex-bigbanner") || id.equals("cortex-bigbanner-close")
                || id.equals("cortex-banner-anim")
                || id.startsWith("cortex-pick-") || id.startsWith("cortex-action-")) {
            return true;
        }
        // Closest ancestor check via cssPath / xpath when id is missing.
        String cssPath = e.cssPath == null ? "" : e.cssPath;
        if (cssPath.contains("#cortex-rec-") || cssPath.contains("#cortex-bigbanner")
                || cssPath.contains("#cortex-pick-")) {
            return true;
        }
        return false;
    }

    /**
     * Encrypts and saves the typed password under {@code alias} so the recorded
     * feature's "I enter encrypted password alias ... into ..." step can actually
     * decrypt at runtime.
     *
     * <p>Failure modes are non-fatal — we never want the recording itself to crash
     * just because credentials cannot be persisted. Instead we drop a {@code #} comment
     * into the generated feature so the human sees what went wrong:</p>
     * <ul>
     *   <li>Empty password → comment "skipped (empty value)"</li>
     *   <li>aes.key missing → comment with setup instructions</li>
     *   <li>Same encrypted value already saved → silent (no-op)</li>
     * </ul>
     */
    private void persistPasswordForAlias(String alias, String plain, List<String> outLines) {
        if (plain == null || plain.isEmpty()) {
            outLines.add("    # [recorder] password persist skipped — empty value captured for alias \""
                    + alias + "\"");
            return;
        }
        try {
            // If alias already has a value, leave it alone (user may have manually
            // set a different password). Re-encrypting the same plaintext would
            // produce a different ciphertext anyway (GCM uses a fresh IV).
            if (PasswordManager.contains(alias)) {
                return;
            }
            EncryptionManager.encryptAndSaveToPasswordFile(plain, alias);
        } catch (Exception e) {
            String msg = e.getMessage() == null ? e.getClass().getSimpleName() : e.getMessage();
            outLines.add("    # [recorder] password persist FAILED for alias \"" + alias + "\": "
                    + msg.replace('\n', ' '));
            outLines.add("    # [recorder] To fix: set CORTEX_AES_KEY=<16 chars> in .env,");
            outLines.add("    # then run EncryptionManager.encryptAndSaveToPasswordFile(<plain>, \""
                    + alias + "\")");
        }
    }
}
