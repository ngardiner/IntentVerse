import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ConfirmationPopup from './ConfirmationPopup';

describe('ConfirmationPopup', () => {
  const mockOnConfirm = jest.fn();
  const mockOnCancel = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders confirmation popup with message', () => {
    render(
      <ConfirmationPopup
        message="Are you sure you want to delete this item?"
        onConfirm={mockOnConfirm}
        onCancel={mockOnCancel}
      />
    );

    expect(screen.getByText('Confirmation')).toBeInTheDocument();
    expect(screen.getByText('Are you sure you want to delete this item?')).toBeInTheDocument();
    expect(screen.getByText('Cancel')).toBeInTheDocument();
    expect(screen.getByText('Delete')).toBeInTheDocument();
  });

  it('calls onConfirm when confirm button is clicked', async () => {
    const user = userEvent.setup();
    
    render(
      <ConfirmationPopup
        message="Are you sure?"
        onConfirm={mockOnConfirm}
        onCancel={mockOnCancel}
      />
    );

    const confirmButton = screen.getByText('Delete');
    await user.click(confirmButton);

    expect(mockOnConfirm).toHaveBeenCalledTimes(1);
  });

  it('calls onCancel when cancel button is clicked', async () => {
    const user = userEvent.setup();
    
    render(
      <ConfirmationPopup
        message="Are you sure?"
        onConfirm={mockOnConfirm}
        onCancel={mockOnCancel}
      />
    );

    const cancelButton = screen.getByText('Cancel');
    await user.click(cancelButton);

    expect(mockOnCancel).toHaveBeenCalledTimes(1);
  });

  it('calls onCancel when close button (×) is clicked', async () => {
    const user = userEvent.setup();
    
    render(
      <ConfirmationPopup
        message="Are you sure?"
        onConfirm={mockOnConfirm}
        onCancel={mockOnCancel}
      />
    );

    const closeButton = document.querySelector('.confirmation-popup-close');
    await user.click(closeButton);

    expect(mockOnCancel).toHaveBeenCalledTimes(1);
  });

  it('calls onCancel when clicking outside the popup', async () => {
    const user = userEvent.setup();
    
    render(
      <ConfirmationPopup
        message="Are you sure?"
        onConfirm={mockOnConfirm}
        onCancel={mockOnCancel}
      />
    );

    const overlay = screen.getByText('Are you sure?').closest('.confirmation-popup-overlay');
    await user.click(overlay);

    expect(mockOnCancel).toHaveBeenCalledTimes(1);
  });

  it('does not call onCancel when clicking inside the popup content', async () => {
    const user = userEvent.setup();
    
    render(
      <ConfirmationPopup
        message="Are you sure?"
        onConfirm={mockOnConfirm}
        onCancel={mockOnCancel}
      />
    );

    const popupContent = screen.getByText('Are you sure?').closest('.confirmation-popup-content');
    await user.click(popupContent);

    expect(mockOnCancel).not.toHaveBeenCalled();
  });

  it('shows processing state correctly', () => {
    render(
      <ConfirmationPopup
        message="Deleting item..."
        onConfirm={mockOnConfirm}
        onCancel={mockOnCancel}
        status="deleting"
      />
    );

    expect(screen.getByText('Confirmation')).toBeInTheDocument();
    expect(screen.getByText('Deleting item...')).toBeInTheDocument();
    
    // Buttons should not be visible during processing
    expect(screen.queryByText('Cancel')).not.toBeInTheDocument();
    expect(screen.queryByText('Delete')).not.toBeInTheDocument();
    expect(document.querySelector('.confirmation-popup-close')).not.toBeInTheDocument();
  });

  it('shows success state correctly', () => {
    render(
      <ConfirmationPopup
        message="Item deleted successfully!"
        onConfirm={mockOnConfirm}
        onCancel={mockOnCancel}
        status="success"
      />
    );

    expect(screen.getByText('Success')).toBeInTheDocument();
    expect(screen.getByText('Item deleted successfully!')).toBeInTheDocument();
    
    // Buttons should not be visible in success state
    expect(screen.queryByText('Cancel')).not.toBeInTheDocument();
    expect(screen.queryByText('Delete')).not.toBeInTheDocument();
    expect(document.querySelector('.confirmation-popup-close')).not.toBeInTheDocument();
  });

  it('shows error state correctly', () => {
    render(
      <ConfirmationPopup
        message="Failed to delete item"
        onConfirm={mockOnConfirm}
        onCancel={mockOnCancel}
        status="error"
      />
    );

    expect(screen.getByText('Error')).toBeInTheDocument();
    expect(screen.getByText('Failed to delete item')).toBeInTheDocument();
    
    // Buttons should not be visible in error state
    expect(screen.queryByText('Cancel')).not.toBeInTheDocument();
    expect(screen.queryByText('Delete')).not.toBeInTheDocument();
    expect(document.querySelector('.confirmation-popup-close')).not.toBeInTheDocument();
  });

  it('applies correct CSS classes based on status', () => {
    const { rerender } = render(
      <ConfirmationPopup
        message="Test message"
        onConfirm={mockOnConfirm}
        onCancel={mockOnCancel}
        status="deleting"
      />
    );

    let messageElement = screen.getByText('Test message');
    expect(messageElement).toHaveClass('confirmation-message', 'deleting');

    rerender(
      <ConfirmationPopup
        message="Test message"
        onConfirm={mockOnConfirm}
        onCancel={mockOnCancel}
        status="success"
      />
    );

    messageElement = screen.getByText('Test message');
    expect(messageElement).toHaveClass('confirmation-message', 'success');

    rerender(
      <ConfirmationPopup
        message="Test message"
        onConfirm={mockOnConfirm}
        onCancel={mockOnCancel}
        status="error"
      />
    );

    messageElement = screen.getByText('Test message');
    expect(messageElement).toHaveClass('confirmation-message', 'error');
  });

  it('disables buttons appropriately based on status', () => {
    const { rerender } = render(
      <ConfirmationPopup
        message="Test message"
        onConfirm={mockOnConfirm}
        onCancel={mockOnCancel}
      />
    );

    // Normal state - buttons should be enabled
    expect(screen.getByText('Cancel')).not.toBeDisabled();
    expect(screen.getByText('Delete')).not.toBeDisabled();

    // Processing state - no buttons should be visible
    rerender(
      <ConfirmationPopup
        message="Processing..."
        onConfirm={mockOnConfirm}
        onCancel={mockOnCancel}
        status="deleting"
      />
    );

    expect(screen.queryByText('Cancel')).not.toBeInTheDocument();
    expect(screen.queryByText('Delete')).not.toBeInTheDocument();
  });

  it('does not call onCancel when clicking overlay during processing', async () => {
    const user = userEvent.setup();
    
    render(
      <ConfirmationPopup
        message="Processing..."
        onConfirm={mockOnConfirm}
        onCancel={mockOnCancel}
        status="deleting"
      />
    );

    const overlay = screen.getByText('Processing...').closest('.confirmation-popup-overlay');
    await user.click(overlay);

    // Should not call onCancel during processing
    expect(mockOnCancel).not.toHaveBeenCalled();
  });
});