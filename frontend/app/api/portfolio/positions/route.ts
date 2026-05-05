import { NextResponse } from 'next/server';
import { getServerApiUrl } from '@/lib/runtime';

const BACKEND_API_URL = getServerApiUrl();

interface BackendPosition {
  id: string;
  symbol: string;
  side?: string;
  size: number;
  entry_price: number;
  current_price: number;
  pnl: number;
  pnl_percent: number;
}

export async function GET() {
  const backendResponse = await fetch(`${BACKEND_API_URL}/trading/positions`, {
    cache: 'no-store',
  });

  if (!backendResponse.ok) {
    const detail = await backendResponse.text();
    return NextResponse.json({ error: 'Failed to fetch positions', detail }, { status: backendResponse.status });
  }

  const data = (await backendResponse.json()) as { positions?: Record<string, BackendPosition[]> };
  const positions = Object.values(data.positions || {}).flat().map(position => ({
    id: position.id,
    symbol: position.symbol,
    size: Number(position.size),
    entryPrice: Number(position.entry_price),
    currentPrice: Number(position.current_price),
    unrealizedPnl: Number(position.pnl),
    unrealizedPnlPercent: Number(position.pnl_percent),
    side: position.side?.toUpperCase() === 'SHORT' ? 'SHORT' : 'LONG',
  }));

  return NextResponse.json(positions);
}
