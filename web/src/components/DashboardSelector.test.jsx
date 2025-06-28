import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import DashboardSelector from './DashboardSelector';
import { getModulesStatus } from '../api/client';

// Mock the API client
jest.mock('../api/client');

describe('DashboardSelector', () => {
  const mockOnDashboardChange = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
    // Default mock - only state dashboard available
    getModulesStatus.mockResolvedValue({
      data: {
        modules: {
          timeline: { is_enabled: false, is_loaded: false }
        }
      }
    });
  });

  it('renders with default state dashboard', async () => {
    render(<DashboardSelector currentDashboard="state" onDashboardChange={mockOnDashboardChange} />);
    
    // Should show the state dashboard as current
    expect(screen.getByText('State')).toBeInTheDocument();
  });

  it('shows dropdown when clicked', async () => {
    const user = userEvent.setup();
    render(<DashboardSelector currentDashboard="state" onDashboardChange={mockOnDashboardChange} />);
    
    const selectorButton = screen.getByRole('button');
    await user.click(selectorButton);
    
    expect(screen.getByText('Switch Dashboard')).toBeInTheDocument();
    expect(screen.getByText('View and manage module states')).toBeInTheDocument();
  });

  it('shows timeline dashboard when timeline module is enabled and loaded', async () => {
    const user = userEvent.setup();
    
    // Mock timeline module as enabled and loaded
    getModulesStatus.mockResolvedValue({
      data: {
        modules: {
          timeline: { is_enabled: true, is_loaded: true }
        }
      }
    });

    render(<DashboardSelector currentDashboard="state" onDashboardChange={mockOnDashboardChange} />);
    
    // Wait for the module status to load
    await waitFor(() => {
      expect(getModulesStatus).toHaveBeenCalled();
    });

    const selectorButton = screen.getByRole('button');
    await user.click(selectorButton);

    // Should show timeline option since it's enabled and loaded
    expect(screen.getByText('View events and activity')).toBeInTheDocument();
    expect(screen.getByText('Timeline')).toBeInTheDocument();
  });

  it('calls onDashboardChange when different dashboard is selected', async () => {
    const user = userEvent.setup();
    
    // Mock timeline module as enabled and loaded
    getModulesStatus.mockResolvedValue({
      data: {
        modules: {
          timeline: { is_enabled: true, is_loaded: true }
        }
      }
    });

    render(<DashboardSelector currentDashboard="state" onDashboardChange={mockOnDashboardChange} />);
    
    // Wait for the module status to load
    await waitFor(() => {
      expect(getModulesStatus).toHaveBeenCalled();
    });

    const selectorButton = screen.getByRole('button');
    await user.click(selectorButton);

    // Click on timeline dashboard
    const timelineOption = screen.getByText('Timeline');
    await user.click(timelineOption);

    expect(mockOnDashboardChange).toHaveBeenCalledWith('timeline');
  });

  it('does not show timeline dashboard when timeline module is disabled', async () => {
    const user = userEvent.setup();
    
    // Mock timeline module as disabled
    getModulesStatus.mockResolvedValue({
      data: {
        modules: {
          timeline: { is_enabled: false, is_loaded: false }
        }
      }
    });

    render(<DashboardSelector currentDashboard="state" onDashboardChange={mockOnDashboardChange} />);
    
    // Wait for the module status to load
    await waitFor(() => {
      expect(getModulesStatus).toHaveBeenCalled();
    });

    const selectorButton = screen.getByRole('button');
    await user.click(selectorButton);

    // Should not show timeline option
    expect(screen.queryByText('View events and activity')).not.toBeInTheDocument();
    expect(screen.queryByText('Timeline')).not.toBeInTheDocument();
  });

  it('shows footer message when only one dashboard is available', async () => {
    const user = userEvent.setup();
    
    render(<DashboardSelector currentDashboard="state" onDashboardChange={mockOnDashboardChange} />);
    
    const selectorButton = screen.getByRole('button');
    await user.click(selectorButton);

    expect(screen.getByText('Enable modules in Settings to see more dashboards')).toBeInTheDocument();
  });

  it('closes dropdown when clicking outside', async () => {
    const user = userEvent.setup();
    
    render(
      <div>
        <DashboardSelector currentDashboard="state" onDashboardChange={mockOnDashboardChange} />
        <div data-testid="outside">Outside element</div>
      </div>
    );
    
    const selectorButton = screen.getByRole('button');
    await user.click(selectorButton);

    // Dropdown should be open
    expect(screen.getByText('Switch Dashboard')).toBeInTheDocument();

    // Click outside
    const outsideElement = screen.getByTestId('outside');
    await user.click(outsideElement);

    // Dropdown should be closed
    expect(screen.queryByText('Switch Dashboard')).not.toBeInTheDocument();
  });

  it('handles API error gracefully', async () => {
    // Mock API error
    getModulesStatus.mockRejectedValue(new Error('API Error'));

    render(<DashboardSelector currentDashboard="state" onDashboardChange={mockOnDashboardChange} />);
    
    // Should still render with fallback state dashboard
    expect(screen.getByText('State')).toBeInTheDocument();
  });
});