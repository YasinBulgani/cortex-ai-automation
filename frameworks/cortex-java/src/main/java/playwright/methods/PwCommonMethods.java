package playwright.methods;

import com.microsoft.playwright.Locator;
import com.microsoft.playwright.Page;
import com.microsoft.playwright.options.LoadState;
import playwright.PlaywrightFactory;

import java.util.Map;

/**
 * Playwright equivalent of the Selenium CommonMethods library.
 * Step defs call into these methods; all operations are thread-safe
 * (ThreadLocal page).
 */
public class PwCommonMethods {

    public static Page page() { return PlaywrightFactory.page(); }

    public static Locator locator(String key, Map<String, String> locators) {
        String sel = locators.get(key);
        if (sel == null) throw new IllegalArgumentException("Locator missing: " + key);

        // Multi-locator (MULTI||sel1||sel2||...) -> Playwright .or() chain
        if (playwright.PwLocatorReader.isMulti(sel)) {
            var parts = playwright.PwLocatorReader.parseMulti(sel);
            Locator chain = page().locator(parts.get(0));
            for (int i = 1; i < parts.size(); i++) {
                chain = chain.or(page().locator(parts.get(i)));
            }
            return chain.first();
        }
        return page().locator(sel).first();
    }

    public static void open(String url) {
        try {
            // LOAD waits for the load event (DOMContentLoaded + all sub-resources).
            // Was previously COMMIT, but the JS driver rejected that on this
            // Playwright build, leaving the browser context in a broken state.
            page().navigate(url, new com.microsoft.playwright.Page.NavigateOptions()
                    .setWaitUntil(com.microsoft.playwright.options.WaitUntilState.LOAD));
        } catch (com.microsoft.playwright.PlaywrightException e) {
            // Tolerate aborted navigations caused by immediate redirects (SPA login flow).
            System.out.println("[PwCommonMethods] navigate() warning (continuing): "
                    + e.getMessage().split("\n")[0]);
        }
        try {
            page().waitForLoadState(LoadState.DOMCONTENTLOADED);
        } catch (com.microsoft.playwright.PlaywrightException ignored) {}
        // NOTE: NETWORKIDLE wait was attempted but it interacts badly with SPAs
        // that hold open connections (Sentry, websockets) — caused TargetClosedError.
        // Instead, rely on locator-level auto-waiting (fill/click block until the
        // element appears, up to playwright.timeout.ms). Bump that timeout via
        //   -Dplaywright.timeout.ms=60000
        // for SPAs that hydrate slowly.
    }

    public static void click(String key, Map<String, String> locators) {
        locator(key, locators).click();
    }

    public static void clickIfPresent(String key, Map<String, String> locators) {
        Locator l = locator(key, locators);
        if (l.count() > 0 && l.isVisible()) l.click();
    }

    public static void doubleClick(String key, Map<String, String> locators) {
        locator(key, locators).dblclick();
    }

    public static void hover(String key, Map<String, String> locators) {
        locator(key, locators).hover();
    }

    public static void scrollTo(String key, Map<String, String> locators) {
        locator(key, locators).scrollIntoViewIfNeeded();
    }

    public static void waitForPageLoad() {
        page().waitForLoadState(LoadState.NETWORKIDLE);
    }

    public static void waitSeconds(int seconds) {
        page().waitForTimeout(seconds * 1000L);
    }

    public static void pressKey(String key) {
        page().keyboard().press(translateKey(key));
    }

    public static void switchToNewTab() {
        var ctx = PlaywrightFactory.context();
        var pages = ctx.pages();
        // If the new tab has not opened yet, wait briefly
        if (pages.size() < 2) {
            page().waitForTimeout(500);
            pages = ctx.pages();
        }
        if (pages.isEmpty()) {
            throw new IllegalStateException("Context has no pages");
        }
        Page newest = pages.get(pages.size() - 1);
        newest.bringToFront();
        PlaywrightFactory.setActivePage(newest);
    }

    /** Switch back to the previous tab. */
    public static void switchToPreviousTab() {
        var pages = PlaywrightFactory.context().pages();
        if (pages.size() < 2) return;
        Page prev = pages.get(pages.size() - 2);
        prev.bringToFront();
        PlaywrightFactory.setActivePage(prev);
    }

    /** Close the current tab (the previous tab becomes active, if any). */
    public static void closeCurrentTab() {
        Page cur = page();
        var ctx = PlaywrightFactory.context();
        cur.close();
        var remaining = ctx.pages();
        if (!remaining.isEmpty()) {
            Page next = remaining.get(remaining.size() - 1);
            next.bringToFront();
            PlaywrightFactory.setActivePage(next);
        }
    }

    private static String translateKey(String userKey) {
        return switch (userKey.toUpperCase()) {
            case "ESC", "ESCAPE" -> "Escape";
            case "ENTER", "RETURN" -> "Enter";
            case "TAB" -> "Tab";
            case "SPACE" -> "Space";
            case "BACKSPACE" -> "Backspace";
            default -> userKey;
        };
    }

    /** Browser history back. */
    public static void goBack() {
        page().goBack();
    }
}
