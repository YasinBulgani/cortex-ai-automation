package utils;

import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;

public class LoggerUtil {

    private static final Logger logger = LogManager.getLogger(LoggerUtil.class);
    private static boolean isFirstLog = true;

    static {
        logger.info("LoggerUtil initialized");
    }

    public static void logInfo(String message) {
        checkAndLogSeparator();
        logger.info(message);
    }

    public static void logError(String message) {
        checkAndLogSeparator();
        logger.error(message);
    }

    public static void logError(String message, Throwable t) {
        checkAndLogSeparator();
        logger.error(message, t);
    }

    public static void logWarn(String message) {
        checkAndLogSeparator();
        logger.warn(message);
    }

    public static void logDebug(String message) {
        checkAndLogSeparator();
        logger.debug(message);
    }

    private static void checkAndLogSeparator() {
        if (isFirstLog) {
            logger.info("----------- TEST STARTED -----------");
            isFirstLog = false;
        }
    }
}
