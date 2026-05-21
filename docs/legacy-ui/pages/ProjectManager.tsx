/**
 * Project Manager Page
 * Manage multiple test projects and configurations
 */

import React, { useState } from 'react';
import '../styles/ProjectManager.css';

interface Project {
  id: string;
  name: string;
  description: string;
  status: 'active' | 'inactive' | 'archived';
  environment: string;
  lastRun: string;
  testCount: number;
  passRate: number;
  owner: string;
  createdAt: string;
}

/**
 * Project Manager Component
 */
const ProjectManager: React.FC = () => {
  const [projects, setProjects] = useState<Project[]>([
    {
      id: '1',
      name: 'E-commerce Platform',
      description: 'Full e-commerce site testing including payment and checkout flows',
      status: 'active',
      environment: 'Production',
      lastRun: '2 hours ago',
      testCount: 156,
      passRate: 97.8,
      owner: 'John Doe',
      createdAt: '2025-01-15',
    },
    {
      id: '2',
      name: 'Authentication System',
      description: 'OAuth2 and JWT-based authentication testing',
      status: 'active',
      environment: 'Staging',
      lastRun: '4 hours ago',
      testCount: 87,
      passRate: 100,
      owner: 'Jane Smith',
      createdAt: '2025-02-01',
    },
    {
      id: '3',
      name: 'Payment Gateway',
      description: 'Stripe and PayPal integration testing',
      status: 'active',
      environment: 'Production',
      lastRun: '6 hours ago',
      testCount: 42,
      passRate: 95.2,
      owner: 'Mike Johnson',
      createdAt: '2025-02-15',
    },
    {
      id: '4',
      name: 'Mobile App - iOS',
      description: 'iOS mobile application testing',
      status: 'inactive',
      environment: 'Staging',
      lastRun: '3 days ago',
      testCount: 120,
      passRate: 92.5,
      owner: 'Sarah Davis',
      createdAt: '2025-03-01',
    },
    {
      id: '5',
      name: 'API Services',
      description: 'REST API and GraphQL endpoint testing',
      status: 'active',
      environment: 'Development',
      lastRun: '1 hour ago',
      testCount: 203,
      passRate: 98.5,
      owner: 'Tom Wilson',
      createdAt: '2025-03-15',
    },
  ]);

  const [showNewProjectForm, setShowNewProjectForm] = useState(false);
  const [filterStatus, setFilterStatus] = useState<'all' | 'active' | 'inactive' | 'archived'>('all');
  const [searchQuery, setSearchQuery] = useState('');

  const filteredProjects = projects.filter((project) => {
    const matchesFilter = filterStatus === 'all' || project.status === filterStatus;
    const matchesSearch =
      project.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      project.description.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesFilter && matchesSearch;
  });

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
        return '#10b981';
      case 'inactive':
        return '#f59e0b';
      case 'archived':
        return '#6b7280';
      default:
        return '#3b82f6';
    }
  };

  return (
    <div className="project-manager">
      {/* Header */}
      <div className="manager-header">
        <h1>Project Manager</h1>
        <p className="subtitle">Manage and monitor your test projects</p>

        <button
          className="btn btn-primary"
          onClick={() => setShowNewProjectForm(!showNewProjectForm)}
        >
          ➕ New Project
        </button>
      </div>

      {/* New Project Form */}
      {showNewProjectForm && (
        <div className="new-project-form">
          <h2>Create New Project</h2>

          <form className="form">
            <div className="form-group">
              <label>Project Name *</label>
              <input type="text" placeholder="Enter project name" />
            </div>

            <div className="form-row">
              <div className="form-group">
                <label>Description</label>
                <textarea placeholder="Project description"></textarea>
              </div>
            </div>

            <div className="form-row">
              <div className="form-group">
                <label>Environment *</label>
                <select>
                  <option>Development</option>
                  <option>Staging</option>
                  <option>Production</option>
                </select>
              </div>

              <div className="form-group">
                <label>Owner</label>
                <input type="text" placeholder="Project owner" />
              </div>
            </div>

            <div className="form-actions">
              <button type="button" className="btn btn-secondary">
                Cancel
              </button>
              <button type="submit" className="btn btn-primary">
                Create Project
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Filters and Search */}
      <div className="manager-controls">
        <div className="search-box">
          <input
            type="text"
            placeholder="Search projects..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="search-input"
          />
          <span className="search-icon">🔍</span>
        </div>

        <div className="filter-buttons">
          <button
            className={`filter-btn ${filterStatus === 'all' ? 'active' : ''}`}
            onClick={() => setFilterStatus('all')}
          >
            All ({projects.length})
          </button>
          <button
            className={`filter-btn ${filterStatus === 'active' ? 'active' : ''}`}
            onClick={() => setFilterStatus('active')}
          >
            Active ({projects.filter((p) => p.status === 'active').length})
          </button>
          <button
            className={`filter-btn ${filterStatus === 'inactive' ? 'active' : ''}`}
            onClick={() => setFilterStatus('inactive')}
          >
            Inactive ({projects.filter((p) => p.status === 'inactive').length})
          </button>
          <button
            className={`filter-btn ${filterStatus === 'archived' ? 'active' : ''}`}
            onClick={() => setFilterStatus('archived')}
          >
            Archived ({projects.filter((p) => p.status === 'archived').length})
          </button>
        </div>
      </div>

      {/* Projects Grid */}
      <div className="projects-grid">
        {filteredProjects.map((project) => (
          <div key={project.id} className="project-card">
            {/* Header */}
            <div className="project-card-header">
              <div className="project-title-section">
                <h3 className="project-name">{project.name}</h3>
                <span
                  className="project-status"
                  style={{ backgroundColor: getStatusColor(project.status) }}
                >
                  {project.status}
                </span>
              </div>

              <button className="project-menu-btn">⋯</button>
            </div>

            {/* Description */}
            <p className="project-description">{project.description}</p>

            {/* Details */}
            <div className="project-details">
              <div className="detail-item">
                <span className="detail-label">Environment</span>
                <span className="detail-value">{project.environment}</span>
              </div>

              <div className="detail-item">
                <span className="detail-label">Owner</span>
                <span className="detail-value">{project.owner}</span>
              </div>

              <div className="detail-item">
                <span className="detail-label">Tests</span>
                <span className="detail-value">{project.testCount}</span>
              </div>

              <div className="detail-item">
                <span className="detail-label">Pass Rate</span>
                <span
                  className="detail-value"
                  style={{
                    color: project.passRate >= 95 ? '#10b981' : project.passRate >= 85 ? '#f59e0b' : '#ef4444',
                  }}
                >
                  {project.passRate}%
                </span>
              </div>
            </div>

            {/* Stats */}
            <div className="project-stats">
              <div className="stat">
                <span className="stat-icon">⏱️</span>
                <span className="stat-text">Last run {project.lastRun}</span>
              </div>

              <div className="stat">
                <span className="stat-icon">📅</span>
                <span className="stat-text">Created {project.createdAt}</span>
              </div>
            </div>

            {/* Actions */}
            <div className="project-actions">
              <button className="action-btn primary">▶ Run Tests</button>
              <button className="action-btn">📊 View Report</button>
              <button className="action-btn">⚙️ Configure</button>
            </div>
          </div>
        ))}
      </div>

      {/* Empty State */}
      {filteredProjects.length === 0 && (
        <div className="empty-state">
          <h3>No projects found</h3>
          <p>Create a new project or adjust your filters to get started.</p>
          <button className="btn btn-primary">Create First Project</button>
        </div>
      )}

      {/* Statistics */}
      <div className="manager-stats">
        <div className="stat-box">
          <span className="stat-number">{projects.length}</span>
          <span className="stat-label">Total Projects</span>
        </div>

        <div className="stat-box">
          <span className="stat-number">{projects.filter((p) => p.status === 'active').length}</span>
          <span className="stat-label">Active Projects</span>
        </div>

        <div className="stat-box">
          <span className="stat-number">{projects.reduce((sum, p) => sum + p.testCount, 0)}</span>
          <span className="stat-label">Total Tests</span>
        </div>

        <div className="stat-box">
          <span className="stat-number">
            {(
              projects.reduce((sum, p) => sum + p.passRate, 0) / projects.length
            ).toFixed(1)}
            %
          </span>
          <span className="stat-label">Avg Pass Rate</span>
        </div>
      </div>
    </div>
  );
};

export default ProjectManager;
