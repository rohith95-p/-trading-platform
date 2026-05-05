"""
WebSocket service for real-time indicator updates.

Implements Task 2.8: Real-time Indicator Updates
Provides real-time streaming of technical indicators via WebSocket connections.

Features:
- Subscription model (clients subscribe to symbol/timeframe/indicators)
- Real-time updates when new market data arrives
- Connection lifecycle management (connect, disconnect, reconnect)
- Heartbeat/ping-pong for connection health
- Comprehensive error handling and logging
"""

import asyncio
import json
import logging
import time
from typing import Dict, List, Set, Optional, Any
from src.core.time import utc_now
from fastapi import WebSocket, WebSocketDisconnect
from dataclasses import dataclass, asdict
import numpy as np

from src.intelligence.indicator_registry import IndicatorRegistry
from src.intelligence.indicator_cache_service import get_cache_service

logger = logging.getLogger(__name__)


@dataclass
class IndicatorSubscription:
    """Represents a client's subscription to indicator updates."""
    symbol: str
    timeframe: str
    indicators: List[str]
    
    def to_key(self) -> str:
        """Generate unique key for this subscription."""
        return f"{self.symbol}:{self.timeframe}:{','.join(sorted(self.indicators))}"


@dataclass
class WebSocketClient:
    """Represents a connected WebSocket client."""
    websocket: WebSocket
    client_id: str
    subscriptions: Set[str]  # Set of subscription keys
    last_heartbeat: float
    connected_at: float
    
    def __hash__(self):
        return hash(self.client_id)
    
    def __eq__(self, other):
        if isinstance(other, WebSocketClient):
            return self.client_id == other.client_id
        return False


