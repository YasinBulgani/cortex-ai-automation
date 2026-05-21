package utilities;

import com.google.gson.Gson;
import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;

import org.apache.poi.ss.usermodel.*;
import org.apache.poi.xssf.usermodel.XSSFWorkbook;

import java.io.FileOutputStream;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.text.SimpleDateFormat;
import java.util.*;

/**
 * Cucumber JSON çıktısından özet, detay ve adım detaylarını içeren Excel raporu üretir.
 * Çoklu domain desteği: Her domain için ayrı bloklar/sekmeler.
 */
public class ExcelReportGenerator {

    /**
     * domainToJsonPath: domain -> JSON dosya yolu (örn: girit -> .../cucumber-girit.json)
     */
    public static void generateExcelReport(java.util.Map<String, String> domainToJsonPath, String outputPath) {
        try {
            LoggerUtil.logInfo("Excel raporu oluşturuluyor...");

            if (domainToJsonPath == null || domainToJsonPath.isEmpty()) {
                LoggerUtil.logError("Domain/JSON eşlemesi boş", null);
                return;
            }

            String env = getEnv();
            Gson gson = new Gson();
            Map<String, JsonArray> domainToFeatures = new LinkedHashMap<>();
            for (Map.Entry<String, String> e : domainToJsonPath.entrySet()) {
                String content = new String(Files.readAllBytes(Paths.get(e.getValue())));
                JsonArray arr = gson.fromJson(content, JsonArray.class);
                if (arr != null && arr.size() > 0) {
                    domainToFeatures.put(e.getKey(), arr);
                }
            }
            if (domainToFeatures.isEmpty()) {
                LoggerUtil.logError("Geçerli JSON bulunamadı", null);
                return;
            }

            Workbook workbook = new XSSFWorkbook();
            CellStyle headerStyle = createHeaderStyle(workbook);
            CellStyle passedStyle = createStatusStyle(workbook, IndexedColors.GREEN.getIndex());
            CellStyle failedStyle = createStatusStyle(workbook, IndexedColors.RED.getIndex());
            CellStyle skippedStyle = createStatusStyle(workbook, IndexedColors.ORANGE.getIndex());
            CellStyle numberStyle = createNumberStyle(workbook);

            createSummarySheetMulti(workbook, domainToFeatures, headerStyle, numberStyle, env);
            createSummaryDetailSheet(workbook, domainToFeatures, headerStyle, passedStyle, failedStyle);
            // Detay sekmeleri (Detay girit, Detay ghz vb.) istenmediği için oluşturulmuyor.
            for (Map.Entry<String, JsonArray> e : domainToFeatures.entrySet()) {
                String envLabel = e.getKey() + " " + env;
                createStepDetailSheets(workbook, e.getValue(), headerStyle, passedStyle, failedStyle, skippedStyle, numberStyle, envLabel, e.getKey());
            }

            try (FileOutputStream fos = new FileOutputStream(outputPath)) {
                workbook.write(fos);
            }
            workbook.close();

            LoggerUtil.logInfo("Excel raporu başarıyla oluşturuldu: " + outputPath);
        } catch (Exception ex) {
            LoggerUtil.logError("Excel raporu oluşturulurken hata oluştu", ex);
        }
    }

    private static String getEnv() {
        String env = System.getProperty("data.env");
        if (env == null || env.isBlank()) {
            env = ConfigReader.get("data.env");
        }
        return (env != null && !env.isBlank()) ? env : "test";
    }

    private static String sanitizeSheetName(String name) {
        if (name == null) return "Sheet";
        String s = name.replaceAll("[:\\\\/?*\\[\\]]", "_");
        return s.length() > 31 ? s.substring(0, 31) : s;
    }

    // ---------------------- ÖZET (her domain alt alta) ----------------------

