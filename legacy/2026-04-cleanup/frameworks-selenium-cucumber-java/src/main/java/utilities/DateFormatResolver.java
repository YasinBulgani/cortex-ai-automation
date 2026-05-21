package utilities;

import java.time.DayOfWeek;
import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.util.LinkedHashMap;
import java.util.Locale;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Input değerlerinde "dateformatnow" ile başlayan formatları bugünün tarihine çevirir.
 * Genişletilebilir: hem isimli formatlar hem ham pattern kullanılabilir.
 *
 * Örnek çıktılar (bugün 20.02.2026 ise):
 * <ul>
 *   <li>dateformatnow dd/MM/yyyy           → "20/02/2026"
 *   <li>dateformatnow dd MMMM yyyy        → "20 Şubat 2026"
 *   <li>dateformatnow dd/MM/yyyy - dd/MM/yyyy → "20/02/2026 - 20/02/2026"
 *   <li>dateformatnow dd/MM/yyyy - dd/MM/yyyy +2 → "20/02/2026 - 22/02/2026" (2. tarih bugün+2 gün)
 *   <li>dateformatnow:short               → "20/02/2026" (dd/MM/yyyy)
 *   <li>dateformatnow:long                → "20 Şubat 2026" (dd MMMM yyyy, Türkçe ay)
 *   <li>dateformatnow:range               → "20/02/2026 - 20/02/2026"
 *   <li>dateformatnow:range +3            → "20/02/2026 - 23/02/2026"
 * </ul>
 */
public final class DateFormatResolver {

    private static final String PREFIX = "dateformatnow";
    private static final String PREFIX_COLON = "dateformatnow:";
    /** Range pattern sonundaki +N (örn. " +2") için. */
    private static final Pattern RANGE_OFFSET_SUFFIX = Pattern.compile(" \\+(\\d+)$");
    private static final String RANGE_SEPARATOR = " - ";

    /** İsimli formatlar – genişletmek için bu map'e ekle. */
    private static final Map<String, String> NAMED_FORMATS = new LinkedHashMap<>();

    static {
        // 20/02/2026 formatı
        NAMED_FORMATS.put("short", "dd/MM/yyyy");
        // 22 Ocak 2026 formatı (Türkçe ay adı)
        NAMED_FORMATS.put("long", "dd MMMM yyyy");
        NAMED_FORMATS.put("range", "dd/MM/yyyy - dd/MM/yyyy");
        // Yeni formatlar buraya eklenebilir:
        // NAMED_FORMATS.put("iso", "yyyy-MM-dd");
    }

    private DateFormatResolver() {
    }

    /**
     * Verilen değer "dateformatnow" veya "dateformatnow:..." ile başlıyorsa
     * bugünün tarihini ilgili formatta string olarak döner; değilse null döner.
     *
     * @param value feature'dan gelen ham string (örn. "dateformatnow dd/MM/yyyy - dd/MM/yyyy")
     * @return formatlanmış tarih string'i veya null (değer dateformatnow değilse)
     */
    public static String resolve(String value) {
        if (value == null || value.isBlank()) {
            return null;
        }
        String trimmed = value.trim();
        if (!trimmed.toLowerCase().startsWith(PREFIX)) {
            return null;
        }

        String pattern = null;
        if (trimmed.toLowerCase().startsWith(PREFIX_COLON)) {
            String afterColon = trimmed.substring(PREFIX_COLON.length()).trim();
            if (afterColon.isEmpty()) {
                throw new IllegalArgumentException("dateformatnow: kullanımında format adı boş olamaz. Örnek: dateformatnow:short");
            }
            // "range +2" → name="range", pattern = "dd/MM/yyyy - dd/MM/yyyy +2" gibi işlenecek
            String name = afterColon;
            int plusIdx = afterColon.indexOf(" +");
            if (plusIdx > 0) {
                String offsetPart = afterColon.substring(plusIdx).trim();
                if (offsetPart.matches("\\+\\d+")) {
                    name = afterColon.substring(0, plusIdx).trim();
                    String base = NAMED_FORMATS.get(name.toLowerCase());
                    if (base != null) {
                        pattern = base + " " + offsetPart;
                    }
                }
            }
            if (pattern == null) {
                pattern = NAMED_FORMATS.get(name.toLowerCase());
            }
            if (pattern == null) {
                throw new IllegalArgumentException(
                        "Bilinmeyen tarih formatı: '" + name + "'. Tanımlı formatlar: " + NAMED_FORMATS.keySet());
            }
        } else {
            pattern = trimmed.substring(PREFIX.length()).trim();
            if (pattern.isEmpty()) {
                throw new IllegalArgumentException("dateformatnow kullanımında format pattern boş olamaz. Örnek: dateformatnow dd/MM/yyyy");
            }
        }

        Locale locale = Locale.forLanguageTag("tr");
        // Pazar ise bir sonraki gün (pazartesi) kullanılır; formatlar aynı kalır
        LocalDate baseDate = LocalDate.now();
        if (baseDate.getDayOfWeek() == DayOfWeek.SUNDAY) {
            baseDate = baseDate.plusDays(1);
        }

        // Sonundaki " +N" varsa ikili range: 1. tarih baseDate, 2. tarih baseDate+N gün
        Matcher offsetMatcher = RANGE_OFFSET_SUFFIX.matcher(pattern);
        if (offsetMatcher.find()) {
            int offsetDays = Integer.parseInt(offsetMatcher.group(1));
            String basePattern = pattern.substring(0, offsetMatcher.start()).trim();
            if (basePattern.contains(RANGE_SEPARATOR)) {
                String[] parts = basePattern.split(RANGE_SEPARATOR, 2);
                if (parts.length == 2) {
                    String pattern1 = parts[0].trim();
                    String pattern2 = parts[1].trim();
                    try {
                        DateTimeFormatter fmt1 = DateTimeFormatter.ofPattern(pattern1, locale);
                        DateTimeFormatter fmt2 = DateTimeFormatter.ofPattern(pattern2, locale);
                        LocalDate date1 = baseDate;
                        LocalDate date2 = baseDate.plusDays(offsetDays);
                        return date1.format(fmt1) + RANGE_SEPARATOR + date2.format(fmt2);
                    } catch (Exception e) {
                        throw new IllegalArgumentException("Geçersiz tarih formatı (range +N): '" + basePattern + "'. " + e.getMessage(), e);
                    }
                }
            }
        }

        try {
            DateTimeFormatter formatter = DateTimeFormatter.ofPattern(pattern, locale);
            return baseDate.format(formatter);
        } catch (Exception e) {
            throw new IllegalArgumentException("Geçersiz tarih formatı: '" + pattern + "'. " + e.getMessage(), e);
        }
    }

    /**
     * Değerin dateformatnow ile başlayıp başlamadığını kontrol eder.
     */
    public static boolean isDateFormatNow(String value) {
        return value != null && value.trim().toLowerCase().startsWith(PREFIX);
    }

    /**
     * Yeni isimli format eklemek için (test veya genişletme amaçlı).
     *
     * @param name    format adı (örn. "iso")
     * @param pattern DateTimeFormatter pattern (örn. "yyyy-MM-dd")
     */
    public static void registerNamedFormat(String name, String pattern) {
        if (name != null && !name.isBlank() && pattern != null && !pattern.isBlank()) {
            NAMED_FORMATS.put(name.toLowerCase().trim(), pattern.trim());
        }
    }
}
