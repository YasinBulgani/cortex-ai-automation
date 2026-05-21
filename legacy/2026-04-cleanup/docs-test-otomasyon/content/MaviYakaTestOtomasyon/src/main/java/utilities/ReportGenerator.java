package utilities;

import net.masterthought.cucumber.Configuration;
import net.masterthought.cucumber.ReportBuilder;

import java.io.BufferedReader;
import java.io.File;
import java.io.InputStreamReader;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;

/**
 * ReportGenerator:
 * Cucumber JSON çıktısından Masterthought HTML raporu üretir.
 * Allure raporlarını da programatik olarak oluşturur.
 * Çoklu domain desteği: MultiDomainCucumberRunner çalıştırılan domainleri set eder.
 */
public class ReportGenerator {

    private static List<String> executedDomains;

    /**
     * MultiDomainCucumberRunner tarafından çağrılır.
     */
    public static void setExecutedDomains(List<String> domains) {
        executedDomains = domains != null ? new ArrayList<>(domains) : null;
    }

    private static List<String> getExecutedDomains() {
        if (executedDomains != null && !executedDomains.isEmpty()) {
            return executedDomains;
        }
        // Tek domain modu (standart Cucumber runner kullanılmış olabilir - geriye dönük)
        String domain = System.getProperty("data.domain");
        if (domain == null || domain.isBlank()) {
            domain = ConfigReader.get("data.domain");
        }
        if (domain == null || domain.isBlank()) {
            domain = "girit";
        }
        return Collections.singletonList(domain);
    }

    public static void generateMasterthoughtReport() {
        String projectDir = System.getProperty("user.dir");
        List<String> domains = getExecutedDomains();
        List<String> jsonPaths = new ArrayList<>();

        for (String domain : domains) {
            String path = Paths.get(projectDir, "target", "cucumber-report", "cucumber-" + domain + ".json").toString();
            File f = new File(path);
            if (f.exists()) {
                jsonPaths.add(path);
            }
        }

        if (jsonPaths.isEmpty()) {
            // Geriye dönük: eski cucumber.json
            File legacy = new File("target/cucumber-report/cucumber.json");
            if (legacy.exists()) {
                jsonPaths.add(legacy.getPath());
            }
        }
        if (jsonPaths.isEmpty()) {
            throw new RuntimeException("Cucumber JSON dosyası bulunamadı: target/cucumber-report/");
        }

        File reportOutputDir = new File("target/masterthought-report");
        Configuration configuration = new Configuration(reportOutputDir, "MaviYakaTestOtomasyon");
        configuration.addClassifications("Browser", "Chrome");
        configuration.addClassifications("Environment", "Local");
        configuration.addClassifications("Domains", String.join(", ", domains));

        ReportBuilder reportBuilder = new ReportBuilder(jsonPaths, configuration);
        reportBuilder.generateReports();
    }

    /**
     * Excel raporu oluşturur.
     * Çoklu domain desteği: Her domain için ayrı JSON okunur, tek Excel'de birleşik rapor üretilir.
     */
    public static void generateExcelReport() {
        try {
            String projectDir = System.getProperty("user.dir");
            String excelOutputPath = Paths.get(projectDir, "rapor", "Test_Raporu.xlsx").toString();

            List<String> domains = getExecutedDomains();
            java.util.Map<String, String> domainToJsonPath = new java.util.LinkedHashMap<>();
            for (String domain : domains) {
                String jsonPath = Paths.get(projectDir, "target", "cucumber-report", "cucumber-" + domain + ".json").toString();
                File f = new File(jsonPath);
                if (f.exists()) {
                    domainToJsonPath.put(domain, jsonPath);
                }
            }
            if (domainToJsonPath.isEmpty()) {
                // Geriye dönük: tek cucumber.json
                String legacy = Paths.get(projectDir, "target", "cucumber-report", "cucumber.json").toString();
                if (new File(legacy).exists()) {
                    String domain = domains.isEmpty() ? "girit" : domains.get(0);
                    domainToJsonPath.put(domain, legacy);
                }
            }
            if (domainToJsonPath.isEmpty()) {
                System.out.println("Cucumber JSON dosyası bulunamadı. Excel raporu oluşturulmayacak.");
                return;
            }

            File reportDir = new File(Paths.get(projectDir, "rapor").toString());
            if (!reportDir.exists()) {
                reportDir.mkdirs();
            }

            ExcelReportGenerator.generateExcelReport(domainToJsonPath, excelOutputPath);
            System.out.println("Excel raporu başarıyla oluşturuldu: " + excelOutputPath);

        } catch (Exception e) {
            System.err.println("Excel raporu oluşturulurken hata oluştu: " + e.getMessage());
            e.printStackTrace();
        }
    }

