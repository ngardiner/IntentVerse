import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import UsersPage from './UsersPage';
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

// Mock the API client
jest.mock('../api/client');

describe('UsersPage', () => {
  const mockCurrentUser = {
    id: 1,
    username: 'admin',
    email: 'admin@example.com',
    full_name: 'Administrator',
    is_admin: true
  };

  const mockUsers = [
    {
      id: 1,
      username: 'admin',
      email: 'admin@example.com',
      full_name: 'Administrator',
      is_admin: true,
      is_active: true,
      created_at: '2024-01-01T00:00:00Z'
    },
    {
      id: 2,
      username: 'user1',
      email: 'user1@example.com',
      full_name: 'User One',
      is_admin: false,
      is_active: true,
      created_at: '2024-01-02T00:00:00Z'
    }
  ];

  const mockGroups = [
    {
      id: 1,
      name: 'administrators',
      description: 'System administrators',
      created_at: '2024-01-01T00:00:00Z'
    },
    {
      id: 2,
      name: 'users',
      description: 'Regular users',
      created_at: '2024-01-01T00:00:00Z'
    }
  ];

  const mockAuditLogs = [
    {
      id: 1,
      action: 'user.create',
      username: 'admin',
      resource_type: 'user',
      resource_id: '2',
      status: 'success',
      timestamp: '2024-01-02T00:00:00Z',
      details: { created_user: 'user1' }
    }
  ];

  const mockAuditStats = {
    total_logs: 100,
    status_breakdown: {
      success: 95,
      failure: 3,
      error: 2
    },
    recent_activity_24h: 25
  };

  beforeEach(() => {
    jest.clearAllMocks();
    getCurrentUser.mockResolvedValue({ data: mockCurrentUser });
    getUsers.mockResolvedValue({ data: mockUsers });
    getGroups.mockResolvedValue({ data: mockGroups });
    getAuditLogs.mockResolvedValue({ data: mockAuditLogs });
    getAuditLogStats.mockResolvedValue({ data: mockAuditStats });
  });

  describe('Initial Loading and Access Control', () => {
    it('renders loading state initially', () => {
      render(<UsersPage />);
      
      expect(screen.getByText('Loading...')).toBeInTheDocument();
    });

    it('loads data on mount', async () => {
      render(<UsersPage />);
      
      await waitFor(() => {
        expect(getCurrentUser).toHaveBeenCalledTimes(1);
        expect(getUsers).toHaveBeenCalledTimes(1);
        expect(getGroups).toHaveBeenCalledTimes(1);
      });
    });

    it('displays access denied for non-admin users', async () => {
      getCurrentUser.mockResolvedValue({ 
        data: { ...mockCurrentUser, is_admin: false } 
      });
      
      render(<UsersPage />);
      
      await waitFor(() => {
        expect(screen.getByText('Access denied: Only administrators can access user management.')).toBeInTheDocument();
      });
    });

    it('displays users tab by default for admin users', async () => {
      render(<UsersPage />);
      
      await waitFor(() => {
        expect(screen.getByText('Users')).toBeInTheDocument();
        expect(screen.getByText('admin')).toBeInTheDocument();
        expect(screen.getByText('user1')).toBeInTheDocument();
      });
    });
  });

  describe('Tab Navigation', () => {
    it('switches between tabs correctly', async () => {
      const user = userEvent.setup();
      render(<UsersPage />);
      
      await waitFor(() => {
        expect(screen.getByText('admin')).toBeInTheDocument();
      });

      // Switch to Groups tab
      const groupsTab = screen.getByRole('button', { name: /Groups/ });
      await user.click(groupsTab);
      
      // Wait for the groups tab to become active and content to render
      await waitFor(() => {
        expect(groupsTab).toHaveClass('active');
      });
      
      // Now check for the group names
      await waitFor(() => {
        expect(screen.getByText('administrators')).toBeInTheDocument();
        expect(screen.getByText('users')).toBeInTheDocument();
      });

      // Switch to Audit tab
      const auditTab = screen.getByRole('button', { name: /Audit Logs/ });
      await user.click(auditTab);
      
      await waitFor(() => {
        expect(getAuditLogs).toHaveBeenCalled();
        expect(getAuditLogStats).toHaveBeenCalled();
      });
    });

    it('loads audit data when switching to audit tab', async () => {
      const user = userEvent.setup();
      render(<UsersPage />);
      
      await waitFor(() => {
        expect(screen.getByText('admin')).toBeInTheDocument();
      });

      const auditTab = screen.getByRole('button', { name: /Audit Logs/ });
      await user.click(auditTab);
      
      await waitFor(() => {
        expect(getAuditLogs).toHaveBeenCalledTimes(1);
        expect(getAuditLogStats).toHaveBeenCalledTimes(1);
      });
    });
  });

  describe('Users Management', () => {
    it('displays users list correctly', async () => {
      render(<UsersPage />);
      
      await waitFor(() => {
        expect(screen.getByText('admin')).toBeInTheDocument();
        expect(screen.getByText('user1')).toBeInTheDocument();
        expect(screen.getByText('admin@example.com')).toBeInTheDocument();
        expect(screen.getByText('user1@example.com')).toBeInTheDocument();
      });
    });

    it('opens create user modal when add button is clicked', async () => {
      const user = userEvent.setup();
      render(<UsersPage />);
      
      await waitFor(() => {
        expect(screen.getByText('Add User')).toBeInTheDocument();
      });

      const addButton = screen.getByText('Add User');
      await user.click(addButton);
      
      expect(screen.getByText('Create User')).toBeInTheDocument();
      expect(screen.getByLabelText('Username')).toBeInTheDocument();
      expect(screen.getByLabelText('Email')).toBeInTheDocument();
    });

    it('creates new user successfully', async () => {
      const user = userEvent.setup();
      createUser.mockResolvedValue({ data: { id: 3, username: 'newuser' } });
      
      render(<UsersPage />);
      
      await waitFor(() => {
        expect(screen.getByText('Add User')).toBeInTheDocument();
      });

      // Open create modal
      const addButton = screen.getByText('Add User');
      await user.click(addButton);
      
      // Fill form
      await user.type(screen.getByLabelText('Username'), 'newuser');
      await user.type(screen.getByLabelText('Email'), 'newuser@example.com');
      await user.type(screen.getByLabelText('Password'), 'password123');
      await user.type(screen.getByLabelText('Full Name'), 'New User');
      
      // Submit form
      const createButton = screen.getByText('Create');
      await user.click(createButton);
      
      await waitFor(() => {
        expect(createUser).toHaveBeenCalledWith({
          username: 'newuser',
          email: 'newuser@example.com',
          password: 'password123',
          full_name: 'New User',
          is_admin: false
        });
      });
    });

    it('opens edit user modal when edit button is clicked', async () => {
      const user = userEvent.setup();
      render(<UsersPage />);
      
      await waitFor(() => {
        expect(screen.getByText('user1')).toBeInTheDocument();
      });

      // Find and click edit button for user1
      const editButtons = screen.getAllByText('Edit');
      await user.click(editButtons[1]); // Second edit button (for user1)
      
      expect(screen.getByText('Edit User')).toBeInTheDocument();
      expect(screen.getByDisplayValue('user1')).toBeInTheDocument();
    });

    it('updates user successfully', async () => {
      const user = userEvent.setup();
      updateUser.mockResolvedValue({ data: { id: 2, email: 'user1_updated@example.com' } });
      
      render(<UsersPage />);
      
      await waitFor(() => {
        expect(screen.getByText('user1')).toBeInTheDocument();
      });

      // Open edit modal
      const editButtons = screen.getAllByText('Edit');
      await user.click(editButtons[1]);
      
      // Update email (username is disabled when editing)
      const emailInput = screen.getByDisplayValue('user1@example.com');
      await user.clear(emailInput);
      await user.type(emailInput, 'user1_updated@example.com');
      
      // Submit form
      const updateButton = screen.getByText('Update');
      await user.click(updateButton);
      
      await waitFor(() => {
        expect(updateUser).toHaveBeenCalledWith(2, expect.objectContaining({
          email: 'user1_updated@example.com'
        }));
      });
    });

    it('deletes user with confirmation', async () => {
      const user = userEvent.setup();
      deleteUser.mockResolvedValue({ data: { success: true } });
      
      // Mock window.confirm
      const confirmSpy = jest.spyOn(window, 'confirm').mockReturnValue(true);
      
      render(<UsersPage />);
      
      await waitFor(() => {
        expect(screen.getByText('user1')).toBeInTheDocument();
      });

      // Wait for all delete buttons to be rendered
      await waitFor(() => {
        const deleteButtons = screen.getAllByText('Delete');
        expect(deleteButtons).toHaveLength(1); // Only user1 should have delete button (admin can't delete themselves)
      });

      // Find and click delete button for user1
      const deleteButtons = screen.getAllByText('Delete');
      await user.click(deleteButtons[0]); // First (and only) delete button (for user1)
      
      expect(confirmSpy).toHaveBeenCalledWith('Are you sure you want to delete user "user1"?');
      
      await waitFor(() => {
        expect(deleteUser).toHaveBeenCalledWith(2);
      });
      
      confirmSpy.mockRestore();
    });

    it('cancels user deletion when confirmation is denied', async () => {
      const user = userEvent.setup();
      
      // Mock window.confirm to return false
      const confirmSpy = jest.spyOn(window, 'confirm').mockReturnValue(false);
      
      render(<UsersPage />);
      
      await waitFor(() => {
        expect(screen.getByText('user1')).toBeInTheDocument();
      });

      // Wait for all delete buttons to be rendered
      await waitFor(() => {
        const deleteButtons = screen.getAllByText('Delete');
        expect(deleteButtons).toHaveLength(1); // Only user1 should have delete button (admin can't delete themselves)
      });

      const deleteButtons = screen.getAllByText('Delete');
      await user.click(deleteButtons[0]); // First (and only) delete button (for user1)
      
      expect(confirmSpy).toHaveBeenCalled();
      expect(deleteUser).not.toHaveBeenCalled();
      
      confirmSpy.mockRestore();
    });
  });

  describe('Groups Management', () => {
    it('displays groups list when groups tab is selected', async () => {
      const user = userEvent.setup();
      render(<UsersPage />);
      
      await waitFor(() => {
        expect(screen.getByText('Groups')).toBeInTheDocument();
      });

      const groupsTab = screen.getByRole('button', { name: /Groups/ });
      await user.click(groupsTab);
      
      expect(screen.getByText('administrators')).toBeInTheDocument();
      expect(screen.getByText('users')).toBeInTheDocument();
      expect(screen.getByText('System administrators')).toBeInTheDocument();
    });

    it('creates new group successfully', async () => {
      const user = userEvent.setup();
      createGroup.mockResolvedValue({ data: { id: 3, name: 'newgroup' } });
      
      render(<UsersPage />);
      
      // Wait for component to load first
      await waitFor(() => {
        expect(screen.getByText('admin')).toBeInTheDocument();
      });
      
      // Switch to groups tab
      const groupsTab = screen.getByRole('button', { name: /Groups/ });
      await user.click(groupsTab);
      
      // Open create modal
      const addButton = screen.getByText('Add Group');
      await user.click(addButton);
      
      // Fill form
      await user.type(screen.getByLabelText('Group Name'), 'newgroup');
      await user.type(screen.getByLabelText('Description'), 'New group description');
      
      // Submit form
      const createButton = screen.getByText('Create');
      await user.click(createButton);
      
      await waitFor(() => {
        expect(createGroup).toHaveBeenCalledWith({
          name: 'newgroup',
          description: 'New group description'
        });
      });
    });

    it('manages group membership correctly', async () => {
      const user = userEvent.setup();
      addUserToGroup.mockResolvedValue({ data: { success: true } });
      
      render(<UsersPage />);
      
      // Wait for component to load first
      await waitFor(() => {
        expect(screen.getByText('admin')).toBeInTheDocument();
      });
      
      // Switch to groups tab
      const groupsTab = screen.getByRole('button', { name: /Groups/ });
      await user.click(groupsTab);
      
      // Wait for groups content to load
      await waitFor(() => {
        expect(screen.getByText('administrators')).toBeInTheDocument();
      });
      
      // Find manage members button
      const manageButtons = screen.getAllByText('Manage Members');
      await user.click(manageButtons[0]);
      
      // Should show group membership modal
      expect(screen.getByText('Manage Group Members')).toBeInTheDocument();
    });
  });

  describe('Audit Logs', () => {
    it('displays audit logs when audit tab is selected', async () => {
      const user = userEvent.setup();
      render(<UsersPage />);
      
      await waitFor(() => {
        expect(screen.getByText('Audit Logs')).toBeInTheDocument();
      });

      const auditTab = screen.getByRole('button', { name: /Audit Logs/ });
      await user.click(auditTab);
      
      await waitFor(() => {
        expect(screen.getByText('user.create')).toBeInTheDocument();
        expect(screen.getByText('success')).toBeInTheDocument();
      });
    });

    it('displays audit statistics', async () => {
      const user = userEvent.setup();
      render(<UsersPage />);
      
      // Wait for component to load first
      await waitFor(() => {
        expect(screen.getByText('admin')).toBeInTheDocument();
      });
      
      const auditTab = screen.getByRole('button', { name: /Audit Logs/ });
      await user.click(auditTab);
      
      await waitFor(() => {
        expect(screen.getByText('100')).toBeInTheDocument(); // Total logs
        expect(screen.getByText('95')).toBeInTheDocument(); // Success count
      });
    });

    it('filters audit logs correctly', async () => {
      const user = userEvent.setup();
      render(<UsersPage />);
      
      // Wait for component to load first
      await waitFor(() => {
        expect(screen.getByText('admin')).toBeInTheDocument();
      });
      
      const auditTab = screen.getByRole('button', { name: /Audit Logs/ });
      await user.click(auditTab);
      
      await waitFor(() => {
        expect(screen.getByText('user.create')).toBeInTheDocument();
      });

      // Apply filter
      const actionFilter = screen.getByLabelText('Action');
      await user.type(actionFilter, 'user.create');
      
      const applyButton = screen.getByText('Apply Filters');
      await user.click(applyButton);
      
      await waitFor(() => {
        expect(getAuditLogs).toHaveBeenCalledWith(expect.objectContaining({
          action: 'user.create'
        }));
      });
    });
  });

  describe('Error Handling', () => {
    it('displays error message when API calls fail', async () => {
      getUsers.mockRejectedValue(new Error('API Error'));
      
      render(<UsersPage />);
      
      await waitFor(() => {
        expect(screen.getByText(/Failed to load data/)).toBeInTheDocument();
      });
    });

    it('handles user creation errors gracefully', async () => {
      const user = userEvent.setup();
      createUser.mockRejectedValue(new Error('Username already exists'));
      
      render(<UsersPage />);
      
      await waitFor(() => {
        expect(screen.getByText('Add User')).toBeInTheDocument();
      });

      // Open create modal and submit
      const addButton = screen.getByText('Add User');
      await user.click(addButton);
      
      await user.type(screen.getByLabelText('Username'), 'admin'); // Duplicate username
      await user.type(screen.getByLabelText('Email'), 'admin@example.com');
      await user.type(screen.getByLabelText('Password'), 'password123');
      
      const createButton = screen.getByText('Create');
      await user.click(createButton);
      
      await waitFor(() => {
        expect(screen.getByText(/Username already exists/)).toBeInTheDocument();
      });
    });
  });

  describe('Form Validation', () => {
    it('validates required fields in user form', async () => {
      const user = userEvent.setup();
      render(<UsersPage />);
      
      await waitFor(() => {
        expect(screen.getByText('Add User')).toBeInTheDocument();
      });

      const addButton = screen.getByText('Add User');
      await user.click(addButton);
      
      // Try to submit without filling required fields
      const createButton = screen.getByText('Create');
      await user.click(createButton);
      
      // Should show validation errors
      expect(screen.getByText('Username is required')).toBeInTheDocument();
      expect(screen.getByText('Email is required')).toBeInTheDocument();
    });

    it('validates email format', async () => {
      const user = userEvent.setup();
      render(<UsersPage />);
      
      await waitFor(() => {
        expect(screen.getByText('Add User')).toBeInTheDocument();
      });

      const addButton = screen.getByText('Add User');
      await user.click(addButton);
      
      // Enter invalid email
      await user.type(screen.getByLabelText('Email'), 'invalid-email');
      
      const createButton = screen.getByText('Create');
      await user.click(createButton);
      
      expect(screen.getByText('Please enter a valid email address')).toBeInTheDocument();
    });
  });

  describe('Modal Management', () => {
    it('closes modal when cancel button is clicked', async () => {
      const user = userEvent.setup();
      render(<UsersPage />);
      
      await waitFor(() => {
        expect(screen.getByText('Add User')).toBeInTheDocument();
      });

      const addButton = screen.getByText('Add User');
      await user.click(addButton);
      
      expect(screen.getByText('Create User')).toBeInTheDocument();
      
      const cancelButton = screen.getByText('Cancel');
      await user.click(cancelButton);
      
      expect(screen.queryByText('Create User')).not.toBeInTheDocument();
    });

    it('resets form when modal is closed', async () => {
      const user = userEvent.setup();
      render(<UsersPage />);
      
      await waitFor(() => {
        expect(screen.getByText('Add User')).toBeInTheDocument();
      });

      const addButton = screen.getByText('Add User');
      await user.click(addButton);
      
      // Fill some data
      await user.type(screen.getByLabelText('Username'), 'testuser');
      
      // Close modal
      const cancelButton = screen.getByText('Cancel');
      await user.click(cancelButton);
      
      // Reopen modal
      await user.click(addButton);
      
      // Form should be reset
      expect(screen.getByLabelText('Username')).toHaveValue('');
    });
  });

  describe('Accessibility', () => {
    it('has proper ARIA labels for form controls', async () => {
      const user = userEvent.setup();
      render(<UsersPage />);
      
      await waitFor(() => {
        expect(screen.getByText('Add User')).toBeInTheDocument();
      });

      const addButton = screen.getByText('Add User');
      await user.click(addButton);
      
      expect(screen.getByLabelText('Username')).toBeInTheDocument();
      expect(screen.getByLabelText('Email')).toBeInTheDocument();
      expect(screen.getByLabelText('Password')).toBeInTheDocument();
      expect(screen.getByLabelText('Full Name')).toBeInTheDocument();
    });

    it('supports keyboard navigation for tabs', async () => {
      const user = userEvent.setup();
      render(<UsersPage />);
      
      await waitFor(() => {
        expect(screen.getByText('Users')).toBeInTheDocument();
      });

      const usersTab = screen.getByRole('button', { name: /Users/ });
      usersTab.focus();
      
      await user.keyboard('{ArrowRight}');
      
      const groupsTab = screen.getByRole('button', { name: /Groups/ });
      expect(groupsTab).toHaveFocus();
    });
  });
});