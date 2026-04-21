import { NextRequest, NextResponse } from 'next/server';

/**
 * GET /api/settings
 * Returns user settings
 */
export async function GET(request: NextRequest) {
  try {
    // TODO: Fetch real settings from backend
    const mockSettings = {
      userId: 'user1',
      account: {
        email: 'user@example.com',
        twoFactorEnabled: false,
      },
      trading: {
        defaultLeverage: 1,
        positionSizingMethod: 'percentage',
        maxPositionSize: 5,
        maxDailyLoss: 1000,
        maxDrawdown: 20,
      },
      notifications: {
        emailNotifications: true,
        emailFrequency: 'daily',
        alertTypes: ['price', 'signal'],
        quietHoursStart: '22:00',
        quietHoursEnd: '08:00',
      },
      display: {
        theme: 'auto',
        defaultTimeframe: '1h',
        defaultChartType: 'candlestick',
        defaultIndicators: ['EMA_20', 'RSI_14'],
        language: 'en',
      },
      createdAt: Date.now(),
      updatedAt: Date.now(),
    };

    return NextResponse.json(mockSettings);
  } catch (error) {
    console.error('Error fetching settings:', error);
    return NextResponse.json({ error: 'Failed to fetch settings' }, { status: 500 });
  }
}

/**
 * PUT /api/settings
 * Updates user settings
 */
export async function PUT(request: NextRequest) {
  try {
    const body = await request.json();

    // TODO: Save settings to backend
    const updatedSettings = {
      ...body,
      updatedAt: Date.now(),
    };

    return NextResponse.json(updatedSettings);
  } catch (error) {
    console.error('Error updating settings:', error);
    return NextResponse.json({ error: 'Failed to update settings' }, { status: 500 });
  }
}
