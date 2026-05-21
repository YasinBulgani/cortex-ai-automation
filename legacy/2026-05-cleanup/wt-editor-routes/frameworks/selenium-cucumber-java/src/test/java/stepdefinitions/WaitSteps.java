package stepdefinitions;

import io.cucumber.java.en.When;
import methods.WaitMethods;
import utilities.LocatorManager;

/**
 * WaitSteps:
 * Feature dosyalarındaki bekleme adımlarını
 * WaitMethods ile bağlar.
 */
public class WaitSteps {

    private final WaitMethods waitMethods = new WaitMethods();

    @When("I wait for {int} seconds")
    public void waitForSeconds(int seconds) {
        waitMethods.waitForSeconds(seconds);
    }

    @When("I wait for element {string} to be clickable")
    public void waitForElementClickable(String elementKey) {
        waitMethods.waitForElementClickable(elementKey, LocatorManager.getLocators());
    }

    @When("I wait for element {string} to disappear")
    public void waitForElementToDisappear(String elementKey) {
        waitMethods.waitForElementToDisappear(elementKey, LocatorManager.getLocators());
    }
}
