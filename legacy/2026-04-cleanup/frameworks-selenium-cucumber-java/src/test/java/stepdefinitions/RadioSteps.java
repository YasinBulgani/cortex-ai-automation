package stepdefinitions;

import io.cucumber.java.en.Then;
import io.cucumber.java.en.When;
import methods.RadioButtonMethods;
import utilities.DataReader;
import utilities.LocatorManager;

/**
 * RadioSteps:
 * Feature dosyalarındaki radyo buton adımlarını RadioButtonMethods ile bağlar.
 */
public class RadioSteps {

    private final RadioButtonMethods radioButtonMethods = new RadioButtonMethods();

    @When("I select radio {string} with value {string}")
    public void selectRadioByValue(String groupOrKey, String value) {
        String actualValue = value.startsWith("@") ? DataReader.get(value.substring(1)) : value;
        radioButtonMethods.selectRadioByValue(groupOrKey, actualValue, LocatorManager.getLocators());
    }

    @Then("I verify radio {string} is selected with value {string}")
    public void verifyRadioSelected(String groupOrKey, String value) {
        String actualValue = value.startsWith("@") ? DataReader.get(value.substring(1)) : value;
        radioButtonMethods.verifyRadioSelected(groupOrKey, actualValue, LocatorManager.getLocators());
    }
}
