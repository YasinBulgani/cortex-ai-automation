package recorder;

import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Set;
import java.util.stream.Collectors;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Unit tests for {@link LocatorBuilder#computeAlternatives(RecordedAction.ElementInfo)}.
 *
 * These cover the new candidate-list API that the recorder dashboard's
 * locator picker depends on. The legacy {@link LocatorBuilder#build} path is
 * already exercised by the wider Cucumber suite; here we lock down the
 * ranking + dedupe behaviour of the alternatives list.
 */
class LocatorBuilderCandidatesTest {

    private final LocatorBuilder builder = new LocatorBuilder();

    @Test
    void null_element_yields_a_single_fallback_candidate() {
        List<LocatorBuilder.Candidate> out = builder.computeAlternatives(null);
        assertEquals(1, out.size());
        assertEquals("fallback", out.get(0).strategy());
        assertTrue(out.get(0).score() < 30, "Fallback should have a low score");
    }

    @Test
    void data_testid_ranks_first_with_high_score() {
        RecordedAction.ElementInfo el = new RecordedAction.ElementInfo();
        el.tag = "button";
        el.dataTestId = "submit-btn";
        el.id = "auto-generated-1";
        el.text = "Submit";

        List<LocatorBuilder.Candidate> out = builder.computeAlternatives(el);

        assertFalse(out.isEmpty());
        assertEquals("data-testid", out.get(0).strategy(),
                "data-testid must rank first when present");
        assertTrue(out.get(0).score() >= 90,
                "data-testid candidate should score >= 90 (got " + out.get(0).score() + ")");
        assertEquals("[data-testid='submit-btn']", out.get(0).value());
    }

    @Test
    void stable_id_outranks_text_but_below_data_attributes() {
        RecordedAction.ElementInfo el = new RecordedAction.ElementInfo();
        el.tag = "button";
        el.id = "loginBtn";   // stable
        el.text = "Login";

        List<LocatorBuilder.Candidate> out = builder.computeAlternatives(el);
        // id and text both produce a candidate; id should rank higher
        int idIdx = indexOf(out, "id");
        int textIdx = indexOf(out, "text");
        assertTrue(idIdx >= 0 && textIdx >= 0);
        assertTrue(idIdx < textIdx, "stable id should rank above text");
        assertTrue(out.get(idIdx).score() > out.get(textIdx).score());
    }

    @Test
    void auto_generated_id_gets_low_score_so_text_can_overtake() {
        RecordedAction.ElementInfo el = new RecordedAction.ElementInfo();
        el.tag = "button";
        el.id = "mui-1234";       // recognised as auto-generated
        el.text = "Sign in";

        List<LocatorBuilder.Candidate> out = builder.computeAlternatives(el);

        int idIdx = indexOf(out, "id");
        int textIdx = indexOf(out, "text");
        assertTrue(idIdx >= 0 && textIdx >= 0);
        assertTrue(out.get(idIdx).score() < 50,
                "Auto-generated MUI id should be flagged as fragile");
        // text candidate (button visible label) should outrank fragile id
        assertTrue(out.get(textIdx).score() > out.get(idIdx).score());
    }

    @Test
    void duplicate_selectors_are_deduped() {
        RecordedAction.ElementInfo el = new RecordedAction.ElementInfo();
        el.tag = "input";
        el.name = "email";
        el.dataTestId = "email";  // produces a different (data-testid) selector — kept
        // (no collision since type+value differ)

        List<LocatorBuilder.Candidate> out = builder.computeAlternatives(el);

        // Same (type, value) pair must appear at most once
        long uniqueFingerprints = out.stream()
                .map(c -> c.type() + ":" + c.value())
                .distinct().count();
        assertEquals(out.size(), uniqueFingerprints,
                "Each (type, value) must be unique");
    }

    @Test
    void deep_css_path_is_penalised() {
        RecordedAction.ElementInfo el = new RecordedAction.ElementInfo();
        el.tag = "button";
        // Deep, brittle CSS path (lots of `>` and `[n]`)
        el.cssPath = "html > body > div#root > div.app > main > section > "
                + "form > div:nth-child(3) > div:nth-child(2) > button:nth-of-type(1)";

        List<LocatorBuilder.Candidate> out = builder.computeAlternatives(el);
        int idx = indexOf(out, "css-path");
        assertTrue(idx >= 0);
        assertTrue(out.get(idx).score() < 50,
                "Deep CSS path with many >/[n] should be penalised (was "
                        + out.get(idx).score() + ")");
    }

    @Test
    void candidates_are_sorted_by_score_descending() {
        RecordedAction.ElementInfo el = new RecordedAction.ElementInfo();
        el.tag = "button";
        el.dataTestId = "ok-btn";
        el.id = "okBtn";
        el.name = "ok";
        el.ariaLabel = "OK";
        el.text = "OK";
        el.placeholder = null;
        el.cssPath = "button.ok";
        el.xpath = "//button[1]";

        List<LocatorBuilder.Candidate> out = builder.computeAlternatives(el);
        assertTrue(out.size() >= 4);
        for (int i = 1; i < out.size(); i++) {
            assertTrue(out.get(i - 1).score() >= out.get(i).score(),
                    "Candidates must be sorted by score desc — violation at index " + i
                            + " (" + out.get(i - 1).strategy() + " score=" + out.get(i - 1).score()
                            + " < " + out.get(i).strategy() + " score=" + out.get(i).score() + ")");
        }
    }

    @Test
    void all_known_strategies_can_be_produced() {
        // An element with every signal populated should produce every strategy
        // (except role+name vs text where one selector dominates).
        RecordedAction.ElementInfo el = new RecordedAction.ElementInfo();
        el.tag = "button";
        el.dataTestId = "btn";
        el.dataCy = "cy-btn";
        el.dataQa = "qa-btn";
        el.id = "loginBtn";
        el.name = "login";
        el.ariaLabel = "Sign in";
        el.role = "button";
        el.text = "Sign in";
        el.placeholder = "Search...";
        el.cssPath = "button.primary";
        el.xpath = "//button[@id='loginBtn']";

        List<LocatorBuilder.Candidate> out = builder.computeAlternatives(el);
        Set<String> strategies = out.stream()
                .map(LocatorBuilder.Candidate::strategy)
                .collect(Collectors.toSet());

        // The minimum set we expect: data-testid + id + name + aria-label + text + css-path + xpath
        assertTrue(strategies.contains("data-testid"));
        assertTrue(strategies.contains("id"));
        assertTrue(strategies.contains("name"));
        assertTrue(strategies.contains("aria-label"));
        assertTrue(strategies.contains("text"));
        assertTrue(strategies.contains("css-path"));
        assertTrue(strategies.contains("xpath"));
    }

    @Test
    void invalid_selectors_still_produce_at_least_one_candidate() {
        RecordedAction.ElementInfo el = new RecordedAction.ElementInfo();
        // Almost everything blank; only tag present
        el.tag = "div";
        List<LocatorBuilder.Candidate> out = builder.computeAlternatives(el);
        assertFalse(out.isEmpty(), "Even with minimal data, computeAlternatives must produce a fallback");
    }

    // ─────────── helpers ───────────

    private int indexOf(List<LocatorBuilder.Candidate> list, String strategy) {
        for (int i = 0; i < list.size(); i++) {
            if (list.get(i).strategy().equals(strategy)) return i;
        }
        return -1;
    }
}
