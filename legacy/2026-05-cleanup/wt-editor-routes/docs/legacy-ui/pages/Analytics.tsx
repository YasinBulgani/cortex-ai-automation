/**
 * Analytics Page
 * Comprehensive analytics and metrics dashboards
 */

import React, { useState } from 'react';
import '../styles/Analytics.css';

interface AnalyticsMetric {
  label: string;
  value: number;
  unit: string;
  trend: number;
  color: string;
}

/**
 * Analytics Component
 */
const Analytics: React.FC = () => {
  const [timeRange, setTimeRange] = useState('7days');
  const [selectedMetric, setSelectedMetric] = useState('pass-rate');

  const metrics: Record<string, AnalyticsMetric> = {
    'pass-rate': {
      label: 'Pass Rate',
      value: 97.8,
      unit: '%',
      trend: 2.3,
      color: '#10b981',
    },
    'avg-duration': {
      label: 'Avg Duration',
      value: 2.4,
      unit: 's',
      trend: -0.2,
      color: '#3b82f6',
    },
    'tests-per-day': {
      label: 'Tests/Day',
      value: 156,
      unit: '',
      trend: 12.5,
      color: '#f59e0b',
    },
    'failure-rate': {
      label: 'Failure Rate',
      value: 2.2,
      unit: '%',
      trend: -0.8,
      color: '#ef4444',
    },
  };

  const trendData = [
    { day: 'Mon', rate: 94.5 },
    { day: 'Tue', rate: 95.2 },
    { day: 'Wed', rate: 96.1 },
    { day: 'Thu', rate: 96.8 },
    { day: 'Fri', rate: 97.2 },
    { day: 'Sat', rate: 97.5 },
    { day: 'Sun', rate: 97.8 },
  ];

  const flakyTests = [
    { name: 'Payment Gateway Integration', flakiness: 45, runs: 20 },
    { name: 'Email Notification Handler', flakiness: 38, runs: 16 },
    { name: 'Inventory Sync Process', flakiness: 28, runs: 14 },
    { name: 'Currency Conversion Service', flakiness: 22, runs: 9 },
  ];

  const topFailures = [
    { error: 'Timeout (>30s)', count: 45, percentage: 32 },
    { error: 'Element Not Found', count: 28, percentage: 20 },
    { error: 'Assertion Failed', count: 35, percentage: 25 },
    { error: 'Network Error', count: 22, percentage: 16 },
    { error: 'Other', count: 10, percentage: 7 },
  ];

  return (
    <div className="analytics">
      {/* Header */}
      <div className="analytics-header">
        <h1>Analytics</h1>
        <p className="subtitle">Comprehensive test metrics and insights</p>

        <div className="header-controls">
          <div className="time-range-selector">
            <button
              className={`range-btn ${timeRange === '7days' ? 'active' : ''}`}
              onClick={() => setTimeRange('7days')}
            >
              7 Days
            </button>
            <button
              className={`range-btn ${timeRange === '30days' ? 'active' : ''}`}
              onClick={() => setTimeRange('30days')}
            >
              30 Days
            </button>
            <button
              className={`range-btn ${timeRange === '90days' ? 'active' : ''}`}
              onClick={() => setTimeRange('90days')}
            >
              90 Days
            </button>
            <button
              className={`range-btn ${timeRange === 'all' ? 'active' : ''}`}
              onClick={() => setTimeRange('all')}
            >
              All Time
            </button>
          </div>

          <button className="control-btn">📥 Export</button>
        </div>
      </div>

      {/* Key Metrics Grid */}
      <div className="metrics-overview">
        {Object.entries(metrics).map(([key, metric]) => (
          <div
            key={key}
            className={`metric-card ${selectedMetric === key ? 'selected' : ''}`}
            onClick={() => setSelectedMetric(key)}
          >
            <div className="metric-header">
              <h3 className="metric-label">{metric.label}</h3>
              <div className="metric-trend" style={{ color: metric.trend > 0 ? '#10b981' : '#ef4444' }}>
                {metric.trend > 0 ? '↑' : '↓'} {Math.abs(metric.trend)}%
              </div>
            </div>

            <div className="metric-value" style={{ color: metric.color }}>
              {metric.value.toFixed(1)}{metric.unit}
            </div>

            <div className="metric-indicator" style={{ backgroundColor: metric.color }}></div>
          </div>
        ))}
      </div>

      {/* Main Analytics Content */}
      <div className="analytics-grid">
        {/* Pass Rate Trend */}
        <div className="analytics-card">
          <h2>Pass Rate Trend</h2>

          <div className="trend-chart">
            <div className="chart-y-axis">
              <span>100%</span>
              <span>95%</span>
              <span>90%</span>
              <span>85%</span>
            </div>

            <div className="chart-bars">
              {trendData.map((data, idx) => (
                <div key={idx} className="bar-container">
                  <div
                    className="bar"
                    style={{ height: `${(data.rate / 100) * 200}px`, backgroundColor: '#3b82f6' }}
                  ></div>
                  <label className="bar-label">{data.day}</label>
                </div>
              ))}
            </div>
          </div>

          <div className="chart-info">
            <p>📈 Consistent improvement trend over the past week</p>
          </div>
        </div>

        {/* Flaky Tests Analysis */}
        <div className="analytics-card">
          <h2>Flakiest Tests</h2>

          <div className="flaky-tests-list">
            {flakyTests.map((test, idx) => (
              <div key={idx} className="flaky-item">
                <div className="flaky-info">
                  <h4 className="flaky-name">{test.name}</h4>
                  <p className="flaky-meta">{test.runs} runs analyzed</p>
                </div>

                <div className="flaky-score">
                  <div className="flaky-bar">
                    <div className="flaky-fill" style={{ width: `${test.flakiness}%` }}></div>
                  </div>
                  <span className="flaky-percentage">{test.flakiness}%</span>
                </div>
              </div>
            ))}
          </div>

          <button className="action-link">View details →</button>
        </div>

        {/* Error Distribution */}
        <div className="analytics-card">
          <h2>Top Failure Reasons</h2>

          <div className="error-distribution">
            {topFailures.map((failure, idx) => (
              <div key={idx} className="error-item">
                <div className="error-info">
                  <h4>{failure.error}</h4>
                  <p className="error-count">{failure.count} occurrences</p>
                </div>

                <div className="error-bar">
                  <div
                    className="error-fill"
                    style={{
                      width: `${failure.percentage}%`,
                      backgroundColor: idx === 0 ? '#ef4444' : idx === 1 ? '#f59e0b' : '#3b82f6',
                    }}
                  ></div>
                </div>

                <span className="error-percentage">{failure.percentage}%</span>
              </div>
            ))}
          </div>
        </div>

        {/* Test Duration Analysis */}
        <div className="analytics-card">
          <h2>Execution Time Distribution</h2>

          <div className="duration-chart">
            <div className="duration-item">
              <span className="duration-label">< 1s</span>
              <div className="duration-bar">
                <div className="duration-fill" style={{ width: '25%' }}></div>
              </div>
              <span className="duration-value">42</span>
            </div>

            <div className="duration-item">
              <span className="duration-label">1-5s</span>
              <div className="duration-bar">
                <div className="duration-fill" style={{ width: '65%' }}></div>
              </div>
              <span className="duration-value">108</span>
            </div>

            <div className="duration-item">
              <span className="duration-label">5-10s</span>
              <div className="duration-bar">
                <div className="duration-fill" style={{ width: '45%' }}></div>
              </div>
              <span className="duration-value">75</span>
            </div>

            <div className="duration-item">
              <span className="duration-label">> 10s</span>
              <div className="duration-bar">
                <div className="duration-fill" style={{ width: '15%' }}></div>
              </div>
              <span className="duration-value">25</span>
            </div>
          </div>
        </div>

        {/* Coverage Summary */}
        <div className="analytics-card">
          <h2>Coverage Summary</h2>

          <div className="coverage-metrics">
            <div className="coverage-item">
              <h4>Code Coverage</h4>
              <div className="coverage-percentage">87.5%</div>
              <div className="coverage-bar">
                <div className="coverage-fill" style={{ width: '87.5%' }}></div>
              </div>
            </div>

            <div className="coverage-item">
              <h4>Feature Coverage</h4>
              <div className="coverage-percentage">92.3%</div>
              <div className="coverage-bar">
                <div className="coverage-fill" style={{ width: '92.3%' }}></div>
              </div>
            </div>

            <div className="coverage-item">
              <h4>API Endpoint Coverage</h4>
              <div className="coverage-percentage">95.1%</div>
              <div className="coverage-bar">
                <div className="coverage-fill" style={{ width: '95.1%' }}></div>
              </div>
            </div>

            <div className="coverage-item">
              <h4>User Flow Coverage</h4>
              <div className="coverage-percentage">88.7%</div>
              <div className="coverage-bar">
                <div className="coverage-fill" style={{ width: '88.7%' }}></div>
              </div>
            </div>
          </div>
        </div>

        {/* Performance Metrics */}
        <div className="analytics-card">
          <h2>Performance Metrics</h2>

          <div className="performance-list">
            <div className="performance-item">
              <span className="perf-label">Avg Response Time</span>
              <span className="perf-value">234ms</span>
              <span className="perf-trend">↑ 5%</span>
            </div>

            <div className="performance-item">
              <span className="perf-label">Max Response Time</span>
              <span className="perf-value">8.2s</span>
              <span className="perf-trend">↓ 2%</span>
            </div>

            <div className="performance-item">
              <span className="perf-label">Tests Per Minute</span>
              <span className="perf-value">42</span>
              <span className="perf-trend">↑ 8%</span>
            </div>

            <div className="performance-item">
              <span className="perf-label">Resource Usage</span>
              <span className="perf-value">68%</span>
              <span className="perf-trend">↓ 12%</span>
            </div>
          </div>
        </div>
      </div>

      {/* Insights Section */}
      <div className="insights-section">
        <h2>Key Insights</h2>

        <div className="insights-grid">
          <div className="insight-card">
            <span className="insight-icon">🎯</span>
            <h4>Stable Performance</h4>
            <p>Pass rate has improved 3.2% this week, showing consistent quality improvement.</p>
          </div>

          <div className="insight-card">
            <span className="insight-icon">⚠️</span>
            <h4>Flaky Test Alert</h4>
            <p>Payment Gateway test is failing 45% of the time. Recommended for immediate attention.</p>
          </div>

          <div className="insight-card">
            <span className="insight-icon">💡</span>
            <h4>Performance Opportunity</h4>
            <p>Average test duration increased by 8%. Optimize page load times to reduce execution time.</p>
          </div>

          <div className="insight-card">
            <span className="insight-icon">📊</span>
            <h4>Coverage Gap</h4>
            <p>API endpoint coverage is 95.1%. Focus on remaining 4.9% for comprehensive testing.</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Analytics;
