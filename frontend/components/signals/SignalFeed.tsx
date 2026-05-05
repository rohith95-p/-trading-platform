'use client';

import React, { useState, useEffect } from 'react';

export type SignalType = 'BUY' | 'SELL' | 'HOLD';

export interface Signal {
  id: string;
  symbol: string;
  type: SignalType;
  confidence: number; // 0-1
  timestamp: number;
  strategy?: string;
}

const SIGNAL_COLORS: Record<SignalType, string> = {
  BUY: 'text-green-400 bg-green-900/30 border-green-700',
  SELL: 'text-red-400 bg-red-900/30 border-red-700',
  HOLD: 'text-gray-400 bg-gray-800/30 border-gray-600',
};

/**
 * SignalFeed Component
 * Displays real-time trading signals (BUY/SELL/HOLD) with auto-refresh every 1 second.
 */
export const SignalFeed: React.FC = () => {
  const [signals, setSignals] = useState<Signal[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchSignals = async () => {
      try {
        const response = await fetch('/api/signals');
        if (!response.ok) throw new Error('Failed to fetch signals');
        const data = await response.json() as Signal[];
        setSignals(data);
        setError(null);
      } catch (err) {
        setSignals([]);
        setError(err instanceof Error ? err.message : 'Unknown error');
      } finally {
        setLoading(false);
      }
    };

    fetchSignals();
    const interval = setInterval(fetchSignals, 1000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return <div className="p-4 text-gray-400">Loading signals...</div>;
  }

  return (
    <div className="bg-gray-900 rounded-lg border border-gray-700 overflow-hidden">
      <div className="px-4 py-3 border-b border-gray-700 flex items-center justify-between">
        <h2 className="text-white font-semibold">Signal Feed</h2>
        <span className="flex items-center gap-1.5 text-xs text-green-400">
          <span className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
          Live
        </span>
      </div>

      {error && (
        <div className="px-4 py-2 text-sm text-red-400 bg-red-900/20">{error}</div>
      )}

      {signals.length === 0 ? (
        <div className="px-4 py-6 text-center text-gray-500 text-sm">No signals available</div>
      ) : (
        <div className="divide-y divide-gray-800">
          {signals.map(signal => (
            <div key={signal.id} className="px-4 py-3 flex items-center justify-between hover:bg-gray-800/50 transition-colors">
              <div className="flex items-center gap-3">
                <span className={`px-2 py-0.5 rounded border text-xs font-bold ${SIGNAL_COLORS[signal.type]}`}>
                  {signal.type}
                </span>
                <div>
                  <div className="text-white font-medium text-sm">{signal.symbol}</div>
                  {signal.strategy && (
                    <div className="text-gray-500 text-xs">{signal.strategy}</div>
                  )}
                </div>
              </div>
              <div className="text-right">
                <div className="text-white text-sm">{(signal.confidence * 100).toFixed(0)}%</div>
                <div className="text-gray-500 text-xs">
                  {new Date(signal.timestamp).toLocaleTimeString()}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default SignalFeed;
