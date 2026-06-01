package playwright.methods;

import com.microsoft.playwright.Locator;
import utils.DecryptUtil;

import java.util.Map;

/** Input / typing operations. */
public class PwInputMethods {

    public static void write(String key, String text, Map<String, String> locators) {
        // E20: self-heal wraps the fill; on TimeoutError the AI is consulted
        // for an alternative selector. Opt-in via -Dcortex.selfheal=true.
        if (playwright.SelfHeal.enabled()) {
            playwright.SelfHeal.attempt("fill", key, locators, null, l -> l.fill(text));
        } else {
            PwCommonMethods.locator(key, locators).fill(text);
        }
    }

    /** Send keys one by one (mimic real typing). */
    public static void type(String key, String text, Map<String, String> locators) {
        Locator l = PwCommonMethods.locator(key, locators);
        l.pressSequentially(text, new Locator.PressSequentiallyOptions().setDelay(40));
    }

    public static void clear(String key, Map<String, String> locators) {
        PwCommonMethods.locator(key, locators).fill("");
    }

    /** Decrypt the alias and type the resulting password. */
    public static void enterEncryptedPassword(String fieldKey, String alias,
                                              Map<String, String> locators) {
        try {
            String decrypted = DecryptUtil.decryptPasswordByAlias(alias);
            PwCommonMethods.locator(fieldKey, locators).fill(decrypted);
        } catch (Exception e) {
            throw new RuntimeException("Failed to decrypt password for alias: " + alias, e);
        }
    }

    public static void uploadFile(String key, String filePath,
                                  Map<String, String> locators) {
        PwCommonMethods.locator(key, locators).setInputFiles(java.nio.file.Paths.get(filePath));
    }

    public static void selectOption(String key, String value,
                                    Map<String, String> locators) {
        PwCommonMethods.locator(key, locators).selectOption(value);
    }

    public static void check(String key, Map<String, String> locators) {
        PwCommonMethods.locator(key, locators).check();
    }

    public static void uncheck(String key, Map<String, String> locators) {
        PwCommonMethods.locator(key, locators).uncheck();
    }
}
