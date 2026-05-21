package playwright.methods;

import com.microsoft.playwright.Locator;

import java.util.Map;

import static com.microsoft.playwright.assertions.PlaywrightAssertions.assertThat;

/** Assertion methods. */
public class PwAssertionMethods {

    public static void see(String key, Map<String, String> locators) {
        Locator l = PwCommonMethods.locator(key, locators);
        assertThat(l).isVisible();
    }

    public static void notSee(String key, Map<String, String> locators) {
        Locator l = PwCommonMethods.locator(key, locators);
        assertThat(l).isHidden();
    }

    public static void containsText(String key, String expected, Map<String, String> locators) {
        Locator l = PwCommonMethods.locator(key, locators);
        assertThat(l).containsText(expected);
    }

    public static void valueIs(String key, String expected, Map<String, String> locators) {
        Locator l = PwCommonMethods.locator(key, locators);
        assertThat(l).hasValue(expected);
    }

    public static void titleContains(String expected) {
        assertThat(PwCommonMethods.page()).hasTitle(java.util.regex.Pattern.compile(".*" + java.util.regex.Pattern.quote(expected) + ".*"));
    }

    public static void urlContains(String expected) {
        assertThat(PwCommonMethods.page()).hasURL(java.util.regex.Pattern.compile(".*" + java.util.regex.Pattern.quote(expected) + ".*"));
    }

    public static void enabled(String key, Map<String, String> locators) {
        assertThat(PwCommonMethods.locator(key, locators)).isEnabled();
    }

    public static void disabled(String key, Map<String, String> locators) {
        assertThat(PwCommonMethods.locator(key, locators)).isDisabled();
    }
}
