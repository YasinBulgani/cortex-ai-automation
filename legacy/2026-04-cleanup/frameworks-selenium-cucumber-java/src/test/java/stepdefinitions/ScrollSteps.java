package stepdefinitions;

import io.cucumber.java.en.When;
import methods.ScrollMethods;
import utilities.LocatorManager;

/**
 * ScrollSteps:
 * Feature dosyalarındaki scroll adımlarını ScrollMethods ile bağlar.
 */
public class ScrollSteps {

    private final ScrollMethods scrollMethods = new ScrollMethods();

    /**
     * Feature kullanımı:
     * When I scroll to the element "FooterSection"
     */
    @When("I scroll to the element {string}")
    public void scrollToTheElement(String elementKey) {
        scrollMethods.scrollToElement(elementKey, LocatorManager.getLocators());
    }

    @When("I scroll to top")
    public void scrollToTop() {
        scrollMethods.scrollToTop();
    }

    @When("I scroll to bottom")
    public void scrollToBottom() {
        scrollMethods.scrollToBottom();
    }

    @When("I scroll down by {int} pixels")
    public void scrollDownByPixels(int pixels) {
        scrollMethods.scrollBy(0, pixels);
    }

    @When("I scroll up by {int} pixels")
    public void scrollUpByPixels(int pixels) {
        scrollMethods.scrollBy(0, -pixels);
    }
}