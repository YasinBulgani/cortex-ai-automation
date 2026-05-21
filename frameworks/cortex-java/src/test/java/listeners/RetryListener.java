package listeners;

import io.cucumber.java.AfterAll;
import io.cucumber.java.BeforeAll;

/**
 * Retry behaviour for flaky tests.
 *
 * Cucumber JVM does not yet ship a built-in retry on the JUnit Platform
 * engine. The pragmatic alternative is to enable it via system property
 * read by the rerun plugin (cucumber.plugin=rerun:target/failed.txt) and
 * then re-running:
 *
 *     mvn -Dcucumber.features=@target/failed.txt test
 *
 * This listener prints a friendly hint at the end of the suite if any
 * failures occurred and the rerun file was produced.
 *
 * In the future, swap this for a true scenario-level retry (e.g. via the
 * JUnit Pioneer @RetryingTest or a Cucumber plugin); for now, keep the
 * rerun pattern documented.
 */
public class RetryListener {

    @BeforeAll
    public static void start() {
        System.out.println("[Cortex] Suite starting...");
    }

    @AfterAll
    public static void end() {
        java.io.File reruns = new java.io.File("target/failed.txt");
        if (reruns.exists() && reruns.length() > 0) {
            System.out.println("=".repeat(70));
            System.out.println(" Some scenarios failed. To retry only the failures:");
            System.out.println("   mvn test -Dcucumber.features=@target/failed.txt");
            System.out.println("=".repeat(70));
        }
    }
}
