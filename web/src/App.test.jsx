import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import App, { AuthProvider, useAuth } from './App';
import { login as apiLogin, getCurrentUser } from './api/client';

// Mock the API client
jest.mock('./api/client');

// Mock all page components
jest.mock('./pages/DashboardPage', () => {
  return function MockDashboardPage(props) {
    return <div data-testid="dashboard-page">Dashboard Page - Editing: {props.isEditing.toString()}</div>;
  };
});

jest.mock('./pages/TimelinePage', () => {
  return function MockTimelinePage() {
    return <div data-testid="timeline-page">Timeline Page</div>;
  };
});

jest.mock('./pages/LoginPage', () => {
  return function MockLoginPage() {
    return <div data-testid="login-page">Login Page</div>;
  };
});

jest.mock('./pages/SettingsPage', () => {
  return function MockSettingsPage() {
    return <div data-testid="settings-page">Settings Page</div>;
  };
});

jest.mock('./pages/ContentPage', () => {
  return function MockContentPage() {
    return <div data-testid="content-page">Content Page</div>;
  };
});

jest.mock('./pages/UsersPage', () => {
  return function MockUsersPage() {
    return <div data-testid="users-page">Users Page</div>;
  };
});

// Mock components
jest.mock('./components/DashboardSelector', () => {
  return function MockDashboardSelector({ currentDashboard, onDashboardChange }) {
    return (
      <div data-testid="dashboard-selector">
        <span>Current: {currentDashboard}</span>
        <button onClick={() => onDashboardChange('timeline')}>Switch to Timeline</button>
      </div>
    );
  };
});

jest.mock('./components/EditButton', () => {
  return function MockEditButton({ isEditing, onClick }) {
    return (
      <button data-testid="edit-button" onClick={onClick}>
        {isEditing ? 'Exit Edit' : 'Edit'}
      </button>
    );
  };
});

