# Phase 1 Months 3-4 Implementation Plan

## Executive Summary

This document provides a detailed implementation plan for executing all remaining Phase 1 tasks (Months 3-4). The plan breaks down 15 major tasks into 80+ sub-tasks with estimated effort, dependencies, and implementation strategy.

**Total Estimated Effort**: 30 days (240 hours)
**Current Status**: Completed Months 1-2 (Tasks 1.1-1.2, partial 1.3)
**Remaining**: Tasks 1.4-1.6 (Month 1-2 completion) + Tasks 2.1-2.4 (Month 2) + Tasks 3.1-3.5 (Month 3) + Tasks 4.1-4.6 (Month 4)

---

## MONTH 3: Execution + Simulation (Weeks 9-12)

### Task 3.1: Kalshi Connector
**Estimated Effort**: 2 days (16 hours)
**Dependencies**: ExchangeConnector interface (✅ Complete)
**Status**: Not Started

#### Implementation Strategy
1. **Research Kalshi API** (2 hours)
   - Review Kalshi API documentation
   - Understand authentication (API key + secret)
   - Identify market data endpoints
   - Identify order placement endpoints

2. **Implement Core Methods** (8 hours)
   - `connect()`: Authenticate with Kalshi API
   - `disconnect()`: Clean up connections
   - `getMarkets()`: Fetch available markets
   - `getOrderBook()`: Fetch order book for symbol
   - `getTicker()`: Fetch current price
   - `placeOrder()`: Place market/limit orders
   - `cancelOrder()`: Cancel existing orders
   - `getPosition()`: Get position for symbol
   - `getBalance()`: Get account balance

3. **Add Paper Trading Enforcement** (3 hours)
   - Add environment variable check for paper trading mode
   - Raise exception if real trading attempted
   - Add unit tests for paper trading enforcement

4. **Error Handling & Retries** (2 hours)
   - Implement exponential backoff (1s, 2s, 4s)
   - Add comprehensive error logging
   - Handle rate limiting (429 responses)

5. **Testing** (1 hour)
   - Unit tests for all methods
   - Integration tests with Kalshi testnet
   - Mock tests for CI/CD

#### Deliverables
- `src/exchanges/kalshi.py` (300-400 lines)
- `tests/unit/exchanges/test_kalshi.py` (200-300 lines)
- `tests/integration/exchanges/test_kalshi_integration.py` (150-200 lines)

#### Acceptance Criteria
- ✅ Implements ExchangeConnector interface
- ✅ Paper trading mode enforced
- ✅ Orders execute within 1 second
- ✅ Tests pass on testnet
- ✅ Validates Requirement 5

---

### Task 3.2: Polymarket Connector
**Estimated Effort**: 2 days (16 hours)
**Dependencies**: ExchangeConnector interface (✅ Complete)
**Status**: Not Started

#### Implementation Strategy
Similar to Kalshi but with Polymarket-specific API:
1. Research Polymarket API (2 hours)
2. Implement core methods (8 hours)
3. Add paper trading enforcement (3 hours)
4. Error handling & retries (2 hours)
5. Testing (1 hour)

#### Deliverables
- `src/exchanges/polymarket.py` (300-400 lines)
- `tests/unit/exchanges/test_polymarket.py` (200-300 lines)
- `tests/integration/exchanges/test_polymarket_integration.py` (150-200 lines)

#### Acceptance Criteria
- ✅ Implements ExchangeConnector interface
- ✅ Paper trading mode enforced
- ✅ Orders execute within 1 second
- ✅ Tests pass

---

### Task 3.3: Alpaca Connector
**Estimated Effort**: 2 days (16 hours)
**Dependencies**: ExchangeConnector interface (✅ Complete)
**Status**: Not Started

#### Implementation Strategy
1. Research Alpaca API (2 hours)
   - Alpaca has excellent Python SDK
   - Paper trading API available
   - Straightforward authentication

2. Implement core methods (8 hours)
   - Use Alpaca SDK for simplicity
   - Wrap SDK methods to match ExchangeConnector interface

3. Add paper trading enforcement (3 hours)
   - Enforce paper trading mode
   - Prevent real trading attempts

4. Error handling & retries (2 hours)
5. Testing (1 hour)

#### Deliverables
- `src/exchanges/alpaca.py` (300-400 lines)
- `tests/unit/exchanges/test_alpaca.py` (200-300 lines)
- `tests/integration/exchanges/test_alpaca_integration.py` (150-200 lines)

