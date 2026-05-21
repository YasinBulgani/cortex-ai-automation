/**
 * Cucumber Hooks
 * Test lifecycle management (Before/After hooks)
 */

import { Before, After, BeforeAll, AfterAll, setDefaultTimeout, setWorldConstructor } from '@cucumber/cucumber';
import { PlaywrightWorld } from './playwright-world';
import * as path from 'path';
import { exec } from 'child_process';
import { promisify } from 'util';
import { Logger } from '../utils/Logger';
import * as fs from 'fs';

const execAsync = promisify(exec);

setDefaultTimeout(60 * 1000);
setWorldConstructor(PlaywrightWorld);

BeforeAll(async function () {
  Logger.info('Test execution started...', {
    environment: process.env.ENVIRONMENT || 'QA',
    browser: process.env.BROWSER || 'chromium',
    timestamp: new Date().toISOString()
  });
});

AfterAll(async function () {
  Logger.info('Test execution completed.', {
    timestamp: new Date().toISOString()
  });
  
  try {
    const reportScriptPath = path.join(__dirname, '../utils/generate-report.js');
    Logger.info('Generating HTML report...');
    const { stdout, stderr } = await execAsync(`node ${reportScriptPath}`);
    if (stdout) Logger.info('Report generation output:', stdout);
    if (stderr && !stderr.includes('Warning')) {
      Logger.warn('Report warnings:', stderr);
    }
    Logger.info('HTML report generated successfully: reports/cucumber_report.html');
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    Logger.error('Report generation failed:', error);
  }
});

Before(async function (this: PlaywrightWorld) {
  const scenario = this.pickle;
  if (scenario) {
    const tags = scenario.tags?.map(tag => tag.name) || [];
    Logger.logScenarioStart(scenario.name, tags);
    Logger.debug('Initializing browser and context...', {
      browser: this.browserType,
      environment: this.environment
    });
  }
  
  await this.init();
  
  Logger.debug('Browser and context initialized successfully');
});

After(async function (this: PlaywrightWorld) {
  const scenario = this.pickle;
  const scenarioStatus = this.result?.status || 'UNKNOWN';
  const duration = this.result?.duration?.nanos ? this.result.duration.nanos / 1000000 : undefined;

  // Screenshot politikası:
  //  - Varsayılan: SADECE FAILED senaryolarda tam sayfa screenshot.
  //    Eskiden her After'da çekilirdi → CI süresi + disk I/O + gürültü.
  //  - `ALWAYS_SCREENSHOT=1` ile geriye dönük davranışa geri dönülebilir
  //    (debug/demo senaryoları için).
  const alwaysScreenshot = process.env.ALWAYS_SCREENSHOT === '1';
  const shouldCapture =
    !!this.page && !!scenario && (alwaysScreenshot || scenarioStatus === 'FAILED');

  if (shouldCapture) {
    try {
      const screenshotsDir = path.join(__dirname, '../reports/screenshots');
      if (!fs.existsSync(screenshotsDir)) {
        fs.mkdirSync(screenshotsDir, { recursive: true });
      }

      const sanitizedName = scenario!.name.replace(/[^a-zA-Z0-9_]/g, '_');
      const suffix = scenarioStatus === 'FAILED' ? 'FAILED' : 'ok';
      const screenshotPath = path.join(
        screenshotsDir,
        `${sanitizedName}_${suffix}_${Date.now()}.png`,
      );
      await this.page!.screenshot({ path: screenshotPath, fullPage: true });
      Logger.debug('Screenshot captured', { path: screenshotPath, status: scenarioStatus });
    } catch (error) {
      Logger.warn('Screenshot capture failed', error);
    }
  }

  if (scenario) {
    const status = scenarioStatus === 'PASSED' ? 'PASSED' :
                   scenarioStatus === 'FAILED' ? 'FAILED' : 'SKIPPED';
    Logger.logScenarioEnd(scenario.name, status, duration);
  }

  await this.cleanup();
  Logger.debug('Browser and context cleaned up');
});
