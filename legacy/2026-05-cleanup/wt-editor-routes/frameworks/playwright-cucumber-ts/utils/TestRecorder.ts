/**
 * Test Recorder Utility
 * Records user actions and generates step definitions automatically
 */

import { Page, BrowserContext } from '@playwright/test';
import { Logger } from './Logger';
import { LLMClient } from './LLMClient';

interface RecordedAction {
  type: 'navigate' | 'click' | 'fill' | 'press' | 'select' | 'check' | 'screenshot';
  selector?: string;
  value?: string;
  key?: string;
  url?: string;
  timestamp: number;
  elementInfo?: {
    text?: string;
    placeholder?: string;
    type?: string;
  };
}

interface RecordingSession {
  id: string;
  startTime: number;
  endTime?: number;
  duration?: number;
  actions: RecordedAction[];
  status: 'recording' | 'stopped' | 'converted';
  generatedSteps?: string[];
}

/**
 * Test Recorder Class
 */
export class TestRecorder {
  private page: Page;
  private logger: Logger;
  private llmClient?: LLMClient;
  private session: RecordingSession | null = null;
  private listeners: Map<string, Function> = new Map();

  constructor(page: Page, logger: Logger, llmClient?: LLMClient) {
    this.page = page;
    this.logger = logger;
    this.llmClient = llmClient;
  }

  /**
   * Start recording
   */
  async startRecording(sessionId?: string): Promise<string> {
    const id = sessionId || `session-${Date.now()}`;

    this.session = {
      id,
      startTime: Date.now(),
      actions: [],
      status: 'recording',
    };

    // Setup listeners for user actions
    await this.setupActionListeners();

    this.logger.info(`Recording started: ${id}`);
    return id;
  }

  /**
   * Stop recording
   */
  async stopRecording(): Promise<RecordingSession> {
    if (!this.session) {
      throw new Error('No active recording session');
    }

    // Remove listeners
    await this.removeActionListeners();

    this.session.endTime = Date.now();
    this.session.duration = this.session.endTime - this.session.startTime;
    this.session.status = 'stopped';

    this.logger.info(`Recording stopped: ${this.session.id}`, {
      actionCount: this.session.actions.length,
      duration: this.session.duration,
    });

    return this.session;
  }

  /**
   * Get current session
   */
  getSession(): RecordingSession | null {
    return this.session;
  }

  /**
   * Convert recorded actions to step definitions
   */
  async convertToSteps(): Promise<string[]> {
    if (!this.session) {
      throw new Error('No active recording session');
    }

    this.logger.info(`Converting ${this.session.actions.length} actions to steps...`);

    const steps: string[] = [];

    for (let i = 0; i < this.session.actions.length; i++) {
      const action = this.session.actions[i];
      const step = await this.actionToStep(action, i);
      if (step) {
        steps.push(step);
      }
    }

    this.session.generatedSteps = steps;
    this.session.status = 'converted';

    this.logger.info(`Generated ${steps.length} step definitions`);
    return steps;
  }

  /**
   * Convert action to BDD step
   */
  private async actionToStep(action: RecordedAction, index: number): Promise<string> {
    switch (action.type) {
      case 'navigate':
        return `Given I navigate to "${action.url}"`;

      case 'click':
        return `When I click on "${this.getElementDescription(action)}"`;

      case 'fill':
        return `And I fill "${this.getElementDescription(action)}" with "${action.value}"`;

      case 'press':
        return `And I press "${action.key}"`;

      case 'select':
        return `And I select "${action.value}" from "${this.getElementDescription(action)}"`;

      case 'check':
        return `And I check "${this.getElementDescription(action)}"`;

      case 'screenshot':
        return `Then I take a screenshot named "${action.value || `step-${index}`}"`;

      default:
        return '';
    }
  }

  /**
   * Get element description from selector or element info
   */
  private getElementDescription(action: RecordedAction): string {
    if (action.elementInfo?.text) {
      return action.elementInfo.text;
    }
    if (action.elementInfo?.placeholder) {
      return action.elementInfo.placeholder;
    }
    return action.selector || 'element';
  }

  /**
   * Generate step definitions code
   */
  async generateStepDefinitions(): Promise<string> {
    if (!this.session || !this.session.generatedSteps) {
      throw new Error('No steps to generate definitions for');
    }

    if (!this.llmClient) {
      // Return basic step definition template
      return this.generateBasicStepDefinitions(this.session.generatedSteps);
    }

    const stepsText = this.session.generatedSteps.join('\n');

    const stepDefinitions = await this.llmClient.generateTestScenarios({
      userStory: stepsText,
      pageUrl: this.page.url(),
    });

    return this.formatStepDefinitions(stepDefinitions.stepDefinitions || []);
  }

  /**
   * Generate basic step definitions without AI
   */
  private generateBasicStepDefinitions(steps: string[]): string {
    const code = `/**
 * Generated Step Definitions from Test Recording
 * Auto-generated by TestRecorder
 */

import { Given, When, Then, And } from '@cucumber/cucumber';

${steps
  .map((step, index) => {
    // Convert step to function
    const match = step.match(/^(Given|When|Then|And)\s+(.+)$/i);
    if (!match) return '';

    const keyword = match[1].toLowerCase();
    const description = match[2];

    return `${keyword}('${description.replace(/"/g, '\\"')}', async function(this: any) {
  // TODO: Implement step logic
  this.logger.info('Step executed: ${description}');
});`;
  })
  .join('\n\n')}

export {};`;

