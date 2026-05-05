'use client';

import React, { useEffect, useRef, useState } from 'react';
import {
  ChartConfig,
  CandleData,
  IndicatorOverlay,
  DrawingTool,
  OrderBook,
  BidAskSpread,
  Timeframe,
} from '@/types/charting';

const DEFAULT_CHART_CONFIG: ChartConfig = {
  symbol: 'BTC/USD',
  timeframe: '1h',
  type: 'candlestick',
  indicators: ['EMA_20', 'RSI_14'],
  height: 420,
  width: 800,
};

/**
 * AdvancedChart Component
 * Renders a trading chart shell with technical overlays and market widgets.
 */
export const AdvancedChart: React.FC<{ config?: ChartConfig }> = ({ config = DEFAULT_CHART_CONFIG }) => {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const [data, setData] = useState<CandleData[]>([]);
  const [indicators, setIndicators] = useState<IndicatorOverlay[]>([]);
  const [drawingTools, setDrawingTools] = useState<DrawingTool[]>([]);
  const [orderBook, setOrderBook] = useState<OrderBook | null>(null);
  const [bidAsk, setBidAsk] = useState<BidAskSpread | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch chart data
  useEffect(() => {
    const fetchChartData = async () => {
      try {
        setLoading(true);
        const response = await fetch(
          `/api/charting/data?symbol=${config.symbol}&timeframe=${config.timeframe}&type=${config.type}`
        );
        if (!response.ok) {
          throw new Error('Failed to fetch chart data');
        }
        const chartData = await response.json();
        setData(chartData.candles || []);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error');
      } finally {
        setLoading(false);
      }
    };

    fetchChartData();
  }, [config.symbol, config.timeframe, config.type]);

  // Fetch indicators
  useEffect(() => {
    if (!config.indicators || config.indicators.length === 0) return;

    const fetchIndicators = async () => {
      try {
        const response = await fetch(
          `/api/charting/indicators?symbol=${config.symbol}&timeframe=${config.timeframe}&indicators=${config.indicators?.join(',')}`
        );
        if (!response.ok) {
          throw new Error('Failed to fetch indicators');
        }
        const indicatorData = await response.json();
        setIndicators(indicatorData.indicators || []);
      } catch (err) {
        console.error('Error fetching indicators:', err);
      }
    };

    fetchIndicators();
  }, [config.symbol, config.timeframe, config.indicators]);

  // Fetch order book if enabled
  useEffect(() => {
    if (!config.showOrderBook) return;

    const fetchOrderBook = async () => {
      try {
        const response = await fetch(`/api/charting/orderbook?symbol=${config.symbol}`);
        if (!response.ok) {
          throw new Error('Failed to fetch order book');
        }
        const orderBookData = await response.json();
        setOrderBook(orderBookData);
      } catch (err) {
        console.error('Error fetching order book:', err);
      }
    };

    fetchOrderBook();
    const interval = setInterval(fetchOrderBook, 1000); // Update every second
    return () => clearInterval(interval);
  }, [config.symbol, config.showOrderBook]);

  // Fetch bid-ask spread if enabled
  useEffect(() => {
    if (!config.showBidAsk) return;

    const fetchBidAsk = async () => {
      try {
        const response = await fetch(`/api/charting/bid-ask?symbol=${config.symbol}`);
        if (!response.ok) {
          throw new Error('Failed to fetch bid-ask spread');
        }
        const bidAskData = await response.json();
        setBidAsk(bidAskData);
      } catch (err) {
        console.error('Error fetching bid-ask spread:', err);
      }
    };

    fetchBidAsk();
    const interval = setInterval(fetchBidAsk, 1000); // Update every second
    return () => clearInterval(interval);
  }, [config.symbol, config.showBidAsk]);

  const handleAddDrawingTool = (tool: DrawingTool) => {
    setDrawingTools([...drawingTools, tool]);
  };

  const handleRemoveDrawingTool = (toolId: string) => {
    setDrawingTools(drawingTools.filter(t => t.id !== toolId));
  };

  const handleChangeTimeframe = (timeframe: Timeframe) => {
    // This would typically trigger a parent component update
    console.log('Changing timeframe to:', timeframe);
  };

  if (loading) {
    return <div className="advanced-chart loading">Loading chart...</div>;
  }

  if (error) {
    return <div className="advanced-chart error">Error: {error}</div>;
  }

  return (
    <div className="advanced-chart">
      <div className="chart-header">
        <div className="chart-info">
          <h2>{config.symbol}</h2>
          <span className="timeframe">{config.timeframe}</span>
        </div>
        <div className="chart-controls">
          <TimeframeSelector
            currentTimeframe={config.timeframe}
            onTimeframeChange={handleChangeTimeframe}
          />
          <DrawingToolsPanel
            tools={drawingTools}
            onAddTool={handleAddDrawingTool}
            onRemoveTool={handleRemoveDrawingTool}
          />
        </div>
      </div>

      <div className="chart-container" ref={chartContainerRef}>
        <ChartCanvas
          data={data}
          type={config.type}
          indicators={indicators}
          drawingTools={drawingTools}
          height={config.height || 500}
          width={config.width || 800}
        />
      </div>

      {config.showBidAsk && bidAsk && (
        <div className="bid-ask-display">
          <div className="bid">
            <span className="label">Bid</span>
            <span className="value">${bidAsk.bid.toFixed(2)}</span>
          </div>
          <div className="spread">
            <span className="label">Spread</span>
            <span className="value">${bidAsk.spread.toFixed(4)} ({bidAsk.spreadPercentage.toFixed(3)}%)</span>
          </div>
          <div className="ask">
            <span className="label">Ask</span>
            <span className="value">${bidAsk.ask.toFixed(2)}</span>
          </div>
        </div>
      )}

      {config.showOrderBook && orderBook && (
        <OrderBookDisplay orderBook={orderBook} />
      )}

      <div className="chart-legend">
        {indicators.map((indicator, index) => (
          <div key={index} className="legend-item">
            <span className="legend-color" style={{ backgroundColor: indicator.color || '#3b82f6' }}></span>
            <span className="legend-label">{indicator.name}</span>
          </div>
        ))}
      </div>
    </div>
  );
};