    private static void createSummarySheetMulti(Workbook wb, Map<String, JsonArray> domainToFeatures,
                                                CellStyle headerStyle, CellStyle numberStyle, String env) {
        Sheet sheet = wb.createSheet("Özet");
        int rowNum = 0;

        Row titleRow = sheet.createRow(rowNum++);
        titleRow.createCell(0).setCellValue("TEST RAPORU ÖZETİ");
        titleRow.getCell(0).setCellStyle(headerStyle);
        rowNum++;

        Row dateRow = sheet.createRow(rowNum++);
        dateRow.createCell(0).setCellValue("Rapor Tarihi:");
        dateRow.createCell(1).setCellValue(new SimpleDateFormat("dd/MM/yyyy HH:mm:ss").format(new Date()));
        rowNum++;

        for (Map.Entry<String, JsonArray> e : domainToFeatures.entrySet()) {
            String envLabel = e.getKey() + " " + env;
            Row envRow = sheet.createRow(rowNum++);
            envRow.createCell(0).setCellValue("Ortam:");
            envRow.createCell(1).setCellValue(envLabel);
            rowNum++;

            int total = 0, passed = 0, failed = 0, skipped = 0;
            long totalDuration = 0L;
            JsonArray features = e.getValue();

            for (JsonElement fEl : features) {
                JsonObject feature = fEl.getAsJsonObject();
                JsonArray elements = feature.getAsJsonArray("elements");
                if (elements == null) continue;
                for (JsonElement el : elements) {
                    JsonObject scenario = el.getAsJsonObject();
                    if (!"scenario".equals(scenario.get("type").getAsString())) continue;
                    total++;
                    JsonArray steps = scenario.getAsJsonArray("steps");
                    boolean hasFail = false, hasSkip = false;
                    if (steps != null) {
                        for (JsonElement stEl : steps) {
                            JsonObject step = stEl.getAsJsonObject();
                            JsonObject result = step.getAsJsonObject("result");
                            if (result == null || !result.has("status")) continue;
                            String status = result.get("status").getAsString();
                            if ("failed".equals(status)) hasFail = true;
                            else if ("skipped".equals(status)) hasSkip = true;
                            if (result.has("duration")) totalDuration += result.get("duration").getAsLong();
                        }
                    }
                    if (hasFail) failed++;
                    else if (hasSkip) skipped++;
                    else passed++;
                }
            }

            rowNum = writeSummaryRow(sheet, rowNum, "Toplam Senaryo", total, numberStyle);
            rowNum = writeSummaryRow(sheet, rowNum, "Başarılı", passed, numberStyle);
            rowNum = writeSummaryRow(sheet, rowNum, "Başarısız", failed, numberStyle);
            rowNum = writeSummaryRow(sheet, rowNum, "Atlanan", skipped, numberStyle);
            double sec = totalDuration / 1_000_000_000.0;
            Row dr = sheet.createRow(rowNum++);
            dr.createCell(0).setCellValue("Toplam Süre (sn)");
            Cell dc = dr.createCell(1);
            dc.setCellValue(sec);
            dc.setCellStyle(numberStyle);
            double rate = total == 0 ? 0.0 : (passed * 100.0 / total);
            Row rr = sheet.createRow(rowNum++);
            rr.createCell(0).setCellValue("Başarı Oranı (%)");
            Cell rc = rr.createCell(1);
            rc.setCellValue(rate);
            rc.setCellStyle(numberStyle);
            rowNum++;
        }

        sheet.autoSizeColumn(0);
        sheet.autoSizeColumn(1);
    }

    // ---------------------- ÖZET DETAY (Senaryo x Domain matris, ✓/✗) ----------------------

