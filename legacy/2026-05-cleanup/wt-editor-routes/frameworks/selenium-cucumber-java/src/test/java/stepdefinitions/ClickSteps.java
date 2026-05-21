package stepdefinitions;

import io.cucumber.java.en.When;
import methods.ClickMethods;
import utilities.LocatorManager;

/**
 * ClickSteps:
 * Feature dosyalarındaki tıklama adımlarını
 * ClickMethods ile bağlar.
 */
public class ClickSteps {

    private final ClickMethods clickMethods = new ClickMethods();

    /**
     * Feature kullanımı:
     * When I click on "LoginButton"
     *
     * @param elementKey JSON locator key
     */
    @When("I click on {string}")
    public void clickOnElement(String elementKey) {
        clickMethods.clickOnElement(elementKey, LocatorManager.getLocators());
    }

    @When("I double click on {string}")
    public void doubleClickOnElement(String elementKey) {
        clickMethods.doubleClickOnElement(elementKey, LocatorManager.getLocators());
    }

    @When("I right click on {string}")
    public void rightClickOnElement(String elementKey) {
        clickMethods.rightClickOnElement(elementKey, LocatorManager.getLocators());
    }
}
