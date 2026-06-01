package recorder;

import java.text.Normalizer;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * Given a RecordedAction.ElementInfo, builds:
 *   - a locator key (camelCase)
 *   - a locator type (id|css|xpath|name)
 *   - a locator value
 *
 * Priority order (first match wins for {@link #build}):
 *   1. data-testid / data-cy / data-qa
 *   2. id (if stable; auto-generated patterns are rejected)
 *   3. name attribute
 *   4. aria-label
 *   5. visible text (xpath for button/link)
 *   6. placeholder (input)
 *   7. CSS path produced by recorder.js
 *   8. XPath fallback
 *
 * {@link #computeAlternatives(RecordedAction.ElementInfo)} returns every
 * matching strategy with a stability score (0-100) so the dashboard can show
 * candidate locators and let the QA engineer pick a different one if the
 * default isn't right.
 */
public final class LocatorBuilder {

    public record Locator(String key, String type, String value) {}

    /**
     * A single locator candidate with metadata for the dashboard picker.
     *
     * @param strategy short identifier (data-testid, id, name, aria-label, text, placeholder, css-path, xpath, fallback)
     * @param type     locator type used by the step library (id|css|xpath|name)
     * @param value    locator value
     * @param key      camelCase key suggestion (used in feature steps)
     * @param score    stability estimate 0-100 (higher = more durable)
     * @param reason   short human-readable explanation
     */
    public record Candidate(String strategy, String type, String value,
                            String key, int score, String reason) {}

    private final Map<String, Integer> keyDedup = new HashMap<>();

    public Locator build(RecordedAction.ElementInfo el) {
        if (el == null) {
            return register(new Locator("element", "css", "body"));
        }

        // 1) data-test* attributes
        if (notBlank(el.dataTestId)) {
            return register(new Locator(toCamelKey(el.dataTestId), "css",
                    "[data-testid='" + el.dataTestId + "']"));
        }
        if (notBlank(el.dataCy)) {
            return register(new Locator(toCamelKey(el.dataCy), "css",
                    "[data-cy='" + el.dataCy + "']"));
        }
        if (notBlank(el.dataQa)) {
            return register(new Locator(toCamelKey(el.dataQa), "css",
                    "[data-qa='" + el.dataQa + "']"));
        }

        // 2) stable id
        if (notBlank(el.id) && isStableId(el.id)) {
            return register(new Locator(toCamelKey(el.id), "id", el.id));
        }

        // 3) name
        if (notBlank(el.name)) {
            return register(new Locator(toCamelKey(el.name), "name", el.name));
        }

        // 4) aria-label
        if (notBlank(el.ariaLabel)) {
            String key = toCamelKey(el.ariaLabel) + suffixByTag(el);
            return register(new Locator(key, "css",
                    el.tag + "[aria-label='" + escape(el.ariaLabel) + "']"));
        }

        // 5) visible text (button/link as xpath)
        if (("button".equalsIgnoreCase(el.tag) || "a".equalsIgnoreCase(el.tag))
                && notBlank(el.text) && el.text.length() < 80) {
            String key = toCamelKey(el.text) + suffixByTag(el);
            String xp  = "//" + el.tag.toLowerCase() + "[normalize-space()='" + escape(el.text.trim()) + "']";
            return register(new Locator(key, "xpath", xp));
        }

        // 6) placeholder (input)
        if (notBlank(el.placeholder)) {
            String key = toCamelKey(el.placeholder) + suffixByTag(el);
            return register(new Locator(key, "css",
                    "[placeholder='" + escape(el.placeholder) + "']"));
        }

        // 7) CSS path from recorder.js
        if (notBlank(el.cssPath)) {
            String key = "element" + suffixByTag(el);
            return register(new Locator(key, "css", el.cssPath));
        }

        // 8) XPath fallback
        if (notBlank(el.xpath)) {
            return register(new Locator("element" + suffixByTag(el), "xpath", el.xpath));
        }

        // last resort
        return register(new Locator("element" + suffixByTag(el), "css", el.tag != null ? el.tag : "body"));
    }

    /* ================================================================== */
    /*  Candidates                                                        */
    /* ================================================================== */

    /**
     * Build a ranked list of locator alternatives for the dashboard picker.
     *
     * The dashboard shows the top {@code N} alternatives next to each recorded
     * action so the user can swap to a more stable selector when the recorder's
     * default pick is fragile (e.g. CSS-path on a deeply nested element).
     *
     * The first item in the list always matches {@link #build(RecordedAction.ElementInfo)} —
     * picking the default is a no-op.
     */
    public List<Candidate> computeAlternatives(RecordedAction.ElementInfo el) {
        List<Candidate> out = new ArrayList<>();
        if (el == null) {
            out.add(new Candidate("fallback", "css", "body", "element", 10,
                    "Element bilgisi yok"));
            return out;
        }
        // Dedup by (type+value) — same selector under multiple names is noise
        Set<String> seen = new LinkedHashSet<>();

        // 1) data-test*
        if (notBlank(el.dataTestId)) {
            addUnique(out, seen, new Candidate("data-testid", "css",
                    "[data-testid='" + el.dataTestId + "']",
                    toCamelKey(el.dataTestId), 95,
                    "data-testid en sağlam strateji"));
        }
        if (notBlank(el.dataCy)) {
            addUnique(out, seen, new Candidate("data-cy", "css",
                    "[data-cy='" + el.dataCy + "']",
                    toCamelKey(el.dataCy), 94,
                    "data-cy (Cypress konvansiyonu)"));
        }
        if (notBlank(el.dataQa)) {
            addUnique(out, seen, new Candidate("data-qa", "css",
                    "[data-qa='" + el.dataQa + "']",
                    toCamelKey(el.dataQa), 94,
                    "data-qa atribütü"));
        }

        // 2) id
        if (notBlank(el.id)) {
            boolean stable = isStableId(el.id);
            int score = stable ? 85 : 35;
            String reason = stable ? "id sabit görünüyor" : "id otomatik üretilmiş olabilir — kırılgan";
            addUnique(out, seen, new Candidate("id", "id", el.id, toCamelKey(el.id),
                    score, reason));
        }

        // 3) name
        if (notBlank(el.name)) {
            addUnique(out, seen, new Candidate("name", "name", el.name,
                    toCamelKey(el.name), 75,
                    "name attribute — formlar için güvenli"));
        }

        // 4) aria-label
        if (notBlank(el.ariaLabel)) {
            String tag = el.tag != null ? el.tag : "*";
            addUnique(out, seen, new Candidate("aria-label", "css",
                    tag + "[aria-label='" + escape(el.ariaLabel) + "']",
                    toCamelKey(el.ariaLabel) + suffixByTag(el), 78,
                    "aria-label — erişilebilirlik metadata"));
        }

        // 5) role + accessible name (visible text)
        if (notBlank(el.role) && notBlank(el.text) && el.text.length() < 80) {
            addUnique(out, seen, new Candidate("role+name", "css",
                    "[role='" + el.role + "'][aria-label='" + escape(el.text.trim()) + "']",
                    toCamelKey(el.text) + suffixByTag(el), 70,
                    "role + accessible name — semantik"));
        }

        // 6) visible text (xpath) — typical for buttons/links
        if (notBlank(el.text) && el.text.length() < 80 && el.tag != null) {
            String tag = el.tag.toLowerCase();
            String xp = "//" + tag + "[normalize-space()='" + escape(el.text.trim()) + "']";
            int score = ("button".equals(tag) || "a".equals(tag)) ? 72 : 55;
            String reason = ("button".equals(tag) || "a".equals(tag))
                    ? "buton/link metni nadiren değişir"
                    : "görünür metin — i18n'de değişebilir";
            addUnique(out, seen, new Candidate("text", "xpath", xp,
                    toCamelKey(el.text) + suffixByTag(el), score, reason));
        }

        // 7) placeholder (input)
        if (notBlank(el.placeholder)) {
            addUnique(out, seen, new Candidate("placeholder", "css",
                    "[placeholder='" + escape(el.placeholder) + "']",
                    toCamelKey(el.placeholder) + suffixByTag(el), 58,
                    "placeholder — i18n'de değişebilir"));
        }

        // 8) CSS path from recorder.js
        if (notBlank(el.cssPath)) {
            int score = scoreSelector(el.cssPath);
            addUnique(out, seen, new Candidate("css-path", "css", el.cssPath,
                    "element" + suffixByTag(el), score,
                    score >= 50 ? "CSS path — DOM yeniden düzenlenirse kırılır"
                                : "CSS path uzun — yapısal değişikliklere çok hassas"));
        }

        // 9) XPath fallback
        if (notBlank(el.xpath)) {
            int score = scoreSelector(el.xpath);
            addUnique(out, seen, new Candidate("xpath", "xpath", el.xpath,
                    "element" + suffixByTag(el), Math.max(20, score - 10),
                    "XPath fallback — son çare"));
        }

        if (out.isEmpty()) {
            // Truly nothing usable — last-resort tag selector
            String tag = el.tag != null ? el.tag : "body";
            out.add(new Candidate("fallback", "css", tag, "element", 5,
                    "Kullanılabilir bir locator stratejisi bulunamadı"));
        }

        // Sort: highest score first
        out.sort((a, b) -> Integer.compare(b.score, a.score));
        return out;
    }

    private static void addUnique(List<Candidate> out, Set<String> seen, Candidate c) {
        String fp = c.type + ":" + c.value;
        if (seen.add(fp)) out.add(c);
    }

    /**
     * Estimate the durability of a long structural selector. Each `>` or `[n]`
     * is a fragility marker.
     */
    private static int scoreSelector(String s) {
        if (s == null) return 20;
        int penalty = 0;
        for (int i = 0; i < s.length(); i++) {
            char c = s.charAt(i);
            if (c == '>') penalty += 4;        // each direct-child step
            if (c == '[') penalty += 3;        // each [n] / [attr] step
        }
        if (s.length() > 200) penalty += 15;
        return Math.max(15, 65 - penalty);
    }

    /* ================================================================== */
    /*  Helpers                                                           */
    /* ================================================================== */

    /** Reject auto-generated ids that change between renders. */
    private boolean isStableId(String id) {
        return !id.matches(":r[a-z0-9]+:")            // React 18 useId
            && !id.matches("mui-\\d+")                 // MUI
            && !id.matches("ant-\\d+")                 // Ant Design
            && !id.matches("[a-z]{2,4}-\\d{3,}-\\d+")  // Angular flavor
            && !id.matches("[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-.*") // UUID
            && id.length() < 64;
    }

    private String suffixByTag(RecordedAction.ElementInfo el) {
        if (el == null || el.tag == null) return "";
        return switch (el.tag.toLowerCase()) {
            case "input", "textarea" -> "Input";
            case "button"            -> "Button";
            case "a"                 -> "Link";
            case "select"            -> "Select";
            case "label"             -> "Label";
            case "form"              -> "Form";
            default                  -> "";
        };
    }

    /**
     * "Giris Yap" -> "girisYap"
     * "kullanici_adi" -> "kullaniciAdi"
     * Turkish characters are stripped to ASCII for safe identifiers.
     */
    public static String toCamelKey(String raw) {
        if (raw == null || raw.isBlank()) return "element";
        String s = Normalizer.normalize(raw, Normalizer.Form.NFD)
                             .replaceAll("\\p{InCombiningDiacriticalMarks}+", "");
        s = s.toLowerCase()
             .replace("ı", "i").replace("ş", "s").replace("ğ", "g")
             .replace("ü", "u").replace("ö", "o").replace("ç", "c")
             .replaceAll("[^a-z0-9 _-]", "")
             .trim();
        String[] parts = s.split("[ _\\-]+");
        StringBuilder out = new StringBuilder();
        for (int i = 0; i < parts.length; i++) {
            if (parts[i].isEmpty()) continue;
            if (i == 0) out.append(parts[i]);
            else out.append(Character.toUpperCase(parts[i].charAt(0)))
                    .append(parts[i].substring(1));
        }
        String result = out.toString();
        if (result.isBlank()) result = "element";
        // Java identifiers cannot start with a digit
        if (Character.isDigit(result.charAt(0))) result = "el" + result;
        // Trim very long names
        if (result.length() > 40) result = result.substring(0, 40);
        return result;
    }

    private Locator register(Locator base) {
        String key = base.key;
        int n = keyDedup.merge(key, 1, Integer::sum);
        if (n > 1) {
            return new Locator(key + "_" + n, base.type, base.value);
        }
        return base;
    }

    private static boolean notBlank(String s) {
        return s != null && !s.isBlank();
    }

    private static String escape(String s) {
        return s.replace("'", "\\'");
    }
}
