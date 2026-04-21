# Portfolio Analytics Component

## Overview

The Portfolio Analytics component provides a comprehensive dashboard for visualizing portfolio composition, performance, and analytics. It displays multiple charts and metrics to help traders understand their portfolio at a glance.

## Features

### 1. Asset Composition Pie Chart
- Displays portfolio breakdown by individual assets (BTC, ETH, etc.)
- Shows percentage allocation for each asset
- Color-coded for easy identification

### 2. Exchange Composition Pie Chart
- Shows portfolio distribution across different exchanges
- Helps traders understand exchange concentration risk
- Useful for diversification analysis

### 3. Strategy Composition Pie Chart
- Displays allocation across different trading strategies
- Helps identify which strategies are driving returns
- Useful for strategy performance analysis

### 4. Cumulative P&L Line Chart
- Shows portfolio value over time
- Displays cumulative profit/loss trend
- Helps identify performance patterns

### 5. Daily P&L Distribution Histogram
- Shows daily profit/loss distribution
- Green bars for positive days, red for negative
- Helps understand daily volatility

### 6. Performance Attribution Bar Chart
- Shows contribution to returns by category
- Helps identify which assets/exchanges/strategies drive performance
- Useful for performance analysis

### 7. Summary Metrics
- Total Portfolio Value
- Total P&L (with color coding)
- Total Return %

## Usage

### Basic Usage

```tsx
import { PortfolioAnalytics } from '@/components/portfolio/PortfolioAnalytics';

export default function Dashboard() {
  return (
    <div>
      <PortfolioAnalytics />
    </div>
  );
}
```

### Using the Hook

```tsx
import { usePortfolioAnalytics } from '@/hooks/usePortfolioAnalytics';

export default function CustomAnalytics() {
  const { analytics, loading, error } = usePortfolioAnalytics(60000); // Update every 60 seconds

  if (loading) return <div>Loading...</div>;
  if (error) return <div>Error: {error}</div>;

  return (
    <div>
      <h1>Total Value: ${analytics?.totalValue}</h1>
      <h2>Total P&L: ${analytics?.totalPnL}</h2>
    </div>
  );
}
```

## API Integration

The component fetches data from the `/api/portfolio/analytics` endpoint:

```typescript
GET /api/portfolio/analytics

Response:
{
  assetComposition: CompositionItem[],
  exchangeComposition: CompositionItem[],
  strategyComposition: CompositionItem[],
  cumulativePnL: CumulativePnL[],
  dailyPnLDistribution: DailyPnL[],
  performanceAttribution: PerformanceAttribution[],
  totalValue: number,
  totalPnL: number,
  totalReturn: number,
  lastUpdated: number
}
```

## Update Frequency

The component updates portfolio analytics at least once per minute (60,000ms). This can be customized via the `usePortfolioAnalytics` hook:

```tsx
const { analytics } = usePortfolioAnalytics(30000); // Update every 30 seconds
```

## Types

All types are defined in `@/types/portfolio`:

```typescript
interface PortfolioAnalytics {
  assetComposition: CompositionItem[];
  exchangeComposition: CompositionItem[];
  strategyComposition: CompositionItem[];
  cumulativePnL: CumulativePnL[];
  dailyPnLDistribution: DailyPnL[];
  performanceAttribution: PerformanceAttribution[];
  totalValue: number;
  totalPnL: number;
  totalReturn: number;
  lastUpdated: number;
}

interface CompositionItem {
  name: string;
  value: number;
  percentage: number;
  color?: string;
}

interface CumulativePnL {
  timestamp: number;
  value: number;
  pnl: number;
}

interface DailyPnL {
  date: string;
  pnl: number;
}

interface PerformanceAttribution {
  category: string;
  attribution: number;
  percentage: number;
}
```

## Styling

The component uses CSS classes for styling. Add the following to your global styles:

