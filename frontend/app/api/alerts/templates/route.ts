import { NextRequest, NextResponse } from 'next/server';

/**
 * GET /api/alerts/templates
 * Returns alert templates
 */
export async function GET(request: NextRequest) {
  try {
    // TODO: Fetch real templates from backend
    const mockTemplates = [
      {
        id: '1',
        name: 'Price Breakout',
        description: 'Alert when price breaks above resistance',
        condition: 'price_above',
        threshold: 0,
        notificationMethod: 'email',
        createdAt: Date.now(),
      },
      {
        id: '2',
        name: 'Price Support',
        description: 'Alert when price breaks below support',
        condition: 'price_below',
        threshold: 0,
        notificationMethod: 'in_app',
        createdAt: Date.now(),
      },
    ];

    return NextResponse.json(mockTemplates);
  } catch (error) {
    console.error('Error fetching templates:', error);
    return NextResponse.json({ error: 'Failed to fetch templates' }, { status: 500 });
  }
}