/**
 * ChartCanvas Component
 * Renders the actual chart using SVG (placeholder for TradingView integration)
 */
const ChartCanvas: React.FC<{
  data: CandleData[];
  type: string;
  indicators: IndicatorOverlay[];
  drawingTools: DrawingTool[];
  height: number;
  width: number;
}> = ({ data, type, indicators, drawingTools, height, width }) => {
  if (data.length === 0) {
    return <div className="chart-placeholder">No data available</div>;
  }

  const minPrice = Math.min(...data.map(d => d.low));
  const maxPrice = Math.max(...data.map(d => d.high));
  const priceRange = maxPrice - minPrice || 1;

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="chart-svg">
      {/* Grid lines */}
      {[0, 0.25, 0.5, 0.75, 1].map((ratio, i) => (
        <line
          key={`grid-${i}`}
          x1="50"
          y1={50 + ratio * (height - 100)}
          x2={width - 50}
          y2={50 + ratio * (height - 100)}
          stroke="#e5e7eb"
          strokeWidth="1"
        />
      ))}

      {/* Candlesticks */}
      {type === 'candlestick' &&
        data.map((candle, i) => {
          const x = 50 + (i / (data.length - 1 || 1)) * (width - 100);
          const openY = height - 50 - ((candle.open - minPrice) / priceRange) * (height - 100);
          const closeY = height - 50 - ((candle.close - minPrice) / priceRange) * (height - 100);
          const highY = height - 50 - ((candle.high - minPrice) / priceRange) * (height - 100);
          const lowY = height - 50 - ((candle.low - minPrice) / priceRange) * (height - 100);
          const color = candle.close >= candle.open ? '#10b981' : '#ef4444';
          const wickWidth = 1;
          const bodyWidth = 4;

          return (
            <g key={`candle-${i}`}>
              {/* Wick */}
              <line x1={x} y1={highY} x2={x} y2={lowY} stroke={color} strokeWidth={wickWidth} />
              {/* Body */}
              <rect
                x={x - bodyWidth / 2}
                y={Math.min(openY, closeY)}
                width={bodyWidth}
                height={Math.abs(closeY - openY) || 1}
                fill={color}
              />
            </g>
          );
        })}

      {/* Line chart */}
      {type === 'line' && (
        <polyline
          points={data
            .map((d, i) => {
              const x = 50 + (i / (data.length - 1 || 1)) * (width - 100);
              const y = height - 50 - ((d.close - minPrice) / priceRange) * (height - 100);
              return `${x},${y}`;
            })
            .join(' ')}
          fill="none"
          stroke="#3b82f6"
          strokeWidth="2"
        />
      )}

      {/* Indicators */}
      {indicators.map((indicator, idx) => (
        <polyline
          key={`indicator-${idx}`}
          points={indicator.data
            .map((d, i) => {
              const x = 50 + (i / (indicator.data.length - 1 || 1)) * (width - 100);
              const y = height - 50 - ((d.value - minPrice) / priceRange) * (height - 100);
              return `${x},${y}`;
            })
            .join(' ')}
          fill="none"
          stroke={indicator.color || '#8b5cf6'}
          strokeWidth={indicator.lineWidth || 1}
          opacity="0.7"
        />
      ))}

      {/* Drawing tools */}
      {drawingTools.map((tool, idx) => (
        <g key={`tool-${idx}`}>
          {tool.type === 'trendline' && tool.points.length >= 2 && (
            <line
              x1={tool.points[0].x}
              y1={tool.points[0].y}
              x2={tool.points[1].x}
              y2={tool.points[1].y}
              stroke={tool.color || '#f59e0b'}
              strokeWidth="2"
              strokeDasharray="5,5"
            />
          )}
        </g>
      ))}
    </svg>
  );
};

