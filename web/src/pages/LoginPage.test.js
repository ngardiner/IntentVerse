import React from 'react';
import { render, screen } from '@testing-library/react';
import LoginPage from './LoginPage';
import AppWrapper from '../App'; // We need the wrapper to provide the auth context

// Mock the useAuth hook to provide a dummy login function
jest.mock('../App', () => ({
  ...jest.requireActual('../App'),
  useAuth: () => ({
    login: jest.fn(),
  }),
}));

test('renders login form correctly', () => {
  // ARRANGE: Render the component within the Auth provider wrapper
  render(<LoginPage />, { wrapper: AppWrapper });

  // ACT & ASSERT: Check if the main elements are on the screen
  const headingElement = screen.getByRole('heading', { name: /intentverse login/i });
  expect(headingElement).toBeInTheDocument();

  const usernameInput = screen.getByLabelText(/username/i);
  expect(usernameInput).toBeInTheDocument();

  const passwordInput = screen.getByLabelText(/password/i);
  expect(passwordInput).toBeInTheDocument();

  const loginButton = screen.getByRole('button', { name: /login/i });
  expect(loginButton).toBeInTheDocument();
});