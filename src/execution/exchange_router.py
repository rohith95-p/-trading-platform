"""Compatibility exchange router for legacy execution module imports.

This module preserves the earlier ``src.execution.exchange_router`` surface
used by tests and older callers while newer code migrates to
``src.exchanges.router``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from src.core.interfaces import ExchangeConnector, ExchangeType, Order


@dataclass
class _ConfiguredConnector:
    """Lightweight fallback connector for config-only initialization paths."""

    name: str
    type: ExchangeType = ExchangeType.CEX

    async def connect(self) -> None:
        return None

    async def disconnect(self) -> None:
        return None

    def is_connected(self) -> bool:
        return False


class ExchangeRouter:
    """Route exchange operations to registered connector instances."""

    def __init__(self) -> None:
        self.connectors: Dict[str, ExchangeConnector] = {}

    def register_connector(self, name: str, connector: ExchangeConnector) -> None:
        self.connectors[name.lower()] = connector

    def get_connector(self, name: str) -> ExchangeConnector:
        connector = self.connectors.get(name.lower())
        if connector is None:
            raise ValueError(f"Unknown exchange: {name}")
        return connector

    async def connect_all(self) -> None:
        for connector in self.connectors.values():
            await connector.connect()

    async def disconnect_all(self) -> None:
        for connector in self.connectors.values():
            await connector.disconnect()

    def get_connected_exchanges(self) -> List[str]:
        connected: List[str] = []
        for name, connector in self.connectors.items():
            if connector.is_connected():
                connected.append(name)
        return connected

    async def get_markets(self, exchange: str) -> Any:
        return await self.get_connector(exchange).get_markets()

    async def get_order_book(self, exchange: str, symbol: str) -> Any:
        return await self.get_connector(exchange).get_order_book(symbol)

    async def get_ticker(self, exchange: str, symbol: str) -> Any:
        return await self.get_connector(exchange).get_ticker(symbol)

    async def place_order(self, exchange: str, order: Order) -> Any:
        return await self.get_connector(exchange).place_order(order)

    async def cancel_order(self, exchange: str, order_id: str) -> None:
        await self.get_connector(exchange).cancel_order(order_id)

    async def get_position(self, exchange: str, symbol: str) -> Any:
        return await self.get_connector(exchange).get_position(symbol)

    async def get_positions(self, exchange: str) -> Any:
        return await self.get_connector(exchange).get_positions()

    async def get_balance(self, exchange: str) -> Any:
        return await self.get_connector(exchange).get_balance()

    def list_exchanges(self) -> List[Dict[str, Any]]:
        result: List[Dict[str, Any]] = []
        for name, connector in self.connectors.items():
            connector_type = getattr(connector, "type", None)
            if isinstance(connector_type, ExchangeType):
                connector_type = connector_type.value
            result.append(
                {
                    "name": name,
                    "type": connector_type,
                    "connected": connector.is_connected(),
                }
            )
        return result


_GLOBAL_ROUTER: Optional[ExchangeRouter] = None


def get_exchange_router() -> ExchangeRouter:
    global _GLOBAL_ROUTER
    if _GLOBAL_ROUTER is None:
        _GLOBAL_ROUTER = ExchangeRouter()
    return _GLOBAL_ROUTER


def _create_hyperliquid_connector(config: Dict[str, Any]) -> ExchangeConnector:
    try:
        from src.exchanges.hyperliquid import HyperliquidConnector

        return HyperliquidConnector(**config)
    except Exception:
        return _ConfiguredConnector(name="hyperliquid")


def _create_kraken_connector(config: Dict[str, Any]) -> ExchangeConnector:
    try:
        from src.exchanges.kraken import KrakenConnector

        return KrakenConnector(**config)
    except Exception:
        return _ConfiguredConnector(name="kraken")


def _create_binance_connector(config: Dict[str, Any]) -> ExchangeConnector:
    try:
        from src.exchanges.binance import BinanceConnector

        return BinanceConnector(**config)
    except Exception:
        return _ConfiguredConnector(name="binance")


def initialize_exchange_router(**config: Dict[str, Any]) -> ExchangeRouter:
    """Initialize global router using exchange-specific config payloads."""

    router = ExchangeRouter()

    hyperliquid_config = config.get("hyperliquid_config")
    if isinstance(hyperliquid_config, dict):
        router.register_connector(
            "hyperliquid", _create_hyperliquid_connector(hyperliquid_config)
        )

    kraken_config = config.get("kraken_config")
    if isinstance(kraken_config, dict):
        router.register_connector("kraken", _create_kraken_connector(kraken_config))

    binance_config = config.get("binance_config")
    if isinstance(binance_config, dict):
        router.register_connector("binance", _create_binance_connector(binance_config))

    global _GLOBAL_ROUTER
    _GLOBAL_ROUTER = router
    return router
