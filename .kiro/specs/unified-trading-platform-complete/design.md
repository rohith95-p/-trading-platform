# Design Document: Unified Trading Intelligence Platform (Complete)

## Architecture Overview

### System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (Vercel)                         │
│  React Dashboard | Charts | Portfolio | Alerts | Settings       │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTPS
┌────────────────────────────▼────────────────────────────────────┐
│                    API Gateway (Railway)                         │
│  Authentication | Rate Limiting | Request Validation            │
└────────────────────────────┬────────────────────────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
┌───────▼────────┐  ┌────────▼────────┐  ┌──────▼──────────┐
│ Intelligence   │  │   Execution     │  │  Backtesting   │
│ Layer          │  │   Layer         │  │  Layer         │
│                │  │                 │  │                │
│ • News Class   │  │ • Exchange      │  │ • Pandas       │
│ • Indicators   │  │   Router        │  │   Backtester   │
│ • Simulation   │  │ • Risk Manager  │  │ • Metrics      │
│ • DRL Agent    │  │ • Order Mgmt    │  │ • Optimization │
└────────────────┘  └─────────────────┘  └────────────────┘
        │                    │                    │
        └────────────────────┼────────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
┌───────▼────────┐  ┌────────▼────────┐  ┌──────▼──────────┐
│ Data Layer     │  │  Cache Layer    │  │  External APIs  │
│                │  │                 │  │                 │
│ • PostgreSQL   │  │ • Redis         │  │ • Claude API    │
│ • Migrations   │  │ • TTL Policies  │  │ • Exchanges     │
│ • RLS Policies │  │ • Invalidation  │  │ • News Sources  │
└────────────────┘  └─────────────────┘  └────────────────┘
```

### Component Interfaces

#### ExchangeConnector Interface
```python
class ExchangeConnector(ABC):
    @abstractmethod
    async def connect(self) -> None:
        """Authenticate with exchange"""
        pass
    
    @abstractmethod
    async def placeOrder(self, order: Order) -> Trade:
        """Place order and return trade"""
        pass
    
    @abstractmethod
    async def getPositions(self) -> List[Position]:
        """Get open positions"""
        pass
    
    @abstractmethod
    async def closePosition(self, position_id: str) -> Trade:
        """Close position"""
        pass
    
    @abstractmethod
    async def getBalance(self) -> Balance:
        """Get account balance"""
        pass
```

#### StrategyExecutor Interface
```python
class StrategyExecutor(ABC):
    @abstractmethod
    async def execute(self, market_data: MarketData) -> Optional[Signal]:
        """Execute strategy and return signal"""
        pass
    
    @abstractmethod
    def validate_config(self, config: Dict) -> bool:
        """Validate strategy configuration"""
        pass
```

#### Backtester Interface
```python
class Backtester(ABC):
    @abstractmethod
    def backtest(self, strategy: Strategy, data: HistoricalData) -> BacktestResult:
        """Run backtest and return results"""
        pass
    
    @abstractmethod
    def compute_metrics(self, trades: List[Trade]) -> Metrics:
        """Compute performance metrics"""
        pass
```

#### DRLAgent Interface
```python
class DRLAgent(ABC):
    @abstractmethod
    async def predict(self, state: State) -> Action:
        """Predict action given state"""
        pass
    
    @abstractmethod
    def train(self, experiences: List[Experience]) -> None:
        """Train agent on experiences"""
        pass
```

### Database Schema

#### Core Tables (Phase 1)
```sql
-- Users table
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- API Keys table
CREATE TABLE api_keys (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  exchange TEXT NOT NULL,
  encrypted_key TEXT NOT NULL,
  encrypted_secret TEXT NOT NULL,
  created_at TIMESTAMP DEFAULT NOW(),
  UNIQUE(user_id, exchange)
);

