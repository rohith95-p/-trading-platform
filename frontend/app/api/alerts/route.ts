import { NextRequest, NextResponse } from 'next/server';

/**
 * GET /api/alerts
 * Returns user's alerts
 */
export async function GET(request: NextRequest) {
  try {
    // TODO: Fetch real alerts from backend
    const mockAlerts = [
      {
        id: '1',
        userId: 'user1',
        asset: 'BTC/USD',
        condition: 'price_above',
        threshold: 50000,
        notificationMethod: 'email',
        status: 'armed',
        createdAt: Date.now(),
      },
      {
        id: '2',
        userId: 'user1',
        asset: 'ETH/USD',
        condition: 'price_below',
        threshold: 2000,
        notificationMethod: 'in_app',
        status: 'armed',
        createdAt: Date.now(),
      },
    ];

    return NextResponse.json(mockAlerts);
  } catch (error) {
    console.error('Error fetching alerts:', error);
    return NextResponse.json({ error: 'Failed to fetch alerts' }, { status: 500 });
  }
}

/**
 * POST /api/alerts
 * Creates a new alert
 */
export async function POST(request: NextRequest) {
  try {
    const body = await request.json();

    // TODO: Save alert to backend
    const newAlert = {
      id: Math.random().toString(36).substr(2, 9),
      userId: 'user1',
      ...body,
      status: 'armed',
      createdAt: Date.now(),
    };

    return NextResponse.json(newAlert, { status: 201 });
  } catch (error) {
    console.error('Error creating alert:', error);
    return NextResponse.json({ error: 'Failed to create alert' }, { status: 500 });
  }
}
