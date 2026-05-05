'use client';

import React, { useState, useEffect } from 'react';

export interface Position {
  id: string;
  symbol: string;
  size: number;
  entryPrice: number;
  currentPrice: number;
  unrealizedPnl: number;
  unrealizedPnlPercent: number;
  side?: 'LONG' | 'SHORT';
}

/**
 * Positions Component
 * Displays open positions with unrealized PnL, auto-refreshes every 1 second.
 */
export const Positions: React.FC = () => {
  const [positions, setPositions] = useState<Position[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchPositions = async () => {
      try {
        const response = await fetch('/api/portfolio/positions');
        if (!response.ok) throw new Error('Failed to fetch positions');
        const data = await response.json() as Position[];
        setPositions(data);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error');
      } finally {
        setLoading(false);
      }
    };

    fetchPositions();
    const interval = setInterval(fetchPositions, 1000);
    return () => clearInterval(interval);
  }, []);

  const totalUnrealizedPnl = positions.reduce((sum, p) => sum + p.unrealizedPnl, 0);

  if (loading) return <div className="p-4 text-gray-400">Loading positions...</div>;

  return (
    <div className="bg-gray-900 rounded-lg border border-gray-700 overflow-hidden">
      <div className="px-4 py-3 border-b border-gray-700 flex items-center justify-between">
        <h2 className="text-white font-semibold">Open Positions</h2>
        <div className="flex items-center gap-3">
          {positions.length > 0 && (
            <span className={`text-sm font-medium ${totalUnrealizedPnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
              Total PnL: {totalUnrealizedPnl >= 0 ? '+' : ''}${totalUnrealizedPnl.toFixed(2)}
            </span>
          )}
          <span className="flex items-center gap-1.5 text-xs text-green-400">
            <span className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
            Live
          </span>
        </div>
      </div>

      {error && <div className="px-4 py-2 text-sm text-red-400 bg-red-900/20">{error}</div>}

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-800">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Symbol</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Side</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Size</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Entry</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Current</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Unrealized PnL</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-800">
            {positions.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-4 py-6 text-center text-gray-500">No open positions</td>
              </tr>
            ) : (
              positions.map(pos => (
                <tr key={pos.id} className="hover:bg-gray-800/50 transition-colors">
                  <td className="px-4 py-3 text-white font-medium">{pos.symbol}</td>
                  <td className="px-4 py-3">
                    {pos.side && (
                      <span className={`px-2 py-0.5 rounded text-xs font-bold ${pos.side === 'LONG' ? 'text-green-400 bg-green-900/30' : 'text-red-400 bg-red-900/30'}`}>
                        {pos.side}
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-gray-300">{pos.size}</td>
                  <td className="px-4 py-3 text-gray-300">${pos.entryPrice.toFixed(2)}</td>
                  <td className="px-4 py-3 text-gray-300">${pos.currentPrice.toFixed(2)}</td>
                  <td className="px-4 py-3">
                    <div className={`font-medium ${pos.unrealizedPnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                      {pos.unrealizedPnl >= 0 ? '+' : ''}${pos.unrealizedPnl.toFixed(2)}
                    </div>
                    <div className={`text-xs ${pos.unrealizedPnlPercent >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                      {pos.unrealizedPnlPercent >= 0 ? '+' : ''}{pos.unrealizedPnlPercent.toFixed(2)}%
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default Positions;
