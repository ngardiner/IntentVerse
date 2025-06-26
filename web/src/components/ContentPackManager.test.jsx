import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ContentPackManager from './ContentPackManager';
import {
  getAvailableContentPacks,
  getLoadedContentPacks,
  exportContentPack,
  loadContentPack,
  unloadContentPack,
  clearAllLoadedPacks,
  getRemoteContentPacks,
  getRemoteRepositoryInfo
} from '../api/client';

// Mock the API client
jest.mock('../api/client');

// Mock the ContentPackPreview component
jest.mock('./ContentPackPreview', () => {
  return function MockContentPackPreview({ filename, onClose }) {
    return (
      <div data-testid="content-pack-preview">
        <div>Preview for {filename}</div>
        <button onClick={onClose}>Close Preview</button>
      </div>
    );
  };
});

describe('ContentPackManager', () => {
  const mockAvailablePacks = [
    {
      filename: 'test-pack.json',
      metadata: {
        name: 'Test Pack',
        summary: 'A test content pack',
        description: 'This is a test content pack for testing purposes',
        author: { name: 'Test Author', email: 'test@example.com' },
        version: '1.0.0',
        created: '2024-01-01T00:00:00Z'
      }
    }
  ];

  const mockLoadedPacks = [
    {
      filename: 'loaded-pack.json',
      metadata: {
        name: 'Loaded Pack',
        summary: 'A loaded content pack',
        description: 'This pack is currently loaded',
        author: { name: 'Loaded Author', email: 'loaded@example.com' },
        version: '1.0.0',
        created: '2024-01-01T00:00:00Z'
      }
    }
  ];

  const mockRemoteRepositoryInfo = {
    name: 'Test Repository',
    description: 'A test repository',
    url: 'https://github.com/test/repo',
    last_updated: '2024-01-01T00:00:00Z'
  };

  beforeEach(() => {
    jest.clearAllMocks();
    getAvailableContentPacks.mockResolvedValue({ data: mockAvailablePacks });
    getLoadedContentPacks.mockResolvedValue({ data: mockLoadedPacks });
    getRemoteContentPacks.mockResolvedValue({ data: [] });
    getRemoteRepositoryInfo.mockResolvedValue({ data: mockRemoteRepositoryInfo });
  });

  it('renders loading state initially', () => {
    render(<ContentPackManager />);
    
    expect(screen.getByText('Loading content packs...')).toBeInTheDocument();
  });

  it('renders available content packs after loading', async () => {
    render(<ContentPackManager />);

    await waitFor(() => {
      expect(screen.getByText('Test Pack')).toBeInTheDocument();
    });

    expect(screen.getByText('A test content pack')).toBeInTheDocument();
    expect(screen.getByText('Test Author')).toBeInTheDocument();
  });

  it('switches between tabs correctly', async () => {
    const user = userEvent.setup();
    render(<ContentPackManager />);

    // Wait for initial load
    await waitFor(() => {
      expect(screen.getByText('Test Pack')).toBeInTheDocument();
    });

    // Switch to loaded packs tab
    const loadedTab = screen.getByText('Loaded Packs');
    await user.click(loadedTab);

    expect(screen.getByText('Loaded Pack')).toBeInTheDocument();
    expect(screen.getByText('A loaded content pack')).toBeInTheDocument();
  });

  it('loads a content pack when load button is clicked', async () => {
    const user = userEvent.setup();
    loadContentPack.mockResolvedValue({ data: { success: true } });
    
    render(<ContentPackManager />);

    await waitFor(() => {
      expect(screen.getByText('Test Pack')).toBeInTheDocument();
    });

    // Click load button
    const loadButton = screen.getByText('Load');
    await user.click(loadButton);

    expect(loadContentPack).toHaveBeenCalledWith('test-pack.json');
  });

  it('unloads a content pack when unload button is clicked', async () => {
    const user = userEvent.setup();
    unloadContentPack.mockResolvedValue({ data: { success: true } });
    
    render(<ContentPackManager />);

    // Switch to loaded packs tab
    await waitFor(() => {
      expect(screen.getByText('Test Pack')).toBeInTheDocument();
    });

    const loadedTab = screen.getByText('Loaded Packs');
    await user.click(loadedTab);

    await waitFor(() => {
      expect(screen.getByText('Loaded Pack')).toBeInTheDocument();
    });

    // Click unload button
    const unloadButton = screen.getByText('Unload');
    await user.click(unloadButton);

    expect(unloadContentPack).toHaveBeenCalledWith('loaded-pack.json');
  });

  it('opens preview modal when preview button is clicked', async () => {
    const user = userEvent.setup();
    render(<ContentPackManager />);

    await waitFor(() => {
      expect(screen.getByText('Test Pack')).toBeInTheDocument();
    });

    // Click preview button
    const previewButton = screen.getByText('Preview');
    await user.click(previewButton);

    expect(screen.getByTestId('content-pack-preview')).toBeInTheDocument();
    expect(screen.getByText('Preview for test-pack.json')).toBeInTheDocument();
  });

  it('closes preview modal when close button is clicked', async () => {
    const user = userEvent.setup();
    render(<ContentPackManager />);

    await waitFor(() => {
      expect(screen.getByText('Test Pack')).toBeInTheDocument();
    });

    // Open preview
    const previewButton = screen.getByText('Preview');
    await user.click(previewButton);

    expect(screen.getByTestId('content-pack-preview')).toBeInTheDocument();

    // Close preview
    const closeButton = screen.getByText('Close Preview');
    await user.click(closeButton);

    expect(screen.queryByTestId('content-pack-preview')).not.toBeInTheDocument();
  });

  it('clears all loaded packs when clear all button is clicked', async () => {
    const user = userEvent.setup();
    clearAllLoadedPacks.mockResolvedValue({ data: { success: true } });
    
    render(<ContentPackManager />);

    // Switch to loaded packs tab
    await waitFor(() => {
      expect(screen.getByText('Test Pack')).toBeInTheDocument();
    });

    const loadedTab = screen.getByText('Loaded Packs');
    await user.click(loadedTab);

    await waitFor(() => {
      expect(screen.getByText('Loaded Pack')).toBeInTheDocument();
    });

    // Click clear all button
    const clearAllButton = screen.getByText('Clear All');
    await user.click(clearAllButton);

    expect(clearAllLoadedPacks).toHaveBeenCalled();
  });

  it('handles export form submission', async () => {
    const user = userEvent.setup();
    exportContentPack.mockResolvedValue({ 
      data: { 
        success: true, 
        filename: 'exported-pack.json' 
      } 
    });
    
    render(<ContentPackManager />);

    // Switch to export tab
    await waitFor(() => {
      expect(screen.getByText('Test Pack')).toBeInTheDocument();
    });

    const exportTab = screen.getByText('Export Current State');
    await user.click(exportTab);

    // Fill out export form
    const filenameInput = screen.getByLabelText(/filename/i);
    const nameInput = screen.getByLabelText(/pack name/i);
    const summaryInput = screen.getByLabelText(/summary/i);

    await user.type(filenameInput, 'my-export');
    await user.type(nameInput, 'My Export Pack');
    await user.type(summaryInput, 'My exported content pack');

    // Submit form
    const exportButton = screen.getByText('Export Content Pack');
    await user.click(exportButton);

    expect(exportContentPack).toHaveBeenCalledWith({
      filename: 'my-export',
      name: 'My Export Pack',
      summary: 'My exported content pack',
      description: '',
      authorName: '',
      authorEmail: ''
    });
  });

  it('handles API errors gracefully', async () => {
    getAvailableContentPacks.mockRejectedValue(new Error('API Error'));
    
    render(<ContentPackManager />);

    await waitFor(() => {
      expect(screen.getByText(/error loading content packs/i)).toBeInTheDocument();
    });
  });

  it('shows action loading states', async () => {
    const user = userEvent.setup();
    // Make loadContentPack return a promise that doesn't resolve immediately
    let resolveLoad;
    const loadPromise = new Promise(resolve => {
      resolveLoad = resolve;
    });
    loadContentPack.mockReturnValue(loadPromise);
    
    render(<ContentPackManager />);

    await waitFor(() => {
      expect(screen.getByText('Test Pack')).toBeInTheDocument();
    });

    // Click load button
    const loadButton = screen.getByText('Load');
    await user.click(loadButton);

    // Should show loading state
    expect(screen.getByText('Loading...')).toBeInTheDocument();

    // Resolve the promise
    resolveLoad({ data: { success: true } });
    
    await waitFor(() => {
      expect(screen.queryByText('Loading...')).not.toBeInTheDocument();
    });
  });

  it('filters content packs by search query', async () => {
    const user = userEvent.setup();
    
    // Add more packs for filtering
    const multiplePacksResponse = [
      ...mockAvailablePacks,
      {
        filename: 'another-pack.json',
        metadata: {
          name: 'Another Pack',
          summary: 'Different content pack',
          description: 'This is different',
          author: { name: 'Other Author', email: 'other@example.com' },
          version: '1.0.0',
          created: '2024-01-01T00:00:00Z'
        }
      }
    ];
    
    getAvailableContentPacks.mockResolvedValue({ data: multiplePacksResponse });
    
    render(<ContentPackManager />);

    await waitFor(() => {
      expect(screen.getByText('Test Pack')).toBeInTheDocument();
      expect(screen.getByText('Another Pack')).toBeInTheDocument();
    });

    // Search for "test"
    const searchInput = screen.getByPlaceholderText(/search content packs/i);
    await user.type(searchInput, 'test');

    // Should only show Test Pack
    expect(screen.getByText('Test Pack')).toBeInTheDocument();
    expect(screen.queryByText('Another Pack')).not.toBeInTheDocument();
  });
});