/**
 * StrategyExecutor Interface
 * 
 * Enables pluggable trading strategies with consistent execution and backtesting APIs.
 * 
 * Implements Requirement 1 (Pluggable Architecture)
 */

import { Trade } from './ExchangeConnector';

export interface Signal {
  asset: string;
  direction: 'long' | 'short' | 'neutral';
  confidence: number; // 0-1
  rationale: string;
  indicators?: { [key: string]: number };
  timestamp: number;
}

export interface BacktestResult {
  totalReturn: number;
  sharpeRatio: number;
  maxDrawdown: number;
  winRate: number;
  trades: Trade[];
  equityCurve: { timestamp: number; equity: number }[];
}

export interface RiskCheck {
  approved: boolean;
  reason?: string;
  adjustedSize?: number;
}

export interface HistoricalData {
  symbol: string;
  timeframe: string;
  data: Array<{
    timestamp: number;
    open: number;
    high: number;
    low: number;
    close: number;
    volume: number;
  }>;
}

export interface StrategyParams {
  [key: string]: any;
}

export interface Portfolio {
  totalValue: number;
  positions: { [symbol: string]: number };
  cash: number;
}

export interface Order {
  symbol: string;
  side: 'buy' | 'sell';
  type: 'market' | 'limit';
  size: number;
  price?: number;
}

export interface StrategyExecutor {
  name: string;
  type: 'directional' | 'market-making' | 'grid' | 'arbitrage';
  
  // Execution
  execute(signal: Signal): Promise<Trade>;
  
  // Backtesting
  backtest(data: HistoricalData, params: StrategyParams): Promise<BacktestResult>;
  
  // Risk management
  checkRisk(order: Order, portfolio: Portfolio): Promise<RiskCheck>;
}