#### Acceptance Criteria
- ✅ Implements ExchangeConnector interface
- ✅ Paper trading mode enforced
- ✅ Orders execute within 1 second
- ✅ Tests pass with Alpaca paper API

---

### Task 3.4: Exchange Router + Risk Manager
**Estimated Effort**: 3 days (24 hours)
**Dependencies**: All 3 exchange connectors (Tasks 3.1-3.3)
**Status**: Not Started

#### Implementation Strategy

**Part 1: Exchange Router** (1 day, 8 hours)
1. Create router class (2 hours)
   - Route orders to correct exchange based on symbol
   - Maintain pool of exchange connectors
   - Handle connection management

2. Implement routing logic (3 hours)
   - Symbol → Exchange mapping
   - Load balancing across exchanges
   - Fallback handling

3. Testing (3 hours)
   - Unit tests for routing logic
   - Integration tests with mock exchanges

**Part 2: Risk Manager** (2 days, 16 hours)
1. Position limits enforcement (4 hours)
   - 10% max position size per asset
   - 50% max total exposure
   - 10x max leverage

2. Kelly criterion position sizing (4 hours)
   - Implement Kelly formula: f* = (bp - q) / b
   - Integrate with risk checks
   - Add configuration for Kelly fraction

3. Circuit breaker for daily drawdown (4 hours)
   - Track daily P&L
   - Halt trading if drawdown > 10%
   - Reset at market open

4. Automatic position close on 20% loss (2 hours)
   - Monitor position P&L
   - Auto-close if loss > 20%
   - Log all auto-closes

5. Testing (2 hours)
   - Property-based tests for risk limits
   - Unit tests for each component

#### Deliverables
- `src/exchanges/router.py` (200-300 lines)
- `src/risk/risk_manager.py` (400-500 lines)
- `tests/unit/exchanges/test_router.py` (150-200 lines)
- `tests/unit/risk/test_risk_manager.py` (300-400 lines)
- `tests/property/test_risk_properties.py` (200-300 lines)

#### Acceptance Criteria
- ✅ Routes orders to correct exchange
- ✅ Enforces 10% position limit
- ✅ Enforces 50% total exposure limit
- ✅ Enforces 10x max leverage
- ✅ Property tests pass (Properties 7, 8, 9, 10)
- ✅ Validates Requirement 6

---

### Task 3.5: Simulation Engine
**Estimated Effort**: 3 days (24 hours)
**Dependencies**: Risk Manager (Task 3.4)
**Status**: Not Started

#### Implementation Strategy

1. **Extract from MiroFish** (4 hours)
   - Review MiroFish simulation code
   - Identify core simulation logic
   - Adapt to use local LLM or OpenAI API

2. **Reduce Agent Count & Rounds** (4 hours)
   - Reduce from 1000 agents to 10
   - Reduce from 100 rounds to 5
   - Optimize for <30 sec execution

3. **Implement Simulation Engine** (8 hours)
   - Create SimulationEngine class
   - Implement agent initialization
   - Implement round execution
   - Implement consensus calculation
   - Implement confidence scoring

4. **Create REST API Endpoint** (4 hours)
   - `POST /intelligence/simulate`
   - Request validation
   - Response formatting
   - Error handling

5. **Auto-trigger for >$1K Trades** (2 hours)
   - Integrate with order placement
   - Automatic simulation trigger
   - Confidence threshold checks

6. **Testing** (2 hours)
   - Unit tests for simulation logic
   - Integration tests with API
   - Property-based tests (Properties 5, 6)

#### Deliverables
- `src/intelligence/simulation.py` (400-500 lines)
- `src/api/intelligence.py` - Add simulate endpoint (100-150 lines)
- `tests/unit/intelligence/test_simulation.py` (200-300 lines)
- `tests/property/test_simulation_properties.py` (150-200 lines)

#### Acceptance Criteria
- ✅ Simulation completes within 30 seconds
- ✅ Returns confidence score 0-1
- ✅ Provides reasoning with consensus/dissent
- ✅ Auto-triggers for trades >$1K
- ✅ Property tests pass (Properties 5, 6)
- ✅ Validates Requirement 4

---

## MONTH 4: DRL + Backtesting + UI (Weeks 13-16)

### Task 4.1: PPO Agent Implementation
**Estimated Effort**: 3 days (24 hours)
**Dependencies**: Risk Manager (Task 3.4)
**Status**: Not Started

#### Implementation Strategy

