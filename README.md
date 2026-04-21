# Unified Trading Intelligence Platform

A comprehensive trading platform with news classification, technical analysis, multi-agent simulation, DRL agents, backtesting, and advanced portfolio management.

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- Docker & Docker Compose (optional)

### Setup

1. **Clone the repository**
```bash
git clone <repo-url>
cd trading-platform
```

2. **Setup Backend**
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env

# Start services with Docker
docker-compose up -d
```

3. **Setup Frontend**
```bash
# Install dependencies
npm install

# Start development server
npm run dev
```

4. **Access the application**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

## Project Structure

```
trading-platform/
├── src/                    # Backend source code
│   ├── main.py            # FastAPI application
│   ├── config.py          # Configuration
│   ├── models.py          # Pydantic models
│   ├── interfaces/        # Core interfaces
│   ├── intelligence/      # Intelligence layer
│   ├── execution/         # Execution layer
│   ├── backtesting/       # Backtesting engine
│   └── utils/             # Utilities
├── frontend/              # Frontend source code
│   ├── app/               # Next.js app
│   ├── components/        # React components
│   ├── pages/             # Next.js pages
│   └── styles/            # Tailwind CSS
├── tests/                 # Test files
├── docs/                  # Documentation
├── docker-compose.yml     # Docker Compose configuration
├── requirements.txt       # Python dependencies
├── package.json          # Node dependencies
└── README.md             # This file
```

## Development

### Running Tests
```bash
# Unit tests
pytest tests/unit/ -v

# Property-based tests
pytest tests/property/ -v

# All tests with coverage
pytest --cov=src --cov-report=html
```

### Code Quality
```bash
# Linting
pylint src/

# Type checking
mypy src/

# Formatting
black src/
```

## Documentation

- [Specification](./docs/SPECIFICATION.md)
- [API Documentation](http://localhost:8000/docs)
- [Architecture](./docs/ARCHITECTURE.md)
- [Deployment Guide](./docs/DEPLOYMENT.md)

## Features

### Phase 1 MVP
- ✅ News classification with Claude API
- ✅ 20+ technical indicators
- ✅ 3 exchange connectors (Kalshi, Polymarket, Alpaca)
- ✅ Risk management with position limits
- ✅ PPO reinforcement learning agent
- ✅ Vectorized backtesting
- ✅ React dashboard with real-time updates

### Phase 1.5 Enhancements
- ✅ 4 new exchange connectors (Hyperliquid, dYdX, Kraken, Binance)
- ✅ 10+ additional technical indicators
- ✅ Multi-timeframe analysis
- ✅ Advanced charting with TradingView
- ✅ Portfolio analytics
- ✅ Risk analytics (VaR, CVaR, Sharpe)
- ✅ Webhook support
- ✅ Strategy management

## Contributing

1. Create a feature branch
2. Make your changes
3. Run tests and linting
4. Submit a pull request

## License

MIT License - see LICENSE file for details

## Support

For issues and questions, please open an issue on GitHub.

---

**Status**: Phase 1 MVP - In Development
**Timeline**: 24 weeks (6 months)
**Target**: Industrial-level trading platform
