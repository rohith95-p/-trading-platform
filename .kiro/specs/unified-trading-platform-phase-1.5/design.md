# Design Document: Unified Trading Intelligence Platform Phase 1.5

## Overview

Phase 1.5 delivers incremental enhancements to the Phase 1 MVP with zero refactoring of core systems. All new components implement existing Phase 1 interfaces, enabling seamless integration. The phase focuses on:

1. **Exchange Expansion**: 4 new exchange connectors (Hyperliquid, dYdX, Kraken, Binance)
2. **Technical Analysis**: 10+ new indicators, multi-timeframe analysis, divergence detection, custom indicator builder
3. **UI Enhancements**: Advanced charting, portfolio analytics, strategy comparison, alert management, dark mode
4. **Advanced Features**: Multi-strategy portfolio management, risk analytics, webhooks, strategy cloning, trade analytics

### Design Principles

1. **Zero Refactoring**: All new components implement Phase 1 interfaces without modification
2. **Backward Compatibility**: Phase 1 APIs, schemas, and functionality remain unchanged
3. **Incremental Delivery**: Features can be deployed independently
4. **Performance**: All new features maintain Phase 1 performance standards (p95 < 500ms)
5. **Extensibility**: Architecture supports future phases without redesign

## Architecture

### New Exchange Connectors

All new exchange connectors implement the `ExchangeConnector` interface from Phase 1:

```python
# src/exchanges/hyperliquid.py
class HyperliquidConnector(ExchangeConnector):
    def __init__(self, api_key: str, secret: str):
        self.name = "hyperliquid"
        self.type = "cex"
        self.api_key = api_key
        self.secret = secret
        self.max_leverage = 20
    
    async def connect(self) -> None:
        """Authenticate with Hyperliquid API"""
        pass
    
    async def placeOrder(self, order: Order) -> Trade:
        """Place order with leverage validation"""
        # Validate leverage
        if order.leverage > self.max_leverage:
            raise ValueError(f"Leverage {order.leverage} exceeds max {self.max_leverage}")
        # Place order via Hyperliquid API
        pass
    
    # Implement remaining ExchangeConnector methods...
```

**Implementation Details**:

- **Hyperliquid**: REST API + WebSocket for real-time updates, supports perpetual futures with up to 20x leverage
- **dYdX**: REST API + WebSocket, blockchain-based with wallet signing, supports perpetual futures with up to 20x leverage
- **Kraken**: REST API + WebSocket, supports spot and margin trading with up to 5x leverage
- **Binance**: REST API + WebSocket, supports spot and futures with up to 125x leverage

**Exchange Router Enhancement**:

```python
# src/execution/exchange_router.py
class ExchangeRouter:
    def __init__(self):
        self.connectors = {
            "kalshi": KalshiConnector(),
            "polymarket": PolymarketConnector(),
            "alpaca": AlpacaConnector(),
            "hyperliquid": HyperliquidConnector(),  # NEW
            "dydx": dYdXConnector(),                 # NEW
            "kraken": KrakenConnector(),             # NEW
            "binance": BinanceConnector(),           # NEW
        }
    
    async def route_order(self, order: Order) -> Trade:
        """Route order to appropriate exchange"""
        connector = self.connectors.get(order.exchange)
        if not connector:
            raise ValueError(f"Unknown exchange: {order.exchange}")
        return await connector.placeOrder(order)
```

### Enhanced Technical Indicators

All new indicators implement the `TechnicalIndicator` interface:

```python
# src/intelligence/indicators.py

class StochasticOscillator(TechnicalIndicator):
    def __init__(self, k_period: int = 14, k_smooth: int = 3, d_smooth: int = 3):
        self.k_period = k_period
        self.k_smooth = k_smooth
        self.d_smooth = d_smooth
    
    def compute(self, prices: np.ndarray) -> Dict[str, np.ndarray]:
        """Compute Stochastic Oscillator
        
        Returns:
            {
                'stoch_k': np.ndarray,  # %K line
                'stoch_d': np.ndarray,  # %D line (SMA of %K)
            }
        """
        # Vectorized computation using NumPy
        pass

class CommodityChannelIndex(TechnicalIndicator):
    def __init__(self, period: int = 20):
        self.period = period
    
    def compute(self, prices: np.ndarray) -> np.ndarray:
        """Compute CCI"""
        pass

# Additional indicators: Williams %R, Ichimoku, Aroon, Keltner Channels, MFI, ROC, A/D, CMF
```

**Indicator Registry**:

