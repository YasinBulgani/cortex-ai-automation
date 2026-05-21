package utilities;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * LoggerUtil:
 * Framework genelinde loglama yapmak için kullanılır.
 * Test adımlarında ve framework seviyesinde bilgi / hata logları üretir.
 */
public class LoggerUtil {

    private static final Logger logger = LoggerFactory.getLogger(LoggerUtil.class);

    /**
     * Bilgilendirme logu
     */
    public static void logInfo(String message) {
        logger.info(message);
    }

    /**
     * Hata logu
     */
    public static void logError(String message, Throwable throwable) {
        if (throwable != null) {
            logger.error(message, throwable);
        } else {
            logger.error(message);
        }
    }
}