class IndicatorWebSocketManager:
    """
    Manages WebSocket connections for real-time indicator updates.
    
    Features:
    - Client connection management
    - Subscription handling
    - Real-time indicator broadcasting
    - Heartbeat monitoring
    - Automatic cleanup of stale connections
    """
    
    def __init__(self, heartbeat_interval: int = 30, heartbeat_timeout: int = 60):
        """
        Initialize WebSocket manager.
        
        Args:
            heartbeat_interval: Seconds between heartbeat checks (default 30)
            heartbeat_timeout: Seconds before considering connection stale (default 60)
        """
        self.clients: Dict[str, WebSocketClient] = {}
        self.subscriptions: Dict[str, Set[str]] = {}  # subscription_key -> set of client_ids
        self.heartbeat_interval = heartbeat_interval
        self.heartbeat_timeout = heartbeat_timeout
        self.registry = IndicatorRegistry()
        self.cache_service = get_cache_service()
        
        # Statistics
        self.stats = {
            "total_connections": 0,
            "active_connections": 0,
            "total_subscriptions": 0,
            "messages_sent": 0,
            "errors": 0,
        }
        
        # Start heartbeat monitor
        self._heartbeat_task: Optional[asyncio.Task] = None
    
    async def start_heartbeat_monitor(self):
        """Start background task for heartbeat monitoring."""
        if self._heartbeat_task is None or self._heartbeat_task.done():
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            logger.info("Heartbeat monitor started")
    
    async def stop_heartbeat_monitor(self):
        """Stop heartbeat monitoring task."""
        if self._heartbeat_task and not self._heartbeat_task.done():
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
            logger.info("Heartbeat monitor stopped")
    
    async def _heartbeat_loop(self):
        """Background task to monitor client heartbeats."""
        while True:
            try:
                await asyncio.sleep(self.heartbeat_interval)
                await self._check_heartbeats()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in heartbeat loop: {e}")
    
    async def _check_heartbeats(self):
        """Check all clients for stale connections."""
        current_time = time.time()
        stale_clients = []
        
        for client_id, client in self.clients.items():
            if current_time - client.last_heartbeat > self.heartbeat_timeout:
                stale_clients.append(client_id)
                logger.warning(f"Client {client_id} heartbeat timeout")
        
        # Disconnect stale clients
        for client_id in stale_clients:
            await self.disconnect(client_id)
    
    async def connect(self, websocket: WebSocket, client_id: str) -> WebSocketClient:
        """
        Accept and register a new WebSocket connection.
        
        Args:
            websocket: FastAPI WebSocket instance
            client_id: Unique client identifier
            
        Returns:
            WebSocketClient instance
        """
        await websocket.accept()
        
        current_time = time.time()
        client = WebSocketClient(
            websocket=websocket,
            client_id=client_id,
            subscriptions=set(),
            last_heartbeat=current_time,
            connected_at=current_time,
        )
        
        self.clients[client_id] = client
        self.stats["total_connections"] += 1
        self.stats["active_connections"] = len(self.clients)
        
        logger.info(f"WebSocket client {client_id} connected. Total: {len(self.clients)}")
        
        # Send welcome message
        await self.send_to_client(client_id, {
            "type": "connected",
            "client_id": client_id,
            "message": "Connected to indicator stream",
            "timestamp": utc_now().isoformat(),
        })
        
        return client
    
    async def disconnect(self, client_id: str):
        """
        Disconnect and cleanup a client.
        
        Args:
            client_id: Client identifier
        """
        if client_id not in self.clients:
            return
        
        client = self.clients[client_id]
        
        # Remove from all subscriptions
        for sub_key in client.subscriptions:
            if sub_key in self.subscriptions:
                self.subscriptions[sub_key].discard(client_id)
                if not self.subscriptions[sub_key]:
                    del self.subscriptions[sub_key]
        
        # Remove client
        del self.clients[client_id]
        self.stats["active_connections"] = len(self.clients)
        
        logger.info(f"WebSocket client {client_id} disconnected. Total: {len(self.clients)}")
    
    async def subscribe(self, client_id: str, subscription: IndicatorSubscription) -> Dict[str, Any]:
        """
        Subscribe a client to indicator updates.
        
        Args:
            client_id: Client identifier
            subscription: Subscription details
            
        Returns:
            Response dict with status
        """
        if client_id not in self.clients:
            return {"status": "error", "message": "Client not connected"}
        
        # Validate indicators
        available_indicators = self.registry.get_available_indicators()
        invalid_indicators = [ind for ind in subscription.indicators if ind not in available_indicators]
        
        if invalid_indicators:
            return {
                "status": "error",
                "message": f"Invalid indicators: {', '.join(invalid_indicators)}",
                "available": available_indicators,
            }
        
        # Validate timeframe
        valid_timeframes = ["1m", "5m", "15m", "1h", "4h", "1d"]
        if subscription.timeframe not in valid_timeframes:
            return {
                "status": "error",
                "message": f"Invalid timeframe. Must be one of: {', '.join(valid_timeframes)}",
            }
        
        # Add subscription
        sub_key = subscription.to_key()
        client = self.clients[client_id]
        client.subscriptions.add(sub_key)
        
        if sub_key not in self.subscriptions:
            self.subscriptions[sub_key] = set()
        self.subscriptions[sub_key].add(client_id)
        
        self.stats["total_subscriptions"] = sum(len(subs) for subs in self.subscriptions.values())
        
        logger.info(f"Client {client_id} subscribed to {sub_key}")
        
        return {
            "status": "success",
            "message": "Subscribed successfully",
            "subscription": asdict(subscription),
        }
    
    async def unsubscribe(self, client_id: str, subscription: IndicatorSubscription) -> Dict[str, Any]:
        """
        Unsubscribe a client from indicator updates.
        
        Args:
            client_id: Client identifier
            subscription: Subscription details
            
        Returns:
            Response dict with status
        """
        if client_id not in self.clients:
            return {"status": "error", "message": "Client not connected"}
        
        sub_key = subscription.to_key()
        client = self.clients[client_id]
        
        if sub_key in client.subscriptions:
            client.subscriptions.discard(sub_key)
            
            if sub_key in self.subscriptions:
                self.subscriptions[sub_key].discard(client_id)
                if not self.subscriptions[sub_key]:
                    del self.subscriptions[sub_key]
            
            self.stats["total_subscriptions"] = sum(len(subs) for subs in self.subscriptions.values())
            
            logger.info(f"Client {client_id} unsubscribed from {sub_key}")
            
            return {
                "status": "success",
                "message": "Unsubscribed successfully",
            }
        else:
            return {
                "status": "error",
                "message": "Subscription not found",
            }
    
    async def broadcast_indicator_update(
        self,
        symbol: str,
        timeframe: str,
        indicators: List[str],
        market_data: Dict[str, List[float]],
    ):
        """
        Broadcast indicator updates to subscribed clients.
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe
            indicators: List of indicator names
            market_data: Market data (highs, lows, closes, volumes)
        """
        try:
            # Compute indicators
            highs = np.array(market_data["highs"], dtype=float)
            lows = np.array(market_data["lows"], dtype=float)
            closes = np.array(market_data["closes"], dtype=float)
            volumes = np.array(market_data.get("volumes", []), dtype=float) if market_data.get("volumes") else None
            
            results = {}
            for indicator_name in indicators:
                try:
                    result = self.registry.compute(
                        indicator_name=indicator_name,
                        highs=highs,
                        lows=lows,
                        closes=closes,
                        volumes=volumes,
                    )
                    
                    # Convert to JSON-serializable format
                    if isinstance(result, np.ndarray):
                        valid_values = result[~np.isnan(result)]
                        results[indicator_name] = float(valid_values[-1]) if len(valid_values) > 0 else None
                    elif isinstance(result, dict):
                        results[indicator_name] = {}
                        for key, value in result.items():
                            if isinstance(value, np.ndarray):
                                valid_values = value[~np.isnan(value)]
                                results[indicator_name][key] = float(valid_values[-1]) if len(valid_values) > 0 else None
                            else:
                                results[indicator_name][key] = float(value) if value is not None else None
                    else:
                        results[indicator_name] = float(result) if result is not None else None
                
                except Exception as e:
                    logger.error(f"Error computing {indicator_name}: {e}")
                    results[indicator_name] = {"error": str(e)}
            
            # Find matching subscriptions
            subscription = IndicatorSubscription(
                symbol=symbol,
                timeframe=timeframe,
                indicators=indicators,
            )
            sub_key = subscription.to_key()
            
            if sub_key in self.subscriptions:
                # Broadcast to all subscribed clients
                message = {
                    "type": "indicator_update",
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "indicators": results,
                    "timestamp": utc_now().isoformat(),
                }
                
                for client_id in list(self.subscriptions[sub_key]):
                    await self.send_to_client(client_id, message)
        
        except Exception as e:
            logger.error(f"Error broadcasting indicator update: {e}")
            self.stats["errors"] += 1
    
    async def send_to_client(self, client_id: str, message: Dict[str, Any]):
        """
        Send message to a specific client.
        
        Args:
            client_id: Client identifier
            message: Message dict to send
        """
        if client_id not in self.clients:
            return
        
        client = self.clients[client_id]
        
        try:
            await client.websocket.send_json(message)
            self.stats["messages_sent"] += 1
        except Exception as e:
            logger.error(f"Error sending to client {client_id}: {e}")
            self.stats["errors"] += 1
            # Disconnect client on error
            await self.disconnect(client_id)
    
    async def handle_ping(self, client_id: str):
        """
        Handle ping from client and update heartbeat.
        
        Args:
            client_id: Client identifier
        """
        if client_id not in self.clients:
            return
        
        client = self.clients[client_id]
        client.last_heartbeat = time.time()
        
        await self.send_to_client(client_id, {
            "type": "pong",
            "timestamp": utc_now().isoformat(),
        })
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get WebSocket manager statistics.
        
        Returns:
            Dict with statistics
        """
        return {
            **self.stats,
            "subscriptions_by_key": {
                key: len(clients) for key, clients in self.subscriptions.items()
            },
        }


# Global WebSocket manager instance
_ws_manager: Optional[IndicatorWebSocketManager] = None


def get_ws_manager() -> IndicatorWebSocketManager:
    """Get or create global WebSocket manager instance."""
    global _ws_manager
    if _ws_manager is None:
        _ws_manager = IndicatorWebSocketManager()
    return _ws_manager


async def initialize_ws_manager():
    """Initialize global WebSocket manager."""
    manager = get_ws_manager()
    await manager.start_heartbeat_monitor()
    logger.info("WebSocket manager initialized")


async def close_ws_manager():
    """Close global WebSocket manager."""
    global _ws_manager
    if _ws_manager:
        await _ws_manager.stop_heartbeat_monitor()
        _ws_manager = None
    logger.info("WebSocket manager closed")
