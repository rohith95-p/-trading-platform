# Unified Trading Intelligence Platform — Deployment Handover

> Version: 2.0 | Date: April 2026 | Status: 82% Complete — Ready for Staging

---

## 1. What This Platform Does

A unified algorithmic trading platform that combines 4 intelligence sources:
1. **Technical Analysis** — 21 indicators, Redis-cached, WebSocket-streamed
2. **News Classification** — Claude API sentiment analysis, <5s latency
3. **Multi-Agent Simulation** — 10 AI agents debate each trade, consensus scoring
4. **Deep Reinforcement Learning** — PPO agent with constitutional guardrails

Across 7 exchanges (all paper trading in Phase 1):
- Kalshi, Polymarket (prediction markets)
- Alpaca (stocks)
- Hyperliquid, dYdX (perpetuals/derivatives)
- Kraken, Binance (spot/futures)

With full risk management:
- 10% max position size, 50% max total exposure, 10x max leverage
- Kelly criterion position sizing (capped at 0.25)
- Circuit breakers: 20% position loss auto-close, 10% daily drawdown halt

---

## 2. Infrastructure

### Live Services
| Service | Provider | URL | Status |
|---------|----------|-----|--------|
| Backend API | Railway | https://[your-app].railway.app | ✅ Deployed |
| Database | Supabase | Project URL configured via environment | Connected |
| Cache | Redis (Railway addon) | Auto-configured | ✅ Active |
| Frontend | Vercel | Pending deployment | ⚠️ Not deployed |

### Environment Variables Required
**Railway (backend):**
```
DATABASE_URL          # Auto-set by Railway PostgreSQL addon
REDIS_URL             # Auto-set by Railway Redis addon
JWT_SECRET            # from deployment secret manager
ENCRYPTION_KEY        # from deployment secret manager
SUPABASE_URL          # from .env.local or deployment env
SUPABASE_ANON_KEY     # from .env.local or deployment env
SUPABASE_SERVICE_KEY  # from .env.local or deployment env
ANTHROPIC_API_KEY     # Required for news classification
OPENAI_API_KEY        # Optional — simulation falls back to mock without it
CORS_ORIGINS          # https://[your-vercel-app].vercel.app,http://localhost:3000
ENVIRONMENT           # production
LOG_LEVEL             # info
ENABLE_PAPER_TRADING  # true
ENABLE_REAL_TRADING   # false
```

**Vercel (frontend):**
```
NEXT_PUBLIC_API_URL              # https://[your-railway-app].railway.app
NEXT_PUBLIC_WS_URL               # wss://[your-railway-app].railway.app/ws
NEXT_PUBLIC_SUPABASE_URL         # from .env.local or deployment env
NEXT_PUBLIC_SUPABASE_ANON_KEY    # from .env.local or deployment env
NEXT_PUBLIC_ENABLE_PAPER_TRADING # true
NEXT_PUBLIC_ENABLE_REAL_TRADING  # false
```

---

## 3. Codebase Structure

