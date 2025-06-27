import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import SwitchableView from './SwitchableView';
import { getModuleState } from '../../api/client';

// Mock the API client
jest.mock('../../api/client');

// Mock GenericTable component
jest.mock('./GenericTable', () => {
  return function MockGenericTable(props) {
    return <div data-testid="generic-table">Table: {props.title}</div>;
  };
});

// Mock GenericKeyValue component
jest.mock('./GenericKeyValue', () => {
  return function MockGenericKeyValue(props) {
    return <div data-testid="generic-key-value">KeyValue: {props.title}</div>;
  };
});

describe('SwitchableView', () => {
  const mockViews = [
    {
      title: 'Table View',
      component_type: 'table',
      data_source_api: '/api/modules/test/state',
      data_path: 'tables'
    },
    {
      title: 'Key-Value View',
      component_type: 'key_value',
      data_source_api: '/api/modules/test/state',
      data_path: 'config'
    }
  ];

  beforeEach(() => {
    jest.clearAllMocks();
    getModuleState.mockResolvedValue({ data: { tables: [], config: {} } });
  });

  it('renders with first view selected by default', async () => {
    render(
      <SwitchableView
        title="Test Switchable"
        module_id="test"
        data_source_api="/api/modules/test/state"
        views={mockViews}
      />
    );

    await waitFor(() => {
      // The component shows the view title, not the main title when views are provided
      expect(screen.getByText('Table View')).toBeInTheDocument();
    });

    // Should show first view by default
    expect(screen.getByTestId('generic-table')).toBeInTheDocument();
    expect(screen.getByText('Table: Table View')).toBeInTheDocument();
  });

  it('switches between views when dropdown options are clicked', async () => {
    const user = userEvent.setup();
    
    render(
      <SwitchableView
        title="Test Switchable"
        module_id="test"
        data_source_api="/api/modules/test/state"
        views={mockViews}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Table View')).toBeInTheDocument();
    });

    // Should show table view initially
    expect(screen.getByTestId('generic-table')).toBeInTheDocument();

    // Click on dropdown button to open view selector
    const dropdownButton = screen.getByLabelText('Switch view');
    await user.click(dropdownButton);

    // Click on Key-Value View option
    const keyValueOption = screen.getByText('Key-Value View');
    await user.click(keyValueOption);

    // Should now show key-value view
    expect(screen.getByTestId('generic-key-value')).toBeInTheDocument();
    expect(screen.getByText('KeyValue: Key-Value View')).toBeInTheDocument();
    expect(screen.queryByTestId('generic-table')).not.toBeInTheDocument();
  });

  it('shows dropdown with view options', async () => {
    const user = userEvent.setup();
    
    render(
      <SwitchableView
        title="Test Switchable"
        module_id="test"
        data_source_api="/api/modules/test/state"
        views={mockViews}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Table View')).toBeInTheDocument();
    });

    // Should have dropdown button for multiple views
    const dropdownButton = screen.getByLabelText('Switch view');
    expect(dropdownButton).toBeInTheDocument();

    // Click dropdown to open options
    await user.click(dropdownButton);

    // Should show both view options
    expect(screen.getByText('Table View')).toBeInTheDocument();
    expect(screen.getByText('Key-Value View')).toBeInTheDocument();
  });

  it('handles single view correctly', async () => {
    const singleView = [mockViews[0]];
    
    render(
      <SwitchableView
        title="Single View"
        module_id="test"
        data_source_api="/api/modules/test/state"
        views={singleView}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Table View')).toBeInTheDocument();
    });

    // Should show the view
    expect(screen.getByTestId('generic-table')).toBeInTheDocument();
    
    // Should not show dropdown for single view
    expect(screen.queryByLabelText('Switch view')).not.toBeInTheDocument();
  });

  it('handles empty views array gracefully', () => {
    render(
      <SwitchableView
        title="Empty Views"
        module_id="test"
        data_source_api="/api/modules/test/state"
        views={[]}
      />
    );

    expect(screen.getByText('Empty Views')).toBeInTheDocument();
    // The component doesn't render anything when views array is empty
    expect(screen.queryByTestId('generic-table')).not.toBeInTheDocument();
    expect(screen.queryByTestId('generic-key-value')).not.toBeInTheDocument();
  });

  it('applies size class correctly', async () => {
    const { container } = render(
      <SwitchableView
        title="Test Switchable"
        module_id="test"
        data_source_api="/api/modules/test/state"
        views={mockViews}
        sizeClass="large-view"
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Table View')).toBeInTheDocument();
    });

    const switchableContainer = container.querySelector('.module-container');
    expect(switchableContainer).toHaveClass('large-view');
  });

  it('passes correct props to child components', async () => {
    render(
      <SwitchableView
        title="Test Switchable"
        module_id="test"
        data_source_api="/api/modules/test/state"
        views={mockViews}
      />
    );

    await waitFor(() => {
      expect(screen.getByTestId('generic-table')).toBeInTheDocument();
    });

    // The mock components should receive the correct title
    expect(screen.getByText('Table: Table View')).toBeInTheDocument();
  });

  it('handles view switching with keyboard navigation', async () => {
    const user = userEvent.setup();
    
    render(
      <SwitchableView
        title="Test Switchable"
        module_id="test"
        data_source_api="/api/modules/test/state"
        views={mockViews}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Table View')).toBeInTheDocument();
    });

    // Focus first tab and use arrow keys
    const tableTab = screen.getByText('Table View');
    tableTab.focus();
    
    // Press Tab to move to next tab
    await user.keyboard('{Tab}');
    
    const keyValueTab = screen.getByText('Key-Value View');
    expect(keyValueTab).toHaveFocus();
    
    // Press Enter to activate
    await user.keyboard('{Enter}');
    
    expect(screen.getByTestId('generic-key-value')).toBeInTheDocument();
  });

  it('maintains view state when switching back and forth', async () => {
    const user = userEvent.setup();
    
    render(
      <SwitchableView
        title="Test Switchable"
        module_id="test"
        data_source_api="/api/modules/test/state"
        views={mockViews}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Table View')).toBeInTheDocument();
    });

    // Start with table view
    expect(screen.getByTestId('generic-table')).toBeInTheDocument();

    // Switch to key-value view
    const keyValueTab = screen.getByText('Key-Value View');
    await user.click(keyValueTab);
    expect(screen.getByTestId('generic-key-value')).toBeInTheDocument();

    // Switch back to table view
    const tableTab = screen.getByText('Table View');
    await user.click(tableTab);
    expect(screen.getByTestId('generic-table')).toBeInTheDocument();
  });
});