1. **Extract from Fiduciary Sentinel** (4 hours)
   - Review Fiduciary Sentinel PPO implementation
   - Identify core agent logic
   - Adapt to use stable-baselines3 library

2. **Implement DRLAgent Interface** (6 hours)
   - Create PPOAgent class
   - Implement `predict()` method
   - Implement `train()` method
   - Implement `save()` and `load()` methods

3. **Create Trading Environment** (6 hours)
   - Implement gym.Env for trading
   - Define state space (price, indicators, position)
   - Define action space (buy, sell, hold)
   - Implement reward function

4. **Create REST API Endpoint** (4 hours)
   - `POST /intelligence/drl/predict`
   - Request validation
   - Response formatting
   - Error handling

5. **Testing** (4 hours)
   - Unit tests for agent methods
   - Integration tests with API
   - Property-based tests for guardrails

#### Deliverables
- `src/drl/ppo_agent.py` (300-400 lines)
- `src/drl/trading_env.py` (200-300 lines)
- `src/api/intelligence.py` - Add drl/predict endpoint (100-150 lines)
- `tests/unit/drl/test_ppo_agent.py` (200-300 lines)
- `tests/property/test_drl_properties.py` (150-200 lines)

#### Acceptance Criteria
- ✅ Implements DRLAgent interface
- ✅ Predicts actions within 500ms
- ✅ Constitutional guardrails enforce risk limits
- ✅ Supports training on 1+ year of data
- ✅ Property tests pass (Property 11)
- ✅ Validates Requirement 7

---

### Task 4.2: Risk Guardrails
**Estimated Effort**: 2 days (16 hours)
**Dependencies**: PPO Agent (Task 4.1)
**Status**: Not Started

#### Implementation Strategy

1. **Extract from Fiduciary Sentinel** (2 hours)
   - Review Fiduciary Sentinel guardrails
   - Identify core safety rules

2. **Implement Guardrail Checks** (6 hours)
   - Position size limits
   - Leverage limits
   - Drawdown limits
   - Sector concentration limits
   - Correlation limits

3. **Integrate with DRL Agent** (4 hours)
   - Override dangerous actions to "hold"
   - Log all guardrail violations
   - Track guardrail effectiveness

4. **Testing** (4 hours)
   - Unit tests for each guardrail
   - Integration tests with DRL agent
   - Scenario tests for edge cases

#### Deliverables
- `src/risk/guardrails.py` (200-300 lines)
- `tests/unit/risk/test_guardrails.py` (200-300 lines)

#### Acceptance Criteria
- ✅ Guardrails prevent risk limit violations
- ✅ Dangerous actions overridden to "hold"
- ✅ Tests verify all guardrail scenarios

---

### Task 4.3: Pandas Backtester
**Estimated Effort**: 3 days (24 hours)
**Dependencies**: None (can be implemented independently)
**Status**: Not Started

#### Implementation Strategy

1. **Create PandasBacktester Class** (4 hours)
   - Implement Backtester interface
   - Vectorized operations using pandas
   - Support for multiple timeframes

2. **Implement Backtesting Logic** (8 hours)
   - Load historical data
   - Generate signals from strategy
   - Execute trades (vectorized)
   - Track positions and P&L
   - Account for fees and slippage

3. **Compute Performance Metrics** (6 hours)
   - Total return
   - Sharpe ratio
   - Maximum drawdown
   - Win rate
   - Profit factor
   - Trade duration

4. **Create REST API Endpoint** (4 hours)
   - `POST /backtest`
   - Request validation
   - Response formatting
   - Error handling

5. **Testing** (2 hours)
   - Unit tests for backtester
   - Property-based tests for metrics
   - Integration tests with API

#### Deliverables
- `src/backtest/pandas_backtester.py` (400-500 lines)
- `src/api/backtest.py` (150-200 lines)
- `tests/unit/backtest/test_pandas_backtester.py` (300-400 lines)
- `tests/property/test_backtest_properties.py` (200-300 lines)

#### Acceptance Criteria
- ✅ Implements Backtester interface
- ✅ Processes 1 year of data in 1-2 minutes
- ✅ Computes all required metrics
- ✅ Property tests pass (Properties 12, 13, 14, 15)
- ✅ Validates Requirement 8

---

### Task 4.4: Dashboard Frontend
**Estimated Effort**: 4 days (32 hours)
**Dependencies**: All backend APIs (Tasks 3.1-4.3)
**Status**: Not Started

#### Implementation Strategy

