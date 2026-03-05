"""Abstract base class for exchange connectors."""

from abc import ABC, abstractmethod
from typing import AsyncIterator, Callable, Optional
import asyncio
import logging

from ..models import OrderBookSnapshot, OrderBookDelta, Trade


logger = logging.getLogger(__name__)


class ExchangeConnector(ABC):
    """
    Abstract base class for exchange connectors.
    Makes it trivial to add Coinbase/Kraken later.
    """

    def __init__(
        self,
        symbols: list[str],
        on_book_snapshot: Optional[Callable] = None,
        on_book_delta: Optional[Callable] = None,
        on_trade: Optional[Callable] = None,
    ):
        """
        Initialize connector.

        Args:
            symbols: List of symbols to subscribe to (e.g., ["BTCUSDT"])
            on_book_snapshot: Callback for order book snapshots
            on_book_delta: Callback for order book deltas
            on_trade: Callback for trades
        """
        self.symbols = symbols
        self.on_book_snapshot = on_book_snapshot
        self.on_book_delta = on_book_delta
        self.on_trade = on_trade
        self.is_connected = False
        self._stop_event = asyncio.Event()
        self._reconnect_delay = 1.0  # Initial reconnect delay in seconds
        self._max_reconnect_delay = 60.0  # Max reconnect delay

    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to exchange."""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection to exchange."""
        pass

    @abstractmethod
    async def subscribe(self, symbol: str) -> None:
        """Subscribe to market data for a symbol."""
        pass

    @abstractmethod
    async def _handle_message(self, message: dict) -> None:
        """Handle incoming WebSocket message."""
        pass

    async def run(self) -> None:
        """
        Main run loop with automatic reconnection and exponential backoff.
        """
        while not self._stop_event.is_set():
            try:
                logger.info(f"Connecting to {self.__class__.__name__}...")
                await self.connect()
                self.is_connected = True
                self._reconnect_delay = 1.0  # Reset delay on successful connection

                # Subscribe to all symbols
                for symbol in self.symbols:
                    await self.subscribe(symbol)

                # Keep connection alive
                while self.is_connected and not self._stop_event.is_set():
                    await asyncio.sleep(1)

            except Exception as e:
                logger.error(f"Connection error: {e}")
                self.is_connected = False

                if not self._stop_event.is_set():
                    logger.info(f"Reconnecting in {self._reconnect_delay} seconds...")
                    await asyncio.sleep(self._reconnect_delay)

                    # Exponential backoff
                    self._reconnect_delay = min(
                        self._reconnect_delay * 2,
                        self._max_reconnect_delay
                    )

    async def stop(self) -> None:
        """Stop the connector gracefully."""
        logger.info(f"Stopping {self.__class__.__name__}...")
        self._stop_event.set()
        await self.disconnect()