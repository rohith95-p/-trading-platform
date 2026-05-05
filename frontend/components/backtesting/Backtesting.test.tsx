import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { Backtesting } from './Backtesting';

global.fetch = jest.fn();

const mockResult = {
  metrics: {
    totalReturn: 25.5,
    sharpeRatio: 1.8,
    maxDrawdown: 8.2,
    winRate: 62.5,
    totalTrades: 48,
    annualizedReturn: 30.1,
  },
  equityCurve: [
    { timestamp: 1000, value: 10000 },
    { timestamp: 2000, value: 10500 },
    { timestamp: 3000, value: 11200 },
    { timestamp: 4000, value: 12550 },
  ],
};

const fillForm = () => {
  fireEvent.change(screen.getByPlaceholderText(/momentum strategy/i), {
    target: { value: 'Test Strategy' },
  });
  fireEvent.change(screen.getByLabelText(/start date/i), {
    target: { value: '2024-01-01' },
  });
  fireEvent.change(screen.getByLabelText(/end date/i), {
    target: { value: '2024-06-01' },
  });
};

// Note: getByLabelText requires htmlFor/id associations which are set in the component

describe('Backtesting', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders the form', () => {
    render(<Backtesting />);
    expect(screen.getByText('Backtesting')).toBeInTheDocument();
    expect(screen.getByText('Run Backtest')).toBeInTheDocument();
    expect(screen.getByLabelText(/strategy name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/fee rate/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/start date/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/end date/i)).toBeInTheDocument();
  });

  it('shows loading state while running', async () => {
    (global.fetch as jest.Mock).mockImplementation(() => new Promise(() => {}));

    render(<Backtesting />);
    fillForm();
    fireEvent.click(screen.getByText('Run Backtest'));

    await waitFor(() => {
      expect(screen.getByText(/running backtest/i)).toBeInTheDocument();
    });
  });

  it('displays results after successful backtest', async () => {
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => mockResult,
    });

    render(<Backtesting />);
    fillForm();
    fireEvent.click(screen.getByText('Run Backtest'));

    await waitFor(() => {
      expect(screen.getByText('Total Return')).toBeInTheDocument();
      expect(screen.getByText('Sharpe Ratio')).toBeInTheDocument();
      expect(screen.getByText('Win Rate')).toBeInTheDocument();
      expect(screen.getByText('Total Trades')).toBeInTheDocument();
    });
  });

  it('shows error on failed backtest', async () => {
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: false,
      statusText: 'Internal Server Error',
    });

    render(<Backtesting />);
    fillForm();
    fireEvent.click(screen.getByText('Run Backtest'));

    await waitFor(() => {
      expect(screen.getByText(/backtest failed/i)).toBeInTheDocument();
    });
  });

  it('calls POST /api/v1/backtest with form data', async () => {
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => mockResult,
    });

    render(<Backtesting />);
    fillForm();
    fireEvent.click(screen.getByText('Run Backtest'));

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        '/api/v1/backtest',
        expect.objectContaining({
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
        })
      );
    });

    const body = JSON.parse((global.fetch as jest.Mock).mock.calls[0][1].body as string);
    expect(body.strategyName).toBe('Test Strategy');
    expect(body.startDate).toBe('2024-01-01');
    expect(body.endDate).toBe('2024-06-01');
  });

  it('renders equity curve chart when results available', async () => {
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => mockResult,
    });

    render(<Backtesting />);
    fillForm();
    fireEvent.click(screen.getByText('Run Backtest'));

    await waitFor(() => {
      expect(screen.getByText('Equity Curve')).toBeInTheDocument();
    });
  });
});