    return code;
  }

  /**
   * Format step definitions from LLM
   */
  private formatStepDefinitions(definitions: string[]): string {
    return `/**
 * Generated Step Definitions from Test Recording
 * Auto-generated by TestRecorder using AI
 */

${definitions.join('\n\n')}

export {};`;
  }

  /**
   * Setup action listeners
   */
  private async setupActionListeners(): Promise<void> {
    if (!this.session) return;

    // Listen for navigation
    this.page.on('framenavigated', () => {
      this.recordAction({
        type: 'navigate',
        url: this.page.url(),
        timestamp: Date.now(),
      });
    });

    // Listen for clicks (via evaluation)
    await this.page.addInitScript(() => {
      (window as any).__recordedClicks = [];
      document.addEventListener(
        'click',
        (e) => {
          const target = e.target as HTMLElement;
          (window as any).__recordedClicks.push({
            selector: this.getSelector(target),
            text: target.textContent?.substring(0, 50),
          });
        },
        true
      );
    });

    // Listen for inputs
    await this.page.addInitScript(() => {
      (window as any).__recordedInputs = [];
      document.addEventListener(
        'change',
        (e) => {
          const target = e.target as HTMLInputElement;
          (window as any).__recordedInputs.push({
            selector: this.getSelector(target),
            value: target.value,
          });
        },
        true
      );
    });

    this.logger.info('Action listeners installed');
  }

  /**
   * Remove action listeners
   */
  private async removeActionListeners(): Promise<void> {
    try {
      // Listeners are automatically removed when page closes
      this.logger.info('Action listeners removed');
    } catch (error) {
      this.logger.warn('Error removing listeners', { error });
    }
  }

  /**
   * Record action
   */
  private recordAction(action: RecordedAction): void {
    if (!this.session || this.session.status !== 'recording') return;

    this.session.actions.push({
      ...action,
      timestamp: Date.now(),
    });

    this.logger.debug(`Action recorded: ${action.type}`);

    // Emit event
    const handler = this.listeners.get('action');
    if (handler) {
      handler(action);
    }
  }

  /**
   * Replay recording
   */
  async replay(): Promise<void> {
    if (!this.session) {
      throw new Error('No session to replay');
    }

    this.logger.info(`Replaying ${this.session.actions.length} actions...`);

    for (const action of this.session.actions) {
      await this.replayAction(action);
    }

    this.logger.info('Replay completed');
  }

  /**
   * Replay single action
   */
  private async replayAction(action: RecordedAction): Promise<void> {
    switch (action.type) {
      case 'navigate':
        if (action.url) {
          await this.page.goto(action.url);
        }
        break;

      case 'click':
        if (action.selector) {
          await this.page.click(action.selector);
        }
        break;

      case 'fill':
        if (action.selector && action.value) {
          await this.page.fill(action.selector, action.value);
        }
        break;

      case 'press':
        if (action.key) {
          await this.page.press('body', action.key);
        }
        break;

      case 'screenshot':
        await this.page.screenshot({ path: `./screenshots/${action.value || 'screenshot'}.png` });
        break;
    }
  }

  /**
   * Export session as JSON
   */
  exportAsJSON(): string {
    if (!this.session) {
      throw new Error('No session to export');
    }

    return JSON.stringify(this.session, null, 2);
  }

  /**
   * Export session as Gherkin feature
   */
  exportAsGherkin(): string {
    if (!this.session || !this.session.generatedSteps) {
      throw new Error('No steps to export');
    }

    let gherkin = 'Feature: Recorded Test Scenario\n\n';
    gherkin += `  Scenario: Recorded at ${new Date(this.session.startTime).toLocaleString()}\n`;

    for (const step of this.session.generatedSteps) {
      gherkin += `    ${step}\n`;
    }

    return gherkin;
  }

  /**
   * Listen to events
   */
  on(event: string, handler: Function): void {
    this.listeners.set(event, handler);
  }

  /**
   * Get statistics
   */
  getStatistics(): {
    sessionId: string;
    actionCount: number;
    stepCount: number;
    duration?: number;
  } {
    if (!this.session) {
      throw new Error('No session');
    }

    return {
      sessionId: this.session.id,
      actionCount: this.session.actions.length,
      stepCount: this.session.generatedSteps?.length || 0,
      duration: this.session.duration,
    };
  }
}

/**
 * Helper function to get selector for element
 * Note: This would be injected into the page
 */
function getSelector(element: HTMLElement): string {
  if (element.id) {
    return `#${element.id}`;
  }

  // Build selector from element path
  const path: string[] = [];
  let current: Element | null = element;

  while (current && current !== document.body) {
    let selector = current.tagName.toLowerCase();

    if ((current as HTMLElement).id) {
      selector += `#${(current as HTMLElement).id}`;
      path.unshift(selector);
      break;
    }

    const parent = current.parentElement;
    if (parent) {
      const siblings = Array.from(parent.children);
      const index = siblings.indexOf(current);
      if (siblings.filter((s) => s.tagName === current?.tagName).length > 1) {
        selector += `:nth-of-type(${index + 1})`;
      }
    }

    path.unshift(selector);
    current = parent;
  }

  return path.join(' > ');
}

/**
 * Helper function to create recorder
 */
export function createTestRecorder(page: Page, logger: Logger, llmClient?: LLMClient): TestRecorder {
  return new TestRecorder(page, logger, llmClient);
}