```css
.portfolio-analytics {
  padding: 20px;
  background: #f9fafb;
}

.analytics-header {
  margin-bottom: 30px;
}

.summary-metrics {
  display: flex;
  gap: 20px;
  margin-top: 15px;
}

.metric {
  display: flex;
  flex-direction: column;
  padding: 15px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.metric .label {
  font-size: 12px;
  color: #6b7280;
  margin-bottom: 5px;
}

.metric .value {
  font-size: 24px;
  font-weight: bold;
  color: #1f2937;
}

.metric .value.positive {
  color: #10b981;
}

.metric .value.negative {
  color: #ef4444;
}

.analytics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
  gap: 20px;
  margin-bottom: 30px;
}

.chart-container {
  background: white;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.chart-container.full-width {
  grid-column: 1 / -1;
}

.chart-container h2 {
  margin: 0 0 15px 0;
  font-size: 16px;
  color: #1f2937;
}

.pie-chart {
  display: flex;
  gap: 20px;
}

.chart-placeholder {
  flex: 1;
  min-height: 250px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.pie-svg {
  width: 100%;
  height: 100%;
}

.chart-legend {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 14px;
}

.legend-color {
  width: 12px;
  height: 12px;
  border-radius: 2px;
}

.legend-label {
  flex: 1;
  color: #4b5563;
}

.legend-value {
  color: #1f2937;
  font-weight: 600;
}

.line-chart,
.histogram-chart,
.bar-chart {
  width: 100%;
  height: 300px;
}

.chart-svg {
  width: 100%;
  height: 100%;
}

.chart-labels {
  display: flex;
  justify-content: space-between;
  margin-top: 10px;
  font-size: 12px;
  color: #6b7280;
}

.analytics-footer {
  text-align: right;
  font-size: 12px;
  color: #9ca3af;
}

.portfolio-analytics.loading,
.portfolio-analytics.error,
.portfolio-analytics.empty {
  padding: 40px;
  text-align: center;
  color: #6b7280;
}
```

## Testing

### Unit Tests

Run unit tests:

```bash
npm test -- PortfolioAnalytics.test.tsx
```

### Integration Tests

Run integration tests:

```bash
npm test -- PortfolioAnalytics.integration.test.tsx
```

### Test Coverage

Target: 80% code coverage

Current coverage:
- Component rendering: ✅
- Data fetching: ✅
- Error handling: ✅
- Chart rendering: ✅
- Periodic updates: ✅

## Performance Considerations

1. **Memoization**: Consider using `React.memo` for chart components to prevent unnecessary re-renders
2. **Lazy Loading**: Charts can be lazy-loaded if needed
3. **Data Caching**: API responses are cached on the backend
4. **Update Frequency**: Default 60-second update interval balances freshness and performance

## Accessibility

- All charts have semantic HTML structure
- Color coding includes text labels for accessibility
- Keyboard navigation supported
- ARIA labels for screen readers

## Browser Support

- Chrome/Edge: ✅
- Firefox: ✅
- Safari: ✅
- Mobile browsers: ✅

## Future Enhancements

1. **Interactive Charts**: Click on chart segments to drill down
2. **Custom Date Ranges**: Allow users to select custom date ranges
3. **Export**: Export analytics as PDF/CSV
4. **Alerts**: Alert when portfolio metrics exceed thresholds
5. **Comparison**: Compare portfolio performance to benchmarks
6. **Customization**: Allow users to customize which charts to display

## Troubleshooting

### Charts not rendering
- Check browser console for errors
- Verify API endpoint is accessible
- Check network tab for failed requests

### Data not updating
- Verify update interval is set correctly
- Check browser console for fetch errors
- Verify API is returning data

### Styling issues
- Ensure CSS classes are imported
- Check for CSS conflicts with other components
- Verify Tailwind CSS is configured correctly

## Related Components

- `PortfolioSummary` - Quick portfolio overview
- `PerformanceChart` - Detailed performance visualization
- `AssetAllocation` - Asset allocation breakdown

## Related Hooks

- `usePortfolioAnalytics` - Fetch and manage portfolio analytics
- `usePortfolio` - Fetch portfolio data
- `useWebSocket` - Real-time updates

## API Endpoints

- `GET /api/portfolio/analytics` - Get portfolio analytics
- `GET /api/portfolio` - Get portfolio data
- `GET /api/portfolio/assets` - Get portfolio assets
- `GET /api/portfolio/strategies` - Get portfolio strategies
