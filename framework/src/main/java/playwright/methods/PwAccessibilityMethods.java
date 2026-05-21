package playwright.methods;

import com.deque.html.axecore.playwright.AxeBuilder;
import com.deque.html.axecore.results.AxeResults;
import com.deque.html.axecore.results.Rule;

import java.util.List;

/**
 * Accessibility audit using axe-core via Playwright.
 *
 * Standard rule tags (WCAG levels):
 *   - wcag2a, wcag2aa, wcag2aaa
 *   - wcag21a, wcag21aa, wcag22aa
 *   - best-practice
 *
 * Default audit runs against the WCAG 2.1 AA rule set plus best-practice.
 */
public class PwAccessibilityMethods {

    /** Run axe on the current page and return all violations. */
    public static List<Rule> runAxe() {
        AxeResults results = new AxeBuilder(PwCommonMethods.page())
                .withTags(List.of("wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "best-practice"))
                .analyze();
        return results.getViolations();
    }

    /** Assert no violations with the given minimum impact level. */
    public static void assertNoViolations(String minImpact) {
        List<Rule> violations = runAxe();
        List<Rule> blocking = violations.stream()
                .filter(r -> isAtLeast(r.getImpact(), minImpact))
                .toList();

        if (blocking.isEmpty()) {
            System.out.println("[a11y] No " + minImpact + "+ violations");
            return;
        }

        StringBuilder sb = new StringBuilder();
        sb.append("[a11y] ").append(blocking.size())
          .append(" violation(s) at impact >= ").append(minImpact).append(":\n");
        for (Rule v : blocking) {
            sb.append(" * ").append(v.getId())
              .append(" [").append(v.getImpact()).append("] ")
              .append(v.getHelp())
              .append(" (").append(v.getNodes().size()).append(" nodes)")
              .append("\n   → ").append(v.getHelpUrl()).append("\n");
        }
        throw new AssertionError(sb.toString());
    }

    /** Convenience: WCAG 2.1 AA blocking issues only (serious + critical). */
    public static void assertWcagAaCompliant() {
        assertNoViolations("serious");
    }

    private static boolean isAtLeast(String impact, String threshold) {
        int rank = rank(impact);
        return rank >= rank(threshold);
    }

    private static int rank(String impact) {
        if (impact == null) return 0;
        return switch (impact.toLowerCase()) {
            case "minor"    -> 1;
            case "moderate" -> 2;
            case "serious"  -> 3;
            case "critical" -> 4;
            default         -> 0;
        };
    }
}