    /**
     * Belirli bir domain için Allure raporu oluşturur (ana dizinde allure-report-{domain}).
     * Öncelik: 1) .allure/ içindeki yerel Allure  2) PATH'teki allure  3) Maven
     */
    public static void generateAllureReportForDomain(String domain) {
        try {
            String projectDir = System.getProperty("user.dir");
            Path resultsDir = Paths.get(projectDir, "target", "allure-results-" + domain);
            Path reportDir = Paths.get(projectDir, "allure-report-" + domain);

            if (!Files.exists(resultsDir)) return;
            try (java.util.stream.Stream<Path> stream = Files.list(resultsDir)) {
                if (stream.findAny().isEmpty()) return;
            }

            Files.createDirectories(reportDir);
            String resultsPath = resultsDir.toAbsolutePath().toString().replace("\\", "/");
            String reportPath = reportDir.toAbsolutePath().toString().replace("\\", "/");

            // 1) .allure/allure-*/bin/ içindeki yerel Allure (Maven/IDE'den çalışır)
            String localAllure = findLocalAllure(projectDir);
            if (localAllure != null && runAllureWithPath(localAllure, resultsPath, reportPath, projectDir)) {
                System.out.println("Allure raporu [" + domain + "] oluşturuldu: " + reportPath);
                return;
            }
            // 2) PATH'teki allure CLI
            if (runAllureCli(resultsPath, reportPath, projectDir)) {
                System.out.println("Allure raporu [" + domain + "] oluşturuldu: " + reportPath);
                return;
            }
            // 3) Maven fallback
            if (runMavenAllureReport(resultsPath, reportPath, projectDir)) {
                System.out.println("Allure raporu [" + domain + "] oluşturuldu: " + reportPath);
            } else {
                System.err.println("Allure raporu [" + domain + "] oluşturulamadı. .allure/ klasörü veya Maven yolunu kontrol edin.");
            }
        } catch (Exception e) {
            System.err.println("Allure raporu [" + domain + "] hatası: " + e.getMessage());
        }
    }

    /** Proje dizinindeki .allure klasorunde yerel Allure binary'sini bulur */
    private static String findLocalAllure(String projectDir) {
        try {
            Path allureDir = Paths.get(projectDir, ".allure");
            if (!Files.exists(allureDir)) return null;
            boolean win = System.getProperty("os.name", "").toLowerCase().contains("win");
            try (java.util.stream.Stream<Path> dirs = Files.list(allureDir)) {
                return dirs.filter(Files::isDirectory)
                        .filter(p -> p.getFileName().toString().startsWith("allure-"))
                        .map(p -> p.resolve("bin").resolve(win ? "allure.bat" : "allure"))
                        .filter(Files::exists)
                        .map(p -> p.toAbsolutePath().toString())
                        .findFirst()
                        .orElse(null);
            }
        } catch (Exception e) {
            return null;
        }
    }

    private static boolean runAllureWithPath(String allureExe, String resultsPath, String reportPath, String projectDir) {
        try {
            ProcessBuilder pb;
            if (allureExe.toLowerCase().endsWith(".bat")) {
                pb = new ProcessBuilder("cmd.exe", "/c", allureExe, "generate", resultsPath, "--clean", "-o", reportPath);
            } else {
                pb = new ProcessBuilder(allureExe, "generate", resultsPath, "--clean", "-o", reportPath);
            }
            pb.directory(new File(projectDir));
            pb.redirectErrorStream(true);
            Process p = pb.start();
            consumeStream(p.getInputStream(), true);
            return p.waitFor() == 0;
        } catch (Exception e) {
            return false;
        }
    }

    private static boolean runAllureCli(String resultsPath, String reportPath, String projectDir) {
        try {
            boolean win = System.getProperty("os.name", "").toLowerCase().contains("win");
            ProcessBuilder pb = win
                    ? new ProcessBuilder("cmd.exe", "/c", "allure", "generate", resultsPath, "--clean", "-o", reportPath)
                    : new ProcessBuilder("allure", "generate", resultsPath, "--clean", "-o", reportPath);
            pb.directory(new File(projectDir));
            pb.redirectErrorStream(true);
            Process p = pb.start();
            consumeStream(p.getInputStream(), true);
            return p.waitFor() == 0;
        } catch (Exception e) {
            return false;
        }
    }

    private static boolean runMavenAllureReport(String resultsPath, String reportPath, String projectDir) {
        try {
            String mvnPath = findMaven();
            boolean win = System.getProperty("os.name", "").toLowerCase().contains("win");
            ProcessBuilder pb = new ProcessBuilder();
            pb.directory(new File(projectDir));
            pb.redirectErrorStream(true);
            List<String> cmd = new ArrayList<>();
            if (win) {
                cmd.add("cmd.exe");
                cmd.add("/c");
            }
            cmd.add(mvnPath != null ? mvnPath : "mvn");
            cmd.add("allure:report");
            cmd.add("-DskipTests");
            cmd.add("-Dallure.results.directory=" + resultsPath);
            cmd.add("-Dallure.report.directory=" + reportPath);
            pb.command(cmd);
            Process p = pb.start();
            consumeStream(p.getInputStream(), true);
            return p.waitFor() == 0;
        } catch (Exception e) {
            return false;
        }
    }

