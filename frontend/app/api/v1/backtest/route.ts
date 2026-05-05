import { NextRequest, NextResponse } from 'next/server';
import { getServerApiUrl } from '@/lib/runtime';

const BACKEND_API_URL = getServerApiUrl();

interface BacktestFormBody {
  strategyName?: string;
  startDate?: string;
  endDate?: string;
  feeRate?: number;
}

interface OHLCVBar {
  datetime: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

interface BackendBacktestResponse {
  metrics: {
    total_return: number;
    annual_return: number;
    sharpe_ratio: number;
    max_drawdown: number;
    win_rate: number;
    trades_count: number;
  };
  equity_curve: number[];
}

function buildHistoricalData(startDate: Date, endDate: Date): OHLCVBar[] {
  const bars: OHLCVBar[] = [];
  const cursor = new Date(startDate);
  let close = 100;

  while (cursor <= endDate && bars.length < 730) {
    const cycle = Math.sin(bars.length / 8) * 1.4;
    const drift = bars.length * 0.015;
    const open = close;
    close = Math.max(1, open + cycle + drift / 100);
    const high = Math.max(open, close) + 1.5;
    const low = Math.max(0.1, Math.min(open, close) - 1.5);

    bars.push({
      datetime: cursor.toISOString(),
      open,
      high,
      low,
      close,
      volume: 1000 + bars.length * 17,
    });

    cursor.setUTCDate(cursor.getUTCDate() + 1);
  }

  return bars;
}

export async function POST(request: NextRequest) {
  const body = (await request.json()) as BacktestFormBody;
  const startDate = body.startDate ? new Date(body.startDate) : new Date(Date.now() - 1000 * 60 * 60 * 24 * 180);
  const endDate = body.endDate ? new Date(body.endDate) : new Date();

  if (Number.isNaN(startDate.getTime()) || Number.isNaN(endDate.getTime()) || startDate >= endDate) {
    return NextResponse.json({ error: 'Invalid backtest date range' }, { status: 400 });
  }

  const historicalData = buildHistoricalData(startDate, endDate);
  if (historicalData.length < 30) {
    return NextResponse.json({ error: 'Backtest needs at least 30 daily bars' }, { status: 400 });
  }

  const backendResponse = await fetch(`${BACKEND_API_URL}/api/v1/backtest`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      strategy_name: body.strategyName || 'SMA Crossover',
      historical_data: historicalData,
      config: {
        fee_rate: body.feeRate ?? 0.001,
        timeframe: '1d',
        fast_window: 10,
        slow_window: 30,
      },
    }),
  });

  if (!backendResponse.ok) {
    const detail = await backendResponse.text();
    return NextResponse.json({ error: 'Backend backtest failed', detail }, { status: backendResponse.status });
  }

  const result = (await backendResponse.json()) as BackendBacktestResponse;

  return NextResponse.json({
    metrics: {
      totalReturn: result.metrics.total_return,
      sharpeRatio: result.metrics.sharpe_ratio,
      maxDrawdown: result.metrics.max_drawdown,
      winRate: result.metrics.win_rate,
      totalTrades: result.metrics.trades_count,
      annualizedReturn: result.metrics.annual_return,
    },
    equityCurve: result.equity_curve.map((value, index) => ({
      timestamp: new Date(historicalData[index]?.datetime || historicalData[0].datetime).getTime(),
      value,
    })),
  });
}
