/**
 * ExchangeConnector Interface
 * 
 * Provides a unified abstraction for all exchange integrations, enabling seamless
 * addition of new exchanges without modifying existing code.
 * 
 * Implements Requirement 1 (Pluggable Architecture) and Requirement 5 (Exchange Connectivity)
 */

export interface Market {
  symbol: string;
  baseAsset: string;
  quoteAsset: string;
  minOrderSize: number;
  maxOrderSize: number;
  pricePrecision: number;
  sizePrecision: number;
}

export interface OrderBook {
  symbol: string;
  bids: [price: number, size: number][];
  asks: [price: number, size: number][];
  timestamp: number;
}

export interface Ticker {
  symbol: string;
  lastPrice: number;
  bidPrice: number;
  askPrice: number;
  volume24h: number;
  timestamp: number;
}

export interface Order {
  symbol: string;
  side: 'buy' | 'sell';
  type: 'market' | 'limit';
  size: number;
  price?: number;
  timeInForce?: 'GTC' | 'IOC' | 'FOK';
}

export interface Trade {
  id: string;
  orderId: string;
  symbol: string;
  side: 'buy' | 'sell';
  price: number;
  size: number;
  fee: number;
  timestamp: number;
}

export interface Position {
  symbol: string;
  size: number;
  avgPrice: number;
  currentPrice: number;
  unrealizedPnl: number;
  realizedPnl: number;
}

export interface ExchangeConnector {
  name: string;
  type: 'cex' | 'dex' | 'prediction' | 'stocks';
  
  // Connection management
  connect(): Promise<void>;
  disconnect(): Promise<void>;
  isConnected(): boolean;
  
  // Market data
  getMarkets(): Promise<Market[]>;
  getOrderBook(symbol: string): Promise<OrderBook>;
  getTicker(symbol: string): Promise<Ticker>;
  
  // Trading
  placeOrder(order: Order): Promise<Trade>;
  cancelOrder(orderId: string): Promise<void>;
  getPosition(symbol: string): Promise<Position>;
  getPositions(): Promise<Position[]>;
  
  // Account
  getBalance(): Promise<{ [asset: string]: number }>;
}