    /** Maven yolunu bulur (MAVEN_HOME veya PATH). IDE'den çalıştırıldığında da çalışır. */
    private static String findMaven() {
        boolean win = System.getProperty("os.name", "").toLowerCase().contains("win");
        String mavenHome = System.getenv("MAVEN_HOME");
        if (mavenHome != null && !mavenHome.isBlank()) {
            Path mvn = Paths.get(mavenHome, "bin", win ? "mvn.cmd" : "mvn");
            if (Files.exists(mvn)) return mvn.toAbsolutePath().toString();
        }
        String m2Home = System.getenv("M2_HOME");
        if (m2Home != null && !m2Home.isBlank()) {
            Path mvn = Paths.get(m2Home, "bin", win ? "mvn.cmd" : "mvn");
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

    private static void consumeStream(java.io.InputStream is) {
        consumeStream(is, false);
    }

    private static void consumeStream(java.io.InputStream is, boolean verbose) {
        try (java.io.BufferedReader r = new java.io.BufferedReader(new java.io.InputStreamReader(is))) {
            String line;
            while ((line = r.readLine()) != null) {
                if (verbose || line.contains("Report generated") || line.contains("BUILD") || line.contains("ERROR")) {
                    System.out.println(line);
                }
            }
        } catch (Exception ignored) {}
    }

    /**
     * Allure raporlarını programatik olarak oluşturur.
     * Tek domain veya birleşik rapor için kullanılır.
     */
    public static void generateAllureReport() {
        try {
            String projectDir = System.getProperty("user.dir");
            Path resultsDir = Paths.get(projectDir, "target", "allure-results");
            Path reportDir = Paths.get(projectDir, "rapor");

            // Allure results klasörü yoksa veya boşsa rapor oluşturma
            boolean hasResults = false;
            if (Files.exists(resultsDir)) {
                try (java.util.stream.Stream<Path> stream = Files.list(resultsDir)) {
                    hasResults = stream.findAny().isPresent();
                }
            }
            if (!hasResults) {
                System.out.println("Allure results bulunamadı, rapor oluşturulmayacak.");
                return;
            }

            // Rapor klasörünü oluştur (yoksa)
            if (!Files.exists(reportDir)) {
                Files.createDirectories(reportDir);
            }

            String resultsPath = resultsDir.toAbsolutePath().toString().replace("\\", "/");
            String reportPath = reportDir.toAbsolutePath().toString().replace("\\", "/");

            // 1) .allure/ içindeki yerel Allure
            String localAllure = findLocalAllure(projectDir);
            if (localAllure != null && runAllureWithPath(localAllure, resultsPath, reportPath, projectDir)) {
                System.out.println("Allure raporu başarıyla oluşturuldu: " + reportDir);
                return;
            }
            // 2) PATH'teki allure CLI
            if (runAllureCli(resultsPath, reportPath, projectDir)) {
                System.out.println("Allure raporu başarıyla oluşturuldu: " + reportDir);
                return;
            }
            // 3) Maven
            String mvnPath = findMaven();
            boolean win = System.getProperty("os.name").toLowerCase().contains("win");
            List<String> cmd = new ArrayList<>();
            if (win) cmd.add("cmd.exe");
            if (win) cmd.add("/c");
            cmd.add(mvnPath != null ? mvnPath : "mvn");
            cmd.add("allure:report");
            cmd.add("-DskipTests");
            cmd.add("-Dallure.results.directory=" + resultsPath);
            cmd.add("-Dallure.report.directory=" + reportPath);
            ProcessBuilder processBuilder = new ProcessBuilder(cmd);
            processBuilder.directory(new File(projectDir));
            processBuilder.redirectErrorStream(true);
            Process process = processBuilder.start();
            consumeStream(process.getInputStream(), true);
            int exitCode = process.waitFor();
            if (exitCode == 0) {
                System.out.println("Allure raporu başarıyla oluşturuldu: " + reportDir);
            } else {
                System.err.println("Allure raporu oluşturulurken hata oluştu. Exit code: " + exitCode);
            }

        } catch (Exception e) {
            System.err.println("Allure raporu oluşturulurken hata oluştu: " + e.getMessage());
            e.printStackTrace();
        }
    }

    /**
     * Sadece rapor oluşturmak için (batch script'ten çağrılır).
     * Kullanım: mvn exec:java -Dexec.mainClass="utilities.ReportGenerator" -Dexec.args="girit ghz pex"
     */
    public static void main(String[] args) {
        if (args.length > 0) {
            setExecutedDomains(new ArrayList<>(Arrays.asList(args)));
        }
        try {
            generateMasterthoughtReport();
            System.out.println("Masterthought raporu oluşturuldu.");
        } catch (Exception e) {
            System.err.println("Masterthought hatası: " + e.getMessage());
        }
        try {
            generateAllureReport();
            System.out.println("Allure raporu oluşturuldu.");
        } catch (Exception e) {
            System.err.println("Allure hatası: " + e.getMessage());
        }
        try {
            generateExcelReport();
        } catch (Exception e) {
            System.err.println("Excel hatası: " + e.getMessage());
        }
    }
}
