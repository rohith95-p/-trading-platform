"""Regression tests for the 2026-10-16 mechanical audit fixes."""
import os

from src.core import alerts, news_filter, risk_rules, trade_log, validation_ledger
from src.core.execution_handler import TradeRecord
from src.strategies.portfolio_v5_core import PORTFOLIO


def test_trade_record_reads_like_mt5_result():
    r = TradeRecord(ticket=7, strategy="X", direction="BUY", price=1.0, sl=0.5, tp=2.0,
                    atr=1.0, session="S", timestamp_ist="t", lots=0.01)
    assert r.order == 7 and r.retcode == 10009 and r.lots == 0.01


def test_vi3_magics_come_from_live_portfolio():
    from src.core import main_loop
    import inspect
    src = inspect.getsource(main_loop._check_vi3_tripwire)
    assert "PORTFOLIO_V5" in src and "3012" not in src
    assert {5001, 5002, 5003, 5005} == {int(c().magic) for c in PORTFOLIO}


def test_runtime_paths_are_absolute(monkeypatch):
    import importlib
    # conftest patches some of these per-test; check the module defaults on reload
    for mod, attr in ((trade_log, "LOG_DIR"), (risk_rules, "STATE_PATH"), (alerts, "ALERT_LOG"),
                      (validation_ledger, "LEDGER_PATH"), (news_filter, "NEWS_CALENDAR_PATH")):
        fresh = importlib.reload(mod)
        assert os.path.isabs(getattr(fresh, attr)), f"{mod.__name__}.{attr} is relative"
