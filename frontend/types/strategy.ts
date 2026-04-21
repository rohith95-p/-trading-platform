/**
 * Strategy Types
 */

export interface Strategy {
  id: string;
  name: string;
  description?: string;
  createdAt: number;
  updatedAt: number;
}

export interface StrategyMetrics {
  strategyId: string;
  totalReturn: number;
  sharpeRatio: number;
  maxDrawdown: number;
  winRate: number;
  trades: number;
  avgWin: number;
  avgLoss: number;
  profitFactor: number;
}

export interface StrategyComparison {
  strategies: Strategy[];
  metrics: Record<string, StrategyMetrics>;
  equityCurves: Record<string, Array<{ time: number; value: number }>>;
  monthlyReturns: Record<string, Record<string, number>>;
  drawdowns: Record<string, Array<{ start: number; end: number; value: number }>>;
}

export interface EquityCurveData {
  time: number;
  value: number;
}

export interface MonthlyReturn {
  month: string;
  return: number;
}

export interface Drawdown {
  start: number;
  end: number;
  value: number;
  duration: number;
}