```python
# src/intelligence/indicator_registry.py
class IndicatorRegistry:
    def __init__(self):
        self.indicators = {
            # Phase 1 indicators
            "EMA": ExponentialMovingAverage,
            "RSI": RelativeStrengthIndex,
            "MACD": MACD,
            "ATR": AverageTrueRange,
            "BBANDS": BollingerBands,
            "ADX": AverageDirectionalIndex,
            "OBV": OnBalanceVolume,
            "VWAP": VolumeWeightedAveragePrice,
            
            # Phase 1.5 indicators
            "STOCH": StochasticOscillator,
            "CCI": CommodityChannelIndex,
            "WILLR": WilliamsPercentR,
            "ICHIMOKU": IchimokuCloud,
            "AROON": AroonIndicator,
            "KELTNER": KeltnerChannels,
            "MFI": MoneyFlowIndex,
            "ROC": RateOfChange,
            "AD": AccumulationDistribution,
            "CMF": ChaikinMoneyFlow,
        }
    
    def compute(self, symbol: str, timeframe: str, indicators: List[str]) -> Dict:
        """Compute multiple indicators efficiently"""
        pass
```

### Multi-Timeframe Analysis

```python
# src/intelligence/multi_timeframe.py
class MultiTimeframeAnalyzer:
    def __init__(self, indicator_registry: IndicatorRegistry):
        self.registry = indicator_registry
        self.timeframes = ["1m", "5m", "15m", "1h", "4h", "1d"]
        self.cache = Redis()
    
    async def analyze(self, symbol: str, indicators: List[str]) -> Dict:
        """Compute indicators across all timeframes
        
        Returns:
            {
                "1m": {"EMA_20": 100.5, "RSI_14": 65.2, ...},
                "5m": {"EMA_20": 100.3, "RSI_14": 64.8, ...},
                ...
                "1d": {"EMA_20": 99.8, "RSI_14": 62.1, ...},
            }
        """
        results = {}
        
        for timeframe in self.timeframes:
            cache_key = f"indicators:{symbol}:{timeframe}:{hash(indicators)}"
            
            # Check cache
            cached = await self.cache.get(cache_key)
            if cached:
                results[timeframe] = json.loads(cached)
                continue
            
            # Fetch data for timeframe
            data = await self.fetch_data(symbol, timeframe)
            
            # Compute indicators
            indicators_result = self.registry.compute(symbol, timeframe, indicators)
            results[timeframe] = indicators_result
            
            # Cache with appropriate TTL
            ttl = self.get_ttl_for_timeframe(timeframe)
            await self.cache.setex(cache_key, ttl, json.dumps(indicators_result))
        
        return results
    
    def get_ttl_for_timeframe(self, timeframe: str) -> int:
        """Return cache TTL based on timeframe"""
        ttls = {
            "1m": 60,      # 1 minute
            "5m": 300,     # 5 minutes
            "15m": 900,    # 15 minutes
            "1h": 3600,    # 1 hour
            "4h": 14400,   # 4 hours
            "1d": 86400,   # 1 day
        }
        return ttls.get(timeframe, 60)
```

### Indicator Divergence Detection

```python
# src/intelligence/divergence_detector.py
class DivergenceDetector:
    def __init__(self, sensitivity: str = "normal"):
        self.sensitivity = sensitivity
        self.lookback = {"strict": 5, "normal": 10, "loose": 20}[sensitivity]
    
    def detect_bullish_divergence(self, prices: np.ndarray, indicator: np.ndarray) -> List[Dict]:
        """Detect bullish divergence (price lower low, indicator higher low)"""
        divergences = []
        
        for i in range(self.lookback, len(prices)):
            # Find local lows in price
            if prices[i] < prices[i-1] and prices[i] < prices[i+1]:
                # Check if indicator made higher low
                if indicator[i] > indicator[i-self.lookback]:
                    divergences.append({
                        "type": "bullish",
                        "index": i,
                        "price_low": prices[i],
                        "indicator_value": indicator[i],
                        "confidence": self.calculate_confidence(prices, indicator, i),
                    })
        
        return divergences
    
    def detect_bearish_divergence(self, prices: np.ndarray, indicator: np.ndarray) -> List[Dict]:
        """Detect bearish divergence (price higher high, indicator lower high)"""
        # Similar logic to bullish divergence
        pass
    
    def calculate_confidence(self, prices: np.ndarray, indicator: np.ndarray, index: int) -> float:
        """Calculate divergence confidence based on magnitude and touches"""
        # Confidence = (magnitude * touches) / lookback
        pass
```

### Custom Indicator Builder