    private static void createSummaryDetailSheet(Workbook wb, Map<String, JsonArray> domainToFeatures,
                                                 CellStyle headerStyle, CellStyle passedStyle, CellStyle failedStyle) {
        Sheet sheet = wb.createSheet("Özet Detay");
        List<String> domains = new ArrayList<>(domainToFeatures.keySet());
        List<String> scenarioRows = new ArrayList<>();
        Map<String, Map<String, Boolean>> scenarioDomainPass = new LinkedHashMap<>();

        for (Map.Entry<String, JsonArray> e : domainToFeatures.entrySet()) {
            String domain = e.getKey();
            for (JsonElement fEl : e.getValue()) {
                JsonObject feature = fEl.getAsJsonObject();
                String fName = feature.has("name") ? feature.get("name").getAsString() : "Bilinmeyen";
                JsonArray elements = feature.getAsJsonArray("elements");
                if (elements == null) continue;
                for (JsonElement el : elements) {
                    JsonObject scenario = el.getAsJsonObject();
                    if (!"scenario".equals(scenario.get("type").getAsString())) continue;
                    String sName = scenario.has("name") ? scenario.get("name").getAsString() : "Bilinmeyen Senaryo";
                    String rowKey = fName + " - " + sName;
                    if (!scenarioRows.contains(rowKey)) {
                        scenarioRows.add(rowKey);
                    }
                    Map<String, Boolean> domainPass = scenarioDomainPass.computeIfAbsent(rowKey, k -> new LinkedHashMap<>());
                    boolean passed = true;
                    JsonArray steps = scenario.getAsJsonArray("steps");
                    if (steps != null) {
                        for (JsonElement stEl : steps) {
                            JsonObject step = stEl.getAsJsonObject();
                            JsonObject res = step.has("result") ? step.getAsJsonObject("result") : null;
                            if (res != null && res.has("status")) {
                                String st = res.get("status").getAsString();
                                if ("failed".equals(st) || "skipped".equals(st)) {
                                    passed = false;
                                    break;
                                }
                            }
                        }
                    }
                    domainPass.put(domain, passed);
                }
            }
        }

        Row header = sheet.createRow(0);
        header.createCell(0).setCellValue("Senaryo");
        header.getCell(0).setCellStyle(headerStyle);
        for (int i = 0; i < domains.size(); i++) {
            Cell c = header.createCell(i + 1);
            c.setCellValue(domains.get(i));
            c.setCellStyle(headerStyle);
        }

        int r = 1;
        for (String rowKey : scenarioRows) {
            Row row = sheet.createRow(r++);
            row.createCell(0).setCellValue(rowKey);
            Map<String, Boolean> dp = scenarioDomainPass.get(rowKey);
            for (int i = 0; i < domains.size(); i++) {
                String d = domains.get(i);
                Boolean pass = dp != null ? dp.get(d) : null;
                Cell cell = row.createCell(i + 1);
                if (pass != null) {
                    cell.setCellValue(pass ? "✓" : "✗");
                    cell.setCellStyle(pass ? passedStyle : failedStyle);
                }
            }
        }

        for (int i = 0; i <= domains.size(); i++) sheet.autoSizeColumn(i);
    }

    // ---------------------- SUMMARY ROW HELPER ----------------------

    private static int writeSummaryRow(Sheet sheet, int rowNum, String label, int value, CellStyle style) {
        Row row = sheet.createRow(rowNum);
        row.createCell(0).setCellValue(label);
        Cell v = row.createCell(1);
        v.setCellValue(value);
        v.setCellStyle(style);
        return rowNum + 1;
    }

    // ---------------------- DETAIL SHEET ----------------------

