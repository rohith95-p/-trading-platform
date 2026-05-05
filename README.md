# Unified Trading Intelligence Platform

> Multi-exchange, multi-intelligence trading platform combining technical analysis, news classification, multi-agent simulation, and deep reinforcement learning.

## Status: ~82% Complete

| Layer | Status |
|-------|--------|
| 21 Technical Indicators + WebSocket | ✅ Production-ready |
| News Classification (Claude API) | ✅ Complete |
| Multi-Agent Simulation (10 agents) | ✅ Complete |
| PPO DRL Agent + Guardrails | ✅ Complete |
| 7 Exchange Connectors (paper trading) | ✅ Complete |
| Risk Management (Kelly, circuit breaker) | ✅ Complete |
| Vectorized Backtester | ✅ Complete |
| Auth + RBAC + API Key Encryption | ✅ Complete |
| Frontend Components | ✅ Built |
| Frontend Dashboard (wired) | ⚠️ In progress |
| Railway Backend Deployment | ✅ Live |
| Supabase Database | ✅ Connected |

## Quick Start

### Backend

```bash
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
cp .env.example .env.local  # Fill in your keys
uvicorn src.main:app --reload
```

API docs: http://localhost:8000/docs

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Dashboard: http://localhost:3000

## Architecture

```
src/
├── api/           # FastAPI routers (auth, trading, intelligence, backtesting, simulation, drl, webhooks)
├── intelligence/  # 21 indicators, news classifier, WebSocket streaming
├── exchanges/     # 7 connectors: Kalshi, Polymarket, Alpaca, Hyperliquid, dYdX, Kraken, Binance
├── risk/          # RiskManager, PositionSizer (Kelly), CircuitBreaker, AdvancedAnalytics
├── simulation/    # SimulationEngine (10 agents, 5 rounds), ConsensusBuilder
├── drl/           # PPOAgent, ConstitutionalGuardrails, TradingEnvironment
├── backtesting/   # PandasBacktester, metrics, advanced filters
├── portfolio/     # MultiStrategyPortfolio
├── auth/          # JWT, sessions, RBAC
└── borrowed/      # Original code from reference repos (preserved before repo deletion)
```

## Key Files

- `PROJECT_DEEP_ANALYSIS.md` — Complete project analysis, every file explained
- `PLACEHOLDERS_AND_TODOS.md` — What still needs real values/implementation
- `CLEANUP_PLAN.md` — Files awaiting deletion approval
- `.env.local` — Your actual secrets (gitignored)
- `.env.railway.example` — Template for Railway env vars

## Tests

```bash
pytest tests/unit/ -q          # 88+ unit tests
pytest tests/integration/ -q   # Integration tests
pytest tests/e2e/ -q           # E2E user flow tests
```

## Deployment

- **Backend**: Railway (already deployed)
- **Database**: Supabase (already connected)
- **Frontend**: Vercel (pending)

See `docs/RAILWAY_DEPLOYMENT_GUIDE.md` for details.

## Reference Repos (Borrowed From)

| Repo | What We Used |
|------|-------------|
| Fiduciary-Sentinel-Core | PPO agent architecture, constitutional guardrails, trading env |
| hyperliquid-trading-agent | Risk manager (7-check validation chain) |
| polymarket-pipeline | Claude classification prompt, news aggregator |
| MiroFish | Parallel simulation runner pattern |

Original code preserved in `src/borrowed/` before repos are deleted.
