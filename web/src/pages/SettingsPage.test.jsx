import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import SettingsPage from './SettingsPage';
import { getModulesStatus, toggleModule } from '../api/client';

// Mock the API client
jest.mock('../api/client');

// Mock window.history.back
const mockHistoryBack = jest.fn();
Object.defineProperty(window, 'history', {
  value: { back: mockHistoryBack },
  writable: true
});

describe('SettingsPage', () => {
  const mockModulesData = {
    filesystem: {
      display_name: 'File System',
      description: 'File system operations',
      is_enabled: true,
      is_loaded: true
    },
    database: {
      display_name: 'Database',
      description: 'Database operations',
      is_enabled: false,
      is_loaded: false
    },
    email: {
      display_name: 'Email',
      description: 'Email operations',
      is_enabled: true,
      is_loaded: true
    }
  };

  beforeEach(() => {
    jest.clearAllMocks();
    getModulesStatus.mockResolvedValue({ data: { modules: mockModulesData } });
    toggleModule.mockResolvedValue({ success: true });
  });

  describe('Initial Loading', () => {
    it('renders loading state initially', () => {
      render(<SettingsPage />);
      
      expect(screen.getByText('Settings')).toBeInTheDocument();
      expect(screen.getByText('Loading settings...')).toBeInTheDocument();
    });

    it('loads modules status on mount', async () => {
      render(<SettingsPage />);
      
      await waitFor(() => {
        expect(getModulesStatus).toHaveBeenCalledTimes(1);
      });
    });
  });

  describe('Modules Display', () => {
    it('renders modules list after loading', async () => {
      render(<SettingsPage />);
      
      await waitFor(() => {
        expect(screen.getByText('File System')).toBeInTheDocument();
        expect(screen.getByText('Database')).toBeInTheDocument();
        expect(screen.getByText('Email')).toBeInTheDocument();
      });

      expect(screen.getByText('File system operations')).toBeInTheDocument();
      expect(screen.getByText('Database operations')).toBeInTheDocument();
      expect(screen.getByText('Email operations')).toBeInTheDocument();
    });

    it('shows correct module status indicators', async () => {
      render(<SettingsPage />);
      
      await waitFor(() => {
        const loadedIndicators = screen.getAllByText('Loaded');
        const unloadedIndicators = screen.getAllByText('Unloaded');
        
        expect(loadedIndicators).toHaveLength(2); // filesystem and email
        expect(unloadedIndicators).toHaveLength(1); // database
      });
    });

    it('shows correct toggle states', async () => {
      render(<SettingsPage />);
      
      await waitFor(() => {
        const toggles = screen.getAllByRole('checkbox');
        
        expect(toggles[0]).toBeChecked(); // filesystem enabled
        expect(toggles[1]).not.toBeChecked(); // database disabled
        expect(toggles[2]).toBeChecked(); // email enabled
      });
    });

    it('displays no modules message when modules list is empty', async () => {
      getModulesStatus.mockResolvedValue({ data: { modules: {} } });
      
      render(<SettingsPage />);
      
      await waitFor(() => {
        expect(screen.getByText('No modules found.')).toBeInTheDocument();
      });
    });
  });

  describe('Module Toggle Functionality', () => {
    it('toggles module when checkbox is clicked', async () => {
      const user = userEvent.setup();
      render(<SettingsPage />);
      
      await waitFor(() => {
        expect(screen.getByText('File System')).toBeInTheDocument();
      });

      const filesystemToggle = screen.getAllByRole('checkbox')[0];
      await user.click(filesystemToggle);
      
      expect(toggleModule).toHaveBeenCalledWith('filesystem', false);
    });

    it('shows loading state during toggle operation', async () => {
      const user = userEvent.setup();
      
      // Make toggleModule return a pending promise
      let resolveToggle;
      toggleModule.mockReturnValue(new Promise(resolve => {
        resolveToggle = resolve;
      }));
      
      render(<SettingsPage />);
      
      await waitFor(() => {
        expect(screen.getByText('File System')).toBeInTheDocument();
      });

      const filesystemToggle = screen.getAllByRole('checkbox')[0];
      await user.click(filesystemToggle);
      
      expect(screen.getByText('Updating...')).toBeInTheDocument();
      expect(filesystemToggle).toBeDisabled();
      
      // Resolve the toggle operation
      resolveToggle({ success: true });
      
      await waitFor(() => {
        expect(screen.queryByText('Updating...')).not.toBeInTheDocument();
      });
    });

    it('updates module state after successful toggle', async () => {
      const user = userEvent.setup();
      render(<SettingsPage />);
      
      await waitFor(() => {
        expect(screen.getByText('Database')).toBeInTheDocument();
      });

      const databaseToggle = screen.getAllByRole('checkbox')[1]; // database is disabled
      expect(databaseToggle).not.toBeChecked();
      
      await user.click(databaseToggle);
      
      await waitFor(() => {
        expect(databaseToggle).toBeChecked();
      });
    });

    it('handles toggle error gracefully', async () => {
      const user = userEvent.setup();
      toggleModule.mockRejectedValue(new Error('Toggle failed'));
      
      render(<SettingsPage />);
      
      await waitFor(() => {
        expect(screen.getByText('File System')).toBeInTheDocument();
      });

      const filesystemToggle = screen.getAllByRole('checkbox')[0];
      await user.click(filesystemToggle);
      
      await waitFor(() => {
        expect(screen.getByText('Failed to disable module filesystem')).toBeInTheDocument();
      });
    });
  });

  describe('Error Handling', () => {
    it('displays error message when modules loading fails', async () => {
      getModulesStatus.mockRejectedValue(new Error('API Error'));
      
      render(<SettingsPage />);
      
      await waitFor(() => {
        expect(screen.getByText('Failed to load modules status')).toBeInTheDocument();
      });
    });

    it('clears error message after successful operation', async () => {
      const user = userEvent.setup();
      
      // First, cause an error
      getModulesStatus.mockRejectedValue(new Error('API Error'));
      render(<SettingsPage />);
      
      await waitFor(() => {
        expect(screen.getByText('Failed to load modules status')).toBeInTheDocument();
      });
      
      // Then fix the API and refresh
      getModulesStatus.mockResolvedValue({ data: { modules: mockModulesData } });
      
      const refreshButton = screen.getByText('Refresh Status');
      await user.click(refreshButton);
      
      await waitFor(() => {
        expect(screen.queryByText('Failed to load modules status')).not.toBeInTheDocument();
        expect(screen.getByText('File System')).toBeInTheDocument();
      });
    });
  });

  describe('Navigation and Actions', () => {
    it('navigates back when cancel button is clicked', async () => {
      const user = userEvent.setup();
      render(<SettingsPage />);
      
      await waitFor(() => {
        expect(screen.getByText('Back to Dashboard')).toBeInTheDocument();
      });

      const backButton = screen.getByText('Back to Dashboard');
      await user.click(backButton);
      
      expect(mockHistoryBack).toHaveBeenCalledTimes(1);
    });

    it('refreshes modules status when refresh button is clicked', async () => {
      const user = userEvent.setup();
      render(<SettingsPage />);
      
      await waitFor(() => {
        expect(getModulesStatus).toHaveBeenCalledTimes(1);
      });

      const refreshButton = screen.getByText('Refresh Status');
      await user.click(refreshButton);
      
      expect(getModulesStatus).toHaveBeenCalledTimes(2);
    });

    it('disables refresh button during loading', async () => {
      const user = userEvent.setup();
      
      // Make getModulesStatus return a pending promise
      let resolveModules;
      getModulesStatus.mockReturnValue(new Promise(resolve => {
        resolveModules = resolve;
      }));
      
      render(<SettingsPage />);
      
      const refreshButton = screen.getByText('Refresh Status');
      expect(refreshButton).toBeDisabled();
      
      // Resolve the loading
      resolveModules({ data: { modules: mockModulesData } });
      
      await waitFor(() => {
        expect(refreshButton).not.toBeDisabled();
      });
    });
  });

  describe('UI Elements', () => {
    it('renders all required sections', async () => {
      render(<SettingsPage />);
      
      await waitFor(() => {
        expect(screen.getByText('Module Configuration')).toBeInTheDocument();
        expect(screen.getByText('Future Tool-Level Configuration')).toBeInTheDocument();
      });

      expect(screen.getByText('Enable or disable modules to control which tools are available in the system.')).toBeInTheDocument();
      expect(screen.getByText(/In the next release, you'll be able to enable\/disable individual tools/)).toBeInTheDocument();
    });

    it('applies correct CSS classes for module status', async () => {
      render(<SettingsPage />);
      
      await waitFor(() => {
        const loadedIndicators = screen.getAllByText('Loaded');
        const unloadedIndicators = screen.getAllByText('Unloaded');
        
        loadedIndicators.forEach(indicator => {
          expect(indicator).toHaveClass('status-indicator', 'loaded');
        });
        
        unloadedIndicators.forEach(indicator => {
          expect(indicator).toHaveClass('status-indicator', 'unloaded');
        });
      });
    });
  });

  describe('Accessibility', () => {
    it('has proper heading structure', async () => {
      render(<SettingsPage />);
      
      await waitFor(() => {
        expect(screen.getByRole('heading', { level: 1, name: 'Settings' })).toBeInTheDocument();
        expect(screen.getByRole('heading', { level: 2, name: 'Module Configuration' })).toBeInTheDocument();
        expect(screen.getByRole('heading', { level: 2, name: 'Future Tool-Level Configuration' })).toBeInTheDocument();
      });
    });

    it('has accessible form controls', async () => {
      render(<SettingsPage />);
      
      await waitFor(() => {
        const toggles = screen.getAllByRole('checkbox');
        toggles.forEach(toggle => {
          expect(toggle).toBeInTheDocument();
        });
      });

      const buttons = screen.getAllByRole('button');
      expect(buttons.length).toBeGreaterThan(0);
    });
  });
});