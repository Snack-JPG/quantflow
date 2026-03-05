"""
Order Book Engine - Core data structure maintaining live order books.
Uses Decimal for all price/quantity calculations as specified.
"""

import asyncio
import logging
import time
from collections import deque
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from ..models import OrderBookSnapshot, OrderBookDelta, PriceLevel


logger = logging.getLogger(__name__)


class OrderBook:
    """
    Maintains L2 order book with full history ring buffer.
    All price/quantity calculations use Decimal for precision.
    """

    def __init__(self, exchange: str, symbol: str, max_snapshots: int = 10000):
        """
        Initialize order book.

        Args:
            exchange: Exchange name
            symbol: Trading pair symbol
            max_snapshots: Maximum snapshots to keep in ring buffer (default: 10,000)
        """
        self.exchange = exchange
        self.symbol = symbol
        self.max_snapshots = max_snapshots

        # Current order book state - using dict for O(1) updates
        self.bids: Dict[Decimal, Decimal] = {}  # price -> quantity
        self.asks: Dict[Decimal, Decimal] = {}  # price -> quantity

        # Ring buffer for historical snapshots
        self.snapshot_buffer: deque[OrderBookSnapshot] = deque(maxlen=max_snapshots)

        # Sequence tracking for gap detection
        self.last_sequence = 0
        self.last_update_time = time.time()

        # Lock for thread-safe operations
        self._lock = asyncio.Lock()

    async def apply_snapshot(self, snapshot: OrderBookSnapshot) -> None:
        """Apply a full order book snapshot (replaces current state)."""
        async with self._lock:
            # Clear current state
            self.bids.clear()
            self.asks.clear()

            # Apply new snapshot
            for level in snapshot.bids:
                if level.quantity > 0:
                    self.bids[level.price] = level.quantity

            for level in snapshot.asks:
                if level.quantity > 0:
                    self.asks[level.price] = level.quantity

            # Update tracking
            self.last_sequence = snapshot.sequence
            self.last_update_time = time.time()

            # Store in buffer
            self.snapshot_buffer.append(snapshot)

            logger.debug(
                f"Applied snapshot for {self.symbol}: "
                f"{len(self.bids)} bids, {len(self.asks)} asks"
            )

    async def apply_delta(self, delta: OrderBookDelta) -> None:
        """Apply incremental order book update."""
        async with self._lock:
            # Check for sequence gaps
            if delta.sequence > 0 and self.last_sequence > 0:
                if delta.first_update_id > self.last_sequence + 1:
                    logger.warning(
                        f"Sequence gap detected for {self.symbol}: "
                        f"expected {self.last_sequence + 1}, got {delta.first_update_id}"
                    )
                    # In production, would trigger snapshot recovery here

            # Apply bid updates
            for level in delta.bids:
                if level.quantity == 0:
                    # Remove price level
                    self.bids.pop(level.price, None)
                else:
                    # Update price level
                    self.bids[level.price] = level.quantity

            # Apply ask updates
            for level in delta.asks:
                if level.quantity == 0:
                    # Remove price level
                    self.asks.pop(level.price, None)
                else:
                    # Update price level
                    self.asks[level.price] = level.quantity

            # Update tracking
            self.last_sequence = delta.final_update_id
            self.last_update_time = time.time()

    async def get_snapshot(self, depth: int = 20) -> OrderBookSnapshot:
        """Get current order book snapshot."""
        async with self._lock:
            # Sort and limit bids (descending by price)
            sorted_bids = sorted(self.bids.items(), key=lambda x: x[0], reverse=True)
            bid_levels = [
                PriceLevel(price=price, quantity=qty)
                for price, qty in sorted_bids[:depth]
            ]

            # Sort and limit asks (ascending by price)
            sorted_asks = sorted(self.asks.items(), key=lambda x: x[0])
            ask_levels = [
                PriceLevel(price=price, quantity=qty)
                for price, qty in sorted_asks[:depth]
            ]

            return OrderBookSnapshot(
                exchange=self.exchange,
                symbol=self.symbol,
                timestamp_us=int(time.time() * 1_000_000),
                sequence=self.last_sequence,
                bids=bid_levels,
                asks=ask_levels,
            )

    def get_mid_price(self) -> Optional[Decimal]:
        """Calculate mid price."""
        best_bid = self.get_best_bid()
        best_ask = self.get_best_ask()

        if best_bid and best_ask:
            return (best_bid[0] + best_ask[0]) / 2
        return None

    def get_best_bid(self) -> Optional[Tuple[Decimal, Decimal]]:
        """Get best bid (price, quantity)."""
        if not self.bids:
            return None
        price = max(self.bids.keys())
        return (price, self.bids[price])

    def get_best_ask(self) -> Optional[Tuple[Decimal, Decimal]]:
        """Get best ask (price, quantity)."""
        if not self.asks:
            return None
        price = min(self.asks.keys())
        return (price, self.asks[price])

    def get_spread(self) -> Optional[Decimal]:
        """Calculate absolute spread."""
        best_bid = self.get_best_bid()
        best_ask = self.get_best_ask()

        if best_bid and best_ask:
            return best_ask[0] - best_bid[0]
        return None

    def get_spread_bps(self) -> Optional[Decimal]:
        """Calculate spread in basis points."""
        mid = self.get_mid_price()
        spread = self.get_spread()

        if mid and spread and mid > 0:
            return (spread / mid) * Decimal('10000')
        return None

    def get_depth_at_bps(self, bps: int) -> Tuple[Decimal, Decimal]:
        """
        Get cumulative depth at N basis points from mid.

        Args:
            bps: Basis points from mid price

        Returns:
            (bid_depth, ask_depth) - cumulative quantities
        """
        mid = self.get_mid_price()
        if not mid:
            return (Decimal(0), Decimal(0))

        # Calculate price thresholds
        factor = Decimal(1) - Decimal(bps) / Decimal(10000)
        bid_threshold = mid * factor

        factor = Decimal(1) + Decimal(bps) / Decimal(10000)
        ask_threshold = mid * factor

        # Sum bid depth above threshold
        bid_depth = sum(
            qty for price, qty in self.bids.items()
            if price >= bid_threshold
        )

        # Sum ask depth below threshold
        ask_depth = sum(
            qty for price, qty in self.asks.items()
            if price <= ask_threshold
        )

        return (bid_depth, ask_depth)

    def get_imbalance(self, levels: int = 5) -> float:
        """
        Calculate order book imbalance.

        Args:
            levels: Number of price levels to consider

        Returns:
            Imbalance ratio in [-1, 1]
        """
        # Get top N levels
        sorted_bids = sorted(self.bids.items(), key=lambda x: x[0], reverse=True)[:levels]
        sorted_asks = sorted(self.asks.items(), key=lambda x: x[0])[:levels]

        bid_vol = sum(qty for _, qty in sorted_bids)
        ask_vol = sum(qty for _, qty in sorted_asks)

        total = bid_vol + ask_vol
        if total == 0:
            return 0.0

        return float((bid_vol - ask_vol) / total)

    def get_vwap(self, side: str, quantity: Decimal) -> Optional[Decimal]:
        """
        Calculate VWAP for executing a given quantity.

        Args:
            side: "buy" or "sell"
            quantity: Total quantity to execute

        Returns:
            Volume-weighted average price, or None if insufficient liquidity
        """
        if side == "buy":
            # Buying lifts asks
            sorted_levels = sorted(self.asks.items(), key=lambda x: x[0])
        else:
            # Selling hits bids
            sorted_levels = sorted(self.bids.items(), key=lambda x: x[0], reverse=True)

        remaining = quantity
        total_value = Decimal(0)

        for price, level_qty in sorted_levels:
            fill_qty = min(remaining, level_qty)
            total_value += price * fill_qty
            remaining -= fill_qty

            if remaining == 0:
                return total_value / quantity

        # Insufficient liquidity
        return None