    private static void createDetailSheet(Workbook wb, JsonArray features,
                                          CellStyle headerStyle, CellStyle passedStyle,
                                          CellStyle failedStyle, CellStyle skippedStyle,
                                          CellStyle numberStyle, String envLabel, String sheetName) {
        Sheet sheet = wb.createSheet(sanitizeSheetName(sheetName));
        Row header = sheet.createRow(0);
        String[] cols = {"Feature", "Senaryo", "Durum", "Adım Sayısı", "Süre (sn)", "Hata Mesajı", "Ortam"};
        for (int i = 0; i < cols.length; i++) {
            Cell c = header.createCell(i);
            c.setCellValue(cols[i]);
            c.setCellStyle(headerStyle);
        }

        int rowNum = 1;

        for (JsonElement fEl : features) {
            JsonObject feature = fEl.getAsJsonObject();
            String featureName = feature.has("name") ? feature.get("name").getAsString() : "Bilinmeyen Feature";
            JsonArray elements = feature.getAsJsonArray("elements");
            if (elements == null) continue;

            for (JsonElement el : elements) {
                JsonObject scenario = el.getAsJsonObject();
                if (!"scenario".equals(scenario.get("type").getAsString())) continue;

                String scenarioName = scenario.has("name") ? scenario.get("name").getAsString() : "Bilinmeyen Senaryo";
                JsonArray steps = scenario.getAsJsonArray("steps");
                int stepCount = steps != null ? steps.size() : 0;

                String status = "PASSED";
                String errorMsg = "";
                long duration = 0L;

                if (steps != null) {
                    for (JsonElement stEl : steps) {
                        JsonObject step = stEl.getAsJsonObject();
                        JsonObject result = step.getAsJsonObject("result");
                        if (result == null || !result.has("status")) continue;
                        String stStatus = result.get("status").getAsString();
                        if ("failed".equals(stStatus)) {
                            status = "FAILED";
                            if (result.has("error_message")) {
                                errorMsg = result.get("error_message").getAsString();
                            }
                        } else if ("skipped".equals(stStatus) && !"FAILED".equals(status)) {
                            status = "SKIPPED";
                        }
                        if (result.has("duration")) {
                            duration += result.get("duration").getAsLong();
                        }
                    }
                }

                Row row = sheet.createRow(rowNum++);
                row.createCell(0).setCellValue(featureName);
                row.createCell(1).setCellValue(scenarioName);

                Cell statusCell = row.createCell(2);
                statusCell.setCellValue(toTurkishStatus(status));
                if ("PASSED".equals(status)) statusCell.setCellStyle(passedStyle);
                else if ("FAILED".equals(status)) statusCell.setCellStyle(failedStyle);
                else statusCell.setCellStyle(skippedStyle);

                row.createCell(3).setCellValue(stepCount);

                Cell durCell = row.createCell(4);
                durCell.setCellValue(duration / 1_000_000_000.0);
                durCell.setCellStyle(numberStyle);

                row.createCell(5).setCellValue(errorMsg);
                row.createCell(6).setCellValue(envLabel);
            }
        }

        for (int i = 0; i < cols.length; i++) {
            sheet.autoSizeColumn(i);
        }
    }

    // ---------------------- STEP DETAIL SHEETS ----------------------

    private static void createStepDetailSheets(Workbook wb, JsonArray features,
                                               CellStyle headerStyle, CellStyle passedStyle,
                                               CellStyle failedStyle, CellStyle skippedStyle,
                                               CellStyle numberStyle, String envLabel, String domain) {
        for (JsonElement fEl : features) {
            JsonObject feature = fEl.getAsJsonObject();
            String featureName = feature.has("name") ? feature.get("name").getAsString() : "Feature";
            String sheetName = sanitizeSheetName(featureName + " " + domain);

            Sheet sheet = wb.createSheet(sheetName);
            Row header = sheet.createRow(0);
            String[] cols = {"Ortam", "Adım Sırası", "Senaryo İsmi", "Adım Sonucu", "Durum", "Süre (sn)", "Adım Açıklaması (Teknik Kısım)", "Hata Mesajı (Teknik Kısım)"};
            for (int i = 0; i < cols.length; i++) {
                Cell c = header.createCell(i);
                c.setCellValue(cols[i]);
                c.setCellStyle(headerStyle);
            }

            int rowNum = 1;

            JsonArray elements = feature.getAsJsonArray("elements");
            if (elements == null) continue;

            // Background (giriş) elementini bul – her senaryodan önce tekrarlanacak
            JsonObject backgroundElement = null;
            String backgroundLabel = "login";
            for (JsonElement el : elements) {
                JsonObject element = el.getAsJsonObject();
                if ("background".equals(element.get("type").getAsString())) {
                    backgroundElement = element;
                    backgroundLabel = element.has("name") && !element.get("name").isJsonNull()
                            ? element.get("name").getAsString() : "login";
                    break;
                }
            }

            // Her senaryo için: önce giriş adımları, sonra senaryo adımları, sonra boş satır
            for (JsonElement el : elements) {
                JsonObject scenario = el.getAsJsonObject();
                if (!"scenario".equals(scenario.get("type").getAsString())) continue;

                // 1) Bu senaryoya ait giriş (background) adımlarını yaz
                if (backgroundElement != null) {
                    JsonArray bgSteps = backgroundElement.getAsJsonArray("steps");
                    if (bgSteps != null) {
                        rowNum = writeStepsToSheet(sheet, rowNum, backgroundLabel, bgSteps,
                                headerStyle, passedStyle, failedStyle, skippedStyle, numberStyle, envLabel);
                    }
                }

                // 2) Senaryonun kendi adımlarını yaz
                String scenarioName = scenario.has("name") ? scenario.get("name").getAsString() : "Bilinmeyen Senaryo";
                JsonArray steps = scenario.getAsJsonArray("steps");
                if (steps != null) {
                    rowNum = writeStepsToSheet(sheet, rowNum, scenarioName, steps,
                            headerStyle, passedStyle, failedStyle, skippedStyle, numberStyle, envLabel);
                }

                rowNum++; // senaryo bloğundan sonra boş satır
            }

            for (int i = 0; i < cols.length; i++) {
                sheet.autoSizeColumn(i);
            }
        }
    }

