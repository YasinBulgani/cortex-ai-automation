package stepdefinitions;

import io.cucumber.java.en.Then;
import io.cucumber.java.en.When;
import methods.CheckboxMethods;
import utilities.LocatorManager;

/**
 * CheckboxSteps:
 * Feature dosyalarındaki checkbox adımlarını CheckboxMethods ile bağlar.
 */
public class CheckboxSteps {

    private final CheckboxMethods checkboxMethods = new CheckboxMethods();

    @When("I check the checkbox {string}")
    public void checkCheckbox(String elementKey) {
        checkboxMethods.checkCheckbox(elementKey, LocatorManager.getLocators());
    }

    @When("I uncheck the checkbox {string}")
    public void uncheckCheckbox(String elementKey) {
        checkboxMethods.uncheckCheckbox(elementKey, LocatorManager.getLocators());
    }

    @Then("I verify checkbox {string} is checked")
    public void verifyCheckboxIsChecked(String elementKey) {
        checkboxMethods.verifyCheckboxIsChecked(elementKey, LocatorManager.getLocators());
    }

    @Then("I verify checkbox {string} is unchecked")
    public void verifyCheckboxIsUnchecked(String elementKey) {
        checkboxMethods.verifyCheckboxIsUnchecked(elementKey, LocatorManager.getLocators());
    }
}
