import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import DashboardSelector from './DashboardSelector';
import { getModulesStatus } from '../api/client';

// Mock the API client
jest.mock('../api/client');

describe('DashboardSelector', () => {
  const mockOnDashboardChange = jest.fn();
  
  const mockModulesResponse = {
    data: {
      modules: {
        timeline: { is_enabled: true, is_loaded: true },
        filesystem: { is_enabled: true, is_loaded: false },
        email: { is_enabled: false, is_loaded: false }
      }
    }
  };

  beforeEach(() => {
    jest.clearAllMocks();
    getModulesStatus.mockResolvedValue(mockModulesResponse);
  });

  it('renders with default state dashboard', async () => {
    render(
      <DashboardSelector 
        currentDashboard="state" 
        onDashboardChange={mockOnDashboardChange} 
      />
    );

    // Should show the state dashboard by default
    expect(screen.getByText('State')).toBeInTheDocument();
    expect(screen.getByText('⚡')).toBeInTheDocument();
  });

  it('loads available dashboards based on module status', async () => {
    render(
      <DashboardSelector 
        currentDashboard="state" 
        onDashboardChange={mockOnDashboardChange} 
      />
    );

    // Wait for API call to complete
    await waitFor(() => {
      expect(getModulesStatus).toHaveBeenCalled();
    });
  });

  it('opens dropdown when clicked', async () => {
    const user = userEvent.setup();
    
    render(
      <DashboardSelector 
        currentDashboard="state" 
        onDashboardChange={mockOnDashboardChange} 
      />
    );

    // Wait for component to load
    await waitFor(() => {
      expect(getModulesStatus).toHaveBeenCalled();
    });

    // Click the selector button
    const selectorButton = screen.getByRole('button');
    await user.click(selectorButton);

    // Should show dropdown
    expect(screen.getByText('Switch Dashboard')).toBeInTheDocument();
    expect(screen.getByText('State')).toBeInTheDocument();
  });

  it('shows timeline dashboard when timeline module is enabled and loaded', async () => {
    const user = userEvent.setup();
    
    render(
      <DashboardSelector 
        currentDashboard="state" 
        onDashboardChange={mockOnDashboardChange} 
      />
    );

    // Wait for component to load
    await waitFor(() => {
      expect(getModulesStatus).toHaveBeenCalled();
    });

    // Open dropdown
    const selectorButton = screen.getByRole('button');
    await user.click(selectorButton);

    // Should show timeline option since it's enabled and loaded
    expect(screen.getByText('Timeline')).toBeInTheDocument();
    expect(screen.getByText('📋')).toBeInTheDocument();
  });

  it('calls onDashboardChange when different dashboard is selected', async () => {
    const user = userEvent.setup();
    
    render(
      <DashboardSelector 
        currentDashboard="state" 
        onDashboardChange={mockOnDashboardChange} 
      />
    );

    // Wait for component to load
    await waitFor(() => {
      expect(getModulesStatus).toHaveBeenCalled();
    });

    // Open dropdown
    const selectorButton = screen.getByRole('button');
    await user.click(selectorButton);

    // Click timeline option
    const timelineOption = screen.getByText('Timeline');
    await user.click(timelineOption);

    // Should call the change handler
    expect(mockOnDashboardChange).toHaveBeenCalledWith('timeline');
  });

  it('does not call onDashboardChange when same dashboard is selected', async () => {
    const user = userEvent.setup();
    
    render(
      <DashboardSelector 
        currentDashboard="state" 
        onDashboardChange={mockOnDashboardChange} 
      />
    );

    // Wait for component to load
    await waitFor(() => {
      expect(getModulesStatus).toHaveBeenCalled();
    });

    // Open dropdown
    const selectorButton = screen.getByRole('button');
    await user.click(selectorButton);

    // Click state option (current dashboard)
    const stateOption = screen.getByText('View and manage module states');
    await user.click(stateOption.closest('button'));

    // Should not call the change handler
    expect(mockOnDashboardChange).not.toHaveBeenCalled();
  });

  it('closes dropdown when clicking outside', async () => {
    const user = userEvent.setup();
    
    render(
      <div>
        <DashboardSelector 
          currentDashboard="state" 
          onDashboardChange={mockOnDashboardChange} 
        />
        <div data-testid="outside">Outside element</div>
      </div>
    );

    // Wait for component to load
    await waitFor(() => {
      expect(getModulesStatus).toHaveBeenCalled();
    });

    // Open dropdown
    const selectorButton = screen.getByRole('button');
    await user.click(selectorButton);

    // Verify dropdown is open
    expect(screen.getByText('Switch Dashboard')).toBeInTheDocument();

    // Click outside
    const outsideElement = screen.getByTestId('outside');
    await user.click(outsideElement);

    // Dropdown should be closed
    await waitFor(() => {
      expect(screen.queryByText('Switch Dashboard')).not.toBeInTheDocument();
    });
  });

  it('closes dropdown when pressing Escape key', async () => {
    const user = userEvent.setup();
    
    render(
      <DashboardSelector 
        currentDashboard="state" 
        onDashboardChange={mockOnDashboardChange} 
      />
    );

    // Wait for component to load
    await waitFor(() => {
      expect(getModulesStatus).toHaveBeenCalled();
    });

    // Open dropdown
    const selectorButton = screen.getByRole('button');
    await user.click(selectorButton);

    // Verify dropdown is open
    expect(screen.getByText('Switch Dashboard')).toBeInTheDocument();

    // Press Escape
    await user.keyboard('{Escape}');

    // Dropdown should be closed
    await waitFor(() => {
      expect(screen.queryByText('Switch Dashboard')).not.toBeInTheDocument();
    });
  });

  it('shows helpful message when only one dashboard is available', async () => {
    // Mock response with no enabled modules
    getModulesStatus.mockResolvedValue({
      data: {
        modules: {
          timeline: { is_enabled: false, is_loaded: false }
        }
      }
    });

    const user = userEvent.setup();
    
    render(
      <DashboardSelector 
        currentDashboard="state" 
        onDashboardChange={mockOnDashboardChange} 
      />
    );

    // Wait for component to load
    await waitFor(() => {
      expect(getModulesStatus).toHaveBeenCalled();
    });

    // Open dropdown
    const selectorButton = screen.getByRole('button');
    await user.click(selectorButton);

    // Should show helpful message
    expect(screen.getByText('Enable modules in Settings to see more dashboards')).toBeInTheDocument();
  });

  it('handles API errors gracefully', async () => {
    // Mock API error
    getModulesStatus.mockRejectedValue(new Error('API Error'));

    render(
      <DashboardSelector 
        currentDashboard="state" 
        onDashboardChange={mockOnDashboardChange} 
      />
    );

    // Wait for error handling
    await waitFor(() => {
      expect(getModulesStatus).toHaveBeenCalled();
    });

    // Should still render with fallback state
    expect(screen.getByText('State')).toBeInTheDocument();
  });

  it('shows current dashboard indicator', async () => {
    const user = userEvent.setup();
    
    render(
      <DashboardSelector 
        currentDashboard="timeline" 
        onDashboardChange={mockOnDashboardChange} 
      />
    );

    // Wait for component to load
    await waitFor(() => {
      expect(getModulesStatus).toHaveBeenCalled();
    });

    // Open dropdown
    const selectorButton = screen.getByRole('button');
    await user.click(selectorButton);

    // Should show checkmark for current dashboard
    const timelineOption = screen.getByText('Timeline').closest('button');
    expect(timelineOption).toHaveClass('active');
  });
});