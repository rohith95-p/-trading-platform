import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { TradeHistory, Trade } from './TradeHistory';

global.fetch = jest.fn();

const makeTrade = (overrides: Partial<Trade> = {}): Trade => ({
  id: '1',
  symbol: 'BTC/USD',
  side: 'BUY',
  entryPrice: 40000,
  exitPrice: 42000,
  pnl: 200,
  pnlPercent: 5,
  timestamp: Date.now(),
  ...overrides,
});

const mockTrades: Trade[] = [
  makeTrade({ id: '1', symbol: 'BTC/USD', side: 'BUY', pnl: 200, pnlPercent: 5 }),
  makeTrade({ id: '2', symbol: 'ETH/USD', side: 'SELL', pnl: -50, pnlPercent: -2.5 }),
  makeTrade({ id: '3', symbol: 'SOL/USD', side: 'BUY', pnl: 30, pnlPercent: 1.5 }),
];

describe('TradeHistory', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders loading state initially', () => {
    (global.fetch as jest.Mock).mockImplementation(() => new Promise(() => {}));
    render(<TradeHistory />);
    expect(screen.getByText(/loading trade history/i)).toBeInTheDocument();
  });

  it('displays trades after fetch', async () => {
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => mockTrades,
    });

    render(<TradeHistory />);

    await waitFor(() => {
      expect(screen.getByText('BTC/USD')).toBeInTheDocument();
      expect(screen.getByText('ETH/USD')).toBeInTheDocument();
    });
  });

  it('shows error on fetch failure', async () => {
    (global.fetch as jest.Mock).mockResolvedValue({ ok: false, statusText: 'Not Found' });

    render(<TradeHistory />);

    await waitFor(() => {
      expect(screen.getByText(/failed to fetch trades/i)).toBeInTheDocument();
    });
  });

  it('shows empty state when no trades', async () => {
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => [],
    });

    render(<TradeHistory />);

    await waitFor(() => {
      expect(screen.getByText(/no trades found/i)).toBeInTheDocument();
    });
  });

  it('color-codes positive PnL green', async () => {
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => [makeTrade({ pnl: 200, pnlPercent: 5 })],
    });

    render(<TradeHistory />);

    await waitFor(() => {
      const pnlCell = screen.getByText('+$200.00');
      expect(pnlCell).toHaveClass('text-green-400');
    });
  });

  it('color-codes negative PnL red', async () => {
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => [makeTrade({ pnl: -50, pnlPercent: -2.5 })],
    });

    render(<TradeHistory />);

    await waitFor(() => {
      const pnlCell = screen.getByText('-$50.00');
      expect(pnlCell).toHaveClass('text-red-400');
    });
  });

  it('sorts by column when header clicked', async () => {
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => mockTrades,
    });

    render(<TradeHistory />);

    await waitFor(() => {
      expect(screen.getByText('BTC/USD')).toBeInTheDocument();
    });

    // Click Symbol header to sort
    fireEvent.click(screen.getByText('Symbol'));

    // After sort, rows should still be present
    expect(screen.getByText('BTC/USD')).toBeInTheDocument();
  });

  it('shows pagination when more than 10 trades', async () => {
    const manyTrades = Array.from({ length: 15 }, (_, i) =>
      makeTrade({ id: String(i), symbol: `COIN${i}/USD` })
    );

    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => manyTrades,
    });

    render(<TradeHistory />);

    await waitFor(() => {
      expect(screen.getByText(/page 1 of 2/i)).toBeInTheDocument();
    });
  });

  it('paginates to next page', async () => {
    const manyTrades = Array.from({ length: 15 }, (_, i) =>
      makeTrade({ id: String(i), symbol: `COIN${i}/USD` })
    );

    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => manyTrades,
    });

    render(<TradeHistory />);

    await waitFor(() => {
      expect(screen.getByText('Next')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Next'));

    await waitFor(() => {
      expect(screen.getByText(/page 2 of 2/i)).toBeInTheDocument();
    });
  });
});
