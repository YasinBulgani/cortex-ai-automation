package stepdefinitions;

import io.cucumber.java.en.Then;
import io.cucumber.java.en.When;
import methods.AssertionMethods;
import methods.ContextMethods;
import methods.InputMethods;
import utilities.LocatorManager;
import utilities.ScenarioContext;

/**
 * ScenarioContextSteps:
 * Aynı senaryo içinde değer saklama ve saklanan değeri kullanma adımlarını bağlar.
 * Saklanan değerler sadece o senaryoda geçerlidir; sonraki senaryoda yoktur.
 */
public class ScenarioContextSteps {

    private final ContextMethods contextMethods = new ContextMethods();
    private final InputMethods inputMethods = new InputMethods();
    private final AssertionMethods assertionMethods = new AssertionMethods();

    @When("I save the value of element {string} as {string}")
    public void saveValueOfElementAs(String elementKey, String storageKey) {
        contextMethods.saveElementTextAs(elementKey, storageKey, LocatorManager.getLocators());
    }

    @When("I save the attribute {string} of element {string} as {string}")
    public void saveAttributeOfElementAs(String attributeName, String elementKey, String storageKey) {
        contextMethods.saveElementAttributeAs(elementKey, attributeName, storageKey, LocatorManager.getLocators());
    }

    @When("I enter the value stored under {string} into the input {string}")
    public void enterValueStoredUnderIntoInput(String storageKey, String elementKey) {
        String value = ScenarioContext.get(storageKey);
        inputMethods.enterTextIntoInput(elementKey, value, LocatorManager.getLocators());
    }

    @Then("I verify element {string} text is the value stored under {string}")
    public void verifyElementTextIsValueStoredUnder(String elementKey, String storageKey) {
        String expectedText = ScenarioContext.get(storageKey);
        assertionMethods.verifyElementTextEquals(elementKey, expectedText, LocatorManager.getLocators());
    }

    @Then("I verify element {string} contains the value stored under {string}")
    public void verifyElementContainsValueStoredUnder(String elementKey, String storageKey) {
        String expectedSubtext = ScenarioContext.get(storageKey);
        assertionMethods.verifyElementContainsText(elementKey, expectedSubtext, LocatorManager.getLocators());
    }
}
