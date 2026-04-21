import { NextRequest, NextResponse } from 'next/server';

/**
 * GET /api/alerts/history
 * Returns alert history
 */
export async function GET(request: NextRequest) {
  try {
    // TODO: Fetch real history from backend
    const mockHistory = [
      {
        id: '1',
        alertId: '1',
        triggeredAt: Date.now() - 3600000,
        value: 50100,
        notificationSent: true,
      },
      {
        id: '2',
        alertId: '2',
        triggeredAt: Date.now() - 7200000,
        value: 1950,
        notificationSent: true,
      },
    ];

    return NextResponse.json(mockHistory);
  } catch (error) {
    console.error('Error fetching alert history:', error);
    return NextResponse.json({ error: 'Failed to fetch alert history' }, { status: 500 });
  }
}
