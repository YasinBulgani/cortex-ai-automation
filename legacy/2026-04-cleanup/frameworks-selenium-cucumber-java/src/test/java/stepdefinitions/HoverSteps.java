package stepdefinitions;

import io.cucumber.java.en.When;
import methods.HoverMethods;
import utilities.LocatorManager;

/**
 * HoverSteps:
 * Feature dosyalarındaki hover adımlarını HoverMethods ile bağlar.
 */
public class HoverSteps {

    private final HoverMethods hoverMethods = new HoverMethods();

    @When("I hover over {string}")
    public void hoverOver(String elementKey) {
        hoverMethods.hoverOverElement(elementKey, LocatorManager.getLocators());
    }
}
