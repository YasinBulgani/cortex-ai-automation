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
    <aside className="sidebar" aria-label="Yan menü">
      {/* Project Selector */}
      <div className="project-selector">
        <div className="project-selector-header">
          <h3 id="project-selector-heading">Projects</h3>
          <button className="add-project-btn" aria-label="Yeni proje ekle">+</button>
        </div>

        <div className="project-dropdown">
          <button
            className="project-toggle"
            onClick={() => setShowProjectMenu(!showProjectMenu)}
            aria-haspopup="listbox"
            aria-expanded={showProjectMenu}
            aria-controls="project-list"
            aria-labelledby="project-selector-heading"
          >
            <span className="project-icon" aria-hidden="true">📦</span>
            <span className="project-label">
              {context?.currentProject ? 'Active Project' : 'Select Project'}
            </span>
            <span className={`dropdown-arrow ${showProjectMenu ? 'open' : ''}`} aria-hidden="true">▼</span>
          </button>

          {showProjectMenu && (
            <div id="project-list" className="project-list" role="listbox" aria-label="Proje listesi">
              {projects.map((project) => (
                <button
                  key={project.id}
                  className={`project-item ${
                    context?.currentProject === project.id ? 'active' : ''
                  }`}
                  onClick={() => handleProjectSelect(project.id)}
                  role="option"
                  aria-selected={context?.currentProject === project.id}
                >
                  <span className="project-item-icon" aria-hidden="true">{project.icon}</span>
                  <span className="project-item-name">{project.name}</span>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Navigation Links */}
      <nav className="sidebar-nav" aria-label="Uygulama navigasyonu">
        <div className="nav-section">
          <h4 className="nav-section-title" id="nav-main">Main</h4>
          <ul className="nav-links" aria-labelledby="nav-main">
            <li>
              <Link
                to="/"
                className={`nav-link ${isActive('/') ? 'active' : ''}`}
                aria-current={isActive('/') ? 'page' : undefined}
              >
                <span className="nav-icon" aria-hidden="true">📊</span>
                <span className="nav-text">Dashboard</span>
              </Link>
            </li>
            <li>
              <Link
                to="/projects"
                className={`nav-link ${isActive('/projects') ? 'active' : ''}`}
                aria-current={isActive('/projects') ? 'page' : undefined}
              >
                <span className="nav-icon" aria-hidden="true">📁</span>
                <span className="nav-text">Projects</span>
              </Link>
            </li>
          </ul>
        </div>

        <div className="nav-section">
          <h4 className="nav-section-title" id="nav-testing">Testing</h4>
          <ul className="nav-links" aria-labelledby="nav-testing">
            <li>
              <Link
                to="/tests"
                className={`nav-link ${isActive('/tests') ? 'active' : ''}`}
                aria-current={isActive('/tests') ? 'page' : undefined}
              >
                <span className="nav-icon" aria-hidden="true">▶️</span>
                <span className="nav-text">Run Tests</span>
              </Link>
            </li>
            <li>
              <Link
                to="/tests"
                className={`nav-link ${location.pathname.startsWith('/tests') ? 'active' : ''}`}
                aria-current={location.pathname.startsWith('/tests') ? 'page' : undefined}
              >
                <span className="nav-icon" aria-hidden="true">👁️</span>
                <span className="nav-text">Monitor</span>
              </Link>
            </li>
          </ul>
        </div>

        <div className="nav-section">
          <h4 className="nav-section-title" id="nav-analytics">Analytics</h4>
          <ul className="nav-links" aria-labelledby="nav-analytics">
            <li>
              <Link
                to="/analytics"
                className={`nav-link ${isActive('/analytics') ? 'active' : ''}`}
                aria-current={isActive('/analytics') ? 'page' : undefined}
              >
                <span className="nav-icon" aria-hidden="true">📈</span>
                <span className="nav-text">Analytics</span>
              </Link>
            </li>
            <li>
              <Link
                to="/reports"
                className={`nav-link ${location.pathname.startsWith('/reports') ? 'active' : ''}`}
                aria-current={location.pathname.startsWith('/reports') ? 'page' : undefined}
              >
                <span className="nav-icon" aria-hidden="true">📋</span>
                <span className="nav-text">Reports</span>
              </Link>
            </li>
            <li>
              <Link
                to="/analytics"
                className={`nav-link ${isActive('/analytics') ? 'active' : ''}`}
                aria-current={isActive('/analytics') ? 'page' : undefined}
              >
                <span className="nav-icon" aria-hidden="true">📉</span>
                <span className="nav-text">Trends</span>
              </Link>
            </li>
          </ul>
        </div>

        <div className="nav-section">
          <h4 className="nav-section-title" id="nav-config">Configuration</h4>
          <ul className="nav-links" aria-labelledby="nav-config">
            <li>
              <Link
                to="/settings"
                className={`nav-link ${isActive('/settings') ? 'active' : ''}`}
                aria-current={isActive('/settings') ? 'page' : undefined}
              >
                <span className="nav-icon" aria-hidden="true">⚙️</span>
                <span className="nav-text">Settings</span>
              </Link>
            </li>
            <li>
              <a
                href={`${process.env.REACT_APP_API_URL || 'http://localhost:8000'}/docs`}
                className="nav-link"
                target="_blank"
                rel="noopener noreferrer"
                aria-label="API Dokümantasyonu (yeni sekmede açılır)"
              >
                <span className="nav-icon" aria-hidden="true">📚</span>
                <span className="nav-text">API Docs</span>
              </a>
            </li>
          </ul>
        </div>
      </nav>

      {/* Quick Stats */}
      <div className="sidebar-stats" aria-label="Hızlı istatistikler" role="region">
        <div className="stat-item">
          <span className="stat-label">Tests Today</span>
          <span className="stat-value" aria-label="Bugün 124 test">124</span>
        </div>
        <div className="stat-item">
          <span className="stat-label">Pass Rate</span>
          <span className="stat-value" aria-label="Geçme oranı %98.4">98.4%</span>
        </div>
        <div className="stat-item">
          <span className="stat-label">Avg Duration</span>
          <span className="stat-value" aria-label="Ortalama süre 2.3 saniye">2.3s</span>
        </div>
      </div>

      {/* Footer */}
      <div className="sidebar-footer">
        <p className="version" aria-label="Versiyon 1.0.0-beta">v1.0.0-beta</p>
        <div className="sidebar-actions">
          <button className="footer-btn" aria-label="Yardım">
            <span aria-hidden="true">❓</span>
          </button>
          <button className="footer-btn" aria-label="Geri bildirim gönder">
            <span aria-hidden="true">💬</span>
          </button>
          <button className="footer-btn" aria-label="Sistem durumu: çevrimiçi">
            <span aria-hidden="true">🟢</span>
          </button>
        </div>
      </div>
    </aside>
  );
};

export default Sidebar;
