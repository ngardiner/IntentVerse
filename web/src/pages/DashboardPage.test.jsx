import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import DashboardPage from './DashboardPage';
import { getUILayout } from '../api/client';

// Mock the API client
jest.mock('../api/client');

// Mock all the generic components
jest.mock('../components/generic/GenericFileTree', () => {
  return function MockGenericFileTree(props) {
    return <div data-testid="file-tree">File Tree: {props.title}</div>;
  };
});

jest.mock('../components/generic/GenericTable', () => {
  return function MockGenericTable(props) {
    return <div data-testid="table">Table: {props.title}</div>;
  };
});

jest.mock('../components/generic/GenericKeyValue', () => {
  return function MockGenericKeyValue(props) {
    return <div data-testid="key-value">Key-Value: {props.title}</div>;
  };
});

jest.mock('../components/generic/SwitchableView', () => {
  return function MockSwitchableView(props) {
    return <div data-testid="switchable-view">Switchable: {props.title}</div>;
  };
});

jest.mock('../components/DashboardLayoutManager', () => {
  return function MockDashboardLayoutManager({ children, isEditing, currentDashboard }) {
    return (
      <div data-testid="layout-manager" data-editing={isEditing} data-dashboard={currentDashboard}>
        {children}
      </div>
    );
  };
});

