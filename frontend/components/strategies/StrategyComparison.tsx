'use client';

import React, { useState, useEffect } from 'react';
import { StrategyComparison as StrategyComparisonType } from '@/types/strategy';

/**
 * StrategyComparison Component
 * Displays side-by-side comparison of multiple strategies with:
 * - Comparison table with metrics
 * - Filtering and sorting
 * - Equity curves chart
 * - Monthly returns heatmap
 * - Drawdown visualization
 * - CSV export
 */
export const StrategyComparison: React.FC = () => {
  const [comparison, setComparison] = useState<StrategyComparisonType | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sortBy, setSortBy] = useState<string>('totalReturn');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [dateRange, setDateRange] = useState({ start: '', end: '' });
  const [selectedAsset, setSelectedAsset] = useState('');
  const [selectedExchange, setSelectedExchange] = useState('');

  useEffect(() => {
    const fetchComparison = async () => {
      try {
        setLoading(true);
        const params = new URLSearchParams();
        if (dateRange.start) params.append('startDate', dateRange.start);
        if (dateRange.end) params.append('endDate', dateRange.end);
        if (selectedAsset) params.append('asset', selectedAsset);
        if (selectedExchange) params.append('exchange', selectedExchange);

        const response = await fetch(`/api/strategies/comparison?${params}`);
        if (!response.ok) {
          throw new Error('Failed to fetch strategy comparison');
        }
        const data = await response.json();
        setComparison(data);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error');
      } finally {
        setLoading(false);
      }
    };

    fetchComparison();
  }, [dateRange, selectedAsset, selectedExchange]);

  const handleExportCSV = () => {
    if (!comparison) return;

    const headers = ['Strategy', 'Total Return %', 'Sharpe Ratio', 'Max Drawdown %', 'Win Rate %', 'Trades'];
    const rows = comparison.strategies.map(strategy => {
      const metrics = comparison.metrics[strategy.id];
      return [
        strategy.name,
        metrics.totalReturn.toFixed(2),
        metrics.sharpeRatio.toFixed(2),
        metrics.maxDrawdown.toFixed(2),
        metrics.winRate.toFixed(2),
        metrics.trades,
      ];
    });

    const csv = [headers, ...rows].map(row => row.join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'strategy-comparison.csv';
    a.click();
  };

  const sortedStrategies = comparison
    ? [...comparison.strategies].sort((a, b) => {
        const metricsA = comparison.metrics[a.id];
        const metricsB = comparison.metrics[b.id];
        let valueA = 0;
        let valueB = 0;

        switch (sortBy) {
          case 'totalReturn':
            valueA = metricsA.totalReturn;
            valueB = metricsB.totalReturn;
            break;
          case 'sharpeRatio':
            valueA = metricsA.sharpeRatio;
            valueB = metricsB.sharpeRatio;
            break;
          case 'maxDrawdown':
            valueA = metricsA.maxDrawdown;
            valueB = metricsB.maxDrawdown;
            break;
          case 'winRate':
            valueA = metricsA.winRate;
            valueB = metricsB.winRate;
            break;
          case 'trades':
            valueA = metricsA.trades;
            valueB = metricsB.trades;
            break;
          default:
            return 0;
        }

        return sortOrder === 'asc' ? valueA - valueB : valueB - valueA;
      })
    : [];

  if (loading) {
    return <div className="strategy-comparison loading">Loading strategy comparison...</div>;
  }

  if (error) {
    return <div className="strategy-comparison error">Error: {error}</div>;
  }

  if (!comparison) {
    return <div className="strategy-comparison empty">No strategies to compare</div>;
  }

  return (
    <div className="strategy-comparison">
      <div className="comparison-header">
        <h1>Strategy Comparison</h1>
        <button className="export-btn" onClick={handleExportCSV}>
          📥 Export CSV
        </button>
      </div>

      <div className="filters">
        <div className="filter-group">
          <label>Date Range</label>
          <input
            type="date"
            value={dateRange.start}
            onChange={e => setDateRange({ ...dateRange, start: e.target.value })}
          />
          <input
            type="date"
            value={dateRange.end}
            onChange={e => setDateRange({ ...dateRange, end: e.target.value })}
          />
        </div>
        <div className="filter-group">
          <label>Asset</label>
          <input
            type="text"
            placeholder="Filter by asset"
            value={selectedAsset}
            onChange={e => setSelectedAsset(e.target.value)}
          />
        </div>
        <div className="filter-group">
          <label>Exchange</label>
          <input
            type="text"
            placeholder="Filter by exchange"
            value={selectedExchange}
            onChange={e => setSelectedExchange(e.target.value)}
          />
        </div>
      </div>

      <div className="comparison-table-container">
        <table className="comparison-table">
          <thead>
            <tr>
              <th>Strategy</th>
              <th
                onClick={() => {
                  setSortBy('totalReturn');
                  setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
                }}
                className={sortBy === 'totalReturn' ? 'active' : ''}
              >
                Total Return % {sortBy === 'totalReturn' && (sortOrder === 'asc' ? '↑' : '↓')}
              </th>
              <th
                onClick={() => {
                  setSortBy('sharpeRatio');
                  setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
                }}
                className={sortBy === 'sharpeRatio' ? 'active' : ''}
              >
                Sharpe Ratio {sortBy === 'sharpeRatio' && (sortOrder === 'asc' ? '↑' : '↓')}
              </th>
              <th
                onClick={() => {
                  setSortBy('maxDrawdown');
                  setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
                }}
                className={sortBy === 'maxDrawdown' ? 'active' : ''}
              >
                Max Drawdown % {sortBy === 'maxDrawdown' && (sortOrder === 'asc' ? '↑' : '↓')}
              </th>
              <th
                onClick={() => {
                  setSortBy('winRate');
                  setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
                }}
                className={sortBy === 'winRate' ? 'active' : ''}
              >
                Win Rate % {sortBy === 'winRate' && (sortOrder === 'asc' ? '↑' : '↓')}
              </th>
              <th
                onClick={() => {
                  setSortBy('trades');
                  setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
                }}
                className={sortBy === 'trades' ? 'active' : ''}
              >
                Trades {sortBy === 'trades' && (sortOrder === 'asc' ? '↑' : '↓')}
              </th>
            </tr>
          </thead>
          <tbody>
            {sortedStrategies.map(strategy => {
              const metrics = comparison.metrics[strategy.id];
              return (
                <tr key={strategy.id}>
                  <td className="strategy-name">{strategy.name}</td>
                  <td className={metrics.totalReturn >= 0 ? 'positive' : 'negative'}>
                    {metrics.totalReturn.toFixed(2)}%
                  </td>
                  <td>{metrics.sharpeRatio.toFixed(2)}</td>
                  <td className="negative">{metrics.maxDrawdown.toFixed(2)}%</td>
                  <td>{metrics.winRate.toFixed(2)}%</td>
                  <td>{metrics.trades}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div className="comparison-charts">
        <div className="chart-container">
          <h2>Equity Curves</h2>
          <EquityCurvesChart data={comparison.equityCurves} strategies={comparison.strategies} />
        </div>

        <div className="chart-container">
          <h2>Monthly Returns Heatmap</h2>
          <MonthlyReturnsHeatmap data={comparison.monthlyReturns} strategies={comparison.strategies} />
        </div>

        <div className="chart-container">
          <h2>Drawdown Periods</h2>
          <DrawdownChart data={comparison.drawdowns} strategies={comparison.strategies} />
        </div>
      </div>
    </div>
  );
};

/**
 * EquityCurvesChart Component
 */
const EquityCurvesChart: React.FC<{
  data: Record<string, Array<{ time: number; value: number }>>;
  strategies: Array<{ id: string; name: string }>;
}> = ({ data, strategies }) => {
  const colors = ['#3b82f6', '#ef4444', '#10b981', '#f59e0b', '#8b5cf6', '#ec4899'];

  return (
    <svg viewBox="0 0 800 300" className="chart-svg">
      {strategies.map((strategy, idx) => {
        const curveData = data[strategy.id] || [];
        if (curveData.length === 0) return null;

        const minValue = Math.min(...curveData.map(d => d.value));
        const maxValue = Math.max(...curveData.map(d => d.value));
        const range = maxValue - minValue || 1;

        return (
          <polyline
            key={strategy.id}
            points={curveData
              .map((d, i) => {
                const x = 50 + (i / (curveData.length - 1 || 1)) * 700;
                const y = 250 - ((d.value - minValue) / range) * 200;
                return `${x},${y}`;
              })
              .join(' ')}
            fill="none"
            stroke={colors[idx % colors.length]}
            strokeWidth="2"
          />
        );
      })}
    </svg>
  );
};

/**
 * MonthlyReturnsHeatmap Component
 */
const MonthlyReturnsHeatmap: React.FC<{
  data: Record<string, Record<string, number>>;
  strategies: Array<{ id: string; name: string }>;
}> = ({ data, strategies }) => {
  return (
    <div className="heatmap">
      {strategies.map(strategy => {
        const monthlyData = data[strategy.id] || {};
        const months = Object.keys(monthlyData).sort();

        return (
          <div key={strategy.id} className="heatmap-row">
            <div className="heatmap-label">{strategy.name}</div>
            <div className="heatmap-cells">
              {months.map(month => {
                const value = monthlyData[month];
                const intensity = Math.min(Math.abs(value) / 10, 1);
                const color = value >= 0
                  ? `rgba(16, 185, 129, ${intensity})`
                  : `rgba(239, 68, 68, ${intensity})`;

                return (
                  <div
                    key={month}
                    className="heatmap-cell"
                    style={{ backgroundColor: color }}
                    title={`${month}: ${value.toFixed(2)}%`}
                  >
                    {value.toFixed(0)}%
                  </div>
                );
              })}
            </div>
          </div>
        );
      })}
    </div>
  );
};

/**
 * DrawdownChart Component
 */
const DrawdownChart: React.FC<{
  data: Record<string, Array<{ start: number; end: number; value: number }>>;
  strategies: Array<{ id: string; name: string }>;
}> = ({ data, strategies }) => {
  return (
    <div className="drawdown-chart">
      {strategies.map(strategy => {
        const drawdowns = data[strategy.id] || [];
        const maxDrawdown = Math.max(...drawdowns.map(d => d.value), 0);

        return (
          <div key={strategy.id} className="drawdown-row">
            <div className="drawdown-label">{strategy.name}</div>
            <div className="drawdown-bars">
              {drawdowns.slice(0, 10).map((dd, i) => (
                <div
                  key={i}
                  className="drawdown-bar"
                  style={{
                    height: `${(dd.value / maxDrawdown) * 100}%`,
                  }}
                  title={`Drawdown: ${dd.value.toFixed(2)}%`}
                />
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
};

export default StrategyComparison;
