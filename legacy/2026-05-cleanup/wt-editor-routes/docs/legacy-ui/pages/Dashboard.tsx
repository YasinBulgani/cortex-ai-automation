/**
 * Dashboard Page
 * Main dashboard with overview widgets and quick actions
 */

import React, { useState, useEffect } from 'react';
import '../styles/Dashboard.css';

interface DashboardStats {
  totalTests: number;
  passedTests: number;
  failedTests: number;
  skippedTests: number;
  averageExecutionTime: number;
  passRate: number;
}

interface RecentRun {
  id: string;
  name: string;
  status: 'passed' | 'failed' | 'running';
  duration: number;
  timestamp: string;
  testCount: number;
}

/**
 * Dashboard Component
 */
const Dashboard: React.FC = () => {
  const [stats, setStats] = useState<DashboardStats>({
    totalTests: 1240,
    passedTests: 1218,
    failedTests: 22,
    skippedTests: 0,
    averageExecutionTime: 2.3,
    passRate: 98.2,
  });

  const [recentRuns, setRecentRuns] = useState<RecentRun[]>([
    {
      id: '1',
      name: 'E-commerce Checkout Flow',
      status: 'passed',
      duration: 45,
      timestamp: '2 hours ago',
      testCount: 87,
    },
    {
      id: '2',
      name: 'Authentication Tests',
      status: 'passed',
      duration: 32,
      timestamp: '4 hours ago',
      testCount: 56,
    },
    {
      id: '3',
      name: 'Payment Gateway Integration',
      status: 'failed',
      duration: 28,
      timestamp: '6 hours ago',
      testCount: 42,
    },
    {
      id: '4',
      name: 'Visual Regression Suite',
      status: 'running',
      duration: 15,
      timestamp: 'Currently running',
      testCount: 124,
    },
  ]);

  useEffect(() => {
    // Simulate real-time updates
    const interval = setInterval(() => {
      setStats((prevStats) => ({
        ...prevStats,
        totalTests: prevStats.totalTests + Math.floor(Math.random() * 5),
        passedTests: prevStats.passedTests + Math.floor(Math.random() * 4),
      }));
    }, 5000);

    return () => clearInterval(interval);
  }, []);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'passed':
        return '#10b981';
      case 'failed':
        return '#ef4444';
      case 'running':
        return '#f59e0b';
      default:
        return '#6b7280';
    }
  };

  return (
    <div className="dashboard">
      {/* Header */}
      <div className="dashboard-header">
        <h1>Dashboard</h1>
        <p className="subtitle">Test execution overview and metrics</p>
      </div>

      {/* Stats Grid */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-content">
            <h3 className="stat-title">Total Tests</h3>
            <p className="stat-number">{stats.totalTests}</p>
            <p className="stat-meta">All time</p>
          </div>
          <div className="stat-icon" style={{ backgroundColor: '#3b82f6' }}>
            📊
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-content">
            <h3 className="stat-title">Pass Rate</h3>
            <p className="stat-number">{stats.passRate.toFixed(1)}%</p>
            <p className="stat-meta">Success ratio</p>
          </div>
          <div className="stat-icon" style={{ backgroundColor: '#10b981' }}>
            ✓
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-content">
            <h3 className="stat-title">Failed Tests</h3>
            <p className="stat-number">{stats.failedTests}</p>
            <p className="stat-meta">Needs attention</p>
          </div>
          <div className="stat-icon" style={{ backgroundColor: '#ef4444' }}>
            ✕
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-content">
            <h3 className="stat-title">Avg Duration</h3>
            <p className="stat-number">{stats.averageExecutionTime}s</p>
            <p className="stat-meta">Per test</p>
          </div>
          <div className="stat-icon" style={{ backgroundColor: '#f59e0b' }}>
            ⏱️
          </div>
        </div>
      </div>

      {/* Main Content Grid */}
      <div className="dashboard-grid">
        {/* Recent Test Runs */}
        <div className="card">
          <div className="card-header">
            <h2>Recent Test Runs</h2>
            <a href="/reports" className="view-all">View All →</a>
          </div>

          <div className="runs-list">
            {recentRuns.map((run) => (
              <div key={run.id} className="run-item">
                <div className="run-status">
                  <div
                    className={`status-badge status-${run.status}`}
                    style={{ backgroundColor: getStatusColor(run.status) }}
                  >
                    {run.status === 'passed' && '✓'}
                    {run.status === 'failed' && '✕'}
                    {run.status === 'running' && '⟳'}
                  </div>
                </div>

                <div className="run-details">
                  <h4 className="run-name">{run.name}</h4>
                  <p className="run-meta">{run.testCount} tests • {run.duration}s</p>
                </div>

                <div className="run-time">
                  <span className="run-timestamp">{run.timestamp}</span>
                </div>

                <button className="run-view-btn">View</button>
              </div>
            ))}
          </div>
        </div>

        {/* Quick Actions */}
        <div className="card">
          <div className="card-header">
            <h2>Quick Actions</h2>
          </div>

          <div className="actions-list">
            <button className="action-item">
              <span className="action-icon">▶️</span>
              <div className="action-content">
                <h4>Run All Tests</h4>
                <p>Execute full test suite</p>
              </div>
              <span className="arrow">→</span>
            </button>

            <button className="action-item">
              <span className="action-icon">🎬</span>
              <div className="action-content">
                <h4>Record New Test</h4>
                <p>Start test recording session</p>
              </div>
              <span className="arrow">→</span>
            </button>

            <button className="action-item">
              <span className="action-icon">🤖</span>
              <div className="action-content">
                <h4>AI Generate Tests</h4>
                <p>Generate scenarios using AI</p>
              </div>
              <span className="arrow">→</span>
            </button>

            <button className="action-item">
              <span className="action-icon">📊</span>
              <div className="action-content">
                <h4>View Analytics</h4>
                <p>Detailed metrics and trends</p>
              </div>
              <span className="arrow">→</span>
            </button>

            <button className="action-item">
              <span className="action-icon">🛠️</span>
              <div className="action-content">
                <h4>Test Configuration</h4>
                <p>Manage test settings</p>
              </div>
              <span className="arrow">→</span>
            </button>

            <button className="action-item">
              <span className="action-icon">📄</span>
              <div className="action-content">
                <h4>Generate Report</h4>
                <p>Create test report</p>
              </div>
              <span className="arrow">→</span>
            </button>
          </div>
        </div>

        {/* Performance Chart */}
        <div className="card">
          <div className="card-header">
            <h2>Pass Rate Trend (7 Days)</h2>
          </div>

          <div className="chart-container">
            <div className="chart-placeholder">
              <div className="chart-bar" style={{ height: '45%' }}></div>
              <div className="chart-bar" style={{ height: '52%' }}></div>
              <div className="chart-bar" style={{ height: '48%' }}></div>
              <div className="chart-bar" style={{ height: '85%' }}></div>
              <div className="chart-bar" style={{ height: '78%' }}></div>
              <div className="chart-bar" style={{ height: '92%' }}></div>
              <div className="chart-bar" style={{ height: '98%' }}></div>
            </div>
          </div>

          <p className="chart-label">Upward trend in test quality →</p>
        </div>

        {/* Key Metrics */}
        <div className="card">
          <div className="card-header">
            <h2>Key Metrics</h2>
          </div>

          <div className="metrics-list">
            <div className="metric">
              <span className="metric-label">Total Duration</span>
              <span className="metric-value">285h 42m</span>
            </div>
            <div className="metric">
              <span className="metric-label">Avg Tests/Day</span>
              <span className="metric-value">156</span>
            </div>
            <div className="metric">
              <span className="metric-label">Flaky Tests</span>
              <span className="metric-value">3</span>
            </div>
            <div className="metric">
              <span className="metric-label">Coverage</span>
              <span className="metric-value">87.5%</span>
            </div>
            <div className="metric">
              <span className="metric-label">Response Time</span>
              <span className="metric-value">234ms</span>
            </div>
            <div className="metric">
              <span className="metric-label">Uptime</span>
              <span className="metric-value">99.9%</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