class OrderBookManager:
    """Manages multiple order books across exchanges and symbols."""

    def __init__(self):
        """Initialize order book manager."""
        self.books: Dict[str, OrderBook] = {}  # "exchange:symbol" -> OrderBook
        self._lock = asyncio.Lock()

    def _get_key(self, exchange: str, symbol: str) -> str:
        """Generate unique key for order book."""
        return f"{exchange}:{symbol}"

    async def get_or_create_book(self, exchange: str, symbol: str) -> OrderBook:
        """Get existing order book or create new one."""
        key = self._get_key(exchange, symbol)

        async with self._lock:
            if key not in self.books:
                self.books[key] = OrderBook(exchange, symbol)
                logger.info(f"Created order book for {key}")

            return self.books[key]

    async def get_book(self, exchange: str, symbol: str) -> Optional[OrderBook]:
        """Get order book if it exists."""
        key = self._get_key(exchange, symbol)
        return self.books.get(key)

    async def get_all_books(self) -> Dict[str, OrderBook]:
        """Get all order books."""
        return self.books.copy()

    async def get_aggregated_snapshot(
        self, symbol: str, depth: int = 20
    ) -> Optional[OrderBookSnapshot]:
        """
        Get aggregated order book across all exchanges for a symbol.

        Args:
            symbol: Trading pair symbol
            depth: Number of price levels

        Returns:
            Aggregated snapshot or None if no books exist
        """
        # Collect all books for this symbol
        symbol_books = []
        for key, book in self.books.items():
            if book.symbol == symbol:
                symbol_books.append(book)

        if not symbol_books:
            return None

        # Aggregate bids and asks across exchanges
        aggregated_bids: Dict[Decimal, Decimal] = {}
        aggregated_asks: Dict[Decimal, Decimal] = {}

        for book in symbol_books:
            # Add bids
            for price, qty in book.bids.items():
                aggregated_bids[price] = aggregated_bids.get(price, Decimal(0)) + qty

            # Add asks
            for price, qty in book.asks.items():
                aggregated_asks[price] = aggregated_asks.get(price, Decimal(0)) + qty

        # Sort and limit
        sorted_bids = sorted(aggregated_bids.items(), key=lambda x: x[0], reverse=True)
        sorted_asks = sorted(aggregated_asks.items(), key=lambda x: x[0])

        bid_levels = [
            PriceLevel(price=price, quantity=qty)
            for price, qty in sorted_bids[:depth]
        ]
        ask_levels = [
            PriceLevel(price=price, quantity=qty)
            for price, qty in sorted_asks[:depth]
        ]

        return OrderBookSnapshot(
            exchange="aggregated",
            symbol=symbol,
            timestamp_us=int(time.time() * 1_000_000),
            sequence=0,
            bids=bid_levels,
            asks=ask_levels,
        )