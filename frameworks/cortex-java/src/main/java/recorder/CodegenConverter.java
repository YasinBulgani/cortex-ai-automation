package recorder;

import java.util.ArrayList;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Converts a Playwright codegen JavaScript file (target=playwright-test) into
 * the same {@link RecordedAction} list produced by the legacy in-page recorder.
 * After this step, the existing {@link ActionTranslator} + {@link FeatureWriter}
 * pipeline does the rest — so .feature output is identical to the legacy path.
 *
 * <p>This is the converter half of the "Method A — Playwright Codegen" approach.
 * The other half is {@link CodegenRecorder}, which spawns codegen, waits for
 * the user to finish, and then feeds the produced .ts file through this class.
 *
 * <p>Supported patterns (each must occur on its own line in the codegen output):
 * <pre>
 *   await page.goto('URL');
 *   await page.getByRole('button', { name: 'X' }).click();
 *   await page.getByRole('button', { name: 'X' }).press('Enter');
 *   await page.getByLabel('Y').fill('text');
 *   await page.getByPlaceholder('Z').click();
 *   await page.getByText('text').click();
 *   await page.getByTestId('id').click();
 *   await page.getByAltText('img').click();
 *   await page.getByTitle('t').hover();
 *   await page.locator('css').selectOption('value');
 * </pre>
 *
 * <p>Unrecognised lines are skipped silently. expect(...) assertions are
 * mapped to assert_visible / assert_text where possible.
 */
public class CodegenConverter {

    // page.goto('url')
    private static final Pattern GOTO_RE = Pattern.compile(
            "await\\s+page\\.goto\\(\\s*(['\"`])([^'\"`]+)\\1\\s*\\)\\s*;?"
    );

    // Generic action chain:   page.<chain>.<verb>(<args>)
    // Greedy on chain, lazy on verb arguments.
    private static final Pattern ACTION_RE = Pattern.compile(
            "await\\s+page\\.(.+)\\.(click|dblclick|check|uncheck|hover|press|fill|selectOption|focus|tap)" +
            "\\(\\s*(.*?)\\s*\\)\\s*;?\\s*$"
    );

    // expect(page.<chain>).toBeVisible()
    private static final Pattern EXPECT_VISIBLE_RE = Pattern.compile(
            "await\\s+expect\\(\\s*page\\.(.+?)\\s*\\)\\.toBeVisible\\(\\s*\\)\\s*;?"
    );

    // expect(page.<chain>).toContainText('text')
    private static final Pattern EXPECT_TEXT_RE = Pattern.compile(
            "await\\s+expect\\(\\s*page\\.(.+?)\\s*\\)\\.toContainText\\(\\s*(['\"`])([^'\"`]*?)\\2\\s*\\)\\s*;?"
    );

    // Locator builders. Match the FIRST one in the chain — codegen normally
    // doesn't deeply nest them. Order matters: most-specific first.
    private static final Pattern GET_BY_ROLE_RE = Pattern.compile(
            "getByRole\\(\\s*(['\"`])(\\w+)\\1\\s*(?:,\\s*\\{[^}]*?\\bname\\s*:\\s*(['\"`])([^'\"`]*?)\\3[^}]*\\})?\\s*\\)"
    );
    private static final Pattern GET_BY_LABEL_RE       = Pattern.compile("getByLabel\\(\\s*(['\"`])([^'\"`]*?)\\1\\s*\\)");
    private static final Pattern GET_BY_PLACEHOLDER_RE = Pattern.compile("getByPlaceholder\\(\\s*(['\"`])([^'\"`]*?)\\1\\s*\\)");
    private static final Pattern GET_BY_TEXT_RE        = Pattern.compile("getByText\\(\\s*(['\"`])([^'\"`]*?)\\1\\s*\\)");
    private static final Pattern GET_BY_TESTID_RE      = Pattern.compile("getByTestId\\(\\s*(['\"`])([^'\"`]*?)\\1\\s*\\)");
    private static final Pattern GET_BY_ALT_RE         = Pattern.compile("getByAltText\\(\\s*(['\"`])([^'\"`]*?)\\1\\s*\\)");
    private static final Pattern GET_BY_TITLE_RE       = Pattern.compile("getByTitle\\(\\s*(['\"`])([^'\"`]*?)\\1\\s*\\)");
    private static final Pattern LOCATOR_RE            = Pattern.compile("locator\\(\\s*(['\"`])([^'\"`]*?)\\1\\s*\\)");

