/**
 * Main Application Component
 * Root component for BGTS_Test_Donusum Web Dashboard
 */

import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import './App.css';

// Components
import Navigation from './components/Navigation';
import Sidebar from './components/Sidebar';
import Dashboard from './pages/Dashboard';
import ProjectManager from './pages/ProjectManager';
import TestMonitor from './pages/TestMonitor';
import ReportViewer from './pages/ReportViewer';
import Analytics from './pages/Analytics';
import Settings from './pages/Settings';

// Services
import { WebSocketClient } from './services/websocket';
import { APIClient } from './services/api';

// Types
interface AppContextType {
  apiClient: APIClient;
  wsClient: WebSocketClient;
  currentProject: string | null;
  setCurrentProject: (projectId: string) => void;
}

export const AppContext = React.createContext<AppContextType | null>(null);

/**
 * Main App Component
 */
const App: React.FC = () => {
  const [currentProject, setCurrentProject] = useState<string | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Initialize services
  const apiClient = new APIClient({
    baseUrl: process.env.REACT_APP_API_URL || 'http://localhost:8000',
  });

  const wsClient = new WebSocketClient({
    url: process.env.REACT_APP_WS_URL || 'ws://localhost:8000/ws',
  });

  // Connect to WebSocket on mount
  useEffect(() => {
    const connectWebSocket = async () => {
      try {
        await wsClient.connect();
        setIsConnected(true);
      } catch (err) {
        setError('Failed to connect to WebSocket');
        console.error('WebSocket connection error:', err);
      }
    };

    connectWebSocket();

    // Cleanup on unmount
    return () => {
      wsClient.disconnect();
    };
  }, [wsClient]);

  // Provide context to child components
  const contextValue: AppContextType = {
    apiClient,
    wsClient,
    currentProject,
    setCurrentProject,
  };

  return (
    <AppContext.Provider value={contextValue}>
      <Router>
        <div className="app">
          {/* Global error notification */}
          {error && (
            <div className="error-notification">
              <p>{error}</p>
              <button onClick={() => setError(null)}>Dismiss</button>
            </div>
          )}

          {/* Connection status indicator */}
          {!isConnected && (
            <div className="connection-warning">
              <span className="indicator"></span>
              Connecting to server...
            </div>
          )}

          {/* Navigation bar */}
          <Navigation />

          <div className="app-container">
            {/* Sidebar */}
            <Sidebar />

            {/* Main content */}
            <main className="main-content">
              <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/projects" element={<ProjectManager />} />
                <Route path="/tests/:testId" element={<TestMonitor />} />
                <Route path="/reports/:reportId" element={<ReportViewer />} />
                <Route path="/analytics" element={<Analytics />} />
                <Route path="/settings" element={<Settings />} />
                {/* 404 fallback */}
                <Route path="*" element={<NotFound />} />
              </Routes>
            </main>
          </div>
        </div>
      </Router>
    </AppContext.Provider>
  );
};

/**
 * Not Found Page
 */
const NotFound: React.FC = () => (
  <div className="not-found">
    <h1>404 - Page Not Found</h1>
    <p>The page you're looking for doesn't exist.</p>
    <a href="/">Go back to dashboard</a>
  </div>
);

export default App;
