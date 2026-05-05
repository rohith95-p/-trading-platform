'use client';

import React, { useState } from 'react';

interface BacktestForm {
  strategyName: string;
  startDate: string;
  endDate: string;
  feeRate: number;
}

interface BacktestMetrics {
  totalReturn: number;
  sharpeRatio: number;
  maxDrawdown: number;
  winRate: number;
  totalTrades: number;
  annualizedReturn: number;
}

interface EquityPoint {
  timestamp: number;
  value: number;
}

interface BacktestResult {
  metrics: BacktestMetrics;
  equityCurve: EquityPoint[];
}

const METRIC_LABELS: Record<keyof BacktestMetrics, string> = {
  totalReturn: 'Total Return',
  sharpeRatio: 'Sharpe Ratio',
  maxDrawdown: 'Max Drawdown',
  winRate: 'Win Rate',
  totalTrades: 'Total Trades',
  annualizedReturn: 'Annualized Return',
};

/**
 * Backtesting Component
 * Form to submit a backtest and display results with metrics + equity curve.
 */
export const Backtesting: React.FC = () => {
  const [form, setForm] = useState<BacktestForm>({
    strategyName: '',
    startDate: '',
    endDate: '',
    feeRate: 0.001,
  });
  const [result, setResult] = useState<BacktestResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await fetch('/api/v1/backtest', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      });

      if (!response.ok) throw new Error(`Backtest failed: ${response.statusText}`);
      const data = await response.json() as BacktestResult;
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  const formatMetric = (key: keyof BacktestMetrics, value: number): string => {
    if (key === 'totalTrades') return value.toString();
    if (key === 'sharpeRatio') return value.toFixed(2);
    return `${value.toFixed(2)}%`;
  };

  const isPositiveMetric = (key: keyof BacktestMetrics, value: number): boolean | null => {
    if (key === 'totalTrades' || key === 'sharpeRatio') return null;
    if (key === 'maxDrawdown') return value <= 10; // low drawdown is good
    return value >= 0;
  };

  return (
    <div className="bg-gray-900 rounded-lg border border-gray-700 overflow-hidden">
      <div className="px-4 py-3 border-b border-gray-700">
        <h2 className="text-white font-semibold">Backtesting</h2>
      </div>

      <div className="p-4">
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label htmlFor="bt-strategy" className="block text-xs text-gray-400 mb-1">Strategy Name</label>
              <input
                id="bt-strategy"
                type="text"
                required
                placeholder="e.g. Momentum Strategy"
                value={form.strategyName}
                onChange={e => setForm({ ...form, strategyName: e.target.value })}
                className="w-full bg-gray-800 border border-gray-600 rounded px-3 py-2 text-white text-sm placeholder-gray-500 focus:outline-none focus:border-blue-500"
              />
            </div>
            <div>
              <label htmlFor="bt-fee" className="block text-xs text-gray-400 mb-1">Fee Rate</label>
              <input
                id="bt-fee"
                type="number"
                step="0.0001"
                min="0"
                max="0.1"
                value={form.feeRate}
                onChange={e => setForm({ ...form, feeRate: parseFloat(e.target.value) })}
                className="w-full bg-gray-800 border border-gray-600 rounded px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
              />
            </div>
            <div>
              <label htmlFor="bt-start" className="block text-xs text-gray-400 mb-1">Start Date</label>
              <input
                id="bt-start"
                type="date"
                required
                value={form.startDate}
                onChange={e => setForm({ ...form, startDate: e.target.value })}
                className="w-full bg-gray-800 border border-gray-600 rounded px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
              />
            </div>
            <div>
              <label htmlFor="bt-end" className="block text-xs text-gray-400 mb-1">End Date</label>
              <input
                id="bt-end"
                type="date"
                required
                value={form.endDate}
                onChange={e => setForm({ ...form, endDate: e.target.value })}
                className="w-full bg-gray-800 border border-gray-600 rounded px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full sm:w-auto px-6 py-2 bg-blue-600 hover:bg-blue-500 disabled:bg-blue-800 disabled:cursor-not-allowed text-white text-sm font-medium rounded transition-colors"
          >
            {loading ? 'Running Backtest...' : 'Run Backtest'}
          </button>
        </form>

        {loading && (
          <div className="mt-6 flex items-center gap-3 text-gray-400 text-sm">
            <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
            Running backtest, please wait...
          </div>
        )}

        {error && (
          <div className="mt-4 px-4 py-3 bg-red-900/20 border border-red-700 rounded text-red-400 text-sm">
            {error}
          </div>
        )}

        {result && (
          <div className="mt-6 space-y-6">
            {/* Metrics Table */}
            <div>
              <h3 className="text-white font-medium mb-3">Results</h3>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                {(Object.keys(result.metrics) as (keyof BacktestMetrics)[]).map(key => {
                  const value = result.metrics[key];
                  const positive = isPositiveMetric(key, value);
                  return (
                    <div key={key} className="bg-gray-800 rounded p-3">
                      <div className="text-xs text-gray-400 mb-1">{METRIC_LABELS[key]}</div>
                      <div className={`text-lg font-semibold ${positive === null ? 'text-white' : positive ? 'text-green-400' : 'text-red-400'}`}>
                        {formatMetric(key, value)}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Equity Curve */}
            {result.equityCurve.length > 1 && (
              <div>
                <h3 className="text-white font-medium mb-3">Equity Curve</h3>
                <EquityCurveChart data={result.equityCurve} />
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

const EquityCurveChart: React.FC<{ data: EquityPoint[] }> = ({ data }) => {
  const minVal = Math.min(...data.map(d => d.value));
  const maxVal = Math.max(...data.map(d => d.value));
  const range = maxVal - minVal || 1;
  const W = 700;
  const H = 200;
  const PAD = 40;

  const points = data
    .map((d, i) => {
      const x = PAD + (i / (data.length - 1)) * (W - PAD * 2);
      const y = H - PAD - ((d.value - minVal) / range) * (H - PAD * 2);
      return `${x},${y}`;
    })
    .join(' ');

  const isProfit = data[data.length - 1].value >= data[0].value;

  return (
    <div className="bg-gray-800 rounded p-3">
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full">
        {/* Grid lines */}
        {[0, 0.5, 1].map((r, i) => (
          <line
            key={i}
            x1={PAD} y1={PAD + r * (H - PAD * 2)}
            x2={W - PAD} y2={PAD + r * (H - PAD * 2)}
            stroke="#374151" strokeWidth="1"
          />
        ))}
        {/* Y labels */}
        <text x={PAD - 4} y={PAD + 4} fill="#9ca3af" fontSize="10" textAnchor="end">${maxVal.toFixed(0)}</text>
        <text x={PAD - 4} y={H - PAD + 4} fill="#9ca3af" fontSize="10" textAnchor="end">${minVal.toFixed(0)}</text>
        {/* Line */}
        <polyline points={points} fill="none" stroke={isProfit ? '#10b981' : '#ef4444'} strokeWidth="2" />
        {/* Start/end dots */}
        {data.length > 0 && (
          <>
            <circle cx={PAD} cy={H - PAD - ((data[0].value - minVal) / range) * (H - PAD * 2)} r="3" fill={isProfit ? '#10b981' : '#ef4444'} />
            <circle cx={W - PAD} cy={H - PAD - ((data[data.length - 1].value - minVal) / range) * (H - PAD * 2)} r="3" fill={isProfit ? '#10b981' : '#ef4444'} />
          </>
        )}
      </svg>
    </div>
  );
};

export default Backtesting;