```python
# src/intelligence/custom_indicator_builder.py
class CustomIndicatorBuilder:
    def __init__(self, indicator_registry: IndicatorRegistry):
        self.registry = indicator_registry
    
    def build(self, formula: str, indicators: Dict[str, np.ndarray]) -> np.ndarray:
        """Build custom indicator from formula
        
        Example formulas:
        - "EMA_20 + RSI_14"
        - "(EMA_20 - EMA_50) / ATR_14"
        - "IF(RSI_14 > 70, 1, IF(RSI_14 < 30, -1, 0))"
        """
        # Parse formula
        parser = FormulaParser()
        ast = parser.parse(formula)
        
        # Validate AST
        validator = FormulaValidator(self.registry)
        validator.validate(ast)
        
        # Evaluate AST
        evaluator = FormulaEvaluator(indicators)
        result = evaluator.evaluate(ast)
        
        return result
    
    def save_template(self, user_id: str, name: str, formula: str) -> str:
        """Save custom indicator as template"""
        template_id = str(uuid.uuid4())
        # Store in database
        db.custom_indicators.insert_one({
            "id": template_id,
            "user_id": user_id,
            "name": name,
            "formula": formula,
            "created_at": datetime.now(),
        })
        return template_id
```

### UI Components

#### Portfolio Analytics Dashboard

```typescript
// frontend/components/portfolio/PortfolioAnalytics.tsx
export const PortfolioAnalytics: React.FC = () => {
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [analytics, setAnalytics] = useState<PortfolioAnalytics | null>(null);
  
  useEffect(() => {
    // Fetch portfolio and analytics
    fetchPortfolioAnalytics().then(data => {
      setPortfolio(data.portfolio);
      setAnalytics(data.analytics);
    });
  }, []);
  
  return (
    <div className="portfolio-analytics">
      <div className="grid grid-cols-2 gap-4">
        {/* Composition by asset */}
        <PieChart data={analytics?.assetComposition} title="By Asset" />
        
        {/* Composition by exchange */}
        <PieChart data={analytics?.exchangeComposition} title="By Exchange" />
        
        {/* Composition by strategy */}
        <PieChart data={analytics?.strategyComposition} title="By Strategy" />
        
        {/* Cumulative P&L */}
        <LineChart data={analytics?.cumulativePnL} title="Cumulative P&L" />
        
        {/* Daily P&L distribution */}
        <HistogramChart data={analytics?.dailyPnLDistribution} title="Daily P&L" />
        
        {/* Performance attribution */}
        <BarChart data={analytics?.performanceAttribution} title="Attribution" />
      </div>
    </div>
  );
};
```

#### Advanced Charting

```typescript
// frontend/components/charting/AdvancedChart.tsx
import { createChart, ColorType } from 'lightweight-charts';

export const AdvancedChart: React.FC<AdvancedChartProps> = ({
  symbol,
  timeframe,
  indicators,
}) => {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  
  useEffect(() => {
    if (!chartContainerRef.current) return;
    
    const chart = createChart(chartContainerRef.current, {
      layout: { background: { type: ColorType.Solid, color: '#ffffff' } },
      width: chartContainerRef.current.clientWidth,
      height: 500,
    });
    
    // Add candlestick series
    const candlestickSeries = chart.addCandlestickSeries();
    candlestickSeries.setData(candleData);
    
    // Add indicator overlays
    indicators.forEach(indicator => {
      const lineSeries = chart.addLineSeries({ color: '#2962FF' });
      lineSeries.setData(indicatorData[indicator]);
    });
    
    // Add drawing tools
    const drawingTools = new DrawingTools(chart);
    
    return () => chart.remove();
  }, [symbol, timeframe, indicators]);
  
  return <div ref={chartContainerRef} />;
};
```

#### Strategy Comparison View

```typescript
// frontend/components/strategies/StrategyComparison.tsx
export const StrategyComparison: React.FC = () => {
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [comparison, setComparison] = useState<StrategyComparison | null>(null);
  
  return (
    <div className="strategy-comparison">
      <table>
        <thead>
          <tr>
            <th>Strategy</th>
            <th>Total Return</th>
            <th>Sharpe Ratio</th>
            <th>Max Drawdown</th>
            <th>Win Rate</th>
            <th>Trades</th>
          </tr>
        </thead>
        <tbody>
          {strategies.map(strategy => (
            <tr key={strategy.id}>
              <td>{strategy.name}</td>
              <td>{comparison?.metrics[strategy.id].totalReturn.toFixed(2)}%</td>
              <td>{comparison?.metrics[strategy.id].sharpeRatio.toFixed(2)}</td>
              <td>{comparison?.metrics[strategy.id].maxDrawdown.toFixed(2)}%</td>
              <td>{comparison?.metrics[strategy.id].winRate.toFixed(2)}%</td>
              <td>{comparison?.metrics[strategy.id].trades}</td>
            </tr>
          ))}
        </tbody>
      </table>
      
      {/* Equity curves comparison */}
      <LineChart data={comparison?.equityCurves} title="Equity Curves" />
      
      {/* Monthly returns heatmap */}
      <HeatmapChart data={comparison?.monthlyReturns} title="Monthly Returns" />
    </div>
  );
};
```

