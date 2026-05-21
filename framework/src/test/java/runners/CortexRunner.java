package runners;

import org.junit.platform.suite.api.ConfigurationParameter;
import org.junit.platform.suite.api.IncludeEngines;
import org.junit.platform.suite.api.SelectClasspathResource;
import org.junit.platform.suite.api.Suite;

/**
 * Master test runner for the Cortex framework.
 *
 * Tag filtering, parallel parameters and reporting all come from
 * src/test/resources/junit-platform.properties so a single runner can be
 * driven by Maven profiles / -D system properties:
 *
 *   mvn test                      Default suite (regression minus @manual)
 *   mvn -Psmoke test              Smoke-only
 *   mvn -Pregression test         Full regression
 *   mvn -Pparallel test           4-thread parallel
 *   mvn -Pparallel -Dparallel.threads=8 test
 *   mvn -Pdebug test              Slow-mo + trace + video
 *   mvn -Pheadless test           Headless mode
 *
 * Tag overrides on the CLI:
 *   mvn test -Dcucumber.filter.tags="@smoke and @login"
 *   mvn test -Dcucumber.filter.tags="@security and not @manual"
 *
 * For ad-hoc single-feature execution:
 *   mvn test -Dcucumber.features=src/test/resources/projects/cortex/features/login.feature
 */
@Suite
@IncludeEngines("cucumber")
@SelectClasspathResource("projects")
@SelectClasspathResource("shared")
@SelectClasspathResource("recordings")
@ConfigurationParameter(key = "cucumber.glue", value = "playwright.stepdefs,listeners")
public class CortexRunner {
}
