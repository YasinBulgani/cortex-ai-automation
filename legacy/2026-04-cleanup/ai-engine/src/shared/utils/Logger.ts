/**
 * Structured Logger for BGTS_Test_Donusum
 *
 * Multi-level structured logging with support for:
 * - Console output (human-readable)
 * - File output (JSON format)
 * - Log rotation
 * - Context preservation across async operations
 */

import * as fs from 'fs';
import * as path from 'path';

export type LogLevel = 'error' | 'warn' | 'info' | 'debug';

interface LogEntry {
  timestamp: string;
  level: LogLevel;
  message: string;
  context?: Record<string, any>;
  stack?: string;
  duration?: number; // milliseconds
}

interface LoggerConfig {
  level: LogLevel;
  outputDir: string;
  maxFileSize: number; // bytes
  maxFiles: number;
  colorize: boolean;
  includeStack: boolean;
  dateFormat: 'iso' | 'local';
}

/**
 * Color codes for console output
 */
const COLORS = {
  reset: '\x1b[0m',
  red: '\x1b[31m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  green: '\x1b[32m',
  gray: '\x1b[90m',
};

const LEVEL_COLORS = {
  error: COLORS.red,
  warn: COLORS.yellow,
  info: COLORS.blue,
  debug: COLORS.gray,
};

const LEVEL_ORDER: Record<LogLevel, number> = {
  error: 3,
  warn: 2,
  info: 1,
  debug: 0,
};

/**
 * Main Logger class
 * Provides structured logging capabilities
 */
export class Logger {
  private config: LoggerConfig;
  private logBuffer: LogEntry[] = [];
  private bufferFlushInterval: NodeJS.Timeout | null = null;
  private contextStack: Map<string, any> = new Map();

  constructor(config: Partial<LoggerConfig> = {}) {
    this.config = {
      level: (process.env.LOG_LEVEL as LogLevel) || 'info',
      outputDir: process.env.LOG_DIR || './logs',
      maxFileSize: 10 * 1024 * 1024, // 10MB
      maxFiles: 5,
      colorize: process.env.NO_COLOR !== 'true',
      includeStack: process.env.NODE_ENV !== 'production',
      dateFormat: 'iso',
      ...config,
    };

    // Ensure logs directory exists
    this.ensureLogDirectory();

    // Start buffer flush interval
    this.startBufferFlush();
  }

  /**
   * Log error level message
   */
  error(message: string, context?: Record<string, any> | Error, stack?: string): void {
    this.log('error', message, this.normalizeContext(context), stack);
  }

  /**
   * Log warning level message
   */
  warn(message: string, context?: Record<string, any>): void {
    this.log('warn', message, context);
  }

  /**
   * Log info level message
   */
  info(message: string, context?: Record<string, any>): void {
    this.log('info', message, context);
  }

  /**
   * Log debug level message
   */
  debug(message: string, context?: Record<string, any>): void {
    this.log('debug', message, context);
  }

  /**
   * Log with timing information
   * Useful for performance measurements
   */
  timed(label: string, fn: () => void): void;
  timed(label: string, fn: () => Promise<void>): Promise<void>;
  timed(label: string, fn: any): any {
    const start = Date.now();
    try {
      const result = fn();
      if (result instanceof Promise) {
        return result
          .then(() => {
            const duration = Date.now() - start;
            this.info(`${label} completed`, { duration });
          })
          .catch((error) => {
            const duration = Date.now() - start;
            this.error(`${label} failed`, { error, duration });
            throw error;
          });
      } else {
        const duration = Date.now() - start;
        this.info(`${label} completed`, { duration });
      }
    } catch (error) {
      const duration = Date.now() - start;
      this.error(`${label} failed`, { error, duration });
      throw error;
    }
  }

  /**
   * Push context for async operations
   * Useful for preserving request context
   */
  pushContext(context: Record<string, any>): void {
    const id = Math.random().toString(36).substr(2, 9);
    this.contextStack.set(id, context);
  }

  /**
   * Pop context
   */
  popContext(): void {
    const lastKey = Array.from(this.contextStack.keys()).pop();
    if (lastKey) {
      this.contextStack.delete(lastKey);
    }
  }

  /**
   * Get current context
   */
  getContext(): Record<string, any> {
    const context: Record<string, any> = {};
    this.contextStack.forEach((value) => {
      Object.assign(context, value);
    });
    return context;
  }

  /**
   * Clear all context
   */
  clearContext(): void {
    this.contextStack.clear();
  }

  /**
   * Core logging method
   */
  private log(
    level: LogLevel,
    message: string,
    context?: Record<string, any>,
    stack?: string
  ): void {
    // Check if message should be logged based on level
    if (LEVEL_ORDER[level] > LEVEL_ORDER[this.config.level]) {
      return;
    }

    // Build log entry
    const entry: LogEntry = {
      timestamp: this.getTimestamp(),
      level,
      message,
      context: { ...this.getContext(), ...context },
    };

    if (stack && this.config.includeStack) {
      entry.stack = stack;
    }

    // Log to console
    this.logToConsole(entry);

    // Add to buffer for file writing
    this.logBuffer.push(entry);

    // Flush immediately for errors
    if (level === 'error') {
      this.flushBuffer();
    }
  }

  /**
   * Log to console with colors
   */
  private logToConsole(entry: LogEntry): void {
    const color = this.config.colorize ? LEVEL_COLORS[entry.level] : '';
    const reset = this.config.colorize ? COLORS.reset : '';

    let output = `${color}[${entry.timestamp}] ${entry.level.toUpperCase()}${reset} ${entry.message}`;

    if (Object.keys(entry.context || {}).length > 0) {
      output += ` ${JSON.stringify(entry.context)}`;
    }

    if (entry.stack) {
      output += `\n${entry.stack}`;
    }

    if (entry.level === 'error') {
      console.error(output);
    } else if (entry.level === 'warn') {
      console.warn(output);
    } else {
      console.log(output);
    }
  }

  /**
   * Write buffered logs to file
   */
  private flushBuffer(): void {
    if (this.logBuffer.length === 0) {
      return;
    }

    const logFile = path.join(this.config.outputDir, 'test.log');
    const jsonContent = this.logBuffer.map((entry) => JSON.stringify(entry)).join('\n');

    try {
      fs.appendFileSync(logFile, jsonContent + '\n');
      this.checkFileSize(logFile);
      this.logBuffer = [];
    } catch (error) {
      console.error('Failed to write log file:', error);
    }
  }

  /**
   * Check log file size and rotate if needed
   */
  private checkFileSize(logFile: string): void {
    try {
      const stats = fs.statSync(logFile);
      if (stats.size > this.config.maxFileSize) {
        this.rotateLogFile(logFile);
      }
    } catch (error) {
      // File doesn't exist yet
    }
  }

  /**
   * Rotate log files
   */
  private rotateLogFile(logFile: string): void {
    const dir = path.dirname(logFile);
    const name = path.basename(logFile, path.extname(logFile));
    const ext = path.extname(logFile);

    // Shift old files
    for (let i = this.config.maxFiles - 2; i >= 0; i--) {
      const oldFile = path.join(dir, `${name}.${i + 1}${ext}`);
      const newFile = path.join(dir, `${name}.${i + 2}${ext}`);

      if (fs.existsSync(oldFile)) {
        fs.renameSync(oldFile, newFile);
      }
    }

    // Rename current file
    const rotatedFile = path.join(dir, `${name}.1${ext}`);
    fs.renameSync(logFile, rotatedFile);

    // Delete oldest file if exceeds max
    const oldestFile = path.join(dir, `${name}.${this.config.maxFiles}${ext}`);
    if (fs.existsSync(oldestFile)) {
      fs.unlinkSync(oldestFile);
    }
  }

  /**
   * Ensure log directory exists
   */
  private ensureLogDirectory(): void {
    if (!fs.existsSync(this.config.outputDir)) {
      fs.mkdirSync(this.config.outputDir, { recursive: true });
    }
  }

  /**
   * Start periodic buffer flush
   */
  private startBufferFlush(): void {
    // Flush every 5 seconds
    this.bufferFlushInterval = setInterval(() => {
      this.flushBuffer();
    }, 5000);
  }

  /**
   * Get formatted timestamp
   */
  private getTimestamp(): string {
    const now = new Date();
    if (this.config.dateFormat === 'iso') {
      return now.toISOString();
    }
    return now.toLocaleString();
  }

  /**
   * Normalize context (handle Error objects)
   */
  private normalizeContext(context?: Record<string, any> | Error): Record<string, any> | undefined {
    if (context instanceof Error) {
      return {
        error: context.message,
        stack: context.stack,
      };
    }
    return context;
  }

  /**
   * Cleanup
   */
  destroy(): void {
    if (this.bufferFlushInterval) {
      clearInterval(this.bufferFlushInterval);
    }
    this.flushBuffer();
  }
}

/**
 * Global logger instance
 */
let globalLogger: Logger | null = null;

/**
 * Get or create global logger
 */
export function getLogger(config?: Partial<LoggerConfig>): Logger {
  if (!globalLogger) {
    globalLogger = new Logger(config);
  }
  return globalLogger;
}

/**
 * Reset global logger (useful for testing)
 */
export function resetLogger(): void {
  if (globalLogger) {
    globalLogger.destroy();
    globalLogger = null;
  }
}

/**
 * Logger test helper
 */
export function createTestLogger(config?: Partial<LoggerConfig>): Logger {
  return new Logger({
    level: 'debug',
    outputDir: './logs/test',
    colorize: false,
    includeStack: true,
    ...config,
  });
}
