package utils;

import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;

import java.util.concurrent.atomic.AtomicBoolean;

/**
 * Thin wrapper around Log4j 2 that adds a one-time test-start separator on the first
 * log call and exposes a consistent API across the framework.
 *
 * <p>Key features:
 * <ul>
 *   <li>First log per JVM run emits a visible "TEST IS STARTED" separator so test
 *       output in CI logs is easy to locate.</li>
 *   <li>Overloaded {@link #logError(String, Throwable)} variant includes the stack
 *       trace; the single-arg overload logs the message only (no phantom Throwable arg).</li>
 *   <li>{@link #logWarn(String, Throwable)} mirrors the error pattern for recoverable
 *       issues that should not fail the test.</li>
 * </ul>
 *
 * <p>Thread safety: {@link java.util.concurrent.atomic.AtomicBoolean} guards the
 * first-log separator against duplicate emission in parallel runs.
 */
public class LoggerUtil {

    private static final Logger logger = LogManager.getLogger(LoggerUtil.class);
    // Thread-safe first-log flag; AtomicBoolean prevents race conditions in parallel execution.
    private static final AtomicBoolean isFirstLog = new AtomicBoolean(true);

    static {
        logger.info("LoggerUtil initialized.");
    }

    /** Logs {@code message} at INFO level, emitting a test-start separator on the very first call. */
    public static void logInfo(String message) {
        checkAndLogSeparator();
        logger.info(message);
    }

    /** Logs {@code message} at ERROR level (no stack trace). Use {@link #logError(String, Throwable)} to include one. */
    public static void logError(String message) {
        checkAndLogSeparator();
        logger.error(message);
    }

    /** Error log with a {@link Throwable} — includes full stack trace. */
    public static void logError(String message, Throwable t) {
        checkAndLogSeparator();
        logger.error(message, t);
    }

    /** Logs {@code message} at WARN level (no stack trace). */
    public static void logWarn(String message) {
        checkAndLogSeparator();
        logger.warn(message);
    }

    /** Logs {@code message} at WARN level with a full stack trace from {@code t}. */
    public static void logWarn(String message, Throwable t) {
        checkAndLogSeparator();
        logger.warn(message, t);
    }

    /** Logs {@code message} at DEBUG level. */
    public static void logDebug(String message) {
        checkAndLogSeparator();
        logger.debug(message);
    }

    private static void checkAndLogSeparator() {
        if (isFirstLog.compareAndSet(true, false)) {
            logger.info("-----------TEST IS STARTED-------------");
        }
    }
}
