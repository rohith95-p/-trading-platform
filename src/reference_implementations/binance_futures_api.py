"""
SOURCE: git repos/hyperliquid-trading-agent-master - Copy/src/trading/binance_api.py
PURPOSE: Binance USD-M Futures testnet client.
         Implements the same interface as our BinanceConnector (src/exchanges/binance.py)
         but uses the official binance-futures-connector SDK directly.

This is the ORIGINAL implementation. Our version in src/exchanges/binance.py
uses aiohttp directly for consistency with other connectors.

Key patterns we adapted:
- _retry() helper with exponential backoff
- _get_symbol() / _get_asset_from_symbol() conversion
- get_user_state() returning normalized position format
- Testnet URL: https://testnet.binancefuture.com

Usage (original):
    api = BinanceAPI()
    await api.place_buy_order("BTC", 0.001)
    state = await api.get_user_state()
    candles = await api.get_candles("BTC", "5m", 100)
"""

import asyncio
import logging


class BinanceAPI:
    """
    Binance Futures Testnet client using official SDK.
    Requires: pip install binance-futures-connector
    """

    def __init__(self, api_key: str = "", api_secret: str = "",
                 testnet: bool = True):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = "https://testnet.binancefuture.com" if testnet else "https://fapi.binance.com"

        try:
            from binance.um_futures import UMFutures
            self.client = UMFutures(key=api_key, secret=api_secret, base_url=self.base_url)
        except ImportError:
            logging.warning("binance-futures-connector not installed. Install with: pip install binance-futures-connector")
            self.client = None

    def _get_symbol(self, asset: str) -> str:
        return asset if "USDT" in asset else f"{asset}USDT"

    def _get_asset_from_symbol(self, symbol: str) -> str:
        return symbol.replace("USDT", "")

    async def _retry(self, fn, *args, max_attempts: int = 3, **kwargs):
        last_err = None
        for attempt in range(max_attempts):
            try:
                return await asyncio.to_thread(fn, *args, **kwargs)
            except Exception as e:
                last_err = e
                logging.warning("Binance call failed (attempt %s/%s): %s", attempt + 1, max_attempts, e)
                await asyncio.sleep(1.0 * (2 ** attempt))
        raise last_err

    async def place_buy_order(self, asset: str, amount: float):
        return await self._retry(self.client.new_order, symbol=self._get_symbol(asset), side="BUY", type="MARKET", quantity=round(amount, 3))

    async def place_sell_order(self, asset: str, amount: float):
        return await self._retry(self.client.new_order, symbol=self._get_symbol(asset), side="SELL", type="MARKET", quantity=round(amount, 3))

    async def place_limit_buy(self, asset: str, amount: float, limit_price: float, tif: str = "GTC"):
        return await self._retry(self.client.new_order, symbol=self._get_symbol(asset), side="BUY", type="LIMIT", quantity=round(amount, 3), price=limit_price, timeInForce=tif)

    async def place_limit_sell(self, asset: str, amount: float, limit_price: float, tif: str = "GTC"):
        return await self._retry(self.client.new_order, symbol=self._get_symbol(asset), side="SELL", type="LIMIT", quantity=round(amount, 3), price=limit_price, timeInForce=tif)

    async def place_take_profit(self, asset: str, is_buy: bool, amount: float, tp_price: float):
        side = "SELL" if is_buy else "BUY"
        return await self._retry(self.client.new_order, symbol=self._get_symbol(asset), side=side, type="TAKE_PROFIT_MARKET", quantity=round(amount, 3), stopPrice=tp_price, closePosition=True)

    async def place_stop_loss(self, asset: str, is_buy: bool, amount: float, sl_price: float):
        side = "SELL" if is_buy else "BUY"
        return await self._retry(self.client.new_order, symbol=self._get_symbol(asset), side=side, type="STOP_MARKET", quantity=round(amount, 3), stopPrice=sl_price, closePosition=True)

    async def cancel_order(self, asset: str, oid: int):
        return await self._retry(self.client.cancel_order, symbol=self._get_symbol(asset), orderId=oid)

    async def cancel_all_orders(self, asset: str):
        try:
            await self._retry(self.client.cancel_open_orders, symbol=self._get_symbol(asset))
            return {"status": "ok"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def get_user_state(self) -> dict:
        """Returns normalized account state: {balance, total_value, positions}"""
        try:
            resp = await self._retry(self.client.account)
            total_value = float(resp.get("totalWalletBalance", 0.0))
            avail_balance = float(resp.get("availableBalance", 0.0))
            positions = []
            for p in resp.get("positions", []):
                contracts = float(p.get("positionAmt", 0))
                if contracts == 0:
                    continue
                positions.append({
                    "coin": self._get_asset_from_symbol(p["symbol"]),
                    "entryPx": float(p.get("entryPrice", 0)),
                    "szi": contracts,
                    "pnl": float(p.get("unrealizedProfit", 0)),
                    "notional_entry": abs(float(p.get("notional", 0))),
                })
            return {"balance": avail_balance, "total_value": total_value, "positions": positions}
        except Exception as e:
            logging.error("get_user_state error: %s", e)
            return {"balance": 0.0, "total_value": 0.0, "positions": []}

    async def get_current_price(self, asset: str) -> float:
        ticker = await self._retry(self.client.ticker_price, symbol=self._get_symbol(asset))
        return float(ticker.get("price", 0.0))

    async def get_candles(self, asset: str, interval: str = "5m", count: int = 100) -> list:
        ohlcvs = await self._retry(self.client.klines, symbol=self._get_symbol(asset), interval=interval, limit=count)
        return [{"t": int(c[0]), "open": float(c[1]), "high": float(c[2]), "low": float(c[3]), "close": float(c[4]), "volume": float(c[5])} for c in ohlcvs]

    async def get_funding_rate(self, asset: str) -> float:
        try:
            funding = await self._retry(self.client.funding_rate, symbol=self._get_symbol(asset))
            if funding and isinstance(funding, list):
                return float(funding[-1].get("fundingRate", 0.0))
            return 0.0
        except Exception:
            return 0.0
