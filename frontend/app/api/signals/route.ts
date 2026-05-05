import { NextRequest, NextResponse } from 'next/server';
import { getServerApiUrl } from '@/lib/runtime';

const BACKEND_API_URL = getServerApiUrl();

type SignalDirection = 'long' | 'short' | 'neutral' | 'buy' | 'sell' | 'hold';

interface BackendSignal {
  id: string;
  asset: string;
  direction: SignalDirection;
  confidence: number | string;
  timestamp: string;
  source?: string;
}

function mapDirection(direction: SignalDirection) {
  if (direction === 'long' || direction === 'buy') return 'BUY';
  if (direction === 'short' || direction === 'sell') return 'SELL';
  return 'HOLD';
}

export async function GET(request: NextRequest) {
  const limit = request.nextUrl.searchParams.get('limit') || '50';
  const backendResponse = await fetch(`${BACKEND_API_URL}/api/v1/intelligence/signals?limit=${encodeURIComponent(limit)}`, {
    cache: 'no-store',
  });

  if (!backendResponse.ok) {
    const detail = await backendResponse.text();
    return NextResponse.json({ error: 'Failed to fetch signals', detail }, { status: backendResponse.status });
  }

  const data = (await backendResponse.json()) as { signals?: BackendSignal[] };
  const signals = (data.signals || []).map(signal => ({
    id: signal.id,
    symbol: signal.asset,
    type: mapDirection(signal.direction),
    confidence: Number(signal.confidence),
    timestamp: new Date(signal.timestamp).getTime(),
    strategy: signal.source,
  }));

  return NextResponse.json(signals);
}
