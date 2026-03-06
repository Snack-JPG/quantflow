"""Kraken WebSocket connector implementation."""

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


class KrakenConnector(ExchangeConnector):
    """
    Kraken WebSocket connector.
    Supports order book and trade data streams.
    """

    BASE_URL = "wss://ws.kraken.com"

    def __init__(self, symbols: list[str], **kwargs):
        """Initialize Kraken connector."""
        super().__init__(symbols, **kwargs)
        self.ws: Optional[WebSocketClientProtocol] = None
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._message_task: Optional[asyncio.Task] = None
        self._last_heartbeat = time.time()
        # Track order books for each symbol
        self._order_books: Dict[str, Dict[str, Dict[str, PriceLevel]]] = {}
        # Track sequence numbers
        self._sequences: Dict[str, int] = {}
        # Map channel IDs to symbols
        self._channel_to_symbol: Dict[int, str] = {}
        # Track subscription IDs
        self._subscription_id = 0

    async def connect(self) -> None:
        """Connect to Kraken WebSocket."""
        try:
            self.ws = await websockets.connect(
                self.BASE_URL,
                ping_interval=20,
                ping_timeout=10,
                close_timeout=10,
            )
            logger.info(f"Connected to Kraken WebSocket: {self.BASE_URL}")

            # Start heartbeat monitoring
            self._heartbeat_task = asyncio.create_task(self._heartbeat_monitor())

            # Start message handler
            self._message_task = asyncio.create_task(self._message_handler())

        except Exception as e:
            logger.error(f"Failed to connect to Kraken: {e}")
            raise

    async def disconnect(self) -> None:
        """Disconnect from Kraken WebSocket."""
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

        logger.info("Disconnected from Kraken WebSocket")

    async def subscribe(self, symbol: str) -> None:
        """Subscribe to a symbol."""
        if not self.ws:
            logger.error("Cannot subscribe: WebSocket not connected")
            return

        # Convert symbol format
        kraken_symbol = self._convert_symbol(symbol)

        # Initialize order book tracking
        if kraken_symbol not in self._order_books:
            self._order_books[kraken_symbol] = {
                "bids": {},
                "asks": {}
            }
            self._sequences[kraken_symbol] = 0

        # Send subscription for order book (depth of 25)
        book_sub = {
            "event": "subscribe",
            "pair": [kraken_symbol],
            "subscription": {
                "name": "book",
                "depth": 25
            },
            "reqid": self._subscription_id
        }
        self._subscription_id += 1

        await self.ws.send(json.dumps(book_sub))
        logger.info(f"Subscribed to Kraken book for {kraken_symbol}")

        # Send subscription for trades
        trade_sub = {
            "event": "subscribe",
            "pair": [kraken_symbol],
            "subscription": {
                "name": "trade"
            },
            "reqid": self._subscription_id
        }
        self._subscription_id += 1

        await self.ws.send(json.dumps(trade_sub))
        logger.info(f"Subscribed to Kraken trades for {kraken_symbol}")

    async def _send_unsubscribe(self) -> None:
        """Unsubscribe from all symbols."""
        if not self.ws:
            return

        for symbol in self.symbols:
            kraken_symbol = self._convert_symbol(symbol)

            # Unsubscribe from book
            unsub_book = {
                "event": "unsubscribe",
                "pair": [kraken_symbol],
                "subscription": {
                    "name": "book"
                }
            }
            try:
                await self.ws.send(json.dumps(unsub_book))
            except Exception as e:
                logger.error(f"Error unsubscribing from book: {e}")

            # Unsubscribe from trades
            unsub_trade = {
                "event": "unsubscribe",
                "pair": [kraken_symbol],
                "subscription": {
                    "name": "trade"
                }
            }
            try:
                await self.ws.send(json.dumps(unsub_trade))
            except Exception as e:
                logger.error(f"Error unsubscribing from trades: {e}")

    def _convert_symbol(self, symbol: str) -> str:
        """
        Convert from standard format to Kraken format.
        BTCUSDT -> XBT/USD, ETHUSDT -> ETH/USD, etc.
        """
        # Kraken uses XBT instead of BTC
        conversions = {
            "BTCUSDT": "XBT/USD",
            "BTCUSD": "XBT/USD",
            "ETHUSDT": "ETH/USD",
            "ETHUSD": "ETH/USD",
            "ETHBTC": "ETH/XBT",
        }

        if symbol in conversions:
            return conversions[symbol]

        # Try generic conversion
        if symbol.endswith("USDT"):
            base = symbol[:-4]
            if base == "BTC":
                base = "XBT"
            return f"{base}/USD"
        elif symbol.endswith("USD"):
            base = symbol[:-3]
            if base == "BTC":
                base = "XBT"
            return f"{base}/USD"
        elif symbol.endswith("BTC"):
            base = symbol[:-3]
            return f"{base}/XBT"

        return symbol

    def _convert_symbol_back(self, kraken_symbol: str) -> str:
        """
        Convert from Kraken format back to standard format.
        XBT/USD -> BTCUSDT, ETH/USD -> ETHUSDT, etc.
        """
        # Replace XBT with BTC and format
        parts = kraken_symbol.split("/")
        if len(parts) == 2:
            base, quote = parts
            # Convert XBT to BTC
            if base == "XBT":
                base = "BTC"
            if quote == "XBT":
                quote = "BTC"
            # Convert USD to USDT
            if quote == "USD":
                return f"{base}USDT"
            else:
                return f"{base}{quote}"

        return kraken_symbol.replace("/", "")

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

    async def _handle_message(self, message) -> None:
        """Handle incoming Kraken WebSocket message."""
        # Kraken sends different message formats
        # System messages are dicts, data messages are arrays

        if isinstance(message, dict):
            # System message
            event = message.get("event", "")

            if event == "systemStatus":
                logger.info(f"Kraken system status: {message.get('status')}")
            elif event == "subscriptionStatus":
                self._handle_subscription_status(message)
            elif event == "heartbeat":
                self._last_heartbeat = time.time()
            elif event == "error":
                logger.error(f"Kraken error: {message.get('errorMessage', 'Unknown error')}")

        elif isinstance(message, list) and len(message) >= 4:
            # Data message format: [channelID, data, channelName, pair]
            channel_id = message[0]
            data = message[1]
            channel_name = message[2]
            pair = message[3]

            if channel_name == "book-25":
                await self._handle_book_message(data, pair)
            elif channel_name == "trade":
                await self._handle_trade_message(data, pair)

    def _handle_subscription_status(self, message: dict) -> None:
        """Handle subscription status message."""
        status = message.get("status", "")
        if status == "subscribed":
            channel_id = message.get("channelID")
            pair = message.get("pair", "")
            subscription = message.get("subscription", {})
            name = subscription.get("name", "")

            # Map channel to symbol
            if channel_id:
                self._channel_to_symbol[channel_id] = pair

            logger.info(f"Kraken subscription confirmed: {name} for {pair} (channel {channel_id})")
        elif status == "error":
            error = message.get("errorMessage", "Unknown error")
            logger.error(f"Kraken subscription error: {error}")

    async def _handle_book_message(self, data: dict, pair: str) -> None:
        """Handle order book message."""
        symbol = self._convert_symbol_back(pair)

        # Check if it's a snapshot or update
        if "as" in data and "bs" in data:
            # Snapshot
            self._order_books[pair] = {
                "bids": {},
                "asks": {}
            }

            # Process bids (bs = bid snapshot)
            for bid in data.get("bs", []):
                if len(bid) >= 2:
                    price = Decimal(bid[0])
                    volume = Decimal(bid[1])
                    if volume > 0:
                        self._order_books[pair]["bids"][str(price)] = PriceLevel(
                            price=price,
                            quantity=volume
                        )

            # Process asks (as = ask snapshot)
            for ask in data.get("as", []):
                if len(ask) >= 2:
                    price = Decimal(ask[0])
                    volume = Decimal(ask[1])
                    if volume > 0:
                        self._order_books[pair]["asks"][str(price)] = PriceLevel(
                            price=price,
                            quantity=volume
                        )

        else:
            # Update
            if pair not in self._order_books:
                logger.warning(f"Received update for untracked pair: {pair}")
                return

            # Process bid updates (b = bid update)
            for bid in data.get("b", []):
                if len(bid) >= 2:
                    price = Decimal(bid[0])
                    volume = Decimal(bid[1])
                    price_str = str(price)

                    if volume == 0:
                        self._order_books[pair]["bids"].pop(price_str, None)
                    else:
                        self._order_books[pair]["bids"][price_str] = PriceLevel(
                            price=price,
                            quantity=volume
                        )

            # Process ask updates (a = ask update)
            for ask in data.get("a", []):
                if len(ask) >= 2:
                    price = Decimal(ask[0])
                    volume = Decimal(ask[1])
                    price_str = str(price)

                    if volume == 0:
                        self._order_books[pair]["asks"].pop(price_str, None)
                    else:
                        self._order_books[pair]["asks"][price_str] = PriceLevel(
                            price=price,
                            quantity=volume
                        )

        # Send snapshot
        await self._send_order_book_snapshot(pair, symbol)

    async def _send_order_book_snapshot(self, pair: str, symbol: str) -> None:
        """Create and send order book snapshot from current state."""
        if pair not in self._order_books:
            return

        # Get sorted bids (descending by price)
        bids = sorted(
            self._order_books[pair]["bids"].values(),
            key=lambda x: x.price,
            reverse=True
        )[:20]  # Top 20 levels

        # Get sorted asks (ascending by price)
        asks = sorted(
            self._order_books[pair]["asks"].values(),
            key=lambda x: x.price
        )[:20]  # Top 20 levels

        # Increment sequence
        self._sequences[pair] = self._sequences.get(pair, 0) + 1

        # Create snapshot
        snapshot = OrderBookSnapshot(
            exchange="kraken",
            symbol=symbol,
            timestamp_us=int(time.time() * 1_000_000),
            sequence=self._sequences[pair],
            bids=bids,
            asks=asks
        )

        # Trigger callback
        if self.on_book_snapshot:
            await self.on_book_snapshot(snapshot)

    async def _handle_trade_message(self, trades: list, pair: str) -> None:
        """Handle trade messages."""
        symbol = self._convert_symbol_back(pair)

        for trade_data in trades:
            if len(trade_data) >= 4:
                # Format: [price, volume, time, side, orderType, misc]
                trade = Trade(
                    exchange="kraken",
                    symbol=symbol,
                    timestamp_us=int(float(trade_data[2]) * 1_000_000),  # Convert to microseconds
                    price=Decimal(trade_data[0]),
                    quantity=Decimal(trade_data[1]),
                    side="buy" if trade_data[3] == "b" else "sell",
                    trade_id=f"{pair}_{trade_data[2]}"  # Use timestamp as part of ID
                )

                # Trigger callback
                if self.on_trade:
                    await self.on_trade(trade)

    async def _heartbeat_monitor(self) -> None:
        """Monitor connection health with heartbeat."""
        while self.is_connected:
            try:
                # Kraken doesn't send regular heartbeats like other exchanges
                # Check if we've received any data recently
                if time.time() - self._last_heartbeat > 60:
                    logger.warning("No data received for 60 seconds, sending ping...")
                    # Send a ping to check connection
                    if self.ws:
                        await self.ws.send(json.dumps({"event": "ping"}))

                    # Wait for response
                    await asyncio.sleep(5)

                    # If still no heartbeat, reconnect
                    if time.time() - self._last_heartbeat > 65:
                        logger.warning("No response to ping, reconnecting...")
                        self.is_connected = False
                        break

                await asyncio.sleep(10)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Heartbeat monitor error: {e}")
                break