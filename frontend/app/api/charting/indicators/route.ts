import { NextRequest, NextResponse } from 'next/server';

/**
 * GET /api/charting/indicators
 * 
 * Returns technical indicator data for charting
 * 
 * Query parameters:
 * - symbol: Trading pair (e.g., BTC/USD)
 * - timeframe: Timeframe (1m, 5m, 15m, 1h, 4h, 1d)
 * - indicators: Comma-separated list of indicators (e.g., EMA_20,RSI_14,MACD)
 */
export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const symbol = searchParams.get('symbol') || 'BTC/USD';
    const timeframe = searchParams.get('timeframe') || '1h';
    const indicatorsParam = searchParams.get('indicators') || '';
    const indicators = indicatorsParam.split(',').filter(i => i);

    // TODO: Fetch real indicator data from backend API
    // const response = await fetch(`${process.env.BACKEND_API_URL}/charting/indicators`, {
    //   params: { symbol, timeframe, indicators },
    // });

    // Mock data for now
    const mockIndicators = indicators.map((indicator, idx) => {
      const colors = ['#3b82f6', '#ef4444', '#10b981', '#f59e0b', '#8b5cf6'];
      return {
        name: indicator,
        type: 'line',
        data: Array.from({ length: 100 }, (_, i) => ({
          time: Math.floor(Date.now() / 1000) - (100 - i) * 3600,
          value: 50 + Math.random() * 50,
        })),
        color: colors[idx % colors.length],
      };
    });

    return NextResponse.json({ indicators: mockIndicators });
  } catch (error) {
    console.error('Error fetching indicators:', error);
    return NextResponse.json(
      { error: 'Failed to fetch indicators' },
      { status: 500 }
    );
  }
}
