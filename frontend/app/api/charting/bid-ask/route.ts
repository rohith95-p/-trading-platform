import { NextRequest, NextResponse } from 'next/server';

/**
 * GET /api/charting/bid-ask
 * 
 * Returns bid-ask spread data
 * 
 * Query parameters:
 * - symbol: Trading pair (e.g., BTC/USD)
 */
export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const symbol = searchParams.get('symbol') || 'BTC/USD';

    // TODO: Fetch real bid-ask data from exchange
    // const response = await fetch(`${process.env.BACKEND_API_URL}/charting/bid-ask`, {
    //   params: { symbol },
    // });

    // Mock data for now
    const bid = 99.95 + Math.random() * 0.1;
    const ask = bid + 0.1 + Math.random() * 0.05;
    const spread = ask - bid;
    const spreadPercentage = (spread / bid) * 100;

    const mockBidAsk = {
      bid,
      ask,
      spread,
      spreadPercentage,
    };

    return NextResponse.json(mockBidAsk);
  } catch (error) {
    console.error('Error fetching bid-ask spread:', error);
    return NextResponse.json(
      { error: 'Failed to fetch bid-ask spread' },
      { status: 500 }
    );
  }
}
