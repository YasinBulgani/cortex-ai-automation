package utilities;

import io.github.bonigarcia.wdm.WebDriverManager;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.chrome.ChromeDriver;
import org.openqa.selenium.chrome.ChromeOptions;
import org.openqa.selenium.edge.EdgeDriver;
import org.openqa.selenium.edge.EdgeOptions;
import org.openqa.selenium.firefox.FirefoxDriver;
import org.openqa.selenium.firefox.FirefoxOptions;

import java.time.Duration;

public class Driver {

    private static final ThreadLocal<WebDriver> driverThreadLocal = new ThreadLocal<>();

    private Driver() {
    }

    public static WebDriver getDriver() {
        if (driverThreadLocal.get() == null) {
            String browser = ConfigReader.get("browser");
            boolean headless = "true".equalsIgnoreCase(ConfigReader.get("headless"));

            WebDriver driver;

            switch (browser.toLowerCase()) {
                case "firefox":
                    WebDriverManager.firefoxdriver().setup();
                    if (headless) {
                        FirefoxOptions ffOptions = new FirefoxOptions();
                        ffOptions.addArguments("--headless");
                        driver = new FirefoxDriver(ffOptions);
                    } else {
                        driver = new FirefoxDriver();
                    }
                    break;

                case "edge":
                    WebDriverManager.edgedriver().setup();
                    if (headless) {
                        EdgeOptions edgeOptions = new EdgeOptions();
                        edgeOptions.addArguments("--headless");
                        edgeOptions.addArguments("--disable-gpu");
                        driver = new EdgeDriver(edgeOptions);
                    } else {
                        driver = new EdgeDriver();
                    }
                    break;

                case "chrome":
                default:
                    WebDriverManager.chromedriver().setup();
                    if (headless) {
                        ChromeOptions chromeOptions = new ChromeOptions();
                        chromeOptions.addArguments("--headless=new");
                        chromeOptions.addArguments("--disable-gpu");
                        chromeOptions.addArguments("--window-size=1920,1080");
                        chromeOptions.addArguments("--no-sandbox");
                        chromeOptions.addArguments("--disable-dev-shm-usage");
                        driver = new ChromeDriver(chromeOptions);
                    } else {
                        driver = new ChromeDriver();
                    }
                    break;
            }

            driver.manage().window().maximize();
            driver.manage().timeouts().implicitlyWait(
                    Duration.ofSeconds(
                            Long.parseLong(ConfigReader.get("implicitWait"))
                    )
            );

            driverThreadLocal.set(driver);
        }

        return driverThreadLocal.get();
    }

    public static void closeDriver() {
        WebDriver driver = driverThreadLocal.get();
        if (driver != null) {
            driver.quit();
            driverThreadLocal.remove();
        }
    }
}
