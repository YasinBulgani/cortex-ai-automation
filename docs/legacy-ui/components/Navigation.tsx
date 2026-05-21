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
    <nav className="navbar" role="navigation" aria-label="Ana navigasyon">
      <div className="navbar-container">
        {/* Logo and branding */}
        <div className="navbar-brand">
          <Link to="/" className="logo" aria-label="BGTS — Ana sayfaya git">
            <span className="logo-icon" aria-hidden="true">🧪</span>
            <span className="logo-text">BGTS</span>
          </Link>
          <span className="tagline">Test Automation Platform</span>
        </div>

        {/* Center: Search */}
        <div className="navbar-search" role="search">
          <label htmlFor="global-search" className="sr-only">Proje, test veya rapor ara</label>
          <input
            id="global-search"
            type="search"
            placeholder="Search projects, tests, reports..."
            className="search-input"
            aria-label="Proje, test veya rapor ara"
          />
          <button className="search-button" aria-label="Ara">
            <span aria-hidden="true">🔍</span>
          </button>
        </div>

        {/* Right: User menu and icons */}
        <div className="navbar-right">
          {/* Connection status */}
          <div className="connection-status" role="status" aria-live="polite" aria-label="Bağlantı durumu: Bağlı">
            <span className="status-indicator connected" aria-hidden="true"></span>
            <span className="status-text">Connected</span>
          </div>

          {/* Notifications */}
          <button className="navbar-icon" aria-label="Bildirimler (3 yeni bildirim)">
            <span aria-hidden="true">🔔</span>
            <span className="notification-badge" aria-hidden="true">3</span>
          </button>

          {/* Settings */}
          <Link to="/settings" className="navbar-icon" aria-label="Ayarlar">
            <span aria-hidden="true">⚙️</span>
          </Link>

          {/* User menu */}
          <div className="user-menu">
            <button
              className="user-button"
              onClick={() => setShowUserMenu(!showUserMenu)}
              aria-haspopup="true"
              aria-expanded={showUserMenu}
              aria-controls="user-dropdown-menu"
              aria-label="Kullanıcı menüsü"
            >
              <span aria-hidden="true">👤</span>
            </button>

            {showUserMenu && (
              <div
                id="user-dropdown-menu"
                className="user-dropdown"
                role="menu"
                aria-label="Kullanıcı seçenekleri"
              >
                <a href="#profile" role="menuitem">Profile</a>
                <a href="#settings" role="menuitem">Settings</a>
                <a href="#help" role="menuitem">Help &amp; Documentation</a>
                <hr aria-hidden="true" />
                <a href="#logout" role="menuitem">Logout</a>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Quick actions bar */}
      <div className="navbar-actions" role="toolbar" aria-label="Hızlı işlemler">
        <button className="action-button primary" aria-label="Yeni proje oluştur">+ New Project</button>
        <button className="action-button" aria-label="Test çalıştır">+ Run Tests</button>
        <button className="action-button" aria-label="Rapor oluştur">Generate Report</button>
      </div>
    </nav>
  );
};

export default Navigation;
