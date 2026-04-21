/**
 * Test endpoint to verify frontend can reach backend
 * GET /api/test
 */

export async function GET() {
  try {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL;
    
    if (!apiUrl) {
      return Response.json(
        { error: "NEXT_PUBLIC_API_URL not configured" },
        { status: 500 }
      );
    }

    const response = await fetch(`${apiUrl}/health`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      return Response.json(
        { error: `Backend returned ${response.status}` },
        { status: response.status }
      );
    }

    const data = await response.json();

    return Response.json({
      status: "success",
      message: "Frontend successfully connected to backend",
      backend: data,
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    return Response.json(
      {
        status: "error",
        message: "Failed to connect to backend",
        error: error instanceof Error ? error.message : String(error),
      },
      { status: 500 }
    );
  }
}
