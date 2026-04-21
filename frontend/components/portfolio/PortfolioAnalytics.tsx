'use client';

import React, { useState, useEffect } from 'react';
import { PortfolioAnalytics as PortfolioAnalyticsType } from '@/types/portfolio';

/**
 * PortfolioAnalytics Component
 * Displays comprehensive portfolio analytics including:
 * - Asset composition pie chart
 * - Exchange composition pie chart
 * - Strategy composition pie chart
 * - Cumulative P&L line chart
 * - Daily P&L distribution histogram
 * - Performance attribution bar chart
 * 
 * Updates at least once per minute
 */
export const PortfolioAnalytics: React.FC = () => {
  const [analytics, setAnalytics] = useState<PortfolioAnalyticsType | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchAnalytics = async () => {
      try {
        setLoading(true);
        const response = await fetch('/api/portfolio/analytics');
        if (!response.ok) {
          throw new Error('Failed to fetch portfolio analytics');
        }
        const data = await response.json();
        setAnalytics(data);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error');
      } finally {
        setLoading(false);
      }
    };

    // Fetch immediately
    fetchAnalytics();

    // Set up interval for updates (at least once per minute)
    const interval = setInterval(fetchAnalytics, 60000);

    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return <div className="portfolio-analytics loading">Loading portfolio analytics...</div>;
  }

  if (error) {
    return <div className="portfolio-analytics error">Error: {error}</div>;
  }

  if (!analytics) {
    return <div className="portfolio-analytics empty">No portfolio data available</div>;
  }

  return (
    <div className="portfolio-analytics">
      <div className="analytics-header">
        <h1>Portfolio Analytics</h1>
        <div className="summary-metrics">
          <div className="metric">
            <span className="label">Total Value</span>
            <span className="value">${analytics.totalValue.toFixed(2)}</span>
          </div>
          <div className="metric">
            <span className="label">Total P&L</span>
            <span className={`value ${analytics.totalPnL >= 0 ? 'positive' : 'negative'}`}>
              ${analytics.totalPnL.toFixed(2)}
            </span>
          </div>
          <div className="metric">
            <span className="label">Total Return</span>
            <span className={`value ${analytics.totalReturn >= 0 ? 'positive' : 'negative'}`}>
              {analytics.totalReturn.toFixed(2)}%
            </span>
          </div>
        </div>
      </div>

      <div className="analytics-grid">
        {/* Asset Composition */}
        <div className="chart-container">
          <h2>Portfolio by Asset</h2>
          <PieChart data={analytics.assetComposition} />
        </div>

        {/* Exchange Composition */}
        <div className="chart-container">
          <h2>Portfolio by Exchange</h2>
          <PieChart data={analytics.exchangeComposition} />
        </div>

        {/* Strategy Composition */}
        <div className="chart-container">
          <h2>Portfolio by Strategy</h2>
          <PieChart data={analytics.strategyComposition} />
        </div>

        {/* Cumulative P&L */}
        <div className="chart-container full-width">
          <h2>Cumulative P&L</h2>
          <LineChart data={analytics.cumulativePnL} />
        </div>

        {/* Daily P&L Distribution */}
        <div className="chart-container">
          <h2>Daily P&L Distribution</h2>
          <HistogramChart data={analytics.dailyPnLDistribution} />
        </div>

        {/* Performance Attribution */}
        <div className="chart-container">
          <h2>Performance Attribution</h2>
          <BarChart data={analytics.performanceAttribution} />
        </div>
      </div>

      <div className="analytics-footer">
        <span className="last-updated">
          Last updated: {new Date(analytics.lastUpdated).toLocaleString()}
        </span>
      </div>
    </div>
  );
};

/**
 * PieChart Component
 * Displays composition data as a pie chart
 */
const PieChart: React.FC<{ data: Array<{ name: string; value: number; percentage: number; color?: string }> }> = ({ data }) => {
  return (
    <div className="pie-chart">
      <div className="chart-placeholder">
        <svg viewBox="0 0 100 100" className="pie-svg">
          {data.map((item, index) => {
            const startAngle = data.slice(0, index).reduce((sum, d) => sum + (d.percentage / 100) * 360, 0);
            const endAngle = startAngle + (item.percentage / 100) * 360;
            const startRad = (startAngle * Math.PI) / 180;
            const endRad = (endAngle * Math.PI) / 180;
            const x1 = 50 + 40 * Math.cos(startRad);
            const y1 = 50 + 40 * Math.sin(startRad);
            const x2 = 50 + 40 * Math.cos(endRad);
            const y2 = 50 + 40 * Math.sin(endRad);
            const largeArc = endAngle - startAngle > 180 ? 1 : 0;
            const pathData = `M 50 50 L ${x1} ${y1} A 40 40 0 ${largeArc} 1 ${x2} ${y2} Z`;
            const colors = ['#3b82f6', '#ef4444', '#10b981', '#f59e0b', '#8b5cf6', '#ec4899'];
            const color = item.color || colors[index % colors.length];
            return <path key={index} d={pathData} fill={color} />;
          })}
        </svg>
      </div>
      <div className="chart-legend">
        {data.map((item, index) => (
          <div key={index} className="legend-item">
            <span className="legend-color" style={{ backgroundColor: item.color || '#3b82f6' }}></span>
            <span className="legend-label">{item.name}</span>
            <span className="legend-value">{item.percentage.toFixed(1)}%</span>
          </div>
        ))}
      </div>
    </div>
  );
};