/**
 * TimeframeSelector Component
 */
const TimeframeSelector: React.FC<{
  currentTimeframe: Timeframe;
  onTimeframeChange: (timeframe: Timeframe) => void;
}> = ({ currentTimeframe, onTimeframeChange }) => {
  const timeframes: Timeframe[] = ['1m', '5m', '15m', '1h', '4h', '1d'];

  return (
    <div className="timeframe-selector">
      {timeframes.map(tf => (
        <button
          key={tf}
          className={`timeframe-btn ${tf === currentTimeframe ? 'active' : ''}`}
          onClick={() => onTimeframeChange(tf)}
        >
          {tf}
        </button>
      ))}
    </div>
  );
};

/**
 * DrawingToolsPanel Component
 */
const DrawingToolsPanel: React.FC<{
  tools: DrawingTool[];
  onAddTool: (tool: DrawingTool) => void;
  onRemoveTool: (toolId: string) => void;
}> = ({ tools, onAddTool, onRemoveTool }) => {
  return (
    <div className="drawing-tools-panel">
      <button className="tool-btn" title="Add Trendline">
        📐
      </button>
      <button className="tool-btn" title="Add Support Level">
        ⬇️
      </button>
      <button className="tool-btn" title="Add Resistance Level">
        ⬆️
      </button>
      <button className="tool-btn" title="Add Annotation">
        💬
      </button>
    </div>
  );
};

/**
 * OrderBookDisplay Component
 */
const OrderBookDisplay: React.FC<{ orderBook: OrderBook }> = ({ orderBook }) => {
  return (
    <div className="order-book-display">
      <div className="order-book-section">
        <h3>Asks</h3>
        <div className="order-book-levels">
          {orderBook.asks.slice(0, 5).map((level, i) => (
            <div key={i} className="order-book-level">
              <span className="price">${level.price.toFixed(2)}</span>
              <span className="quantity">{level.quantity.toFixed(4)}</span>
            </div>
          ))}
        </div>
      </div>
      <div className="order-book-section">
        <h3>Bids</h3>
        <div className="order-book-levels">
          {orderBook.bids.slice(0, 5).map((level, i) => (
            <div key={i} className="order-book-level">
              <span className="price">${level.price.toFixed(2)}</span>
              <span className="quantity">{level.quantity.toFixed(4)}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default AdvancedChart;
