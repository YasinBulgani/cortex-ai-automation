package utilities;

import org.openqa.selenium.*;
import org.openqa.selenium.support.ui.ExpectedConditions;
import org.openqa.selenium.support.ui.WebDriverWait;

import java.time.Duration;
import java.util.Set;

public class BrowserUtils {

    public static void switchToNewWindow() {
        WebDriver driver = Driver.getDriver();
        String currentHandle = driver.getWindowHandle();
        Set<String> handles = driver.getWindowHandles();
        for (String handle : handles) {
            if (!handle.equals(currentHandle)) {
                driver.switchTo().window(handle);
                break;
            }
        }
    }

    public static void switchToOriginalWindow() {
        WebDriver driver = Driver.getDriver();
        Set<String> handles = driver.getWindowHandles();
        driver.switchTo().window(handles.iterator().next());
    }

    public static void switchToFrame(String frameIdOrName) {
        Driver.getDriver().switchTo().frame(frameIdOrName);
    }

    public static void switchToFrame(int index) {
        Driver.getDriver().switchTo().frame(index);
    }

    public static void switchToDefaultContent() {
        Driver.getDriver().switchTo().defaultContent();
    }

    public static void acceptAlert() {
        WebDriverWait wait = new WebDriverWait(Driver.getDriver(), Duration.ofSeconds(5));
        wait.until(ExpectedConditions.alertIsPresent());
        Driver.getDriver().switchTo().alert().accept();
    }

    public static void dismissAlert() {
        WebDriverWait wait = new WebDriverWait(Driver.getDriver(), Duration.ofSeconds(5));
        wait.until(ExpectedConditions.alertIsPresent());
        Driver.getDriver().switchTo().alert().dismiss();
    }

    public static String getAlertText() {
        WebDriverWait wait = new WebDriverWait(Driver.getDriver(), Duration.ofSeconds(5));
        wait.until(ExpectedConditions.alertIsPresent());
        return Driver.getDriver().switchTo().alert().getText();
    }

    public static Object executeJavaScript(String script, Object... args) {
        return ((JavascriptExecutor) Driver.getDriver()).executeScript(script, args);
    }

    public static void setLocalStorage(String key, String value) {
        executeJavaScript("window.localStorage.setItem(arguments[0], arguments[1]);", key, value);
    }

    public static String getLocalStorage(String key) {
        return (String) executeJavaScript("return window.localStorage.getItem(arguments[0]);", key);
    }

    public static void clearLocalStorage() {
        executeJavaScript("window.localStorage.clear();");
    }

    public static void waitForPageLoad(int timeoutSeconds) {
        new WebDriverWait(Driver.getDriver(), Duration.ofSeconds(timeoutSeconds))
                .until(d -> ((JavascriptExecutor) d)
                        .executeScript("return document.readyState").equals("complete"));
    }

    public static void waitForAjaxComplete(int timeoutSeconds) {
        new WebDriverWait(Driver.getDriver(), Duration.ofSeconds(timeoutSeconds))
                .until(d -> {
                    Boolean jqDone = (Boolean) ((JavascriptExecutor) d)
                            .executeScript("return (typeof jQuery === 'undefined') || jQuery.active === 0");
                    return jqDone != null && jqDone;
                });
    }

    public static String getCurrentUrl() {
        return Driver.getDriver().getCurrentUrl();
    }

    public static String getPageTitle() {
        return Driver.getDriver().getTitle();
    }

    public static void deleteCookies() {
        Driver.getDriver().manage().deleteAllCookies();
    }

    public static void addCookie(String name, String value) {
        Driver.getDriver().manage().addCookie(new Cookie(name, value));
    }
}