    /** Verilen adımları sayfaya yazar; güncel satır numarasını döndürür. */
    private static int writeStepsToSheet(Sheet sheet, int rowNum, String scenarioLabel, JsonArray steps,
                                         CellStyle headerStyle, CellStyle passedStyle, CellStyle failedStyle,
                                         CellStyle skippedStyle, CellStyle numberStyle, String envLabel) {
        int index = 1;
        for (JsonElement stEl : steps) {
            JsonObject step = stEl.getAsJsonObject();
            String stepName = step.has("name") ? step.get("name").getAsString() : "";

            StepInfo info = extractStepInfo(step, stepName);

            Row row = sheet.createRow(rowNum++);
            // 1. Ortam, 2. Adım Sırası, 3. Senaryo İsmi, 4. Adım Sonucu, 5. Durum, 6. Süre, 7. Adım Açıklaması (Teknik Kısım), 8. Hata Mesajı (Teknik Kısım)
            row.createCell(0).setCellValue(envLabel);
            row.createCell(1).setCellValue(index++);
            row.createCell(2).setCellValue(scenarioLabel);
            String stepResult = info.description != null ? info.description : "";
            row.createCell(3).setCellValue(stepResult);

            Cell statusCell = row.createCell(4);
            statusCell.setCellValue(toTurkishStatus(info.status));
            if ("PASSED".equals(info.status)) statusCell.setCellStyle(passedStyle);
            else if ("FAILED".equals(info.status)) statusCell.setCellStyle(failedStyle);
            else statusCell.setCellStyle(skippedStyle);

            Cell durCell = row.createCell(5);
            durCell.setCellValue(info.durationSeconds);
            durCell.setCellStyle(numberStyle);

            row.createCell(6).setCellValue(stepName);
            row.createCell(7).setCellValue(info.errorMessage);
        }
        return rowNum;
    }

    // ---------------------- STEP INFO EXTRACTION ----------------------

    private static class StepInfo {
        String status = "PASSED";
        String description = "";
        String errorMessage = "";
        double durationSeconds = 0.0;
    }

