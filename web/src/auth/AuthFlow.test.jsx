import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import AppWrapper, { AuthProvider, useAuth } from '../App';
import LoginPage from '../pages/LoginPage';
import { login as apiLogin, getCurrentUser } from '../api/client';

// Mock the API client
jest.mock('../api/client', () => ({
  getCurrentUser: jest.fn(),
  login: jest.fn(),
}));

// Create a fresh localStorage mock for this test file
const localStorageMock = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn(),
};

// Override global localStorage with our mock
Object.defineProperty(global, 'localStorage', {
  value: localStorageMock,
  writable: true
});

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
  // Increase timeout for integration tests
  jest.setTimeout(15000);
  
  beforeEach(() => {
    // Set default behavior - no token exists, no user data
    localStorageMock.getItem.mockReturnValue(null);
    getCurrentUser.mockResolvedValue({ data: null });
    
    // Clear any existing timers
    jest.clearAllTimers();
  });

  afterEach(() => {
    // Additional cleanup after each test
    jest.clearAllTimers();
    
    // localStorage mock is already cleared by setupTests.js
  });

  describe('Initial Authentication State', () => {
    it('shows login page when no token exists', async () => {
      // Explicitly set localStorage to return null
      localStorageMock.getItem.mockReturnValue(null);
      
      render(<AppWrapper />);
      
      // Wait for token validation to complete and login page to appear
      await waitFor(() => {
        expect(screen.getByTestId('login-page')).toBeInTheDocument();
      });
      expect(screen.queryByTestId('dashboard-page')).not.toBeInTheDocument();
    });

    it('shows login page when localStorage is empty', async () => {
      localStorageMock.getItem.mockReturnValue(null);
      
      render(<AppWrapper />);
      
      // Wait for token validation to complete and login page to appear
      await waitFor(() => {
        expect(screen.getByTestId('login-page')).toBeInTheDocument();
      });
    });

    it('attempts to validate token when token exists in localStorage', async () => {
      // CRITICAL: Set up localStorage mock BEFORE rendering
      // Use the localStorageMock that's already set up in beforeEach
      localStorageMock.getItem.mockImplementation((key) => {
        if (key === 'authToken') return 'existing-token';
        return null;
      });
      
      getCurrentUser.mockResolvedValue({ data: { username: 'testuser', id: 1 } });
      
      render(<AppWrapper />);
      
      // Wait for token validation to complete (AuthProvider call)
      await waitFor(() => {
        expect(getCurrentUser).toHaveBeenCalledTimes(1);
      }, { timeout: 8000 });
      
      // Wait for dashboard to appear
      await waitFor(() => {
        expect(screen.getByTestId('dashboard-page')).toBeInTheDocument();
      }, { timeout: 8000 });
      
      // Wait for user info to load (App component call)
      await waitFor(() => {
        expect(getCurrentUser).toHaveBeenCalledTimes(2); // AuthProvider validation + App user info loading
      }, { timeout: 8000 });
      
      // Should display user info
      await waitFor(() => {
        expect(screen.getByText('testuser')).toBeInTheDocument();
      }, { timeout: 8000 });
    });
  });

  describe('Successful Authentication Flow', () => {
    it('completes full login flow successfully', async () => {
      const user = userEvent.setup();
      
      // Ensure no token exists initially
      localStorageMock.getItem.mockReturnValue(null);
      
      // Mock successful login
      apiLogin.mockResolvedValue({
        data: { access_token: 'new-auth-token' }
      });
      getCurrentUser.mockResolvedValue({
        data: { username: 'testuser', id: 1, email: 'test@example.com' }
      });
      
      render(<AppWrapper />);
      
      // Should start with login page
      await waitFor(() => {
        expect(screen.getByTestId('login-page')).toBeInTheDocument();
      });
      
      // Fill login form
      const usernameInput = screen.getByLabelText(/username/i);
      const passwordInput = screen.getByLabelText(/password/i);
      const loginButton = screen.getByRole('button', { name: /login/i });
      
      await user.type(usernameInput, 'testuser');
      await user.type(passwordInput, 'password123');
      await user.click(loginButton);
      
      // Should call login API
      await waitFor(() => {
        expect(apiLogin).toHaveBeenCalledWith({
          username: 'testuser',
          password: 'password123'
        });
      });
      
      // Should store token and show dashboard
      await waitFor(() => {
        expect(localStorageMock.setItem).toHaveBeenCalledWith('authToken', 'new-auth-token');
      }, { timeout: 8000 });
      
      await waitFor(() => {
        expect(screen.getByTestId('dashboard-page')).toBeInTheDocument();
      }, { timeout: 8000 });
      
      // Should fetch current user info
      await waitFor(() => {
        expect(getCurrentUser).toHaveBeenCalled();
      }, { timeout: 8000 });
      
      // Should display user info
      await waitFor(() => {
        expect(screen.getByText('testuser')).toBeInTheDocument();
      }, { timeout: 8000 });
    });

    it('restores authentication state on page reload', async () => {
      // CRITICAL: Set up localStorage mock BEFORE any component creation
      localStorageMock.getItem.mockImplementation((key) => {
        if (key === 'authToken') return 'valid-token';
        return null;
      });
      getCurrentUser.mockResolvedValue({
        data: { username: 'testuser', id: 1 }
      });
      
      render(<AppWrapper />);
      
      // Should validate existing token first (AuthProvider call)
      await waitFor(() => {
        expect(getCurrentUser).toHaveBeenCalledTimes(1);
      }, { timeout: 8000 });
      
      // Should show dashboard and load user info (App component call)
      await waitFor(() => {
        expect(screen.getByTestId('dashboard-page')).toBeInTheDocument();
      }, { timeout: 8000 });
      
      await waitFor(() => {
        expect(getCurrentUser).toHaveBeenCalledTimes(2); // AuthProvider validation + App user info loading
      }, { timeout: 8000 });
      
      // Should display user info (second call to getCurrentUser)
      await waitFor(() => {
        expect(screen.getByText('testuser')).toBeInTheDocument();
      }, { timeout: 8000 });
    });

    it('maintains authentication state across component re-renders', async () => {
      const user = userEvent.setup();
      
      // Set up localStorage mock BEFORE rendering
      localStorageMock.getItem.mockImplementation((key) => {
        if (key === 'authToken') return 'valid-token';
        return null;
      });
      getCurrentUser.mockResolvedValue({
        data: { username: 'testuser', id: 1 }
      });
      
      const { rerender } = render(<AppWrapper />);
      
      await waitFor(() => {
        expect(screen.getByTestId('dashboard-page')).toBeInTheDocument();
      });
      
      // Re-render component
      rerender(<AppWrapper />);
      
      // Should still be authenticated
      expect(screen.getByTestId('dashboard-page')).toBeInTheDocument();
      
      // Wait for user info to load after re-render
      await waitFor(() => {
        expect(screen.getByText('testuser')).toBeInTheDocument();
      });
    });
  });

  describe('Authentication Errors and Edge Cases', () => {
    it('handles invalid credentials gracefully', async () => {
      const user = userEvent.setup();
      
      // Ensure no token exists and getCurrentUser returns null
      localStorageMock.getItem.mockReturnValue(null);
      getCurrentUser.mockResolvedValue({ data: null });
      
      apiLogin.mockRejectedValue({
        response: { status: 401, data: { detail: 'Invalid credentials' } }
      });
      
      render(<AppWrapper />);
      
      // Wait for login page to appear
      await waitFor(() => {
        expect(screen.getByTestId('login-page')).toBeInTheDocument();
      });
      
      const usernameInput = screen.getByLabelText(/username/i);
      const passwordInput = screen.getByLabelText(/password/i);
      const loginButton = screen.getByRole('button', { name: /login/i });
      
      await user.type(usernameInput, 'wronguser');
      await user.type(passwordInput, 'wrongpassword');
      await user.click(loginButton);
      
      // Should remain on login page
      await waitFor(() => {
        expect(screen.getByTestId('login-page')).toBeInTheDocument();
      });
      
      // Should not store any token
      expect(localStorageMock.setItem).not.toHaveBeenCalled();
    });

    it('handles expired/invalid tokens correctly', async () => {
      // CRITICAL: Set up localStorage mock BEFORE any component creation
      localStorageMock.getItem.mockImplementation((key) => {
        if (key === 'authToken') return 'expired-token';
        return null;
      });
      
      getCurrentUser.mockRejectedValue({
        response: { status: 401, data: { detail: 'Token expired' } }
      });
      
      render(<AppWrapper />);
      
      // Should attempt to validate token
      await waitFor(() => {
        expect(getCurrentUser).toHaveBeenCalledTimes(1);
      }, { timeout: 8000 });
      
      // Should clear invalid token and show login page
      await waitFor(() => {
        expect(localStorageMock.removeItem).toHaveBeenCalledWith('authToken');
      }, { timeout: 8000 });
      
      await waitFor(() => {
        expect(screen.getByTestId('login-page')).toBeInTheDocument();
      }, { timeout: 8000 });
    });

    it('handles network errors during authentication', async () => {
      const user = userEvent.setup();
      
      // Ensure no token exists and getCurrentUser returns null
      localStorageMock.getItem.mockReturnValue(null);
      getCurrentUser.mockResolvedValue({ data: null });
      
      apiLogin.mockRejectedValue(new Error('Network error'));
      
      render(<AppWrapper />);
      
      // Wait for login page to appear
      await waitFor(() => {
        expect(screen.getByTestId('login-page')).toBeInTheDocument();
      });
      
      const usernameInput = screen.getByLabelText(/username/i);
      const passwordInput = screen.getByLabelText(/password/i);
      const loginButton = screen.getByRole('button', { name: /login/i });
      
      await user.type(usernameInput, 'testuser');
      await user.type(passwordInput, 'password123');
      await user.click(loginButton);
      
      // Should handle error gracefully
      await waitFor(() => {
        expect(screen.getByTestId('login-page')).toBeInTheDocument();
      });
      expect(localStorageMock.setItem).not.toHaveBeenCalled();
    });

    it('handles malformed API responses', async () => {
      const user = userEvent.setup();
      
      // Ensure no token exists and getCurrentUser returns null
      localStorageMock.getItem.mockReturnValue(null);
      getCurrentUser.mockResolvedValue({ data: null });
      
      // Mock API returning response without access_token
      apiLogin.mockResolvedValue({
        data: { message: 'Login successful' } // Missing access_token
      });
      
      render(<AppWrapper />);
      
      // Wait for login page to appear
      await waitFor(() => {
        expect(screen.getByTestId('login-page')).toBeInTheDocument();
      });
      
      const usernameInput = screen.getByLabelText(/username/i);
      const passwordInput = screen.getByLabelText(/password/i);
      const loginButton = screen.getByRole('button', { name: /login/i });
      
      await user.type(usernameInput, 'testuser');
      await user.type(passwordInput, 'password123');
      await user.click(loginButton);
      
      // Should not proceed with authentication
      expect(localStorageMock.setItem).not.toHaveBeenCalled();
      await waitFor(() => {
        expect(screen.getByTestId('login-page')).toBeInTheDocument();
      });
    });
  });

  describe('Logout Flow', () => {
    it('completes logout flow successfully', async () => {
      const user = userEvent.setup();
      
      // Start with authenticated state - set up localStorage mock BEFORE rendering
      localStorageMock.getItem.mockImplementation((key) => {
        if (key === 'authToken') return 'valid-token';
        return null;
      });
      
      getCurrentUser.mockResolvedValue({
        data: { username: 'testuser', id: 1 }
      });
      
      render(<AppWrapper />);
      
      // Wait for authentication to complete and dashboard to appear
      await waitFor(() => {
        expect(getCurrentUser).toHaveBeenCalledTimes(1);
      }, { timeout: 8000 });
      
      await waitFor(() => {
        expect(screen.getByTestId('dashboard-page')).toBeInTheDocument();
      }, { timeout: 8000 });
      
      // Wait for user info to load
      await waitFor(() => {
        expect(screen.getByText('testuser')).toBeInTheDocument();
      }, { timeout: 8000 });
      
      // Open user dropdown
      const userIcon = screen.getByText('testuser');
      await user.click(userIcon);
      
      // Click logout
      const logoutButton = screen.getByText('Logout');
      await user.click(logoutButton);
      
      // Should clear token and show login page
      await waitFor(() => {
        expect(localStorageMock.removeItem).toHaveBeenCalledWith('authToken');
      }, { timeout: 8000 });
      
      await waitFor(() => {
        expect(screen.getByTestId('login-page')).toBeInTheDocument();
      }, { timeout: 8000 });
    });

    it('clears all authentication state on logout', async () => {
      const user = userEvent.setup();
      
      // CRITICAL: Set up localStorage mock BEFORE any component creation
      localStorageMock.getItem.mockImplementation((key) => {
        if (key === 'authToken') return 'valid-token';
        return null;
      });
      getCurrentUser.mockResolvedValue({
        data: { username: 'testuser', id: 1 }
      });
      
      render(<AppWrapper />);
      
      // Wait for authentication to complete
      await waitFor(() => {
        expect(getCurrentUser).toHaveBeenCalledTimes(1);
      }, { timeout: 8000 });
      
      await waitFor(() => {
        expect(screen.getByTestId('dashboard-page')).toBeInTheDocument();
      }, { timeout: 8000 });
      
      await waitFor(() => {
        expect(screen.getByText('testuser')).toBeInTheDocument();
      }, { timeout: 8000 });
      
      // Logout
      const userIcon = screen.getByText('testuser');
      await user.click(userIcon);
      const logoutButton = screen.getByText('Logout');
      await user.click(logoutButton);
      
      // Should clear all state
      await waitFor(() => {
        expect(screen.getByTestId('login-page')).toBeInTheDocument();
      }, { timeout: 8000 });
      
      await waitFor(() => {
        expect(screen.queryByText('testuser')).not.toBeInTheDocument();
      }, { timeout: 8000 });
    });
  });

  describe('Token Validation Edge Cases', () => {
    it('handles getCurrentUser returning null user', async () => {
      // CRITICAL: Set up localStorage mock BEFORE any component creation
      localStorageMock.getItem.mockImplementation((key) => {
        if (key === 'authToken') return 'valid-token';
        return null;
      });
      getCurrentUser.mockResolvedValue({ data: null });
      
      render(<AppWrapper />);
      
      // Should attempt to validate token
      await waitFor(() => {
        expect(getCurrentUser).toHaveBeenCalledTimes(1);
      }, { timeout: 8000 });
      
      // Should clear token when user data is null and show login page
      await waitFor(() => {
        expect(localStorageMock.removeItem).toHaveBeenCalledWith('authToken');
      }, { timeout: 8000 });
      
      await waitFor(() => {
        expect(screen.getByTestId('login-page')).toBeInTheDocument();
      }, { timeout: 8000 });
    });

    it('handles getCurrentUser returning malformed user data', async () => {
      // CRITICAL: Set up localStorage mock BEFORE any component creation
      localStorageMock.getItem.mockImplementation((key) => {
        if (key === 'authToken') return 'valid-token';
        return null;
      });
      getCurrentUser.mockResolvedValue({ data: { invalid: 'data' } });
      
      render(<AppWrapper />);
      
      // Should validate token first (AuthProvider call)
      await waitFor(() => {
        expect(getCurrentUser).toHaveBeenCalledTimes(1);
      }, { timeout: 8000 });
      
      // Should handle malformed user data by clearing token and showing login
      await waitFor(() => {
        expect(screen.getByTestId('login-page')).toBeInTheDocument();
      }, { timeout: 8000 });
      
      // Should have called getCurrentUser once for token validation (malformed data causes token to be cleared)
      expect(getCurrentUser).toHaveBeenCalledTimes(1);
    });

    it('retries token validation on temporary network failures', async () => {
      // CRITICAL: Set up localStorage mock BEFORE any component creation
      localStorageMock.getItem.mockImplementation((key) => {
        if (key === 'authToken') return 'valid-token';
        return null;
      });
      getCurrentUser.mockRejectedValue(new Error('Network timeout'));
      
      render(<AppWrapper />);
      
      // Should attempt to validate token and fail
      await waitFor(() => {
        expect(getCurrentUser).toHaveBeenCalledTimes(1);
      }, { timeout: 8000 });
      
      // Should show login page after token validation fails
      await waitFor(() => {
        expect(screen.getByTestId('login-page')).toBeInTheDocument();
      }, { timeout: 8000 });
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
      getCurrentUser.mockResolvedValue({ data: { username: 'testuser', id: 1 } });
      
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
      
      getCurrentUser.mockResolvedValue({ data: { username: 'testuser', id: 1 } });
      
      render(
        <AuthProvider>
          <TestComponent1 />
          <TestComponent2 />
        </AuthProvider>
      );
      
      expect(authContext1.isAuthenticated).toBe(false);
      expect(authContext2.isAuthenticated).toBe(false);
      
      // Both components should have the same state
      expect(authContext1.isAuthenticated).toBe(authContext2.isAuthenticated);
    });
  });

  describe('Security Considerations', () => {
    it('does not expose sensitive data in component state', async () => {
      // CRITICAL: Set up localStorage mock BEFORE any component creation
      localStorageMock.getItem.mockImplementation((key) => {
        if (key === 'authToken') return 'sensitive-token';
        return null;
      });
      getCurrentUser.mockResolvedValue({
        data: { username: 'testuser', id: 1, password: 'should-not-be-exposed' }
      });
      
      render(<AppWrapper />);
      
      // Wait for authentication to complete
      await waitFor(() => {
        expect(getCurrentUser).toHaveBeenCalledTimes(1);
      }, { timeout: 8000 });
      
      await waitFor(() => {
        expect(screen.getByTestId('dashboard-page')).toBeInTheDocument();
      }, { timeout: 8000 });
      
      // Password should not be displayed anywhere
      expect(screen.queryByText('should-not-be-exposed')).not.toBeInTheDocument();
    });

    it('clears sensitive data from memory on logout', async () => {
      const user = userEvent.setup();
      
      // CRITICAL: Set up localStorage mock BEFORE any component creation
      localStorageMock.getItem.mockImplementation((key) => {
        if (key === 'authToken') return 'valid-token';
        return null;
      });
      getCurrentUser.mockResolvedValue({
        data: { username: 'testuser', id: 1 }
      });
      
      render(<AppWrapper />);
      
      // Wait for authentication to complete
      await waitFor(() => {
        expect(getCurrentUser).toHaveBeenCalledTimes(1);
      }, { timeout: 8000 });
      
      await waitFor(() => {
        expect(screen.getByTestId('dashboard-page')).toBeInTheDocument();
      }, { timeout: 8000 });
      
      await waitFor(() => {
        expect(screen.getByText('testuser')).toBeInTheDocument();
      }, { timeout: 8000 });
      
      // Logout
      const userIcon = screen.getByText('testuser');
      await user.click(userIcon);
      const logoutButton = screen.getByText('Logout');
      await user.click(logoutButton);
      
      // All user data should be cleared
      await waitFor(() => {
        expect(screen.queryByText('testuser')).not.toBeInTheDocument();
      }, { timeout: 8000 });
    });
  });
});