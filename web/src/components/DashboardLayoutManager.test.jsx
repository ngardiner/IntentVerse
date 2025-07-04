import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import DashboardLayoutManager from './DashboardLayoutManager';

// Mock localStorage
const localStorageMock = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn(),
};

// Properly mock localStorage
Object.defineProperty(window, 'localStorage', {
  value: localStorageMock,
  writable: true
});

describe('DashboardLayoutManager', () => {
  const mockChildren = [
    <div key="widget1" module_id="widget1" sizeClass="size-medium" data-testid="widget1">
      Widget 1
    </div>,
    <div key="widget2" module_id="widget2" sizeClass="size-small" data-testid="widget2">
      Widget 2
    </div>,
    <div key="widget3" module_id="widget3" sizeClass="size-large" data-testid="widget3">
      Widget 3
    </div>
  ];

  let defaultProps;
  
  const createDefaultProps = () => ({
    isEditing: false,
    onSaveLayout: jest.fn(),
    onCancelEdit: jest.fn(),
    children: mockChildren,
    currentDashboard: 'test-dashboard'
  });

  beforeEach(() => {
    jest.clearAllMocks();
    localStorageMock.getItem.mockClear();
    localStorageMock.setItem.mockClear();
    localStorageMock.removeItem.mockClear();
    localStorageMock.clear.mockClear();
    localStorageMock.getItem.mockReturnValue(null);
    defaultProps = createDefaultProps();
  });

  describe('Basic Rendering', () => {
    it('renders children correctly in view mode', () => {
      render(<DashboardLayoutManager {...defaultProps} />);
      
      expect(screen.getByTestId('widget1')).toBeInTheDocument();
      expect(screen.getByTestId('widget2')).toBeInTheDocument();
      expect(screen.getByTestId('widget3')).toBeInTheDocument();
      expect(screen.getByText('Widget 1')).toBeInTheDocument();
      expect(screen.getByText('Widget 2')).toBeInTheDocument();
      expect(screen.getByText('Widget 3')).toBeInTheDocument();
    });

    it('applies correct grid layout classes', () => {
      render(<DashboardLayoutManager {...defaultProps} />);
      
      const widget = screen.getByTestId('widget1');
      const gridContainer = widget.parentElement.parentElement; // The modules-grid is the grandparent
      expect(gridContainer).toHaveClass('modules-grid');
    });

    it('handles empty children gracefully', () => {
      render(<DashboardLayoutManager {...defaultProps} children={[]} />);
      
      // Should render without crashing - check for the main container
      expect(document.querySelector('.dashboard-layout-manager')).toBeInTheDocument();
      expect(document.querySelector('.modules-grid')).toBeInTheDocument();
    });

    it('handles null children gracefully', () => {
      render(<DashboardLayoutManager {...defaultProps} children={null} />);
      
      // Should render without crashing - check for the main container
      expect(document.querySelector('.dashboard-layout-manager')).toBeInTheDocument();
      expect(document.querySelector('.modules-grid')).toBeInTheDocument();
    });
  });

  describe('Edit Mode', () => {
    it('shows edit controls when in editing mode', () => {
      render(<DashboardLayoutManager {...defaultProps} isEditing={true} />);
      
      expect(screen.getByText('Save Layout')).toBeInTheDocument();
      expect(screen.getByText('Cancel')).toBeInTheDocument();
      expect(screen.getByText('Reset to Default')).toBeInTheDocument();
    });

    it('shows widget controls in edit mode', () => {
      render(<DashboardLayoutManager {...defaultProps} isEditing={true} />);
      
      // Should show hide/show buttons for each widget
      const hideButtons = screen.getAllByText('Hide');
      expect(hideButtons).toHaveLength(3); // One for each widget
    });

    it('does not show edit controls in view mode', () => {
      render(<DashboardLayoutManager {...defaultProps} isEditing={false} />);
      
      expect(screen.queryByText('Save Layout')).not.toBeInTheDocument();
      expect(screen.queryByText('Cancel')).not.toBeInTheDocument();
      expect(screen.queryByText('Reset to Default')).not.toBeInTheDocument();
    });

    it('calls onSaveLayout when save button is clicked', async () => {
      const user = userEvent.setup();
      render(<DashboardLayoutManager {...defaultProps} isEditing={true} />);
      
      const saveButton = screen.getByText('Save Layout');
      await user.click(saveButton);
      
      expect(defaultProps.onSaveLayout).toHaveBeenCalledTimes(1);
    });

    it('calls onCancelEdit when cancel button is clicked', async () => {
      const user = userEvent.setup();
      render(<DashboardLayoutManager {...defaultProps} isEditing={true} />);
      
      const cancelButton = screen.getByText('Cancel');
      await user.click(cancelButton);
      
      expect(defaultProps.onCancelEdit).toHaveBeenCalledTimes(1);
    });
  });

  describe('Widget Visibility Management', () => {
    it('hides widget when hide button is clicked', async () => {
      const user = userEvent.setup();
      render(<DashboardLayoutManager {...defaultProps} isEditing={true} />);
      
      expect(screen.getByTestId('widget1')).toBeInTheDocument();
      
      const hideButtons = screen.getAllByText('Hide');
      await user.click(hideButtons[0]); // Hide first widget
      
      expect(screen.queryByTestId('widget1')).not.toBeInTheDocument();
    });

    it('shows hidden widget when show button is clicked', async () => {
      const user = userEvent.setup();
      render(<DashboardLayoutManager {...defaultProps} isEditing={true} />);
      
      // First hide a widget
      const hideButtons = screen.getAllByText('Hide');
      await user.click(hideButtons[0]);
      
      expect(screen.queryByTestId('widget1')).not.toBeInTheDocument();
      
      // Then show it again
      const showButton = screen.getByText('Show');
      await user.click(showButton);
      
      expect(screen.getByTestId('widget1')).toBeInTheDocument();
    });

    it('maintains hidden state during edit session', async () => {
      const user = userEvent.setup();
      render(<DashboardLayoutManager {...defaultProps} isEditing={true} />);
      
      // Hide a widget
      const hideButtons = screen.getAllByText('Hide');
      await user.click(hideButtons[0]);
      
      expect(screen.queryByTestId('widget1')).not.toBeInTheDocument();
      
      // Widget should remain hidden
      expect(screen.queryByTestId('widget1')).not.toBeInTheDocument();
      expect(screen.getByTestId('widget2')).toBeInTheDocument();
      expect(screen.getByTestId('widget3')).toBeInTheDocument();
    });

    it('restores original visibility on cancel', async () => {
      const user = userEvent.setup();
      render(<DashboardLayoutManager {...defaultProps} isEditing={true} />);
      
      // Hide a widget
      const hideButtons = screen.getAllByText('Hide');
      await user.click(hideButtons[0]);
      
      expect(screen.queryByTestId('widget1')).not.toBeInTheDocument();
      
      // Cancel editing
      const cancelButton = screen.getByText('Cancel');
      await user.click(cancelButton);
      
      expect(defaultProps.onCancelEdit).toHaveBeenCalled();
    });
  });

  describe('Layout Persistence', () => {
    it('localStorage mock is working', () => {
      localStorage.setItem('test', 'value');
      expect(localStorageMock.setItem).toHaveBeenCalledWith('test', 'value');
    });

    it('saves layout to localStorage when save is clicked', async () => {
      const user = userEvent.setup();
      render(<DashboardLayoutManager {...defaultProps} isEditing={true} />);
      
      // Wait for the component to be fully rendered and initialized
      await waitFor(() => {
        expect(screen.getByText('Save Layout')).toBeInTheDocument();
      });
      
      const saveButton = screen.getByText('Save Layout');
      
      // Verify the button is enabled and clickable
      expect(saveButton).toBeEnabled();
      expect(saveButton).toHaveAttribute('aria-label', 'Save layout changes');
      
      await user.click(saveButton);
      
      // First check that the onSaveLayout callback was called
      expect(defaultProps.onSaveLayout).toHaveBeenCalledTimes(1);
      
      // Then check that localStorage was called with the correct keys
      expect(localStorageMock.setItem).toHaveBeenCalledWith(
        'dashboard-layout-test-dashboard',
        expect.any(String)
      );
      expect(localStorageMock.setItem).toHaveBeenCalledWith(
        'dashboard-hidden-test-dashboard',
        expect.any(String)
      );
      
      // Verify localStorage was called exactly twice (layout + hidden state)
      expect(localStorageMock.setItem).toHaveBeenCalledTimes(2);
    });

    it('loads layout from localStorage on mount', async () => {
      const savedLayout = JSON.stringify({
        widget1: { row: 1, col: 1, colSpan: 6 },
        widget2: { row: 1, col: 7, colSpan: 3 },
        widget3: { row: 2, col: 1, colSpan: 9 }
      });
      
      // Mock getItem to return saved layout for layout key, null for hidden key
      localStorageMock.getItem.mockImplementation((key) => {
        if (key === 'dashboard-layout-test-dashboard') {
          return savedLayout;
        }
        return null;
      });
      
      render(<DashboardLayoutManager {...defaultProps} />);
      
      // Wait for the component to load and call localStorage for both layout and hidden state
      await waitFor(() => {
        expect(localStorageMock.getItem).toHaveBeenCalledWith('dashboard-layout-test-dashboard');
      });
      
      expect(localStorageMock.getItem).toHaveBeenCalledWith('dashboard-hidden-test-dashboard');
    });

    it('handles invalid localStorage data gracefully', () => {
      localStorageMock.getItem.mockReturnValue('invalid-json');
      
      render(<DashboardLayoutManager {...defaultProps} />);
      
      // Should not crash and should use default layout
      expect(screen.getByTestId('widget1')).toBeInTheDocument();
    });

    it('resets to default layout when reset button is clicked', async () => {
      const user = userEvent.setup();
      render(<DashboardLayoutManager {...defaultProps} isEditing={true} />);
      
      const resetButton = screen.getByText('Reset to Default');
      await user.click(resetButton);
      
      // Should restore original layout
      expect(screen.getByTestId('widget1')).toBeInTheDocument();
      expect(screen.getByTestId('widget2')).toBeInTheDocument();
      expect(screen.getByTestId('widget3')).toBeInTheDocument();
    });
  });

  describe('Size Class Handling', () => {
    it('applies correct column spans for different size classes', () => {
      const childrenWithSizes = [
        <div key="small" module_id="small" sizeClass="size-small" data-testid="small">Small</div>,
        <div key="medium" module_id="medium" sizeClass="size-medium" data-testid="medium">Medium</div>,
        <div key="large" module_id="large" sizeClass="size-large" data-testid="large">Large</div>,
        <div key="xlarge" module_id="xlarge" sizeClass="size-xlarge" data-testid="xlarge">XLarge</div>
      ];
      
      render(
        <DashboardLayoutManager 
          {...defaultProps} 
          children={childrenWithSizes}
          isEditing={true}
        />
      );
      
      // All widgets should be rendered
      expect(screen.getByTestId('small')).toBeInTheDocument();
      expect(screen.getByTestId('medium')).toBeInTheDocument();
      expect(screen.getByTestId('large')).toBeInTheDocument();
      expect(screen.getByTestId('xlarge')).toBeInTheDocument();
    });

    it('handles widgets without size class', () => {
      const childrenWithoutSize = [
        <div key="nosizeclass" module_id="nosizeclass" data-testid="nosizeclass">No Size Class</div>
      ];
      
      render(
        <DashboardLayoutManager 
          {...defaultProps} 
          children={childrenWithoutSize}
        />
      );
      
      expect(screen.getByTestId('nosizeclass')).toBeInTheDocument();
    });
  });

  describe('Drag and Drop (if implemented)', () => {
    it('enables drag and drop in edit mode', () => {
      render(<DashboardLayoutManager {...defaultProps} isEditing={true} />);
      
      const widget1 = screen.getByTestId('widget1');
      const wrapper = widget1.parentElement;
      expect(wrapper).toHaveAttribute('draggable', 'true');
    });

    it('disables drag and drop in view mode', () => {
      render(<DashboardLayoutManager {...defaultProps} isEditing={false} />);
      
      const widget1 = screen.getByTestId('widget1');
      const wrapper = widget1.parentElement;
      expect(wrapper).not.toHaveAttribute('draggable', 'true');
    });

    it('handles drag start event', () => {
      render(<DashboardLayoutManager {...defaultProps} isEditing={true} />);
      
      const widget1 = screen.getByTestId('widget1');
      const wrapper = widget1.parentElement;
      fireEvent.dragStart(wrapper);
      
      // Should set dragging state on wrapper
      expect(wrapper).toHaveClass('dragging');
    });

    it('handles drop event', async () => {
      render(<DashboardLayoutManager {...defaultProps} isEditing={true} />);
      
      const widget1 = screen.getByTestId('widget1');
      const wrapper1 = widget1.parentElement;
      
      fireEvent.dragStart(wrapper1);
      
      // Verify dragging class is added
      expect(wrapper1).toHaveClass('dragging');
      
      // Simulate drag end to clean up dragging state
      fireEvent.dragEnd(wrapper1);
      
      // Wait for the drag end to complete and dragging class to be removed
      await waitFor(() => {
        expect(wrapper1).not.toHaveClass('dragging');
      });
    });
  });

  describe('Responsive Behavior', () => {
    it('adjusts layout for different screen sizes', () => {
      // Mock window.innerWidth
      Object.defineProperty(window, 'innerWidth', {
        writable: true,
        configurable: true,
        value: 768, // Mobile width
      });
      
      render(<DashboardLayoutManager {...defaultProps} />);
      
      // Should render widgets in mobile layout
      expect(screen.getByTestId('widget1')).toBeInTheDocument();
    });

    it('handles window resize events', () => {
      render(<DashboardLayoutManager {...defaultProps} />);
      
      // Simulate window resize
      Object.defineProperty(window, 'innerWidth', {
        writable: true,
        configurable: true,
        value: 1200,
      });
      
      fireEvent(window, new Event('resize'));
      
      // Layout should adapt to new size
      expect(screen.getByTestId('widget1')).toBeInTheDocument();
    });
  });

  describe('Error Handling', () => {
    it('handles widgets without module_id gracefully', () => {
      const childrenWithoutId = [
        <div key="no-id" data-testid="no-id">No Module ID</div>
      ];
      
      render(
        <DashboardLayoutManager 
          {...defaultProps} 
          children={childrenWithoutId}
        />
      );
      
      // Should render without crashing
      expect(screen.getByTestId('no-id')).toBeInTheDocument();
    });

    it('handles localStorage errors gracefully', () => {
      localStorageMock.getItem.mockImplementation(() => {
        throw new Error('localStorage error');
      });
      
      render(<DashboardLayoutManager {...defaultProps} />);
      
      // Should render with default layout
      expect(screen.getByTestId('widget1')).toBeInTheDocument();
    });

    it('handles save errors gracefully', async () => {
      const user = userEvent.setup();
      localStorageMock.setItem.mockImplementation(() => {
        throw new Error('Save error');
      });
      
      render(<DashboardLayoutManager {...defaultProps} isEditing={true} />);
      
      const saveButton = screen.getByText('Save Layout');
      await user.click(saveButton);
      
      // Should still call onSaveLayout despite localStorage error
      expect(defaultProps.onSaveLayout).toHaveBeenCalled();
    });
  });

  describe('Accessibility', () => {
    it('has proper ARIA labels for edit controls', () => {
      render(<DashboardLayoutManager {...defaultProps} isEditing={true} />);
      
      expect(screen.getByLabelText('Save layout changes')).toBeInTheDocument();
      expect(screen.getByLabelText('Cancel layout changes')).toBeInTheDocument();
      expect(screen.getByLabelText('Reset layout to default')).toBeInTheDocument();
    });

    it('supports keyboard navigation in edit mode', async () => {
      const user = userEvent.setup();
      render(<DashboardLayoutManager {...defaultProps} isEditing={true} />);
      
      // Tab through edit controls
      await user.tab();
      expect(screen.getByText('Save Layout')).toHaveFocus();
      
      await user.tab();
      expect(screen.getByText('Cancel')).toHaveFocus();
    });

    it('announces layout changes to screen readers', async () => {
      const user = userEvent.setup();
      render(<DashboardLayoutManager {...defaultProps} isEditing={true} />);
      
      const hideButtons = screen.getAllByText('Hide');
      await user.click(hideButtons[0]);
      
      // Should have aria-live region for announcements
      expect(screen.getByRole('status')).toBeInTheDocument();
    });
  });
});