    private static StepInfo extractStepInfo(JsonObject stepObj, String stepName) {
        StepInfo info = new StepInfo();

        if (stepObj.has("result")) {
            JsonObject result = stepObj.getAsJsonObject("result");
            if (result.has("status")) {
                String raw = result.get("status").getAsString();
                info.status = raw != null ? raw.trim().toUpperCase(Locale.ENGLISH) : "SKIPPED";
            } else {
                info.status = "SKIPPED";
            }
            if (result.has("duration")) {
                info.durationSeconds = result.get("duration").getAsLong() / 1_000_000_000.0;
            }
            if (result.has("error_message")) {
                info.errorMessage = result.get("error_message").getAsString();
            }
        } else {
            // Cucumber Java'da bazen atlanan adımlarda result yok (önceki adım fail olunca)
            info.status = "SKIPPED";
        }

        String resultAttachment = null;
        String errorAttachment = null;

        if (stepObj.has("embeddings")) {
            JsonArray embeddings = stepObj.getAsJsonArray("embeddings");
            for (JsonElement emb : embeddings) {
                JsonObject embedding = emb.getAsJsonObject();
                if (!embedding.has("mime_type") || !embedding.has("data")) continue;
                if (!"text/plain".equals(embedding.get("mime_type").getAsString())) continue;

                String data = embedding.get("data").getAsString();
                if (data != null) data = data.trim();
                String decoded;
                try {
                    byte[] bytes = java.util.Base64.getDecoder().decode(data);
                    decoded = new String(bytes, java.nio.charset.StandardCharsets.UTF_8);
                } catch (Exception e) {
                    decoded = data != null ? data : "";
                }

                String name = embedding.has("name") && !embedding.get("name").isJsonNull()
                        ? embedding.get("name").getAsString() : "";
                if (name != null) name = name.trim();
                if (name != null && name.contains("Adım Sonucu")) {
                    resultAttachment = decoded;
                } else if (name != null && name.contains("Adım Hatası")) {
                    errorAttachment = decoded;
                }
            }
        }

        // Adım Sonucu sütunu: StepReporter.reportStepSuccess / reportStepError ile gönderilen mesajlar.
        // Başarısız: embedding "Adım Hatası" veya scenario.log → output; metoddan gelen "Hata: ..." kısmı alınır.
        if ("FAILED".equals(info.status)) {
            String errorText = errorAttachment;
            if (errorText != null) {
                // output'ta: "❌ ADIM HATALI: ...\n   Hata: 'X' adlı elemana tıklanamadı. ...\n   Hata Tipi: ..."
                // Sadece "Hata: " sonrası ilk satır = metoddan reportStepError'a gönderilen errorMessage
                int idx = errorText.indexOf("Hata: ");
                if (idx >= 0) {
                    String afterHata = errorText.substring(idx + 6).trim();
                    int firstNewline = afterHata.indexOf('\n');
                    info.description = firstNewline >= 0 ? afterHata.substring(0, firstNewline).trim() : afterHata;
                } else {
                    info.description = errorText.trim();
                }
                // Hata Mesajı sütununda gerçek exception (result.error_message) kalır; burada sadece Adım Sonucu (description) doldurulur.
            }
        } else if (resultAttachment != null) {
            // Başarılı: metoddan StepReporter.reportStepSuccess(stepDescription, successDetails) ile
            // gönderilen Türkçe mesaj (örn: "'X' adlı alanın içeriği başarıyla temizlendi.")
            // Format: "✅ BAŞARILI\n" + stepDescription + "\n" + successDetails (successDetails = Excel'e yazılacak)
            String[] lines = resultAttachment.split("\\r?\\n");
            if (lines.length >= 3) {
                // successDetails 3. satırdan itibaren (birden fazla satır olabilir)
                StringBuilder sb = new StringBuilder();
                for (int i = 2; i < lines.length; i++) {
                    if (i > 2) sb.append("\n");
                    sb.append(lines[i] != null ? lines[i] : "");
                }
                info.description = sb.toString().trim();
            } else if (lines.length == 2) {
                info.description = lines[1] != null ? lines[1].trim() : "";
            } else {
                info.description = resultAttachment != null ? resultAttachment.trim() : "";
            }
            // Metoddan StepReporter'a gönderilen mesaj aynen yazılır.
        }
        // Adım Sonucu sütununa sadece metoddan StepReporter'a gönderilen mesaj yazılır; yedek metin eklenmez.
        return info;
    }