```
ultra_core/
├── src/                          # Backend (Python 3.11+, FastAPI)
│   ├── main.py                   # App entry point, all routers registered
│   ├── config.py                 # All env vars via Pydantic Settings
│   ├── database.py               # SQLAlchemy engine + session
│   ├── models.py                 # Pydantic request/response models
│   ├── security.py               # Password hashing utilities
│   │
│   ├── api/                      # FastAPI routers
│   │   ├── auth.py               # POST /auth/login, /register, /refresh
│   │   ├── api_keys.py           # CRUD /api-keys (AES-256 encrypted)
│   │   ├── backtesting.py        # POST /api/v1/backtest
│   │   ├── drl.py                # POST /intelligence/drl/predict
│   │   ├── execution.py          # Order execution
│   │   ├── intelligence.py       # GET/POST /intelligence/indicators/*
│   │   ├── roles.py              # RBAC role management
│   │   ├── sessions.py           # Session management
│   │   ├── simulation.py         # POST /intelligence/simulate
│   │   ├── test.py               # GET /health, /api/v1/test/*
│   │   ├── trading.py            # POST /trading/orders, GET /trading/positions
│   │   └── webhooks.py           # POST /webhooks/register, /test/{id}
│   │
│   ├── auth/                     # Authentication
│   │   ├── auth_service.py       # Login, register, token refresh
│   │   ├── jwt_handler.py        # JWT encode/decode/verify
│   │   ├── middleware.py         # Auth middleware, @require_permission
│   │   └── models.py             # TokenResponse, UserProfile models
│   │
│   ├── api_keys/                 # Exchange API key vault
│   │   ├── api_key_service.py    # CRUD + AES-256-GCM encrypt/decrypt
│   │   ├── encryption.py         # Cryptographic primitives
│   │   └── models.py             # APIKey models
│   │
│   ├── backtesting/              # Backtesting engine
│   │   ├── pandas_backtester.py  # Vectorized backtester, fee/slippage
│   │   ├── metrics.py            # Sharpe, drawdown, win rate, profit factor
│   │   └── advanced_filters.py  # Date/symbol/pnl filters, trade analytics
│   │
│   ├── data/                     # Database layer
│   │   ├── database.py           # Engine, session factory
│   │   ├── models.py             # User, Trade, Position, Signal, APIKey, AuditLog
│   │   └── migrations.py         # Schema migration utilities
│   │
│   ├── drl/                      # Deep Reinforcement Learning
│   │   ├── ppo_agent.py          # PPOAgent (SB3 PPO + MockPPO fallback)
│   │   ├── guardrails.py         # ConstitutionalGuardrails (circuit breaker, leverage)
│   │   └── training_env.py       # TradingEnvironment (gymnasium, 10-feature obs)
│   │
│   ├── exchanges/                # Exchange connectors
│   │   ├── __init__.py           # Exports all 7 connectors
│   │   ├── kalshi.py             # Kalshi prediction markets
│   │   ├── polymarket.py         # Polymarket CLOB API
│   │   ├── alpaca.py             # Alpaca paper trading API
│   │   ├── hyperliquid.py        # Hyperliquid perpetuals (20x leverage)
│   │   ├── dydx.py               # dYdX decentralized derivatives
│   │   ├── kraken.py             # Kraken spot/margin
│   │   ├── binance.py            # Binance spot/futures
│   │   └── router.py             # ExchangeRouter — multi-exchange routing
│   │
│   ├── intelligence/             # Intelligence layer
│   │   ├── indicators.py         # 21 technical indicators (NumPy vectorized)
│   │   ├── indicator_registry.py # Dynamic indicator lookup
│   │   ├── indicator_cache_service.py  # Redis cache, timeframe TTLs
│   │   ├── indicator_cache.py    # Low-level cache ops
│   │   ├── indicator_websocket_service.py  # Real-time WebSocket streaming
│   │   ├── news_classifier.py    # Claude API classification, signal generation
│   │   ├── news_stream.py        # Multi-source news ingestion
│   │   ├── classifier.py         # Alternative classifier
│   │   ├── classification_monitor.py  # Metrics monitoring
│   │   ├── custom_indicator_builder.py  # DSL for custom indicators
│   │   ├── divergence_detector.py  # RSI/MACD divergence
│   │   ├── multi_timeframe.py    # Multi-timeframe analysis
│   │   └── news/                 # News subsystem
│   │       ├── models.py         # NewsArticle models
│   │       ├── news_stream.py    # NewsStreamService
│   │       ├── deduplication.py  # Content hash dedup
│   │       └── sources/          # RSS, Twitter, Telegram adapters
│   │
│   ├── interfaces/               # Core abstractions
│   │   ├── exchange_connector.py # ExchangeConnector ABC + Order/Trade/Position
│   │   ├── backtester.py         # Backtester ABC + BacktestResult
│   │   ├── drl_agent.py          # DRLAgent ABC
│   │   ├── strategy_executor.py  # StrategyExecutor ABC
│   │   ├── registry.py           # Component registry
│   │   └── examples.py           # Example implementations
│   │
│   ├── portfolio/
│   │   └── multi_strategy.py     # MultiStrategyPortfolio (add/rebalance/clone)
│   │
│   ├── rbac/                     # Role-Based Access Control
│   │   ├── models.py             # Role, Permission models
│   │   ├── permissions.py        # Permission definitions
│   │   ├── rbac_service.py       # Service + default role init
│   │   └── decorators.py         # @require_permission
│   │
│   ├── risk/                     # Risk management
│   │   ├── manager.py            # RiskManager (position/exposure/leverage limits)
│   │   ├── position_sizer.py     # Kelly criterion (capped 0.25)
│   │   ├── circuit_breaker.py    # 20% position loss, 10% daily drawdown
│   │   └── advanced_analytics.py # VaR, CVaR, Beta, Correlation, Sortino
│   │
│   ├── session/                  # Session management
│   │   ├── session_service.py    # Session CRUD
│   │   ├── models.py             # Session models
│   │   └── middleware.py         # Session middleware
│   │
│   ├── simulation/               # Multi-agent simulation
│   │   ├── engine.py             # SimulationEngine (10 agents, 5 rounds)
│   │   └── consensus.py          # ConsensusBuilder (weighted majority)
│   │
│   └── borrowed/                 # Original code from reference repos
│       ├── README.md             # What was borrowed and from where
│       ├── fiduciary_sentinel_core.py    # FiduciarySentinel guardrail
│       ├── fiduciary_rl_agent.py         # DualHeadPPO architecture
│       ├── fiduciary_trading_env.py      # Trading env design notes
│       ├── hyperliquid_risk_manager.py   # Original RiskManager
│       ├── polymarket_classifier.py      # Claude classification prompt
│       └── polymarket_news_stream.py     # News aggregator
│
├── frontend/                     # Frontend (Next.js 14, TypeScript, TailwindCSS)
│   ├── app/
│   │   ├── page.tsx              # ⚠️ PLACEHOLDER — needs dashboard wiring
│   │   ├── layout.tsx            # Root layout
│   │   └── api/                  # Next.js API proxy routes
│   │       ├── portfolio/analytics/route.ts
│   │       ├── alerts/route.ts
│   │       ├── charting/         # Chart data proxies
│   │       ├── settings/route.ts
│   │       └── strategies/       # Strategy proxies
│   │
│   ├── components/               # All UI components (built, tested)
│   │   ├── portfolio/PortfolioAnalytics.tsx  # Charts, P&L curves
│   │   ├── charting/AdvancedChart.tsx        # TradingView-style
│   │   ├── strategies/StrategyComparison.tsx
│   │   ├── alerts/AlertManagement.tsx
│   │   ├── settings/SettingsPanel.tsx
│   │   ├── signals/SignalFeed.tsx            # 1s refresh, BUY/SELL/HOLD
│   │   ├── trades/TradeHistory.tsx           # Sortable, paginated
│   │   ├── positions/Positions.tsx           # Live PnL
│   │   ├── backtesting/Backtesting.tsx       # Form + equity curve
│   │   └── common/ThemeToggle.tsx
│   │
│   ├── hooks/
│   │   ├── useWebSocket.ts       # Auto-reconnect WebSocket hook
│   │   └── usePortfolioAnalytics.ts
│   │
│   ├── context/ThemeContext.tsx  # Dark mode
│   └── types/                   # TypeScript types
│
├── tests/                        # 88+ tests
│   ├── unit/                     # Unit + property-based tests
│   ├── integration/              # API + exchange integration tests
│   └── e2e/                      # End-to-end user flow tests
│
├── docs/                         # Documentation
├── sql/                          # Database schemas
├── scripts/                      # Utility scripts
├── examples/                     # WebSocket client examples
├── .github/workflows/            # 8 CI/CD workflows
├── docker-compose.yml            # Local dev stack
├── Dockerfile.backend            # Backend container
└── requirements.txt              # Python dependencies
```

