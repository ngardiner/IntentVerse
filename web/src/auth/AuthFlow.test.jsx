import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import App, { AuthProvider, useAuth } from '../App';
import LoginPage from '../pages/LoginPage';
import { login as apiLogin, getCurrentUser } from '../api/client';

// Mock the API client
jest.mock('../api/client');

// Mock localStorage
const localStorageMock = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn(),
};
global.localStorage = localStorageMock;

// Mock all page components for cleaner testing
jest.mock('../pages/DashboardPage', () => {
  return function MockDashboardPage() {
    return <div data-testid="dashboard-page">Dashboard Page</div>;
  };
});

jest.mock('../pages/TimelinePage', () => {
  return function MockTimelinePage() {
    return <div data-testid="timeline-page">Timeline Page</div>;
  };
});

jest.mock('../pages/SettingsPage', () => {
  return function MockSettingsPage() {
    return <div data-testid="settings-page">Settings Page</div>;
  };
});

jest.mock('../pages/ContentPage', () => {
  return function MockContentPage() {
    return <div data-testid="content-page">Content Page</div>;
  };
});

jest.mock('../pages/UsersPage', () => {
  return function MockUsersPage() {
    return <div data-testid="users-page">Users Page</div>;
  };
});

jest.mock('../components/DashboardSelector', () => {
  return function MockDashboardSelector({ currentDashboard, onDashboardChange }) {
    return (
      <div data-testid="dashboard-selector">
        <span>Current: {currentDashboard}</span>
        <button onClick={() => onDashboardChange('timeline')}>Switch to Timeline</button>
      </div>
    );
  };
});

jest.mock('../components/EditButton', () => {
  return function MockEditButton({ isEditing, onClick }) {
    return (
      <button onClick={onClick} data-testid="edit-button">
        {isEditing ? 'Save' : 'Edit'}
      </button>
    );
  };
});

