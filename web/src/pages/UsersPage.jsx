import React, { useState, useEffect } from 'react';
import { 
  getUsers, 
  getGroups, 
  createUser, 
  updateUser, 
  deleteUser, 
  createGroup, 
  updateGroup, 
  deleteGroup,
  addUserToGroup,
  removeUserFromGroup,
  getCurrentUser,
  getAuditLogs,
  getAuditLogStats
} from '../api/client';

const UsersPage = () => {
  const [activeTab, setActiveTab] = useState('users');
  const [users, setUsers] = useState([]);
  const [groups, setGroups] = useState([]);
  const [auditLogs, setAuditLogs] = useState([]);
  const [auditStats, setAuditStats] = useState(null);
  const [currentUser, setCurrentUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showUserModal, setShowUserModal] = useState(false);
  const [showGroupModal, setShowGroupModal] = useState(false);
  const [editingUser, setEditingUser] = useState(null);
  const [editingGroup, setEditingGroup] = useState(null);
  const [userForm, setUserForm] = useState({
    username: '',
    password: '',
    email: '',
    full_name: '',
    is_admin: false
  });
  const [groupForm, setGroupForm] = useState({
    name: '',
    description: ''
  });
  const [auditFilters, setAuditFilters] = useState({
    action: '',
    username: '',
    resource_type: '',
    status: '',
    start_date: '',
    end_date: ''
  });

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const [usersResponse, groupsResponse, currentUserResponse] = await Promise.all([
        getUsers(),
        getGroups(),
        getCurrentUser()
      ]);
      setUsers(usersResponse.data);
      setGroups(groupsResponse.data);
      setCurrentUser(currentUserResponse.data);
      
      // Check if current user is admin
      if (!currentUserResponse.data.is_admin) {
        setError('Access denied: Only administrators can access user management.');
        return;
      }
      
      // Load audit logs and stats if on audit tab
      if (activeTab === 'audit') {
        await loadAuditData();
      }
      
      setError(null);
    } catch (err) {
      setError('Failed to load data: ' + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  const loadAuditData = async () => {
    try {
      const [auditLogsResponse, auditStatsResponse] = await Promise.all([
        getAuditLogs({ limit: 100, ...auditFilters }),
        getAuditLogStats()
      ]);
      setAuditLogs(auditLogsResponse.data);
      setAuditStats(auditStatsResponse.data);
    } catch (err) {
      setError('Failed to load audit data: ' + (err.response?.data?.detail || err.message));
    }
  };

  const handleCreateUser = async (e) => {
    e.preventDefault();
    try {
      await createUser(userForm);
      setShowUserModal(false);
      setUserForm({ username: '', password: '', email: '', full_name: '', is_admin: false });
      loadData();
    } catch (err) {
      setError('Failed to create user: ' + (err.response?.data?.detail || err.message));
    }
  };

  const handleUpdateUser = async (e) => {
    e.preventDefault();
    try {
      const updateData = { ...userForm };
      if (!updateData.password) {
        delete updateData.password; // Don't update password if empty
      }
      await updateUser(editingUser.id, updateData);
      setShowUserModal(false);
      setEditingUser(null);
      setUserForm({ username: '', password: '', email: '', full_name: '', is_admin: false });
      loadData();
    } catch (err) {
      setError('Failed to update user: ' + (err.response?.data?.detail || err.message));
    }
  };

  const handleDeleteUser = async (userId) => {
    if (window.confirm('Are you sure you want to delete this user?')) {
      try {
        await deleteUser(userId);
        loadData();
      } catch (err) {
        setError('Failed to delete user: ' + (err.response?.data?.detail || err.message));
      }
    }
  };

  const handleCreateGroup = async (e) => {
    e.preventDefault();
    try {
      await createGroup(groupForm);
      setShowGroupModal(false);
      setGroupForm({ name: '', description: '' });
      loadData();
    } catch (err) {
      setError('Failed to create group: ' + (err.response?.data?.detail || err.message));
    }
  };

  const handleUpdateGroup = async (e) => {
    e.preventDefault();
    try {
      await updateGroup(editingGroup.id, groupForm);
      setShowGroupModal(false);
      setEditingGroup(null);
      setGroupForm({ name: '', description: '' });
      loadData();
    } catch (err) {
      setError('Failed to update group: ' + (err.response?.data?.detail || err.message));
    }
  };

  const handleDeleteGroup = async (groupId) => {
    if (window.confirm('Are you sure you want to delete this group?')) {
      try {
        await deleteGroup(groupId);
        loadData();
      } catch (err) {
        setError('Failed to delete group: ' + (err.response?.data?.detail || err.message));
      }
    }
  };

  const openUserModal = (user = null) => {
    if (user) {
      setEditingUser(user);
      setUserForm({
        username: user.username,
        password: '',
        email: user.email || '',
        full_name: user.full_name || '',
        is_admin: user.is_admin
      });
    } else {
      setEditingUser(null);
      setUserForm({ username: '', password: '', email: '', full_name: '', is_admin: false });
    }
    setShowUserModal(true);
  };

  const openGroupModal = (group = null) => {
    if (group) {
      setEditingGroup(group);
      setGroupForm({
        name: group.name,
        description: group.description || ''
      });
    } else {
      setEditingGroup(null);
      setGroupForm({ name: '', description: '' });
    }
    setShowGroupModal(true);
  };

  const handleTabChange = async (tab) => {
    setActiveTab(tab);
    if (tab === 'audit') {
      setLoading(true);
      await loadAuditData();
      setLoading(false);
    }
  };

  const handleAuditFilterChange = (field, value) => {
    setAuditFilters(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const applyAuditFilters = async () => {
    setLoading(true);
    await loadAuditData();
    setLoading(false);
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString() + ' ' + new Date(dateString).toLocaleTimeString();
  };

  const getStatusBadgeClass = (status) => {
    switch (status) {
      case 'success': return 'badge-success';
      case 'failure': return 'badge-danger';
      case 'error': return 'badge-danger';
      default: return 'badge-secondary';
    }
  };

  if (loading) {
    return (
      <div className="page-container">
        <div className="loading">Loading...</div>
      </div>
    );
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <h1>User Management</h1>
        <p>Manage users and groups for the IntentVerse system</p>
      </div>

      {error && (
        <div className="error-message">
          {error}
          <button onClick={() => setError(null)}>×</button>
        </div>
      )}

      <div className="tabs">
        <button 
          className={`tab ${activeTab === 'users' ? 'active' : ''}`}
          onClick={() => handleTabChange('users')}
        >
          Users ({users.length})
        </button>
        <button 
          className={`tab ${activeTab === 'groups' ? 'active' : ''}`}
          onClick={() => handleTabChange('groups')}
        >
          Groups ({groups.length})
        </button>
        <button 
          className={`tab ${activeTab === 'audit' ? 'active' : ''}`}
          onClick={() => handleTabChange('audit')}
        >
          Audit Logs
        </button>
      </div>

      {activeTab === 'users' && (
        <div className="tab-content">
          <div className="section-header">
            <h2>Users</h2>
            <button className="btn btn-primary" onClick={() => openUserModal()}>
              Add User
            </button>
          </div>

          <div className="table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Username</th>
                  <th>Full Name</th>
                  <th>Email</th>
                  <th>Admin</th>
                  <th>Active</th>
                  <th>Created</th>
                  <th>Last Login</th>
                  <th>Groups</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {users.map(user => (
                  <tr key={user.id}>
                    <td>{user.username}</td>
                    <td>{user.full_name || '-'}</td>
                    <td>{user.email || '-'}</td>
                    <td>
                      <span className={`badge ${user.is_admin ? 'badge-success' : 'badge-secondary'}`}>
                        {user.is_admin ? 'Yes' : 'No'}
                      </span>
                    </td>
                    <td>
                      <span className={`badge ${user.is_active ? 'badge-success' : 'badge-danger'}`}>
                        {user.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </td>
                    <td>{formatDate(user.created_at)}</td>
                    <td>{user.last_login ? formatDate(user.last_login) : 'Never'}</td>
                    <td>
                      {user.groups && user.groups.length > 0 ? (
                        <div className="group-tags">
                          {user.groups.map(group => (
                            <span key={group} className="group-tag">{group}</span>
                          ))}
                        </div>
                      ) : '-'}
                    </td>
                    <td>
                      <div className="action-buttons">
                        <button 
                          className="btn btn-sm btn-secondary"
                          onClick={() => openUserModal(user)}
                        >
                          Edit
                        </button>
                        {user.id !== currentUser?.id && (
                          <button 
                            className="btn btn-sm btn-danger"
                            onClick={() => handleDeleteUser(user.id)}
                          >
                            Delete
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {activeTab === 'groups' && (
        <div className="tab-content">
          <div className="section-header">
            <h2>Groups</h2>
            <button className="btn btn-primary" onClick={() => openGroupModal()}>
              Add Group
            </button>
          </div>

          <div className="table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Description</th>
                  <th>Created</th>
                  <th>Users</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {groups.map(group => (
                  <tr key={group.id}>
                    <td>{group.name}</td>
                    <td>{group.description || '-'}</td>
                    <td>{formatDate(group.created_at)}</td>
                    <td>
                      {group.users && group.users.length > 0 ? (
                        <div className="user-tags">
                          {group.users.map(username => (
                            <span key={username} className="user-tag">{username}</span>
                          ))}
                        </div>
                      ) : 'No users'}
                    </td>
                    <td>
                      <div className="action-buttons">
                        <button 
                          className="btn btn-sm btn-secondary"
                          onClick={() => openGroupModal(group)}
                        >
                          Edit
                        </button>
                        <button 
                          className="btn btn-sm btn-danger"
                          onClick={() => handleDeleteGroup(group.id)}
                        >
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {activeTab === 'audit' && (
        <div className="tab-content">
          <div className="section-header">
            <h2>Audit Logs</h2>
            <button className="btn btn-secondary" onClick={applyAuditFilters}>
              Refresh
            </button>
          </div>

          {/* Audit Statistics */}
          {auditStats && (
            <div className="audit-stats">
              <div className="stats-grid">
                <div className="stat-card">
                  <h3>Total Logs</h3>
                  <p className="stat-number">{auditStats.total_logs}</p>
                </div>
                <div className="stat-card">
                  <h3>Success</h3>
                  <p className="stat-number success">{auditStats.status_breakdown.success}</p>
                </div>
                <div className="stat-card">
                  <h3>Failures</h3>
                  <p className="stat-number failure">{auditStats.status_breakdown.failure}</p>
                </div>
                <div className="stat-card">
                  <h3>Errors</h3>
                  <p className="stat-number error">{auditStats.status_breakdown.error}</p>
                </div>
                <div className="stat-card">
                  <h3>Recent Activity (24h)</h3>
                  <p className="stat-number">{auditStats.recent_activity_24h}</p>
                </div>
              </div>
            </div>
          )}

          {/* Audit Filters */}
          <div className="audit-filters">
            <div className="filter-row">
              <div className="filter-group">
                <label>Action</label>
                <input
                  type="text"
                  value={auditFilters.action}
                  onChange={(e) => handleAuditFilterChange('action', e.target.value)}
                  placeholder="Filter by action..."
                />
              </div>
              <div className="filter-group">
                <label>Username</label>
                <input
                  type="text"
                  value={auditFilters.username}
                  onChange={(e) => handleAuditFilterChange('username', e.target.value)}
                  placeholder="Filter by username..."
                />
              </div>
              <div className="filter-group">
                <label>Resource Type</label>
                <select
                  value={auditFilters.resource_type}
                  onChange={(e) => handleAuditFilterChange('resource_type', e.target.value)}
                >
                  <option value="">All Types</option>
                  <option value="user">User</option>
                  <option value="group">Group</option>
                  <option value="tool">Tool</option>
                  <option value="content_pack">Content Pack</option>
                </select>
              </div>
              <div className="filter-group">
                <label>Status</label>
                <select
                  value={auditFilters.status}
                  onChange={(e) => handleAuditFilterChange('status', e.target.value)}
                >
                  <option value="">All Statuses</option>
                  <option value="success">Success</option>
                  <option value="failure">Failure</option>
                  <option value="error">Error</option>
                </select>
              </div>
              <div className="filter-group">
                <button className="btn btn-primary" onClick={applyAuditFilters}>
                  Apply Filters
                </button>
              </div>
            </div>
          </div>

          {/* Audit Logs Table */}
          <div className="table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Timestamp</th>
                  <th>User</th>
                  <th>Action</th>
                  <th>Resource</th>
                  <th>Status</th>
                  <th>IP Address</th>
                  <th>Details</th>
                </tr>
              </thead>
              <tbody>
                {auditLogs.map(log => (
                  <tr key={log.id}>
                    <td>{formatDate(log.timestamp)}</td>
                    <td>{log.username}</td>
                    <td>{log.action}</td>
                    <td>
                      {log.resource_type && (
                        <span>
                          {log.resource_type}
                          {log.resource_name && `: ${log.resource_name}`}
                        </span>
                      )}
                    </td>
                    <td>
                      <span className={`badge ${getStatusBadgeClass(log.status)}`}>
                        {log.status}
                      </span>
                    </td>
                    <td>{log.ip_address || '-'}</td>
                    <td>
                      {log.error_message && (
                        <span className="error-text">{log.error_message}</span>
                      )}
                      {log.details && Object.keys(log.details).length > 0 && (
                        <details className="audit-details">
                          <summary>View Details</summary>
                          <pre>{JSON.stringify(log.details, null, 2)}</pre>
                        </details>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* User Modal */}
      {showUserModal && (
        <div className="modal-overlay">
          <div className="modal">
            <div className="modal-header">
              <h3>{editingUser ? 'Edit User' : 'Create User'}</h3>
              <button 
                className="modal-close"
                onClick={() => setShowUserModal(false)}
              >
                ×
              </button>
            </div>
            <form onSubmit={editingUser ? handleUpdateUser : handleCreateUser}>
              <div className="modal-body">
                <div className="form-group">
                  <label>Username</label>
                  <input
                    type="text"
                    value={userForm.username}
                    onChange={(e) => setUserForm({...userForm, username: e.target.value})}
                    required
                    disabled={editingUser} // Can't change username when editing
                  />
                </div>
                <div className="form-group">
                  <label>Password {editingUser && '(leave empty to keep current)'}</label>
                  <input
                    type="password"
                    value={userForm.password}
                    onChange={(e) => setUserForm({...userForm, password: e.target.value})}
                    required={!editingUser}
                  />
                </div>
                <div className="form-group">
                  <label>Full Name</label>
                  <input
                    type="text"
                    value={userForm.full_name}
                    onChange={(e) => setUserForm({...userForm, full_name: e.target.value})}
                  />
                </div>
                <div className="form-group">
                  <label>Email</label>
                  <input
                    type="email"
                    value={userForm.email}
                    onChange={(e) => setUserForm({...userForm, email: e.target.value})}
                  />
                </div>
                <div className="form-group">
                  <label className="checkbox-label">
                    <input
                      type="checkbox"
                      checked={userForm.is_admin}
                      onChange={(e) => setUserForm({...userForm, is_admin: e.target.checked})}
                    />
                    Administrator
                  </label>
                </div>
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={() => setShowUserModal(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary">
                  {editingUser ? 'Update' : 'Create'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Group Modal */}
      {showGroupModal && (
        <div className="modal-overlay">
          <div className="modal">
            <div className="modal-header">
              <h3>{editingGroup ? 'Edit Group' : 'Create Group'}</h3>
              <button 
                className="modal-close"
                onClick={() => setShowGroupModal(false)}
              >
                ×
              </button>
            </div>
            <form onSubmit={editingGroup ? handleUpdateGroup : handleCreateGroup}>
              <div className="modal-body">
                <div className="form-group">
                  <label>Name</label>
                  <input
                    type="text"
                    value={groupForm.name}
                    onChange={(e) => setGroupForm({...groupForm, name: e.target.value})}
                    required
                    disabled={editingGroup} // Can't change group name when editing
                  />
                </div>
                <div className="form-group">
                  <label>Description</label>
                  <textarea
                    value={groupForm.description}
                    onChange={(e) => setGroupForm({...groupForm, description: e.target.value})}
                    rows="3"
                  />
                </div>
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={() => setShowGroupModal(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary">
                  {editingGroup ? 'Update' : 'Create'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default UsersPage;