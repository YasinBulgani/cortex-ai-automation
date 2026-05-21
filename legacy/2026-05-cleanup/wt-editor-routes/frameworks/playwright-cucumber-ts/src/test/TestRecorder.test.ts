/**
 * TestRecorder Unit Tests
 * Test suite for user action recording and code generation
 */

import { TestRecorder, RecordingSession, UserAction } from '../../core/typescript/utils/TestRecorder';

const mockLogger = {
  info: jest.fn(),
  warn: jest.fn(),
  error: jest.fn(),
  debug: jest.fn(),
};

const mockPage = {
  screenshot: jest.fn(),
  click: jest.fn(),
  fill: jest.fn(),
  navigate: jest.fn(),
};

describe('TestRecorder', () => {
  let recorder: TestRecorder;

  beforeEach(() => {
    jest.clearAllMocks();
    recorder = new TestRecorder(mockPage as any, mockLogger as any);
  });

  describe('Initialization', () => {
    test('should initialize recorder with page and logger', () => {
      expect(recorder).toBeDefined();
      expect(recorder.isRecording).toBe(false);
    });

    test('should have empty recording session initially', () => {
      const session = recorder.getCurrentSession();
      expect(session).toBeNull();
    });
  });

  describe('Recording Lifecycle', () => {
    test('should start recording', () => {
      recorder.startRecording('test-session');
      expect(recorder.isRecording).toBe(true);
    });

    test('should stop recording', () => {
      recorder.startRecording('test-session');
      recorder.stopRecording();
      expect(recorder.isRecording).toBe(false);
    });

    test('should create session with unique ID', () => {
      recorder.startRecording();
      const session = recorder.getCurrentSession();
      expect(session).toBeDefined();
      expect(session?.sessionId).toBeDefined();
    });

    test('should not allow starting while already recording', () => {
      recorder.startRecording('session-1');
      expect(() => recorder.startRecording('session-2')).toThrow();
    });

    test('should not allow stopping when not recording', () => {
      expect(() => recorder.stopRecording()).toThrow();
    });
  });

  describe('Action Recording', () => {
    beforeEach(() => {
      recorder.startRecording('test-session');
    });

    afterEach(() => {
      if (recorder.isRecording) {
        recorder.stopRecording();
      }
    });

    test('should record click actions', () => {
      recorder.recordAction({
        type: 'click',
        selector: 'button.submit',
        timestamp: Date.now(),
      });

      const session = recorder.getCurrentSession();
      expect(session?.actions.length).toBe(1);
      expect(session?.actions[0].type).toBe('click');
    });

    test('should record fill actions', () => {
      recorder.recordAction({
        type: 'fill',
        selector: 'input[type="text"]',
        value: 'test value',
        timestamp: Date.now(),
      });

      const session = recorder.getCurrentSession();
      expect(session?.actions[0].type).toBe('fill');
      expect(session?.actions[0].value).toBe('test value');
    });

    test('should record navigation actions', () => {
      recorder.recordAction({
        type: 'navigate',
        url: 'https://example.com',
        timestamp: Date.now(),
      });

      const session = recorder.getCurrentSession();
      expect(session?.actions[0].type).toBe('navigate');
    });

    test('should record screenshot actions', () => {
      recorder.recordAction({
        type: 'screenshot',
        filename: 'screenshot-1.png',
        timestamp: Date.now(),
      });

      const session = recorder.getCurrentSession();
      expect(session?.actions[0].type).toBe('screenshot');
    });

    test('should maintain action order', () => {
      const timestamp = Date.now();

      recorder.recordAction({
        type: 'navigate',
        url: 'https://example.com',
        timestamp: timestamp,
      });

      recorder.recordAction({
        type: 'click',
        selector: 'button',
        timestamp: timestamp + 1000,
      });

      recorder.recordAction({
        type: 'fill',
        selector: 'input',
        value: 'test',
        timestamp: timestamp + 2000,
      });

      const session = recorder.getCurrentSession();
      expect(session?.actions.length).toBe(3);
      expect(session?.actions[0].type).toBe('navigate');
      expect(session?.actions[1].type).toBe('click');
      expect(session?.actions[2].type).toBe('fill');
    });

    test('should record action duration', () => {
      const startTime = Date.now();
      recorder.recordAction({
        type: 'click',
        selector: 'button',
        timestamp: startTime,
        duration: 500,
      });

      const session = recorder.getCurrentSession();
      expect(session?.actions[0].duration).toBe(500);
    });
  });

  describe('Step Conversion', () => {
    beforeEach(() => {
      recorder.startRecording('test-session');
    });

    afterEach(() => {
      if (recorder.isRecording) {
        recorder.stopRecording();
      }
    });

    test('should convert recorded actions to BDD steps', () => {
      recorder.recordAction({
        type: 'navigate',
        url: 'https://example.com',
        timestamp: Date.now(),
      });

      recorder.recordAction({
        type: 'click',
        selector: 'button.search',
        timestamp: Date.now() + 1000,
      });

      const steps = recorder.convertToSteps();
      expect(steps.length).toBeGreaterThan(0);
      expect(typeof steps[0]).toBe('string');
    });

    test('should generate valid Gherkin syntax', () => {
      recorder.recordAction({
        type: 'navigate',
        url: 'https://example.com',
        timestamp: Date.now(),
      });

      const steps = recorder.convertToSteps();
      expect(steps.some(step => step.includes('Given'))).toBe(true);
    });

    test('should include selectors in step definitions', () => {
      recorder.recordAction({
        type: 'click',
        selector: 'button.submit',
        timestamp: Date.now(),
      });

      const steps = recorder.convertToSteps();
      const clickSteps = steps.filter(s => s.includes('click'));
      expect(clickSteps.length).toBeGreaterThan(0);
    });
  });

  describe('Code Generation', () => {
    beforeEach(() => {
      recorder.startRecording('test-session');
    });

    afterEach(() => {
      if (recorder.isRecording) {
        recorder.stopRecording();
      }
    });

    test('should generate TypeScript step definitions', () => {
      recorder.recordAction({
        type: 'navigate',
        url: 'https://example.com',
        timestamp: Date.now(),
      });

      recorder.recordAction({
        type: 'click',
        selector: 'button',
        timestamp: Date.now() + 1000,
      });

      const definitions = recorder.generateStepDefinitions();
      expect(definitions).toBeDefined();
      expect(definitions.includes('async')).toBe(true);
      expect(definitions.includes('await')).toBe(true);
    });

    test('should include valid TypeScript syntax', () => {
      recorder.recordAction({
        type: 'fill',
        selector: 'input[name="email"]',
        value: 'test@example.com',
        timestamp: Date.now(),
      });

      const definitions = recorder.generateStepDefinitions();
      expect(definitions.includes('await page.fill')).toBe(true);
    });

    test('should generate step pattern matching', () => {
      recorder.recordAction({
        type: 'click',
        selector: 'button',
        timestamp: Date.now(),
      });

      const definitions = recorder.generateStepDefinitions();
      expect(definitions.includes('When') || definitions.includes('Then')).toBe(true);
    });
  });

  describe('Export Functionality', () => {
    beforeEach(() => {
      recorder.startRecording('test-session');

      recorder.recordAction({
        type: 'navigate',
        url: 'https://example.com',
        timestamp: Date.now(),
      });

      recorder.recordAction({
        type: 'click',
        selector: 'button',
        timestamp: Date.now() + 1000,
      });

      recorder.stopRecording();
    });

    test('should export as JSON', () => {
      const json = recorder.exportAsJSON();
      const parsed = JSON.parse(json);

      expect(parsed.sessionId).toBeDefined();
      expect(parsed.actions).toBeDefined();
      expect(Array.isArray(parsed.actions)).toBe(true);
    });

    test('should export as Gherkin', () => {
      const gherkin = recorder.exportAsGherkin();

      expect(typeof gherkin).toBe('string');
      expect(gherkin.length).toBeGreaterThan(0);
    });

    test('should include all actions in export', () => {
      const json = recorder.exportAsJSON();
      const parsed = JSON.parse(json);

      expect(parsed.actions.length).toBe(2);
    });
  });

  describe('Replay Functionality', () => {
    beforeEach(() => {
      recorder.startRecording('test-session');

      recorder.recordAction({
        type: 'navigate',
        url: 'https://example.com',
        timestamp: Date.now(),
      });

      recorder.recordAction({
        type: 'click',
        selector: 'button',
        timestamp: Date.now() + 1000,
      });

      recorder.stopRecording();
    });

    test('should replay recorded actions', async () => {
      await recorder.replay(mockPage as any);
      expect(mockPage.navigate).toHaveBeenCalled();
    });

    test('should replay in correct order', async () => {
      const callOrder: string[] = [];

      mockPage.navigate.mockImplementation(() => {
        callOrder.push('navigate');
      });

      mockPage.click.mockImplementation(() => {
        callOrder.push('click');
      });

      await recorder.replay(mockPage as any);

      expect(callOrder[0]).toBe('navigate');
    });

    test('should respect action timing', async () => {
      const durations: number[] = [];

      jest.useFakeTimers();

      await recorder.replay(mockPage as any);

      jest.useRealTimers();
    });
  });

  describe('Statistics', () => {
    beforeEach(() => {
      recorder.startRecording('test-session');
    });

    afterEach(() => {
      if (recorder.isRecording) {
        recorder.stopRecording();
      }
    });

    test('should track action count', () => {
      recorder.recordAction({
        type: 'click',
        selector: 'button',
        timestamp: Date.now(),
      });

      const session = recorder.getCurrentSession();
      expect(session?.actions.length).toBe(1);
    });

    test('should calculate total duration', () => {
      const startTime = Date.now();

      recorder.recordAction({
        type: 'navigate',
        url: 'https://example.com',
        timestamp: startTime,
      });

      recorder.recordAction({
        type: 'click',
        selector: 'button',
        timestamp: startTime + 5000,
      });

      const session = recorder.getCurrentSession();
      expect(session?.endTime).toBeUndefined(); // Still recording

      recorder.stopRecording();
      const finalSession = recorder.getCompletedSessions()[0];
      expect(finalSession.duration).toBeGreaterThanOrEqual(5000);
    });
  });

  describe('Session Management', () => {
    test('should store completed sessions', () => {
      recorder.startRecording('session-1');
      recorder.recordAction({
        type: 'navigate',
        url: 'https://example.com',
        timestamp: Date.now(),
      });
      recorder.stopRecording();

      const completedSessions = recorder.getCompletedSessions();
      expect(completedSessions.length).toBe(1);
      expect(completedSessions[0].sessionId).toBe('session-1');
    });

    test('should clear recording history', () => {
      recorder.startRecording('session-1');
      recorder.stopRecording();

      let completedSessions = recorder.getCompletedSessions();
      expect(completedSessions.length).toBe(1);

      recorder.clearHistory();
      completedSessions = recorder.getCompletedSessions();
      expect(completedSessions.length).toBe(0);
    });
  });
});
