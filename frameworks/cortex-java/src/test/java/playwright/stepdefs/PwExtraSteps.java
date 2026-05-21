package playwright.stepdefs;

import com.microsoft.playwright.Keyboard;
import com.microsoft.playwright.Locator;
import com.microsoft.playwright.options.MouseButton;
import crypto.EncryptionManager;
import io.cucumber.java.en.Given;
import io.cucumber.java.en.Then;
import io.cucumber.java.en.When;
import playwright.PlaywrightFactory;
import playwright.methods.PwAccessibilityMethods;
import playwright.methods.PwAssertionMethods;
import playwright.methods.PwCommonMethods;
import playwright.methods.PwDbMethods;
import playwright.methods.PwInputMethods;
import playwright.methods.PwVariableMethods;

import java.util.Map;

/**
 * Playwright counterparts for every step phrase that exists on the Selenium side.
 * Complements PwCommonSteps (P1-P20 + extras).
 */
public class PwExtraSteps {

    private Map<String, String> loc() { return PwConfigSteps.getLocators(); }

    /* ============================================================== */
    /*  Click / interaction (P1-P5, P14, P15, P19)                   */
    /* ============================================================== */

    @When("I click {string} if it exists")
    public void clickIfExists(String key) {
        PwCommonMethods.clickIfPresent(key, loc());
    }

    @When("I click radio {string} element")
    public void clickRadio(String key) {
        PwCommonMethods.locator(key, loc()).check();
    }

    @When("I click {string} checkbox element")
    public void clickCheckbox(String key) {
        PwInputMethods.check(key, loc());
    }

    @When("I click {string} uncheck checkbox element")
    public void clickUncheckCheckbox(String key) {
        PwInputMethods.uncheck(key, loc());
    }

    @When("I right click on element with key {string}")
    public void rightClick(String key) {
        PwCommonMethods.locator(key, loc())
                .click(new Locator.ClickOptions().setButton(MouseButton.RIGHT));
    }

    @When("I mouseover on {string} element")
    public void mouseOver(String key) {
        PwCommonMethods.hover(key, loc());
    }

    @When("I drag {string} element to {string} target element")
    public void drag(String src, String tgt) {
        PwCommonMethods.locator(src, loc()).dragTo(PwCommonMethods.locator(tgt, loc()));
    }

    @When("I hold mouse button on {string} element for {int} seconds")
    public void holdMouse(String key, int seconds) {
        Locator l = PwCommonMethods.locator(key, loc());
        l.hover();
        PlaywrightFactory.page().mouse().down();
        PlaywrightFactory.page().waitForTimeout(seconds * 1000L);
        PlaywrightFactory.page().mouse().up();
    }

    @When("I click outside the current active element")
    public void clickOutside() {
        PlaywrightFactory.page().mouse().click(10, 10);
    }

    /* ============================================================== */
    /*  Navigation (P17, P18)                                          */
    /* ============================================================== */

    @When("I go back and see previous page")
    public void goBack() {
        PwCommonMethods.goBack();
    }

    @When("I go forward and see next page")
    public void goForward() {
        PlaywrightFactory.page().goForward();
    }

    @When("I reload current page")
    public void reload() {
        PlaywrightFactory.page().reload();
    }

    @When("Close the current tab")
    public void closeCurrentTab() {
        PwCommonMethods.closeCurrentTab();
    }

    @When("I switch back to the previous tab")
    public void switchPrev() {
        PwCommonMethods.switchToPreviousTab();
    }

    /* ============================================================== */
    /*  Keyboard (P6)                                                  */
    /* ============================================================== */

    @When("I press {string} key")
    public void pressKey(String key) {
        PwCommonMethods.pressKey(key);
    }

    @When("I press {string} and {string} keys simultaneously")
    public void pressCombo(String key1, String key2) {
        Keyboard kb = PlaywrightFactory.page().keyboard();
        kb.down(translate(key1));
        kb.press(translate(key2));
        kb.up(translate(key1));
    }

    @When("I force press ESC key")
    public void forceEsc() {
        PlaywrightFactory.page().keyboard().press("Escape");
    }

    private static String translate(String userKey) {
        return switch (userKey.toUpperCase()) {
            case "ESC", "ESCAPE" -> "Escape";
            case "ENTER", "RETURN" -> "Enter";
            case "TAB" -> "Tab";
            case "CTRL", "CONTROL" -> "Control";
            case "SHIFT" -> "Shift";
            case "ALT" -> "Alt";
            case "META", "CMD" -> "Meta";
            default -> userKey;
        };
    }

    /* ============================================================== */
    /*  Force input (P12 partial)                                      */
    /* ============================================================== */

    @When("I force clear {string}")
    public void forceClear(String key) {
        PlaywrightFactory.page().evaluate(
            "el => { if ('value' in el) el.value = ''; }",
            PwCommonMethods.locator(key, loc()).elementHandle()
        );
    }

    @When("I force type {string} into {string}")
    public void forceType(String text, String key) {
        Locator l = PwCommonMethods.locator(key, loc());
        l.fill("");
        l.pressSequentially(text, new Locator.PressSequentiallyOptions().setDelay(30));
    }

    @When("I force click {string}")
    public void forceClick(String key) {
        PwCommonMethods.locator(key, loc())
                .click(new Locator.ClickOptions().setForce(true));
    }

    /* ============================================================== */
    /*  Shadow DOM (P4) - Playwright shadow penetration yerleskik     */
    /* ============================================================== */

    @When("I click shadow element with key {string}")
    public void clickShadow(String key) {
        // Playwright locators automatically pierce shadow DOM
        PwCommonMethods.click(key, loc());
    }

