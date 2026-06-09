package karate;

import com.intuit.karate.junit5.Karate;

/**
 * Karate test runner with JUnit 5
 *
 * Usage:
 *   mvn test -Dtest=TestRunner
 *   mvn test -Dtest=TestRunner -Dkarate.options="--tags @smoke"
 *   mvn test -Dtest=TestRunner -Dbase.url=http://localhost:8000
 *
 * Environment profiles:
 *   dev   — http://localhost:8000 (default)
 *   stage — https://api-stage.example.com
 *   prod  — https://api.example.com
 */
public class TestRunner {

    @Karate.Test
    public Karate testAll() {
        return Karate.run().relativeTo(getClass());
    }

    @Karate.Test
    public Karate testSmoke() {
        return Karate.run()
                .tags("@smoke")
                .relativeTo(getClass());
    }

    @Karate.Test
    public Karate testCritical() {
        return Karate.run()
                .tags("@critical")
                .relativeTo(getClass());
    }

    @Karate.Test
    public Karate testRBAC() {
        return Karate.run()
                .tags("@rbac")
                .relativeTo(getClass());
    }
}