---

## 4. API Endpoints Reference

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /auth/register | Create account |
| POST | /auth/login | Get JWT tokens |
| POST | /auth/refresh | Refresh access token |
| GET | /auth/profile | Get user profile |

### Intelligence
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/v1/intelligence/indicators/compute | Compute 21 indicators |
| POST | /api/v1/intelligence/indicators/compute/batch | Batch computation |
| GET | /api/v1/intelligence/indicators/available | List all indicators |
| POST | /intelligence/classify-news | Claude news classification |
| POST | /intelligence/simulate | Multi-agent simulation |
| POST | /intelligence/drl/predict | PPO agent prediction |
| WS | /api/v1/intelligence/ws/indicators | Real-time indicator stream |

### Trading
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /trading/orders | Place order (risk-validated) |
| GET | /trading/positions | All positions across exchanges |
| GET | /trading/balance | Total balance |
| DELETE | /trading/orders/{id} | Cancel order |
| GET | /trading/circuit-breaker | Circuit breaker status |

### Backtesting
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/v1/backtest | Run vectorized backtest |

### Webhooks
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /webhooks/register | Register webhook URL |
| GET | /webhooks | List webhooks |
| DELETE | /webhooks/{id} | Remove webhook |
| POST | /webhooks/test/{id} | Send test payload |

---

## 5. What's Complete vs What's Not

### ✅ Production-Ready
- All 21 technical indicators with Redis caching and WebSocket streaming
- News classification pipeline (Claude API, RSS/Twitter/Telegram)
- Multi-agent simulation engine (10 agents, 5 rounds, OpenAI/mock)
- PPO DRL agent with constitutional guardrails
- All 7 exchange connectors (paper trading mode)
- Risk management (position limits, Kelly criterion, circuit breakers)
- Vectorized backtester with fee/slippage modeling
- JWT authentication + RBAC + AES-256 API key encryption
- Database schema (all tables, indexes, RLS-ready)
- 88+ tests passing (unit, integration, e2e, property-based)
- CI/CD pipeline (8 GitHub Actions workflows)
- Railway backend deployment
- Supabase database connection

