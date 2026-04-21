import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { PortfolioAnalytics } from './PortfolioAnalytics';
import { PortfolioAnalytics as PortfolioAnalyticsType } from '@/types/portfolio';

// Mock fetch
global.fetch = jest.fn();

describe('PortfolioAnalytics Component', () => {
  const mockAnalytics: PortfolioAnalyticsType = {
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
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => mockAnalytics,
    });
  });

  it('should render loading state initially', () => {
    (global.fetch as jest.Mock).mockImplementation(
      () => new Promise(() => {}) // Never resolves
    );
    render(<PortfolioAnalytics />);
    expect(screen.getByText(/loading portfolio analytics/i)).toBeInTheDocument();
  });

  it('should fetch and display portfolio analytics', async () => {
    render(<PortfolioAnalytics />);

    await waitFor(() => {
      expect(screen.getByText('Portfolio Analytics')).toBeInTheDocument();
    });

    expect(screen.getByText('$100000.00')).toBeInTheDocument();
    expect(screen.getByText('$5000.00')).toBeInTheDocument();
    expect(screen.getByText('5.00%')).toBeInTheDocument();
  });

  it('should display all composition charts', async () => {
    render(<PortfolioAnalytics />);

    await waitFor(() => {
      expect(screen.getByText('Portfolio by Asset')).toBeInTheDocument();
      expect(screen.getByText('Portfolio by Exchange')).toBeInTheDocument();
      expect(screen.getByText('Portfolio by Strategy')).toBeInTheDocument();
    });
  });

  it('should display cumulative P&L chart', async () => {
    render(<PortfolioAnalytics />);

    await waitFor(() => {
      expect(screen.getByText('Cumulative P&L')).toBeInTheDocument();
    });
  });

  it('should display daily P&L distribution chart', async () => {
    render(<PortfolioAnalytics />);

    await waitFor(() => {
      expect(screen.getByText('Daily P&L Distribution')).toBeInTheDocument();
    });
  });

  it('should display performance attribution chart', async () => {
    render(<PortfolioAnalytics />);

    await waitFor(() => {
      expect(screen.getByText('Performance Attribution')).toBeInTheDocument();
    });
  });

  it('should display asset composition items', async () => {
    render(<PortfolioAnalytics />);

    await waitFor(() => {
      expect(screen.getByText('BTC')).toBeInTheDocument();
      expect(screen.getByText('ETH')).toBeInTheDocument();
    });
  });

  it('should display exchange composition items', async () => {
    render(<PortfolioAnalytics />);

    await waitFor(() => {
      expect(screen.getByText('Binance')).toBeInTheDocument();
      expect(screen.getByText('Kraken')).toBeInTheDocument();
    });
  });

  it('should display strategy composition items', async () => {
    render(<PortfolioAnalytics />);

    await waitFor(() => {
      expect(screen.getByText('Strategy A')).toBeInTheDocument();
      expect(screen.getByText('Strategy B')).toBeInTheDocument();
    });
  });

  it('should handle fetch errors gracefully', async () => {
    (global.fetch as jest.Mock).mockRejectedValue(new Error('Network error'));

    render(<PortfolioAnalytics />);

    await waitFor(() => {
      expect(screen.getByText(/error: network error/i)).toBeInTheDocument();
    });
  });

  it('should handle HTTP errors gracefully', async () => {
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: false,
      status: 500,
    });

    render(<PortfolioAnalytics />);

    await waitFor(() => {
      expect(screen.getByText(/error: failed to fetch portfolio analytics/i)).toBeInTheDocument();
    });
  });

  it('should display last updated timestamp', async () => {
    render(<PortfolioAnalytics />);

    await waitFor(() => {
      expect(screen.getByText(/last updated:/i)).toBeInTheDocument();
    });
  });

  it('should format positive P&L with positive class', async () => {
    render(<PortfolioAnalytics />);

    await waitFor(() => {
      const pnlElement = screen.getByText('$5000.00');
      expect(pnlElement).toHaveClass('positive');
    });
  });

  it('should format negative P&L with negative class', async () => {
    const negativeAnalytics = {
      ...mockAnalytics,
      totalPnL: -5000,
      totalReturn: -5,
    };

    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => negativeAnalytics,
    });

    render(<PortfolioAnalytics />);

    await waitFor(() => {
      const pnlElement = screen.getByText('$-5000.00');
      expect(pnlElement).toHaveClass('negative');
    });
  });

  it('should set up interval for periodic updates', async () => {
    jest.useFakeTimers();
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

    jest.useRealTimers();
  });

  it('should display composition percentages correctly', async () => {
    render(<PortfolioAnalytics />);

    await waitFor(() => {
      expect(screen.getByText('50.0%')).toBeInTheDocument();
      expect(screen.getByText('60.0%')).toBeInTheDocument();
      expect(screen.getByText('70.0%')).toBeInTheDocument();
    });
  });
});
