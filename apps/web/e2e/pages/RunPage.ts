import { Page, expect } from "@playwright/test";
import { BasePage } from "./BasePage";

/**
 * RunPage - Page Object for test execution and results
 * Handles: polling, status tracking, result viewing, export
 *
 * Critical patterns:
 * - Async polling with timeout protection
 * - Status transitions: pending → running → passed/failed
 * - Result detail tabs (overview, logs, attachments, metrics)
 * - Export/download functionality
 */

export interface RunResult {
  status: "passed" | "failed" | "skipped" | "timeout";
  duration: number;
  startedAt: string;
  completedAt: string;
  logs: string;
  failureReason?: string;
  screenshotCount: number;
}

export class RunPage extends BasePage {
  // ── Selectors ──────────────────────────────────────────────────────────

  // Run page
  readonly runPageContainer = '[data-testid="run-page"]';
  readonly runHeader = '[data-testid="run-header"]';
  readonly runStatus = '[data-testid="run-status"]';
  readonly runDuration = '[data-testid="run-duration"]';
  readonly runProgressBar = '[data-testid="run-progress"]';

  // Run execution
  readonly startRunBtn = '[data-testid="start-run-btn"]';
  readonly stopRunBtn = '[data-testid="stop-run-btn"]';
  readonly retryRunBtn = '[data-testid="retry-run-btn"]';
  readonly runLoading = '[data-testid="run-loading"]';
  readonly runSpinner = '[data-testid="run-spinner"]';

  // Results view
  readonly resultContainer = '[data-testid="result-container"]';
  readonly resultOverviewTab = '[data-testid="result-tab-overview"]';
  readonly resultLogsTab = '[data-testid="result-tab-logs"]';
  readonly resultAttachmentsTab = '[data-testid="result-tab-attachments"]';
  readonly resultMetricsTab = '[data-testid="result-tab-metrics"]';

  // Result details
  readonly resultStatus = '[data-testid="result-status"]';
  readonly resultDuration = '[data-testid="result-duration"]';
  readonly resultTimestamp = '[data-testid="result-timestamp"]';
  readonly resultLogs = '[data-testid="result-logs"]';
  readonly resultFailureReason = '[data-testid="result-failure-reason"]';
  readonly resultScreenshots = '[data-testid="result-screenshots"]';
  readonly resultAttachmentList = '[data-testid="result-attachment-list"]';

  // Export & Share
  readonly exportBtn = '[data-testid="export-btn"]';
  readonly exportModal = '[data-testid="export-modal"]';
  readonly exportFormatSelect = '[data-testid="export-format"]';
  readonly exportScopeSelect = '[data-testid="export-scope"]';
  readonly exportConfirmBtn = '[data-testid="export-confirm"]';
  readonly shareBtn = '[data-testid="share-btn"]';
  readonly shareModal = '[data-testid="share-modal"]';
  readonly shareLink = '[data-testid="share-link"]';
  readonly copyLinkBtn = '[data-testid="copy-link-btn"]';

  // Actions from result
  readonly reportDefectBtn = '[data-testid="report-defect-btn"]';
  readonly linkJiraBtn = '[data-testid="link-jira-btn"]';
  readonly backToListBtn = '[data-testid="back-to-list-btn"]';

  // List view
  readonly runListContainer = '[data-testid="run-list"]';
  readonly runListItem = '[data-testid="run-list-item"]';
  readonly runListItemStatus = '[data-testid="run-list-item-status"]';

  constructor(page: Page) {
    super(page);
  }

  /**
   * Navigate to run page (usually auto-navigated after clicking Run)
   */
  async goto(projectId: string, testCaseId: string, runId: string) {
    await super.goto(`/projects/${projectId}/test-cases/${testCaseId}/runs/${runId}`);
    await this.waitForPageReady();
  }

  /**
   * Navigate to run list for a test case
   */
  async gotoRunList(projectId: string, testCaseId: string) {
    await super.goto(`/projects/${projectId}/test-cases/${testCaseId}/runs`);
    await this.waitForPageReady();
  }

