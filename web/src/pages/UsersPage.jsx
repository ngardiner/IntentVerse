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
  getCurrentUser
} from '../api/client';

const UsersPage = () => {
  const [activeTab, setActiveTab] = useState('users');
  const [users, setUsers] = useState([]);
  const [groups, setGroups] = useState([]);
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
      setError(null);
    } catch (err) {
      setError('Failed to load data: ' + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
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

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString() + ' ' + new Date(dateString).toLocaleTimeString();
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
          onClick={() => setActiveTab('users')}
        >
          Users ({users.length})
        </button>
        <button 
          className={`tab ${activeTab === 'groups' ? 'active' : ''}`}
          onClick={() => setActiveTab('groups')}
        >
          Groups ({groups.length})
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