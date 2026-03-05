"""Binance WebSocket connector implementation."""

import asyncio
import json
import logging
import time
from decimal import Decimal
from typing import Optional

import websockets
from websockets.client import WebSocketClientProtocol

from ..models import OrderBookSnapshot, OrderBookDelta, Trade, PriceLevel
from .base import ExchangeConnector


logger = logging.getLogger(__name__)


class BinanceConnector(ExchangeConnector):
    """
    Binance WebSocket connector.
    Uses exact message formats from RESEARCH.md Section 2.
    """

    BASE_URL = "wss://stream.binance.com:9443"

    def __init__(self, symbols: list[str], **kwargs):
        """Initialize Binance connector."""
        super().__init__(symbols, **kwargs)
        self.ws: Optional[WebSocketClientProtocol] = None
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._message_task: Optional[asyncio.Task] = None
        self._last_heartbeat = time.time()

    async def connect(self) -> None:
        """Connect to Binance WebSocket."""
        # Build stream URL for combined streams
        streams = []
        for symbol in self.symbols:
            symbol_lower = symbol.lower()
            # Subscribe to depth snapshots and trades
            streams.extend([
                f"{symbol_lower}@depth20@100ms",  # Order book snapshot (top 20 levels)
                f"{symbol_lower}@trade"  # Trade stream
            ])

        url = f"{self.BASE_URL}/stream?streams={'/'.join(streams)}"

        try:
            self.ws = await websockets.connect(
                url,
                ping_interval=20,
                ping_timeout=10,
                close_timeout=10,
            )
            logger.info(f"Connected to Binance WebSocket: {url}")

            # Start heartbeat monitoring
            self._heartbeat_task = asyncio.create_task(self._heartbeat_monitor())

            # Start message handler
            self._message_task = asyncio.create_task(self._message_handler())

        except Exception as e:
            logger.error(f"Failed to connect to Binance: {e}")
            raise

    async def disconnect(self) -> None:
        """Disconnect from Binance WebSocket."""
        self.is_connected = False

        # Cancel tasks
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
        if self._message_task:
            self._message_task.cancel()

        # Close WebSocket
        if self.ws:
            await self.ws.close()
            self.ws = None

        logger.info("Disconnected from Binance WebSocket")

    async def subscribe(self, symbol: str) -> None:
        """Subscribe to a symbol (handled in connect for Binance)."""
        # Binance subscriptions are handled via the stream URL
        pass

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
        """
        Handle incoming Binance WebSocket message.
        Combined streams wrap data in {stream, data} format.
        """
        # Extract stream name and data
        stream = message.get("stream", "")
        data = message.get("data", {})

        if "@depth" in stream:
            await self._handle_depth_message(stream, data)
        elif "@trade" in stream:
            await self._handle_trade_message(stream, data)

    async def _handle_depth_message(self, stream: str, data: dict) -> None:
        """Handle order book depth message (snapshot)."""
        # Extract symbol from stream name
        symbol = stream.split("@")[0].upper()

        # Parse bids and asks
        bids = [
            PriceLevel(
                price=Decimal(bid[0]),
                quantity=Decimal(bid[1])
            )
            for bid in data.get("bids", [])
            if Decimal(bid[1]) > 0  # Filter out zero quantities
        ]

        asks = [
            PriceLevel(
                price=Decimal(ask[0]),
                quantity=Decimal(ask[1])
            )
            for ask in data.get("asks", [])
            if Decimal(ask[1]) > 0  # Filter out zero quantities
        ]

        # Create snapshot
        snapshot = OrderBookSnapshot(
            exchange="binance",
            symbol=symbol,
            timestamp_us=int(time.time() * 1_000_000),  # Convert to microseconds
            sequence=data.get("lastUpdateId", 0),
            bids=bids,
            asks=asks,
        )

        # Trigger callback
        if self.on_book_snapshot:
            await self.on_book_snapshot(snapshot)

    async def _handle_trade_message(self, stream: str, data: dict) -> None:
        """Handle trade message."""
        # Extract symbol from stream name
        symbol = stream.split("@")[0].upper()

        # Determine trade side
        # In Binance, 'm' field: true = buyer is maker (sell trade), false = buyer is taker (buy trade)
        is_buyer_maker = data.get("m", False)
        side = "sell" if is_buyer_maker else "buy"

        # Create trade object
        trade = Trade(
            exchange="binance",
            symbol=symbol,
            timestamp_us=data.get("T", 0) * 1000,  # Convert ms to us
            price=Decimal(data.get("p", "0")),
            quantity=Decimal(data.get("q", "0")),
            side=side,
            trade_id=str(data.get("t", "")),
        )

        # Trigger callback
        if self.on_trade:
            await self.on_trade(trade)

    async def _heartbeat_monitor(self) -> None:
        """Monitor connection health with heartbeat."""
        while self.is_connected:
            try:
                # Check if we've received data recently
                if time.time() - self._last_heartbeat > 30:
                    logger.warning("No heartbeat received for 30 seconds, reconnecting...")
                    self.is_connected = False
                    break

                await asyncio.sleep(10)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Heartbeat monitor error: {e}")
                break