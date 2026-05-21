package utilities;

import java.util.HashMap;
import java.util.Map;

/**
 * ScenarioContext:
 * Aynı senaryo içinde adımlar arası key-value saklama.
 * Her senaryo kendi map'ine sahiptir; senaryo bitince temizlenir (Hooks @After).
 * ThreadLocal kullanır; senaryo bazlı izolasyon sağlar.
 */
public class ScenarioContext {

    private static final ThreadLocal<Map<String, String>> CONTEXT = ThreadLocal.withInitial(HashMap::new);

    /**
     * Key ile değer saklar. Aynı key tekrar kullanılırsa üzerine yazar.
     */
    public static void put(String key, String value) {
        if (key == null || key.isBlank()) {
            throw new IllegalArgumentException("ScenarioContext key boş olamaz.");
        }
        CONTEXT.get().put(key.trim(), value != null ? value : "");
    }

    /**
     * Key ile saklanan değeri döner. Key yoksa RuntimeException fırlatır.
     */
    public static String get(String key) {
        Map<String, String> map = CONTEXT.get();
        if (!map.containsKey(key)) {
            throw new RuntimeException("ScenarioContext'te '" + key + "' anahtarı bulunamadı. Önce bu senaryoda bir adımda değer saklanmış olmalı.");
        }
        return map.get(key);
    }

    /**
     * Key'in var olup olmadığını kontrol eder.
     */
    public static boolean containsKey(String key) {
        return CONTEXT.get().containsKey(key);
    }

    /**
     * Senaryo sonunda çağrılır (Hooks @After). Bu senaryoya ait tüm veriyi temizler.
     */
    public static void clear() {
        CONTEXT.remove();
    }
}
