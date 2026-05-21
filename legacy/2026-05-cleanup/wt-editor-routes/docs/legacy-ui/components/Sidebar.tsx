/**
 * Sidebar Component
 * Left navigation sidebar with project selector and navigation links
 */

import React, { useState, useContext } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { AppContext } from '../App';
import './Sidebar.css';

interface SidebarProject {
  id: string;
  name: string;
  icon: string;
}

/**
 * Sidebar Navigation Component
 */
const Sidebar: React.FC = () => {
  const [showProjectMenu, setShowProjectMenu] = useState(false);
  const [projects, setProjects] = useState<SidebarProject[]>([
    { id: '1', name: 'Ecommerce Platform', icon: '🛒' },
    { id: '2', name: 'Auth System', icon: '🔐' },
    { id: '3', name: 'Payment Gateway', icon: '💳' },
  ]);

  const context = useContext(AppContext);
  const location = useLocation();

  const handleProjectSelect = (projectId: string) => {
    if (context) {
      context.setCurrentProject(projectId);
    }
    setShowProjectMenu(false);
  };

  const isActive = (path: string) => location.pathname === path;

  return (
    <aside className="sidebar">
      {/* Project Selector */}
      <div className="project-selector">
        <div className="project-selector-header">
          <h3>Projects</h3>
          <button className="add-project-btn" title="Add new project">+</button>
        </div>

        <div className="project-dropdown">
          <button
            className="project-toggle"
            onClick={() => setShowProjectMenu(!showProjectMenu)}
          >
            <span className="project-icon">📦</span>
            <span className="project-label">
              {context?.currentProject ? 'Active Project' : 'Select Project'}
            </span>
            <span className={`dropdown-arrow ${showProjectMenu ? 'open' : ''}`}>▼</span>
          </button>

          {showProjectMenu && (
            <div className="project-list">
              {projects.map((project) => (
                <button
                  key={project.id}
                  className={`project-item ${
                    context?.currentProject === project.id ? 'active' : ''
                  }`}
                  onClick={() => handleProjectSelect(project.id)}
                >
                  <span className="project-item-icon">{project.icon}</span>
                  <span className="project-item-name">{project.name}</span>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Navigation Links */}
      <nav className="sidebar-nav">
        <div className="nav-section">
          <h4 className="nav-section-title">Main</h4>
          <ul className="nav-links">
            <li>
              <Link
                to="/"
                className={`nav-link ${isActive('/') ? 'active' : ''}`}
              >
                <span className="nav-icon">📊</span>
                <span className="nav-text">Dashboard</span>
              </Link>
            </li>
            <li>
              <Link
                to="/projects"
                className={`nav-link ${isActive('/projects') ? 'active' : ''}`}
              >
                <span className="nav-icon">📁</span>
                <span className="nav-text">Projects</span>
              </Link>
            </li>
          </ul>
        </div>

        <div className="nav-section">
          <h4 className="nav-section-title">Testing</h4>
          <ul className="nav-links">
            <li>
              <Link to="/tests" className="nav-link">
                <span className="nav-icon">▶️</span>
                <span className="nav-text">Run Tests</span>
              </Link>
            </li>
            <li>
              <Link to="/test-monitor" className="nav-link">
                <span className="nav-icon">👁️</span>
                <span className="nav-text">Monitor</span>
              </Link>
            </li>
          </ul>
        </div>

        <div className="nav-section">
          <h4 className="nav-section-title">Analytics</h4>
          <ul className="nav-links">
            <li>
              <Link
                to="/analytics"
                className={`nav-link ${isActive('/analytics') ? 'active' : ''}`}
              >
                <span className="nav-icon">📈</span>
                <span className="nav-text">Analytics</span>
              </Link>
            </li>
            <li>
              <Link to="/reports" className="nav-link">
                <span className="nav-icon">📋</span>
                <span className="nav-text">Reports</span>
              </Link>
            </li>
            <li>
              <Link to="/trends" className="nav-link">
                <span className="nav-icon">📉</span>
                <span className="nav-text">Trends</span>
              </Link>
            </li>
          </ul>
        </div>

        <div className="nav-section">
          <h4 className="nav-section-title">Configuration</h4>
          <ul className="nav-links">
            <li>
              <Link
                to="/settings"
                className={`nav-link ${isActive('/settings') ? 'active' : ''}`}
              >
                <span className="nav-icon">⚙️</span>
                <span className="nav-text">Settings</span>
              </Link>
            </li>
            <li>
              <Link to="/api-docs" className="nav-link">
                <span className="nav-icon">📚</span>
                <span className="nav-text">API Docs</span>
              </Link>
            </li>
          </ul>
        </div>
      </nav>

      {/* Quick Stats */}
      <div className="sidebar-stats">
        <div className="stat-item">
          <span className="stat-label">Tests Today</span>
          <span className="stat-value">124</span>
        </div>
        <div className="stat-item">
          <span className="stat-label">Pass Rate</span>
          <span className="stat-value">98.4%</span>
        </div>
        <div className="stat-item">
          <span className="stat-label">Avg Duration</span>
          <span className="stat-value">2.3s</span>
        </div>
      </div>

      {/* Footer */}
      <div className="sidebar-footer">
        <p className="version">v1.0.0-beta</p>
        <div className="sidebar-actions">
          <button className="footer-btn" title="Help">❓</button>
          <button className="footer-btn" title="Feedback">💬</button>
          <button className="footer-btn" title="Status">🟢</button>
        </div>
      </div>
    </aside>
  );
};

export default Sidebar;
