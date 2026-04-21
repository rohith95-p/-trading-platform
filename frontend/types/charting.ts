/**
 * Advanced Charting Types
 * Defines types for TradingView Lightweight Charts integration
 */

export type ChartType = 'candlestick' | 'ohlc' | 'line' | 'area';
export type Timeframe = '1m' | '5m' | '15m' | '1h' | '4h' | '1d';

export interface CandleData {
  time: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume?: number;
}

export interface LineData {
  time: number;
  value: number;
}

export interface AreaData {
  time: number;
  value: number;
}

export interface OHLCData {
  time: number;
  open: number;
  high: number;
  low: number;
  close: number;
}

export interface IndicatorOverlay {
  name: string;
  type: 'line' | 'histogram' | 'cloud';
  data: LineData[];
  color?: string;
  lineWidth?: number;
}

export interface DrawingTool {
  id: string;
  type: 'trendline' | 'support' | 'resistance' | 'annotation';
  points: Array<{ x: number; y: number }>;
  label?: string;
  color?: string;
}

export interface OrderBookLevel {
  price: number;
  quantity: number;
  side: 'bid' | 'ask';
}

export interface OrderBook {
  bids: OrderBookLevel[];
  asks: OrderBookLevel[];
  timestamp: number;
}

export interface BidAskSpread {
  bid: number;
  ask: number;
  spread: number;
  spreadPercentage: number;
}

export interface ChartConfig {
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

export interface ChartState {
  config: ChartConfig;
  data: CandleData[];
  indicators: IndicatorOverlay[];
  drawingTools: DrawingTool[];
  orderBook?: OrderBook;
  bidAsk?: BidAskSpread;
  isLoading: boolean;
  error?: string;
}

export interface TrendlineData {
  startPrice: number;
  endPrice: number;
  startTime: number;
  endTime: number;
  slope: number;
  support?: number;
  resistance?: number;
}
