import React, { useState, useEffect } from 'react';
import CompatibilityStatus from './CompatibilityStatus';

/**
 * Component that fetches and displays compatibility status for a content pack
 */
const PackCompatibilityIndicator = ({ 
  pack, 
  getCompatibilityInfo, 
  showDetails = false,
  className = ''
}) => {
  const [compatibility, setCompatibility] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchCompatibility = async () => {
      try {
        setLoading(true);
        const compatibilityInfo = await getCompatibilityInfo(pack);
        setCompatibility(compatibilityInfo);
      } catch (err) {
        console.error('Error fetching compatibility:', err);
        setCompatibility({
          compatible: false,
          has_conditions: true,
          conditions: [],
          reasons: ['Error checking compatibility']
        });
      } finally {
        setLoading(false);
      }
    };

    if (pack) {
      fetchCompatibility();
    }
  }, [pack, getCompatibilityInfo]);

  if (loading) {
    return (
      <div className={`compatibility-loading ${className}`}>
        <span className="loading-text">Checking compatibility...</span>
      </div>
    );
  }

  if (!compatibility) {
    return null;
  }

  return (
    <CompatibilityStatus 
      compatibility={compatibility}
      showDetails={showDetails}
      className={`pack-compatibility ${className}`}
    />
  );
};

export default PackCompatibilityIndicator;