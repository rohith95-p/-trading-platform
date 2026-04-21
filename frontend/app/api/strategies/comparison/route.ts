import { NextRequest, NextResponse } from 'next/server';

/**
 * GET /api/strategies/comparison
 * 
 * Returns strategy comparison data
 * 
 * Query parameters:
 * - startDate: Start date for filtering
 * - endDate: End date for filtering
 * - asset: Filter by asset
 * - exchange: Filter by exchange
 */
export async function GET(request: NextRequest) {
  try {
    // TODO: Fetch real strategy comparison data from backend
    const mockComparison = {
      strategies: [
        { id: '1', name: 'Strategy A', createdAt: Date.now(), updatedAt: Date.now() },
        { id: '2', name: 'Strategy B', createdAt: Date.now(), updatedAt: Date.now() },
        { id: '3', name: 'Strategy C', createdAt: Date.now(), updatedAt: Date.now() },
      ],
      metrics: {
        '1': {
          strategyId: '1',
          totalReturn: 25.5,
          sharpeRatio: 1.8,
          maxDrawdown: -12.3,
          winRate: 62.5,
          trades: 48,
          avgWin: 450,
          avgLoss: -280,
          profitFactor: 2.1,
        },
        '2': {
          strategyId: '2',
          totalReturn: 18.2,
          sharpeRatio: 1.5,
          maxDrawdown: -15.8,
          winRate: 58.3,
          trades: 36,
          avgWin: 380,
          avgLoss: -320,
          profitFactor: 1.8,
        },
        '3': {
          strategyId: '3',
          totalReturn: 32.1,
          sharpeRatio: 2.1,
          maxDrawdown: -10.5,
          winRate: 65.2,
          trades: 52,
          avgWin: 520,
          avgLoss: -250,
          profitFactor: 2.4,
        },
      },
      equityCurves: {
        '1': Array.from({ length: 100 }, (_, i) => ({
          time: Date.now() - (100 - i) * 86400000,
          value: 100000 + i * 255,
        })),
        '2': Array.from({ length: 100 }, (_, i) => ({
          time: Date.now() - (100 - i) * 86400000,
          value: 100000 + i * 182,
        })),
        '3': Array.from({ length: 100 }, (_, i) => ({
          time: Date.now() - (100 - i) * 86400000,
          value: 100000 + i * 321,
        })),
      },
      monthlyReturns: {
        '1': {
          'Jan': 5.2,
          'Feb': 3.1,
          'Mar': 4.8,
          'Apr': 2.9,
          'May': 6.1,
          'Jun': 3.4,
        },
        '2': {
          'Jan': 3.8,
          'Feb': 2.1,
          'Mar': 3.2,
          'Apr': 1.9,
          'May': 4.2,
          'Jun': 3.0,
        },
        '3': {
          'Jan': 6.5,
          'Feb': 4.2,
          'Mar': 5.8,
          'Apr': 4.1,
          'May': 7.3,
          'Jun': 4.2,
        },
      },
      drawdowns: {
        '1': [
          { start: Date.now() - 50 * 86400000, end: Date.now() - 40 * 86400000, value: 8.5, duration: 10 },
          { start: Date.now() - 30 * 86400000, end: Date.now() - 25 * 86400000, value: 12.3, duration: 5 },
        ],
        '2': [
          { start: Date.now() - 50 * 86400000, end: Date.now() - 38 * 86400000, value: 12.1, duration: 12 },
          { start: Date.now() - 25 * 86400000, end: Date.now() - 18 * 86400000, value: 15.8, duration: 7 },
        ],
        '3': [
          { start: Date.now() - 50 * 86400000, end: Date.now() - 42 * 86400000, value: 7.2, duration: 8 },
          { start: Date.now() - 28 * 86400000, end: Date.now() - 23 * 86400000, value: 10.5, duration: 5 },
        ],
      },
    };

    return NextResponse.json(mockComparison);
  } catch (error) {
    console.error('Error fetching strategy comparison:', error);
    return NextResponse.json(
      { error: 'Failed to fetch strategy comparison' },
      { status: 500 }
    );
  }
}
