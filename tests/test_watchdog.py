"""
Tests for watchdog crash recovery and alerting (P0-4).
"""

import sys
import pytest
from unittest.mock import Mock, patch

from scripts import watchdog
from src.core import alerts


class TestWatchdogCrashRecovery:
    """Tests for watchdog auto-restart, alerting, and fatal exit logic."""

    @patch('scripts.watchdog._start_loop')
    @patch('scripts.watchdog._alert')
    @patch('src.core.trade_log.lifecycle')
    def test_watchdog_restarts_main_loop_and_alerts_on_crash(self, mock_lifecycle, mock_alert, mock_start):
        """
        P0-4 Action 6: On crash, watchdog must alert, log traceback/lifecycle event,
        wait, and restart main_loop.
        """
        restarts = watchdog.handle_main_loop_crash(consecutive_restarts=0, wait_seconds=0)

        assert restarts == 1
        assert mock_alert.call_count == 1
        args, kwargs = mock_alert.call_args
        assert "crashed (attempt #1/3)" in args[0]
        assert kwargs.get("severity") == alerts.WARN

        assert mock_lifecycle.call_count == 1
        l_args, l_kwargs = mock_lifecycle.call_args
        assert l_args[0] == "watchdog_restart"
        assert l_kwargs.get("attempt") == 1

        assert mock_start.call_count == 1

    @patch('scripts.watchdog._start_loop')
    @patch('scripts.watchdog._alert')
    @patch('src.core.trade_log.lifecycle')
    def test_watchdog_fatal_exit_on_3_consecutive_restarts(self, mock_lifecycle, mock_alert, mock_start):
        """
        P0-4 Action 3: On 3rd consecutive restart failure, fire CRITICAL alert
        and exit non-zero (sys.exit(1)).
        """
        with pytest.raises(SystemExit) as exc_info:
            watchdog.handle_main_loop_crash(consecutive_restarts=2, wait_seconds=0)

        assert exc_info.value.code == 1

        assert mock_alert.call_count == 1
        args, kwargs = mock_alert.call_args
        assert "FATAL" in args[0]
        assert kwargs.get("severity") == alerts.CRITICAL

        assert mock_lifecycle.call_count == 1
        l_args, l_kwargs = mock_lifecycle.call_args
        assert l_args[0] == "watchdog_fatal_exit"
        assert l_kwargs.get("attempts") == 3

        mock_start.assert_not_called()