/**
 * LineChart Component
 * Displays cumulative P&L as a line chart
 */
const LineChart: React.FC<{ data: Array<{ timestamp: number; value: number; pnl: number }> }> = ({ data }) => {
  if (data.length === 0) {
    return <div className="chart-placeholder">No data available</div>;
  }

  const minValue = Math.min(...data.map(d => d.value));
  const maxValue = Math.max(...data.map(d => d.value));
  const range = maxValue - minValue || 1;

  return (
    <div className="line-chart">
      <svg viewBox="0 0 800 300" className="chart-svg">
        {/* Grid lines */}
        {[0, 0.25, 0.5, 0.75, 1].map((ratio, i) => (
          <line
            key={`grid-${i}`}
            x1="50"
            y1={50 + ratio * 200}
            x2="750"
            y2={50 + ratio * 200}
            stroke="#e5e7eb"
            strokeWidth="1"
          />
        ))}

        {/* Line path */}
        <polyline
          points={data
            .map((d, i) => {
              const x = 50 + (i / (data.length - 1 || 1)) * 700;
              const y = 250 - ((d.value - minValue) / range) * 200;
              return `${x},${y}`;
            })
            .join(' ')}
          fill="none"
          stroke="#3b82f6"
          strokeWidth="2"
        />

        {/* Data points */}
        {data.map((d, i) => {
          const x = 50 + (i / (data.length - 1 || 1)) * 700;
          const y = 250 - ((d.value - minValue) / range) * 200;
          return <circle key={`point-${i}`} cx={x} cy={y} r="3" fill="#3b82f6" />;
        })}
      </svg>
      <div className="chart-labels">
        <span className="y-label">${maxValue.toFixed(0)}</span>
        <span className="y-label">${minValue.toFixed(0)}</span>
      </div>
    </div>
  );
};

/**
 * HistogramChart Component
 * Displays daily P&L distribution as a histogram
 */
const HistogramChart: React.FC<{ data: Array<{ date: string; pnl: number }> }> = ({ data }) => {
  if (data.length === 0) {
    return <div className="chart-placeholder">No data available</div>;
  }

  const maxPnL = Math.max(...data.map(d => Math.abs(d.pnl)));

  return (
    <div className="histogram-chart">
      <svg viewBox="0 0 800 300" className="chart-svg">
        {data.map((d, i) => {
          const barWidth = 700 / data.length;
          const x = 50 + i * barWidth;
          const height = (Math.abs(d.pnl) / maxPnL) * 200;
          const y = 250 - height;
          const color = d.pnl >= 0 ? '#10b981' : '#ef4444';
          return (
            <rect
              key={`bar-${i}`}
              x={x + barWidth * 0.1}
              y={y}
              width={barWidth * 0.8}
              height={height}
              fill={color}
            />
          );
        })}
      </svg>
    </div>
  );
};

/**
 * BarChart Component
 * Displays performance attribution as a bar chart
 */
const BarChart: React.FC<{ data: Array<{ category: string; attribution: number; percentage: number }> }> = ({ data }) => {
  if (data.length === 0) {
    return <div className="chart-placeholder">No data available</div>;
  }

  const maxAttribution = Math.max(...data.map(d => Math.abs(d.attribution)));

  return (
    <div className="bar-chart">
      <svg viewBox="0 0 800 300" className="chart-svg">
        {data.map((d, i) => {
          const barWidth = 700 / data.length;
          const x = 50 + i * barWidth;
          const height = (Math.abs(d.attribution) / maxAttribution) * 200;
          const y = 250 - height;
          const color = d.attribution >= 0 ? '#3b82f6' : '#ef4444';
          return (
            <rect
              key={`bar-${i}`}
              x={x + barWidth * 0.1}
              y={y}
              width={barWidth * 0.8}
              height={height}
              fill={color}
            />
          );
        })}
      </svg>
      <div className="chart-labels">
        {data.map((d, i) => (
          <span key={`label-${i}`} className="x-label">
            {d.category}
          </span>
        ))}
      </div>
    </div>
  );
};

export default PortfolioAnalytics;
