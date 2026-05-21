package playwright.methods;

import com.microsoft.playwright.Locator;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Thread-safe variable storage + element value/text capture.
 * Playwright equivalent of the Selenium VariableMethods.
 */
public class PwVariableMethods {

    private static final ThreadLocal<Map<String, String>> STORE =
            ThreadLocal.withInitial(ConcurrentHashMap::new);

    public static void save(String name, String value) {
        STORE.get().put(name, value == null ? "" : value);
    }

    public static String get(String name) {
        String v = STORE.get().get(name);
        if (v == null) throw new IllegalStateException("Variable not set: " + name);
        return v;
    }

    public static void saveElementText(String key, String varName, Map<String, String> locators) {
        Locator l = PwCommonMethods.locator(key, locators);
        save(varName, l.innerText());
    }

    public static void saveElementValue(String key, String varName, Map<String, String> locators) {
        Locator l = PwCommonMethods.locator(key, locators);
        save(varName, l.inputValue());
    }

    public static void saveCurrentDate(String pattern, String varName) {
        save(varName, LocalDateTime.now().format(DateTimeFormatter.ofPattern(pattern)));
    }

    public static void saveRandomEmail(String domain, String varName) {
        String prefix = UUID.randomUUID().toString().replace("-", "").substring(0, 12);
        save(varName, prefix + "@" + domain);
    }

    public static void typeVariable(String varName, String key, Map<String, String> locators) {
        String v = get(varName);
        PwCommonMethods.locator(key, locators).fill(v);
    }

    public static void verifyEquals(String var1, String var2) {
        if (!get(var1).equals(get(var2))) {
            throw new AssertionError(var1 + " (" + get(var1) + ") != " + var2 + " (" + get(var2) + ")");
        }
    }

    public static void verifyContains(String var1, String var2) {
        if (!get(var1).contains(get(var2))) {
            throw new AssertionError(var1 + " does not contain " + var2);
        }
    }

    public static void verifyNotEquals(String var1, String var2) {
        if (get(var1).equals(get(var2))) {
            throw new AssertionError(var1 + " and " + var2 + " should differ");
        }
    }

    public static void verifyElementTextEquals(String key, String varName, Map<String, String> locators) {
        String text = PwCommonMethods.locator(key, locators).innerText();
        if (!text.equals(get(varName))) {
            throw new AssertionError("Element text '" + text + "' != " + varName + " '" + get(varName) + "'");
        }
    }

    public static void verifyElementTextContains(String key, String varName, Map<String, String> locators) {
        String text = PwCommonMethods.locator(key, locators).innerText();
        if (!text.contains(get(varName))) {
            throw new AssertionError("Element text '" + text + "' does not contain " + varName);
        }
    }

    public static void verifyElementValueContains(String key, String varName, Map<String, String> locators) {
        String val = PwCommonMethods.locator(key, locators).inputValue();
        if (!val.contains(get(varName))) {
            throw new AssertionError("Element value '" + val + "' does not contain " + varName);
        }
    }

    public static void clear() {
        STORE.remove();
    }
}
