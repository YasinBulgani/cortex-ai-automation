package utilities;

import io.cucumber.java.Scenario;

import java.nio.charset.StandardCharsets;

/**
 * StepReporter:
 * Feature dosyalarındaki her adım için Cucumber ve Allure raporlarına
 * okunabilir Türkçe açıklamalar ekler.
 */
public class StepReporter {

    // Thread-local Scenario saklamak için
    private static final ThreadLocal<Scenario> scenarioThreadLocal = new ThreadLocal<>();

    /** Scenario'yu thread-local'a set eder (Hooks'tan çağrılır) */
    public static void setScenario(Scenario scenario) {
        scenarioThreadLocal.set(scenario);
    }

    /** Thread-local'dan Scenario'yu alır */
    private static Scenario getScenario() {
        return scenarioThreadLocal.get();
    }

    /** Thread-local'ı temizler (Hooks'tan çağrılır) */
    public static void clearScenario() {
        scenarioThreadLocal.remove();
    }

    /**
     * Allure'a attachment ekler (reflection ile, optional)
     * Allure bağımlılığı test scope'unda olduğu için reflection kullanıyoruz.
     */
    private static void addAllureAttachment(String name, String type, String content) {
        try {
            Class<?> allureClass = Class.forName("io.qameta.allure.Allure");
            java.lang.reflect.Method addAttachmentMethod =
                    allureClass.getMethod("addAttachment", String.class, String.class, String.class);
            addAttachmentMethod.invoke(null, name, type, content);
        } catch (Exception e) {
            // Allure yoksa sessiz geç
        }
    }

    /**
     * Adımın başladığını raporlara yazar.
     */
    public static void reportStepStart(String stepDescription, String details) {
        String message = "📋 ADIM BAŞLADI: " + stepDescription;
        if (details != null && !details.isEmpty()) {
            message += "\n   Detay: " + details;
        }

        // Allure'da sadece "Adım Açıklaması" (scenario.log/attach kaldırıldı, text output tekrarı yok)
        addAllureAttachment(
                "Adım Açıklaması",
                "text/plain",
                stepDescription + (details != null && !details.isEmpty() ? "\n" + details : "")
        );

        LoggerUtil.logInfo(message);
    }

    /**
     * Adımın başarıyla tamamlandığını raporlara yazar.
     */
    public static void reportStepSuccess(String stepDescription, String successDetails) {
        String message = "✅ ADIM BAŞARILI: " + stepDescription;
        if (successDetails != null && !successDetails.isEmpty()) {
            message += "\n   Sonuç: " + successDetails;
        }

        // Adım Sonucu: sadece scenario.attach → Cucumber JSON (Excel "Adım Sonucu" sütunu) + Allure'da tek gösterim (plugin ile)
        StringBuilder sb = new StringBuilder();
        sb.append("✅ BAŞARILI\n");
        sb.append(stepDescription != null ? stepDescription : "");
        if (successDetails != null && !successDetails.isEmpty()) {
            sb.append("\n").append(successDetails);
        }

        Scenario scenario = getScenario();
        if (scenario != null) {
            scenario.attach(sb.toString().getBytes(StandardCharsets.UTF_8), "text/plain", "Adım Sonucu");
        }
        LoggerUtil.logInfo(message);
    }

    /**
     * Adımın hata aldığını raporlara yazar.
     */
    public static void reportStepError(String stepDescription,
                                       String errorMessage,
                                       Throwable exception) {
        String message = "❌ ADIM HATALI: " + stepDescription;
        message += "\n   Hata: " + errorMessage;
        if (exception != null) {
            message += "\n   Hata Tipi: " + exception.getClass().getSimpleName();
            if (exception.getMessage() != null) {
                message += "\n   Hata Detayı: " + exception.getMessage();
            }
        }

        // Adım Hatası: sadece scenario.attach → Cucumber JSON (Excel "Adım Sonucu" sütunu) + Allure'da tek gösterim (plugin ile)
        StringBuilder sb = new StringBuilder();
        sb.append("❌ HATA\n");
        sb.append(stepDescription != null ? stepDescription : "");
        sb.append("\nHata: ").append(errorMessage != null ? errorMessage : "");

        if (exception != null && exception.getMessage() != null) {
            String exMsg = exception.getMessage();
            if (!exMsg.equals(errorMessage) && !exMsg.contains(errorMessage)) {
                sb.append("\n").append(exMsg);
            }
        }

        Scenario scenario = getScenario();
        if (scenario != null) {
            scenario.attach(sb.toString().getBytes(StandardCharsets.UTF_8), "text/plain", "Adım Hatası");
        }
        LoggerUtil.logError(message, exception);
    }

    /**
     * Genel bilgi mesajı.
     */
    public static void reportStepInfo(String infoMessage) {
        String message = "ℹ️ BİLGİ: " + infoMessage;

        Scenario scenario = getScenario();
        if (scenario != null) {
            scenario.log(message);
        }

        addAllureAttachment("Adım Bilgisi", "text/plain", infoMessage);
        LoggerUtil.logInfo(message);
    }

    /**
     * Adım için Türkçe, kullanıcı dostu açıklama üretir.
     */
    public static String createUserFriendlyDescription(String action,
                                                       String elementKey,
                                                       String additionalInfo) {
        StringBuilder desc = new StringBuilder();
        if (elementKey == null) elementKey = "";

        switch (action.toLowerCase()) {
            case "click":
            case "tıklama":
                desc.append("'").append(elementKey).append("' adlı butona/elemana tıklanıyor");
                break;
            case "enter":
            case "yazma":
                desc.append("'").append(elementKey).append("' adlı alana metin yazılıyor");
                if (additionalInfo != null) {
                    desc.append(" (Yazılan: ").append(additionalInfo).append(")");
                }
                break;
            case "clear":
            case "temizleme":
                desc.append("'").append(elementKey).append("' adlı alanın içeriği temizleniyor");
                break;
            case "verify":
            case "doğrulama":
                desc.append("'").append(elementKey).append("' adlı elemanın değeri kontrol ediliyor");
                if (additionalInfo != null) {
                    desc.append(" (Beklenen: ").append(additionalInfo).append(")");
                }
                break;
            case "upload":
            case "yükleme":
                desc.append("'").append(elementKey).append("' adlı alana dosya yükleniyor");
                if (additionalInfo != null) {
                    desc.append(" (Dosya: ").append(additionalInfo).append(")");
                }
                break;
            case "scroll":
            case "kaydırma":
                desc.append("Sayfa '").append(elementKey).append("' adlı elemana kadar kaydırılıyor");
                break;
            case "navigate":
            case "navigasyon":
                desc.append("Uygulama açılıyor");
                if (additionalInfo != null) {
                    desc.append(" (URL: ").append(additionalInfo).append(")");
                }
                break;
            case "key":
            case "tuş":
                desc.append("Klavyeden '").append(additionalInfo != null ? additionalInfo : elementKey)
                        .append("' tuşuna basılıyor");
                break;
            default:
                desc.append("'").append(elementKey).append("' adlı eleman üzerinde işlem yapılıyor");
                if (additionalInfo != null) {
                    desc.append(" (").append(additionalInfo).append(")");
                }
        }

        return desc.toString();
    }
}