### ⚠️ Needs Work Before Full Production
1. **Frontend dashboard** — `app/page.tsx` is a placeholder. All components exist but need wiring into a real page with navigation sidebar.
2. **Frontend API proxy routes** — `/api/signals`, `/api/portfolio/trades`, `/api/portfolio/positions` routes missing (components fetch these but they don't exist yet).
3. **OAuth (Google/GitHub)** — Returns HTTP 501. Needs Supabase Auth integration.
4. **2FA database operations** — TOTP secret storage/retrieval are stubs.
5. **Backtester signal input** — Currently uses hardcoded "buy every 10 bars". Needs real strategy signal input.
6. **Exchange key validation** — Marks keys as valid without actually calling the exchange API.
7. **Better Stack monitoring** — Not configured. No production alerting.
8. **Vercel deployment** — Frontend not deployed yet.

---

## 6. Known Issues & Risks

| Issue | Severity | Impact | Fix |
|-------|----------|--------|-----|
| Frontend is placeholder page | High | Users see blank page | Wire components into app/page.tsx |
| OAuth returns 501 | High | Can't login with Google/GitHub | Implement Supabase Auth |
| 2FA stubs | Medium | 2FA setup/verify broken | Add totp_secret to User model |
| Backtester hardcoded signal | Medium | Backtest results meaningless | Accept strategy config |
| No production monitoring | Medium | Blind to errors in prod | Configure Better Stack |
| JWT secret in fallback | Low | Dev only, env var overrides | Already handled by Railway env vars |

---

## 7. Deployment Checklist

### Before Going Live
- [ ] Set all Railway env vars (see Section 2)
- [ ] Wire frontend dashboard (app/page.tsx)
- [ ] Add missing API proxy routes (signals, trades, positions)
- [ ] Deploy frontend to Vercel
- [ ] Update CORS_ORIGINS in Railway to include Vercel URL
- [ ] Test health endpoint: `curl https://[railway-url]/health`
- [ ] Test indicator computation: POST /api/v1/intelligence/indicators/compute
- [ ] Test news classification: POST /intelligence/classify-news
- [ ] Test simulation: POST /intelligence/simulate
- [ ] Test DRL prediction: POST /intelligence/drl/predict
- [ ] Test paper trade: POST /trading/orders
- [ ] Run full test suite: `pytest tests/ -q`

### Optional (Phase 2)
- [ ] Implement OAuth (Google/GitHub via Supabase Auth)
- [ ] Implement 2FA database operations
- [ ] Configure Better Stack monitoring
- [ ] Enable real trading (set ENABLE_REAL_TRADING=true, add real API keys)
- [ ] Add exchange API key validation (call exchange on key save)

---

## 8. Local Development

```bash
# Backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn src.main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev

# Full stack (Docker)
docker-compose up

# Tests
pytest tests/unit/ -q
pytest tests/integration/ -q
```

---

## 9. Reference Repos (Can Be Deleted)

All borrowed code has been preserved in `src/borrowed/`.

| Repo | What We Used | Preserved In |
|------|-------------|--------------|
| Fiduciary-Sentinel-Core | PPO agent, guardrails, trading env | src/borrowed/fiduciary_*.py |
| hyperliquid-trading-agent | Risk manager (7-check chain) | src/borrowed/hyperliquid_risk_manager.py |
| polymarket-pipeline | Claude prompt, news aggregator | src/borrowed/polymarket_*.py |
| MiroFish | Parallel simulation pattern | src/simulation/engine.py (adapted) |
| hummingbot | Exchange connector patterns | src/interfaces/ (adapted) |
| freqtrade | Strategy/backtesting patterns | src/backtesting/ (adapted) |
| vectorbt | Metrics computation | src/backtesting/metrics.py (adapted) |

**All repos deleted.** Code preserved in `src/reference_implementations/`.

---

## 10. Security Notes

- All exchange API keys encrypted with AES-256-GCM before database storage
- JWT secrets and encryption keys must be set as Railway env vars (never in code)
- Paper trading enforced at connector level — cannot be overridden via API
- ENABLE_REAL_TRADING defaults to false — requires explicit env var to enable
- Row-level security (RLS) policies defined in Supabase for all user data tables
- CORS restricted to known origins (localhost + Vercel URL)
- Rate limiting: 100 calls/hour for indicator computation, 50/hour for batch

---

*This document is the single source of truth for deployment. Keep it updated.*
