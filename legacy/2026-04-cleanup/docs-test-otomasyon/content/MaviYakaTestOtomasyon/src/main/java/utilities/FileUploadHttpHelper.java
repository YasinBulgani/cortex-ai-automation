package utilities;

import org.openqa.selenium.JavascriptExecutor;
import org.openqa.selenium.WebDriver;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Duration;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Tarayıcı cookie'leri ile /SystemGeneral/UploadTemp'e dosya yükler.
 * Sayfa plugin'i 200 dönse bile UI güncellemediğinde, test tarafında gerçek upload yapıp
 * dönen dosya ID'sini sayfaya enjekte etmek için kullanılır.
 */
public class FileUploadHttpHelper {

    private static final String UPLOAD_PATH = "/SystemGeneral/UploadTemp";
    private static final String BOUNDARY = "----WebKitFormBoundary" + Long.toHexString(System.currentTimeMillis());
    private static final Pattern GUID_PATTERN = Pattern.compile(
            "\"(?:tempFileGuid|TempFileGuid|fileId|FileId|id)\"\\s*:\\s*\"([^\"]+)\"",
            Pattern.CASE_INSENSITIVE);

    /**
     * Sayfadan componentId'yi bulur. Script içinde form id (EmployeeLeaveFiles_fileupload / EmployeeLeavePdfFiles_fileupload)
     * ile birlikte geçen componentId: 'uuid' regex ile alınır. Önce görünür alan (EmployeeLeaveFiles) denenir.
     */
    public static String getComponentIdFromPage(WebDriver driver) {
        try {
            String script =
                    "var scripts = document.getElementsByTagName('script'); " +
                    "var re = /componentId\\s*:\\s*'([a-f0-9-]{36})'/gi; " +
                    "for (var i = 0; i < scripts.length; i++) { " +
                    "  var t = scripts[i].innerHTML || ''; " +
                    "  if (t.indexOf('EmployeeLeaveFiles_fileupload') >= 0 && t.indexOf('componentId') >= 0) { var m = re.exec(t); if (m) return m[1]; } " +
                    "} " +
                    "re.lastIndex = 0; " +
                    "for (var j = 0; j < scripts.length; j++) { " +
                    "  var s = scripts[j].innerHTML || ''; " +
                    "  if (s.indexOf('_fileupload') >= 0 && s.indexOf('componentId') >= 0) { var n = re.exec(s); if (n) return n[1]; } " +
                    "} " +
                    "return null;";
            Object result = ((JavascriptExecutor) driver).executeScript(script);
            return result != null ? result.toString().trim() : null;
        } catch (Exception e) {
            LoggerUtil.logInfo("ComponentId sayfadan alınamadı: " + e.getMessage());
            return null;
        }
    }

    /**
     * Görünür (display:none olmayan) file upload formunun flag adını döner (örn. EmployeeLeaveFiles).
     */
    public static String getFlagCompNameFromPage(WebDriver driver) {
        try {
            String script =
                    "var forms = document.querySelectorAll('form[id$=\"_fileupload\"]'); " +
                    "for (var i = 0; i < forms.length; i++) { " +
                    "  var f = forms[i], el = f; " +
                    "  while (el) { if (window.getComputedStyle(el).display === 'none') break; el = el.parentElement; } " +
                    "  if (!el) return f.id.replace(/_fileupload$/, ''); " +
                    "} " +
                    "return 'EmployeeLeavePdfFiles';";
            Object result = ((JavascriptExecutor) driver).executeScript(script);
            return result != null ? result.toString().trim() : "EmployeeLeavePdfFiles";
        } catch (Exception e) {
            return "EmployeeLeavePdfFiles";
        }
    }