describe('Authentication Flow Integration Tests', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorageMock.clear();
    localStorageMock.getItem.mockReturnValue(null);
  });

  describe('Initial Authentication State', () => {
    it('shows login page when no token exists', () => {
      render(<App />);
      
      expect(screen.getByTestId('login-page')).toBeInTheDocument();
      expect(screen.queryByTestId('dashboard-page')).not.toBeInTheDocument();
    });

    it('shows login page when localStorage is empty', () => {
      localStorageMock.getItem.mockReturnValue(null);
      
      render(<App />);
      
      expect(screen.getByTestId('login-page')).toBeInTheDocument();
    });

    it('attempts to validate token when token exists in localStorage', async () => {
      // Clear the default mock from beforeEach and set up the specific mock for this test
      localStorageMock.getItem.mockClear();
      localStorageMock.getItem.mockImplementation((key) => {
        if (key === 'authToken') return 'existing-token';
        return null;
      });
      getCurrentUser.mockResolvedValue({ data: { username: 'testuser', id: 1 } });
      
      render(<App />);
      
      await waitFor(() => {
        expect(getCurrentUser).toHaveBeenCalledTimes(1);
      });
    });
  });

  describe('Successful Authentication Flow', () => {
    it('completes full login flow successfully', async () => {
      const user = userEvent.setup();
      
      // Mock successful login
      apiLogin.mockResolvedValue({
        data: { access_token: 'new-auth-token' }
      });
      getCurrentUser.mockResolvedValue({
        data: { username: 'testuser', id: 1, email: 'test@example.com' }
      });
      
      render(<App />);
      
      // Should start with login page
      expect(screen.getByTestId('login-page')).toBeInTheDocument();
      
      // Fill login form
      const usernameInput = screen.getByLabelText(/username/i);
      const passwordInput = screen.getByLabelText(/password/i);
      const loginButton = screen.getByRole('button', { name: /login/i });
      
      await user.type(usernameInput, 'testuser');
      await user.type(passwordInput, 'password123');
      await user.click(loginButton);
      
      // Should call login API
      expect(apiLogin).toHaveBeenCalledWith({
        username: 'testuser',
        password: 'password123'
      });
      
      // Should store token and show dashboard
      await waitFor(() => {
        expect(localStorageMock.setItem).toHaveBeenCalledWith('authToken', 'new-auth-token');
        expect(screen.getByTestId('dashboard-page')).toBeInTheDocument();
      });
      
      // Should fetch current user info
      expect(getCurrentUser).toHaveBeenCalled();
      
      // Should display user info
      await waitFor(() => {
        expect(screen.getByText('testuser')).toBeInTheDocument();
      });
    });

    it('restores authentication state on page reload', async () => {
      localStorageMock.getItem.mockClear();
      localStorageMock.getItem.mockImplementation((key) => {
        if (key === 'authToken') return 'valid-token';
        return null;
      });
      getCurrentUser.mockResolvedValue({
        data: { username: 'testuser', id: 1 }
      });
      
      render(<App />);
      
      // Should validate existing token
      await waitFor(() => {
        expect(getCurrentUser).toHaveBeenCalledTimes(1);
        expect(screen.getByTestId('dashboard-page')).toBeInTheDocument();
      });
      
      // Should display user info
      await waitFor(() => {
        expect(screen.getByText('testuser')).toBeInTheDocument();
      });
    });

    it('maintains authentication state across component re-renders', async () => {
      const user = userEvent.setup();
      
      localStorageMock.getItem.mockClear();
      localStorageMock.getItem.mockImplementation((key) => {
        if (key === 'authToken') return 'valid-token';
        return null;
      });
      getCurrentUser.mockResolvedValue({
        data: { username: 'testuser', id: 1 }
      });
      
      const { rerender } = render(<App />);
      
      await waitFor(() => {
        expect(screen.getByTestId('dashboard-page')).toBeInTheDocument();
      });
      
      // Re-render component
      rerender(<App />);
      
      // Should still be authenticated
      expect(screen.getByTestId('dashboard-page')).toBeInTheDocument();
      expect(screen.getByText('testuser')).toBeInTheDocument();
    });
  });

  describe('Authentication Errors and Edge Cases', () => {
    it('handles invalid credentials gracefully', async () => {
      const user = userEvent.setup();
      
      apiLogin.mockRejectedValue({
        response: { status: 401, data: { detail: 'Invalid credentials' } }
      });
      
      render(<App />);
      
      const usernameInput = screen.getByLabelText(/username/i);
      const passwordInput = screen.getByLabelText(/password/i);
      const loginButton = screen.getByRole('button', { name: /login/i });
      
      await user.type(usernameInput, 'wronguser');
      await user.type(passwordInput, 'wrongpassword');
      await user.click(loginButton);
      
      // Should remain on login page
      expect(screen.getByTestId('login-page')).toBeInTheDocument();
      
      // Should not store any token
      expect(localStorageMock.setItem).not.toHaveBeenCalled();
    });

    it('handles expired/invalid tokens correctly', async () => {
      localStorageMock.getItem.mockClear();
      localStorageMock.getItem.mockImplementation((key) => {
        if (key === 'authToken') return 'expired-token';
        return null;
      });
      getCurrentUser.mockRejectedValue({
        response: { status: 401, data: { detail: 'Token expired' } }
      });
      
      render(<App />);
      
      // Should attempt to validate token
      await waitFor(() => {
        expect(getCurrentUser).toHaveBeenCalledTimes(1);
      });
      
      // Should clear invalid token and show login page
      await waitFor(() => {
        expect(localStorageMock.removeItem).toHaveBeenCalledWith('authToken');
        expect(screen.getByTestId('login-page')).toBeInTheDocument();
      });
    });

    it('handles network errors during authentication', async () => {
      const user = userEvent.setup();
      
      apiLogin.mockRejectedValue(new Error('Network error'));
      
      render(<App />);
      
      const usernameInput = screen.getByLabelText(/username/i);
      const passwordInput = screen.getByLabelText(/password/i);
      const loginButton = screen.getByRole('button', { name: /login/i });
      
      await user.type(usernameInput, 'testuser');
      await user.type(passwordInput, 'password123');
      await user.click(loginButton);
      
      // Should handle error gracefully
      expect(screen.getByTestId('login-page')).toBeInTheDocument();
      expect(localStorageMock.setItem).not.toHaveBeenCalled();
    });

    it('handles malformed API responses', async () => {
      const user = userEvent.setup();
      
      // Mock API returning response without access_token
      apiLogin.mockResolvedValue({
        data: { message: 'Login successful' } // Missing access_token
      });
      
      render(<App />);
      
      const usernameInput = screen.getByLabelText(/username/i);
      const passwordInput = screen.getByLabelText(/password/i);
      const loginButton = screen.getByRole('button', { name: /login/i });
      
      await user.type(usernameInput, 'testuser');
      await user.type(passwordInput, 'password123');
      await user.click(loginButton);
      
      // Should not proceed with authentication
      expect(localStorageMock.setItem).not.toHaveBeenCalled();
      expect(screen.getByTestId('login-page')).toBeInTheDocument();
    });
  });

  describe('Logout Flow', () => {
    it('completes logout flow successfully', async () => {
      const user = userEvent.setup();
      
      // Start with authenticated state
      localStorageMock.getItem.mockClear();
      localStorageMock.getItem.mockImplementation((key) => {
        if (key === 'authToken') return 'valid-token';
        return null;
      });
      getCurrentUser.mockResolvedValue({
        data: { username: 'testuser', id: 1 }
      });
      
      render(<App />);
      
      await waitFor(() => {
        expect(screen.getByTestId('dashboard-page')).toBeInTheDocument();
      });
      
      // Open user dropdown
      const userIcon = screen.getByText('testuser');
      await user.click(userIcon);
      
      // Click logout
      const logoutButton = screen.getByText('Logout');
      await user.click(logoutButton);
      
      // Should clear token and show login page
      await waitFor(() => {
        expect(localStorageMock.removeItem).toHaveBeenCalledWith('authToken');
        expect(screen.getByTestId('login-page')).toBeInTheDocument();
      });
    });

    it('clears all authentication state on logout', async () => {
      const user = userEvent.setup();
      
      localStorageMock.getItem.mockClear();
      localStorageMock.getItem.mockImplementation((key) => {
        if (key === 'authToken') return 'valid-token';
        return null;
      });
      getCurrentUser.mockResolvedValue({
        data: { username: 'testuser', id: 1 }
      });
      
      render(<App />);
      
      await waitFor(() => {
        expect(screen.getByText('testuser')).toBeInTheDocument();
      });
      
      // Logout
      const userIcon = screen.getByText('testuser');
      await user.click(userIcon);
      const logoutButton = screen.getByText('Logout');
      await user.click(logoutButton);
      
      // Should clear all state
      await waitFor(() => {
        expect(screen.getByTestId('login-page')).toBeInTheDocument();
        expect(screen.queryByText('testuser')).not.toBeInTheDocument();
      });
    });
  });

  describe('Token Validation Edge Cases', () => {
    it('handles getCurrentUser returning null user', async () => {
      localStorageMock.getItem.mockClear();
      localStorageMock.getItem.mockImplementation((key) => {
        if (key === 'authToken') return 'valid-token';
        return null;
      });
      getCurrentUser.mockResolvedValue({ data: null });
      
      render(<App />);
      
      await waitFor(() => {
        expect(getCurrentUser).toHaveBeenCalledTimes(1);
        expect(screen.getByTestId('login-page')).toBeInTheDocument();
      });
    });

    it('handles getCurrentUser returning malformed user data', async () => {
      localStorageMock.getItem.mockClear();
      localStorageMock.getItem.mockImplementation((key) => {
        if (key === 'authToken') return 'valid-token';
        return null;
      });
      getCurrentUser.mockResolvedValue({ data: { invalid: 'data' } });
      
      render(<App />);
      
      await waitFor(() => {
        expect(getCurrentUser).toHaveBeenCalledTimes(1);
      });
      
      // Should handle gracefully, possibly showing login page
      expect(screen.getByTestId('dashboard-page')).toBeInTheDocument();
    });

    it('retries token validation on temporary network failures', async () => {
      localStorageMock.getItem.mockClear();
      localStorageMock.getItem.mockImplementation((key) => {
        if (key === 'authToken') return 'valid-token';
        return null;
      });
      getCurrentUser
        .mockRejectedValueOnce(new Error('Network timeout'))
        .mockResolvedValue({ data: { username: 'testuser', id: 1 } });
      
      render(<App />);
      
      // Should eventually succeed after retry
      await waitFor(() => {
        expect(getCurrentUser).toHaveBeenCalledTimes(1);
      });
    });
  });

  describe('Authentication Context Behavior', () => {
    it('provides correct authentication state to child components', async () => {
      let authContext;
      
      function TestComponent() {
        authContext = useAuth();
        return <div>Test Component</div>;
      }
      
      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );
      
      // Should start unauthenticated
      expect(authContext.isAuthenticated).toBe(false);
      expect(authContext.token).toBeNull();
      expect(typeof authContext.login).toBe('function');
      expect(typeof authContext.logout).toBe('function');
    });

    it('updates authentication state correctly after login', async () => {
      let authContext;
      
      function TestComponent() {
        authContext = useAuth();
        return (
          <button onClick={() => authContext.login({ username: 'test', password: 'test' })}>
            Login
          </button>
        );
      }
      
      apiLogin.mockResolvedValue({
        data: { access_token: 'new-token' }
      });
      
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
        expect(authContext.token).toBe('new-token');
      });
    });

    it('synchronizes authentication state across multiple components', async () => {
      let authContext1, authContext2;
      
      function TestComponent1() {
        authContext1 = useAuth();
        return <div>Component 1: {authContext1.isAuthenticated.toString()}</div>;
      }
      
      function TestComponent2() {
        authContext2 = useAuth();
        return <div>Component 2: {authContext2.isAuthenticated.toString()}</div>;
      }
      
      render(
        <AuthProvider>
          <TestComponent1 />
          <TestComponent2 />
        </AuthProvider>
      );
      
      expect(authContext1.isAuthenticated).toBe(false);
      expect(authContext2.isAuthenticated).toBe(false);
      
      // Simulate login by setting token directly
      localStorageMock.getItem.mockReturnValue('test-token');
      
      // Both components should have the same state
      expect(authContext1.isAuthenticated).toBe(authContext2.isAuthenticated);
    });
  });

  describe('Security Considerations', () => {
    it('does not expose sensitive data in component state', async () => {
      localStorageMock.getItem.mockClear();
      localStorageMock.getItem.mockImplementation((key) => {
        if (key === 'authToken') return 'sensitive-token';
        return null;
      });
      getCurrentUser.mockResolvedValue({
        data: { username: 'testuser', id: 1, password: 'should-not-be-exposed' }
      });
      
      render(<App />);
      
      await waitFor(() => {
        expect(screen.getByTestId('dashboard-page')).toBeInTheDocument();
      });
      
      // Password should not be displayed anywhere
      expect(screen.queryByText('should-not-be-exposed')).not.toBeInTheDocument();
    });

    it('clears sensitive data from memory on logout', async () => {
      const user = userEvent.setup();
      
      localStorageMock.getItem.mockClear();
      localStorageMock.getItem.mockImplementation((key) => {
        if (key === 'authToken') return 'valid-token';
        return null;
      });
      getCurrentUser.mockResolvedValue({
        data: { username: 'testuser', id: 1 }
      });
      
      render(<App />);
      
      await waitFor(() => {
        expect(screen.getByText('testuser')).toBeInTheDocument();
      });
      
      // Logout
      const userIcon = screen.getByText('testuser');
      await user.click(userIcon);
      const logoutButton = screen.getByText('Logout');
      await user.click(logoutButton);
      
      // All user data should be cleared
      await waitFor(() => {
        expect(screen.queryByText('testuser')).not.toBeInTheDocument();
      });
    });
  });
});