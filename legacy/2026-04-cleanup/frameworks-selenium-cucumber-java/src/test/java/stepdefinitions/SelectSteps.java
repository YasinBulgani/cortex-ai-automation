package stepdefinitions;

import io.cucumber.java.en.When;
import methods.SelectMethods;
import utilities.DataReader;
import utilities.LocatorManager;

/**
 * SelectSteps:
 * Feature dosyalarındaki dropdown (&lt;select&gt;) seçim adımlarını
 * SelectMethods ile bağlar.
 */
public class SelectSteps {

    private final SelectMethods selectMethods = new SelectMethods();

    /**
     * Feature: When I select "Option A" from "CountrySelect"
     * "@key" ile JSON'dan okunabilir.
     */
    @When("I select {string} from {string}")
    public void selectByVisibleText(String optionText, String elementKey) {
        String actualText = optionText.startsWith("@")
                ? DataReader.get(optionText.substring(1))
                : optionText;
        selectMethods.selectOptionByVisibleText(elementKey, actualText, LocatorManager.getLocators());
    }

    /**
     * Feature: When I select value "tr" from "CountrySelect"
     */
    @When("I select value {string} from {string}")
    public void selectByValue(String value, String elementKey) {
        String actualValue = value.startsWith("@")
                ? DataReader.get(value.substring(1))
                : value;
        selectMethods.selectOptionByValue(elementKey, actualValue, LocatorManager.getLocators());
    }
}
