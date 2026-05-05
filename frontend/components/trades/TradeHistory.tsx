'use client';

import React, { useState, useEffect, useCallback } from 'react';

export interface Trade {
  id: string;
  symbol: string;
  side: 'BUY' | 'SELL';
  entryPrice: number;
  exitPrice: number;
  pnl: number;
  pnlPercent: number;
  timestamp: number;
  quantity?: number;
}

type SortKey = keyof Pick<Trade, 'symbol' | 'side' | 'entryPrice' | 'exitPrice' | 'pnl' | 'pnlPercent' | 'timestamp'>;

const PAGE_SIZE = 10;

/**
 * TradeHistory Component
 * Sortable, paginated table of closed trades fetched from /api/portfolio/trades.
 */
export const TradeHistory: React.FC = () => {
  const [trades, setTrades] = useState<Trade[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sortKey, setSortKey] = useState<SortKey>('timestamp');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');
  const [page, setPage] = useState(0);

  useEffect(() => {
    const fetchTrades = async () => {
      try {
        const response = await fetch('/api/portfolio/trades');
        if (!response.ok) throw new Error('Failed to fetch trades');
        const data = await response.json() as Trade[];
        setTrades(data);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error');
      } finally {
        setLoading(false);
      }
    };

    fetchTrades();
  }, []);

  const handleSort = useCallback((key: SortKey) => {
    if (key === sortKey) {
      setSortDir(d => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortKey(key);
      setSortDir('desc');
    }
    setPage(0);
  }, [sortKey]);

  const sorted = [...trades].sort((a, b) => {
    const av = a[sortKey];
    const bv = b[sortKey];
    const cmp = typeof av === 'string' ? av.localeCompare(bv as string) : (av as number) - (bv as number);
    return sortDir === 'asc' ? cmp : -cmp;
  });

  const totalPages = Math.ceil(sorted.length / PAGE_SIZE);
  const paginated = sorted.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);

  const SortHeader: React.FC<{ label: string; col: SortKey }> = ({ label, col }) => (
    <th
      className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider cursor-pointer hover:text-white select-none"
      onClick={() => handleSort(col)}
    >
      {label}
      {sortKey === col && <span className="ml-1">{sortDir === 'asc' ? 'asc' : 'desc'}</span>}
    </th>
  );

  if (loading) return <div className="p-4 text-gray-400">Loading trade history...</div>;

  return (
    <div className="bg-gray-900 rounded-lg border border-gray-700 overflow-hidden">
      <div className="px-4 py-3 border-b border-gray-700">
        <h2 className="text-white font-semibold">Trade History</h2>
      </div>

      {error && <div className="px-4 py-2 text-sm text-red-400 bg-red-900/20">{error}</div>}

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-800">
            <tr>
              <SortHeader label="Symbol" col="symbol" />
              <SortHeader label="Side" col="side" />
              <SortHeader label="Entry" col="entryPrice" />
              <SortHeader label="Exit" col="exitPrice" />
              <SortHeader label="PnL" col="pnl" />
              <SortHeader label="PnL %" col="pnlPercent" />
              <SortHeader label="Time" col="timestamp" />
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-800">
            {paginated.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-4 py-6 text-center text-gray-500">No trades found</td>
              </tr>
            ) : (
              paginated.map(trade => (
                <tr key={trade.id} className="hover:bg-gray-800/50 transition-colors">
                  <td className="px-4 py-3 text-white font-medium">{trade.symbol}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-0.5 rounded text-xs font-bold ${trade.side === 'BUY' ? 'text-green-400 bg-green-900/30' : 'text-red-400 bg-red-900/30'}`}>
                      {trade.side}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-300">${trade.entryPrice.toFixed(2)}</td>
                  <td className="px-4 py-3 text-gray-300">${trade.exitPrice.toFixed(2)}</td>
                  <td className={`px-4 py-3 font-medium ${trade.pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                    {trade.pnl >= 0 ? '+' : ''}${trade.pnl.toFixed(2)}
                  </td>
                  <td className={`px-4 py-3 font-medium ${trade.pnlPercent >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                    {trade.pnlPercent >= 0 ? '+' : ''}{trade.pnlPercent.toFixed(2)}%
                  </td>
                  <td className="px-4 py-3 text-gray-500 text-xs">
                    {new Date(trade.timestamp).toLocaleString()}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div className="px-4 py-3 border-t border-gray-700 flex items-center justify-between">
          <span className="text-xs text-gray-500">
            Page {page + 1} of {totalPages} ({trades.length} trades)
          </span>
          <div className="flex gap-2">
            <button
              className="px-3 py-1 text-xs rounded bg-gray-700 text-gray-300 hover:bg-gray-600 disabled:opacity-40"
              onClick={() => setPage(p => p - 1)}
              disabled={page === 0}
            >
              Prev
            </button>
            <button
              className="px-3 py-1 text-xs rounded bg-gray-700 text-gray-300 hover:bg-gray-600 disabled:opacity-40"
              onClick={() => setPage(p => p + 1)}
              disabled={page >= totalPages - 1}
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default TradeHistory;
