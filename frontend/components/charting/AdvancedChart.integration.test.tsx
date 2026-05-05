import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { AdvancedChart } from './AdvancedChart';
import { ChartConfig } from '@/types/charting';

/**
 * Integration Tests for AdvancedChart Component
 * Tests interaction with charting API endpoints
 */

describe('AdvancedChart Integration Tests', () => {
  const mockChartConfig: ChartConfig = {
    type: 'candlestick',
    timeframe: '1h',
    symbol: 'BTC/USD',
    indicators: ['EMA_20', 'RSI_14', 'MACD'],
    showOrderBook: true,
    showBidAsk: true,
  };

  const mockChartData = {
    candles: Array.from({ length: 100 }, (_, i) => ({
      time: 1000 + i * 3600,
      open: 100 + Math.random() * 10,
      high: 110 + Math.random() * 10,
      low: 90 + Math.random() * 10,
      close: 100 + Math.random() * 10,
      volume: 1000 + Math.random() * 5000,
    })),
  };

  const mockIndicators = {
    indicators: [
      {
        name: 'EMA_20',
        type: 'line',
        data: Array.from({ length: 100 }, (_, i) => ({
          time: 1000 + i * 3600,
          value: 100 + Math.random() * 5,
        })),
        color: '#3b82f6',
      },
      {
        name: 'RSI_14',
        type: 'line',
        data: Array.from({ length: 100 }, (_, i) => ({
          time: 1000 + i * 3600,
          value: 50 + Math.random() * 20,
        })),
        color: '#ef4444',
      },
      {
        name: 'MACD',
        type: 'histogram',
        data: Array.from({ length: 100 }, (_, i) => ({
          time: 1000 + i * 3600,
          value: Math.random() * 2 - 1,
        })),
        color: '#10b981',
      },
    ],
  };

  const mockOrderBook = {
    bids: Array.from({ length: 10 }, (_, i) => ({
      price: 99.9 - i * 0.1,
      quantity: Math.random() * 5,
      side: 'bid',
    })),
    asks: Array.from({ length: 10 }, (_, i) => ({
      price: 100.1 + i * 0.1,
      quantity: Math.random() * 5,
      side: 'ask',
    })),
    timestamp: Date.now(),
  };

  const mockBidAsk = {
    bid: 99.95,
    ask: 100.05,
    spread: 0.1,
    spreadPercentage: 0.001,
  };

  beforeEach(() => {
    jest.clearAllMocks();
    global.fetch = jest.fn((input: RequestInfo | URL) => {
      const url = input.toString();
      if (url.includes('/api/charting/data')) {
        return Promise.resolve({
          ok: true,
          json: async () => mockChartData,
        } as Response);
      }
      if (url.includes('/api/charting/indicators')) {
        return Promise.resolve({
          ok: true,
          json: async () => mockIndicators,
        } as Response);
      }
      if (url.includes('/api/charting/orderbook')) {
        return Promise.resolve({
          ok: true,
          json: async () => mockOrderBook,
        } as Response);
      }
      if (url.includes('/api/charting/bid-ask')) {
        return Promise.resolve({
          ok: true,
          json: async () => mockBidAsk,
        } as Response);
      }
      return Promise.reject(new Error('Unknown endpoint'));
    }) as jest.MockedFunction<typeof fetch>;
  });

  it('should fetch chart data from API', async () => {
    render(<AdvancedChart config={mockChartConfig} />);

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/charting/data?symbol=BTC/USD&timeframe=1h&type=candlestick')
      );
    });
  });

  it('should fetch indicators from API', async () => {
    render(<AdvancedChart config={mockChartConfig} />);

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/charting/indicators?symbol=BTC/USD&timeframe=1h&indicators=EMA_20,RSI_14,MACD')
      );
    });
  });

  it('should fetch order book from API', async () => {
    render(<AdvancedChart config={mockChartConfig} />);

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/charting/orderbook?symbol=BTC/USD')
      );
    });
  });

  it('should fetch bid-ask spread from API', async () => {
    render(<AdvancedChart config={mockChartConfig} />);

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/charting/bid-ask?symbol=BTC/USD')
      );
    });
  });

  it('should display all indicators from API', async () => {
    render(<AdvancedChart config={mockChartConfig} />);

    await waitFor(() => {
      expect(screen.getByText('EMA_20')).toBeInTheDocument();
      expect(screen.getByText('RSI_14')).toBeInTheDocument();
      expect(screen.getByText('MACD')).toBeInTheDocument();
    });
  });

  it('should display bid-ask spread values', async () => {
    render(<AdvancedChart config={mockChartConfig} />);

    await waitFor(() => {
      expect(screen.getByText('$99.95')).toBeInTheDocument();
      expect(screen.getByText('$100.05')).toBeInTheDocument();
    });
  });

  it('should display order book depth', async () => {
    render(<AdvancedChart config={mockChartConfig} />);

    await waitFor(() => {
      expect(screen.getByText('Asks')).toBeInTheDocument();
      expect(screen.getByText('Bids')).toBeInTheDocument();
    });
  });

  it('should handle large datasets', async () => {
    const largeChartData = {
      candles: Array.from({ length: 10000 }, (_, i) => ({
        time: 1000 + i * 60,
        open: 100 + Math.random() * 10,
        high: 110 + Math.random() * 10,
        low: 90 + Math.random() * 10,
        close: 100 + Math.random() * 10,
        volume: 1000 + Math.random() * 5000,
      })),
    };

    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => largeChartData,
    });

    render(<AdvancedChart config={mockChartConfig} />);

    await waitFor(() => {
      expect(screen.getByText('BTC/USD')).toBeInTheDocument();
    });
  });

  it('should handle API errors gracefully', async () => {
    (global.fetch as jest.Mock).mockRejectedValue(new Error('API Error'));

    render(<AdvancedChart config={mockChartConfig} />);

    await waitFor(() => {
      expect(screen.getByText(/error: api error/i)).toBeInTheDocument();
    });
  });

  it('should handle HTTP 500 errors', async () => {
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: false,
      status: 500,
    });

    render(<AdvancedChart config={mockChartConfig} />);

    await waitFor(() => {
      expect(screen.getByText(/error: failed to fetch chart data/i)).toBeInTheDocument();
    });
  });

  it('should support different chart types', async () => {
    const chartTypes = ['candlestick', 'ohlc', 'line', 'area'] as const;

    for (const type of chartTypes) {
      const config: ChartConfig = {
        ...mockChartConfig,
        type,
      };

      const { unmount } = render(<AdvancedChart config={config} />);

      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalledWith(
          expect.stringContaining(`type=${type}`)
        );
      });

      unmount();
    }
  });

  it('should support different timeframes', async () => {
    const timeframes = ['1m', '5m', '15m', '1h', '4h', '1d'] as const;

    for (const timeframe of timeframes) {
      const config: ChartConfig = {
        ...mockChartConfig,
        timeframe,
      };

      const { unmount } = render(<AdvancedChart config={config} />);

      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalledWith(
          expect.stringContaining(`timeframe=${timeframe}`)
        );
      });

      unmount();
    }
  });

  it('should update order book in real-time', async () => {
    jest.useFakeTimers();

    render(<AdvancedChart config={mockChartConfig} />);

    await waitFor(() => {
      expect(screen.getByText('Asks')).toBeInTheDocument();
    });

    const initialOrderBookCalls = (global.fetch as jest.Mock).mock.calls.filter(
      call => call[0].includes('/api/charting/orderbook')
    ).length;

    // Advance time by 1 second
    jest.advanceTimersByTime(1000);

    const updatedOrderBookCalls = (global.fetch as jest.Mock).mock.calls.filter(
      call => call[0].includes('/api/charting/orderbook')
    ).length;

    expect(updatedOrderBookCalls).toBeGreaterThan(initialOrderBookCalls);

    jest.useRealTimers();
  });

  it('should update bid-ask spread in real-time', async () => {
    jest.useFakeTimers();

    render(<AdvancedChart config={mockChartConfig} />);

    await waitFor(() => {
      expect(screen.getByText('Spread')).toBeInTheDocument();
    });

    const initialBidAskCalls = (global.fetch as jest.Mock).mock.calls.filter(
      call => call[0].includes('/api/charting/bid-ask')
    ).length;

    // Advance time by 1 second
    jest.advanceTimersByTime(1000);

    const updatedBidAskCalls = (global.fetch as jest.Mock).mock.calls.filter(
      call => call[0].includes('/api/charting/bid-ask')
    ).length;

    expect(updatedBidAskCalls).toBeGreaterThan(initialBidAskCalls);

    jest.useRealTimers();
  });

  it('should handle missing indicators gracefully', async () => {
    const config: ChartConfig = {
      ...mockChartConfig,
      indicators: undefined,
    };

    render(<AdvancedChart config={config} />);

    await waitFor(() => {
      expect(screen.getByText('BTC/USD')).toBeInTheDocument();
    });

    // Should not have called indicators endpoint
    expect(global.fetch).not.toHaveBeenCalledWith(
      expect.stringContaining('/api/charting/indicators')
    );
  });

  it('should handle missing order book gracefully', async () => {
    const config: ChartConfig = {
      ...mockChartConfig,
      showOrderBook: false,
    };

    render(<AdvancedChart config={config} />);

    await waitFor(() => {
      expect(screen.getByText('BTC/USD')).toBeInTheDocument();
    });

    // Should not have called order book endpoint
    expect(global.fetch).not.toHaveBeenCalledWith(
      expect.stringContaining('/api/charting/orderbook')
    );
  });

  it('should handle missing bid-ask gracefully', async () => {
    const config: ChartConfig = {
      ...mockChartConfig,
      showBidAsk: false,
    };

    render(<AdvancedChart config={config} />);

    await waitFor(() => {
      expect(screen.getByText('BTC/USD')).toBeInTheDocument();
    });

    // Should not have called bid-ask endpoint
    expect(global.fetch).not.toHaveBeenCalledWith(
      expect.stringContaining('/api/charting/bid-ask')
    );
  });
});