describe('App', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorage.clear();
  });

  it('renders login page when not authenticated', () => {
    render(<App />);
    
    expect(screen.getByTestId('login-page')).toBeInTheDocument();
  });

  it('renders dashboard when authenticated', async () => {
    // Mock successful login
    apiLogin.mockResolvedValue({
      data: { access_token: 'test-token' }
    });

    getCurrentUser.mockResolvedValue({
      data: { username: 'admin', id: 1 }
    });

    // Set token in localStorage to simulate existing session
    localStorage.setItem('authToken', 'test-token');

    render(<App />);

    await waitFor(() => {
      expect(screen.getByTestId('dashboard-page')).toBeInTheDocument();
    });

    expect(screen.getByText('IntentVerse')).toBeInTheDocument();
    expect(screen.getByTestId('dashboard-selector')).toBeInTheDocument();
    expect(screen.getByTestId('edit-button')).toBeInTheDocument();
  });

  it('switches between pages correctly', async () => {
    localStorage.setItem('authToken', 'test-token');
    getCurrentUser.mockResolvedValue({
      data: { username: 'admin', id: 1 }
    });

    const user = userEvent.setup();
    render(<App />);

    await waitFor(() => {
      expect(screen.getByTestId('dashboard-page')).toBeInTheDocument();
    });

    // Switch to Content page
    const contentLink = screen.getByText('Content');
    await user.click(contentLink);

    expect(screen.getByTestId('content-page')).toBeInTheDocument();

    // Switch to Settings page
    const settingsLink = screen.getByText('Settings');
    await user.click(settingsLink);

    expect(screen.getByTestId('settings-page')).toBeInTheDocument();
  });

  it('toggles edit mode correctly', async () => {
    localStorage.setItem('authToken', 'test-token');
    getCurrentUser.mockResolvedValue({
      data: { username: 'admin', id: 1 }
    });

    const user = userEvent.setup();
    render(<App />);

    await waitFor(() => {
      expect(screen.getByTestId('dashboard-page')).toBeInTheDocument();
    });

    // Should show "Edit" button initially
    expect(screen.getByText('Edit')).toBeInTheDocument();
    expect(screen.getByText('Dashboard Page - Editing: false')).toBeInTheDocument();

    // Click edit button
    const editButton = screen.getByTestId('edit-button');
    await user.click(editButton);

    // Should now be in edit mode
    expect(screen.getByText('Exit Edit')).toBeInTheDocument();
    expect(screen.getByText('Dashboard Page - Editing: true')).toBeInTheDocument();
  });

  it('switches dashboards correctly', async () => {
    localStorage.setItem('authToken', 'test-token');
    getCurrentUser.mockResolvedValue({
      data: { username: 'admin', id: 1 }
    });

    const user = userEvent.setup();
    render(<App />);

    await waitFor(() => {
      expect(screen.getByTestId('dashboard-page')).toBeInTheDocument();
    });

    // Should show state dashboard initially
    expect(screen.getByText('Current: state')).toBeInTheDocument();

    // Switch to timeline dashboard
    const switchButton = screen.getByText('Switch to Timeline');
    await user.click(switchButton);

    expect(screen.getByTestId('timeline-page')).toBeInTheDocument();
  });

  it('logs out correctly', async () => {
    localStorage.setItem('authToken', 'test-token');
    getCurrentUser.mockResolvedValue({
      data: { username: 'admin', id: 1 }
    });

    const user = userEvent.setup();
    render(<App />);

    await waitFor(() => {
      expect(screen.getByTestId('dashboard-page')).toBeInTheDocument();
    });

    // Click logout button
    const logoutButton = screen.getByText('Logout');
    await user.click(logoutButton);

    // Should return to login page
    expect(screen.getByTestId('login-page')).toBeInTheDocument();
    expect(localStorage.getItem('authToken')).toBeNull();
  });

  it('handles authentication errors gracefully', async () => {
    localStorage.setItem('authToken', 'invalid-token');
    getCurrentUser.mockRejectedValue(new Error('Unauthorized'));

    render(<App />);

    await waitFor(() => {
      expect(screen.getByTestId('login-page')).toBeInTheDocument();
    });

    // Token should be cleared from localStorage
    expect(localStorage.getItem('authToken')).toBeNull();
  });

  it('shows user info when authenticated', async () => {
    localStorage.setItem('authToken', 'test-token');
    getCurrentUser.mockResolvedValue({
      data: { username: 'testuser', id: 1 }
    });

    render(<App />);

    await waitFor(() => {
      expect(screen.getByText('testuser')).toBeInTheDocument();
    });
  });

  it('hides edit button on non-dashboard pages', async () => {
    localStorage.setItem('authToken', 'test-token');
    getCurrentUser.mockResolvedValue({
      data: { username: 'admin', id: 1 }
    });

    const user = userEvent.setup();
    render(<App />);

    await waitFor(() => {
      expect(screen.getByTestId('dashboard-page')).toBeInTheDocument();
    });

    // Edit button should be visible on dashboard
    expect(screen.getByTestId('edit-button')).toBeInTheDocument();

    // Switch to settings page
    const settingsLink = screen.getByText('Settings');
    await user.click(settingsLink);

    // Edit button should not be visible on settings page
    expect(screen.queryByTestId('edit-button')).not.toBeInTheDocument();
  });

  it('persists authentication state across page reloads', () => {
    // Simulate existing token in localStorage
    localStorage.setItem('authToken', 'existing-token');

    render(<App />);

    // Should not show login page immediately
    expect(screen.queryByTestId('login-page')).not.toBeInTheDocument();
  });
});

describe('AuthProvider', () => {
  it('provides authentication context to children', () => {
    let authContext;
    
    function TestComponent() {
      authContext = useAuth();
      return <div>Test</div>;
    }

    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );

    expect(authContext).toBeDefined();
    expect(authContext.isAuthenticated).toBe(false);
    expect(typeof authContext.login).toBe('function');
    expect(typeof authContext.logout).toBe('function');
  });

  it('updates authentication state when login is called', async () => {
    apiLogin.mockResolvedValue({
      data: { access_token: 'new-token' }
    });

    let authContext;
    
    function TestComponent() {
      authContext = useAuth();
      return (
        <button onClick={() => authContext.login({ username: 'test', password: 'test' })}>
          Login
        </button>
      );
    }

    const user = userEvent.setup();
    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );

    expect(authContext.isAuthenticated).toBe(false);

    const loginButton = screen.getByText('Login');
    await user.click(loginButton);

    await waitFor(() => {
      expect(authContext.isAuthenticated).toBe(true);
    });

    expect(authContext.token).toBe('new-token');
  });
});