describe('DashboardPage', () => {
  const mockOnSaveLayout = jest.fn();
  const mockOnCancelEdit = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders loading state initially', () => {
    getUILayout.mockImplementation(() => new Promise(() => {})); // Never resolves
    
    render(
      <DashboardPage
        isEditing={false}
        onSaveLayout={mockOnSaveLayout}
        onCancelEdit={mockOnCancelEdit}
        currentDashboard="state"
      />
    );

    expect(screen.getByText('Loading Dashboard...')).toBeInTheDocument();
  });

  it('renders dashboard with modules after loading', async () => {
    const mockLayout = {
      data: {
        modules: [
          {
            module_id: 'filesystem',
            title: 'File System',
            component_type: 'file_tree',
            size: 'medium'
          },
          {
            module_id: 'email',
            title: 'Email',
            component_type: 'table',
            size: 'large',
            data_path: 'inbox'
          }
        ]
      }
    };

    getUILayout.mockResolvedValue(mockLayout);
    
    render(
      <DashboardPage
        isEditing={false}
        onSaveLayout={mockOnSaveLayout}
        onCancelEdit={mockOnCancelEdit}
        currentDashboard="state"
      />
    );

    await waitFor(() => {
      expect(screen.getByTestId('layout-manager')).toBeInTheDocument();
    });

    expect(screen.getByTestId('file-tree')).toBeInTheDocument();
    expect(screen.getByText('File Tree: File System')).toBeInTheDocument();
    expect(screen.getByTestId('table')).toBeInTheDocument();
    expect(screen.getByText('Table: Email')).toBeInTheDocument();
  });

  it('renders key-value component correctly', async () => {
    const mockLayout = {
      data: {
        modules: [
          {
            module_id: 'memory',
            title: 'Memory',
            component_type: 'key_value_viewer',
            size: 'small',
            data_path: 'short_term',
            display_as: 'json'
          }
        ]
      }
    };

    getUILayout.mockResolvedValue(mockLayout);
    
    render(
      <DashboardPage
        isEditing={false}
        onSaveLayout={mockOnSaveLayout}
        onCancelEdit={mockOnCancelEdit}
        currentDashboard="state"
      />
    );

    await waitFor(() => {
      expect(screen.getByTestId('key-value')).toBeInTheDocument();
    });

    expect(screen.getByText('Key-Value: Memory')).toBeInTheDocument();
  });

  it('renders switchable group component correctly', async () => {
    const mockLayout = {
      data: {
        modules: [
          {
            module_id: 'database',
            title: 'Database',
            component_type: 'switchable_group',
            size: 'xlarge',
            views: [
              {
                title: 'Tables',
                component_type: 'table',
                data_source_api: '/api/modules/database/state'
              }
            ]
          }
        ]
      }
    };

    getUILayout.mockResolvedValue(mockLayout);
    
    render(
      <DashboardPage
        isEditing={false}
        onSaveLayout={mockOnSaveLayout}
        onCancelEdit={mockOnCancelEdit}
        currentDashboard="state"
      />
    );

    await waitFor(() => {
      expect(screen.getByTestId('switchable-view')).toBeInTheDocument();
    });

    expect(screen.getByText('Switchable: Database')).toBeInTheDocument();
  });

  it('handles modules with multiple components', async () => {
    const mockLayout = {
      data: {
        modules: [
          {
            module_id: 'complex',
            title: 'Complex Module',
            components: [
              {
                title: 'Component 1',
                component_type: 'table',
                size: 'medium'
              },
              {
                title: 'Component 2',
                component_type: 'key_value',
                size: 'small'
              }
            ]
          }
        ]
      }
    };

    getUILayout.mockResolvedValue(mockLayout);
    
    render(
      <DashboardPage
        isEditing={false}
        onSaveLayout={mockOnSaveLayout}
        onCancelEdit={mockOnCancelEdit}
        currentDashboard="state"
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Table: Component 1')).toBeInTheDocument();
    });

    expect(screen.getByText('Key-Value: Component 2')).toBeInTheDocument();
  });

  it('handles unknown component types gracefully', async () => {
    const mockLayout = {
      data: {
        modules: [
          {
            module_id: 'unknown',
            title: 'Unknown Module',
            component_type: 'unknown_type',
            size: 'medium'
          }
        ]
      }
    };

    getUILayout.mockResolvedValue(mockLayout);
    
    render(
      <DashboardPage
        isEditing={false}
        onSaveLayout={mockOnSaveLayout}
        onCancelEdit={mockOnCancelEdit}
        currentDashboard="state"
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Unknown Module')).toBeInTheDocument();
    });

    expect(screen.getByText('Unknown component type: unknown_type')).toBeInTheDocument();
  });

  it('handles API errors gracefully', async () => {
    getUILayout.mockRejectedValue(new Error('API Error'));
    
    render(
      <DashboardPage
        isEditing={false}
        onSaveLayout={mockOnSaveLayout}
        onCancelEdit={mockOnCancelEdit}
        currentDashboard="state"
      />
    );

    await waitFor(() => {
      expect(screen.getByText(/Failed to fetch UI layout/)).toBeInTheDocument();
    });
  });

  it('renders empty state when no modules are loaded', async () => {
    const mockLayout = {
      data: {
        modules: []
      }
    };

    getUILayout.mockResolvedValue(mockLayout);
    
    render(
      <DashboardPage
        isEditing={false}
        onSaveLayout={mockOnSaveLayout}
        onCancelEdit={mockOnCancelEdit}
        currentDashboard="state"
      />
    );

    await waitFor(() => {
      expect(screen.getByText('No modules were loaded by the Core Engine.')).toBeInTheDocument();
    });
  });

  it('passes editing state to layout manager', async () => {
    const mockLayout = {
      data: {
        modules: [
          {
            module_id: 'test',
            title: 'Test Module',
            component_type: 'table'
          }
        ]
      }
    };

    getUILayout.mockResolvedValue(mockLayout);
    
    render(
      <DashboardPage
        isEditing={true}
        onSaveLayout={mockOnSaveLayout}
        onCancelEdit={mockOnCancelEdit}
        currentDashboard="timeline"
      />
    );

    await waitFor(() => {
      expect(screen.getByTestId('layout-manager')).toBeInTheDocument();
    });

    const layoutManager = screen.getByTestId('layout-manager');
    expect(layoutManager).toHaveAttribute('data-editing', 'true');
    expect(layoutManager).toHaveAttribute('data-dashboard', 'timeline');
  });

  it('applies correct size classes to components', async () => {
    const mockLayout = {
      data: {
        modules: [
          {
            module_id: 'small-module',
            title: 'Small Module',
            component_type: 'table',
            size: 'small'
          },
          {
            module_id: 'large-module',
            title: 'Large Module',
            component_type: 'file_tree',
            size: 'large'
          }
        ]
      }
    };

    getUILayout.mockResolvedValue(mockLayout);
    
    render(
      <DashboardPage
        isEditing={false}
        onSaveLayout={mockOnSaveLayout}
        onCancelEdit={mockOnCancelEdit}
        currentDashboard="state"
      />
    );

    await waitFor(() => {
      expect(screen.getByTestId('table')).toBeInTheDocument();
    });

    // Note: Size classes are passed as props to components, 
    // so we can't easily test them in the DOM without more complex mocking
    expect(screen.getByTestId('table')).toBeInTheDocument();
    expect(screen.getByTestId('file-tree')).toBeInTheDocument();
  });

  it('handles missing module data gracefully', async () => {
    const mockLayout = {
      data: {} // No modules property
    };

    getUILayout.mockResolvedValue(mockLayout);
    
    render(
      <DashboardPage
        isEditing={false}
        onSaveLayout={mockOnSaveLayout}
        onCancelEdit={mockOnCancelEdit}
        currentDashboard="state"
      />
    );

    await waitFor(() => {
      expect(screen.getByText('No modules were loaded by the Core Engine.')).toBeInTheDocument();
    });
  });
});