1. **Setup React/Next.js Project** (2 hours)
   - Configure Next.js with TypeScript
   - Setup Tailwind CSS
   - Setup API client (axios/fetch)

2. **Create Core Components** (12 hours)
   - Portfolio view (value, P&L, return)
   - Signal feed (real-time signals)
   - Trade history (with filters)
   - Positions view (current positions)
   - Backtesting UI (strategy selection, date range)

3. **Implement WebSocket Connections** (6 hours)
   - Connect to `/ws` endpoint
   - Subscribe to portfolio updates
   - Subscribe to trade executions
   - Subscribe to signal feed
   - Handle reconnection logic

4. **Add Real-Time Updates** (6 hours)
   - Update portfolio every 1 second
   - Update positions every 1 second
   - Update signal feed in real-time
   - Update trade history on new trades

5. **Testing** (6 hours)
   - Component tests
   - Integration tests
   - E2E tests

#### Deliverables
- `frontend/components/portfolio/PortfolioView.tsx` (200-300 lines)
- `frontend/components/signals/SignalFeed.tsx` (200-300 lines)
- `frontend/components/trades/TradeHistory.tsx` (200-300 lines)
- `frontend/components/positions/PositionsView.tsx` (200-300 lines)
- `frontend/components/backtesting/BacktestUI.tsx` (200-300 lines)
- `frontend/hooks/useWebSocket.ts` (100-150 lines)
- `frontend/lib/api.ts` (100-150 lines)
- `tests/frontend/` (300-400 lines)

#### Acceptance Criteria
- ✅ All components render correctly
- ✅ Real-time updates working
- ✅ WebSocket connections stable
- ✅ Dashboard loads within 2 seconds
- ✅ Validates Requirement 9

---

### Task 4.5: Integration Testing
**Estimated Effort**: 2 days (16 hours)
**Dependencies**: All components (Tasks 3.1-4.4)
**Status**: Not Started

#### Implementation Strategy

1. **API Endpoint Integration Tests** (4 hours)
   - Test all REST endpoints
   - Test request validation
   - Test error handling
   - Test authentication

2. **Exchange Connector Integration Tests** (4 hours)
   - Test with testnet APIs
   - Test order placement and cancellation
   - Test position tracking
   - Test error scenarios

3. **Database Integration Tests** (2 hours)
   - Test data persistence
   - Test migrations
   - Test RLS policies

4. **End-to-End User Flow Tests** (4 hours)
   - User registration → login
   - Add API keys
   - Create strategy
   - Place trade
   - View portfolio
   - Run backtest

5. **Setup CI/CD Pipeline** (2 hours)
   - GitHub Actions workflow
   - Run tests on push
   - Generate coverage report
   - Block deployment if tests fail

#### Deliverables
- `tests/integration/test_api_endpoints.py` (300-400 lines)
- `tests/integration/test_exchanges.py` (200-300 lines)
- `tests/integration/test_database.py` (150-200 lines)
- `tests/e2e/test_user_flows.py` (200-300 lines)
- `.github/workflows/test.yml` (50-100 lines)
- `tests/conftest.py` (100-150 lines)

#### Acceptance Criteria
- ✅ All integration tests pass
- ✅ 80%+ code coverage achieved
- ✅ CI/CD pipeline working
- ✅ Validates Requirement 17

---

### Task 4.6: Production Deployment
**Estimated Effort**: 2 days (16 hours)
**Dependencies**: All components (Tasks 3.1-4.5)
**Status**: Not Started

#### Implementation Strategy

1. **Deploy Backend to Railway** (4 hours)
   - Create Railway project
   - Configure environment variables
   - Deploy FastAPI application
   - Setup health checks
   - Configure auto-scaling

2. **Deploy Frontend to Vercel** (2 hours)
   - Create Vercel project
   - Configure environment variables
   - Deploy Next.js application
   - Setup custom domain (optional)

3. **Configure Production Environment** (4 hours)
   - Setup production database
   - Configure production API keys
   - Setup encryption keys
   - Configure rate limiting

4. **Setup Monitoring & Logging** (4 hours)
   - Integrate Better Stack
   - Configure log aggregation
   - Setup error tracking
   - Configure alerts

5. **Run Smoke Tests** (2 hours)
   - Test all critical endpoints
   - Test user flows
   - Verify monitoring

#### Deliverables
- `docs/PRODUCTION_DEPLOYMENT.md` (500+ lines)
- `.env.production` (template)
- `railway.json` (Railway configuration)
- `vercel.json` (Vercel configuration)
- `tests/smoke/test_production.py` (100-150 lines)

