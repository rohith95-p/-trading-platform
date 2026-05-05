import React from 'react';
import { render, screen, waitFor, act } from '@testing-library/react';
import { SignalFeed, Signal } from './SignalFeed';

global.fetch = jest.fn();

const mockSignals: Signal[] = [
  { id: '1', symbol: 'BTC/USD', type: 'BUY', confidence: 0.87, timestamp: Date.now(), strategy: 'Momentum' },
  { id: '2', symbol: 'ETH/USD', type: 'SELL', confidence: 0.72, timestamp: Date.now() },
  { id: '3', symbol: 'SOL/USD', type: 'HOLD', confidence: 0.55, timestamp: Date.now() },
];

describe('SignalFeed', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it('renders loading state initially', () => {
    (global.fetch as jest.Mock).mockImplementation(() => new Promise(() => {}));
    render(<SignalFeed />);
    expect(screen.getByText(/loading signals/i)).toBeInTheDocument();
  });

  it('displays signals after fetch', async () => {
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => mockSignals,
    });

    render(<SignalFeed />);

    await waitFor(() => {
      expect(screen.getByText('BTC/USD')).toBeInTheDocument();
      expect(screen.getByText('ETH/USD')).toBeInTheDocument();
      expect(screen.getByText('SOL/USD')).toBeInTheDocument();
    });
  });

  it('shows BUY, SELL, HOLD badges', async () => {
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => mockSignals,
    });

    render(<SignalFeed />);

    await waitFor(() => {
      expect(screen.getByText('BUY')).toBeInTheDocument();
      expect(screen.getByText('SELL')).toBeInTheDocument();
      expect(screen.getByText('HOLD')).toBeInTheDocument();
    });
  });

  it('shows confidence as percentage', async () => {
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => [mockSignals[0]],
    });

    render(<SignalFeed />);

    await waitFor(() => {
      expect(screen.getByText('87%')).toBeInTheDocument();
    });
  });

  it('falls back to mock data on fetch error', async () => {
    (global.fetch as jest.Mock).mockRejectedValue(new Error('Network error'));

    render(<SignalFeed />);

    await waitFor(() => {
      // Mock data has BTC/USD
      expect(screen.getByText('BTC/USD')).toBeInTheDocument();
    });
  });

  it('shows empty state when no signals', async () => {
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => [],
    });

    render(<SignalFeed />);

    await waitFor(() => {
      expect(screen.getByText(/no signals available/i)).toBeInTheDocument();
    });
  });

  it('auto-refreshes every 1 second', async () => {
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => mockSignals,
    });

    render(<SignalFeed />);

    await waitFor(() => expect(global.fetch).toHaveBeenCalledTimes(1));

    act(() => { jest.advanceTimersByTime(1000); });
    await waitFor(() => expect(global.fetch).toHaveBeenCalledTimes(2));

    act(() => { jest.advanceTimersByTime(1000); });
    await waitFor(() => expect(global.fetch).toHaveBeenCalledTimes(3));
  });

  it('shows Live indicator', async () => {
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => mockSignals,
    });

    render(<SignalFeed />);

    await waitFor(() => {
      expect(screen.getByText('Live')).toBeInTheDocument();
    });
  });
});
