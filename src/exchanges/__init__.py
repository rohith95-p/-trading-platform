"""Exchange connector exports.

Connectors are imported lazily so optional exchange SDK dependencies do not
break application startup when that exchange is not configured.
"""

__all__ = [
    "HyperliquidConnector",
    "dYdXConnector",
    "KrakenConnector",
    "BinanceConnector",
    "KalshiConnector",
    "PolymarketConnector",
    "AlpacaConnector",
]

_CONNECTOR_MODULES = {
    "HyperliquidConnector": ".hyperliquid",
    "dYdXConnector": ".dydx",
    "KrakenConnector": ".kraken",
    "BinanceConnector": ".binance",
    "KalshiConnector": ".kalshi",
    "PolymarketConnector": ".polymarket",
    "AlpacaConnector": ".alpaca",
}


def __getattr__(name: str):
    if name not in _CONNECTOR_MODULES:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    from importlib import import_module

    module = import_module(_CONNECTOR_MODULES[name], __name__)
    value = getattr(module, name)
    globals()[name] = value
    return value
