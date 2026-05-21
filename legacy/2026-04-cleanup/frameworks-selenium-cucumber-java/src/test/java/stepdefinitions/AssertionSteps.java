package stepdefinitions;

import io.cucumber.java.en.Then;
import methods.AssertionMethods;
import utilities.DataReader;
import utilities.DateFormatResolver;
import utilities.LocatorManager;
import utilities.ScenarioContext;

/**
 * AssertionSteps:
 * Feature dosyasındaki doğrulama adımlarını AssertionMethods ile bağlar.
 */
public class AssertionSteps {

    private final AssertionMethods assertionMethods = new AssertionMethods();

    /**
     * Feature kullanımı:
     * Then I verify element "UserMenu" text is "Girit"
     * Then I verify element "UserMenu" text is "@expectedName" (JSON'dan okur)
     * Then I verify element "..." text is "+-abc" (senaryoda +-abc ile saklanan değerle kontrol)
     * Then I verify element "..." text is "dateformatnow dd/MM/yyyy" (bugünün tarihi, aynı formatta)
     */
    @Then("I verify element {string} text is {string}")
    public void verifyElementText(String elementKey, String expectedText) {
        String actualExpectedText = resolveExpectedText(expectedText);
        assertionMethods.verifyElementTextEquals(elementKey, actualExpectedText, LocatorManager.getLocators());
    }

    /**
     * "+-key" → ScenarioContext'ten key ile saklanan değer.
     * "@key" → DataReader.
     * "dateformatnow ..." / "dateformatnow:name" → bugünün tarihi, verilen formatta (input ile aynı mantık).
     * Aksi halde literal.
     */
    private String resolveExpectedText(String expectedText) {
        if (expectedText != null && expectedText.startsWith("+-")) {
            String key = expectedText.substring(2).trim();
            return ScenarioContext.get(key);
        }
        if (expectedText != null && expectedText.startsWith("@")) {
            return DataReader.get(expectedText.substring(1));
        }
        if (DateFormatResolver.isDateFormatNow(expectedText)) {
            String resolved = DateFormatResolver.resolve(expectedText);
            return resolved != null ? resolved : expectedText;
        }
        return expectedText != null ? expectedText : "";
    }

    /**
     * Feature kullanımı:
     * Then I  see element "Element"
     */
    @Then("I see the element {string}")
    public void iSeeTheElement(String elementKey) {
        assertionMethods.verifyElementIsVisible(elementKey, LocatorManager.getLocators());
    }

    /**
     * Feature kullanımı:
     * Then I don't see element "ErrorMessage"
     */
    @Then("I don't see element {string}")
    public void verifyElementNotExists(String elementKey) {
        assertionMethods.verifyElementNotExists(elementKey, LocatorManager.getLocators());
    }

    @Then("I verify element {string} contains text {string}")
    public void verifyElementContainsText(String elementKey, String expectedSubtext) {
        String actualSubtext = resolveExpectedText(expectedSubtext);
        assertionMethods.verifyElementContainsText(elementKey, actualSubtext, LocatorManager.getLocators());
    }

    @Then("I verify element {string} is enabled")
    public void verifyElementIsEnabled(String elementKey) {
        assertionMethods.verifyElementIsEnabled(elementKey, LocatorManager.getLocators());
    }

    @Then("I verify element {string} is disabled")
    public void verifyElementIsDisabled(String elementKey) {
        assertionMethods.verifyElementIsDisabled(elementKey, LocatorManager.getLocators());
    }

    @Then("I verify element {string} has attribute {string} equal to {string}")
    public void verifyElementAttributeEquals(String elementKey, String attributeName, String expectedValue) {
        String actualExpected = resolveExpectedText(expectedValue);
        assertionMethods.verifyElementAttributeEquals(elementKey, attributeName, actualExpected, LocatorManager.getLocators());
    }

    @Then("I verify the selected option in {string} is {string}")
    public void verifySelectedOptionIn(String elementKey, String expectedText) {
        String actualExpected = resolveExpectedText(expectedText);
        assertionMethods.verifySelectSelectedOptionEquals(elementKey, actualExpected, LocatorManager.getLocators());
    }

}