  /**
   * Start a test case run
   * Used when already on test case detail page
   */
  async runTestCase(): Promise<void> {
    const runBtn = this.page.locator(this.startRunBtn);
    if (await runBtn.count() === 0) {
      throw new Error("Run button not found");
    }

    await runBtn.click();

    // Wait for run to start (might show loading or navigate to run page)
    await this.page.waitForTimeout(500);
    await this.waitForPageReady();
  }

  /**
   * Poll for run completion with timeout
   *
   * Pattern: Check status every 2s for up to 60s (default)
   * Returns: "passed" | "failed" | "timeout"
   *
   * @param timeout - Max wait time in milliseconds (default: 60000)
   * @returns Final status
   */
  async pollRunCompletion(
    timeout = 60000,
    pollInterval = 2000
  ): Promise<"passed" | "failed" | "timeout" | "skipped"> {
    const startTime = Date.now();

    while (Date.now() - startTime < timeout) {
      try {
        const status = await this.getRunStatus();

        // Check if run is complete
        if (
          status === "passed" ||
          status === "failed" ||
          status === "skipped" ||
          status === "error"
        ) {
          return status as "passed" | "failed" | "timeout" | "skipped";
        }

        // Still running, wait before next poll
        await this.page.waitForTimeout(pollInterval);
      } catch (error) {
        // Element not found or other error, retry
        await this.page.waitForTimeout(pollInterval);
      }
    }

    return "timeout";
  }

  /**
   * Get current run status
   *
   * @returns Status string (pending, running, passed, failed, error, skipped)
   */
  async getRunStatus(): Promise<string> {
    const statusEl = this.page.locator(this.runStatus);
    if (await statusEl.count() === 0) {
      throw new Error("Status element not found");
    }

    const status = await statusEl.textContent();
    return status?.toLowerCase().trim() || "unknown";
  }

  /**
   * Get run duration in seconds
   */
  async getRunDuration(): Promise<number> {
    const durationEl = this.page.locator(this.runDuration);
    if (await durationEl.count() === 0) {
      return 0;
    }

    const text = await durationEl.textContent();
    const match = text?.match(/(\d+\.?\d*)/);
    return match ? parseFloat(match[1]) : 0;
  }

  /**
   * Get full run result details
   */
  async getResultDetail(): Promise<RunResult> {
    // Wait for results to load
    await this.waitFor(this.resultContainer, 10000);

    const status = await this.getRunStatus();
    const duration = await this.getRunDuration();

    // Get timestamps
    const timestampEl = this.page.locator(this.resultTimestamp);
    const timestamp = await timestampEl.textContent();

    // Get logs
    let logs = "";
    if (await this.page.locator(this.resultLogs).count() > 0) {
      logs = await this.getText(this.resultLogs);
    }

    // Get failure reason if failed
    let failureReason: string | undefined = undefined;
    if (status === "failed" && (await this.page.locator(this.resultFailureReason).count() > 0)) {
      failureReason = await this.getText(this.resultFailureReason);
    }

    // Count screenshots
    const screenshots = this.page.locator(this.resultScreenshots);
    const screenshotCount = await screenshots.count();

    return {
      status: status as "passed" | "failed" | "skipped" | "timeout",
      duration,
      startedAt: timestamp || "",
      completedAt: timestamp || "",
      logs,
      failureReason,
      screenshotCount,
    };
  }

  /**
   * Click on result tab
   *
   * @param tab - Tab name (overview, logs, attachments, metrics)
   */
  async clickResultTab(tab: "overview" | "logs" | "attachments" | "metrics"): Promise<void> {
    const tabSelector = `[data-testid="result-tab-${tab}"]`;
    await this.click(tabSelector);
    await this.page.waitForTimeout(300);
  }

  /**
   * Get logs text from result
   */
  async getLogsText(): Promise<string> {
    await this.clickResultTab("logs");
    return this.getText(this.resultLogs);
  }