#### Alert Management UI

```typescript
// frontend/components/alerts/AlertManagement.tsx
export const AlertManagement: React.FC = () => {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [showForm, setShowForm] = useState(false);
  
  const handleCreateAlert = async (alert: AlertFormData) => {
    const response = await api.post('/alerts', alert);
    setAlerts([...alerts, response.data]);
    setShowForm(false);
  };
  
  return (
    <div className="alert-management">
      <button onClick={() => setShowForm(true)}>Create Alert</button>
      
      {showForm && <AlertForm onSubmit={handleCreateAlert} />}
      
      <div className="alerts-list">
        {alerts.map(alert => (
          <AlertCard key={alert.id} alert={alert} />
        ))}
      </div>
    </div>
  );
};
```

#### Dark Mode Support

```typescript
// frontend/context/ThemeContext.tsx
export const ThemeProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [theme, setTheme] = useState<'light' | 'dark'>('light');
  
  useEffect(() => {
    // Detect system preference
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    setTheme(prefersDark ? 'dark' : 'light');
  }, []);
  
  useEffect(() => {
    // Apply theme to document
    document.documentElement.setAttribute('data-theme', theme);
  }, [theme]);
  
  return (
    <ThemeContext.Provider value={{ theme, setTheme }}>
      {children}
    </ThemeContext.Provider>
  );
};
```

### Database Schema Extensions

```sql
-- New tables for Phase 1.5

-- Custom indicators
CREATE TABLE custom_indicators (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  formula TEXT NOT NULL,
  description TEXT,
  is_template BOOLEAN DEFAULT false,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Alerts
CREATE TABLE alerts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  asset TEXT NOT NULL,
  condition TEXT NOT NULL,  -- 'price_above', 'price_below', 'indicator_above', etc.
  threshold DECIMAL(20, 8) NOT NULL,
  notification_method TEXT NOT NULL,  -- 'email', 'sms', 'webhook', 'in_app'
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMP DEFAULT NOW(),
  triggered_at TIMESTAMP,
  
  INDEX idx_alerts_user_id (user_id),
  INDEX idx_alerts_is_active (is_active)
);

-- Webhooks
CREATE TABLE webhooks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  url TEXT NOT NULL,
  signing_key TEXT NOT NULL,
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMP DEFAULT NOW(),
  
  INDEX idx_webhooks_user_id (user_id)
);

-- Strategy templates
CREATE TABLE strategy_templates (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  description TEXT,
  config JSONB NOT NULL,
  is_public BOOLEAN DEFAULT false,
  created_at TIMESTAMP DEFAULT NOW(),
  
  INDEX idx_templates_user_id (user_id)
);

-- Historical data cache
CREATE TABLE historical_data (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  exchange TEXT NOT NULL,
  symbol TEXT NOT NULL,
  timeframe TEXT NOT NULL,  -- '1m', '5m', '1h', '1d'
  timestamp TIMESTAMP NOT NULL,
  open DECIMAL(20, 8) NOT NULL,
  high DECIMAL(20, 8) NOT NULL,
  low DECIMAL(20, 8) NOT NULL,
  close DECIMAL(20, 8) NOT NULL,
  volume DECIMAL(20, 8) NOT NULL,
  created_at TIMESTAMP DEFAULT NOW(),
  
  UNIQUE(exchange, symbol, timeframe, timestamp),
  INDEX idx_historical_symbol_timestamp (symbol, timestamp)
);

-- Trade analytics
CREATE TABLE trade_analytics (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  trade_id UUID REFERENCES trades(id) ON DELETE CASCADE,
  slippage DECIMAL(20, 8),
  execution_quality DECIMAL(3, 2),  -- 0-1
  market_impact DECIMAL(20, 8),
  created_at TIMESTAMP DEFAULT NOW()
);

-- Correlation matrix cache
CREATE TABLE correlation_matrix (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  asset1 TEXT NOT NULL,
  asset2 TEXT NOT NULL,
  correlation DECIMAL(3, 2),
  timestamp TIMESTAMP DEFAULT NOW(),
  
  UNIQUE(user_id, asset1, asset2),
  INDEX idx_correlation_user_id (user_id)
);
```

### API Endpoints

