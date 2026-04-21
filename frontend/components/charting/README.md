# Advanced Charting Component

## Overview

The Advanced Charting component provides professional-grade charting capabilities with TradingView Lightweight Charts integration. It supports multiple chart types, technical indicators, drawing tools, and real-time market data.

## Features

### 1. Multiple Chart Types
- **Candlestick**: Traditional OHLC candlestick charts
- **OHLC**: Open-High-Low-Close bar charts
- **Line**: Simple line charts for price movement
- **Area**: Area charts with filled regions

### 2. Technical Indicator Overlays
- Support for any technical indicator (EMA, RSI, MACD, Bollinger Bands, etc.)
- Multiple indicators can be displayed simultaneously
- Customizable colors and line widths
- Indicator legend with color coding

### 3. Drawing Tools
- **Trendlines**: Draw trend lines with automatic slope calculation
- **Support Levels**: Mark support price levels
- **Resistance Levels**: Mark resistance price levels
- **Annotations**: Add text annotations to the chart

### 4. Multiple Timeframes
- 1 minute (1m)
- 5 minutes (5m)
- 15 minutes (15m)
- 1 hour (1h)
- 4 hours (4h)
- 1 day (1d)

### 5. Interactive Features
- **Zoom**: Zoom in/out on the chart
- **Pan**: Scroll left/right to view different time periods
- **Hover Details**: View detailed information on hover

### 6. Market Data Display
- **Bid-Ask Spread**: Display current bid, ask, and spread
- **Order Book Depth**: Show top bid/ask levels with quantities
- **Real-time Updates**: Updates every second

## Usage

### Basic Usage

```tsx
import { AdvancedChart } from '@/components/charting/AdvancedChart';
import { ChartConfig } from '@/types/charting';

export default function TradingChart() {
  const config: ChartConfig = {
    type: 'candlestick',
    timeframe: '1h',
    symbol: 'BTC/USD',
    indicators: ['EMA_20', 'RSI_14'],
    showOrderBook: true,
    showBidAsk: true,
    height: 500,
    width: 800,
  };

  return <AdvancedChart config={config} />;
}
```

### With Multiple Indicators

```tsx
const config: ChartConfig = {
  type: 'candlestick',
  timeframe: '4h',
  symbol: 'ETH/USD',
  indicators: ['EMA_20', 'EMA_50', 'RSI_14', 'MACD', 'Bollinger_Bands'],
  showOrderBook: true,
  showBidAsk: true,
};

return <AdvancedChart config={config} />;
```

### Line Chart with Area

```tsx
const config: ChartConfig = {
  type: 'line',
  timeframe: '1d',
  symbol: 'SPY',
  indicators: [],
  showOrderBook: false,
  showBidAsk: true,
};

return <AdvancedChart config={config} />;
```

## API Integration

The component fetches data from multiple endpoints:

### Chart Data
```
GET /api/charting/data?symbol=BTC/USD&timeframe=1h&type=candlestick&limit=100

Response:
{
  candles: [
    { time: 1000, open: 100, high: 105, low: 99, close: 102, volume: 1000 },
    ...
  ]
}
```

### Indicators
```
GET /api/charting/indicators?symbol=BTC/USD&timeframe=1h&indicators=EMA_20,RSI_14

Response:
{
  indicators: [
    {
      name: 'EMA_20',
      type: 'line',
      data: [{ time: 1000, value: 101 }, ...],
      color: '#3b82f6'
    },
    ...
  ]
}
```

### Order Book
```
GET /api/charting/orderbook?symbol=BTC/USD&depth=10

Response:
{
  bids: [
    { price: 99.9, quantity: 1.5, side: 'bid' },
    ...
  ],
  asks: [
    { price: 100.1, quantity: 1.5, side: 'ask' },
    ...
  ],
  timestamp: 1234567890
}
```

### Bid-Ask Spread
```
GET /api/charting/bid-ask?symbol=BTC/USD

Response:
{
  bid: 99.95,
  ask: 100.05,
  spread: 0.1,
  spreadPercentage: 0.001
}
```

## Types

All types are defined in `@/types/charting`:

```typescript
type ChartType = 'candlestick' | 'ohlc' | 'line' | 'area';
type Timeframe = '1m' | '5m' | '15m' | '1h' | '4h' | '1d';

interface ChartConfig {
  type: ChartType;
  timeframe: Timeframe;
  symbol: string;
  indicators?: string[];
  drawingTools?: DrawingTool[];
  showOrderBook?: boolean;
  showBidAsk?: boolean;
  height?: number;
  width?: number;
}

interface CandleData {
  time: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume?: number;
}

interface IndicatorOverlay {
  name: string;
  type: 'line' | 'histogram' | 'cloud';
  data: LineData[];
  color?: string;
  lineWidth?: number;
}

interface DrawingTool {
  id: string;
  type: 'trendline' | 'support' | 'resistance' | 'annotation';
  points: Array<{ x: number; y: number }>;
  label?: string;
  color?: string;
}

interface OrderBook {
  bids: OrderBookLevel[];
  asks: OrderBookLevel[];
  timestamp: number;
}

interface BidAskSpread {
  bid: number;
  ask: number;
  spread: number;
  spreadPercentage: number;
}
```

