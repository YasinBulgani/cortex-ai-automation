/**
 * Test Recording Step Definitions
 * Record user actions and generate test code automatically
 */

import { Given, When, Then } from '@cucumber/cucumber';
import { TestRecorder } from '../utils/TestRecorder';

/**
 * RECORDING SESSION STEPS
 */

Given('I start recording user actions', async function (this: any) {
  const recorder = new TestRecorder(this.page, this.logger, this.llmClient);
  const sessionId = await recorder.startRecording();

  this.testRecorder = recorder;
  this.recordingSessionId = sessionId;

  this.logger.info(`Recording session started: ${sessionId}`);
});

When('I stop recording', async function (this: any) {
  if (!this.testRecorder) {
    throw new Error('No active recording session');
  }

  const session = await this.testRecorder.stopRecording();
  this.recordedSession = session;

  this.logger.info(`Recording stopped - ${session.actions.length} actions recorded`);
});

Then('the recording should capture all user actions', async function (this: any) {
  if (!this.recordedSession || this.recordedSession.actions.length === 0) {
    throw new Error('No actions were recorded');
  }

  this.logger.info(`✓ Recorded ${this.recordedSession.actions.length} user actions`);
});

/**
 * STEP GENERATION STEPS
 */

When('I convert recorded actions to test steps', async function (this: any) {
  if (!this.testRecorder) {
    throw new Error('No active test recorder');
  }

  const steps = await this.testRecorder.convertToSteps();
  this.generatedSteps = steps;

  this.logger.info(`Generated ${steps.length} test steps from actions`);
});

Then('the generated steps should follow BDD format', async function (this: any) {
  if (!this.generatedSteps || this.generatedSteps.length === 0) {
    throw new Error('No steps generated');
  }

  const bddKeywords = ['Given', 'When', 'Then', 'And', 'But'];
  const validSteps = this.generatedSteps.filter((step) =>
    bddKeywords.some((keyword) => step.startsWith(keyword))
  );

  if (validSteps.length !== this.generatedSteps.length) {
    throw new Error(
      `Only ${validSteps.length}/${this.generatedSteps.length} steps follow BDD format`
    );
  }

  this.logger.info(`✓ All ${this.generatedSteps.length} steps follow BDD format`);
});

/**
 * STEP DEFINITION GENERATION STEPS
 */

When('I generate step definitions from the recording', async function (this: any) {
  if (!this.testRecorder) {
    throw new Error('No active test recorder');
  }

  const stepDefinitions = await this.testRecorder.generateStepDefinitions();
  this.generatedStepDefinitions = stepDefinitions;

  this.logger.info('Step definitions generated successfully');
});

Then('the generated step definitions should be valid TypeScript', async function (this: any) {
  if (!this.generatedStepDefinitions) {
    throw new Error('No step definitions generated');
  }

  // Check for TypeScript syntax
  const hasImports = this.generatedStepDefinitions.includes('import');
  const hasSteps =
    this.generatedStepDefinitions.includes('Given') ||
    this.generatedStepDefinitions.includes('When') ||
    this.generatedStepDefinitions.includes('Then');
  const hasExport = this.generatedStepDefinitions.includes('export');

  if (!hasImports || !hasSteps || !hasExport) {
    throw new Error('Generated step definitions are not valid TypeScript');
  }

  this.logger.info('✓ Generated step definitions are valid TypeScript');
});

/**
 * RECORDING EXPORT STEPS
 */

When('I export the recording as JSON', async function (this: any) {
  if (!this.testRecorder) {
    throw new Error('No active test recorder');
  }

  const json = this.testRecorder.exportAsJSON();
  this.exportedJSON = json;

  this.logger.info('Recording exported as JSON');
});

When('I export the recording as Gherkin', async function (this: any) {
  if (!this.testRecorder) {
    throw new Error('No active test recorder');
  }

  const gherkin = this.testRecorder.exportAsGherkin();
  this.exportedGherkin = gherkin;

  this.logger.info('Recording exported as Gherkin');
});

Then('the exported JSON should contain all recorded actions', async function (this: any) {
  if (!this.exportedJSON) {
    throw new Error('No JSON export available');
  }

  const parsed = JSON.parse(this.exportedJSON);
  if (!parsed.actions || parsed.actions.length === 0) {
    throw new Error('Exported JSON does not contain actions');
  }

  this.logger.info(`✓ JSON export contains ${parsed.actions.length} actions`);
});

