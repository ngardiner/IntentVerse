import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import LoginPage from './LoginPage';
import { AuthProvider, useAuth } from '../App';

// Mock the useAuth hook to provide a dummy login function
jest.mock('../App', () => {
  const originalModule = jest.requireActual('../App');
  return {
    ...originalModule,
    useAuth: jest.fn(),
  };
});

// A simple mock AuthProvider for testing
const MockAuthProvider = ({ children }) => {
  return <div>{children}</div>;
};

// A wrapper to provide the context for our tests
const renderWithAuthProvider = (ui) => {
  return render(<MockAuthProvider>{ui}</MockAuthProvider>);
};

describe('LoginPage', () => {
  const mockLogin = jest.fn();

  beforeEach(() => {
    // Before each test, reset the mock and set the mocked return value for useAuth
    jest.clearAllMocks();
    // Clear localStorage to ensure clean state
    localStorage.clear();
    useAuth.mockReturnValue({
      login: mockLogin,
      isAuthenticated: false,
    });
  });

  test('renders login form correctly', () => {
    renderWithAuthProvider(<LoginPage />);

    expect(screen.getByRole('heading', { name: /intentverse login/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/username/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /login/i })).toBeInTheDocument();
  });

  test('calls login function with credentials on form submission', () => {
    renderWithAuthProvider(<LoginPage />);

    const usernameInput = screen.getByLabelText(/username/i);
    expect(usernameInput).toBeInTheDocument();

    const passwordInput = screen.getByLabelText(/password/i);
    expect(passwordInput).toBeInTheDocument();

    const loginButton = screen.getByRole('button', { name: /login/i });
    expect(loginButton).toBeInTheDocument();

    // ACT: Simulate a user typing and clicking
    fireEvent.change(usernameInput, { target: { value: 'testuser' } });
    fireEvent.change(passwordInput, { target: { value: 'password123' } });
    fireEvent.click(loginButton);

    // ASSERT: Check that our mocked login function was called with the correct data
    expect(mockLogin).toHaveBeenCalledTimes(1);
    expect(mockLogin).toHaveBeenCalledWith({
      username: 'testuser',
      password: 'password123',
    });
  });
});