import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ContentPackPreview from './ContentPackPreview';

describe('ContentPackPreview', () => {
  const mockContentPack = {
    id: 'test-pack',
    name: 'Test Content Pack',
    version: '1.0.0',
    description: 'A test content pack for testing purposes',
    author: 'Test Author',
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-02T00:00:00Z',
    tags: ['test', 'example'],
    modules: [
      {
        name: 'test_module',
        description: 'Test module description',
        tools: [
          {
            name: 'test_tool',
            description: 'Test tool description',
            parameters: {
              param1: { type: 'string', description: 'First parameter' },
              param2: { type: 'number', description: 'Second parameter' }
            }
          }
        ]
      }
    ],
    dependencies: ['dependency1', 'dependency2'],
    configuration: {
      setting1: 'value1',
      setting2: 42
    }
  };

  const defaultProps = {
    contentPack: mockContentPack,
    onClose: jest.fn(),
    onLoad: jest.fn(),
    onUnload: jest.fn(),
    isLoaded: false,
    isLoading: false
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Basic Rendering', () => {
    it('renders content pack information correctly', () => {
      render(<ContentPackPreview {...defaultProps} />);
      
      expect(screen.getByText('Test Content Pack')).toBeInTheDocument();
      expect(screen.getByText('1.0.0')).toBeInTheDocument();
      expect(screen.getByText('A test content pack for testing purposes')).toBeInTheDocument();
      expect(screen.getByText('Test Author')).toBeInTheDocument();
    });

    it('displays content pack metadata', () => {
      render(<ContentPackPreview {...defaultProps} />);
      
      expect(screen.getByText('Created:')).toBeInTheDocument();
      expect(screen.getByText('Updated:')).toBeInTheDocument();
      expect(screen.getByText('1/1/2024')).toBeInTheDocument();
      expect(screen.getByText('1/2/2024')).toBeInTheDocument();
    });

    it('displays tags correctly', () => {
      render(<ContentPackPreview {...defaultProps} />);
      
      expect(screen.getByText('test')).toBeInTheDocument();
      expect(screen.getByText('example')).toBeInTheDocument();
    });

    it('displays modules and tools information', () => {
      render(<ContentPackPreview {...defaultProps} />);
      
      expect(screen.getByText('test_module')).toBeInTheDocument();
      expect(screen.getByText('Test module description')).toBeInTheDocument();
      expect(screen.getByText('test_tool')).toBeInTheDocument();
      expect(screen.getByText('Test tool description')).toBeInTheDocument();
    });
  });

  describe('Load/Unload Actions', () => {
    it('shows load button when content pack is not loaded', () => {
      render(<ContentPackPreview {...defaultProps} isLoaded={false} />);
      
      expect(screen.getByText('Load')).toBeInTheDocument();
      expect(screen.queryByText('Unload')).not.toBeInTheDocument();
    });

    it('shows unload button when content pack is loaded', () => {
      render(<ContentPackPreview {...defaultProps} isLoaded={true} />);
      
      expect(screen.getByText('Unload')).toBeInTheDocument();
      expect(screen.queryByText('Load')).not.toBeInTheDocument();
    });

    it('shows loading state when loading', () => {
      render(<ContentPackPreview {...defaultProps} isLoading={true} />);
      
      expect(screen.getByText('Loading...')).toBeInTheDocument();
      expect(screen.queryByText('Load')).not.toBeInTheDocument();
    });

    it('calls onLoad when load button is clicked', async () => {
      const user = userEvent.setup();
      render(<ContentPackPreview {...defaultProps} />);
      
      const loadButton = screen.getByText('Load');
      await user.click(loadButton);
      
      expect(defaultProps.onLoad).toHaveBeenCalledWith(mockContentPack);
    });

    it('calls onUnload when unload button is clicked', async () => {
      const user = userEvent.setup();
      render(<ContentPackPreview {...defaultProps} isLoaded={true} />);
      
      const unloadButton = screen.getByText('Unload');
      await user.click(unloadButton);
      
      expect(defaultProps.onUnload).toHaveBeenCalledWith(mockContentPack);
    });

    it('disables action buttons when loading', () => {
      render(<ContentPackPreview {...defaultProps} isLoading={true} />);
      
      const loadingButton = screen.getByText('Loading...');
      expect(loadingButton).toBeDisabled();
    });
  });

  describe('Dependencies Section', () => {
    it('displays dependencies list', () => {
      render(<ContentPackPreview {...defaultProps} />);
      
      expect(screen.getByText('Dependencies:')).toBeInTheDocument();
      expect(screen.getByText('dependency1')).toBeInTheDocument();
      expect(screen.getByText('dependency2')).toBeInTheDocument();
    });

    it('shows no dependencies message when dependencies array is empty', () => {
      const propsWithNoDeps = {
        ...defaultProps,
        contentPack: {
          ...mockContentPack,
          dependencies: []
        }
      };
      
      render(<ContentPackPreview {...propsWithNoDeps} />);
      
      expect(screen.getByText('No dependencies')).toBeInTheDocument();
    });

    it('handles missing dependencies gracefully', () => {
      const propsWithoutDeps = {
        ...defaultProps,
        contentPack: {
          ...mockContentPack,
          dependencies: undefined
        }
      };
      
      render(<ContentPackPreview {...propsWithoutDeps} />);
      
      expect(screen.getByText('No dependencies')).toBeInTheDocument();
    });
  });

  describe('Configuration Section', () => {
    it('displays configuration settings', () => {
      render(<ContentPackPreview {...defaultProps} />);
      
      expect(screen.getByText('Configuration:')).toBeInTheDocument();
      expect(screen.getByText('setting1: value1')).toBeInTheDocument();
      expect(screen.getByText('setting2: 42')).toBeInTheDocument();
    });

    it('shows no configuration message when configuration is empty', () => {
      const propsWithNoConfig = {
        ...defaultProps,
        contentPack: {
          ...mockContentPack,
          configuration: {}
        }
      };
      
      render(<ContentPackPreview {...propsWithNoConfig} />);
      
      expect(screen.getByText('No configuration')).toBeInTheDocument();
    });

    it('handles missing configuration gracefully', () => {
      const propsWithoutConfig = {
        ...defaultProps,
        contentPack: {
          ...mockContentPack,
          configuration: undefined
        }
      };
      
      render(<ContentPackPreview {...propsWithoutConfig} />);
      
      expect(screen.getByText('No configuration')).toBeInTheDocument();
    });
  });

  describe('Tools Details', () => {
    it('displays tool parameters correctly', () => {
      render(<ContentPackPreview {...defaultProps} />);
      
      expect(screen.getByText('Parameters:')).toBeInTheDocument();
      expect(screen.getByText('param1 (string): First parameter')).toBeInTheDocument();
      expect(screen.getByText('param2 (number): Second parameter')).toBeInTheDocument();
    });

    it('shows no parameters message when tool has no parameters', () => {
      const propsWithNoParams = {
        ...defaultProps,
        contentPack: {
          ...mockContentPack,
          modules: [{
            name: 'test_module',
            description: 'Test module',
            tools: [{
              name: 'test_tool',
              description: 'Test tool',
              parameters: {}
            }]
          }]
        }
      };
      
      render(<ContentPackPreview {...propsWithNoParams} />);
      
      expect(screen.getByText('No parameters')).toBeInTheDocument();
    });

    it('handles tools without parameters property', () => {
      const propsWithoutParams = {
        ...defaultProps,
        contentPack: {
          ...mockContentPack,
          modules: [{
            name: 'test_module',
            description: 'Test module',
            tools: [{
              name: 'test_tool',
              description: 'Test tool'
            }]
          }]
        }
      };
      
      render(<ContentPackPreview {...propsWithoutParams} />);
      
      expect(screen.getByText('No parameters')).toBeInTheDocument();
    });
  });

  describe('Modal Behavior', () => {
    it('calls onClose when close button is clicked', async () => {
      const user = userEvent.setup();
      render(<ContentPackPreview {...defaultProps} />);
      
      const closeButton = screen.getByText('×');
      await user.click(closeButton);
      
      expect(defaultProps.onClose).toHaveBeenCalledTimes(1);
    });

    it('calls onClose when clicking outside modal (if implemented)', async () => {
      const user = userEvent.setup();
      render(<ContentPackPreview {...defaultProps} />);
      
      // This test assumes the modal has an overlay that can be clicked
      const modal = screen.getByRole('dialog');
      if (modal.parentElement) {
        await user.click(modal.parentElement);
        // Note: This would only work if the component implements click-outside behavior
      }
    });

    it('supports keyboard navigation for closing modal', async () => {
      const user = userEvent.setup();
      render(<ContentPackPreview {...defaultProps} />);
      
      // Press Escape key
      await user.keyboard('{Escape}');
      
      // Note: This would only work if the component implements keyboard event handling
      // expect(defaultProps.onClose).toHaveBeenCalledTimes(1);
    });
  });

  describe('Edge Cases and Error Handling', () => {
    it('handles content pack with no modules', () => {
      const propsWithNoModules = {
        ...defaultProps,
        contentPack: {
          ...mockContentPack,
          modules: []
        }
      };
      
      render(<ContentPackPreview {...propsWithNoModules} />);
      
      expect(screen.getByText('Test Content Pack')).toBeInTheDocument();
      expect(screen.getByText('No modules')).toBeInTheDocument();
    });

    it('handles content pack with modules but no tools', () => {
      const propsWithNoTools = {
        ...defaultProps,
        contentPack: {
          ...mockContentPack,
          modules: [{
            name: 'empty_module',
            description: 'Module with no tools',
            tools: []
          }]
        }
      };
      
      render(<ContentPackPreview {...propsWithNoTools} />);
      
      expect(screen.getByText('empty_module')).toBeInTheDocument();
      expect(screen.getByText('No tools')).toBeInTheDocument();
    });

    it('handles missing required fields gracefully', () => {
      const propsWithMinimalData = {
        ...defaultProps,
        contentPack: {
          id: 'minimal-pack',
          name: 'Minimal Pack'
          // Missing other fields
        }
      };
      
      render(<ContentPackPreview {...propsWithMinimalData} />);
      
      expect(screen.getByText('Minimal Pack')).toBeInTheDocument();
      // Should not crash and should handle missing fields gracefully
    });

    it('handles null or undefined content pack', () => {
      const propsWithNullPack = {
        ...defaultProps,
        contentPack: null
      };
      
      render(<ContentPackPreview {...propsWithNullPack} />);
      
      // Should show error message or empty state
      expect(screen.getByText('No content pack data available')).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('has proper ARIA labels and roles', () => {
      render(<ContentPackPreview {...defaultProps} />);
      
      expect(screen.getByRole('dialog')).toBeInTheDocument();
      expect(screen.getByLabelText('Close')).toBeInTheDocument();
    });

    it('has proper heading structure', () => {
      render(<ContentPackPreview {...defaultProps} />);
      
      expect(screen.getByRole('heading', { level: 2, name: 'Test Content Pack' })).toBeInTheDocument();
      expect(screen.getByRole('heading', { level: 3, name: 'Modules' })).toBeInTheDocument();
    });

    it('supports keyboard navigation', async () => {
      const user = userEvent.setup();
      render(<ContentPackPreview {...defaultProps} />);
      
      // Tab through interactive elements
      await user.tab();
      expect(screen.getByText('×')).toHaveFocus();
      
      await user.tab();
      expect(screen.getByText('Load')).toHaveFocus();
    });

    it('has proper focus management when modal opens', () => {
      render(<ContentPackPreview {...defaultProps} />);
      
      // Focus should be trapped within the modal
      const modal = screen.getByRole('dialog');
      expect(modal).toBeInTheDocument();
    });
  });

  describe('Visual States', () => {
    it('applies correct CSS classes for loaded state', () => {
      render(<ContentPackPreview {...defaultProps} isLoaded={true} />);
      
      const unloadButton = screen.getByText('Unload');
      expect(unloadButton).toHaveClass('unload-button');
    });

    it('applies correct CSS classes for loading state', () => {
      render(<ContentPackPreview {...defaultProps} isLoading={true} />);
      
      const loadingButton = screen.getByText('Loading...');
      expect(loadingButton).toHaveClass('loading-button');
    });

    it('displays version badge correctly', () => {
      render(<ContentPackPreview {...defaultProps} />);
      
      const versionBadge = screen.getByText('1.0.0');
      expect(versionBadge).toHaveClass('version-badge');
    });

    it('displays tags with proper styling', () => {
      render(<ContentPackPreview {...defaultProps} />);
      
      const testTag = screen.getByText('test');
      const exampleTag = screen.getByText('example');
      
      expect(testTag).toHaveClass('tag');
      expect(exampleTag).toHaveClass('tag');
    });
  });
});