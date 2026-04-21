"""
Example WebSocket client for real-time indicator updates.

This script demonstrates how to connect to the indicator WebSocket endpoint,
subscribe to indicators, and receive real-time updates.

Usage:
    python examples/websocket_indicator_client.py
"""

import asyncio
import websockets
import json
from datetime import datetime


async def indicator_client():
    """Connect to indicator WebSocket and receive updates."""
    uri = "ws://localhost:8000/api/v1/intelligence/ws/indicators"
    
    async with websockets.connect(uri) as websocket:
        print(f"Connected to {uri}")
        
        # Receive welcome message
        welcome = await websocket.recv()
        welcome_data = json.loads(welcome)
        print(f"Welcome: {welcome_data}")
        
        # Subscribe to BTC-USD indicators
        subscribe_message = {
            "action": "subscribe",
            "symbol": "BTC-USD",
            "timeframe": "1h",
            "indicators": ["EMA_20", "RSI_14", "MACD", "BBANDS_20"]
        }
        
        await websocket.send(json.dumps(subscribe_message))
        print(f"Sent subscription: {subscribe_message}")
        
        # Receive subscription confirmation
        response = await websocket.recv()
        response_data = json.loads(response)
        print(f"Subscription response: {response_data}")
        
        # Subscribe to ETH-USD indicators
        subscribe_message_2 = {
            "action": "subscribe",
            "symbol": "ETH-USD",
            "timeframe": "4h",
            "indicators": ["EMA_50", "ADX_14", "VWAP"]
        }
        
        await websocket.send(json.dumps(subscribe_message_2))
        print(f"Sent subscription: {subscribe_message_2}")
        
        # Receive subscription confirmation
        response_2 = await websocket.recv()
        response_data_2 = json.loads(response_2)
        print(f"Subscription response: {response_data_2}")
        
        # Start heartbeat task
        async def send_heartbeat():
            while True:
                await asyncio.sleep(30)
                await websocket.send("ping")
                print(f"[{datetime.now()}] Sent ping")
        
        heartbeat_task = asyncio.create_task(send_heartbeat())
        
        try:
            # Listen for indicator updates
            print("\nListening for indicator updates...")
            print("=" * 80)
            
            while True:
                message = await websocket.recv()
                data = json.loads(message)
                
                if data["type"] == "indicator_update":
                    print(f"\n[{data['timestamp']}] Indicator Update:")
                    print(f"  Symbol: {data['symbol']}")
                    print(f"  Timeframe: {data['timeframe']}")
                    print(f"  Indicators:")
                    
                    for indicator, value in data["indicators"].items():
                        if isinstance(value, dict):
                            print(f"    {indicator}:")
                            for key, val in value.items():
                                print(f"      {key}: {val}")
                        else:
                            print(f"    {indicator}: {value}")
                    
                    print("-" * 80)
                
                elif data["type"] == "pong":
                    print(f"[{datetime.now()}] Received pong")
                
                elif data["type"] == "error":
                    print(f"ERROR: {data['message']}")
        
        except KeyboardInterrupt:
            print("\nDisconnecting...")
            heartbeat_task.cancel()
        
        except Exception as e:
            print(f"Error: {e}")
            heartbeat_task.cancel()


if __name__ == "__main__":
    print("Real-time Indicator WebSocket Client")
    print("=" * 80)
    print("This client will connect to the indicator WebSocket endpoint")
    print("and receive real-time indicator updates.")
    print()
    print("Make sure the backend server is running on http://localhost:8000")
    print()
    print("Press Ctrl+C to disconnect")
    print("=" * 80)
    print()
    
    try:
        asyncio.run(indicator_client())
    except KeyboardInterrupt:
        print("\nClient stopped")