#### Acceptance Criteria
- ✅ Production deployment successful
- ✅ All services accessible via HTTPS
- ✅ Monitoring and alerts active
- ✅ 99% uptime target met
- ✅ Validates Requirements 10, 13

---

## Implementation Timeline

### Week 9-10: Exchange Connectors (Tasks 3.1-3.3)
- Day 1-2: Kalshi Connector
- Day 3-4: Polymarket Connector
- Day 5-6: Alpaca Connector
- **Deliverables**: 3 exchange connectors, 600+ lines of code, 30+ tests

### Week 11-12: Router + Risk Manager + Simulation (Tasks 3.4-3.5)
- Day 1-3: Exchange Router + Risk Manager
- Day 4-6: Simulation Engine
- **Deliverables**: Router, Risk Manager, Simulation Engine, 1000+ lines of code, 40+ tests

### Week 13-14: PPO Agent + Guardrails (Tasks 4.1-4.2)
- Day 1-3: PPO Agent Implementation
- Day 4-5: Risk Guardrails
- **Deliverables**: PPO Agent, Guardrails, 500+ lines of code, 30+ tests

### Week 15: Backtester (Task 4.3)
- Day 1-3: Pandas Backtester
- **Deliverables**: Backtester, 400+ lines of code, 20+ tests

### Week 16: Dashboard + Testing + Deployment (Tasks 4.4-4.6)
- Day 1-4: Dashboard Frontend
- Day 5-6: Integration Testing
- Day 7-8: Production Deployment
- **Deliverables**: Dashboard, Integration Tests, Production Deployment, 1500+ lines of code

---

## Total Effort Summary

| Phase | Tasks | Days | Hours | Lines of Code |
|-------|-------|------|-------|---------------|
| Month 3 | 3.1-3.5 | 12 | 96 | 2000+ |
| Month 4 | 4.1-4.6 | 18 | 144 | 3000+ |
| **Total** | **15** | **30** | **240** | **5000+** |

---

## Risk Mitigation

### High-Risk Areas
1. **Exchange API Integration**: Kalshi, Polymarket, Alpaca APIs may have rate limits or changes
   - Mitigation: Use testnet APIs, implement comprehensive error handling, add retry logic

2. **Performance**: Simulation engine must complete in <30 seconds
   - Mitigation: Profile code, optimize hot paths, use vectorized operations

3. **Risk Management**: Guardrails must prevent catastrophic losses
   - Mitigation: Extensive testing, property-based tests, manual review

4. **Frontend Real-Time Updates**: WebSocket connections must be stable
   - Mitigation: Implement reconnection logic, use heartbeats, test with high-frequency updates

### Mitigation Strategies
- Implement comprehensive error handling throughout
- Use property-based testing for critical algorithms
- Implement circuit breakers for external APIs
- Use caching to reduce API calls
- Implement rate limiting to stay within free tier quotas
- Use testnet APIs for integration testing

---

## Success Criteria

### Code Quality
- ✅ 80%+ code coverage
- ✅ All tests passing
- ✅ Type checking passing
- ✅ Linting passing
- ✅ No security vulnerabilities

### Functionality
- ✅ All 15 requirements validated
- ✅ All 15 tasks completed
- ✅ All 80+ sub-tasks completed
- ✅ All acceptance criteria met

### Performance
- ✅ API responses <500ms (p95)
- ✅ Simulation completes <30 seconds
- ✅ Backtester processes 1 year in 1-2 minutes
- ✅ Dashboard loads <2 seconds

### Deployment
- ✅ Backend deployed to Railway
- ✅ Frontend deployed to Vercel
- ✅ Database deployed to Supabase
- ✅ Monitoring and alerts active
- ✅ 99% uptime achieved

---

## Next Steps

1. **Review this plan** with stakeholders
2. **Prioritize tasks** if needed
3. **Begin implementation** with Task 3.1 (Kalshi Connector)
4. **Track progress** against timeline
5. **Adjust plan** as needed based on learnings

---

## References

- [Design Document](./kiro/specs/unified-trading-platform-phase-1/design.md)
- [Requirements Document](./kiro/specs/unified-trading-platform-phase-1/requirements.md)
- [Tasks Document](./kiro/specs/unified-trading-platform-phase-1/tasks.md)
- [Current Implementation Status](./PHASE_1_IMPLEMENTATION_STATUS.md)

