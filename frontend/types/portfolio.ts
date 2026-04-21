/**
 * Portfolio Analytics Types
 * Defines types for portfolio composition, performance, and analytics
 */

export interface PortfolioComposition {
  assetComposition: CompositionItem[];
  exchangeComposition: CompositionItem[];
  strategyComposition: CompositionItem[];
}

export interface CompositionItem {
  name: string;
  value: number;
  percentage: number;
  color?: string;
}

export interface CumulativePnL {
  timestamp: number;
  value: number;
  pnl: number;
}

export interface DailyPnL {
  date: string;
  pnl: number;
}

export interface PerformanceAttribution {
  category: string;
  attribution: number;
  percentage: number;
}

export interface PortfolioAnalytics {
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

export interface Portfolio {
  id: string;
  userId: string;
  totalValue: number;
  totalPnL: number;
  totalReturn: number;
  assets: PortfolioAsset[];
  strategies: PortfolioStrategy[];
  lastUpdated: number;
}

export interface PortfolioAsset {
  symbol: string;
  exchange: string;
  quantity: number;
  value: number;
  pnl: number;
  return: number;
}

export interface PortfolioStrategy {
  id: string;
  name: string;
  value: number;
  pnl: number;
  return: number;
  allocation: number;
}