**New Endpoints**:

```
# Exchange connectors
GET    /exchanges                    List all exchanges (includes new ones)
GET    /exchanges/:name/markets      Get markets for exchange

# Technical indicators
POST   /intelligence/indicators      Compute indicators (supports new indicators)
POST   /intelligence/multi-timeframe Compute multi-timeframe indicators
POST   /intelligence/divergence      Detect divergences

# Custom indicators
POST   /custom-indicators            Create custom indicator
GET    /custom-indicators            List custom indicators
DELETE /custom-indicators/:id        Delete custom indicator

# Alerts
GET    /alerts                       List user's alerts
POST   /alerts                       Create alert
PUT    /alerts/:id                   Update alert
DELETE /alerts/:id                   Delete alert
POST   /alerts/:id/test              Test alert condition

# Webhooks
GET    /webhooks                     List user's webhooks
POST   /webhooks                     Create webhook
DELETE /webhooks/:id                 Delete webhook
POST   /webhooks/:id/test            Test webhook

# Strategy templates
GET    /strategy-templates           List templates
POST   /strategy-templates           Create template
POST   /strategies/from-template     Create strategy from template

# Portfolio analytics
GET    /portfolio/analytics          Get portfolio analytics
GET    /portfolio/risk-metrics       Get risk metrics (VaR, Sharpe, correlation)

# Trade analytics
GET    /trades/analytics             Get trade analytics
GET    /trades/performance-attribution Get performance attribution

# Historical data
GET    /historical-data/:symbol      Get cached historical data
POST   /historical-data/sync         Sync historical data from exchanges
```

### Performance Considerations

1. **Indicator Caching**: All indicators cached with appropriate TTLs (1m-1d based on timeframe)
2. **Multi-Timeframe Optimization**: Compute all timeframes in parallel using asyncio
3. **Database Indexing**: Indexes on frequently queried fields (user_id, symbol, timestamp)
4. **Connection Pooling**: Redis and PostgreSQL connection pools sized for concurrent requests
5. **Rate Limiting**: Per-user and per-endpoint rate limits to prevent abuse

### Backward Compatibility

1. **API Versioning**: All Phase 1.5 endpoints use `/api/v1` (same as Phase 1)
2. **Database Migrations**: New tables added without modifying existing schemas
3. **Exchange Router**: New connectors added to router without modifying existing connectors
4. **Indicator Registry**: New indicators added to registry without modifying existing indicators
5. **Feature Flags**: New features can be disabled via configuration if issues arise

## Implementation Roadmap

### Phase 1.5.1 (Week 1-2): Exchange Connectors
- Implement Hyperliquid connector
- Implement dYdX connector
- Implement Kraken connector
- Implement Binance connector
- Update exchange router
- Test with testnet APIs

### Phase 1.5.2 (Week 3-4): Technical Indicators
- Implement 10+ new indicators
- Implement multi-timeframe analysis
- Implement divergence detection
- Implement custom indicator builder
- Add indicator caching

### Phase 1.5.3 (Week 5-6): UI Enhancements
- Implement portfolio analytics dashboard
- Integrate TradingView Lightweight Charts
- Implement strategy comparison view
- Implement alert management UI
- Implement user settings panel
- Implement dark mode support

### Phase 1.5.4 (Week 7-8): Advanced Features
- Implement multi-strategy portfolio management
- Implement advanced risk analytics
- Implement webhook support
- Implement strategy cloning and templating
- Implement historical data caching
- Implement trade analytics

### Phase 1.5.5 (Week 9-10): Testing and Deployment
- Integration testing
- End-to-end testing
- Performance testing
- Security testing
- Documentation
- Deployment to production

## Testing Strategy

### Unit Tests
- Test each new indicator independently
- Test divergence detection logic
- Test custom indicator builder
- Target: 80% code coverage

### Integration Tests
- Test exchange connectors with testnet APIs
- Test multi-timeframe analysis
- Test alert triggering
- Test webhook delivery

### End-to-End Tests
- Test complete trading flows with new exchanges
- Test portfolio analytics calculations
- Test strategy comparison
- Test alert management

### Performance Tests
- Verify indicator computation < 100ms
- Verify multi-timeframe analysis < 500ms
- Verify API responses < 500ms p95
- Verify dashboard loads < 2 seconds

## Security Considerations

1. **API Key Encryption**: New exchange API keys encrypted with AES-256
2. **Webhook Validation**: HMAC-SHA256 signature validation
3. **Input Validation**: All user inputs validated with Pydantic
4. **Rate Limiting**: Per-user and per-endpoint rate limits
5. **Audit Logging**: All new features logged for compliance