    @When("I force click shadow element with key {string}")
    public void forceClickShadow(String key) {
        PwCommonMethods.locator(key, loc())
                .click(new Locator.ClickOptions().setForce(true));
    }

    /* ============================================================== */
    /*  File operations (P12)                                          */
    /* ============================================================== */

    @When("I upload file {string} into {string}")
    public void uploadFile(String path, String key) {
        PwInputMethods.uploadFile(key, path, loc());
    }

    @When("I click {string} to download file {string} with extension {string} and max size {int} MB")
    public void clickToDownload(String key, String filename, String extension, int maxMb) {
        // Playwright download otomatik yakalama
        var dl = PlaywrightFactory.page().waitForDownload(() ->
                PwCommonMethods.locator(key, loc()).click()
        );
        java.nio.file.Path target = java.nio.file.Paths.get(
                "src/main/resources/files/download", filename + "." + extension);
        try { java.nio.file.Files.createDirectories(target.getParent()); } catch (Exception ignored) {}
        dl.saveAs(target);
        long sizeMb = target.toFile().length() / (1024 * 1024);
        if (sizeMb > maxMb) {
            throw new AssertionError("Indirilen dosya boyutu " + sizeMb + " MB > limit " + maxMb);
        }
    }

    @When("I delete downloaded file {string}")
    public void deleteDownloaded(String filename) {
        java.io.File f = new java.io.File("src/main/resources/files/download/" + filename);
        if (f.exists() && !f.delete()) {
            throw new RuntimeException("Dosya silinemedi: " + filename);
        }
    }

    /* ============================================================== */
    /*  Variables (P7, P11)                                            */
    /* ============================================================== */

    @Given("I save the text {string} as the variable {string}")
    public void saveText(String value, String varName) {
        PwVariableMethods.save(varName, value);
    }

    @Given("I save the element text {string} as the variable {string}")
    public void saveElementText(String key, String varName) {
        PwVariableMethods.saveElementText(key, varName, loc());
    }

    @Given("I save the element value {string} as the variable {string}")
    public void saveElementValue(String key, String varName) {
        PwVariableMethods.saveElementValue(key, varName, loc());
    }

    @Given("I save the current date {string} as the variable {string}")
    public void saveDate(String pattern, String varName) {
        PwVariableMethods.saveCurrentDate(pattern, varName);
    }

    @Given("I generate a random unique email with domain {string} as the variable {string}")
    public void saveRandomEmail(String domain, String varName) {
        PwVariableMethods.saveRandomEmail(domain, varName);
    }

    @When("I type variable {string} into element {string}")
    public void typeVar(String varName, String key) {
        PwVariableMethods.typeVariable(varName, key, loc());
    }

    @Then("I verify the variable {string} equals to other variable {string}")
    public void varEquals(String a, String b) { PwVariableMethods.verifyEquals(a, b); }

    @Then("I verify the variable {string} contains other variable {string}")
    public void varContains(String a, String b) { PwVariableMethods.verifyContains(a, b); }

    @Then("I verify the variable {string} is not equal to other variable {string}")
    public void varNotEquals(String a, String b) { PwVariableMethods.verifyNotEquals(a, b); }

    @Then("I verify element text {string} equals to variable {string}")
    public void elTextEqualsVar(String key, String varName) {
        PwVariableMethods.verifyElementTextEquals(key, varName, loc());
    }

    @Then("I verify element text {string} contains variable {string}")
    public void elTextContainsVar(String key, String varName) {
        PwVariableMethods.verifyElementTextContains(key, varName, loc());
    }

    @Then("I verify element value {string} contains variable {string}")
    public void elValueContainsVar(String key, String varName) {
        PwVariableMethods.verifyElementValueContains(key, varName, loc());
    }

    /* ============================================================== */
    /*  Database (P8, P10, P16) - Selenium tarafiyla ayni utility    */
    /* ============================================================== */

    private final PwDbMethods dbMethods = new PwDbMethods();

    @When("I connect to the database {string}")
    public void dbConnect(String dbKey) {
        dbMethods.connectToDatabaseByIdentifier(dbKey);
    }

    @When("I close the database connection")
    public void dbClose() {
        dbMethods.closeConnection();
    }

    @When("I execute the SQL from json with key {string} and parameters {string}")
    public void dbExecuteFromJson(String queryKey, String params) {
        dbMethods.executeSqlFromJson(queryKey, params);
    }

    /* ============================================================== */
    /*  Crypto (P9)                                                    */
    /* ============================================================== */

    @When("I encrypt password {string} and save as alias {string} with overwrite")
    public void encryptPassword(String plain, String alias) {
        EncryptionManager.encryptAndSaveToPasswordFile(plain, alias);
    }

    /* ============================================================== */
    /*  Negative assertions                                             */
    /* ============================================================== */

    @Then("I do not see {string} element")
    public void doNotSeeElement(String key) {
        PwAssertionMethods.notSee(key, loc());
    }

    /* ============================================================== */
    /*  Accessibility (axe-core)                                        */
    /* ============================================================== */

    @Then("I run accessibility audit and expect no critical violations")
    public void a11yAuditNoCritical() {
        PwAccessibilityMethods.assertNoViolations("critical");
    }

    @Then("I run accessibility audit and expect WCAG 2.1 AA compliance")
    public void a11yAuditWcagAa() {
        PwAccessibilityMethods.assertWcagAaCompliant();
    }

    @Then("I run accessibility audit with minimum impact {string}")
    public void a11yAudit(String impact) {
        PwAccessibilityMethods.assertNoViolations(impact);
    }
}
