"""Coinbase WebSocket connector implementation."""

import asyncio
import json
import logging
import time
from decimal import Decimal
from typing import Optional, Dict, List
from datetime import datetime

import websockets
from websockets.client import WebSocketClientProtocol

from ..models import OrderBookSnapshot, OrderBookDelta, Trade, PriceLevel
from .base import ExchangeConnector


logger = logging.getLogger(__name__)


class CoinbaseConnector(ExchangeConnector):
    """
    Coinbase WebSocket connector.
    Supports L2 order book data and trade streams.
    """

    BASE_URL = "wss://ws-feed.exchange.coinbase.com"

    def __init__(self, symbols: list[str], **kwargs):
        """Initialize Coinbase connector."""
        super().__init__(symbols, **kwargs)
        self.ws: Optional[WebSocketClientProtocol] = None
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._message_task: Optional[asyncio.Task] = None
        self._last_heartbeat = time.time()
        # Track order books for each symbol
        self._order_books: Dict[str, Dict[str, Dict[str, PriceLevel]]] = {}
        # Track sequence numbers for each symbol
        self._sequences: Dict[str, int] = {}

    async def connect(self) -> None:
        """Connect to Coinbase WebSocket."""
        try:
            self.ws = await websockets.connect(
                self.BASE_URL,
                ping_interval=20,
                ping_timeout=10,
                close_timeout=10,
            )
            logger.info(f"Connected to Coinbase WebSocket: {self.BASE_URL}")

            # Start heartbeat monitoring
            self._heartbeat_task = asyncio.create_task(self._heartbeat_monitor())

            # Start message handler
            self._message_task = asyncio.create_task(self._message_handler())

        except Exception as e:
            logger.error(f"Failed to connect to Coinbase: {e}")
            raise

    async def disconnect(self) -> None:
        """Disconnect from Coinbase WebSocket."""
        self.is_connected = False

        # Unsubscribe before disconnecting
        if self.ws and self.symbols:
            await self._send_unsubscribe()

        # Cancel tasks
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
        if self._message_task:
            self._message_task.cancel()

        # Close WebSocket
        if self.ws:
            await self.ws.close()
            self.ws = None

        logger.info("Disconnected from Coinbase WebSocket")

    async def subscribe(self, symbol: str) -> None:
        """Subscribe to a symbol."""
        if not self.ws:
            logger.error("Cannot subscribe: WebSocket not connected")
            return

        # Convert symbol format (BTCUSDT -> BTC-USD)
        coinbase_symbol = self._convert_symbol(symbol)

        # Initialize order book tracking
        if coinbase_symbol not in self._order_books:
            self._order_books[coinbase_symbol] = {
                "bids": {},
                "asks": {}
            }
            self._sequences[coinbase_symbol] = 0

        # Send subscription message
        subscribe_msg = {
            "type": "subscribe",
            "product_ids": [coinbase_symbol],
            "channels": [
                {"name": "level2", "product_ids": [coinbase_symbol]},
                {"name": "matches", "product_ids": [coinbase_symbol]},
                {"name": "heartbeat", "product_ids": [coinbase_symbol]}
            ]
        }

        await self.ws.send(json.dumps(subscribe_msg))
        logger.info(f"Subscribed to Coinbase {coinbase_symbol}")

    async def _send_unsubscribe(self) -> None:
        """Unsubscribe from all symbols."""
        if not self.ws or not self.symbols:
            return

        coinbase_symbols = [self._convert_symbol(s) for s in self.symbols]

        unsubscribe_msg = {
            "type": "unsubscribe",
            "product_ids": coinbase_symbols,
            "channels": ["level2", "matches", "heartbeat"]
        }

        try:
            await self.ws.send(json.dumps(unsubscribe_msg))
        except Exception as e:
            logger.error(f"Error unsubscribing: {e}")

    def _convert_symbol(self, symbol: str) -> str:
        """
        Convert from standard format to Coinbase format.
        BTCUSDT -> BTC-USD, ETHUSDT -> ETH-USD, etc.
        """
        # Common conversions
        conversions = {
            "BTCUSDT": "BTC-USD",
            "ETHUSDT": "ETH-USD",
            "BTCUSD": "BTC-USD",
            "ETHUSD": "ETH-USD",
            "ETHBTC": "ETH-BTC",
        }

        if symbol in conversions:
            return conversions[symbol]

        # Try generic conversion (remove T from USDT)
        if symbol.endswith("USDT"):
            base = symbol[:-4]
            return f"{base}-USD"
        elif symbol.endswith("USD"):
            base = symbol[:-3]
            return f"{base}-USD"
        elif symbol.endswith("BTC"):
            base = symbol[:-3]
            return f"{base}-BTC"

        return symbol

    def _convert_symbol_back(self, coinbase_symbol: str) -> str:
        """
        Convert from Coinbase format back to standard format.
        BTC-USD -> BTCUSDT, ETH-USD -> ETHUSDT, etc.
        """
        # Remove dashes and convert
        parts = coinbase_symbol.split("-")
        if len(parts) == 2:
            base, quote = parts
            if quote == "USD":
                return f"{base}USDT"
            elif quote == "BTC":
                return f"{base}BTC"

        return coinbase_symbol.replace("-", "")

    async def _message_handler(self) -> None:
        """Handle incoming WebSocket messages."""
        if not self.ws:
            return

        try:
            async for message in self.ws:
                self._last_heartbeat = time.time()

                try:
                    data = json.loads(message)
                    await self._handle_message(data)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse message: {e}")
                except Exception as e:
                    logger.error(f"Error handling message: {e}")

        except websockets.exceptions.ConnectionClosed:
            logger.warning("WebSocket connection closed")
            self.is_connected = False
        except Exception as e:
            logger.error(f"Message handler error: {e}")
            self.is_connected = False

    async def _handle_message(self, message: dict) -> None:
        """Handle incoming Coinbase WebSocket message."""
        msg_type = message.get("type", "")

        if msg_type == "subscriptions":
            logger.info(f"Coinbase subscriptions confirmed: {message.get('channels', [])}")
        elif msg_type == "heartbeat":
            # Update heartbeat timestamp
            self._last_heartbeat = time.time()
        elif msg_type == "snapshot":
            await self._handle_snapshot(message)
        elif msg_type == "l2update":
            await self._handle_l2_update(message)
        elif msg_type == "match":
            await self._handle_trade(message)
        elif msg_type == "error":
            logger.error(f"Coinbase error: {message.get('message', 'Unknown error')}")

    async def _handle_snapshot(self, data: dict) -> None:
        """Handle order book snapshot."""
        product_id = data.get("product_id", "")
        symbol = self._convert_symbol_back(product_id)

        # Clear existing order book
        self._order_books[product_id] = {
            "bids": {},
            "asks": {}
        }

        # Process bids
        for bid in data.get("bids", []):
            if len(bid) >= 2:
                price = Decimal(bid[0])
                quantity = Decimal(bid[1])
                if quantity > 0:
                    self._order_books[product_id]["bids"][str(price)] = PriceLevel(
                        price=price,
                        quantity=quantity
                    )

        # Process asks
        for ask in data.get("asks", []):
            if len(ask) >= 2:
                price = Decimal(ask[0])
                quantity = Decimal(ask[1])
                if quantity > 0:
                    self._order_books[product_id]["asks"][str(price)] = PriceLevel(
                        price=price,
                        quantity=quantity
                    )

        # Create and send snapshot
        await self._send_order_book_snapshot(product_id, symbol)

    async def _handle_l2_update(self, data: dict) -> None:
        """Handle incremental L2 order book update."""
        product_id = data.get("product_id", "")
        symbol = self._convert_symbol_back(product_id)

        if product_id not in self._order_books:
            logger.warning(f"Received update for untracked product: {product_id}")
            return

        changes = data.get("changes", [])

        for change in changes:
            if len(change) >= 3:
                side = change[0]  # "buy" or "sell"
                price = Decimal(change[1])
                size = Decimal(change[2])
                price_str = str(price)

                if side == "buy":
                    if size == 0:
                        # Remove level
                        self._order_books[product_id]["bids"].pop(price_str, None)
                    else:
                        # Update level
                        self._order_books[product_id]["bids"][price_str] = PriceLevel(
                            price=price,
                            quantity=size
                        )
                elif side == "sell":
                    if size == 0:
                        # Remove level
                        self._order_books[product_id]["asks"].pop(price_str, None)
                    else:
                        # Update level
                        self._order_books[product_id]["asks"][price_str] = PriceLevel(
                            price=price,
                            quantity=size
                        )

        # Send updated snapshot
        await self._send_order_book_snapshot(product_id, symbol)

    async def _send_order_book_snapshot(self, product_id: str, symbol: str) -> None:
        """Create and send order book snapshot from current state."""
        if product_id not in self._order_books:
            return

        # Get sorted bids (descending by price)
        bids = sorted(
            self._order_books[product_id]["bids"].values(),
            key=lambda x: x.price,
            reverse=True
        )[:20]  # Top 20 levels

        # Get sorted asks (ascending by price)
        asks = sorted(
            self._order_books[product_id]["asks"].values(),
            key=lambda x: x.price
        )[:20]  # Top 20 levels

        # Increment sequence
        self._sequences[product_id] = self._sequences.get(product_id, 0) + 1

        # Create snapshot
        snapshot = OrderBookSnapshot(
            exchange="coinbase",
            symbol=symbol,
            timestamp_us=int(time.time() * 1_000_000),
            sequence=self._sequences[product_id],
            bids=bids,
            asks=asks
        )

        # Trigger callback
        if self.on_book_snapshot:
            await self.on_book_snapshot(snapshot)

    async def _handle_trade(self, data: dict) -> None:
        """Handle trade/match message."""
        product_id = data.get("product_id", "")
        symbol = self._convert_symbol_back(product_id)

        # Parse trade data
        trade = Trade(
            exchange="coinbase",
            symbol=symbol,
            timestamp_us=int(datetime.fromisoformat(
                data.get("time", "").replace("Z", "+00:00")
            ).timestamp() * 1_000_000) if data.get("time") else int(time.time() * 1_000_000),
            price=Decimal(data.get("price", "0")),
            quantity=Decimal(data.get("size", "0")),
            side=data.get("side", "buy"),  # Coinbase provides maker side
            trade_id=str(data.get("trade_id", ""))
        )

        # Trigger callback
        if self.on_trade:
            await self.on_trade(trade)

    async def _heartbeat_monitor(self) -> None:
        """Monitor connection health with heartbeat."""
        while self.is_connected:
            try:
                # Check if we've received data recently
                if time.time() - self._last_heartbeat > 60:
                    logger.warning("No heartbeat received for 60 seconds, reconnecting...")
                    self.is_connected = False
                    break

                await asyncio.sleep(10)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Heartbeat monitor error: {e}")
                break