"""
Kalshi Connector Example

Demonstrates how to use the Kalshi connector for paper trading.
"""

import asyncio
import logging
from src.exchanges.kalshi import KalshiConnector
from src.core.interfaces import Order, OrderSide, OrderType

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def main():
    """Main example function"""
    
    # Initialize Kalshi connector (paper trading mode)
    logger.info("Initializing Kalshi connector...")
    connector = KalshiConnector(
        api_key=None,  # Optional for public data
        private_key=None,  # Optional for public data
        demo=True,  # Use demo API
        paper_trading=True,  # Always enforced
    )
    
    try:
        # Connect to Kalshi
        logger.info("Connecting to Kalshi...")
        await connector.connect()
        logger.info("Connected successfully!")
        
        # Get available markets
        logger.info("\n=== Available Markets ===")
        markets = await connector.get_markets()
        logger.info(f"Found {len(markets)} markets")
        
        # Display first 5 markets
        for i, market in enumerate(markets[:5]):
            logger.info(f"{i+1}. {market.symbol}")
        
        # Get ticker for first market (if available)
        if markets:
            symbol = markets[0].symbol
            logger.info(f"\n=== Ticker for {symbol} ===")
            ticker = await connector.get_ticker(symbol)
            logger.info(f"Last Price: ${ticker.lastPrice:.4f}")
            logger.info(f"Bid: ${ticker.bidPrice:.4f}")
            logger.info(f"Ask: ${ticker.askPrice:.4f}")
            logger.info(f"Volume: {ticker.volume24h}")
            
            # Get order book
            logger.info(f"\n=== Order Book for {symbol} ===")
            order_book = await connector.get_order_book(symbol)
            logger.info(f"Best Bid: ${order_book.bids[0][0]:.4f} x {order_book.bids[0][1]}")
            logger.info(f"Best Ask: ${order_book.asks[0][0]:.4f} x {order_book.asks[0][1]}")
            
            # Check initial balance
            logger.info("\n=== Initial Balance ===")
            balance = await connector.get_balance()
            logger.info(f"Cash: ${balance['USD']:.2f}")
            logger.info(f"Total: ${balance['total']:.2f}")
            
            # Place a paper buy order
            logger.info(f"\n=== Placing Paper Buy Order ===")
            order = Order(
                symbol=symbol,
                side=OrderSide.BUY,
                type=OrderType.MARKET,
                size=10.0,
            )
            trade = await connector.place_order(order)
            logger.info(f"Trade ID: {trade.id}")
            logger.info(f"Price: ${trade.price:.4f}")
            logger.info(f"Size: {trade.size}")
            logger.info(f"Fee: ${trade.fee:.4f}")
            
            # Check positions
            logger.info("\n=== Positions ===")
            positions = await connector.get_positions()
            for pos in positions:
                pnl_pct = (pos.unrealizedPnl / (pos.avgPrice * pos.size)) * 100 if pos.size > 0 else 0
                logger.info(
                    f"{pos.symbol}: {pos.size} @ ${pos.avgPrice:.4f} "
                    f"(P&L: ${pos.unrealizedPnl:.2f}, {pnl_pct:+.2f}%)"
                )
            
            # Check balance after trade
            logger.info("\n=== Balance After Trade ===")
            balance = await connector.get_balance()
            logger.info(f"Cash: ${balance['USD']:.2f}")
            logger.info(f"Positions Value: ${balance['positions_value']:.2f}")
            logger.info(f"Total: ${balance['total']:.2f}")
            
            # Place a limit order
            logger.info(f"\n=== Placing Paper Limit Order ===")
            limit_order = Order(
                symbol=symbol,
                side=OrderSide.BUY,
                type=OrderType.LIMIT,
                size=5.0,
                price=0.45,  # Limit price
            )
            limit_trade = await connector.place_order(limit_order)
            logger.info(f"Trade ID: {limit_trade.id}")
            logger.info(f"Price: ${limit_trade.price:.4f}")
            logger.info(f"Size: {limit_trade.size}")
            
            # Final positions
            logger.info("\n=== Final Positions ===")
            positions = await connector.get_positions()
            for pos in positions:
                pnl_pct = (pos.unrealizedPnl / (pos.avgPrice * pos.size)) * 100 if pos.size > 0 else 0
                logger.info(
                    f"{pos.symbol}: {pos.size} @ ${pos.avgPrice:.4f} "
                    f"(P&L: ${pos.unrealizedPnl:.2f}, {pnl_pct:+.2f}%)"
                )
            
            # Final balance
            logger.info("\n=== Final Balance ===")
            balance = await connector.get_balance()
            logger.info(f"Cash: ${balance['USD']:.2f}")
            logger.info(f"Positions Value: ${balance['positions_value']:.2f}")
            logger.info(f"Total: ${balance['total']:.2f}")
        
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
    
    finally:
        # Disconnect
        logger.info("\n=== Disconnecting ===")
        await connector.disconnect()
        logger.info("Disconnected successfully!")


if __name__ == "__main__":
    asyncio.run(main())
