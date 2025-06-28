import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ContentPackPreview from './ContentPackPreview';
import * as apiClient from '../api/client';

// Mock the API client
jest.mock('../api/client');

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
    filename: 'test-pack.json',
    isOpen: true,
    onClose: jest.fn(),
    onLoad: jest.fn()
  };

  beforeEach(() => {
    jest.clearAllMocks();
    
    // Mock the API response
    const mockApiResponse = {
      data: {
        validation: {
          is_valid: true,
          errors: [],
          warnings: []
        },
        preview: {
          metadata: {
            name: 'Test Content Pack',
            version: '1.0.0',
            detailed_description: 'A test content pack for testing purposes',
            author_name: 'Test Author',
            created_at: '2024-01-01T00:00:00Z',
            updated_at: '2024-01-02T00:00:00Z',
            tags: ['test', 'example']
          }
        }
      }
    };
    
    apiClient.previewContentPack.mockResolvedValue(mockApiResponse);
  });

  describe('Basic Rendering', () => {
    it('renders content pack information correctly', async () => {
      render(<ContentPackPreview {...defaultProps} />);
      
      // Wait for the API call to complete and data to render
      await waitFor(() => {
        expect(screen.getByText('Test Content Pack')).toBeInTheDocument();
      });
      
      expect(screen.getByText('1.0.0')).toBeInTheDocument();
      expect(screen.getByText('A test content pack for testing purposes')).toBeInTheDocument();
      expect(screen.getByText('Test Author')).toBeInTheDocument();
    });

    it('displays content pack metadata', async () => {
      render(<ContentPackPreview {...defaultProps} />);
      
      // Wait for the API call to complete and metadata to render
      await waitFor(() => {
        expect(screen.getByText('Metadata')).toBeInTheDocument();
      });
      
      expect(screen.getByText('Name:')).toBeInTheDocument();
      expect(screen.getByText('Version:')).toBeInTheDocument();
      expect(screen.getByText('Author:')).toBeInTheDocument();
      expect(screen.getByText('Description:')).toBeInTheDocument();
    });

    it('displays validation status', async () => {
      render(<ContentPackPreview {...defaultProps} />);
      
      // Wait for the API call to complete and validation status to render
      await waitFor(() => {
        expect(screen.getByText('Validation Status')).toBeInTheDocument();
      });
      
      expect(screen.getByText('✓ Valid')).toBeInTheDocument();
    });

    it('displays modal header with filename', async () => {
      render(<ContentPackPreview {...defaultProps} />);
      
      expect(screen.getByText('Content Pack Preview: test-pack.json')).toBeInTheDocument();
      expect(screen.getByText('×')).toBeInTheDocument(); // Close button
    });
  });

  describe('Load Actions', () => {
    it('shows load button when content pack is valid', async () => {
      render(<ContentPackPreview {...defaultProps} />);
      
      // Wait for the API call to complete and load button to appear
      await waitFor(() => {
        expect(screen.getByText('Load Content Pack')).toBeInTheDocument();
      });
    });

    it('does not show load button when content pack is invalid', async () => {
      // Mock invalid content pack
      const invalidResponse = {
        data: {
          validation: {
            is_valid: false,
            errors: ['Invalid format'],
            warnings: []
          },
          preview: {}
        }
      };
      apiClient.previewContentPack.mockResolvedValue(invalidResponse);
      
      render(<ContentPackPreview {...defaultProps} />);
      
      // Wait for the API call to complete
      await waitFor(() => {
        expect(screen.getByText('✗ Invalid')).toBeInTheDocument();
      });
      
      expect(screen.queryByText('Load Content Pack')).not.toBeInTheDocument();
    });

    it('shows loading state when fetching preview', async () => {
      // Mock a delayed API response
      apiClient.previewContentPack.mockImplementation(() => 
        new Promise(resolve => setTimeout(() => resolve({
          data: { validation: { is_valid: true }, preview: {} }
        }), 100))
      );
      
      render(<ContentPackPreview {...defaultProps} />);
      
      expect(screen.getByText('Loading preview...')).toBeInTheDocument();
    });

    it('calls onLoad when load button is clicked', async () => {
      const user = userEvent.setup();
      render(<ContentPackPreview {...defaultProps} />);
      
      // Wait for the load button to appear
      await waitFor(() => {
        expect(screen.getByText('Load Content Pack')).toBeInTheDocument();
      });
      
      const loadButton = screen.getByText('Load Content Pack');
      await user.click(loadButton);
      
      expect(defaultProps.onLoad).toHaveBeenCalledWith('test-pack.json');
      expect(defaultProps.onClose).toHaveBeenCalled();
    });

    it('calls onClose when close button is clicked', async () => {
      const user = userEvent.setup();
      render(<ContentPackPreview {...defaultProps} />);
      
      const closeButton = screen.getByText('×');
      await user.click(closeButton);
      
      expect(defaultProps.onClose).toHaveBeenCalled();
    });

  });

  describe('Error Handling', () => {
    it('displays error message when API call fails', async () => {
      const errorMessage = 'Failed to load preview';
      apiClient.previewContentPack.mockRejectedValue(new Error(errorMessage));
      
      render(<ContentPackPreview {...defaultProps} />);
      
      await waitFor(() => {
        expect(screen.getByText(/Error loading preview/)).toBeInTheDocument();
      });
      
      expect(screen.getByText('Retry')).toBeInTheDocument();
    });

    it('retries API call when retry button is clicked', async () => {
      const user = userEvent.setup();
      apiClient.previewContentPack.mockRejectedValueOnce(new Error('Network error'));
      
      render(<ContentPackPreview {...defaultProps} />);
      
      // Wait for error to appear
      await waitFor(() => {
        expect(screen.getByText('Retry')).toBeInTheDocument();
      });
      
      const retryButton = screen.getByText('Retry');
      await user.click(retryButton);
      
      expect(apiClient.previewContentPack).toHaveBeenCalledTimes(2);
    });
  });

  describe('Modal Behavior', () => {
    it('does not render when isOpen is false', () => {
      render(<ContentPackPreview {...defaultProps} isOpen={false} />);
      
      expect(screen.queryByText('Content Pack Preview:')).not.toBeInTheDocument();
    });

    it('calls API when component opens', () => {
      render(<ContentPackPreview {...defaultProps} />);
      
      expect(apiClient.previewContentPack).toHaveBeenCalledWith('test-pack.json');
    });
  });
});