Then('the exported Gherkin should be a valid feature file', async function (this: any) {
  if (!this.exportedGherkin) {
    throw new Error('No Gherkin export available');
  }

  const hasFeature = this.exportedGherkin.includes('Feature:');
  const hasScenario = this.exportedGherkin.includes('Scenario:');

  if (!hasFeature || !hasScenario) {
    throw new Error('Exported Gherkin is not a valid feature file');
  }

  this.logger.info('✓ Exported Gherkin is a valid feature file');
});

/**
 * RECORDING REPLAY STEPS
 */

When('I replay the recorded actions', async function (this: any) {
  if (!this.testRecorder) {
    throw new Error('No active test recorder');
  }

  try {
    await this.testRecorder.replay();
    this.replaySuccessful = true;
  } catch (error) {
    this.replaySuccessful = false;
    this.replayError = error;
    this.logger.warn('Replay encountered errors', { error });
  }
});

Then('the replay should complete successfully', async function (this: any) {
  if (!this.replaySuccessful) {
    throw new Error(`Replay failed: ${this.replayError?.message}`);
  }

  this.logger.info('✓ Replay completed successfully');
});

/**
 * RECORDING STATISTICS STEPS
 */

When('I check recording statistics', async function (this: any) {
  if (!this.testRecorder) {
    throw new Error('No active test recorder');
  }

  const stats = this.testRecorder.getStatistics();
  this.recordingStats = stats;

  this.logger.info('Recording statistics', stats);
});

Then('the recording should have {int} or more actions', async function (this: any, minActions: number) {
  if (!this.recordingStats) {
    throw new Error('No recording statistics available');
  }

  if (this.recordingStats.actionCount < minActions) {
    throw new Error(
      `Only ${this.recordingStats.actionCount} actions recorded, expected at least ${minActions}`
    );
  }

  this.logger.info(`✓ Recording captured ${this.recordingStats.actionCount} actions`);
});

Then('the recording should have generated {int} or more steps', async function (this: any, minSteps: number) {
  if (!this.recordingStats) {
    throw new Error('No recording statistics available');
  }

  if (this.recordingStats.stepCount < minSteps) {
    throw new Error(
      `Only ${this.recordingStats.stepCount} steps generated, expected at least ${minSteps}`
    );
  }

  this.logger.info(`✓ Recording generated ${this.recordingStats.stepCount} test steps`);
});

/**
 * COMPLETE RECORDING WORKFLOW STEPS
 */

Given('I have a test recording setup', async function (this: any) {
  const recorder = new TestRecorder(this.page, this.logger, this.llmClient);
  this.testRecorder = recorder;
  this.recordingWorkflow = {
    sessionId: null,
    actions: [],
    steps: [],
    stepDefinitions: null,
    status: 'initialized',
  };

  this.logger.info('Test recording setup initialized');
});

When('I perform a complete recording workflow', async function (this: any) {
  if (!this.testRecorder) {
    throw new Error('No test recorder available');
  }

  // Start recording
  const sessionId = await this.testRecorder.startRecording();
  this.recordingWorkflow.sessionId = sessionId;

  // Simulate some actions by navigating
  await this.page.goto(this.page.url());

  // Stop recording
  const session = await this.testRecorder.stopRecording();
  this.recordingWorkflow.actions = session.actions;

  // Convert to steps
  const steps = await this.testRecorder.convertToSteps();
  this.recordingWorkflow.steps = steps;

  // Generate step definitions
  const stepDefinitions = await this.testRecorder.generateStepDefinitions();
  this.recordingWorkflow.stepDefinitions = stepDefinitions;

  this.recordingWorkflow.status = 'completed';

  this.logger.info('Recording workflow completed', {
    actions: this.recordingWorkflow.actions.length,
    steps: this.recordingWorkflow.steps.length,
  });
});

Then('the recording workflow should produce valid output', async function (this: any) {
  const workflow = this.recordingWorkflow;

  if (workflow.status !== 'completed') {
    throw new Error('Recording workflow did not complete');
  }

  if (!workflow.sessionId) {
    throw new Error('No session ID recorded');
  }

  if (workflow.steps.length === 0) {
    throw new Error('No steps were generated');
  }

  if (!workflow.stepDefinitions) {
    throw new Error('No step definitions were generated');
  }

  this.logger.info('✓ Recording workflow produced valid output', {
    sessionId: workflow.sessionId,
    stepCount: workflow.steps.length,
  });
});

/**
 * Export
 */
export {};
