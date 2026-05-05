import { NextRequest, NextResponse } from 'next/server';

export const dynamic = 'force-dynamic';

/**
 * GET /api/charting/orderbook
 * 
 * Returns order book data for display
 * 
 * Query parameters:
 * - symbol: Trading pair (e.g., BTC/USD)
 * - depth: Number of levels to return (default: 10)
 */
export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const symbol = searchParams.get('symbol') || 'BTC/USD';
    const depth = parseInt(searchParams.get('depth') || '10');

    // TODO: Fetch real order book data from exchange
    // const response = await fetch(`${process.env.BACKEND_API_URL}/charting/orderbook`, {
    //   params: { symbol, depth },
    // });

    // Mock data for now
    const mockOrderBook = {
      bids: Array.from({ length: depth }, (_, i) => ({
        price: 99.9 - i * 0.1,
        quantity: Math.random() * 5,
        side: 'bid',
      })),
      asks: Array.from({ length: depth }, (_, i) => ({
        price: 100.1 + i * 0.1,
        quantity: Math.random() * 5,
        side: 'ask',
      })),
      timestamp: Date.now(),
    };

    return NextResponse.json(mockOrderBook);
  } catch (error) {
    console.error('Error fetching order book:', error);
    return NextResponse.json(
      { error: 'Failed to fetch order book' },
      { status: 500 }
    );
  }
}
