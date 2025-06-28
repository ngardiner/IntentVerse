import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import CreateEmailButton from './CreateEmailButton';
import { createDraft } from '../../api/client';

// Mock the API client
jest.mock('../../api/client', () => ({
  createDraft: jest.fn(),
}));

describe('CreateEmailButton', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('renders create email button', () => {
    render(<CreateEmailButton />);
    
    const button = screen.getByRole('button', { name: /create new email/i });
    expect(button).toBeInTheDocument();
    expect(button).toHaveAttribute('title', 'Create new email');
  });

  test('displays plus icon', () => {
    render(<CreateEmailButton />);
    
    const icon = screen.getByText('+');
    expect(icon).toBeInTheDocument();
    expect(icon).toHaveClass('create-email-icon');
  });

  test('calls createDraft API when clicked', async () => {
    const mockResponse = {
      data: {
        email_id: 'draft-123',
      },
    };
    createDraft.mockResolvedValue(mockResponse);

    const mockOnEmailCreated = jest.fn();
    render(<CreateEmailButton onEmailCreated={mockOnEmailCreated} />);
    
    const button = screen.getByRole('button', { name: /create new email/i });
    fireEvent.click(button);

    await waitFor(() => {
      expect(createDraft).toHaveBeenCalledWith([], '', '');
    });
  });

  test('calls onEmailCreated callback with new email data', async () => {
    const mockResponse = {
      data: {
        email_id: 'draft-123',
      },
    };
    createDraft.mockResolvedValue(mockResponse);

    const mockOnEmailCreated = jest.fn();
    render(<CreateEmailButton onEmailCreated={mockOnEmailCreated} />);
    
    const button = screen.getByRole('button', { name: /create new email/i });
    fireEvent.click(button);

    await waitFor(() => {
      expect(mockOnEmailCreated).toHaveBeenCalledWith({
        email_id: 'draft-123',
        to: [],
        cc: [],
        subject: '',
        body: '',
        timestamp: expect.any(String),
        isNewDraft: true,
      });
    });
  });

  test('handles API error gracefully', async () => {
    const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
    createDraft.mockRejectedValue(new Error('API Error'));

    const mockOnEmailCreated = jest.fn();
    render(<CreateEmailButton onEmailCreated={mockOnEmailCreated} />);
    
    const button = screen.getByRole('button', { name: /create new email/i });
    fireEvent.click(button);

    await waitFor(() => {
      expect(consoleErrorSpy).toHaveBeenCalledWith('Failed to create new email draft:', expect.any(Error));
    });

    expect(mockOnEmailCreated).not.toHaveBeenCalled();
    consoleErrorSpy.mockRestore();
  });

  test('does not call callback if no email_id in response', async () => {
    const mockResponse = {
      data: {},
    };
    createDraft.mockResolvedValue(mockResponse);

    const mockOnEmailCreated = jest.fn();
    render(<CreateEmailButton onEmailCreated={mockOnEmailCreated} />);
    
    const button = screen.getByRole('button', { name: /create new email/i });
    fireEvent.click(button);

    await waitFor(() => {
      expect(createDraft).toHaveBeenCalled();
    });

    expect(mockOnEmailCreated).not.toHaveBeenCalled();
  });
});