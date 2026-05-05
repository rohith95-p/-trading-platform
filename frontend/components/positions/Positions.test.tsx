import React from 'react';
import { render, screen, waitFor, act } from '@testing-library/react';
import { Positions, Position } from './Positions';

global.fetch = jest.fn();

const mockPositions: Position[] = [
  {
    id: '1',
    symbol: 'BTC/USD',
    size: 0.5,
    entryPrice: 40000,
    currentPrice: 42000,
    unrealizedPnl: 1000,
    unrealizedPnlPercent: 5,
    side: 'LONG',
  },
  {
    id: '2',
    symbol: 'ETH/USD',
    size: 2,
    entryPrice: 2500,
    currentPrice: 2400,
    unrealizedPnl: -200,
    unrealizedPnlPercent: -4,
    side: 'SHORT',
  },
];

describe('Positions', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it('renders loading state initially', () => {
    (global.fetch as jest.Mock).mockImplementation(() => new Promise(() => {}));
    render(<Positions />);
    expect(screen.getByText(/loading positions/i)).toBeInTheDocument();
  });

  it('displays positions after fetch', async () => {
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => mockPositions,
    });

    render(<Positions />);

    await waitFor(() => {
      expect(screen.getByText('BTC/USD')).toBeInTheDocument();
      expect(screen.getByText('ETH/USD')).toBeInTheDocument();
    });
  });

  it('shows empty state when no positions', async () => {
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => [],
    });

    render(<Positions />);

    await waitFor(() => {
      expect(screen.getByText(/no open positions/i)).toBeInTheDocument();
    });
  });

  it('shows error on fetch failure', async () => {
    (global.fetch as jest.Mock).mockResolvedValue({ ok: false });

    render(<Positions />);

    await waitFor(() => {
      expect(screen.getByText(/failed to fetch positions/i)).toBeInTheDocument();
    });
  });

  it('color-codes positive unrealized PnL green', async () => {
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => [mockPositions[0]],
    });

    render(<Positions />);

    await waitFor(() => {
      const pnlEl = screen.getByText('+$1000.00');
      expect(pnlEl).toHaveClass('text-green-400');
    });
  });

  it('color-codes negative unrealized PnL red', async () => {
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => [mockPositions[1]],
    });

    render(<Positions />);

    await waitFor(() => {
      const pnlEl = screen.getByText('-$200.00');
      expect(pnlEl).toHaveClass('text-red-400');
    });
  });

  it('shows total unrealized PnL', async () => {
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => mockPositions,
    });

    render(<Positions />);

    await waitFor(() => {
      // 1000 - 200 = 800
      expect(screen.getByText(/total pnl/i)).toBeInTheDocument();
    });
  });

  it('auto-refreshes every 1 second', async () => {
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => mockPositions,
    });

    render(<Positions />);

    await waitFor(() => expect(global.fetch).toHaveBeenCalledTimes(1));

    act(() => { jest.advanceTimersByTime(1000); });
    await waitFor(() => expect(global.fetch).toHaveBeenCalledTimes(2));
  });
});
