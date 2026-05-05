import { NextRequest, NextResponse } from 'next/server';
import { getServerApiUrl } from '@/lib/runtime';

const BACKEND_API_URL = getServerApiUrl();

interface BackendTrade {
  id: string;
  symbol: string;
  side: string;
  price: number | string;
  size: number | string;
  pnl?: number | string | null;
  timestamp: string;
}

export async function GET(request: NextRequest) {
  const limit = request.nextUrl.searchParams.get('limit') || '100';
  const backendResponse = await fetch(`${BACKEND_API_URL}/trading/trades?limit=${encodeURIComponent(limit)}`, {
    cache: 'no-store',
  });

  if (!backendResponse.ok) {
    const detail = await backendResponse.text();
    return NextResponse.json({ error: 'Failed to fetch trades', detail }, { status: backendResponse.status });
  }

  const data = (await backendResponse.json()) as { trades?: BackendTrade[] };
  const trades = (data.trades || []).map(trade => {
    const price = Number(trade.price);
    const size = Number(trade.size);
    const pnl = Number(trade.pnl || 0);
    const notional = Math.abs(price * size);

    return {
      id: trade.id,
      symbol: trade.symbol,
      side: trade.side.toLowerCase() === 'sell' ? 'SELL' : 'BUY',
      entryPrice: price,
      exitPrice: price,
      pnl,
      pnlPercent: notional > 0 ? (pnl / notional) * 100 : 0,
      timestamp: new Date(trade.timestamp).getTime(),
      quantity: size,
    };
  });

  return NextResponse.json(trades);
}
