"""
End-to-end user flow tests.

Tests key user journeys through the FastAPI application using TestClient
with mocked dependencies (no real API calls, no real DB writes).

Flows covered:
1. User places a trade  (risk check → order placement → position update)
2. User runs a backtest (submit data → get results)
3. User gets DRL prediction (state → prediction → guardrail check)
4. User runs simulation  (symbol → consensus result)
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from fastapi.testclient import TestClient

from src.main import app
from src.interfaces.exchange_connector import Order, Trade, Position, Balance
from src.exchanges.router import ExchangeRouter
from src.risk.manager import RiskManager
from src.risk.circuit_breaker import CircuitBreaker
from src.api.trading import get_exchange_router, get_risk_manager, get_circuit_breaker


# ---------------------------------------------------------------------------
# Shared client fixture
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def client():
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


# ===========================================================================
# Flow 1: User places a trade
# ===========================================================================


class TestUserPlacesTrade:
    """
    Flow: risk check → order placement → position update.

    The trading API validates the order against risk limits, routes it to the
    correct exchange connector, and returns a trade confirmation.
    """

    def _make_trade(self):
        return Trade(
            id="trade_001",
            symbol="AAPL",
            side="buy",
            price=150.0,
            size=5.0,
            fee=0.75,
            timestamp=datetime.utcnow(),
        )

    def test_place_trade_success(self, client):
        """Happy path: valid order passes risk checks and is executed."""
        mock_trade = self._make_trade()

        mock_router = MagicMock(spec=ExchangeRouter)
        mock_router.get_all_positions = AsyncMock(return_value={"alpaca": []})
        mock_router.place_order = AsyncMock(return_value=mock_trade)

        mock_risk = MagicMock(spec=RiskManager)
        mock_risk.validate_order = MagicMock()  # no exception = valid

        mock_cb = MagicMock(spec=CircuitBreaker)
        mock_cb.is_triggered = MagicMock(return_value=False)

        app.dependency_overrides[get_exchange_router] = lambda: mock_router
        app.dependency_overrides[get_risk_manager] = lambda: mock_risk
        app.dependency_overrides[get_circuit_breaker] = lambda: mock_cb

        try:
            response = client.post(
                "/trading/orders",
                json={
                    "exchange": "alpaca",
                    "symbol": "AAPL",
                    "side": "buy",
                    "type": "market",
                    "size": 5.0,
                    "portfolio_value": 10000.0,
                },
            )
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()
        assert data["trade_id"] == "trade_001"
        assert data["symbol"] == "AAPL"
        assert data["side"] == "buy"
        assert data["size"] == 5.0
        assert data["price"] == 150.0

    def test_place_trade_circuit_breaker_blocks(self, client):
        """Circuit breaker active → 403 Forbidden."""
        mock_cb = MagicMock(spec=CircuitBreaker)
        mock_cb.is_triggered = MagicMock(return_value=True)

        app.dependency_overrides[get_circuit_breaker] = lambda: mock_cb

        try:
            response = client.post(
                "/trading/orders",
                json={
                    "exchange": "alpaca",
                    "symbol": "AAPL",
                    "side": "buy",
                    "type": "market",
                    "size": 5.0,
                    "portfolio_value": 10000.0,
                },
            )
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 403

    def test_place_trade_risk_violation_rejected(self, client):
        """Order that violates risk limits → 422 Unprocessable Entity."""
        mock_router = MagicMock(spec=ExchangeRouter)
        mock_router.get_all_positions = AsyncMock(return_value={"alpaca": []})

        mock_risk = MagicMock(spec=RiskManager)
        mock_risk.validate_order = MagicMock(
            side_effect=ValueError("Order notional exceeds 10% position limit")
        )

        mock_cb = MagicMock(spec=CircuitBreaker)
        mock_cb.is_triggered = MagicMock(return_value=False)

        app.dependency_overrides[get_exchange_router] = lambda: mock_router
        app.dependency_overrides[get_risk_manager] = lambda: mock_risk
        app.dependency_overrides[get_circuit_breaker] = lambda: mock_cb

        try:
            response = client.post(
                "/trading/orders",
                json={
                    "exchange": "alpaca",
                    "symbol": "AAPL",
                    "side": "buy",
                    "type": "market",
                    "size": 9999.0,  # Huge size
                    "portfolio_value": 10000.0,
                },
            )
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 422

    def test_place_trade_unknown_exchange_returns_404(self, client):
        """Unknown exchange name → 404 Not Found."""
        mock_router = MagicMock(spec=ExchangeRouter)
        mock_router.get_all_positions = AsyncMock(return_value={})
        mock_router.place_order = AsyncMock(side_effect=KeyError("Connector 'ghost' not found"))

        mock_risk = MagicMock(spec=RiskManager)
        mock_risk.validate_order = MagicMock()

        mock_cb = MagicMock(spec=CircuitBreaker)
        mock_cb.is_triggered = MagicMock(return_value=False)

        app.dependency_overrides[get_exchange_router] = lambda: mock_router
        app.dependency_overrides[get_risk_manager] = lambda: mock_risk
        app.dependency_overrides[get_circuit_breaker] = lambda: mock_cb

        try:
            response = client.post(
                "/trading/orders",
                json={
                    "exchange": "ghost",
                    "symbol": "AAPL",
                    "side": "buy",
                    "type": "market",
                    "size": 1.0,
                    "portfolio_value": 10000.0,
                },
            )
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 404

    def test_get_positions_after_trade(self, client):
        """GET /trading/positions returns positions from all exchanges."""
        pos = Position(
            id="pos_001",
            symbol="AAPL",
            side="long",
            size=5.0,
            entry_price=150.0,
            current_price=155.0,
            pnl=25.0,
            pnl_percent=3.33,
        )
        mock_router = MagicMock(spec=ExchangeRouter)
        mock_router.get_all_positions = AsyncMock(return_value={"alpaca": [pos]})

        app.dependency_overrides[get_exchange_router] = lambda: mock_router

        try:
            response = client.get("/trading/positions")
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()
        assert data["total_positions"] == 1
        assert "alpaca" in data["positions"]
        assert data["positions"]["alpaca"][0]["symbol"] == "AAPL"


# ===========================================================================
# Flow 2: User runs a backtest
# ===========================================================================


class TestUserRunsBacktest:
    """
    Flow: submit OHLCV data → backtester processes → return metrics + trades.
    """

    def _ohlcv_bars(self, n=60):
        """Generate n simple OHLCV bars with valid dates."""
        from datetime import date, timedelta
        bars = []
        price = 100.0
        start = date(2024, 1, 1)
        for i in range(n):
            d = start + timedelta(days=i)
            bars.append({
                "datetime": d.strftime("%Y-%m-%dT00:00:00"),
                "open": price,
                "high": price + 1.0,
                "low": price - 1.0,
                "close": price + 0.5,
                "volume": 10000.0,
            })
            price += 0.5
        return bars

    def test_backtest_success(self, client):
        """Valid OHLCV data returns backtest metrics."""
        response = client.post(
            "/api/v1/backtest",
            json={
                "strategy_name": "simple_ma",
                "historical_data": self._ohlcv_bars(60),
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["strategy_name"] == "simple_ma"
        assert "metrics" in data
        assert "equity_curve" in data
        assert "trades" in data
        metrics = data["metrics"]
        assert "total_return" in metrics
        assert "sharpe_ratio" in metrics
        assert "max_drawdown" in metrics
        assert "win_rate" in metrics

    def test_backtest_with_config(self, client):
        """Backtest accepts optional fee/slippage config."""
        response = client.post(
            "/api/v1/backtest",
            json={
                "strategy_name": "fee_test",
                "historical_data": self._ohlcv_bars(30),
                "config": {"fee_rate": 0.002, "slippage_rate": 0.001},
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["strategy_name"] == "fee_test"

    def test_backtest_returns_date_range(self, client):
        """Backtest response includes start_date and end_date."""
        response = client.post(
            "/api/v1/backtest",
            json={
                "strategy_name": "date_check",
                "historical_data": self._ohlcv_bars(30),
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "start_date" in data
        assert "end_date" in data

    def test_backtest_equity_curve_length(self, client):
        """Equity curve has at least one data point."""
        bars = self._ohlcv_bars(30)
        response = client.post(
            "/api/v1/backtest",
            json={
                "strategy_name": "equity_check",
                "historical_data": bars,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["equity_curve"]) >= 1


# ===========================================================================
# Flow 3: User gets DRL prediction
# ===========================================================================


class TestUserGetsDRLPrediction:
    """
    Flow: state vector → PPO agent predicts action → guardrail check → response.
    """

    def _state(self, n=10):
        return [float(i) * 0.1 for i in range(n)]

    def test_drl_predict_success(self, client):
        """Valid state vector returns action, action_name, confidence."""
        response = client.post(
            "/intelligence/drl/predict",
            json={"state": self._state(10)},
        )

        assert response.status_code == 200
        data = response.json()
        assert "action" in data
        assert data["action"] in (0, 1, 2)
        assert "action_name" in data
        assert data["action_name"] in ("hold", "buy", "sell")
        assert "confidence" in data
        assert 0.0 <= data["confidence"] <= 1.0
        assert "guardrail_applied" in data

    def test_drl_predict_with_context(self, client):
        """State with context dict is accepted."""
        response = client.post(
            "/intelligence/drl/predict",
            json={
                "state": self._state(10),
                "context": {"circuit_breaker_triggered": False, "current_leverage": 1.0},
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["action"] in (0, 1, 2)

    def test_drl_predict_circuit_breaker_forces_hold(self, client):
        """When circuit breaker is triggered in context, action is HOLD (0).

        The guardrail forces HOLD only when the raw action is not HOLD.
        An untrained agent already returns HOLD, so guardrail_applied may be False.
        Either way, the final action must be HOLD.
        """
        response = client.post(
            "/intelligence/drl/predict",
            json={
                "state": self._state(10),
                "context": {"circuit_breaker_triggered": True},
            },
        )

        assert response.status_code == 200
        data = response.json()
        # Circuit breaker must result in HOLD action
        assert data["action"] == 0  # HOLD

    def test_drl_predict_invalid_state_rejected(self, client):
        """Empty state vector is rejected with 422."""
        response = client.post(
            "/intelligence/drl/predict",
            json={"state": []},
        )

        assert response.status_code == 422

    def test_drl_predict_confidence_range(self, client):
        """Confidence is always in [0, 1]."""
        for _ in range(3):
            response = client.post(
                "/intelligence/drl/predict",
                json={"state": self._state(10)},
            )
            assert response.status_code == 200
            data = response.json()
            assert 0.0 <= data["confidence"] <= 1.0


# ===========================================================================
# Flow 4: User runs simulation
# ===========================================================================


class TestUserRunsSimulation:
    """
    Flow: symbol + context → multi-agent simulation → consensus result.
    """

    def test_simulation_success(self, client):
        """Valid symbol returns consensus, confidence, votes, duration."""
        response = client.post(
            "/intelligence/simulate",
            json={"symbol": "BTC-USD"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "consensus" in data
        assert data["consensus"] in ("BUY", "SELL", "HOLD")
        assert "confidence" in data
        assert 0.0 <= data["confidence"] <= 1.0
        assert "votes" in data
        assert len(data["votes"]) > 0
        assert "duration_seconds" in data
        assert data["duration_seconds"] >= 0

    def test_simulation_with_context(self, client):
        """Simulation accepts optional market context."""
        response = client.post(
            "/intelligence/simulate",
            json={
                "symbol": "ETH-USD",
                "context": {"price": 3000.0, "rsi": 55.0},
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["consensus"] in ("BUY", "SELL", "HOLD")

    def test_simulation_auto_trigger_flag(self, client):
        """trade_value > $1K sets auto_triggered=True."""
        response = client.post(
            "/intelligence/simulate",
            json={
                "symbol": "BTC-USD",
                "trade_value": 1500.0,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["auto_triggered"] is True

    def test_simulation_no_auto_trigger_below_threshold(self, client):
        """trade_value <= $1K sets auto_triggered=False."""
        response = client.post(
            "/intelligence/simulate",
            json={
                "symbol": "BTC-USD",
                "trade_value": 500.0,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["auto_triggered"] is False

    def test_simulation_votes_structure(self, client):
        """Each vote has agent_id, action, confidence, round, reasoning."""
        response = client.post(
            "/intelligence/simulate",
            json={"symbol": "AAPL"},
        )

        assert response.status_code == 200
        data = response.json()
        for vote in data["votes"]:
            assert "agent_id" in vote
            assert "action" in vote
            assert "confidence" in vote
            assert "round" in vote
            assert "reasoning" in vote

    def test_simulation_missing_symbol_rejected(self, client):
        """Missing symbol field returns 422."""
        response = client.post(
            "/intelligence/simulate",
            json={"context": {"price": 100.0}},
        )

        assert response.status_code == 422
