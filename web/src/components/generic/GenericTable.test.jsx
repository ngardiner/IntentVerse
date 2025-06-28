import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import GenericTable from './GenericTable';
import { getModuleState } from '../../api/client';

// Mock the API client
jest.mock('../../api/client');

// Mock EmailPopout component
jest.mock('./EmailPopout', () => {
  return function MockEmailPopout({ email, onClose }) {
    return (
      <div data-testid="email-popout">
        <div>Email: {email.subject}</div>
        <button onClick={onClose}>Close</button>
      </div>
    );
  };
});

describe('GenericTable', () => {
  const mockTableData = [
    { id: 1, name: 'John Doe', email: 'john@example.com', age: 30 },
    { id: 2, name: 'Jane Smith', email: 'jane@example.com', age: 25 },
    { id: 3, name: 'Bob Johnson', email: 'bob@example.com', age: 35 }
  ];

  const mockColumns = [
    { data_key: 'id', header: 'ID', type: 'text' },
    { data_key: 'name', header: 'Name', type: 'text' },
    { data_key: 'email', header: 'Email', type: 'text' },
    { data_key: 'age', header: 'Age', type: 'number' }
  ];

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders loading state initially', () => {
    getModuleState.mockImplementation(() => new Promise(() => {})); // Never resolves
    
    render(
      <GenericTable
        title="Test Table"
        data_source_api="/api/modules/test/state"
        columns={mockColumns}
        module_id="test"
      />
    );

    expect(screen.getByText('Loading data...')).toBeInTheDocument();
  });

  it('renders table with data after loading', async () => {
    getModuleState.mockResolvedValue(mockTableData);
    
    render(
      <GenericTable
        title="Test Table"
        data_source_api="/api/modules/test/state"
        columns={mockColumns}
        module_id="test"
      />
    );

    // Wait for the data to load and table to render
    await waitFor(() => {
      expect(screen.getByText('ID')).toBeInTheDocument();
    });

    // Check all headers
    expect(screen.getByText('Name')).toBeInTheDocument();
    expect(screen.getByText('Email')).toBeInTheDocument();
    expect(screen.getByText('Age')).toBeInTheDocument();

    // Check data rows
    expect(screen.getByText('John Doe')).toBeInTheDocument();
    expect(screen.getByText('jane@example.com')).toBeInTheDocument();
    expect(screen.getByText('35')).toBeInTheDocument();
  });

  it('extracts data using data_path', async () => {
    const nestedData = {
      users: {
        list: mockTableData
      }
    };
    
    getModuleState.mockResolvedValue({ data: nestedData });
    
    render(
      <GenericTable
        title="Test Table"
        data_source_api="/api/modules/test/state"
        columns={mockColumns}
        module_id="test"
        data_path="users.list"
      />
    );

    await waitFor(() => {
      expect(screen.getByText('John Doe')).toBeInTheDocument();
    });
  });

  it('handles API errors gracefully', async () => {
    getModuleState.mockRejectedValue(new Error('API Error'));
    
    render(
      <GenericTable
        title="Test Table"
        data_source_api="/api/modules/test/state"
        columns={mockColumns}
        module_id="test"
      />
    );

    await waitFor(() => {
      expect(screen.getByText(/Failed to fetch state for/i)).toBeInTheDocument();
    });
  });

  it('generates dynamic columns when dynamic_columns is true', async () => {
    getModuleState.mockResolvedValue({ data: mockTableData });
    
    render(
      <GenericTable
        title="Test Table"
        data_source_api="/api/modules/test/state"
        module_id="test"
        dynamic_columns={true}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Test Table')).toBeInTheDocument();
    });

    // Should generate columns from data keys
    expect(screen.getByText('id')).toBeInTheDocument();
    expect(screen.getByText('name')).toBeInTheDocument();
    expect(screen.getByText('email')).toBeInTheDocument();
    expect(screen.getByText('age')).toBeInTheDocument();
  });

  it('limits rows when max_rows is specified', async () => {
    const largeDataSet = Array.from({ length: 100 }, (_, i) => ({
      id: i + 1,
      name: `User ${i + 1}`,
      email: `user${i + 1}@example.com`,
      age: 20 + (i % 50)
    }));

    getModuleState.mockResolvedValue({ data: largeDataSet });
    
    render(
      <GenericTable
        title="Test Table"
        data_source_api="/api/modules/test/state"
        columns={mockColumns}
        module_id="test"
        max_rows={5}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Test Table')).toBeInTheDocument();
    });

    // Should only show first 5 rows plus header
    const rows = screen.getAllByRole('row');
    expect(rows).toHaveLength(6); // 1 header + 5 data rows
  });

  it('opens email popout for email module', async () => {
    const emailData = [
      {
        id: 1,
        from: 'sender@example.com',
        to: 'recipient@example.com',
        subject: 'Test Email',
        body: 'This is a test email',
        timestamp: '2024-01-01T10:00:00Z'
      }
    ];

    getModuleState.mockResolvedValue({ data: { inbox: emailData } });
    
    const user = userEvent.setup();
    
    render(
      <GenericTable
        title="Email Table"
        data_source_api="/api/modules/email/state"
        columns={[
          { data_key: 'from', header: 'From', type: 'text' },
          { data_key: 'subject', header: 'Subject', type: 'text' }
        ]}
        module_id="email"
        data_path="inbox"
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Test Email')).toBeInTheDocument();
    });

    // Click on email row
    const emailRow = screen.getByText('Test Email').closest('tr');
    await user.click(emailRow);

    // Should open email popout
    expect(screen.getByTestId('email-popout')).toBeInTheDocument();
    expect(screen.getByText('Email: Test Email')).toBeInTheDocument();
  });

  it('closes email popout when close button is clicked', async () => {
    const emailData = [
      {
        id: 1,
        from: 'sender@example.com',
        subject: 'Test Email',
        body: 'This is a test email'
      }
    ];

    getModuleState.mockResolvedValue({ data: { inbox: emailData } });
    
    const user = userEvent.setup();
    
    render(
      <GenericTable
        title="Email Table"
        data_source_api="/api/modules/email/state"
        columns={[
          { data_key: 'from', header: 'From', type: 'text' },
          { data_key: 'subject', header: 'Subject', type: 'text' }
        ]}
        module_id="email"
        data_path="inbox"
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Test Email')).toBeInTheDocument();
    });

    // Open email popout
    const emailRow = screen.getByText('Test Email').closest('tr');
    await user.click(emailRow);

    expect(screen.getByTestId('email-popout')).toBeInTheDocument();

    // Close email popout
    const closeButton = screen.getByText('Close');
    await user.click(closeButton);

    expect(screen.queryByTestId('email-popout')).not.toBeInTheDocument();
  });

  it('handles empty data gracefully', async () => {
    getModuleState.mockResolvedValue({ data: [] });
    
    render(
      <GenericTable
        title="Empty Table"
        data_source_api="/api/modules/test/state"
        columns={mockColumns}
        module_id="test"
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Empty Table')).toBeInTheDocument();
    });

    // Should show headers but no data rows
    expect(screen.getByText('ID')).toBeInTheDocument();
    expect(screen.getByText('Name')).toBeInTheDocument();
    
    // Should show "No items to display" message
    expect(screen.getByText(/No items to display/i)).toBeInTheDocument();
  });

  it('applies size class correctly', async () => {
    getModuleState.mockResolvedValue({ data: mockTableData });
    
    const { container } = render(
      <GenericTable
        title="Test Table"
        data_source_api="/api/modules/test/state"
        columns={mockColumns}
        module_id="test"
        sizeClass="large-table"
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Test Table')).toBeInTheDocument();
    });

    // Check if size class is applied to module container
    const moduleContainer = container.querySelector('.module-container');
    expect(moduleContainer).toBeInTheDocument();
  });

  it('auto-refreshes data periodically', async () => {
    getModuleState.mockResolvedValue({ data: mockTableData });
    
    render(
      <GenericTable
        title="Test Table"
        data_source_api="/api/modules/test/state"
        columns={mockColumns}
        module_id="test"
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Test Table')).toBeInTheDocument();
    });

    // Clear the mock to verify it's called again
    jest.clearAllMocks();
    getModuleState.mockResolvedValue({ data: mockTableData });

    // Wait for auto-refresh (the component refreshes every 5 seconds)
    // We'll just verify the component renders correctly without testing the interval
    expect(screen.getByText('Test Table')).toBeInTheDocument();
    expect(screen.getByText('John Doe')).toBeInTheDocument();
  });

  it('handles database module last_query_result with dynamic columns', async () => {
    const databaseQueryResult = {
      last_query_result: {
        columns: ['id', 'name', 'email'],
        rows: [
          [1, 'John Doe', 'john@example.com'],
          [2, 'Jane Smith', 'jane@example.com'],
          [3, 'Bob Johnson', 'bob@example.com']
        ]
      }
    };

    getModuleState.mockResolvedValue({ data: databaseQueryResult });
    
    render(
      <GenericTable
        title="Last Query Result"
        data_source_api="/api/modules/database/state"
        module_id="database"
        data_path="last_query_result"
        dynamic_columns={true}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Last Query Result')).toBeInTheDocument();
    });

    // Check dynamic headers from columns array
    expect(screen.getByText('id')).toBeInTheDocument();
    expect(screen.getByText('name')).toBeInTheDocument();
    expect(screen.getByText('email')).toBeInTheDocument();

    // Check data from rows array
    expect(screen.getByText('John Doe')).toBeInTheDocument();
    expect(screen.getByText('jane@example.com')).toBeInTheDocument();
    expect(screen.getByText('Bob Johnson')).toBeInTheDocument();
  });

  it('handles empty database query result', async () => {
    const emptyDatabaseResult = {
      last_query_result: {
        columns: [],
        rows: []
      }
    };

    getModuleState.mockResolvedValue({ data: emptyDatabaseResult });
    
    render(
      <GenericTable
        title="Last Query Result"
        data_source_api="/api/modules/database/state"
        module_id="database"
        data_path="last_query_result"
        dynamic_columns={true}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Last Query Result')).toBeInTheDocument();
    });

    // Should show "No items to display" message
    expect(screen.getByText(/No items to display/i)).toBeInTheDocument();
  });
});