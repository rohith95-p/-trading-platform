"""
Integration tests for real-time indicator WebSocket endpoints.

Tests Task 2.8: Real-time Indicator Updates
"""

import pytest
import json
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock
import numpy as np

from src.intelligence.indicator_websocket_service import (
    IndicatorWebSocketManager,
    IndicatorSubscription,
    WebSocketClient,
)


@pytest.fixture
def ws_manager():
    """Create WebSocket manager instance."""
    return IndicatorWebSocketManager(heartbeat_interval=1, heartbeat_timeout=2)


class TestWebSocketConnection:
    """Test WebSocket connection establishment and lifecycle."""
    
    def test_websocket_connection(self, client):
        """Test WebSocket connection establishment."""
        with client.websocket_connect("/api/v1/intelligence/ws/indicators") as websocket:
            # Should receive welcome message
            data = websocket.receive_json()
            
            assert data["type"] == "connected"
            assert "client_id" in data
            assert "message" in data
            assert "timestamp" in data
    
    def test_websocket_ping_pong(self, client):
        """Test WebSocket ping/pong heartbeat."""
        with client.websocket_connect("/api/v1/intelligence/ws/indicators") as websocket:
            # Receive welcome message
            websocket.receive_json()
            
            # Send ping
            websocket.send_text("ping")
            
            # Should receive pong
            data = websocket.receive_json()
            assert data["type"] == "pong"
            assert "timestamp" in data
    
    def test_multiple_connections(self, client):
        """Test multiple simultaneous WebSocket connections."""
        connections = []
        
        try:
            # Open 3 connections
            for _ in range(3):
                ws = client.websocket_connect("/api/v1/intelligence/ws/indicators")
                ws.__enter__()
                connections.append(ws)
                
                # Receive welcome message
                data = ws.receive_json()
                assert data["type"] == "connected"
            
            # All connections should be active
            assert len(connections) == 3
        
        finally:
            # Close all connections
            for ws in connections:
                ws.__exit__(None, None, None)


class TestIndicatorSubscription:
    """Test indicator subscription functionality."""
    
    def test_subscribe_valid_indicators(self, client):
        """Test subscribing to valid indicators."""
        with client.websocket_connect("/api/v1/intelligence/ws/indicators") as websocket:
            # Receive welcome message
            websocket.receive_json()
            
            # Subscribe to indicators
            websocket.send_json({
                "action": "subscribe",
                "symbol": "BTC-USD",
                "timeframe": "1h",
                "indicators": ["EMA_20", "RSI_14", "MACD"]
            })
            
            # Should receive subscription confirmation
            data = websocket.receive_json()
            assert data["type"] == "subscribed"
            assert data["status"] == "success"
            assert "subscription" in data
    
    def test_subscribe_invalid_indicators(self, client):
        """Test subscribing to invalid indicators."""
        with client.websocket_connect("/api/v1/intelligence/ws/indicators") as websocket:
            # Receive welcome message
            websocket.receive_json()
            
            # Subscribe to invalid indicators
            websocket.send_json({
                "action": "subscribe",
                "symbol": "BTC-USD",
                "timeframe": "1h",
                "indicators": ["INVALID_INDICATOR"]
            })
            
            # Should receive error
            data = websocket.receive_json()
            assert data["type"] == "error"
            assert "Invalid indicators" in data["message"]
    
    def test_subscribe_invalid_timeframe(self, client):
        """Test subscribing with invalid timeframe."""
        with client.websocket_connect("/api/v1/intelligence/ws/indicators") as websocket:
            # Receive welcome message
            websocket.receive_json()
            
            # Subscribe with invalid timeframe
            websocket.send_json({
                "action": "subscribe",
                "symbol": "BTC-USD",
                "timeframe": "invalid",
                "indicators": ["EMA_20"]
            })
            
            # Should receive error
            data = websocket.receive_json()
            assert data["type"] == "error"
            assert "Invalid timeframe" in data["message"]
    
    def test_subscribe_missing_fields(self, client):
        """Test subscribing with missing required fields."""
        with client.websocket_connect("/api/v1/intelligence/ws/indicators") as websocket:
            # Receive welcome message
            websocket.receive_json()
            
            # Subscribe without indicators
            websocket.send_json({
                "action": "subscribe",
                "symbol": "BTC-USD",
                "timeframe": "1h"
            })
            
            # Should receive error
            data = websocket.receive_json()
            assert data["type"] == "error"
            assert "Missing required fields" in data["message"]
    
    def test_unsubscribe(self, client):
        """Test unsubscribing from indicators."""
        with client.websocket_connect("/api/v1/intelligence/ws/indicators") as websocket:
            # Receive welcome message
            websocket.receive_json()
            
            # Subscribe first
            websocket.send_json({
                "action": "subscribe",
                "symbol": "BTC-USD",
                "timeframe": "1h",
                "indicators": ["EMA_20", "RSI_14"]
            })
            websocket.receive_json()  # Subscription confirmation
            
            # Unsubscribe
            websocket.send_json({
                "action": "unsubscribe",
                "symbol": "BTC-USD",
                "timeframe": "1h",
                "indicators": ["EMA_20", "RSI_14"]
            })
            
            # Should receive unsubscription confirmation
            data = websocket.receive_json()
            assert data["type"] == "unsubscribed"
            assert data["status"] == "success"
    
    def test_multiple_subscriptions(self, client):
        """Test multiple subscriptions from same client."""
        with client.websocket_connect("/api/v1/intelligence/ws/indicators") as websocket:
            # Receive welcome message
            websocket.receive_json()
            
            # Subscribe to first set of indicators
            websocket.send_json({
                "action": "subscribe",
                "symbol": "BTC-USD",
                "timeframe": "1h",
                "indicators": ["EMA_20", "RSI_14"]
            })
            data1 = websocket.receive_json()
            assert data1["type"] == "subscribed"
            
            # Subscribe to second set of indicators
            websocket.send_json({
                "action": "subscribe",
                "symbol": "ETH-USD",
                "timeframe": "4h",
                "indicators": ["MACD", "BBANDS_20"]
            })
            data2 = websocket.receive_json()
            assert data2["type"] == "subscribed"


