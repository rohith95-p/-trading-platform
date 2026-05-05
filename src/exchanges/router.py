"""
Exchange Router - routes orders to the correct exchange connector.
"""

from typing import Dict, List, Optional
from src.interfaces.exchange_connector import ExchangeConnector, Order, Trade, Position, Balance
import logging

log = logging.getLogger(__name__)


class ExchangeRouter:
    """
    Routes orders and queries to the appropriate exchange connector.

    Supports adding/removing connectors at runtime and aggregating
    data (positions, balances) across all registered exchanges.
    """

    def __init__(self):
        self._connectors: Dict[str, ExchangeConnector] = {}

    # -------------------------------------------------------------------------
    # Connector management
    # -------------------------------------------------------------------------

    def add_connector(self, connector: ExchangeConnector) -> None:
        """Register an exchange connector by its name."""
        self._connectors[connector.name] = connector
        log.info(f"Registered connector: {connector.name}")

    def remove_connector(self, name: str) -> None:
        """Remove a registered connector by name."""
        if name in self._connectors:
            del self._connectors[name]
            log.info(f"Removed connector: {name}")
        else:
            raise KeyError(f"Connector '{name}' not found")

    def get_connector(self, name: str) -> ExchangeConnector:
        """Return the connector for the given exchange name."""
        if name not in self._connectors:
            raise KeyError(f"Connector '{name}' not found. Available: {list(self._connectors)}")
        return self._connectors[name]

    @property
    def connector_names(self) -> List[str]:
        """Return list of registered connector names."""
        return list(self._connectors.keys())

    # -------------------------------------------------------------------------
    # Order routing
    # -------------------------------------------------------------------------

    async def place_order(self, exchange_name: str, order: Order) -> Trade:
        """
        Place an order on the specified exchange.

        Args:
            exchange_name: Name of the target exchange connector.
            order: Order to place.

        Returns:
            Trade object with execution details.
        """
        connector = self.get_connector(exchange_name)
        log.info(f"Routing order to {exchange_name}: {order.symbol} {order.side} {order.size}")
        return await connector.place_order(order)

    async def cancel_order(self, exchange_name: str, order_id: str) -> bool:
        """Cancel an order on the specified exchange."""
        connector = self.get_connector(exchange_name)
        return await connector.cancel_order(order_id)

    # -------------------------------------------------------------------------
    # Aggregated queries
    # -------------------------------------------------------------------------

    async def get_all_positions(self) -> Dict[str, List[Position]]:
        """
        Fetch open positions from all registered exchanges.

        Returns:
            Dict mapping exchange name -> list of positions.
        """
        result: Dict[str, List[Position]] = {}
        for name, connector in self._connectors.items():
            try:
                result[name] = await connector.get_positions()
            except Exception as exc:
                log.error(f"Failed to fetch positions from {name}: {exc}")
                result[name] = []
        return result

    async def get_total_balance(self) -> float:
        """
        Sum the total balance across all registered exchanges.

        Returns:
            Combined total balance (float).
        """
        total = 0.0
        for name, connector in self._connectors.items():
            try:
                balance: Balance = await connector.get_balance()
                total += balance.total
            except Exception as exc:
                log.error(f"Failed to fetch balance from {name}: {exc}")
        return total

    async def get_balances(self) -> Dict[str, Balance]:
        """
        Fetch balances from all registered exchanges.

        Returns:
            Dict mapping exchange name -> Balance.
        """
        result: Dict[str, Balance] = {}
        for name, connector in self._connectors.items():
            try:
                result[name] = await connector.get_balance()
            except Exception as exc:
                log.error(f"Failed to fetch balance from {name}: {exc}")
        return result
