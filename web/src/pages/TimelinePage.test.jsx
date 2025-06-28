import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import TimelinePage from './TimelinePage';
import { getTimelineEvents } from '../api/client';

// Mock the API client
jest.mock('../api/client');

// Mock DashboardLayoutManager
jest.mock('../components/DashboardLayoutManager', () => {
  return function MockDashboardLayoutManager({ isEditing, onSaveLayout, onCancelEdit }) {
    return (
      <div data-testid="dashboard-layout-manager">
        <div>Dashboard Layout Manager</div>
        <div>Editing: {isEditing.toString()}</div>
        {isEditing && (
          <>
            <button onClick={onSaveLayout}>Save Layout</button>
            <button onClick={onCancelEdit}>Cancel Edit</button>
          </>
        )}
      </div>
    );
  };
});

// Mock timers for polling
jest.useFakeTimers();

describe('TimelinePage', () => {
  const mockEvents = [
    {
      id: 1,
      timestamp: '2024-01-15T10:30:00Z',
      event_type: 'tool_execution',
      title: 'File Read Operation',
      description: 'Read file: test.txt',
      metadata: { tool: 'filesystem.read_file', file: 'test.txt' }
    },
    {
      id: 2,
      timestamp: '2024-01-15T10:25:00Z',
      event_type: 'system_event',
      title: 'System Started',
      description: 'IntentVerse system initialized',
      metadata: { version: '1.0.0' }
    },
    {
      id: 3,
      timestamp: '2024-01-14T15:45:00Z',
      event_type: 'tool_execution',
      title: 'Database Query',
      description: 'Executed SELECT query',
      metadata: { tool: 'database.query', rows: 5 }
    }
  ];

  const defaultProps = {
    isEditing: false,
    onSaveLayout: jest.fn(),
    onCancelEdit: jest.fn(),
    currentDashboard: 'timeline'
  };

  beforeEach(() => {
    jest.clearAllMocks();
    getTimelineEvents.mockResolvedValue({ data: mockEvents });
  });

  afterEach(() => {
    jest.runOnlyPendingTimers();
    jest.useRealTimers();
    jest.useFakeTimers();
  });

  describe('Initial Loading', () => {
    it('renders loading state initially', () => {
      render(<TimelinePage {...defaultProps} />);
      
      expect(screen.getByText('Loading timeline events...')).toBeInTheDocument();
    });

    it('fetches timeline events on mount', async () => {
      render(<TimelinePage {...defaultProps} />);
      
      await waitFor(() => {
        expect(getTimelineEvents).toHaveBeenCalledTimes(1);
      });
    });

    it('displays events after loading', async () => {
      render(<TimelinePage {...defaultProps} />);
      
      await waitFor(() => {
        expect(screen.getByText('File Read Operation')).toBeInTheDocument();
        expect(screen.getByText('System Started')).toBeInTheDocument();
        expect(screen.getByText('Database Query')).toBeInTheDocument();
      });
    });
  });

  describe('Event Display', () => {
    it('sorts events by timestamp (newest first)', async () => {
      render(<TimelinePage {...defaultProps} />);
      
      await waitFor(() => {
        const eventTitles = screen.getAllByText(/File Read Operation|System Started|Database Query/);
        expect(eventTitles[0]).toHaveTextContent('File Read Operation'); // 10:30
        expect(eventTitles[1]).toHaveTextContent('System Started'); // 10:25
        expect(eventTitles[2]).toHaveTextContent('Database Query'); // Previous day
      });
    });

    it('groups events by date', async () => {
      render(<TimelinePage {...defaultProps} />);
      
      await waitFor(() => {
        // Should have date headers for grouping
        expect(screen.getByText('1/15/2024')).toBeInTheDocument();
        expect(screen.getByText('1/14/2024')).toBeInTheDocument();
      });
    });

    it('displays event metadata correctly', async () => {
      render(<TimelinePage {...defaultProps} />);
      
      await waitFor(() => {
        expect(screen.getByText('Read file: test.txt')).toBeInTheDocument();
        expect(screen.getByText('IntentVerse system initialized')).toBeInTheDocument();
        expect(screen.getByText('Executed SELECT query')).toBeInTheDocument();
      });
    });
  });

  describe('Event Filtering', () => {
    it('shows all event types in filter dropdown', async () => {
      render(<TimelinePage {...defaultProps} />);
      
      await waitFor(() => {
        expect(screen.getByText('All Events')).toBeInTheDocument();
        expect(screen.getByText('tool_execution')).toBeInTheDocument();
        expect(screen.getByText('system_event')).toBeInTheDocument();
      });
    });

    it('filters events by type when filter is selected', async () => {
      const user = userEvent.setup();
      render(<TimelinePage {...defaultProps} />);
      
      await waitFor(() => {
        expect(screen.getByText('File Read Operation')).toBeInTheDocument();
        expect(screen.getByText('System Started')).toBeInTheDocument();
      });

      // Filter by tool_execution
      const filterSelect = screen.getByDisplayValue('All Events');
      await user.selectOptions(filterSelect, 'tool_execution');
      
      expect(screen.getByText('File Read Operation')).toBeInTheDocument();
      expect(screen.getByText('Database Query')).toBeInTheDocument();
      expect(screen.queryByText('System Started')).not.toBeInTheDocument();
    });

    it('resets filter when "All Events" is selected', async () => {
      const user = userEvent.setup();
      render(<TimelinePage {...defaultProps} />);
      
      await waitFor(() => {
        expect(screen.getByText('File Read Operation')).toBeInTheDocument();
      });

      // First filter by system_event
      const filterSelect = screen.getByDisplayValue('All Events');
      await user.selectOptions(filterSelect, 'system_event');
      
      expect(screen.queryByText('File Read Operation')).not.toBeInTheDocument();
      expect(screen.getByText('System Started')).toBeInTheDocument();

      // Then reset to all events
      await user.selectOptions(filterSelect, '');
      
      expect(screen.getByText('File Read Operation')).toBeInTheDocument();
      expect(screen.getByText('System Started')).toBeInTheDocument();
    });
  });

  describe('Event Interaction', () => {
    it('shows event details when event is clicked', async () => {
      const user = userEvent.setup();
      render(<TimelinePage {...defaultProps} />);
      
      await waitFor(() => {
        expect(screen.getByText('File Read Operation')).toBeInTheDocument();
      });

      const eventElement = screen.getByText('File Read Operation');
      await user.click(eventElement);
      
      // Should show detailed view
      expect(screen.getByText('Event Details')).toBeInTheDocument();
      expect(screen.getByText('tool_execution')).toBeInTheDocument();
    });

    it('shows tooltip on event hover', async () => {
      const user = userEvent.setup();
      render(<TimelinePage {...defaultProps} />);
      
      await waitFor(() => {
        expect(screen.getByText('File Read Operation')).toBeInTheDocument();
      });

      const eventElement = screen.getByText('File Read Operation');
      await user.hover(eventElement);
      
      // Should show tooltip with event details
      expect(screen.getByText('tool_execution')).toBeInTheDocument();
    });

    it('hides tooltip when mouse leaves event', async () => {
      const user = userEvent.setup();
      render(<TimelinePage {...defaultProps} />);
      
      await waitFor(() => {
        expect(screen.getByText('File Read Operation')).toBeInTheDocument();
      });

      const eventElement = screen.getByText('File Read Operation');
      await user.hover(eventElement);
      await user.unhover(eventElement);
      
      // Tooltip should be hidden
      await waitFor(() => {
        expect(screen.queryByText('Event tooltip')).not.toBeInTheDocument();
      });
    });
  });

  describe('Polling and Real-time Updates', () => {
    it('sets up polling interval for events', async () => {
      render(<TimelinePage {...defaultProps} />);
      
      await waitFor(() => {
        expect(getTimelineEvents).toHaveBeenCalledTimes(1);
      });

      // Fast-forward 5 seconds
      jest.advanceTimersByTime(5000);
      
      await waitFor(() => {
        expect(getTimelineEvents).toHaveBeenCalledTimes(2);
      });
    });

    it('clears polling interval on unmount', async () => {
      const { unmount } = render(<TimelinePage {...defaultProps} />);
      
      await waitFor(() => {
        expect(getTimelineEvents).toHaveBeenCalledTimes(1);
      });

      unmount();
      
      // Fast-forward 5 seconds after unmount
      jest.advanceTimersByTime(5000);
      
      // Should not call API again
      expect(getTimelineEvents).toHaveBeenCalledTimes(1);
    });

    it('updates events when new data is received', async () => {
      render(<TimelinePage {...defaultProps} />);
      
      await waitFor(() => {
        expect(screen.getByText('File Read Operation')).toBeInTheDocument();
      });

      // Mock new events for the next poll
      const newEvents = [
        ...mockEvents,
        {
          id: 4,
          timestamp: '2024-01-15T11:00:00Z',
          event_type: 'tool_execution',
          title: 'New Event',
          description: 'A new event occurred',
          metadata: {}
        }
      ];
      getTimelineEvents.mockResolvedValue({ data: newEvents });

      // Trigger polling
      jest.advanceTimersByTime(5000);
      
      await waitFor(() => {
        expect(screen.getByText('New Event')).toBeInTheDocument();
      });
    });
  });

  describe('Error Handling', () => {
    it('displays error message when API call fails', async () => {
      getTimelineEvents.mockRejectedValue(new Error('API Error'));
      
      render(<TimelinePage {...defaultProps} />);
      
      await waitFor(() => {
        expect(screen.getByText('Failed to fetch timeline events. Please ensure the core service is running.')).toBeInTheDocument();
      });
    });

    it('continues polling even after error', async () => {
      getTimelineEvents.mockRejectedValueOnce(new Error('API Error'));
      getTimelineEvents.mockResolvedValue({ data: mockEvents });
      
      render(<TimelinePage {...defaultProps} />);
      
      await waitFor(() => {
        expect(screen.getByText('Failed to fetch timeline events. Please ensure the core service is running.')).toBeInTheDocument();
      });

      // Fast-forward to next poll
      jest.advanceTimersByTime(5000);
      
      await waitFor(() => {
        expect(screen.getByText('File Read Operation')).toBeInTheDocument();
      });
    });
  });

  describe('Layout Management Integration', () => {
    it('renders DashboardLayoutManager when editing', () => {
      render(<TimelinePage {...defaultProps} isEditing={true} />);
      
      expect(screen.getByTestId('dashboard-layout-manager')).toBeInTheDocument();
      expect(screen.getByText('Editing: true')).toBeInTheDocument();
    });

    it('passes correct props to DashboardLayoutManager', () => {
      const mockSaveLayout = jest.fn();
      const mockCancelEdit = jest.fn();
      
      render(
        <TimelinePage 
          {...defaultProps} 
          isEditing={true}
          onSaveLayout={mockSaveLayout}
          onCancelEdit={mockCancelEdit}
        />
      );
      
      expect(screen.getByText('Save Layout')).toBeInTheDocument();
      expect(screen.getByText('Cancel Edit')).toBeInTheDocument();
    });

    it('calls onSaveLayout when save is clicked', async () => {
      const user = userEvent.setup();
      const mockSaveLayout = jest.fn();
      
      render(
        <TimelinePage 
          {...defaultProps} 
          isEditing={true}
          onSaveLayout={mockSaveLayout}
        />
      );
      
      const saveButton = screen.getByText('Save Layout');
      await user.click(saveButton);
      
      expect(mockSaveLayout).toHaveBeenCalledTimes(1);
    });

    it('calls onCancelEdit when cancel is clicked', async () => {
      const user = userEvent.setup();
      const mockCancelEdit = jest.fn();
      
      render(
        <TimelinePage 
          {...defaultProps} 
          isEditing={true}
          onCancelEdit={mockCancelEdit}
        />
      );
      
      const cancelButton = screen.getByText('Cancel Edit');
      await user.click(cancelButton);
      
      expect(mockCancelEdit).toHaveBeenCalledTimes(1);
    });
  });

  describe('Empty State', () => {
    it('displays empty state when no events are available', async () => {
      getTimelineEvents.mockResolvedValue({ data: [] });
      
      render(<TimelinePage {...defaultProps} />);
      
      await waitFor(() => {
        expect(screen.getByText('No timeline events found.')).toBeInTheDocument();
      });
    });

    it('displays empty state when all events are filtered out', async () => {
      const user = userEvent.setup();
      render(<TimelinePage {...defaultProps} />);
      
      await waitFor(() => {
        expect(screen.getByText('File Read Operation')).toBeInTheDocument();
      });

      // Filter by a type that doesn't exist
      const filterSelect = screen.getByDisplayValue('All Events');
      await user.selectOptions(filterSelect, 'nonexistent_type');
      
      expect(screen.getByText('No events match the selected filter.')).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('has proper ARIA labels for interactive elements', async () => {
      render(<TimelinePage {...defaultProps} />);
      
      await waitFor(() => {
        const filterSelect = screen.getByLabelText('Filter by event type');
        expect(filterSelect).toBeInTheDocument();
      });
    });

    it('supports keyboard navigation for events', async () => {
      const user = userEvent.setup();
      render(<TimelinePage {...defaultProps} />);
      
      await waitFor(() => {
        expect(screen.getByText('File Read Operation')).toBeInTheDocument();
      });

      const eventElement = screen.getByText('File Read Operation');
      eventElement.focus();
      
      await user.keyboard('{Enter}');
      
      expect(screen.getByText('Event Details')).toBeInTheDocument();
    });
  });
});