    /**
     * Tarayıcı cookie ve origin bilgisiyle UploadTemp'e POST atar.
     * @return 200 ise response body'den çıkarılan dosya GUID'ı, değilse null
     */
    public static String uploadWithBrowserSession(WebDriver driver, Path filePath) {
        if (!Files.isRegularFile(filePath)) {
            LoggerUtil.logInfo("Dosya bulunamadı: " + filePath);
            return null;
        }
        String componentId = getComponentIdFromPage(driver);
        if (componentId == null || componentId.isEmpty()) {
            LoggerUtil.logInfo("ComponentId bulunamadı, HTTP upload atlanıyor.");
            return null;
        }
        String flagCompName = getFlagCompNameFromPage(driver);

        String currentUrl = driver.getCurrentUrl();
        String baseUrl = getBaseUrl(currentUrl);
        if (baseUrl == null) {
            LoggerUtil.logInfo("Base URL çıkarılamadı: " + currentUrl);
            return null;
        }

        String cookieHeader = buildCookieHeader(driver);
        String fileName = filePath.getFileName().toString();

        try {
            byte[] fileBytes = Files.readAllBytes(filePath);
            byte[] body = buildMultipartBody(componentId, flagCompName, fileName, fileBytes);

            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(baseUrl + UPLOAD_PATH))
                    .timeout(Duration.ofSeconds(30))
                    .header("Accept", "application/json, text/javascript, */*; q=0.01")
                    .header("Content-Type", "multipart/form-data; boundary=" + BOUNDARY)
                    .header("Origin", baseUrl)
                    .header("Referer", currentUrl)
                    .header("X-Requested-With", "XMLHttpRequest")
                    .header("Cookie", cookieHeader)
                    .POST(HttpRequest.BodyPublishers.ofByteArray(body))
                    .build();

            HttpClient client = HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(15)).build();
            HttpResponse<String> response = client.send(request, HttpResponse.BodyHandlers.ofString(StandardCharsets.UTF_8));

            if (response.statusCode() != 200) {
                LoggerUtil.logInfo("UploadTemp HTTP " + response.statusCode() + ": " + response.body());
                return null;
            }

            String responseBody = response.body();
            String guid = extractGuidFromResponse(responseBody);
            if (guid != null) {
                LoggerUtil.logInfo("UploadTemp 200, dosya ID: " + guid);
            }
            return guid;
        } catch (Exception e) {
            LoggerUtil.logError("UploadTemp HTTP hatası", e);
            return null;
        }
    }

    private static String getBaseUrl(String url) {
        try {
            URI uri = URI.create(url);
            return uri.getScheme() + "://" + uri.getHost() + (uri.getPort() > 0 && uri.getPort() != (uri.getScheme().equals("https") ? 443 : 80) ? ":" + uri.getPort() : "");
        } catch (Exception e) {
            return null;
        }
    }

    private static String buildCookieHeader(WebDriver driver) {
        StringBuilder sb = new StringBuilder();
        driver.manage().getCookies().forEach(c -> {
            if (sb.length() > 0) sb.append("; ");
            sb.append(c.getName()).append("=").append(c.getValue());
        });
        return sb.toString();
    }

    private static byte[] buildMultipartBody(String componentId, String flagCompName, String fileName, byte[] fileBytes) {
        StringBuilder sb = new StringBuilder();
        sb.append("--").append(BOUNDARY).append("\r\n");
        sb.append("Content-Disposition: form-data; name=\"isFileDefault\"\r\n\r\nTrue\r\n");
        sb.append("--").append(BOUNDARY).append("\r\n");
        sb.append("Content-Disposition: form-data; name=\"flagCompName\"\r\n\r\n").append(flagCompName).append("\r\n");
        sb.append("--").append(BOUNDARY).append("\r\n");
        sb.append("Content-Disposition: form-data; name=\"componentId\"\r\n\r\n").append(componentId).append("\r\n");
        sb.append("--").append(BOUNDARY).append("\r\n");
        sb.append("Content-Disposition: form-data; name=\"files[]\"; filename=\"").append(fileName).append("\"\r\n");
        sb.append("Content-Type: application/pdf\r\n\r\n");

        byte[] header = sb.toString().getBytes(StandardCharsets.UTF_8);
        String footer = "\r\n--" + BOUNDARY + "--\r\n";
        byte[] footerBytes = footer.getBytes(StandardCharsets.UTF_8);

        byte[] result = new byte[header.length + fileBytes.length + footerBytes.length];
        System.arraycopy(header, 0, result, 0, header.length);
        System.arraycopy(fileBytes, 0, result, header.length, fileBytes.length);
        System.arraycopy(footerBytes, 0, result, header.length + fileBytes.length, footerBytes.length);
        return result;
    }

    private static String extractGuidFromResponse(String json) {
        if (json == null || json.isEmpty()) return null;
        Matcher m = GUID_PATTERN.matcher(json);
        return m.find() ? m.group(1) : null;
    }
}
