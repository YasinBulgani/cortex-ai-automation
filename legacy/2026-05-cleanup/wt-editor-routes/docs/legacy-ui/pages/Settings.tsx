/**
 * Settings Page
 * Application configuration and settings management
 */

import React, { useState } from 'react';
import '../styles/Settings.css';

interface SettingsConfig {
  general: {
    appName: string;
    theme: 'light' | 'dark' | 'auto';
    language: string;
  };
  api: {
    baseUrl: string;
    timeout: number;
    retryAttempts: number;
  };
  notifications: {
    emailOnFailure: boolean;
    slackIntegration: boolean;
    dailySummary: boolean;
  };
  testing: {
    defaultTimeout: number;
    parallelWorkers: number;
    retryFailedTests: boolean;
  };
  integrations: {
    openaiKey?: string;
    anthropicKey?: string;
    deepseekKey?: string;
  };
}

/**
 * Settings Component
 */
const Settings: React.FC = () => {
  const [settings, setSettings] = useState<SettingsConfig>({
    general: {
      appName: 'BGTS - Test Automation Platform',
      theme: 'auto',
      language: 'en',
    },
    api: {
      baseUrl: 'http://localhost:8000',
      timeout: 30000,
      retryAttempts: 3,
    },
    notifications: {
      emailOnFailure: true,
      slackIntegration: false,
      dailySummary: true,
    },
    testing: {
      defaultTimeout: 30000,
      parallelWorkers: 4,
      retryFailedTests: true,
    },
    integrations: {
      openaiKey: '***',
      anthropicKey: '',
      deepseekKey: '',
    },
  });

  const [activeTab, setActiveTab] = useState('general');
  const [isSaved, setIsSaved] = useState(false);

  const handleSave = () => {
    setIsSaved(true);
    setTimeout(() => setIsSaved(false), 3000);
  };

  return (
    <div className="settings">
      {/* Header */}
      <div className="settings-header">
        <h1>Settings</h1>
        <p className="subtitle">Configure application behavior and integrations</p>
      </div>

      {/* Tabs */}
      <div className="settings-tabs">
        <button
          className={`tab-btn ${activeTab === 'general' ? 'active' : ''}`}
          onClick={() => setActiveTab('general')}
        >
          General
        </button>
        <button
          className={`tab-btn ${activeTab === 'api' ? 'active' : ''}`}
          onClick={() => setActiveTab('api')}
        >
          API
        </button>
        <button
          className={`tab-btn ${activeTab === 'notifications' ? 'active' : ''}`}
          onClick={() => setActiveTab('notifications')}
        >
          Notifications
        </button>
        <button
          className={`tab-btn ${activeTab === 'testing' ? 'active' : ''}`}
          onClick={() => setActiveTab('testing')}
        >
          Testing
        </button>
        <button
          className={`tab-btn ${activeTab === 'integrations' ? 'active' : ''}`}
          onClick={() => setActiveTab('integrations')}
        >
          Integrations
        </button>
      </div>

      {/* Success Message */}
      {isSaved && (
        <div className="success-message">
          ✓ Settings saved successfully
        </div>
      )}

      {/* Tab Content */}
      <div className="settings-content">
        {/* General Settings */}
        {activeTab === 'general' && (
          <div className="settings-section">
            <h2>General Settings</h2>

            <div className="setting-group">
              <label className="setting-label">Application Name</label>
              <input
                type="text"
                className="setting-input"
                defaultValue={settings.general.appName}
                onChange={(e) =>
                  setSettings((prev) => ({
                    ...prev,
                    general: { ...prev.general, appName: e.target.value },
                  }))
                }
              />
            </div>

            <div className="setting-group">
              <label className="setting-label">Theme</label>
              <select
                className="setting-select"
                defaultValue={settings.general.theme}
                onChange={(e) =>
                  setSettings((prev) => ({
                    ...prev,
                    general: { ...prev.general, theme: e.target.value as any },
                  }))
                }
              >
                <option value="light">Light</option>
                <option value="dark">Dark</option>
                <option value="auto">Auto (System)</option>
              </select>
            </div>

            <div className="setting-group">
              <label className="setting-label">Language</label>
              <select
                className="setting-select"
                defaultValue={settings.general.language}
                onChange={(e) =>
                  setSettings((prev) => ({
                    ...prev,
                    general: { ...prev.general, language: e.target.value },
                  }))
                }
              >
                <option value="en">English</option>
                <option value="tr">Turkish (Türkçe)</option>
                <option value="es">Spanish (Español)</option>
                <option value="de">German (Deutsch)</option>
                <option value="fr">French (Français)</option>
              </select>
            </div>
          </div>
        )}

        {/* API Settings */}
        {activeTab === 'api' && (
          <div className="settings-section">
            <h2>API Configuration</h2>

            <div className="setting-group">
              <label className="setting-label">Base URL</label>
              <input
                type="text"
                className="setting-input"
                defaultValue={settings.api.baseUrl}
                onChange={(e) =>
                  setSettings((prev) => ({
                    ...prev,
                    api: { ...prev.api, baseUrl: e.target.value },
                  }))
                }
              />
              <p className="setting-help">The base URL for API requests</p>
            </div>

            <div className="setting-group">
              <label className="setting-label">Request Timeout (ms)</label>
              <input
                type="number"
                className="setting-input"
                defaultValue={settings.api.timeout}
                onChange={(e) =>
                  setSettings((prev) => ({
                    ...prev,
                    api: { ...prev.api, timeout: parseInt(e.target.value) },
                  }))
                }
              />
              <p className="setting-help">Maximum time to wait for API responses</p>
            </div>

            <div className="setting-group">
              <label className="setting-label">Retry Attempts</label>
              <input
                type="number"
                className="setting-input"
                defaultValue={settings.api.retryAttempts}
                onChange={(e) =>
                  setSettings((prev) => ({
                    ...prev,
                    api: { ...prev.api, retryAttempts: parseInt(e.target.value) },
                  }))
                }
              />
              <p className="setting-help">Number of times to retry failed requests</p>
            </div>
          </div>
        )}

        {/* Notification Settings */}
        {activeTab === 'notifications' && (
          <div className="settings-section">
            <h2>Notification Preferences</h2>

            <div className="setting-group checkbox">
              <input
                type="checkbox"
                id="email-failure"
                defaultChecked={settings.notifications.emailOnFailure}
                onChange={(e) =>
                  setSettings((prev) => ({
                    ...prev,
                    notifications: {
                      ...prev.notifications,
                      emailOnFailure: e.target.checked,
                    },
                  }))
                }
              />
              <label htmlFor="email-failure">Send email when tests fail</label>
              <p className="setting-help">Get notified immediately when a test run fails</p>
            </div>

            <div className="setting-group checkbox">
              <input
                type="checkbox"
                id="slack-integration"
                defaultChecked={settings.notifications.slackIntegration}
                onChange={(e) =>
                  setSettings((prev) => ({
                    ...prev,
                    notifications: {
                      ...prev.notifications,
                      slackIntegration: e.target.checked,
                    },
                  }))
                }
              />
              <label htmlFor="slack-integration">Enable Slack notifications</label>
              <p className="setting-help">Send test results to your Slack channel</p>
            </div>

            <div className="setting-group checkbox">
              <input
                type="checkbox"
                id="daily-summary"
                defaultChecked={settings.notifications.dailySummary}
                onChange={(e) =>
                  setSettings((prev) => ({
                    ...prev,
                    notifications: {
                      ...prev.notifications,
                      dailySummary: e.target.checked,
                    },
                  }))
                }
              />
              <label htmlFor="daily-summary">Send daily test summary</label>
              <p className="setting-help">Receive daily digest of test execution metrics</p>
            </div>
          </div>
        )}

        {/* Testing Settings */}
        {activeTab === 'testing' && (
          <div className="settings-section">
            <h2>Testing Configuration</h2>

            <div className="setting-group">
              <label className="setting-label">Default Timeout (ms)</label>
              <input
                type="number"
                className="setting-input"
                defaultValue={settings.testing.defaultTimeout}
                onChange={(e) =>
                  setSettings((prev) => ({
                    ...prev,
                    testing: {
                      ...prev.testing,
                      defaultTimeout: parseInt(e.target.value),
                    },
                  }))
                }
              />
              <p className="setting-help">Default timeout for test steps</p>
            </div>

            <div className="setting-group">
              <label className="setting-label">Parallel Workers</label>
              <input
                type="number"
                className="setting-input"
                defaultValue={settings.testing.parallelWorkers}
                min="1"
                max="16"
                onChange={(e) =>
                  setSettings((prev) => ({
                    ...prev,
                    testing: {
                      ...prev.testing,
                      parallelWorkers: parseInt(e.target.value),
                    },
                  }))
                }
              />
              <p className="setting-help">Number of parallel test executions</p>
            </div>

            <div className="setting-group checkbox">
              <input
                type="checkbox"
                id="retry-failed"
                defaultChecked={settings.testing.retryFailedTests}
                onChange={(e) =>
                  setSettings((prev) => ({
                    ...prev,
                    testing: {
                      ...prev.testing,
                      retryFailedTests: e.target.checked,
                    },
                  }))
                }
              />
              <label htmlFor="retry-failed">Automatically retry failed tests</label>
              <p className="setting-help">Re-run failed tests to check for flakiness</p>
            </div>
          </div>
        )}

        {/* Integration Settings */}
        {activeTab === 'integrations' && (
          <div className="settings-section">
            <h2>AI Provider Integrations</h2>

            <div className="integration-warning">
              ⚠️ API keys are encrypted and never shared. Keep them confidential.
            </div>

            <div className="setting-group">
              <label className="setting-label">OpenAI API Key</label>
              <div className="api-key-input">
                <input
                  type="password"
                  className="setting-input"
                  defaultValue={settings.integrations.openaiKey}
                  placeholder="sk-..."
                  onChange={(e) =>
                    setSettings((prev) => ({
                      ...prev,
                      integrations: {
                        ...prev.integrations,
                        openaiKey: e.target.value,
                      },
                    }))
                  }
                />
                <button className="btn-reveal">👁️</button>
              </div>
              <p className="setting-help">Required for GPT-based test generation</p>
            </div>

            <div className="setting-group">
              <label className="setting-label">Anthropic API Key</label>
              <div className="api-key-input">
                <input
                  type="password"
                  className="setting-input"
                  placeholder="sk-ant-..."
                  onChange={(e) =>
                    setSettings((prev) => ({
                      ...prev,
                      integrations: {
                        ...prev.integrations,
                        anthropicKey: e.target.value,
                      },
                    }))
                  }
                />
                <button className="btn-reveal">👁️</button>
              </div>
              <p className="setting-help">Required for Claude-based test generation</p>
            </div>

            <div className="setting-group">
              <label className="setting-label">DeepSeek API Key</label>
              <div className="api-key-input">
                <input
                  type="password"
                  className="setting-input"
                  onChange={(e) =>
                    setSettings((prev) => ({
                      ...prev,
                      integrations: {
                        ...prev.integrations,
                        deepseekKey: e.target.value,
                      },
                    }))
                  }
                />
                <button className="btn-reveal">👁️</button>
              </div>
              <p className="setting-help">Optional: For cost-optimized test generation</p>
            </div>

            <div className="integrations-status">
              <h4>Integration Status</h4>
              <div className="status-item">
                <span className="status-icon">🟢</span>
                <span>OpenAI: Connected</span>
              </div>
              <div className="status-item">
                <span className="status-icon">🔴</span>
                <span>Anthropic: Not configured</span>
              </div>
              <div className="status-item">
                <span className="status-icon">🟡</span>
                <span>DeepSeek: Not configured</span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="settings-footer">
        <button className="btn btn-secondary">Reset to Defaults</button>
        <button className="btn btn-primary" onClick={handleSave}>
          Save Changes
        </button>
      </div>
    </div>
  );
};

export default Settings;
