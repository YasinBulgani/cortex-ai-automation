/**
 * Report Viewer Page
 * View and export test reports in multiple formats
 */

import React, { useState } from 'react';
import '../styles/ReportViewer.css';

interface ReportData {
  id: string;
  title: string;
  date: string;
  duration: number;
  environment: string;
  browser: string;
  totalTests: number;
  passedTests: number;
  failedTests: number;
  skippedTests: number;
  passRate: number;
}

/**
 * Report Viewer Component
 */
const ReportViewer: React.FC = () => {
  const [reportData] = useState<ReportData>({
    id: 'report-001',
    title: 'E-commerce Platform Test Report',
    date: '2026-04-04',
    duration: 245,
    environment: 'Production',
    browser: 'Chrome 124',
    totalTests: 156,
    passedTests: 152,
    failedTests: 4,
    skippedTests: 0,
    passRate: 97.4,
  });

  const [exportFormat, setExportFormat] = useState<'html' | 'pdf' | 'json'>('html');
  const [showExportMenu, setShowExportMenu] = useState(false);

  const failedTests = [
    { id: '1', name: 'Payment Processing with Invalid Card', error: 'Timeout after 30s' },
    { id: '2', name: 'Coupon Code Validation', error: 'Expected "Valid" but got "Invalid"' },
    { id: '3', name: 'Email Notification on Order', error: 'Email not received within 5s' },
    { id: '4', name: 'Inventory Update on Purchase', error: 'Inventory count mismatch' },
  ];

  const handleExport = (format: 'html' | 'pdf' | 'json') => {
    console.log(`Exporting report as ${format.toUpperCase()}`);
    setExportFormat(format);
    setShowExportMenu(false);
  };

  return (
    <div className="report-viewer">
      {/* Header */}
      <div className="report-header">
        <div className="report-title-section">
          <h1>{reportData.title}</h1>
          <p className="report-meta">
            Generated: {reportData.date} • Environment: {reportData.environment} •
            Browser: {reportData.browser}
          </p>
        </div>

        <div className="report-actions">
          <button className="action-btn">🔄 Regenerate</button>
          <button className="action-btn">📧 Share</button>

          <div className="export-menu">
            <button
              className="action-btn primary"
              onClick={() => setShowExportMenu(!showExportMenu)}
            >
              📥 Export
            </button>

            {showExportMenu && (
              <div className="export-dropdown">
                <button onClick={() => handleExport('html')}>📄 HTML</button>
                <button onClick={() => handleExport('pdf')}>📕 PDF</button>
                <button onClick={() => handleExport('json')}>📋 JSON</button>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Summary Section */}
      <div className="report-summary">
        <div className="summary-card">
          <h3>Execution Summary</h3>
          <div className="summary-content">
            <div className="summary-item">
              <span className="label">Total Duration</span>
              <span className="value">{Math.floor(reportData.duration / 60)}m {reportData.duration % 60}s</span>
            </div>
            <div className="summary-item">
              <span className="label">Environment</span>
              <span className="value">{reportData.environment}</span>
            </div>
            <div className="summary-item">
              <span className="label">Browser</span>
              <span className="value">{reportData.browser}</span>
            </div>
          </div>
        </div>

        <div className="summary-card">
          <h3>Test Results</h3>
          <div className="results-grid">
            <div className="result-item">
              <span className="result-number">{reportData.totalTests}</span>
              <span className="result-label">Total</span>
            </div>
            <div className="result-item">
              <span className="result-number" style={{ color: '#10b981' }}>
                {reportData.passedTests}
              </span>
              <span className="result-label">Passed</span>
            </div>
            <div className="result-item">
              <span className="result-number" style={{ color: '#ef4444' }}>
                {reportData.failedTests}
              </span>
              <span className="result-label">Failed</span>
            </div>
            <div className="result-item">
              <span className="result-number" style={{ color: '#f59e0b' }}>
                {reportData.passRate.toFixed(1)}%
              </span>
              <span className="result-label">Pass Rate</span>
            </div>
          </div>
        </div>

        <div className="summary-card">
          <h3>Trend</h3>
          <div className="trend-indicator">
            <span className="trend-arrow">📈</span>
            <div className="trend-text">
              <p>+3.2% improvement</p>
              <p className="trend-meta">vs previous run</p>
            </div>
          </div>
        </div>
      </div>

      {/* Pass Rate Visualization */}
      <div className="report-chart">
        <h2>Test Results Distribution</h2>
        <div className="chart-content">
          <div className="pie-chart">
            <div className="pie-slice passed" style={{ '--percentage': '97.4' }}></div>
            <div className="pie-slice failed" style={{ '--percentage': '2.6' }}></div>
          </div>

          <div className="chart-legend">
            <div className="legend-item">
              <span className="legend-color passed"></span>
              <span className="legend-text">
                Passed ({reportData.passedTests})
              </span>
            </div>
            <div className="legend-item">
              <span className="legend-color failed"></span>
              <span className="legend-text">
                Failed ({reportData.failedTests})
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Failed Tests Details */}
      {reportData.failedTests > 0 && (
        <div className="report-section">
          <h2>Failed Tests ({reportData.failedTests})</h2>

          <div className="failed-tests-list">
            {failedTests.map((test) => (
              <div key={test.id} className="failed-test-item">
                <div className="failed-test-header">
                  <span className="test-status">✕</span>
                  <h4 className="test-name">{test.name}</h4>
                  <button className="expand-btn">▼</button>
                </div>

                <div className="failed-test-details">
                  <h5>Error Details</h5>
                  <p className="error-message">{test.error}</p>

                  <h5>Suggested Actions</h5>
                  <ul className="suggestions">
                    <li>Check the element locator or page structure</li>
                    <li>Increase timeout values if needed</li>
                    <li>Verify test environment configuration</li>
                    <li>Review recent code changes</li>
                  </ul>

                  <button className="action-btn">Re-run Test</button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Test Breakdown by Category */}
      <div className="report-section">
        <h2>Test Breakdown by Category</h2>

        <div className="breakdown-grid">
          <div className="breakdown-card">
            <h4>Functional Tests</h4>
            <p className="breakdown-number">87</p>
            <p className="breakdown-meta">Core functionality</p>
            <div className="breakdown-bar">
              <div className="bar-fill" style={{ width: '98%' }}></div>
            </div>
            <p className="breakdown-stats">85 passed, 2 failed</p>
          </div>

          <div className="breakdown-card">
            <h4>Visual Regression</h4>
            <p className="breakdown-number">32</p>
            <p className="breakdown-meta">UI consistency</p>
            <div className="breakdown-bar">
              <div className="bar-fill" style={{ width: '100%' }}></div>
            </div>
            <p className="breakdown-stats">32 passed, 0 failed</p>
          </div>

          <div className="breakdown-card">
            <h4>Performance Tests</h4>
            <p className="breakdown-number">20</p>
            <p className="breakdown-meta">Speed & responsiveness</p>
            <div className="breakdown-bar">
              <div className="bar-fill" style={{ width: '95%' }}></div>
            </div>
            <p className="breakdown-stats">19 passed, 1 failed</p>
          </div>

          <div className="breakdown-card">
            <h4>Accessibility Tests</h4>
            <p className="breakdown-number">17</p>
            <p className="breakdown-meta">WCAG compliance</p>
            <div className="breakdown-bar">
              <div className="bar-fill" style={{ width: '100%' }}></div>
            </div>
            <p className="breakdown-stats">17 passed, 0 failed</p>
          </div>
        </div>
      </div>

      {/* Recommendations */}
      <div className="report-section recommendations">
        <h2>Recommendations</h2>

        <div className="recommendations-list">
          <div className="recommendation-item">
            <span className="rec-icon">⚠️</span>
            <div className="rec-content">
              <h4>Flaky Tests Detected</h4>
              <p>
                Tests 1 and 4 have failed in the last 3 runs. Review timing issues and
                dependencies.
              </p>
            </div>
          </div>

          <div className="recommendation-item">
            <span className="rec-icon">💡</span>
            <div className="rec-content">
              <h4>Performance Optimization</h4>
              <p>
                Average test duration increased by 8%. Consider optimizing page load
                times.
              </p>
            </div>
          </div>

          <div className="recommendation-item">
            <span className="rec-icon">📊</span>
            <div className="rec-content">
              <h4>Coverage Gap</h4>
              <p>
                New API endpoints lack test coverage. Consider adding integration tests
                for payment module.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="report-footer">
        <p>Report ID: {reportData.id}</p>
        <p>Generated on {reportData.date} at 14:32 UTC</p>
      </div>
    </div>
  );
};

export default ReportViewer;
