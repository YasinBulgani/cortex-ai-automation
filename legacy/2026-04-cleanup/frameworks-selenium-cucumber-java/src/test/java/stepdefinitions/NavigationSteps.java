package stepdefinitions;

import io.cucumber.java.en.Given;
import io.cucumber.java.en.When;
import methods.NavigationMethods;

/**
 * NavigationSteps:
 * Feature dosyalarında yer alan navigasyon (URL açma)
 * adımlarını NavigationMethods ile bağlar.
 */
public class NavigationSteps {

    private final NavigationMethods navigationMethods = new NavigationMethods();

    /**
     * Config dosyasındaki anahtara karşılık gelen URL'i açar.
     *
     * Feature kullanımı:
     * Given I open the application url from config "url"
     */
    @Given("I open the application url from config {string}")
    public void openApplicationUrlFromConfig(String configKey) {
        navigationMethods.openUrlFromConfig(configKey);
    }

    /**
     * Verilen URL'i doğrudan açar.
     *
     * Feature kullanımı:
     * Given I open the application url "https://example.com"
     */
    @Given("I open the application url {string}")
    public void openApplicationUrl(String url) {
        navigationMethods.openUrl(url);
    }

    @When("I go back")
    public void goBack() {
        navigationMethods.goBack();
    }

    @When("I go forward")
    public void goForward() {
        navigationMethods.goForward();
    }

    @When("I refresh the page")
    public void refreshPage() {
        navigationMethods.refreshPage();
    }
}