-- Strategies table
CREATE TABLE strategies (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  type TEXT NOT NULL,
  config JSONB NOT NULL,
  is_active BOOLEAN DEFAULT false,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Trades table
CREATE TABLE trades (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  strategy_id UUID REFERENCES strategies(id),
  exchange TEXT NOT NULL,
  symbol TEXT NOT NULL,
  side TEXT NOT NULL,
  price DECIMAL(20, 8) NOT NULL,
  size DECIMAL(20, 8) NOT NULL,
  fee DECIMAL(20, 8),
  pnl DECIMAL(20, 8),
  created_at TIMESTAMP DEFAULT NOW()
);

-- Positions table
CREATE TABLE positions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  strategy_id UUID REFERENCES strategies(id),
  exchange TEXT NOT NULL,
  symbol TEXT NOT NULL,
  side TEXT NOT NULL,
  size DECIMAL(20, 8) NOT NULL,
  entry_price DECIMAL(20, 8) NOT NULL,
  current_price DECIMAL(20, 8),
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Signals table
CREATE TABLE signals (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  source TEXT NOT NULL,
  asset TEXT NOT NULL,
  direction TEXT NOT NULL,
  confidence DECIMAL(3, 2),
  rationale TEXT,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Audit log table
CREATE TABLE audit_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  action TEXT NOT NULL,
  details JSONB,
  created_at TIMESTAMP DEFAULT NOW()
);
```

#### Phase 1.5 Extension Tables
```sql
-- Custom indicators
CREATE TABLE custom_indicators (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  formula TEXT NOT NULL,
  is_template BOOLEAN DEFAULT false,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Alerts
CREATE TABLE alerts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  asset TEXT NOT NULL,
  condition TEXT NOT NULL,
  threshold DECIMAL(20, 8),
  notification_method TEXT NOT NULL,
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Webhooks
CREATE TABLE webhooks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  url TEXT NOT NULL,
  signing_key TEXT NOT NULL,
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Strategy templates
CREATE TABLE strategy_templates (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  config JSONB NOT NULL,
  is_public BOOLEAN DEFAULT false,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Historical data cache
CREATE TABLE historical_data (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  exchange TEXT NOT NULL,
  symbol TEXT NOT NULL,
  timeframe TEXT NOT NULL,
  timestamp TIMESTAMP NOT NULL,
  open DECIMAL(20, 8) NOT NULL,
  high DECIMAL(20, 8) NOT NULL,
  low DECIMAL(20, 8) NOT NULL,
  close DECIMAL(20, 8) NOT NULL,
  volume DECIMAL(20, 8) NOT NULL,
  created_at TIMESTAMP DEFAULT NOW(),
  UNIQUE(exchange, symbol, timeframe, timestamp)
);
```

### API Endpoints

#### Authentication
```
POST   /api/v1/auth/register          Register new user
POST   /api/v1/auth/login             Login user
POST   /api/v1/auth/logout            Logout user
POST   /api/v1/auth/refresh           Refresh JWT token
POST   /api/v1/auth/password-reset    Reset password
```

#### API Keys
```
GET    /api/v1/api-keys               List user's API keys
POST   /api/v1/api-keys               Add new API key
DELETE /api/v1/api-keys/:id           Delete API key
POST   /api/v1/api-keys/:id/validate  Validate API key
```

#### Intelligence Layer
```
POST   /api/v1/intelligence/classify-news        Classify news article
POST   /api/v1/intelligence/indicators           Compute indicators
POST   /api/v1/intelligence/multi-timeframe      Compute multi-timeframe indicators
POST   /api/v1/intelligence/divergence           Detect divergences
POST   /api/v1/intelligence/simulate             Run multi-agent simulation
POST   /api/v1/intelligence/drl/predict          Get DRL agent prediction
```

#### Execution Layer
```
GET    /api/v1/exchanges              List all exchanges
GET    /api/v1/exchanges/:name/markets Get markets for exchange
POST   /api/v1/orders                 Place order
GET    /api/v1/positions              Get open positions
DELETE /api/v1/positions/:id          Close position
GET    /api/v1/balance                Get account balance
```

#### Backtesting
```
POST   /api/v1/backtest               Run backtest
GET    /api/v1/backtest/:id           Get backtest results
GET    /api/v1/backtest/:id/trades    Get backtest trades
```

#### Portfolio
```
GET    /api/v1/portfolio              Get portfolio overview
GET    /api/v1/portfolio/analytics    Get portfolio analytics
GET    /api/v1/portfolio/risk-metrics Get risk metrics
```

#### Strategies
```
GET    /api/v1/strategies             List user's strategies
POST   /api/v1/strategies             Create strategy
PUT    /api/v1/strategies/:id         Update strategy
DELETE /api/v1/strategies/:id         Delete strategy
POST   /api/v1/strategies/:id/start   Start strategy
POST   /api/v1/strategies/:id/stop    Stop strategy
POST   /api/v1/strategies/:id/clone   Clone strategy
POST   /api/v1/strategies/from-template Create from template
```

#### Alerts (Phase 1.5)
```
GET    /api/v1/alerts                 List user's alerts
POST   /api/v1/alerts                 Create alert
PUT    /api/v1/alerts/:id             Update alert
DELETE /api/v1/alerts/:id             Delete alert
POST   /api/v1/alerts/:id/test        Test alert condition
```

#### Webhooks (Phase 1.5)
```
GET    /api/v1/webhooks               List user's webhooks
POST   /api/v1/webhooks               Create webhook
DELETE /api/v1/webhooks/:id           Delete webhook
POST   /api/v1/webhooks/:id/test      Test webhook
POST   /api/v1/webhooks/receive       Receive external signal
```

#### Custom Indicators (Phase 1.5)
```
GET    /api/v1/custom-indicators      List custom indicators
POST   /api/v1/custom-indicators      Create custom indicator
DELETE /api/v1/custom-indicators/:id  Delete custom indicator
```

### Technology Stack

#### Backend
- **Language**: Python 3.11+
- **Framework**: FastAPI
- **Database**: PostgreSQL (Supabase)
- **Cache**: Redis
- **Authentication**: JWT + OAuth
- **Async**: asyncio + aiohttp
- **Testing**: pytest + hypothesis

#### Frontend
- **Language**: TypeScript
- **Framework**: React 18+
- **UI Library**: TailwindCSS
- **Charts**: TradingView Lightweight Charts
- **State Management**: React Context
- **Testing**: Jest + Playwright

#### Infrastructure
- **Backend Hosting**: Railway
- **Frontend Hosting**: Vercel
- **Database**: Supabase
- **Logging**: Better Stack
- **CI/CD**: GitHub Actions

### Correctness Properties

#### Property 1: News Classification Output Structure
For any news classification result, the result SHALL contain sentiment ∈ {bullish, bearish, neutral} and confidence ∈ [0, 1].

#### Property 2: Trading Signal Structure
For any news article matching a tradeable market, the signal SHALL contain non-empty asset, direction, and rationale fields.

#### Property 3: Technical Indicator Range Constraints
For any price series: RSI ∈ [0, 100], ADX ∈ [0, 100], ATR ≥ 0, lower_band ≤ middle_band ≤ upper_band.

#### Property 4: Technical Indicator Mathematical Properties
EMA is weighted average with recent prices higher weight, MACD = fast_EMA - slow_EMA, OBV is cumulative sum, VWAP is volume-weighted average price.

#### Property 5: Simulation Confidence Score Range
For any simulation result, confidence ∈ [0, 1].

#### Property 6: Simulation Result Structure
For any simulation result, reasoning SHALL contain both consensus and dissenting opinions.

#### Property 7: Position Size Risk Limit
For portfolio value V and position size S, if S > 0.10 * V, then Risk_Manager SHALL reject.

#### Property 8: Total Exposure Risk Limit
For portfolio value V and positions P, if sum(P) > 0.50 * V, then Risk_Manager SHALL reject new positions.

#### Property 9: Leverage Risk Limit
For position with notional N and collateral C, if N / C > 10, then Risk_Manager SHALL reject.

#### Property 10: Kelly Criterion Calculation
For win probability p, average win W, average loss L: Kelly = (p * W - (1-p) * L) / W.

#### Property 11: Constitutional Guardrails Enforcement
For DRL agent action violating risk limits, action SHALL be overridden to "hold".

#### Property 12: Sharpe Ratio Calculation
For returns R: Sharpe = (mean(R) / std(R)) * sqrt(252).

#### Property 13: Maximum Drawdown Calculation
Max drawdown = max(0, max_i(E[i]) - min_{j>i}(E[j])) / max_i(E[i]).

#### Property 14: Trading Fees Impact
For fee rate f > 0: return_with_fees ≤ return_without_fees.

#### Property 15: Slippage Impact
For slippage s > 0: buy_price = signal_price * (1 + s), sell_price = signal_price * (1 - s).

### Security Architecture

#### Authentication & Authorization
- JWT tokens with 24-hour expiration
- Refresh tokens with 7-day expiration
- OAuth integration (Google, GitHub)
- Role-based access control (RBAC)

#### Data Encryption
- AES-256-GCM for API keys at rest
- TLS 1.3 for data in transit
- Encryption key rotation support

#### API Security
- Rate limiting: 100 calls/hour per user
- Input validation with Pydantic
- SQL injection prevention (parameterized queries)
- XSS prevention (Content Security Policy)
- CORS configuration

#### Secrets Management
- Environment variables for all secrets
- Never commit secrets to Git
- Rotation policies for sensitive credentials

### Performance Optimization

#### Caching Strategy
- Redis for indicator calculations (1m-1d TTL)
- Database query result caching
- Historical data caching
- Divergence calculation caching

#### Database Optimization
- Indexes on frequently queried fields
- Connection pooling (min 5, max 20)
- Query optimization and EXPLAIN analysis
- Partitioning for large tables

#### API Optimization
- Asynchronous request handling
- Batch operations for bulk requests
- Pagination for large result sets
- Compression (gzip) for responses

#### Frontend Optimization
- Code splitting and lazy loading
- Image optimization
- CSS-in-JS for dynamic styling
- WebSocket for real-time updates

### Deployment Architecture

#### Development Environment
- Local development with Docker Compose
- SQLite for local database
- Mock exchange APIs

#### Staging Environment
- Railway staging project
- Supabase staging project
- Vercel staging deployment
- Real exchange testnets

#### Production Environment
- Railway production project
- Supabase production project
- Vercel production deployment
- Real exchange APIs (paper trading)

### Monitoring & Observability

#### Metrics
- API latency (p50, p95, p99)
- Error rate (5xx errors)
- Database query time
- Cache hit rate
- Active users
- Trade volume

#### Logging
- Centralized logging with Better Stack
- Structured logging (JSON format)
- Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
- Request/response logging for debugging

#### Alerting
- Error rate > 5% over 5 minutes
- API latency p95 > 1 second
- Database connection failures
- Exchange API failures
- Disk usage > 80%

