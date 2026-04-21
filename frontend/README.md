# Frontend - Unified Trading Intelligence Platform

This directory contains the Next.js 14 frontend application for the Unified Trading Intelligence Platform Phase 1 MVP.

## Technology Stack

- **Framework**: Next.js 14 (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS (to be configured)
- **State Management**: React Context + Custom Hooks
- **API Communication**: REST API + WebSocket
- **Deployment**: Vercel

## Directory Structure

```
frontend/
├── app/                    # Next.js 14 App Router pages
│   ├── layout.tsx         # Root layout
│   ├── page.tsx           # Home page
│   ├── dashboard/         # Dashboard pages
│   ├── auth/              # Authentication pages
│   ├── strategies/        # Strategy management
│   └── api-keys/          # API key management
│
├── components/            # React components
│   ├── portfolio/         # Portfolio monitoring components
│   ├── signals/           # Signal feed components
│   ├── trades/            # Trade history components
│   ├── positions/         # Position tracking components
│   ├── backtesting/       # Backtesting UI components
│   ├── common/            # Shared/reusable components
│   └── layout/            # Layout components
│
├── hooks/                 # Custom React hooks
│   ├── usePortfolio.ts   # Portfolio data hook
│   ├── useSignals.ts     # Signal feed hook
│   ├── useTrades.ts      # Trade history hook
│   ├── usePositions.ts   # Positions hook
│   └── useWebSocket.ts   # WebSocket connection hook
│
├── lib/                   # Utility functions and libraries
│   ├── api.ts            # API client
│   ├── websocket.ts      # WebSocket client
│   ├── utils.ts          # General utilities
│   ├── formatters.ts     # Data formatting
│   └── validators.ts     # Input validation
│
├── types/                 # TypeScript type definitions
│   ├── api.ts            # API types
│   ├── models.ts         # Data models
│   └── components.ts     # Component prop types
│
├── context/               # React Context providers
│   ├── AuthContext.tsx   # Authentication state
│   ├── WebSocketContext.tsx  # WebSocket management
│   └── ThemeContext.tsx  # Theme management
│
├── config/                # Configuration files
│   ├── api.ts            # API endpoints
│   ├── constants.ts      # Application constants
│   └── env.ts            # Environment variables
│
├── styles/                # Global styles
│   ├── globals.css       # Global CSS
│   └── variables.css     # CSS variables
│
└── public/                # Static assets
    ├── images/           # Image files
    ├── icons/            # Icon files
    └── favicon.ico       # Favicon
```

## Dashboard Requirements

The frontend implements the following dashboard features (Requirement 9):

### 1. Portfolio Monitoring
- Current portfolio value
- Daily P&L
- Total return
- Real-time updates (1 second refresh)

### 2. Signal Feed
- Real-time trading signals from Intelligence Layer
- Filter by source (news, technical, DRL, simulation)
- Filter by confidence level
- Filter by asset

### 3. Trade History
- Historical trades with pagination
- Filters: date range, asset, exchange
- Trade details (price, size, fee, P&L)

### 4. Open Positions
- Current positions with real-time P&L
- Unrealized gains/losses
- Position management (close position)

### 5. Backtesting Interface
- Strategy selection
- Date range picker
- Asset selection
- Performance metrics display
- Equity curve visualization
- Trade-by-trade log

## API Integration

### REST API
- Base URL: `https://api.trading-platform.railway.app/api/v1`
- Authentication: JWT Bearer token
- Endpoints: See `lib/api.ts`

### WebSocket
- URL: `wss://api.trading-platform.railway.app/ws`
- Channels: `news`, `signals`, `portfolio`, `trades`
- Authentication: JWT token in query parameter

## Environment Variables

Create a `.env.local` file with:

```bash
NEXT_PUBLIC_API_URL=https://api.trading-platform.railway.app
NEXT_PUBLIC_WS_URL=wss://api.trading-platform.railway.app/ws
NEXT_PUBLIC_SUPABASE_URL=<supabase-url>
NEXT_PUBLIC_SUPABASE_ANON_KEY=<supabase-anon-key>
```

## Development

```bash
# Install dependencies
npm install

# Run development server
npm run dev

# Build for production
npm run build

# Start production server
npm start

# Run linter
npm run lint

# Run type check
npm run type-check
```

## Next.js 14 Best Practices

This project follows Next.js 14 best practices:

1. **App Router**: Uses the new App Router pattern (not Pages Router)
2. **Server Components**: Default to Server Components, use Client Components only when needed
3. **Data Fetching**: Use `fetch` with caching in Server Components
4. **Streaming**: Use `loading.tsx` for loading states
5. **Error Handling**: Use `error.tsx` for error boundaries
6. **Metadata**: Use `metadata` export for SEO
7. **Route Handlers**: Use Route Handlers for API routes

## Component Guidelines

### Component Structure
```tsx
// components/portfolio/PortfolioSummary.tsx
'use client'; // Only if client-side interactivity needed

import { usePortfolio } from '@/hooks/usePortfolio';

interface PortfolioSummaryProps {
  userId: string;
}

export function PortfolioSummary({ userId }: PortfolioSummaryProps) {
  const { portfolio, loading, error } = usePortfolio(userId);
  
  if (loading) return <div>Loading...</div>;
  if (error) return <div>Error: {error.message}</div>;
  
  return (
    <div>
      {/* Component JSX */}
    </div>
  );
}
```

### Custom Hook Structure
```tsx
// hooks/usePortfolio.ts
import { useState, useEffect } from 'react';
import { api } from '@/lib/api';

export function usePortfolio(userId: string) {
  const [portfolio, setPortfolio] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  useEffect(() => {
    // Fetch portfolio data
  }, [userId]);
  
  return { portfolio, loading, error };
}
```

## Deployment

The frontend is deployed to Vercel:

1. Connect GitHub repository to Vercel
2. Configure environment variables
3. Deploy automatically on push to `main` branch

## Testing

```bash
# Run unit tests
npm test

# Run E2E tests
npm run test:e2e

# Run tests with coverage
npm run test:coverage
```

## Contributing

1. Create feature branch from `develop`
2. Implement feature following component guidelines
3. Write tests for new components
4. Submit pull request
5. Wait for CI/CD pipeline to pass
6. Request code review

## License

Proprietary - All rights reserved