    public List<RecordedAction> parse(String codegenSource) {
        List<RecordedAction> out = new ArrayList<>();
        long ts = System.currentTimeMillis();

        for (String raw : codegenSource.split("\\r?\\n")) {
            String line = raw.trim();
            if (line.isEmpty()) continue;
            if (line.startsWith("//") || line.startsWith("/*") || line.startsWith("*")) continue;
            if (line.startsWith("import ") || line.startsWith("test(") || line.startsWith("test.")) continue;
            if (line.startsWith("(async") || line.startsWith("const ") || line.startsWith("let ")) continue;
            if (line.startsWith("await browser") || line.startsWith("await context")) continue;
            if (line.equals("});") || line.equals("})();")) continue;

            // 1) page.goto('url')
            Matcher mGoto = GOTO_RE.matcher(line);
            if (mGoto.find()) {
                RecordedAction a = new RecordedAction();
                a.type = "navigate";
                a.url = mGoto.group(2);
                a.timestamp = ts++;
                out.add(a);
                continue;
            }

            // 2) expect(...).toBeVisible() → assert_visible
            Matcher mVis = EXPECT_VISIBLE_RE.matcher(line);
            if (mVis.find()) {
                RecordedAction a = new RecordedAction();
                a.type = "assert_visible";
                a.element = parseLocator(mVis.group(1));
                a.timestamp = ts++;
                out.add(a);
                continue;
            }

            // 3) expect(...).toContainText('text') → assert_text
            Matcher mTxt = EXPECT_TEXT_RE.matcher(line);
            if (mTxt.find()) {
                RecordedAction a = new RecordedAction();
                a.type = "assert_text";
                a.element = parseLocator(mTxt.group(1));
                a.text = mTxt.group(3);
                a.timestamp = ts++;
                out.add(a);
                continue;
            }

            // 4) page.<locator-chain>.<verb>(args)
            Matcher m = ACTION_RE.matcher(line);
            if (m.find()) {
                RecordedAction a = mapAction(m.group(1), m.group(2), m.group(3));
                if (a != null) {
                    a.timestamp = ts++;
                    out.add(a);
                }
                continue;
            }

            // Unknown line — kept as a comment for visibility in the .feature.
            if (line.startsWith("await ") || line.startsWith("page.")) {
                RecordedAction a = new RecordedAction();
                a.type = "comment";
                a.text = "codegen: " + line;
                a.timestamp = ts++;
                out.add(a);
            }
        }
        return out;
    }

    private RecordedAction mapAction(String locatorChain, String verb, String args) {
        RecordedAction.ElementInfo el = parseLocator(locatorChain);
        RecordedAction a = new RecordedAction();
        a.element = el;

        switch (verb) {
            case "click":
            case "dblclick":
            case "check":
            case "uncheck":
            case "tap":
                a.type = "click";
                return a;
            case "focus":
            case "hover":
                a.type = "hover";
                return a;
            case "press":
                a.type = "press";
                a.key = unquote(firstArg(args));
                return a;
            case "fill":
                a.type = "fill";
                a.text = unquote(firstArg(args));
                if (el != null && el.isPassword) {
                    a.passwordAlias = (el.name != null && !el.name.isBlank())
                            ? el.name
                            : "recordedPassword";
                }
                return a;
            case "selectOption":
                a.type = "change";
                a.text = unquote(firstArg(args));
                return a;
            default:
                return null;
        }
    }