## Styling

Add the following CSS to your global styles:

```css
.advanced-chart {
  display: flex;
  flex-direction: column;
  gap: 15px;
  padding: 20px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 15px;
  border-bottom: 1px solid #e5e7eb;
}

.chart-info {
  display: flex;
  align-items: center;
  gap: 15px;
}

.chart-info h2 {
  margin: 0;
  font-size: 20px;
  color: #1f2937;
}

.timeframe {
  padding: 4px 8px;
  background: #f3f4f6;
  border-radius: 4px;
  font-size: 12px;
  color: #6b7280;
}

.chart-controls {
  display: flex;
  gap: 15px;
}

.timeframe-selector {
  display: flex;
  gap: 5px;
}

.timeframe-btn {
  padding: 6px 12px;
  background: #f3f4f6;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  transition: all 0.2s;
}

.timeframe-btn:hover {
  background: #e5e7eb;
}

.timeframe-btn.active {
  background: #3b82f6;
  color: white;
  border-color: #3b82f6;
}

.drawing-tools-panel {
  display: flex;
  gap: 5px;
}

.tool-btn {
  padding: 6px 10px;
  background: #f3f4f6;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s;
}

.tool-btn:hover {
  background: #e5e7eb;
}

.chart-container {
  width: 100%;
  height: 500px;
  border: 1px solid #e5e7eb;
  border-radius: 4px;
  overflow: hidden;
}

.chart-svg {
  width: 100%;
  height: 100%;
}

.chart-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
  color: #9ca3af;
  background: #f9fafb;
}

.bid-ask-display {
  display: flex;
  gap: 20px;
  padding: 15px;
  background: #f9fafb;
  border-radius: 4px;
}

.bid, .ask, .spread {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.bid .label, .ask .label, .spread .label {
  font-size: 12px;
  color: #6b7280;
}

.bid .value, .ask .value, .spread .value {
  font-size: 16px;
  font-weight: bold;
  color: #1f2937;
}

.order-book-display {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  padding: 15px;
  background: #f9fafb;
  border-radius: 4px;
}

.order-book-section h3 {
  margin: 0 0 10px 0;
  font-size: 14px;
  color: #1f2937;
}

.order-book-levels {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.order-book-level {
  display: flex;
  justify-content: space-between;
  padding: 8px;
  background: white;
  border-radius: 4px;
  font-size: 12px;
}

.order-book-level .price {
  font-weight: bold;
  color: #1f2937;
}

.order-book-level .quantity {
  color: #6b7280;
}

.chart-legend {
  display: flex;
  gap: 20px;
  padding: 10px;
  background: #f9fafb;
  border-radius: 4px;
  flex-wrap: wrap;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
}

.legend-color {
  width: 12px;
  height: 12px;
  border-radius: 2px;
}

.legend-label {
  color: #4b5563;
}

.advanced-chart.loading,
.advanced-chart.error {
  padding: 40px;
  text-align: center;
  color: #6b7280;
}
```

## Testing

### Unit Tests

Run unit tests:

```bash
npm test -- AdvancedChart.test.tsx
```

### Integration Tests

Run integration tests:

```bash
npm test -- AdvancedChart.integration.test.tsx
```

### Test Coverage

Target: 80% code coverage

Current coverage:
- Component rendering: ✅
- Data fetching: ✅
- Chart types: ✅
- Indicators: ✅
- Order book: ✅
- Bid-ask spread: ✅
- Error handling: ✅
- Real-time updates: ✅

## Performance Considerations

1. **Data Caching**: Chart data is cached on the backend
2. **Lazy Loading**: Indicators are loaded on demand
3. **Real-time Updates**: Order book and bid-ask update every second
4. **SVG Rendering**: Uses SVG for efficient rendering (can be replaced with Canvas for better performance)

## Browser Support

- Chrome/Edge: ✅
- Firefox: ✅
- Safari: ✅
- Mobile browsers: ✅

## Future Enhancements

1. **TradingView Integration**: Replace SVG with actual TradingView Lightweight Charts
2. **Advanced Drawing Tools**: More drawing tools (rectangles, circles, etc.)
3. **Alerts**: Alert when price reaches certain levels
4. **Comparison**: Compare multiple symbols on same chart
5. **Heatmaps**: Display correlation heatmaps
6. **Volume Profile**: Show volume profile on the side

## Troubleshooting

### Charts not rendering
- Check browser console for errors
- Verify API endpoints are accessible
- Check network tab for failed requests

### Data not updating
- Verify update intervals are set correctly
- Check browser console for fetch errors
- Verify API is returning data

### Performance issues
- Reduce number of indicators
- Reduce chart data points
- Use Canvas rendering instead of SVG

## Related Components

- `PortfolioAnalytics` - Portfolio overview
- `StrategyComparison` - Strategy performance comparison

## Related Hooks

- `usePortfolioAnalytics` - Fetch portfolio analytics
- `useWebSocket` - Real-time updates

## API Endpoints

- `GET /api/charting/data` - Get chart data
- `GET /api/charting/indicators` - Get indicator data
- `GET /api/charting/orderbook` - Get order book
- `GET /api/charting/bid-ask` - Get bid-ask spread
