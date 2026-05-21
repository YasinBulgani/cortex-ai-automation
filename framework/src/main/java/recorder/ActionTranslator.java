package recorder;

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

    private final LocatorBuilder locatorBuilder = new LocatorBuilder();

    public TranslationResult translate(List<RecordedAction> actions) {
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
                                : "recordedPassword";
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
        if (!locators.containsKey(loc.key())) {
            Map<String, String> entry = new LinkedHashMap<>();
            entry.put("key", loc.key());
            entry.put("type", loc.type());
            entry.put("value", loc.value());
            locators.put(loc.key(), entry);
        }
        lines.add(stepFn.apply(loc));
    }

    private static String nullToEmpty(String s) { return s == null ? "" : s; }
}
