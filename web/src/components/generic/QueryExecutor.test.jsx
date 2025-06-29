import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import QueryExecutor from './QueryExecutor';
import * as apiClient from '../../api/client';

// Mock the API client
jest.mock('../../api/client');

describe('QueryExecutor', () => {
  const mockOnQueryExecuted = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders with title and description', () => {
    render(
      <QueryExecutor
        title="Execute Query"
        description="Enter and execute SQL queries directly"
        module_id="database"
        onQueryExecuted={mockOnQueryExecuted}
      />
    );

    expect(screen.getByRole('heading', { name: 'Execute Query' })).toBeInTheDocument();
    expect(screen.getByText('Enter and execute SQL queries directly')).toBeInTheDocument();
  });

  it('renders textarea and buttons', () => {
    render(
      <QueryExecutor
        title="Execute Query"
        module_id="database"
        onQueryExecuted={mockOnQueryExecuted}
      />
    );

    expect(screen.getByPlaceholderText(/Enter your SQL query here/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Clear' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Execute Query' })).toBeInTheDocument();
  });

  it('disables buttons when no query is entered', () => {
    render(
      <QueryExecutor
        title="Execute Query"
        module_id="database"
        onQueryExecuted={mockOnQueryExecuted}
      />
    );

    const clearButton = screen.getByRole('button', { name: 'Clear' });
    const executeButton = screen.getByRole('button', { name: 'Execute Query' });

    expect(clearButton).toBeDisabled();
    expect(executeButton).toBeDisabled();
  });

  it('enables buttons when query is entered', () => {
    render(
      <QueryExecutor
        title="Execute Query"
        module_id="database"
        onQueryExecuted={mockOnQueryExecuted}
      />
    );

    const textarea = screen.getByPlaceholderText(/Enter your SQL query here/);
    const clearButton = screen.getByRole('button', { name: 'Clear' });
    const executeButton = screen.getByRole('button', { name: 'Execute Query' });

    fireEvent.change(textarea, { target: { value: 'SELECT * FROM users' } });

    expect(clearButton).not.toBeDisabled();
    expect(executeButton).not.toBeDisabled();
  });

  it('clears query when clear button is clicked', () => {
    render(
      <QueryExecutor
        title="Execute Query"
        module_id="database"
        onQueryExecuted={mockOnQueryExecuted}
      />
    );

    const textarea = screen.getByPlaceholderText(/Enter your SQL query here/);
    const clearButton = screen.getByRole('button', { name: 'Clear' });

    fireEvent.change(textarea, { target: { value: 'SELECT * FROM users' } });
    expect(textarea.value).toBe('SELECT * FROM users');

    fireEvent.click(clearButton);
    expect(textarea.value).toBe('');
  });

  it('executes query successfully', async () => {
    apiClient.executeQuery.mockResolvedValue({ data: { status: 'success' } });

    render(
      <QueryExecutor
        title="Execute Query"
        module_id="database"
        onQueryExecuted={mockOnQueryExecuted}
      />
    );

    const textarea = screen.getByPlaceholderText(/Enter your SQL query here/);
    const executeButton = screen.getByRole('button', { name: 'Execute Query' });

    fireEvent.change(textarea, { target: { value: 'SELECT * FROM users' } });
    fireEvent.click(executeButton);

    await waitFor(() => {
      expect(apiClient.executeQuery).toHaveBeenCalledWith('SELECT * FROM users');
      expect(mockOnQueryExecuted).toHaveBeenCalled();
      expect(textarea.value).toBe(''); // Query should be cleared after successful execution
    });
  });

  it('shows error message when query execution fails', async () => {
    const errorMessage = 'SQL syntax error';
    apiClient.executeQuery.mockRejectedValue({
      response: { data: { detail: errorMessage } }
    });

    render(
      <QueryExecutor
        title="Execute Query"
        module_id="database"
        onQueryExecuted={mockOnQueryExecuted}
      />
    );

    const textarea = screen.getByPlaceholderText(/Enter your SQL query here/);
    const executeButton = screen.getByRole('button', { name: 'Execute Query' });

    fireEvent.change(textarea, { target: { value: 'INVALID SQL' } });
    fireEvent.click(executeButton);

    await waitFor(() => {
      expect(screen.getByText(errorMessage)).toBeInTheDocument();
      expect(mockOnQueryExecuted).not.toHaveBeenCalled();
    });
  });

  it('shows error when trying to execute empty query via keyboard shortcut', () => {
    render(
      <QueryExecutor
        title="Execute Query"
        module_id="database"
        onQueryExecuted={mockOnQueryExecuted}
      />
    );

    const textarea = screen.getByPlaceholderText(/Enter your SQL query here/);

    // Add some whitespace
    fireEvent.change(textarea, { target: { value: '   ' } });
    
    // Use keyboard shortcut to trigger execution (since button is disabled for empty queries)
    fireEvent.keyDown(textarea, { key: 'Enter', ctrlKey: true });

    expect(screen.getByText('Please enter a query to execute')).toBeInTheDocument();
    expect(apiClient.executeQuery).not.toHaveBeenCalled();
  });

  it('disables execute button for whitespace-only queries', () => {
    render(
      <QueryExecutor
        title="Execute Query"
        module_id="database"
        onQueryExecuted={mockOnQueryExecuted}
      />
    );

    const textarea = screen.getByPlaceholderText(/Enter your SQL query here/);
    const executeButton = screen.getByRole('button', { name: 'Execute Query' });

    // Add some whitespace
    fireEvent.change(textarea, { target: { value: '   ' } });
    
    // Button should remain disabled for whitespace-only content
    expect(executeButton).toBeDisabled();
  });

  it('executes query with Ctrl+Enter keyboard shortcut', async () => {
    apiClient.executeQuery.mockResolvedValue({ data: { status: 'success' } });

    render(
      <QueryExecutor
        title="Execute Query"
        module_id="database"
        onQueryExecuted={mockOnQueryExecuted}
      />
    );

    const textarea = screen.getByPlaceholderText(/Enter your SQL query here/);

    fireEvent.change(textarea, { target: { value: 'SELECT * FROM users' } });
    fireEvent.keyDown(textarea, { key: 'Enter', ctrlKey: true });

    await waitFor(() => {
      expect(apiClient.executeQuery).toHaveBeenCalledWith('SELECT * FROM users');
      expect(mockOnQueryExecuted).toHaveBeenCalled();
    });
  });

  it('shows loading state during query execution', async () => {
    // Create a promise that we can control
    let resolvePromise;
    const promise = new Promise((resolve) => {
      resolvePromise = resolve;
    });
    apiClient.executeQuery.mockReturnValue(promise);

    render(
      <QueryExecutor
        title="Execute Query"
        module_id="database"
        onQueryExecuted={mockOnQueryExecuted}
      />
    );

    const textarea = screen.getByPlaceholderText(/Enter your SQL query here/);
    const executeButton = screen.getByRole('button', { name: 'Execute Query' });

    fireEvent.change(textarea, { target: { value: 'SELECT * FROM users' } });
    fireEvent.click(executeButton);

    // Check loading state
    expect(screen.getByRole('button', { name: 'Executing...' })).toBeInTheDocument();
    expect(textarea).toBeDisabled();

    // Resolve the promise
    resolvePromise({ data: { status: 'success' } });

    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Execute Query' })).toBeInTheDocument();
      expect(textarea).not.toBeDisabled();
    });
  });
});