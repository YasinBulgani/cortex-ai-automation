package runners;

import io.cucumber.core.cli.Main;
import org.junit.runner.Description;
import org.junit.runner.Runner;
import org.junit.runner.notification.RunNotifier;
import utilities.ConfigReader;
import utilities.DataReader;
import utilities.DomainListHelper;
import utilities.ReportGenerator;

import java.io.BufferedReader;
import java.io.File;
import java.io.IOException;
import java.io.InputStreamReader;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

/**
 * Çoklu veya tek domain için Cucumber testlerini sırayla çalıştırır.
 * Her domain için cucumber-{domain}.json üretir.
 */
public class MultiDomainCucumberRunner extends Runner {

    private final Class<?> testClass;
    private final List<String> executedDomains = new ArrayList<>();

    public MultiDomainCucumberRunner(Class<?> testClass) {
        this.testClass = testClass;
    }

    /** Her domain için tek düğüm: "Run: girit" vb. (ara suite yok, çift/boş düğüm olmaz). */
    private static String runNodeName(String domain) {
        return "Run: " + domain;
    }

    /** Suite yerine test description kullanıyoruz; IDE isimsiz alt düğüm eklemesin diye. */
    private Description runDescription(String domain) {
        return Description.createTestDescription(testClass, runNodeName(domain));
    }

    @Override
    public Description getDescription() {
        Description suite = Description.createSuiteDescription(testClass);
        for (String domain : DomainListHelper.getDomainList()) {
            suite.addChild(runDescription(domain));
        }
        return suite;
    }

    @Override
    public void run(RunNotifier notifier) {
        List<String> domains = DomainListHelper.getDomainList();
        String env = getEnv();
        String projectDir = System.getProperty("user.dir");
        boolean multiDomain = domains.size() > 1;

        clearPreviousAllureData(projectDir, domains);

        if (multiDomain) {
            String mvnPath = findMaven(projectDir);
            if (mvnPath != null) {
                runDomainsForked(notifier, domains, env, projectDir, mvnPath);
            } else {
                runDomainsInProcess(notifier, domains, env, projectDir);
            }
        } else {
            runDomainsInProcess(notifier, domains, env, projectDir);
        }

        ReportGenerator.setExecutedDomains(new ArrayList<>(executedDomains));
        generateAllReports(multiDomain, executedDomains);
    }

    /** Forked domain çalışmasında rapor üretilmiş mi kontrol eder (exit 1'i yorumlamak için). */
    private boolean hasDomainReportOutput(String projectDir, String domain) {
        try {
            Path allureDir = Paths.get(projectDir, "target", "allure-results-" + domain);
            if (Files.exists(allureDir)) {
                try (var s = Files.list(allureDir)) {
                    if (s.findAny().isPresent()) return true;
                }
            }
            Path cucumberJson = Paths.get(projectDir, "target", "cucumber-report", "cucumber-" + domain + ".json");
            if (Files.exists(cucumberJson) && Files.size(cucumberJson) > 0) return true;
        } catch (Exception ignored) {}
        return false;
    }

    private void clearPreviousAllureData(String projectDir, List<String> domains) {
        try {
            clearDir(Paths.get(projectDir, "target", "allure-results"));
            for (String domain : domains) {
                clearDir(Paths.get(projectDir, "target", "allure-results-" + domain));
                clearDir(Paths.get(projectDir, "allure-report-" + domain));
            }
            if (domains.size() == 1) {
                clearAllureReportFromRapor(Paths.get(projectDir, "rapor"));
            }
        } catch (Exception ignored) {}
    }

    private void clearDir(Path dir) {
        try {
            if (!Files.exists(dir)) return;
            try (var s = Files.list(dir)) {
                s.forEach(p -> {
                    try {
                        if (Files.isDirectory(p)) deleteRecursive(p);
                        else Files.delete(p);
                    } catch (IOException ignored) {}
                });
            }
        } catch (IOException ignored) {}
    }

    private void clearAllureReportFromRapor(Path raporDir) {
        try {
            if (!Files.exists(raporDir)) return;
            try (var s = Files.list(raporDir)) {
                s.forEach(p -> {
                    try {
                        if (!p.getFileName().toString().toLowerCase().endsWith(".xlsx")) {
                            if (Files.isDirectory(p)) deleteRecursive(p);
                            else Files.delete(p);
                        }
                    } catch (IOException ignored) {}
                });
            }
        } catch (Exception ignored) {}
    }

    private void deleteRecursive(Path dir) {
        try {
            if (Files.isDirectory(dir)) {
                try (var s = Files.list(dir)) {
                    s.forEach(this::deleteRecursive);
                }
            }
            Files.delete(dir);
        } catch (IOException ignored) {}
    }

