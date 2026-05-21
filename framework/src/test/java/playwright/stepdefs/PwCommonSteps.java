package playwright.stepdefs;

import config.ConfigManager;
import io.cucumber.java.en.Given;
import io.cucumber.java.en.Then;
import io.cucumber.java.en.When;
import playwright.methods.PwAssertionMethods;
import playwright.methods.PwCommonMethods;
import playwright.methods.PwInputMethods;

/**
 * Mirrors every Gherkin phrase from the Selenium {@code CommonSteps}.
 * A single feature file therefore runs with either runner.
 *
 * Runner selection:
 *   mvn test                       -> Selenium (TestRunner)
 *   mvn -Pplaywright test          -> Playwright (PlaywrightTestRunner)
 *   mvn -Pplaywright,parallel test -> Playwright + N threads
 */
public class PwCommonSteps {

    /* ------------------------- navigation ----------------------------- */

    @Given("I open {string} link")
    public void openLink(String urlKey) {
        String url = ConfigManager.getProperty(urlKey);
        if (url == null || url.isBlank()) url = urlKey;   // raw URL was passed
        PwCommonMethods.open(url);
    }

    @Given("I open the recorded url {string}")
    public void openRecordedUrl(String url) {
        PwCommonMethods.open(url);
    }

    /* ------------------------- click / scroll ------------------------- */

    @When("I click {string}")
    public void click(String key) {
        PwCommonMethods.click(key, PwConfigSteps.getLocators());
    }

    @When("I click {string} if present")
    public void clickIfPresent(String key) {
        PwCommonMethods.clickIfPresent(key, PwConfigSteps.getLocators());
    }

    @When("I double click {string}")
    public void doubleClick(String key) {
        PwCommonMethods.doubleClick(key, PwConfigSteps.getLocators());
    }

    @When("I hover over {string}")
    public void hover(String key) {
        PwCommonMethods.hover(key, PwConfigSteps.getLocators());
    }

    @When("I scroll to {string}")
    public void scrollTo(String key) {
        PwCommonMethods.scrollTo(key, PwConfigSteps.getLocators());
    }

    /* ------------------------- input ---------------------------------- */

    @When("I write {string} into {string}")
    public void write(String text, String key) {
        // resolve placeholders like ${ENV:CORTEX_USERNAME}
        PwInputMethods.write(key, resolveEnv(text), PwConfigSteps.getLocators());
    }

    /**
     * Expands "${ENV:VAR}" or "${ENV:VAR:default}" placeholders.
     * If no placeholder is present the text is returned as-is.
     */
    static String resolveEnv(String text) {
        if (text == null || !text.contains("${ENV:")) return text;
        java.util.regex.Matcher m = java.util.regex.Pattern
                .compile("\\$\\{ENV:([A-Z0-9_]+)(?::([^}]*))?}")
                .matcher(text);
        StringBuilder out = new StringBuilder();
        while (m.find()) {
            String env = System.getenv(m.group(1));
            if (env == null) env = m.group(2);
            if (env == null) env = "";
            m.appendReplacement(out, java.util.regex.Matcher.quoteReplacement(env));
        }
        m.appendTail(out);
        return out.toString();
    }

    @When("I type {string} into {string}")
    public void type(String text, String key) {
        PwInputMethods.type(key, resolveEnv(text), PwConfigSteps.getLocators());
    }

    @When("I clear {string}")
    public void clear(String key) {
        PwInputMethods.clear(key, PwConfigSteps.getLocators());
    }

    @When("I enter encrypted password alias {string} into {string}")
    public void enterEncrypted(String alias, String key) {
        PwInputMethods.enterEncryptedPassword(key, alias, PwConfigSteps.getLocators());
    }

    @When("I select {string} from {string}")
    public void select(String value, String key) {
        PwInputMethods.selectOption(key, value, PwConfigSteps.getLocators());
    }

    @When("I check {string}")
    public void check(String key) {
        PwInputMethods.check(key, PwConfigSteps.getLocators());
    }

    @When("I uncheck {string}")
    public void uncheck(String key) {
        PwInputMethods.uncheck(key, PwConfigSteps.getLocators());
    }

    // 'I upload file {string} into {string}' is defined in PwExtraSteps.

    /* ------------------------- waits / keys --------------------------- */

    @When("I wait for {int} seconds")
    public void waitSeconds(int seconds) {
        PwCommonMethods.waitSeconds(seconds);
    }

    @When("I wait for page to load")
    public void waitForLoad() {
        PwCommonMethods.waitForPageLoad();
    }

    @When("I press {string}")
    public void press(String key) {
        PwCommonMethods.pressKey(key);
    }

    @When("I switch to the newly opened tab")
    public void switchTab() {
        PwCommonMethods.switchToNewTab();
    }

    /* ------------------------- assertions ----------------------------- */

    @Then("I see {string}")
    public void see(String key) {
        PwAssertionMethods.see(key, PwConfigSteps.getLocators());
    }

    @Then("I do not see {string}")
    public void notSee(String key) {
        PwAssertionMethods.notSee(key, PwConfigSteps.getLocators());
    }

    @Then("I verify {string} contains {string}")
    public void containsText(String key, String text) {
        PwAssertionMethods.containsText(key, text, PwConfigSteps.getLocators());
    }

    @Then("I verify {string} value is {string}")
    public void valueIs(String key, String value) {
        PwAssertionMethods.valueIs(key, value, PwConfigSteps.getLocators());
    }

    @Then("I verify title contains {string}")
    public void titleContains(String s) {
        PwAssertionMethods.titleContains(s);
    }

    @Then("I verify url contains {string}")
    public void urlContains(String s) {
        PwAssertionMethods.urlContains(s);
    }

    @Then("I verify {string} is enabled")
    public void enabled(String key) {
        PwAssertionMethods.enabled(key, PwConfigSteps.getLocators());
    }

    @Then("I verify {string} is disabled")
    public void disabled(String key) {
        PwAssertionMethods.disabled(key, PwConfigSteps.getLocators());
    }
}
