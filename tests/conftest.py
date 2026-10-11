"""Global test configuration and fixtures for ultra_core test suite.

Ensures no unit tests ever communicate with external services (MT5 terminals,
Telegram bots, webhooks) or leak test notifications to production channels.
"""
import os
import sys
import types
import pytest
from unittest.mock import patch

# Cross-platform MT5 stubbing for environments without native MetaTrader5 (Linux CI/macOS)
if "MetaTrader5" not in sys.modules:
    try:
        import MetaTrader5  # noqa: F401
    except (ImportError, ModuleNotFoundError):
        _mt5 = types.ModuleType("MetaTrader5")
        _mt5.ORDER_TYPE_BUY = 0
        _mt5.ORDER_TYPE_SELL = 1
        _mt5.TRADE_ACTION_DEAL = 1
        _mt5.TRADE_ACTION_SLTP = 6
        _mt5.ORDER_TIME_GTC = 0
        _mt5.ORDER_FILLING_IOC = 1
        _mt5.TRADE_RETCODE_DONE = 10009
        _mt5.initialize = lambda *a, **kw: True
        _mt5.shutdown = lambda: None
        _mt5.account_info = lambda: None
        _mt5.symbol_info = lambda s: None
        _mt5.symbol_info_tick = lambda s: None
        _mt5.positions_get = lambda **kw: []
        _mt5.order_send = lambda r: None
        sys.modules["MetaTrader5"] = _mt5

# Prevent any test from sending live network alerts, even if individual tests don't patch
os.environ["ULTRA_DISABLE_ALERTS"] = "1"


@pytest.fixture(autouse=True)
def silence_all_alerts():
    """Globally block ALL live Telegram and webhook alerts across all tests.

    Prevents tests that exercise order execution, risk rules, circuit breakers,
    or watchdog alerts from firing real messages to the trader's phone.
    """
    with patch("src.core.alerts._telegram", return_value=True), \
         patch("src.core.alerts._webhook", return_value=True), \
         patch("src.core.alerts.send", return_value=True) as mock_send:
        yield mock_send
