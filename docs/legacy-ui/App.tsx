/**
 * Main Application Component
 * Root component for BGTS_Test_Donusum Web Dashboard
 */

import React, { useState, useEffect, useRef } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
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

  // useRef ile sabit instance'lar — her render'da yeniden oluşturulmaması için
  const apiClientRef = useRef<APIClient>(new APIClient({
    baseUrl: process.env.REACT_APP_API_URL || 'http://localhost:8000',
  }));
  const wsClientRef = useRef<WebSocketClient>(new WebSocketClient({
    url: process.env.REACT_APP_WS_URL || 'ws://localhost:8000/ws',
  }));

  const apiClient = apiClientRef.current;
  const wsClient = wsClientRef.current;

  // Connect to WebSocket on mount — bağımlılık dizisi boş: yalnızca mount'ta çalışır
  useEffect(() => {
    const connectWebSocket = async () => {
      try {
        await wsClientRef.current.connect();
        setIsConnected(true);
      } catch (err) {
        setError('Failed to connect to WebSocket');
        console.error('WebSocket connection error:', err);
      }
    };

    // Kaydedilen token varsa auth header'ı ayarla
    const savedToken = localStorage.getItem('bgts_access_token');
    if (savedToken) {
      apiClientRef.current.setAuthToken(savedToken);
    }

    connectWebSocket();

    return () => {
      wsClientRef.current.disconnect();
    };
  }, []);

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
                {/* Hem liste hem de tekil test sayfası */}
                <Route path="/tests" element={<TestMonitor />} />
                <Route path="/tests/:testId" element={<TestMonitor />} />
                {/* /test-monitor → /tests yönlendirmesi */}
                <Route path="/test-monitor" element={<Navigate to="/tests" replace />} />
                {/* Hem liste hem de tekil rapor sayfası */}
                <Route path="/reports" element={<ReportViewer />} />
                <Route path="/reports/:reportId" element={<ReportViewer />} />
                <Route path="/analytics" element={<Analytics />} />
                {/* /trends → /analytics yönlendirmesi */}
                <Route path="/trends" element={<Navigate to="/analytics" replace />} />
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
