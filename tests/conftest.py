"""Global test configuration and fixtures for ultra_core test suite.

Ensures no unit tests ever communicate with external services (MT5 terminals,
Telegram bots, webhooks) or leak test notifications to production channels.
"""
import os
import pytest
from unittest.mock import patch

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