    private static String createFriendlyStepDescription(String stepName) {
        if (stepName == null || stepName.isEmpty()) return "";
        String lower = stepName.toLowerCase();
        String elementKey = extractElementKeyFromStep(stepName);
        String value = extractValueFromStep(stepName);
        if (lower.contains("open the application") || lower.contains("open application")) {
            if (elementKey != null && !elementKey.isEmpty()) return "Uygulama açılıyor (Config'den: " + elementKey + ")";
            return "Uygulama açılıyor (Config'den)";
        }
        if (lower.contains("click on")) {
            if (elementKey != null && !elementKey.isEmpty()) return "'" + elementKey + "' adlı butona/elemana tıklanıyor";
            return "Butona/elemana tıklanıyor";
        }
        if (lower.contains("enter") && lower.contains("into the input")) {
            if (elementKey != null && !elementKey.isEmpty()) {
                String msg = "'" + elementKey + "' adlı alana metin yazılıyor";
                if (value != null && !value.isEmpty()) msg += " (Yazılan: " + value + ")";
                return msg;
            }
            return "Alana metin yazılıyor";
        }
        if (lower.contains("don't see element") || lower.contains("dont see element")) {
            if (elementKey != null && !elementKey.isEmpty()) return "'" + elementKey + "' adlı elemanın sayfada olmadığı kontrol ediliyor";
            return "Elemanın sayfada olmadığı kontrol ediliyor";
        }
        if (lower.contains("see the element")) {
            if (elementKey != null && !elementKey.isEmpty()) return "'" + elementKey + "' adlı elemanın sayfada görünür olduğu kontrol ediliyor";
            return "Elemanın sayfada görünür olduğu kontrol ediliyor";
        }
        if (lower.contains("clear") || lower.contains("temizle")) {
            if (elementKey != null && !elementKey.isEmpty()) return "'" + elementKey + "' adlı alanın içeriği temizleniyor";
            return "Alanın içeriği temizleniyor";
        }
        return stepName != null ? stepName : "";
    }

    private static String extractValueFromStep(String stepName) {
        if (stepName == null) return "";
        String lower = stepName.toLowerCase();
        if (lower.contains("verify element") && lower.contains("text is")) {
            int idx = lower.indexOf("text is");
            if (idx != -1) {
                int d = stepName.indexOf('"', idx);
                int s = stepName.indexOf('\'', idx);
                if (d != -1 && (s == -1 || d < s)) {
                    int e = stepName.indexOf('"', d + 1);
                    if (e != -1) return stepName.substring(d + 1, e);
                } else if (s != -1) {
                    int e = stepName.indexOf('\'', s + 1);
                    if (e != -1) return stepName.substring(s + 1, e);
                }
            }
        }
        String[] parts = stepName.split("\"");
        if (parts.length >= 4) return parts[3];
        if (parts.length >= 2) return parts[1];
        return "";
    }

    // Step name'den element key'i çıkar
    private static String extractElementKeyFromStep(String stepName) {
        if (stepName == null) return "";
        String lower = stepName.toLowerCase();

        if (lower.contains("into the input")) {
            int idx = lower.indexOf("into the input");
            if (idx != -1) {
                int d = stepName.indexOf('"', idx);
                int s = stepName.indexOf('\'', idx);
                if (d != -1 && (s == -1 || d < s)) {
                    int e = stepName.indexOf('"', d + 1);
                    if (e != -1) return stepName.substring(d + 1, e);
                } else if (s != -1) {
                    int e = stepName.indexOf('\'', s + 1);
                    if (e != -1) return stepName.substring(s + 1, e);
                }
            }
        } else if (lower.contains("see element") || lower.contains("see the element")) {
            int elementIndex = lower.indexOf("element");
            if (elementIndex != -1) {
                int after = elementIndex + "element".length();
                int d = stepName.indexOf('"', after);
                int s = stepName.indexOf('\'', after);
                if (d != -1 && (s == -1 || d < s)) {
                    int e = stepName.indexOf('"', d + 1);
                    if (e != -1) return stepName.substring(d + 1, e);
                } else if (s != -1) {
                    int e = stepName.indexOf('\'', s + 1);
                    if (e != -1) return stepName.substring(s + 1, e);
                }
            }
        } else {
            int d = stepName.indexOf('"');
            int s = stepName.indexOf('\'');
            if (s != -1 && s < 10) {
                String before = stepName.substring(0, s).toLowerCase();
                if (before.contains("don") || before.contains("dont")) {
                    s = stepName.indexOf('\'', s + 1);
                }
            }
            if (d != -1 && (s == -1 || d < s)) {
                int e = stepName.indexOf('"', d + 1);
                if (e != -1) return stepName.substring(d + 1, e);
            } else if (s != -1) {
                int e = stepName.indexOf('\'', s + 1);
                if (e != -1) return stepName.substring(s + 1, e);
            }
        }
        return "";
    }

