package stepdefinitions;

import io.cucumber.java.en.When;
import methods.ScreenshotMethods;
import utilities.LocatorManager;

/**
 * ScreenshotSteps:
 * Feature dosyalarındaki ekran görüntüsü adımlarını ScreenshotMethods ile bağlar.
 */
public class ScreenshotSteps {

    private final ScreenshotMethods screenshotMethods = new ScreenshotMethods();

    @When("I take a screenshot {string}")
    public void takeScreenshot(String name) {
        screenshotMethods.takeScreenshot(name);
    }

    @When("I take screenshot of element {string}")
    public void takeScreenshotOfElement(String elementKey) {
        screenshotMethods.takeScreenshotOfElement(elementKey, LocatorManager.getLocators());
    }
}