    private String findMaven(String projectDir) {
        boolean win = System.getProperty("os.name", "").toLowerCase().contains("win");
        String mavenHome = System.getenv("MAVEN_HOME");
        if (mavenHome != null && !mavenHome.isBlank()) {
            Path mvn = Paths.get(mavenHome, "bin", win ? "mvn.cmd" : "mvn");
            if (Files.exists(mvn)) return mvn.toAbsolutePath().toString();
        }
        try {
            ProcessBuilder pb = win
                    ? new ProcessBuilder("cmd.exe", "/c", "where", "mvn")
                    : new ProcessBuilder("sh", "-c", "which mvn");
            pb.redirectErrorStream(true);
            Process p = pb.start();
            try (BufferedReader r = new BufferedReader(new InputStreamReader(p.getInputStream()))) {
                String line = r.readLine();
                if (line != null && !line.isBlank()) return line.trim().split("\\s+")[0];
            }
        } catch (Exception ignored) {}
        return null;
    }

    private void runDomainsForked(RunNotifier notifier, List<String> domains, String env, String projectDir, String mvnPath) {
        boolean win = System.getProperty("os.name", "").toLowerCase().contains("win");
        for (String domain : domains) {
            Description runDesc = runDescription(domain);
            notifier.fireTestStarted(runDesc);
            try {
                runDomainForkedOnce(notifier, domain, env, projectDir, mvnPath, win);
            } finally {
                notifier.fireTestFinished(runDesc);
            }
        }
    }

    private void runDomainForkedOnce(RunNotifier notifier, String domain, String env, String projectDir, String mvnPath, boolean win) {
        Path domainAllureDir = Paths.get(projectDir, "target", "allure-results-" + domain);
        Path domainReportDir = Paths.get(projectDir, "allure-report-" + domain);
        String allurePath = domainAllureDir.toAbsolutePath().toString().replace("\\", "/");
        String reportPath = domainReportDir.toAbsolutePath().toString().replace("\\", "/");

        List<String> cmd = new ArrayList<>();
        if (win) {
            cmd.add("cmd.exe");
            cmd.add("/c");
        }
        cmd.add(mvnPath);
        cmd.add("-q");
        cmd.add("test");
        cmd.add("-Dtest=TestRunner");
        cmd.add("-Ddomains=" + domain);
        cmd.add("-Dallure.results.directory=" + allurePath);
        cmd.add("-Dallure.report.directory=" + reportPath);
        cmd.add("-Ddata.env=" + env);

        ProcessBuilder pb = new ProcessBuilder(cmd);
        pb.directory(new File(projectDir));
        pb.redirectErrorStream(true);

        try {
            Process p = pb.start();
            List<String> outputLines = new ArrayList<>();
            try (BufferedReader r = new BufferedReader(new InputStreamReader(p.getInputStream()))) {
                String line;
                while ((line = r.readLine()) != null) {
                    outputLines.add(line);
                    System.out.println(line);
                    System.out.flush();
                    if (line.contains("ERROR") || line.contains("FAILURE")) System.err.println(line);
                }
            }
            System.out.flush();
            System.err.flush();
            int exit = p.waitFor();
            executedDomains.add(domain);
            if (exit != 0) {
                boolean hasReport = hasDomainReportOutput(projectDir, domain);
                if (hasReport) {
                    System.err.println("[domain: " + domain + "] Maven exit code: " + exit + " (raporlar üretildi, hata sayılmadı).");
                } else {
                    System.err.println("[domain: " + domain + "] Maven process exit code: " + exit + ". Son çıktı:");
                    for (String line : outputLines) System.err.println(line);
                    notifier.fireTestFailure(new org.junit.runner.notification.Failure(
                            runDescription(domain),
                            new RuntimeException("Cucumber run failed for domain: " + domain + " (exit " + exit + "). Yukarıdaki Maven çıktısına bakın.")));
                }
            }
        } catch (Exception e) {
            executedDomains.add(domain);
            notifier.fireTestFailure(new org.junit.runner.notification.Failure(
                    runDescription(domain),
                    new RuntimeException("Domain çalıştırılamadı: " + domain, e)));
        }
    }

    private void runDomainsInProcess(RunNotifier notifier, List<String> domains, String env, String projectDir) {
        ClassLoader classLoader = Thread.currentThread().getContextClassLoader();
        boolean multiDomain = domains.size() > 1;
        for (String domain : domains) {
            Description runDesc = runDescription(domain);
            notifier.fireTestStarted(runDesc);
            try {
                runDomainInProcess(notifier, domain, env, projectDir, classLoader, multiDomain);
            } finally {
                notifier.fireTestFinished(runDesc);
            }
        }
    }

