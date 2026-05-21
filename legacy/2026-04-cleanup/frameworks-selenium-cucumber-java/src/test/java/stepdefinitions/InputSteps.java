package stepdefinitions;

import io.cucumber.java.en.When;
import methods.InputMethods;
import utilities.DataReader;
import utilities.DateFormatResolver;
import utilities.LocatorManager;
import utilities.ScenarioContext;
import utilities.TestFileResolver;

import java.util.Random;

/**
 * InputSteps:
 * Feature dosyasındaki input adımlarını
 * InputMethods ile bağlar.
 * "+-key" → 15 haneli random üretir, inputa yazar ve ScenarioContext'e key ile saklar (senaryoda birden fazla key kullanılabilir).
 */
public class InputSteps {

    private static final int RANDOM_STRING_LENGTH = 15;
    private static final String ALPHANUMERIC = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";
    private static final Random RANDOM = new Random();

    private final InputMethods inputMethods = new InputMethods();

    /**
     * Feature:
     * When I enter "test@test.com" into the input "EmailInput"
     * When I enter "@username" into the input "UserNameInput" (JSON'dan okur)
     * When I enter "+-abc" into the input "..." → 15 haneli random üretilir, yazılır ve "abc" key ile hafızada tutulur
     */
    @When("I enter {string} into the input {string}")
    public void enterTextIntoInput(String text, String elementKey) {
        String actualText = resolveInputText(text);
        inputMethods.enterTextIntoInput(elementKey, actualText, LocatorManager.getLocators());
    }
    
    /**
     * Feature kullanımı:
     * When I clear the input "UserNameInput"
     */
    @When("I clear the input {string}")
    public void clearTheInputField(String elementKey) {
        inputMethods.clearInputField(elementKey, LocatorManager.getLocators());
    }

    /**
     * File input'a (type=file) dosya yükler.
     * "pdf" / "Doc" → testFile içindeki ilgili uzantılı dosya; tam yol veya "@key" (DataReader) da kullanılabilir.
     */
    @When("I upload the file {string} to the input {string}")
    public void uploadFileToInput(String filePath, String elementKey) {
        String actualPath = resolveFilePath(filePath);
        inputMethods.enterFilePathIntoFileInput(elementKey, actualPath, LocatorManager.getLocators());
    }

    /**
     * Dosya yolunu çözümler: "@key" → DataReader, "pdf"/"Doc" → testFile'dan uzantıya göre, aksi halde tam yol.
     */
    private String resolveFilePath(String filePath) {
        if (filePath.startsWith("@")) {
            return DataReader.get(filePath.substring(1));
        }
        return TestFileResolver.getFilePath(filePath);
    }

    @When("I enter {string} into the input {string} and press {string}")
    public void enterTextAndPressKey(String text, String elementKey, String keyName) {
        String actualText = resolveInputText(text);
        inputMethods.enterTextIntoInputAndPressKey(elementKey, actualText, keyName, LocatorManager.getLocators());
    }

    @When("I clear and enter {string} into the input {string}")
    public void clearAndEnterText(String text, String elementKey) {
        String actualText = resolveInputText(text);
        inputMethods.clearAndEnterText(elementKey, actualText, LocatorManager.getLocators());
    }

    /**
     * "+-key" → Key daha önce ScenarioContext'te varsa o değer kullanılır; yoksa 15 haneli random
     * üretilir, key ile saklanır ve döner. Böylece aynı key birden fazla input'a yazıldığında hep aynı değer gider.
     * "@key" → DataReader'dan okur.
     * "dateformatnow ..." veya "dateformatnow:name" → bugünün tarihi, verilen formatta string.
     * Aksi halde literal metin.
     */
    private String resolveInputText(String text) {
        if (text != null && text.startsWith("+-")) {
            String key = text.substring(2).trim();
            if (key.isEmpty()) {
                throw new IllegalArgumentException("+- kullanımında key boş olamaz. Örnek: +-abc");
            }
            if (ScenarioContext.containsKey(key)) {
                return ScenarioContext.get(key);
            }
            String random = generateRandom15();
            ScenarioContext.put(key, random);
            return random;
        }
        if (text != null && text.startsWith("@")) {
            return DataReader.get(text.substring(1));
        }
        if (DateFormatResolver.isDateFormatNow(text)) {
            String resolved = DateFormatResolver.resolve(text);
            return resolved != null ? resolved : text;
        }
        return text != null ? text : "";
    }

    private static String generateRandom15() {
        StringBuilder sb = new StringBuilder(RANDOM_STRING_LENGTH);
        for (int i = 0; i < RANDOM_STRING_LENGTH; i++) {
            sb.append(ALPHANUMERIC.charAt(RANDOM.nextInt(ALPHANUMERIC.length())));
        }
        return sb.toString();
    }
}
