import React from 'react';
import { render, screen } from '@testing-library/react';
import CompatibilityStatus from './CompatibilityStatus';

describe('CompatibilityStatus', () => {
  const mockCompatibilityCompatible = {
    compatible: true,
    has_conditions: true,
    app_version: '1.0.0',
    conditions: [
      {
        type: 'version_range',
        min_version: '1.0.0',
        reason: 'Requires v1.0+ features'
      }
    ],
    reasons: []
  };

  const mockCompatibilityIncompatible = {
    compatible: false,
    has_conditions: true,
    app_version: '1.0.0',
    conditions: [
      {
        type: 'version_range',
        min_version: '2.0.0',
        reason: 'Requires v2.0+ features'
      }
    ],
    reasons: ['Requires v2.0+ features: requires version >= 2.0.0, got 1.0.0']
  };

  const mockCompatibilityUniversal = {
    compatible: true,
    has_conditions: false,
    app_version: '1.0.0',
    conditions: [],
    reasons: []
  };

  test('renders compatible status correctly', () => {
    render(<CompatibilityStatus compatibility={mockCompatibilityCompatible} />);
    
    expect(screen.getByText('Compatible')).toBeInTheDocument();
    expect(screen.getByTitle('Compatible')).toBeInTheDocument();
    expect(screen.getByText('(v1.0.0)')).toBeInTheDocument();
  });

  test('renders incompatible status correctly', () => {
    render(<CompatibilityStatus compatibility={mockCompatibilityIncompatible} />);
    
    expect(screen.getByText('Incompatible')).toBeInTheDocument();
    expect(screen.getByTitle('Incompatible')).toBeInTheDocument();
    expect(screen.getByText('(v1.0.0)')).toBeInTheDocument();
  });

  test('renders universal compatibility correctly', () => {
    render(<CompatibilityStatus compatibility={mockCompatibilityUniversal} />);
    
    expect(screen.getByText('Universal compatibility')).toBeInTheDocument();
    expect(screen.getByTitle('Universal compatibility')).toBeInTheDocument();
  });

  test('shows details when showDetails is true', () => {
    render(
      <CompatibilityStatus 
        compatibility={mockCompatibilityIncompatible} 
        showDetails={true} 
      />
    );
    
    expect(screen.getByText('Issues:')).toBeInTheDocument();
    expect(screen.getByText('Requirements:')).toBeInTheDocument();
    // Use getAllByText instead of getByText since there are multiple matches
    const elements = screen.getAllByText(/Requires v2\.0\+ features/);
    expect(elements.length).toBeGreaterThan(0);
  });

  test('hides details when showDetails is false', () => {
    render(
      <CompatibilityStatus 
        compatibility={mockCompatibilityIncompatible} 
        showDetails={false} 
      />
    );
    
    expect(screen.queryByText('Issues:')).not.toBeInTheDocument();
    expect(screen.queryByText('Requirements:')).not.toBeInTheDocument();
  });

  test('renders nothing when compatibility is null', () => {
    const { container } = render(<CompatibilityStatus compatibility={null} />);
    expect(container.firstChild).toBeNull();
  });

  test('applies custom className', () => {
    const { container } = render(
      <CompatibilityStatus 
        compatibility={mockCompatibilityCompatible} 
        className="custom-class" 
      />
    );
    
    expect(container.firstChild).toHaveClass('custom-class');
  });
});