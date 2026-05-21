package stepdefinitions;

import io.cucumber.java.After;
import io.cucumber.java.Before;
import io.cucumber.java.BeforeStep;
import io.cucumber.java.Scenario;
import io.qameta.allure.Allure;
import io.qameta.allure.model.Label;
import org.openqa.selenium.OutputType;
import org.openqa.selenium.TakesScreenshot;
import utilities.ConfigReader;
import utilities.Driver;
import utilities.LocatorManager;
import utilities.LoggerUtil;
import utilities.ScenarioContext;
import utilities.StepReporter;


/**
 * Hooks:
 * Cucumber senaryolarından önce/sonra otomatik çalışan metotları barındırır.
 *
 * Bu class Step Definition değildir.
 * Ama Cucumber lifecycle'ının bir parçasıdır.
 */
public class Hooks {

    private static final ThreadLocal<Boolean> ALLURE_LABELS_SET = ThreadLocal.withInitial(() -> false);

    /**
     * İlk adımdan önce - Allure test oluşturulduktan sonra domain bilgisini ekle.
     */
    @BeforeStep
    public void setAllureDomainLabels(Scenario scenario) {
        if (ALLURE_LABELS_SET.get()) return;
        String domain = System.getProperty("data.domain");
        if (domain == null || domain.isBlank()) {
            domain = ConfigReader.get("data.domain");
        }
        if (domain != null && !domain.isBlank()) {
            final String domainVal = domain;
            try {
                Allure.getLifecycle().updateTestCase(result -> {
                    result.setName((scenario.getName() != null ? scenario.getName() : "Test") + " [" + domainVal + "]");
                    result.getLabels().removeIf(l -> "parentSuite".equals(l.getName()));
                    result.getLabels().add(new Label().setName("parentSuite").setValue(domainVal));
                    result.getLabels().removeIf(l -> "domain".equals(l.getName()));
                    result.getLabels().add(new Label().setName("domain").setValue(domainVal));
                    result.getParameters().removeIf(p -> "domain".equals(p.getName()));
                    result.getParameters().add(new io.qameta.allure.model.Parameter().setName("domain").setValue(domainVal));
                });
                ALLURE_LABELS_SET.set(true);
            } catch (Exception ignored) { }
        }
    }

    /**
     * Her Scenario'dan önce çalışır.
     *
     * Burada:
     * 1) Locator'ları JSON'dan yükleriz (1 kez)
     * 2) Driver'ı hazırlarız (tarayıcıyı açarız)
     * 3) Allure raporunda domain etiketi eklenir (domain bazlı filtreleme için)
     */
    @Before
    public void setUp(Scenario scenario) {
        // StepReporter'a Scenario'yu set et (thread-local)
        StepReporter.setScenario(scenario);

        // Locator JSON dosyalarının bulunduğu klasör (proje köküne göre - IDE/Maven fark etmez)
        String projectRoot = System.getProperty("user.dir");
        String locatorPath = projectRoot + "/src/main/resources/locators";

        // Feature name'i otomatik olarak URI'den al
        String featureUri = scenario.getUri().toString();
        String featureFile = featureUri.substring(featureUri.lastIndexOf("/") + 1);
        String featureName = featureFile.replace(".feature", "");

        LoggerUtil.logInfo("Loading locators for feature: " + featureName + " from: " + locatorPath);

        // Locator'ları yükle (JSON -> Map<String, By>). Hata olursa test hemen dursun, exception yutulmasın.
        LocatorManager.loadLocators(locatorPath, featureName);


        // Tarayıcıyı başlat / hazırla
        Driver.getDriver();
    }

    /**
     * Her Scenario'dan sonra çalışır.
     *
     * Burada:
     * - Tarayıcıyı kapatırız
     */
    @After
    public void tearDown(Scenario scenario) {

        // Senaryo başarısız olduysa
        if (scenario.isFailed()) {

            LoggerUtil.logError("Scenario FAILED: " + scenario.getName(), null);

            try {
                // Screenshot al
                byte[] screenshot = ((TakesScreenshot) Driver.getDriver())
                        .getScreenshotAs(OutputType.BYTES);

                // Cucumber raporuna ekle (JSON içine gömülür)
                scenario.attach(
                        screenshot,
                        "image/png",
                        "Failure Screenshot"
                );

            } catch (Exception e) {
                LoggerUtil.logError("Failed to capture screenshot", e);
            }
        }
        
        // StepReporter'dan Scenario'yu temizle
        StepReporter.clearScenario();
        // Senaryo context'ini temizle (bir sonraki senaryoda önceki veriler kalmasın)
        ScenarioContext.clear();
        ALLURE_LABELS_SET.remove();

        // Tarayıcıyı kapatır ve driver'ı null'a çeker
       Driver.closeDriver();
    }
}
