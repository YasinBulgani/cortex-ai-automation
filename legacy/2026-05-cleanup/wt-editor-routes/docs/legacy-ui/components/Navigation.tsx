/**
 * Navigation Component
 * Top navigation bar for the dashboard
 */

import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import './Navigation.css';

/**
 * Navigation Bar Component
 */
const Navigation: React.FC = () => {
  const [showUserMenu, setShowUserMenu] = useState(false);

  return (
    <nav className="navbar">
      <div className="navbar-container">
        {/* Logo and branding */}
        <div className="navbar-brand">
          <Link to="/" className="logo">
            <span className="logo-icon">🧪</span>
            <span className="logo-text">BGTS</span>
          </Link>
          <span className="tagline">Test Automation Platform</span>
        </div>

        {/* Center: Search */}
        <div className="navbar-search">
          <input
            type="text"
            placeholder="Search projects, tests, reports..."
            className="search-input"
          />
          <button className="search-button">🔍</button>
        </div>

        {/* Right: User menu and icons */}
        <div className="navbar-right">
          {/* Connection status */}
          <div className="connection-status">
            <span className="status-indicator connected"></span>
            <span className="status-text">Connected</span>
          </div>

          {/* Notifications */}
          <button className="navbar-icon" title="Notifications">
            🔔
            <span className="notification-badge">3</span>
          </button>

          {/* Settings */}
          <Link to="/settings" className="navbar-icon" title="Settings">
            ⚙️
          </Link>

          {/* User menu */}
          <div className="user-menu">
            <button
              className="user-button"
              onClick={() => setShowUserMenu(!showUserMenu)}
              title="User menu"
            >
              👤
            </button>

            {showUserMenu && (
              <div className="user-dropdown">
                <a href="#profile">Profile</a>
                <a href="#settings">Settings</a>
                <a href="#help">Help & Documentation</a>
                <hr />
                <a href="#logout">Logout</a>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Quick actions bar */}
      <div className="navbar-actions">
        <button className="action-button primary">+ New Project</button>
        <button className="action-button">+ Run Tests</button>
        <button className="action-button">Generate Report</button>
      </div>
    </nav>
  );
};

export default Navigation;
