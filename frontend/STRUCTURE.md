# Frontend Directory Structure

Complete directory structure for the Unified Trading Intelligence Platform frontend.

## Created Structure

```
frontend/
├── README.md                              # Frontend documentation
├── STRUCTURE.md                           # This file
│
├── app/                                   # Next.js 14 App Router
│   └── .gitkeep
│
├── components/                            # React components
│   ├── .gitkeep
│   ├── portfolio/                         # Portfolio monitoring
│   │   └── .gitkeep
│   ├── signals/                           # Signal feed
│   │   └── .gitkeep
│   ├── trades/                            # Trade history
│   │   └── .gitkeep
│   ├── positions/                         # Position tracking
│   │   └── .gitkeep
│   ├── backtesting/                       # Backtesting UI
│   │   └── .gitkeep
│   ├── common/                            # Shared components
│   │   └── .gitkeep
│   └── layout/                            # Layout components
│       └── .gitkeep
│
├── hooks/                                 # Custom React hooks
│   └── .gitkeep
│
├── lib/                                   # Utility functions
│   └── .gitkeep
│
├── types/                                 # TypeScript types
│   └── .gitkeep
│
├── context/                               # React Context providers
│   └── .gitkeep
│
├── config/                                # Configuration
│   └── .gitkeep
│
├── styles/                                # Global styles
│   └── .gitkeep
│
└── public/                                # Static assets
    └── .gitkeep
```

## Directory Purposes

### `/app` - Next.js 14 App Router
The main application pages using Next.js 14's App Router pattern. This replaces the traditional `/pages` directory.

**Future structure:**
- `layout.tsx` - Root layout with providers
- `page.tsx` - Landing/home page
- `dashboard/page.tsx` - Main dashboard
- `auth/login/page.tsx` - Login page
- `auth/register/page.tsx` - Registration page
- `strategies/page.tsx` - Strategy list
- `strategies/[id]/page.tsx` - Strategy details
- `api-keys/page.tsx` - API key management

### `/components` - React Components
Organized by feature area to support the dashboard requirements:

#### `/components/portfolio`
- `PortfolioSummary.tsx` - Portfolio value, daily P&L, total return
- `PerformanceChart.tsx` - Equity curve visualization
- `AssetAllocation.tsx` - Portfolio breakdown

#### `/components/signals`
- `SignalFeed.tsx` - Real-time signal feed with WebSocket
- `SignalCard.tsx` - Individual signal display
- `SignalFilters.tsx` - Filter by source, confidence, asset

#### `/components/trades`
- `TradeHistory.tsx` - Historical trades table
- `TradeFilters.tsx` - Date range, asset, exchange filters
- `TradeDetails.tsx` - Detailed trade view

#### `/components/positions`
- `PositionList.tsx` - Open positions table
- `PositionCard.tsx` - Individual position with P&L
- `ClosePositionModal.tsx` - Position closing interface

#### `/components/backtesting`
- `BacktestForm.tsx` - Strategy, date range, asset selection
- `BacktestResults.tsx` - Metrics and equity curve
- `BacktestTradeLog.tsx` - Trade-by-trade log

#### `/components/common`
- `Button.tsx` - Reusable button
- `Card.tsx` - Card container
- `Table.tsx` - Data table
- `Modal.tsx` - Modal dialog
- `Input.tsx` - Form input
- `Select.tsx` - Dropdown select
- `Loader.tsx` - Loading spinner

#### `/components/layout`
- `Header.tsx` - Top navigation
- `Sidebar.tsx` - Side navigation
- `Footer.tsx` - Footer
- `Layout.tsx` - Main layout wrapper

### `/hooks` - Custom React Hooks
Encapsulate data fetching and state management logic:

- `usePortfolio.ts` - Fetch and manage portfolio data
- `useSignals.ts` - Subscribe to signal feed via WebSocket
- `useTrades.ts` - Fetch trade history with pagination
- `usePositions.ts` - Fetch and manage positions
- `useWebSocket.ts` - WebSocket connection management
- `useAuth.ts` - Authentication state
- `useBacktest.ts` - Backtest execution and results

### `/lib` - Utility Functions
Shared utilities and API clients:

- `api.ts` - REST API client with authentication
- `websocket.ts` - WebSocket client for real-time updates
- `utils.ts` - General utility functions
- `formatters.ts` - Data formatting (currency, dates, percentages)
- `validators.ts` - Input validation functions

### `/types` - TypeScript Types
Type definitions for type safety:

- `api.ts` - API request/response types
- `models.ts` - Data models (User, Strategy, Trade, Position, Signal)
- `components.ts` - Component prop types

### `/context` - React Context
Global state management:

- `AuthContext.tsx` - User authentication state
- `WebSocketContext.tsx` - WebSocket connection state
- `ThemeContext.tsx` - Theme/dark mode state

### `/config` - Configuration
Application configuration:

- `api.ts` - API endpoint URLs
- `constants.ts` - Application constants
- `env.ts` - Environment variable validation

### `/styles` - Global Styles
CSS and styling:

- `globals.css` - Global CSS styles
- `variables.css` - CSS variables (colors, spacing, fonts)

### `/public` - Static Assets
Static files served by Next.js:

- `images/` - Image assets
- `icons/` - Icon files
- `favicon.ico` - Favicon

## Alignment with Requirements

This structure supports all dashboard requirements (Requirement 9):

✅ **Portfolio Monitoring** - `/components/portfolio`
✅ **Signal Feed** - `/components/signals` + `useSignals` hook
✅ **Trade History** - `/components/trades` + `useTrades` hook
✅ **Open Positions** - `/components/positions` + `usePositions` hook
✅ **Backtesting Interface** - `/components/backtesting` + `useBacktest` hook
✅ **Real-time Updates** - `/lib/websocket.ts` + `useWebSocket` hook

## Next.js 14 Best Practices

✅ **App Router** - Uses `/app` directory instead of `/pages`
✅ **Component Organization** - Feature-based organization
✅ **Type Safety** - TypeScript types in `/types`
✅ **Custom Hooks** - Reusable logic in `/hooks`
✅ **Context Providers** - Global state in `/context`
✅ **Utility Functions** - Shared utilities in `/lib`

## Next Steps

1. **Install Dependencies**
   ```bash
   cd frontend
   npm init -y
   npm install next@14 react react-dom typescript @types/react @types/node
   npm install -D tailwindcss postcss autoprefixer
   ```

2. **Configure Next.js**
   - Create `next.config.js`
   - Create `tsconfig.json`
   - Create `tailwind.config.js`

3. **Implement Components**
   - Start with layout components
   - Implement dashboard components
   - Add authentication components

4. **Set Up API Integration**
   - Implement API client in `/lib/api.ts`
   - Implement WebSocket client in `/lib/websocket.ts`
   - Create custom hooks for data fetching

5. **Deploy to Vercel**
   - Connect GitHub repository
   - Configure environment variables
   - Deploy

## Status

✅ Directory structure created
✅ Documentation added
⏳ Dependencies to be installed
⏳ Configuration files to be created
⏳ Components to be implemented
⏳ API integration to be implemented
⏳ Deployment to be configured
