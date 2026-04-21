# Project Structure

## Backend Directory Structure

The Unified Trading Intelligence Platform Phase 1 MVP follows a modular architecture with clear separation of concerns.

```
.
├── src/                          # Source code
│   ├── api/                      # FastAPI application and REST endpoints
│   ├── core/                     # Core interfaces and types
│   │   └── interfaces/           # Pluggable architecture interfaces
│   ├── intelligence/             # Intelligence Layer
│   │                             # - News classification (Claude API)
│   │                             # - Technical analysis (20+ indicators)
│   │                             # - Multi-agent simulation
│   │                             # - DRL integration
│   ├── exchanges/                # Execution Layer
│   │                             # - Exchange connectors (Kalshi, Polymarket, Alpaca)
│   │                             # - Unified order routing
│   ├── drl/                      # Deep Reinforcement Learning
│   │                             # - PPO agent
│   │                             # - Trading environment
│   │                             # - Constitutional guardrails
│   ├── risk/                     # Risk Management
│   │                             # - Position limits
│   │                             # - Kelly criterion sizing
│   │                             # - Drawdown protection
│   └── data/                     # Data Management
│                                 # - Market data
│                                 # - Historical data
│                                 # - Caching
│
├── tests/                        # Test suite
│   ├── unit/                     # Unit tests (60% of test pyramid)
│   ├── property/                 # Property-based tests (Hypothesis)
│   ├── integration/              # Integration tests (30% of test pyramid)
│   ├── e2e/                      # End-to-end tests (10% of test pyramid)
│   └── performance/              # Performance and load tests (Locust)
│
└── docs/                         # Documentation
    ├── README.md                 # Documentation overview
    └── project-structure.md      # This file
```

## Key Components

### Intelligence Layer (`src/intelligence/`)
- **News Classifier**: Real-time news classification using Claude API
- **Technical Indicators**: 20+ indicators (EMA, RSI, MACD, ATR, BBands, ADX, OBV, VWAP)
- **Multi-Agent Simulator**: 10-agent simulation for high-stakes trades (>$1K)
- **DRL Integration**: Interface to DRL agents for AI-driven trading

### Execution Layer (`src/exchanges/`)
- **Exchange Connectors**: Kalshi, Polymarket, Alpaca (paper trading only in Phase 1)
- **Unified Routing**: Single interface for all exchanges via ExchangeConnector interface
- **Order Management**: Place, cancel, and track orders across exchanges

### Risk Management (`src/risk/`)
- **Position Limits**: Max 10% per asset, 50% total exposure
- **Kelly Criterion**: Optimal position sizing
- **Drawdown Protection**: Auto-halt on 10% daily drawdown
- **Constitutional Guardrails**: Safety rules for DRL agents

### DRL Agents (`src/drl/`)
- **PPO Agent**: Proximal Policy Optimization for trading decisions
- **Trading Environment**: Gym-compatible environment for training
- **Model Persistence**: Save/load trained models

### Core Interfaces (`src/core/interfaces/`)
- **ExchangeConnector**: Pluggable exchange integration
- **StrategyExecutor**: Pluggable trading strategies
- **Backtester**: Pluggable backtesting engines
- **DRLAgent**: Pluggable reinforcement learning agents

## Testing Strategy

### Test Pyramid (80% code coverage target)
- **Unit Tests (60%)**: Pure functions, business logic, utilities
- **Integration Tests (30%)**: API endpoints, database, exchanges
- **E2E Tests (10%)**: Critical user flows

### Property-Based Testing
- 15 correctness properties validated using Hypothesis
- Minimum 100 iterations per property test
- Tag format: `Feature: unified-trading-platform-phase-1, Property {number}: {property_text}`

## Design Principles

1. **Pluggable Architecture**: All major components implement well-defined interfaces
2. **Separation of Concerns**: Intelligence, Execution, and Risk layers are decoupled
3. **Safety First**: Paper trading only, constitutional guardrails, comprehensive risk management
4. **Performance**: Vectorized operations, caching, connection pooling
5. **Resilience**: Exponential backoff retries, circuit breakers, graceful degradation

## Next Steps

1. Implement core interfaces in `src/core/interfaces/`
2. Set up FastAPI application in `src/api/`
3. Integrate exchange connectors in `src/exchanges/`
4. Build intelligence layer components in `src/intelligence/`
5. Implement risk management in `src/risk/`
6. Add DRL agents in `src/drl/`
7. Write comprehensive tests in `tests/`