  /**
   * Get list of attachments
   */
  async getAttachmentList(): Promise<string[]> {
    await this.clickResultTab("attachments");

    const items = this.page.locator(this.resultAttachmentList);
    const count = await items.count();
    const attachments: string[] = [];

    for (let i = 0; i < count; i++) {
      const text = await items.nth(i).textContent();
      if (text) {
        attachments.push(text.trim());
      }
    }

    return attachments;
  }

  /**
   * Download screenshot by index
   */
  async downloadScreenshot(index = 0): Promise<void> {
    const screenshots = this.page.locator(this.resultScreenshots);
    if (index >= (await screenshots.count())) {
      throw new Error(`Screenshot ${index} not found`);
    }

    await screenshots.nth(index).click();
    // Browser will handle download
    await this.page.waitForTimeout(500);
  }

  /**
   * Export run result
   *
   * @param format - Export format (pdf, csv, json)
   */
  async exportResult(format: "pdf" | "csv" | "json" = "pdf"): Promise<void> {
    // Click export button
    await this.click(this.exportBtn);

    // Wait for modal
    await this.waitFor(this.exportModal, 5000);

    // Select format
    await this.page.selectOption(this.exportFormatSelect, format);

    // Confirm export (triggers download)
    const [download] = await Promise.all([
      this.page.waitForEvent("download"),
      this.click(this.exportConfirmBtn),
    ]);

    // Browser handles download automatically
    await download.delete(); // Clean up test file
  }

  /**
   * Share run result (generates link)
   */
  async shareResult(): Promise<string> {
    // Click share button
    await this.click(this.shareBtn);

    // Wait for modal with link
    await this.waitFor(this.shareModal, 5000);

    // Get share link
    const linkEl = this.page.locator(this.shareLink);
    const link = await linkEl.inputValue();

    // Copy link
    await this.click(this.copyLinkBtn);

    return link;
  }

  /**
   * Report defect from result
   */
  async reportDefect(): Promise<void> {
    await this.click(this.reportDefectBtn);
    await this.waitForPageReady();
  }

  /**
   * Retry the run
   */
  async retryRun(): Promise<void> {
    const retryBtn = this.page.locator(this.retryRunBtn);
    if (await retryBtn.count() === 0) {
      throw new Error("Retry button not found");
    }

    await retryBtn.click();
    await this.page.waitForTimeout(500);
  }

  /**
   * Stop a running test
   */
  async stopRun(): Promise<void> {
    const stopBtn = this.page.locator(this.stopRunBtn);
    if (await stopBtn.count() === 0) {
      throw new Error("Stop button not found");
    }

    await stopBtn.click();
    await this.page.waitForTimeout(500);
  }

  /**
   * Check if run is still loading
   */
  async isRunning(): Promise<boolean> {
    const spinner = this.page.locator(this.runSpinner);
    return (await spinner.count()) > 0;
  }

  /**
   * Get list of all runs (from run list page)
   */
  async getRunList(): Promise<Array<{ id: string; status: string; duration: string }>> {
    const items = this.page.locator(this.runListItem);
    const count = await items.count();
    const runs: Array<{ id: string; status: string; duration: string }> = [];

    for (let i = 0; i < count; i++) {
      const item = items.nth(i);
      const id = await item.getAttribute("data-run-id");
      const statusEl = item.locator(this.runListItemStatus);
      const status = await statusEl.textContent();

      runs.push({
        id: id || "",
        status: status?.trim() || "",
        duration: "",
      });
    }

    return runs;
  }

  /**
   * Wait for specific status with timeout
   *
   * @param expectedStatus - Status to wait for
   * @param timeout - Max wait time in milliseconds
   */
  async waitForStatus(
    expectedStatus: string,
    timeout = 60000
  ): Promise<boolean> {
    const startTime = Date.now();
    const pollInterval = 2000;

    while (Date.now() - startTime < timeout) {
      const currentStatus = await this.getRunStatus();
      if (currentStatus === expectedStatus) {
        return true;
      }
      await this.page.waitForTimeout(pollInterval);
    }

    return false;
  }

  /**
   * Navigate back to test case list
   */
  async backToList(): Promise<void> {
    await this.click(this.backToListBtn);
    await this.waitForPageReady();
  }
}
