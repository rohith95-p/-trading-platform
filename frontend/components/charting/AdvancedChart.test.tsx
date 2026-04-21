import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { AdvancedChart } from './AdvancedChart';
import { ChartConfig } from '@/types/charting';

// Mock fetch
global.fetch = jest.fn();

describe('AdvancedChart Component', () => {
  const mockChartConfig: ChartConfig = {
    type: 'candlestick',
    timeframe: '1h',
    symbol: 'BTC/USD',
    indicators: ['EMA_20', 'RSI_14'],
    showOrderBook: true,
    showBidAsk: true,
    height: 500,
    width: 800,
  };

  const mockCandleData = [
    { time: 1000, open: 100, high: 105, low: 99, close: 102, volume: 1000 },
    { time: 2000, open: 102, high: 108, low: 101, close: 107, volume: 1200 },
    { time: 3000, open: 107, high: 110, low: 106, close: 108, volume: 1100 },
  ];

  const mockIndicatorData = {
    indicators: [
      {
        name: 'EMA_20',
        type: 'line',
        data: [
          { time: 1000, value: 101 },
          { time: 2000, value: 104 },
          { time: 3000, value: 107 },
        ],
        color: '#3b82f6',
      },
    ],
  };

  const mockOrderBook = {
    bids: [
      { price: 99.9, quantity: 1.5, side: 'bid' },
      { price: 99.8, quantity: 2.0, side: 'bid' },
    ],
    asks: [
      { price: 100.1, quantity: 1.5, side: 'ask' },
      { price: 100.2, quantity: 2.0, side: 'ask' },
    ],
    timestamp: Date.now(),
  };

  const mockBidAsk = {
    bid: 99.9,
    ask: 100.1,
    spread: 0.2,
    spreadPercentage: 0.002,
  };

  beforeEach(() => {
    jest.clearAllMocks();
    (global.fetch as jest.Mock).mockImplementation((url: string) => {
      if (url.includes('/api/charting/data')) {
        return Promise.resolve({
          ok: true,
          json: async () => ({ candles: mockCandleData }),
        });
      }
      if (url.includes('/api/charting/indicators')) {
        return Promise.resolve({
          ok: true,
          json: async () => mockIndicatorData,
        });
      }
      if (url.includes('/api/charting/orderbook')) {
        return Promise.resolve({
          ok: true,
          json: async () => mockOrderBook,
        });
      }
      if (url.includes('/api/charting/bid-ask')) {
        return Promise.resolve({
          ok: true,
          json: async () => mockBidAsk,
        });
      }
      return Promise.reject(new Error('Unknown endpoint'));
    });
  });

  it('should render loading state initially', () => {
    (global.fetch as jest.Mock).mockImplementation(
      () => new Promise(() => {}) // Never resolves
    );
    render(<AdvancedChart config={mockChartConfig} />);
    expect(screen.getByText(/loading chart/i)).toBeInTheDocument();
  });

  it('should fetch and display chart data', async () => {
    render(<AdvancedChart config={mockChartConfig} />);

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/charting/data')
      );
    });
  });

  it('should display chart header with symbol and timeframe', async () => {
    render(<AdvancedChart config={mockChartConfig} />);

    await waitFor(() => {
      expect(screen.getByText('BTC/USD')).toBeInTheDocument();
      expect(screen.getByText('1h')).toBeInTheDocument();
    });
  });

  it('should display timeframe selector buttons', async () => {
    render(<AdvancedChart config={mockChartConfig} />);

    await waitFor(() => {
      expect(screen.getByText('1m')).toBeInTheDocument();
      expect(screen.getByText('5m')).toBeInTheDocument();
      expect(screen.getByText('15m')).toBeInTheDocument();
      expect(screen.getByText('1h')).toBeInTheDocument();
      expect(screen.getByText('4h')).toBeInTheDocument();
      expect(screen.getByText('1d')).toBeInTheDocument();
    });
  });

  it('should fetch indicators when specified', async () => {
    render(<AdvancedChart config={mockChartConfig} />);

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/charting/indicators')
      );
    });
  });

  it('should display bid-ask spread when enabled', async () => {
    render(<AdvancedChart config={mockChartConfig} />);

    await waitFor(() => {
      expect(screen.getByText('Bid')).toBeInTheDocument();
      expect(screen.getByText('Ask')).toBeInTheDocument();
      expect(screen.getByText('Spread')).toBeInTheDocument();
    });
  });

  it('should display order book when enabled', async () => {
    render(<AdvancedChart config={mockChartConfig} />);

    await waitFor(() => {
      expect(screen.getByText('Asks')).toBeInTheDocument();
      expect(screen.getByText('Bids')).toBeInTheDocument();
    });
  });

  it('should display indicator legend', async () => {
    render(<AdvancedChart config={mockChartConfig} />);

    await waitFor(() => {
      expect(screen.getByText('EMA_20')).toBeInTheDocument();
    });
  });

  it('should handle fetch errors gracefully', async () => {
    (global.fetch as jest.Mock).mockRejectedValue(new Error('Network error'));

    render(<AdvancedChart config={mockChartConfig} />);

    await waitFor(() => {
      expect(screen.getByText(/error: network error/i)).toBeInTheDocument();
    });
  });

  it('should handle HTTP errors gracefully', async () => {
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: false,
      status: 500,
    });

    render(<AdvancedChart config={mockChartConfig} />);

    await waitFor(() => {
      expect(screen.getByText(/error: failed to fetch chart data/i)).toBeInTheDocument();
    });
  });

  it('should support candlestick chart type', async () => {
    const config: ChartConfig = {
      ...mockChartConfig,
      type: 'candlestick',
    };

    render(<AdvancedChart config={config} />);

    await waitFor(() => {
      expect(screen.getByText('BTC/USD')).toBeInTheDocument();
    });
  });

  it('should support line chart type', async () => {
    const config: ChartConfig = {
      ...mockChartConfig,
      type: 'line',
    };

    render(<AdvancedChart config={config} />);

    await waitFor(() => {
      expect(screen.getByText('BTC/USD')).toBeInTheDocument();
    });
  });

  it('should support area chart type', async () => {
    const config: ChartConfig = {
      ...mockChartConfig,
      type: 'area',
    };

    render(<AdvancedChart config={config} />);

    await waitFor(() => {
      expect(screen.getByText('BTC/USD')).toBeInTheDocument();
    });
  });

  it('should support OHLC chart type', async () => {
    const config: ChartConfig = {
      ...mockChartConfig,
      type: 'ohlc',
    };

    render(<AdvancedChart config={config} />);

    await waitFor(() => {
      expect(screen.getByText('BTC/USD')).toBeInTheDocument();
    });
  });

  it('should support multiple timeframes', async () => {
    const timeframes = ['1m', '5m', '15m', '1h', '4h', '1d'] as const;

    for (const tf of timeframes) {
      const config: ChartConfig = {
        ...mockChartConfig,
        timeframe: tf,
      };

      const { unmount } = render(<AdvancedChart config={config} />);

      await waitFor(() => {
        expect(screen.getByText(tf)).toBeInTheDocument();
      });

      unmount();
    }
  });

  it('should hide bid-ask when disabled', async () => {
    const config: ChartConfig = {
      ...mockChartConfig,
      showBidAsk: false,
    };

    render(<AdvancedChart config={config} />);

    await waitFor(() => {
      expect(screen.queryByText('Bid')).not.toBeInTheDocument();
    });
  });

  it('should hide order book when disabled', async () => {
    const config: ChartConfig = {
      ...mockChartConfig,
      showOrderBook: false,
    };

    render(<AdvancedChart config={config} />);

    await waitFor(() => {
      expect(screen.queryByText('Asks')).not.toBeInTheDocument();
    });
  });

  it('should update order book periodically', async () => {
    jest.useFakeTimers();
    render(<AdvancedChart config={mockChartConfig} />);

    await waitFor(() => {
      expect(screen.getByText('Asks')).toBeInTheDocument();
    });

    const initialCallCount = (global.fetch as jest.Mock).mock.calls.length;

    // Advance time by 1 second
    jest.advanceTimersByTime(1000);

    // Should have fetched order book again
    expect((global.fetch as jest.Mock).mock.calls.length).toBeGreaterThan(initialCallCount);

    jest.useRealTimers();
  });

  it('should display drawing tools panel', async () => {
    render(<AdvancedChart config={mockChartConfig} />);

    await waitFor(() => {
      expect(screen.getByTitle('Add Trendline')).toBeInTheDocument();
      expect(screen.getByTitle('Add Support Level')).toBeInTheDocument();
      expect(screen.getByTitle('Add Resistance Level')).toBeInTheDocument();
      expect(screen.getByTitle('Add Annotation')).toBeInTheDocument();
    });
  });

  it('should handle empty chart data', async () => {
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => ({ candles: [] }),
    });

    render(<AdvancedChart config={mockChartConfig} />);

    await waitFor(() => {
      expect(screen.getByText(/no data available/i)).toBeInTheDocument();
    });
  });
});