    // Generic mesajlara element adını yerleştir
    private static String ensureElementNameInMessage(String message, String stepName, String elementKey) {
        if (message == null || message.isEmpty() || elementKey == null || elementKey.isEmpty()) return message;
        if (message.contains("'" + elementKey + "'")) return message;

        String lower = message.toLowerCase();
        if (lower.contains("butona/elemana tıklanıyor")) {
            return "'" + elementKey + "' adlı butona/elemana tıklanıyor";
        }
        if (lower.contains("alana metin yazılıyor")) {
            return "'" + elementKey + "' adlı alana metin yazılıyor";
        }
        if (lower.contains("alanın içeriği temizleniyor")) {
            return "'" + elementKey + "' adlı alanın içeriği temizleniyor";
        }
        if (lower.contains("elemanın metni doğrulanıyor")) {
            return "'" + elementKey + "' adlı elemanın metni doğrulanıyor";
        }
        if (lower.contains("elemanın sayfada olmadığı kontrol ediliyor")) {
            return "'" + elementKey + "' adlı elemanın sayfada olmadığı kontrol ediliyor";
        }
        if (lower.contains("elemanın sayfada görünür olduğu kontrol ediliyor")) {
            return "'" + elementKey + "' adlı elemanın sayfada görünür olduğu kontrol ediliyor";
        }
        if (lower.contains("elemanın değeri kontrol ediliyor")) {
            return "'" + elementKey + "' adlı elemanın değeri kontrol ediliyor";
        }
        return message;
    }

    // ---------------------- STYLES & HELPERS ----------------------

    private static CellStyle createHeaderStyle(Workbook wb) {
        CellStyle style = wb.createCellStyle();
        Font font = wb.createFont();
        font.setBold(true);
        font.setColor(IndexedColors.WHITE.getIndex());
        style.setFont(font);
        style.setFillForegroundColor(IndexedColors.DARK_BLUE.getIndex());
        style.setFillPattern(FillPatternType.SOLID_FOREGROUND);
        style.setAlignment(HorizontalAlignment.CENTER);
        style.setVerticalAlignment(VerticalAlignment.CENTER);
        style.setBorderBottom(BorderStyle.THIN);
        style.setBorderTop(BorderStyle.THIN);
        style.setBorderLeft(BorderStyle.THIN);
        style.setBorderRight(BorderStyle.THIN);
        return style;
    }

    private static CellStyle createStatusStyle(Workbook wb, short color) {
        CellStyle style = wb.createCellStyle();
        Font font = wb.createFont();
        font.setBold(true);
        font.setColor(IndexedColors.WHITE.getIndex());
        style.setFont(font);
        style.setFillForegroundColor(color);
        style.setFillPattern(FillPatternType.SOLID_FOREGROUND);
        style.setAlignment(HorizontalAlignment.CENTER);
        return style;
    }

    private static CellStyle createNumberStyle(Workbook wb) {
        CellStyle style = wb.createCellStyle();
        DataFormat df = wb.createDataFormat();
        style.setDataFormat(df.getFormat("0.00"));
        return style;
    }

    private static String toTurkishStatus(String status) {
        if (status == null) return "";
        switch (status.toUpperCase()) {
            case "PASSED":
                return "BAŞARILI";
            case "FAILED":
                return "BAŞARISIZ";
            case "SKIPPED":
                return "ATLANDI";
            case "PENDING":
                return "BEKLENİYOR";
            default:
                return status;
        }
    }

    private static String getEnvironmentLabel() {
        String domain = System.getProperty("data.domain");
        if (domain == null || domain.isBlank()) {
            String cfg = ConfigReader.get("data.domain");
            if (cfg != null && !cfg.isBlank()) domain = cfg;
        }
        if (domain == null || domain.isBlank()) domain = "girit";

        String env = System.getProperty("data.env");
        if (env == null || env.isBlank()) {
            String cfg = ConfigReader.get("data.env");
            if (cfg != null && !cfg.isBlank()) env = cfg;
        }
        if (env == null || env.isBlank()) env = "test";

        return domain + " " + env;
    }
}

