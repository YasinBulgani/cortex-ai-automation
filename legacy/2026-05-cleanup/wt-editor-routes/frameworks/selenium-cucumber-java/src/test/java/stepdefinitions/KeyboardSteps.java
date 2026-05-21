package stepdefinitions;

import io.cucumber.java.en.When;
import methods.InputMethods;

/**
 * KeyboardSteps:
 * Klavye tuşu basma adımlarını InputMethods ile bağlar.
 */
public class KeyboardSteps {

    private final InputMethods inputMethods = new InputMethods();

    /**
     * Feature kullanımı:
     * When I press the "ENTER" key
     */
    @When("I press the {string} key")
    public void pressTheKey(String keyName) {
        inputMethods.pressKey(keyName);
    }
}
