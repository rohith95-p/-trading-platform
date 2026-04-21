import { useState, useEffect } from 'react';
import { PortfolioAnalytics } from '@/types/portfolio';

/**
 * usePortfolioAnalytics Hook
 * Fetches and manages portfolio analytics data with automatic updates
 * 
 * @param updateInterval - Interval in milliseconds for fetching updates (default: 60000ms = 1 minute)
 * @returns Object containing analytics data, loading state, and error state
 */
export const usePortfolioAnalytics = (updateInterval: number = 60000) => {
  const [analytics, setAnalytics] = useState<PortfolioAnalytics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchAnalytics = async () => {
      try {
        setLoading(true);
        const response = await fetch('/api/portfolio/analytics');
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        setAnalytics(data);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error');
      } finally {
        setLoading(false);
      }
    };

    // Fetch immediately
    fetchAnalytics();

    // Set up interval for periodic updates
    const interval = setInterval(fetchAnalytics, updateInterval);

    return () => clearInterval(interval);
  }, [updateInterval]);

  return { analytics, loading, error };
};
