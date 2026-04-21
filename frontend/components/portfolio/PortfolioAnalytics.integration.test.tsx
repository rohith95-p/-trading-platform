import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { PortfolioAnalytics } from './PortfolioAnalytics';

/**
 * Integration Tests for PortfolioAnalytics Component
 * Tests interaction with API endpoints
 */

describe('PortfolioAnalytics Integration Tests', () => {
  const mockAnalyticsResponse = {
    assetComposition: [
      { name: 'BTC', value: 50000, percentage: 50 },
      { name: 'ETH', value: 50000, percentage: 50 },
    ],
    exchangeComposition: [
      { name: 'Binance', value: 60000, percentage: 60 },
      { name: 'Kraken', value: 40000, percentage: 40 },
    ],
    strategyComposition: [
      { name: 'Strategy A', value: 70000, percentage: 70 },
      { name: 'Strategy B', value: 30000, percentage: 30 },
    ],
    cumulativePnL: [
      { timestamp: 1000, value: 100000, pnl: 0 },
      { timestamp: 2000, value: 105000, pnl: 5000 },
      { timestamp: 3000, value: 103000, pnl: 3000 },
    ],
    dailyPnLDistribution: [
      { date: '2024-01-01', pnl: 1000 },
      { date: '2024-01-02', pnl: -500 },
      { date: '2024-01-03', pnl: 2000 },
    ],
    performanceAttribution: [
      { category: 'Asset', attribution: 3000, percentage: 60 },
      { category: 'Exchange', attribution: 2000, percentage: 40 },
    ],
    totalValue: 100000,
    totalPnL: 5000,
    totalReturn: 5,
    lastUpdated: Date.now(),
  };

  beforeEach(() => {
    jest.clearAllMocks();
    global.fetch = jest.fn();
  });

  it('should fetch portfolio analytics from API endpoint', async () => {
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => mockAnalyticsResponse,
    });

    render(<PortfolioAnalytics />);

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith('/api/portfolio/analytics');
    });
  });

  it('should display all composition data from API', async () => {
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => mockAnalyticsResponse,
    });

    render(<PortfolioAnalytics />);

    await waitFor(() => {
      // Asset composition
      expect(screen.getByText('BTC')).toBeInTheDocument();
      expect(screen.getByText('ETH')).toBeInTheDocument();

      // Exchange composition
      expect(screen.getByText('Binance')).toBeInTheDocument();
      expect(screen.getByText('Kraken')).toBeInTheDocument();

      // Strategy composition
      expect(screen.getByText('Strategy A')).toBeInTheDocument();
      expect(screen.getByText('Strategy B')).toBeInTheDocument();
    });
  });

  it('should display all chart sections', async () => {
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => mockAnalyticsResponse,
    });

    render(<PortfolioAnalytics />);

    await waitFor(() => {
      expect(screen.getByText('Portfolio by Asset')).toBeInTheDocument();
      expect(screen.getByText('Portfolio by Exchange')).toBeInTheDocument();
      expect(screen.getByText('Portfolio by Strategy')).toBeInTheDocument();
      expect(screen.getByText('Cumulative P&L')).toBeInTheDocument();
      expect(screen.getByText('Daily P&L Distribution')).toBeInTheDocument();
      expect(screen.getByText('Performance Attribution')).toBeInTheDocument();
    });
  });

  it('should update analytics at least once per minute', async () => {
    jest.useFakeTimers();
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => mockAnalyticsResponse,
    });

    render(<PortfolioAnalytics />);

    await waitFor(() => {
      expect(screen.getByText('Portfolio Analytics')).toBeInTheDocument();
    });

    // Initial fetch
    expect(global.fetch).toHaveBeenCalledTimes(1);

    // Advance time by 60 seconds
    jest.advanceTimersByTime(60000);

    // Should have fetched again
    expect(global.fetch).toHaveBeenCalledTimes(2);

    // Advance time by another 60 seconds
    jest.advanceTimersByTime(60000);

    // Should have fetched again
    expect(global.fetch).toHaveBeenCalledTimes(3);

    jest.useRealTimers();
  });

  it('should handle API errors gracefully', async () => {
    (global.fetch as jest.Mock).mockRejectedValue(new Error('API Error'));

    render(<PortfolioAnalytics />);

    await waitFor(() => {
      expect(screen.getByText(/error: api error/i)).toBeInTheDocument();
    });
  });

  it('should handle HTTP 500 errors', async () => {
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: false,
      status: 500,
    });

    render(<PortfolioAnalytics />);

    await waitFor(() => {
      expect(screen.getByText(/error: failed to fetch portfolio analytics/i)).toBeInTheDocument();
    });
  });

  it('should handle empty composition data', async () => {
    const emptyAnalytics = {
      ...mockAnalyticsResponse,
      assetComposition: [],
      exchangeComposition: [],
      strategyComposition: [],
    };

    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => emptyAnalytics,
    });

    render(<PortfolioAnalytics />);

    await waitFor(() => {
      expect(screen.getByText('Portfolio Analytics')).toBeInTheDocument();
    });
  });

  it('should handle empty P&L data', async () => {
    const emptyAnalytics = {
      ...mockAnalyticsResponse,
      cumulativePnL: [],
      dailyPnLDistribution: [],
    };

    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => emptyAnalytics,
    });

    render(<PortfolioAnalytics />);

    await waitFor(() => {
      expect(screen.getByText('Portfolio Analytics')).toBeInTheDocument();
    });
  });

  it('should display correct summary metrics', async () => {
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => mockAnalyticsResponse,
    });

    render(<PortfolioAnalytics />);

    await waitFor(() => {
      expect(screen.getByText('$100000.00')).toBeInTheDocument(); // Total Value
      expect(screen.getByText('$5000.00')).toBeInTheDocument();   // Total P&L
      expect(screen.getByText('5.00%')).toBeInTheDocument();      // Total Return
    });
  });

  it('should display last updated timestamp', async () => {
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => mockAnalyticsResponse,
    });

    render(<PortfolioAnalytics />);

    await waitFor(() => {
      expect(screen.getByText(/last updated:/i)).toBeInTheDocument();
    });
  });

  it('should handle large datasets', async () => {
    const largeAnalytics = {
      ...mockAnalyticsResponse,
      cumulativePnL: Array.from({ length: 1000 }, (_, i) => ({
        timestamp: i * 1000,
        value: 100000 + i * 100,
        pnl: i * 100,
      })),
      dailyPnLDistribution: Array.from({ length: 365 }, (_, i) => ({
        date: `2024-${String((i % 12) + 1).padStart(2, '0')}-${String((i % 28) + 1).padStart(2, '0')}`,
        pnl: Math.random() * 10000 - 5000,
      })),
    };

    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => largeAnalytics,
    });

    render(<PortfolioAnalytics />);

    await waitFor(() => {
      expect(screen.getByText('Portfolio Analytics')).toBeInTheDocument();
    });
  });
});
