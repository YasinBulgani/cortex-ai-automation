package recorder;

import java.text.Normalizer;
import java.util.HashMap;
import java.util.Map;

/**
 * Given a RecordedAction.ElementInfo, builds:
 *   - a locator key (camelCase)
 *   - a locator type (id|css|xpath|name)
 *   - a locator value
 *
 * Priority order (first match wins):
 *   1. data-testid / data-cy / data-qa
 *   2. id (if stable; auto-generated patterns are rejected)
 *   3. name attribute
 *   4. aria-label
 *   5. visible text (xpath for button/link)
 *   6. placeholder (input)
 *   7. CSS path produced by recorder.js
 *   8. XPath fallback
 */
public final class LocatorBuilder {

    public record Locator(String key, String type, String value) {}

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

    /* ------------------------------------------------------------------ */

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
