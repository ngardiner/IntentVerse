import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import EditButton from './EditButton';

describe('EditButton', () => {
  const mockOnClick = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders edit button in non-editing state', () => {
    render(<EditButton isEditing={false} onClick={mockOnClick} />);

    const button = screen.getByRole('button');
    expect(button).toBeInTheDocument();
    expect(button).toHaveClass('edit-button');
    expect(button).not.toHaveClass('active');
    expect(button).toHaveAttribute('title', 'Edit dashboard layout');
  });

  it('renders edit button in editing state', () => {
    render(<EditButton isEditing={true} onClick={mockOnClick} />);

    const button = screen.getByRole('button');
    expect(button).toBeInTheDocument();
    expect(button).toHaveClass('edit-button', 'active');
    expect(button).toHaveAttribute('title', 'Exit edit mode');
  });

  it('calls onClick when button is clicked', async () => {
    const user = userEvent.setup();
    
    render(<EditButton isEditing={false} onClick={mockOnClick} />);

    const button = screen.getByRole('button');
    await user.click(button);

    expect(mockOnClick).toHaveBeenCalledTimes(1);
  });

  it('calls onClick when button is clicked in editing state', async () => {
    const user = userEvent.setup();
    
    render(<EditButton isEditing={true} onClick={mockOnClick} />);

    const button = screen.getByRole('button');
    await user.click(button);

    expect(mockOnClick).toHaveBeenCalledTimes(1);
  });

  it('displays correct SVG icon for non-editing state', () => {
    render(<EditButton isEditing={false} onClick={mockOnClick} />);

    const button = screen.getByRole('button');
    const svg = button.querySelector('svg');
    
    expect(svg).toBeInTheDocument();
    expect(svg).toHaveAttribute('width', '18');
    expect(svg).toHaveAttribute('height', '18');
    expect(svg).toHaveAttribute('viewBox', '0 0 18 18');
    expect(svg).toHaveAttribute('fill', 'currentColor');
    
    // Check for the grid icon path (4 squares)
    const path = svg.querySelector('path');
    expect(path).toHaveAttribute('d', 'M 2 2 h 6 v 6 h -6 z M 10 2 h 6 v 6 h -6 z M 2 10 h 6 v 6 h -6 z M 10 10 h 6 v 6 h -6 z');
  });

  it('displays correct SVG icon for editing state', () => {
    render(<EditButton isEditing={true} onClick={mockOnClick} />);

    const button = screen.getByRole('button');
    const svg = button.querySelector('svg');
    
    expect(svg).toBeInTheDocument();
    expect(svg).toHaveAttribute('width', '18');
    expect(svg).toHaveAttribute('height', '18');
    expect(svg).toHaveAttribute('viewBox', '0 0 18 18');
    
    // Check for the X icon path
    const path = svg.querySelector('path');
    expect(path).toHaveAttribute('d', 'M 4 4 L 14 14 M 14 4 L 4 14');
    expect(path).toHaveAttribute('fill', 'none');
    expect(path).toHaveAttribute('stroke', 'currentColor');
    expect(path).toHaveAttribute('stroke-width', '2');
    expect(path).toHaveAttribute('stroke-linecap', 'round');
  });

  it('toggles between states correctly', () => {
    const { rerender } = render(<EditButton isEditing={false} onClick={mockOnClick} />);

    // Initial state - not editing
    let button = screen.getByRole('button');
    expect(button).not.toHaveClass('active');
    expect(button).toHaveAttribute('title', 'Edit dashboard layout');

    // Rerender in editing state
    rerender(<EditButton isEditing={true} onClick={mockOnClick} />);

    button = screen.getByRole('button');
    expect(button).toHaveClass('active');
    expect(button).toHaveAttribute('title', 'Exit edit mode');

    // Rerender back to non-editing state
    rerender(<EditButton isEditing={false} onClick={mockOnClick} />);

    button = screen.getByRole('button');
    expect(button).not.toHaveClass('active');
    expect(button).toHaveAttribute('title', 'Edit dashboard layout');
  });

  it('is accessible with proper ARIA attributes', () => {
    render(<EditButton isEditing={false} onClick={mockOnClick} />);

    const button = screen.getByRole('button');
    expect(button).toHaveAttribute('title');
    
    // Button should be focusable
    expect(button).not.toHaveAttribute('disabled');
  });

  it('maintains focus behavior', async () => {
    const user = userEvent.setup();
    
    render(<EditButton isEditing={false} onClick={mockOnClick} />);

    const button = screen.getByRole('button');
    
    // Focus the button
    await user.tab();
    expect(button).toHaveFocus();

    // Click should maintain focus
    await user.click(button);
    expect(mockOnClick).toHaveBeenCalledTimes(1);
  });

  it('handles keyboard interaction', async () => {
    const user = userEvent.setup();
    
    render(<EditButton isEditing={false} onClick={mockOnClick} />);

    const button = screen.getByRole('button');
    
    // Focus and press Enter
    button.focus();
    await user.keyboard('{Enter}');
    expect(mockOnClick).toHaveBeenCalledTimes(1);

    // Reset mock and try Space
    mockOnClick.mockClear();
    await user.keyboard(' ');
    expect(mockOnClick).toHaveBeenCalledTimes(1);
  });
});