class TestIndicatorBroadcast:
    """Test indicator broadcasting functionality."""
    
    def test_broadcast_to_subscribed_clients(self, client):
        """Test broadcasting indicator updates to subscribed clients."""
        with client.websocket_connect("/api/v1/intelligence/ws/indicators") as websocket:
            # Receive welcome message
            websocket.receive_json()
            
            # Subscribe to indicators
            websocket.send_json({
                "action": "subscribe",
                "symbol": "BTC-USD",
                "timeframe": "1h",
                "indicators": ["EMA_20", "RSI_14"]
            })
            websocket.receive_json()  # Subscription confirmation
            
            # Trigger broadcast via API
            response = client.post("/api/v1/intelligence/indicators/broadcast", json={
                "symbol": "BTC-USD",
                "timeframe": "1h",
                "indicators": ["EMA_20", "RSI_14"],
                "market_data": {
                    "highs": [100.0 + i for i in range(50)],
                    "lows": [99.0 + i for i in range(50)],
                    "closes": [99.5 + i for i in range(50)],
                    "volumes": [1000.0 + i * 10 for i in range(50)]
                }
            })
            
            assert response.status_code == 200
            assert response.json()["status"] == "success"
            assert response.json()["clients_notified"] >= 1
            
            # Should receive indicator update
            data = websocket.receive_json()
            assert data["type"] == "indicator_update"
            assert data["symbol"] == "BTC-USD"
            assert data["timeframe"] == "1h"
            assert "indicators" in data
            assert "EMA_20" in data["indicators"]
            assert "RSI_14" in data["indicators"]
    
    def test_broadcast_no_subscribers(self, client):
        """Test broadcasting when no clients are subscribed."""
        response = client.post("/api/v1/intelligence/indicators/broadcast", json={
            "symbol": "BTC-USD",
            "timeframe": "1h",
            "indicators": ["EMA_20"],
            "market_data": {
                "highs": [100.0 + i for i in range(50)],
                "lows": [99.0 + i for i in range(50)],
                "closes": [99.5 + i for i in range(50)],
                "volumes": [1000.0 + i * 10 for i in range(50)]
            }
        })
        
        assert response.status_code == 200
        assert response.json()["clients_notified"] == 0


