/**
 * Test Monitor Page
 * Real-time test execution monitoring with live updates
 */

import React, { useState, useEffect } from 'react';
import '../styles/TestMonitor.css';

interface TestStep {
  id: string;
  name: string;
  status: 'pending' | 'running' | 'passed' | 'failed' | 'skipped';
  duration: number;
  error?: string;
}

interface TestCase {
  id: string;
  name: string;
  status: 'pending' | 'running' | 'passed' | 'failed' | 'skipped';
  steps: TestStep[];
  duration: number;
  screenshot?: string;
}

/**
 * Test Monitor Component
 */
const TestMonitor: React.FC = () => {
  const [testCases, setTestCases] = useState<TestCase[]>([
    {
      id: '1',
      name: 'User Login - Valid Credentials',
      status: 'passed',
      duration: 3.2,
      steps: [
        { id: '1-1', name: 'Navigate to login page', status: 'passed', duration: 0.5 },
        { id: '1-2', name: 'Enter username', status: 'passed', duration: 0.3 },
        { id: '1-3', name: 'Enter password', status: 'passed', duration: 0.2 },
        { id: '1-4', name: 'Click login button', status: 'passed', duration: 0.4 },
        { id: '1-5', name: 'Verify dashboard loads', status: 'passed', duration: 1.8 },
      ],
    },
    {
      id: '2',
      name: 'Add Item to Cart',
      status: 'running',
      duration: 2.1,
      steps: [
        { id: '2-1', name: 'Navigate to product page', status: 'passed', duration: 0.6 },
        { id: '2-2', name: 'Select product variant', status: 'passed', duration: 0.4 },
        { id: '2-3', name: 'Set quantity', status: 'running', duration: 1.1 },
        { id: '2-4', name: 'Click add to cart', status: 'pending', duration: 0 },
        { id: '2-5', name: 'Verify cart updated', status: 'pending', duration: 0 },
      ],
    },
    {
      id: '3',
      name: 'Checkout Process',
      status: 'pending',
      duration: 0,
      steps: [
        { id: '3-1', name: 'Navigate to cart', status: 'pending', duration: 0 },
        { id: '3-2', name: 'Review items', status: 'pending', duration: 0 },
        { id: '3-3', name: 'Enter shipping info', status: 'pending', duration: 0 },
        { id: '3-4', name: 'Select payment method', status: 'pending', duration: 0 },
        { id: '3-5', name: 'Complete payment', status: 'pending', duration: 0 },
      ],
    },
  ]);

  const [isRunning, setIsRunning] = useState(true);
  const [selectedTest, setSelectedTest] = useState<string | null>('2');
  const [selectedScreenshot, setSelectedScreenshot] = useState<string | null>(null);

  // Simulate real-time test execution
  useEffect(() => {
    if (!isRunning) return;

    const interval = setInterval(() => {
      setTestCases((prevCases) =>
        prevCases.map((testCase) => {
          if (testCase.status === 'pending') return testCase;

          const updatedSteps = testCase.steps.map((step) => {
            if (step.status === 'pending' && Math.random() > 0.7) {
              return {
                ...step,
                status: 'running' as const,
                duration: Math.random() * 2,
              };
            }
            if (step.status === 'running' && Math.random() > 0.6) {
              return {
                ...step,
                status: Math.random() > 0.1 ? ('passed' as const) : ('failed' as const),
                duration: step.duration + Math.random() * 0.5,
              };
            }
            return step;
          });

          const allStepsDone = updatedSteps.every(
            (s) => s.status !== 'pending' && s.status !== 'running'
          );

          if (allStepsDone && testCase.status === 'running') {
            return {
              ...testCase,
              steps: updatedSteps,
              status: updatedSteps.some((s) => s.status === 'failed') ? 'failed' : 'passed',
              duration: updatedSteps.reduce((sum, s) => sum + s.duration, 0),
            };
          }

          return {
            ...testCase,
            steps: updatedSteps,
          };
        })
      );
    }, 2000);

    return () => clearInterval(interval);
  }, [isRunning]);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'passed':
        return '#10b981';
      case 'failed':
        return '#ef4444';
      case 'running':
        return '#f59e0b';
      case 'skipped':
        return '#6b7280';
      default:
        return '#3b82f6';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'passed':
        return '✓';
      case 'failed':
        return '✕';
      case 'running':
        return '⟳';
      case 'skipped':
        return '-';
      default:
        return '●';
    }
  };

  const selectedTestData = testCases.find((t) => t.id === selectedTest);

  return (
    <div className="test-monitor">
      {/* Header */}
      <div className="monitor-header">
        <h1>Test Monitor</h1>
        <div className="monitor-controls">
          <button
            className={`control-btn ${isRunning ? 'active' : ''}`}
            onClick={() => setIsRunning(!isRunning)}
          >
            {isRunning ? '⏸ Pause' : '▶ Resume'}
          </button>
          <button className="control-btn">⟳ Reset</button>
          <button className="control-btn">📊 Summary</button>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="progress-container">
        <div className="progress-info">
          <span>Overall Progress</span>
          <span className="progress-percentage">
            {Math.round(
              (testCases.filter((t) => t.status !== 'pending').length / testCases.length) * 100
            )}
            %
          </span>
        </div>
        <div className="progress-bar">
          <div
            className="progress-fill"
            style={{
              width: `${
                (testCases.filter((t) => t.status !== 'pending').length / testCases.length) * 100
              }%`,
            }}
          ></div>
        </div>
      </div>

      {/* Main Content */}
      <div className="monitor-content">
        {/* Test Cases List */}
        <div className="test-list-section">
          <h2>Test Cases ({testCases.length})</h2>

          <div className="test-list">
            {testCases.map((testCase) => (
              <div
                key={testCase.id}
                className={`test-item ${selectedTest === testCase.id ? 'selected' : ''}`}
                onClick={() => setSelectedTest(testCase.id)}
              >
                <div className="test-status">
                  <div
                    className="status-icon"
                    style={{ backgroundColor: getStatusColor(testCase.status) }}
                  >
                    {getStatusIcon(testCase.status)}
                  </div>
                </div>

                <div className="test-info">
                  <h4 className="test-name">{testCase.name}</h4>
                  <p className="test-meta">
                    {testCase.steps.filter((s) => s.status !== 'pending').length}/
                    {testCase.steps.length} steps • {testCase.duration.toFixed(2)}s
                  </p>
                </div>

                <span className="test-status-label">{testCase.status}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Details Section */}
        <div className="details-section">
          {selectedTestData ? (
            <>
              <h2>{selectedTestData.name}</h2>

              {/* Steps */}
              <div className="steps-container">
                <h3>Test Steps</h3>
                <div className="steps-list">
                  {selectedTestData.steps.map((step) => (
                    <div key={step.id} className={`step-item status-${step.status}`}>
                      <div
                        className="step-status"
                        style={{ backgroundColor: getStatusColor(step.status) }}
                      >
                        {getStatusIcon(step.status)}
                      </div>

                      <div className="step-content">
                        <h4 className="step-name">{step.name}</h4>
                        {step.error && <p className="step-error">{step.error}</p>}
                      </div>

                      <span className="step-duration">
                        {step.duration > 0 ? `${step.duration.toFixed(2)}s` : '-'}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Screenshot Section */}
              {selectedTestData.screenshot && (
                <div className="screenshot-container">
                  <h3>Screenshot</h3>
                  <div
                    className="screenshot"
                    style={{ backgroundColor: '#f3f4f6', padding: '20px', textAlign: 'center' }}
                  >
                    📷 Screenshot: {selectedTestData.screenshot}
                  </div>
                </div>
              )}
            </>
          ) : (
            <div className="empty-state">
              <p>Select a test to view details</p>
            </div>
          )}
        </div>
      </div>

      {/* Statistics Footer */}
      <div className="monitor-footer">
        <div className="stat">
          <span className="stat-label">Total</span>
          <span className="stat-value">{testCases.length}</span>
        </div>
        <div className="stat">
          <span className="stat-label">Passed</span>
          <span className="stat-value" style={{ color: '#10b981' }}>
            {testCases.filter((t) => t.status === 'passed').length}
          </span>
        </div>
        <div className="stat">
          <span className="stat-label">Failed</span>
          <span className="stat-value" style={{ color: '#ef4444' }}>
            {testCases.filter((t) => t.status === 'failed').length}
          </span>
        </div>
        <div className="stat">
          <span className="stat-label">Running</span>
          <span className="stat-value" style={{ color: '#f59e0b' }}>
            {testCases.filter((t) => t.status === 'running').length}
          </span>
        </div>
        <div className="stat">
          <span className="stat-label">Total Duration</span>
          <span className="stat-value">
            {testCases.reduce((sum, t) => sum + t.duration, 0).toFixed(2)}s
          </span>
        </div>
      </div>
    </div>
  );
};

export default TestMonitor;
