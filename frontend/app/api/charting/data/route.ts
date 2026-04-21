import { NextRequest, NextResponse } from 'next/server';

/**
 * GET /api/charting/data
 * 
 * Returns candlestick/OHLC data for charting
 * 
 * Query parameters:
 * - symbol: Trading pair (e.g., BTC/USD)
 * - timeframe: Timeframe (1m, 5m, 15m, 1h, 4h, 1d)
 * - type: Chart type (candlestick, ohlc, line, area)
 * - limit: Number of candles to return (default: 100)
 */
export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const symbol = searchParams.get('symbol') || 'BTC/USD';
    const timeframe = searchParams.get('timeframe') || '1h';
    const type = searchParams.get('type') || 'candlestick';
    const limit = parseInt(searchParams.get('limit') || '100');

    // TODO: Fetch real data from backend API or exchange
    // const response = await fetch(`${process.env.BACKEND_API_URL}/charting/data`, {
    //   params: { symbol, timeframe, type, limit },
    // });

    // Mock data for now
    const mockCandles = Array.from({ length: limit }, (_, i) => ({
      time: Math.floor(Date.now() / 1000) - (limit - i) * 3600,
      open: 100 + Math.random() * 10,
      high: 110 + Math.random() * 10,
      low: 90 + Math.random() * 10,
      close: 100 + Math.random() * 10,
      volume: 1000 + Math.random() * 5000,
    }));

    return NextResponse.json({ candles: mockCandles });
  } catch (error) {
    console.error('Error fetching chart data:', error);
    return NextResponse.json(
      { error: 'Failed to fetch chart data' },
      { status: 500 }
    );
  }
}