    private void runDomainInProcess(RunNotifier notifier, String domain, String env, String projectDir,
                                    ClassLoader classLoader, boolean multiDomain) {
        System.setProperty("data.domain", domain);
        System.setProperty("data.env", env);
        DataReader.reloadForNewDomain(domain, env);

        String jsonPath = "target/cucumber-report/cucumber-" + domain + ".json";
        ensureReportDir();

        if (multiDomain) {
            Path domainAllureDir = Paths.get(projectDir, "target", "allure-results-" + domain);
            ensureDir(domainAllureDir);
            String allureDirPath = domainAllureDir.toAbsolutePath().toString().replace("\\", "/");
            System.setProperty("allure.results.directory", allureDirPath);
            writeAllureProperties(projectDir, allureDirPath);
        } else {
            String defaultAllurePath = Paths.get(projectDir, "target", "allure-results")
                    .toAbsolutePath().toString().replace("\\", "/");
            writeAllureProperties(projectDir, defaultAllurePath);
        }

        byte exitCode = Main.run(buildCucumberArgs(jsonPath), classLoader);
        System.out.flush();
        System.err.flush();
        executedDomains.add(domain);

        if (exitCode != 0) {
            notifier.fireTestFailure(new org.junit.runner.notification.Failure(
                    runDescription(domain),
                    new RuntimeException("Cucumber run failed for domain: " + domain)));
        }
    }

    private void generateAllReports(boolean multiDomain, List<String> executedDomainsList) {
        try {
            ReportGenerator.generateMasterthoughtReport();
        } catch (Exception e) {
            System.err.println("Masterthought raporu oluşturulamadı: " + e.getMessage());
        }
        // Çoklu domain: Her domain için allure-results-{domain} -> allure-report-{domain} HTML üret
        if (multiDomain && executedDomainsList != null) {
            for (String domain : executedDomainsList) {
                try {
                    ReportGenerator.generateAllureReportForDomain(domain);
                } catch (Exception e) {
                    System.err.println("Allure raporu [" + domain + "] oluşturulamadı: " + e.getMessage());
                }
            }
        } else if (!multiDomain) {
            try {
                ReportGenerator.generateAllureReport();
            } catch (Exception e) {
                System.err.println("Allure raporu oluşturulamadı: " + e.getMessage());
            }
        }
        try {
            ReportGenerator.generateExcelReport();
        } catch (Exception e) {
            System.err.println("Excel raporu oluşturulamadı: " + e.getMessage());
        }
    }

    private String getEnv() {
        String env = System.getProperty("data.env");
        if (env == null || env.isBlank()) {
            env = ConfigReader.get("data.env");
        }
        return (env != null && !env.isBlank()) ? env : "test";
    }

    private void ensureReportDir() {
        ensureDir(Paths.get("target", "cucumber-report"));
    }

    private void ensureDir(Path dir) {
        try {
            if (!Files.exists(dir)) {
                Files.createDirectories(dir);
            }
        } catch (IOException e) {
            throw new RuntimeException("Klasör oluşturulamadı: " + dir, e);
        }
    }

    private void writeAllureProperties(String projectDir, String resultsPath) {
        try {
            Path propsPath = Paths.get(projectDir, "target", "test-classes", "allure.properties");
            Files.createDirectories(propsPath.getParent());
            String content = "allure.results.directory=" + resultsPath + "\nallure.report.name=" + ConfigReader.getReportName() + "\n";
            Files.writeString(propsPath, content);
        } catch (IOException ignored) {}
    }

    /**
     * Tek feature veya klasör çalıştırmak için: VM option ile -Dcucumber.features=path verilebilir.
     * Örnek: -Dcucumber.features=src/test/resources/features/absence.feature
     * Virgülle birden fazla path: -Dcucumber.features=src/.../a.feature,src/.../b.feature
     * Verilmezse her zaman tüm features klasörü çalışır (mevcut davranış).
     */
    private String[] buildCucumberArgs(String jsonPath) {
        String featuresProp = System.getProperty("cucumber.features");
        String[] featurePaths;
        if (featuresProp != null && !featuresProp.isBlank()) {
            featurePaths = Arrays.stream(featuresProp.split(","))
                    .map(String::trim)
                    .filter(s -> !s.isEmpty())
                    .toArray(String[]::new);
        } else {
            featurePaths = new String[]{"src/test/resources/features"};
        }

        List<String> args = new ArrayList<>(Arrays.asList(
                "-g", "stepdefinitions",
                "-p", "pretty",
                "-p", "html:target/cucumber-report.html",
                "-p", "json:" + jsonPath,
                "-p", "junit:target/cucumber-report/cucumber.xml",
                "-p", "io.qameta.allure.cucumber7jvm.AllureCucumber7Jvm",
                "-t", "@all"
        ));
        for (String path : featurePaths) {
            args.add(path);
        }
        return args.toArray(new String[0]);
    }
}