    /**
     * Parse the locator-builder chain (e.g. {@code getByRole('button', { name: 'Login' })})
     * into an {@link RecordedAction.ElementInfo}. {@link LocatorBuilder} downstream
     * uses these fields (role, ariaLabel, dataTestId, text, placeholder, cssPath)
     * to build a stable Selenium key.
     */
    RecordedAction.ElementInfo parseLocator(String chain) {
        RecordedAction.ElementInfo el = new RecordedAction.ElementInfo();
        if (chain == null) return el;

        Matcher mRole = GET_BY_ROLE_RE.matcher(chain);
        if (mRole.find()) {
            el.role = mRole.group(2);
            if (mRole.group(4) != null) el.text = mRole.group(4);
            // Map common roles to tag for downstream readability.
            el.tag = roleToTag(el.role);
            // Heuristic: role=textbox + name like "şifre" => mark as password.
            if ("textbox".equals(el.role) && el.text != null) {
                String lower = el.text.toLowerCase();
                if (lower.contains("password") || lower.contains("şifre") || lower.contains("sifre")) {
                    el.isPassword = true;
                }
            }
            return el;
        }

        Matcher mLabel = GET_BY_LABEL_RE.matcher(chain);
        if (mLabel.find()) {
            el.ariaLabel = mLabel.group(2);
            String lower = el.ariaLabel.toLowerCase();
            if (lower.contains("password") || lower.contains("şifre") || lower.contains("sifre")) {
                el.isPassword = true;
            }
            return el;
        }

        Matcher mPh = GET_BY_PLACEHOLDER_RE.matcher(chain);
        if (mPh.find()) {
            el.placeholder = mPh.group(2);
            return el;
        }

        Matcher mTestId = GET_BY_TESTID_RE.matcher(chain);
        if (mTestId.find()) {
            el.dataTestId = mTestId.group(2);
            return el;
        }

        Matcher mText = GET_BY_TEXT_RE.matcher(chain);
        if (mText.find()) {
            el.text = mText.group(2);
            return el;
        }

        Matcher mAlt = GET_BY_ALT_RE.matcher(chain);
        if (mAlt.find()) {
            el.ariaLabel = mAlt.group(2);
            el.tag = "img";
            return el;
        }

        Matcher mTitle = GET_BY_TITLE_RE.matcher(chain);
        if (mTitle.find()) {
            el.ariaLabel = mTitle.group(2);
            return el;
        }

        Matcher mLoc = LOCATOR_RE.matcher(chain);
        if (mLoc.find()) {
            el.cssPath = mLoc.group(2);
            return el;
        }

        return el;
    }

    private static String roleToTag(String role) {
        if (role == null) return null;
        return switch (role) {
            case "button"      -> "button";
            case "link"        -> "a";
            case "textbox"     -> "input";
            case "checkbox"    -> "input";
            case "radio"       -> "input";
            case "combobox"    -> "select";
            case "img"         -> "img";
            case "heading"     -> "h1";
            default            -> null;
        };
    }

    private static String firstArg(String args) {
        if (args == null) return "";
        // codegen separates multiple args by comma — but quoted strings may
        // contain commas. Cheap split: find the first balanced top-level comma.
        int depth = 0;
        char open = 0;
        for (int i = 0; i < args.length(); i++) {
            char c = args.charAt(i);
            if (open == 0 && (c == '\'' || c == '"' || c == '`')) { open = c; continue; }
            if (open != 0 && c == open) { open = 0; continue; }
            if (open != 0) continue;
            if (c == '(' || c == '{' || c == '[') depth++;
            else if (c == ')' || c == '}' || c == ']') depth--;
            else if (c == ',' && depth == 0) return args.substring(0, i).trim();
        }
        return args.trim();
    }

    private static String unquote(String s) {
        if (s == null) return "";
        s = s.trim();
        if (s.length() < 2) return s;
        char first = s.charAt(0);
        char last  = s.charAt(s.length() - 1);
        if ((first == '\'' || first == '"' || first == '`') && first == last) {
            return s.substring(1, s.length() - 1)
                    .replace("\\'", "'")
                    .replace("\\\"", "\"")
                    .replace("\\\\", "\\");
        }
        return s;
    }
}
