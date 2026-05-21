/**
 * Logger Utility
 * Centralized logging system with file and console output
 */

import * as fs from 'fs';
import * as path from 'path';
import { LOG_LEVELS, LogLevel, ENV_VARS } from '../config/constants';

export class Logger {
  private static readonly LOG_DIR = path.join(__dirname, '../logs');
  private static readonly LOG_FILE = path.join(
    this.LOG_DIR,
    `test-execution-${new Date().toISOString().split('T')[0]}.log`
  );
  private static logLevel: LogLevel = 'INFO';

  static initialize(): void {
    if (!fs.existsSync(this.LOG_DIR)) {
      fs.mkdirSync(this.LOG_DIR, { recursive: true });
    }

    const envLogLevel = process.env[ENV_VARS.LOG_LEVEL]?.toUpperCase();
    if (envLogLevel && LOG_LEVELS.includes(envLogLevel as LogLevel)) {
      this.logLevel = envLogLevel as LogLevel;
    }
  }

  private static writeLog(level: string, message: string, data?: unknown): void {
    const timestamp = new Date().toISOString();
    const logLine = `[${timestamp}] [${level}] ${message}${data ? ` | Data: ${JSON.stringify(data)}` : ''}\n`;

    console.log(logLine.trim());

    try {
      fs.appendFileSync(this.LOG_FILE, logLine, 'utf-8');
    } catch (error) {
      console.error('Log file write error:', error);
    }
  }

  private static shouldLog(level: string): boolean {
    const levels = ['DEBUG', 'INFO', 'WARN', 'ERROR'];
    const currentLevelIndex = levels.indexOf(this.logLevel);
    const messageLevelIndex = levels.indexOf(level);
    return messageLevelIndex >= currentLevelIndex;
  }

  static debug(message: string, data?: unknown): void {
    if (this.shouldLog('DEBUG')) {
      this.writeLog('DEBUG', message, data);
    }
  }

  static info(message: string, data?: unknown): void {
    if (this.shouldLog('INFO')) {
      this.writeLog('INFO', message, data);
    }
  }

  static warn(message: string, data?: unknown): void {
    if (this.shouldLog('WARN')) {
      this.writeLog('WARN', message, data);
    }
  }

  static error(message: string, error?: Error | unknown): void {
    if (this.shouldLog('ERROR')) {
      const errorData = error instanceof Error
        ? { message: error.message, stack: error.stack }
        : error;
      this.writeLog('ERROR', message, errorData);
    }
  }

  static logScenarioStart(scenarioName: string, tags?: string[]): void {
    this.info(`Scenario Started: ${scenarioName}`, { tags });
  }

  static logScenarioEnd(scenarioName: string, status: 'PASSED' | 'FAILED' | 'SKIPPED', duration?: number): void {
    this.info(`Scenario ${status}: ${scenarioName}`, { duration: duration ? `${duration}ms` : undefined });
  }

  static logApiRequest(method: string, url: string, statusCode?: number, responseTime?: number): void {
    this.debug(`API Request: ${method} ${url}`, {
      statusCode,
      responseTime: responseTime ? `${responseTime}ms` : undefined
    });
  }

  static logWebAction(action: string, element?: string, value?: string): void {
    this.debug(`Web Action: ${action}`, { element, value });
  }
}

Logger.initialize();
