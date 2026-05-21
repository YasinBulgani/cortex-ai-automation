package stepdefinitions;

import io.cucumber.java.en.When;
import methods.DragDropMethods;
import utilities.LocatorManager;

/**
 * DragDropSteps:
 * Feature dosyalarındaki sürükle-bırak adımlarını DragDropMethods ile bağlar.
 */
public class DragDropSteps {

    private final DragDropMethods dragDropMethods = new DragDropMethods();

    @When("I drag {string} and drop on {string}")
    public void dragAndDrop(String sourceKey, String targetKey) {
        dragDropMethods.dragAndDrop(sourceKey, targetKey, LocatorManager.getLocators());
    }
}