class TestWebSocketManager:
    """Test WebSocket manager functionality."""
    
    @pytest.mark.asyncio
    async def test_manager_connect_disconnect(self, ws_manager):
        """Test manager connect and disconnect."""
        # Mock websocket
        mock_ws = AsyncMock()
        
        # Connect client
        client = await ws_manager.connect(mock_ws, "test-client-1")
        
        assert client.client_id == "test-client-1"
        assert "test-client-1" in ws_manager.clients
        assert ws_manager.stats["active_connections"] == 1
        
        # Disconnect client
        await ws_manager.disconnect("test-client-1")
        
        assert "test-client-1" not in ws_manager.clients
        assert ws_manager.stats["active_connections"] == 0
    
    @pytest.mark.asyncio
    async def test_manager_subscription(self, ws_manager):
        """Test manager subscription handling."""
        # Mock websocket
        mock_ws = AsyncMock()
        
        # Connect client
        await ws_manager.connect(mock_ws, "test-client-1")
        
        # Subscribe
        subscription = IndicatorSubscription(
            symbol="BTC-USD",
            timeframe="1h",
            indicators=["EMA_20", "RSI_14"]
        )
        
        result = await ws_manager.subscribe("test-client-1", subscription)
        
        assert result["status"] == "success"
        assert subscription.to_key() in ws_manager.subscriptions
        assert "test-client-1" in ws_manager.subscriptions[subscription.to_key()]
    
    @pytest.mark.asyncio
    async def test_manager_heartbeat_timeout(self, ws_manager):
        """Test manager heartbeat timeout detection."""
        # Mock websocket
        mock_ws = AsyncMock()
        
        # Connect client
        client = await ws_manager.connect(mock_ws, "test-client-1")
        
        # Set last heartbeat to past
        client.last_heartbeat = 0
        
        # Check heartbeats (should disconnect stale client)
        await ws_manager._check_heartbeats()
        
        assert "test-client-1" not in ws_manager.clients
    
    @pytest.mark.asyncio
    async def test_manager_broadcast(self, ws_manager):
        """Test manager broadcast functionality."""
        # Mock websocket
        mock_ws = AsyncMock()
        
        # Connect client
        await ws_manager.connect(mock_ws, "test-client-1")
        
        # Subscribe
        subscription = IndicatorSubscription(
            symbol="BTC-USD",
            timeframe="1h",
            indicators=["EMA_20"]
        )
        await ws_manager.subscribe("test-client-1", subscription)
        
        # Broadcast update
        await ws_manager.broadcast_indicator_update(
            symbol="BTC-USD",
            timeframe="1h",
            indicators=["EMA_20"],
            market_data={
                "highs": [100.0 + i for i in range(50)],
                "lows": [99.0 + i for i in range(50)],
                "closes": [99.5 + i for i in range(50)],
                "volumes": [1000.0 + i * 10 for i in range(50)]
            }
        )
        
        # Verify message was sent
        assert mock_ws.send_json.call_count >= 2  # Welcome + update


class TestWebSocketStats:
    """Test WebSocket statistics endpoint."""
    
    def test_get_stats(self, client):
        """Test getting WebSocket statistics."""
        response = client.get("/api/v1/intelligence/indicators/ws/stats")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "total_connections" in data
        assert "active_connections" in data
        assert "total_subscriptions" in data
        assert "messages_sent" in data
        assert "errors" in data
        assert "subscriptions_by_key" in data


class TestErrorHandling:
    """Test error handling in WebSocket connections."""
    
    def test_invalid_json(self, client):
        """Test handling of invalid JSON messages."""
        with client.websocket_connect("/api/v1/intelligence/ws/indicators") as websocket:
            # Receive welcome message
            websocket.receive_json()
            
            # Send invalid JSON
            websocket.send_text("invalid json {")
            
            # Should receive error
            data = websocket.receive_json()
            assert data["type"] == "error"
            assert "Invalid JSON" in data["message"]
    
    def test_unknown_action(self, client):
        """Test handling of unknown action."""
        with client.websocket_connect("/api/v1/intelligence/ws/indicators") as websocket:
            # Receive welcome message
            websocket.receive_json()
            
            # Send unknown action
            websocket.send_json({
                "action": "unknown_action"
            })
            
            # Should receive error
            data = websocket.receive_json()
            assert data["type"] == "error"
            assert "Unknown action" in data["message"]


class TestSubscriptionKey:
    """Test subscription key generation."""
    
    def test_subscription_key_consistency(self):
        """Test that subscription keys are consistent."""
        sub1 = IndicatorSubscription(
            symbol="BTC-USD",
            timeframe="1h",
            indicators=["EMA_20", "RSI_14"]
        )
        
        sub2 = IndicatorSubscription(
            symbol="BTC-USD",
            timeframe="1h",
            indicators=["RSI_14", "EMA_20"]  # Different order
        )
        
        # Keys should be the same (indicators are sorted)
        assert sub1.to_key() == sub2.to_key()
    
    def test_subscription_key_uniqueness(self):
        """Test that different subscriptions have different keys."""
        sub1 = IndicatorSubscription(
            symbol="BTC-USD",
            timeframe="1h",
            indicators=["EMA_20"]
        )
        
        sub2 = IndicatorSubscription(
            symbol="ETH-USD",
            timeframe="1h",
            indicators=["EMA_20"]
        )
        
        sub3 = IndicatorSubscription(
            symbol="BTC-USD",
            timeframe="4h",
            indicators=["EMA_20"]
        )
        
        # All keys should be different
        assert sub1.to_key() != sub2.to_key()
        assert sub1.to_key() != sub3.to_key()
        assert sub2.to_key() != sub3.to_key()
