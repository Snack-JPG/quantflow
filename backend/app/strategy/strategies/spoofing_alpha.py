"""
Spoofing Detection Alpha Strategy.

This strategy detects spoofing patterns and trades against the fake orders.
When spoofing is detected, it assumes the spoofer is trying to manipulate
price in one direction to trade in the opposite direction.
"""
from typing import List, Dict, Any, Optional, Tuple
from decimal import Decimal
from datetime import datetime, timedelta
from collections import deque
from dataclasses import dataclass

from ..base import Strategy
from ..models import (
    OrderBookSnapshot,
    Trade,
    Alert,
    Signal,
    SignalDirection,
    OrderSide,
    PriceLevel
)


@dataclass
class SpoofingEvent:
    """Record of potential spoofing event."""
    timestamp: datetime
    symbol: str
    side: str  # 'bid' or 'ask'
    price: Decimal
    size: Decimal
    levels_affected: int
    confidence: float


class SpoofingAlphaStrategy(Strategy):
    """
    Spoofing Detection Alpha Strategy.

    Detects spoofing patterns and trades opposite to the fake orders.

    Parameters:
    - size_threshold_multiplier: Order size threshold as multiple of avg (default 3.0)
    - cancel_time_threshold: Max time before cancel to consider spoofing (default 2.0 seconds)
    - min_events_for_signal: Min spoofing events to generate signal (default 3)
    - lookback_window: Time window to track spoofing events (default 60 seconds)
    - confidence_threshold: Min confidence to trade on alert (default 0.8)
    """

    def __init__(
        self,
        name: str = "Spoofing_Alpha",
        symbols: List[str] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """Initialize Spoofing Alpha strategy."""
        super().__init__(name, symbols or ['BTCUSDT'], config)

        # Strategy parameters
        self.size_threshold_multiplier = self.config.get('size_threshold_multiplier', 3.0)
        self.cancel_time_threshold = self.config.get('cancel_time_threshold', 2.0)
        self.min_events_for_signal = self.config.get('min_events_for_signal', 3)
        self.lookback_window = self.config.get('lookback_window', 60)  # seconds
        self.confidence_threshold = self.config.get('confidence_threshold', 0.8)

        # Spoofing detection state
        self.book_history: Dict[str, deque] = {}  # Symbol -> deque of (timestamp, snapshot)
        self.spoofing_events: Dict[str, deque] = {}  # Symbol -> deque of SpoofingEvent
        self.level_sizes: Dict[str, deque] = {}  # Symbol -> deque of avg level sizes

        # Large order tracking
        self.large_orders: Dict[str, List[Tuple[datetime, str, Decimal, Decimal]]] = {}

        # Initialize state
        for symbol in self.symbols:
            self.book_history[symbol] = deque(maxlen=100)  # Keep last 100 snapshots
            self.spoofing_events[symbol] = deque()
            self.level_sizes[symbol] = deque(maxlen=50)
            self.large_orders[symbol] = []

    def on_book_update(self, book: OrderBookSnapshot) -> List[Signal]:
        """Handle order book update - main driver for spoofing detection."""
        signals = []
        symbol = book.symbol
        current_time = book.timestamp

        # Store book snapshot
        self.book_history[symbol].append((current_time, book))
        self.last_book[symbol] = book

        # Update average level sizes
        avg_bid_size = sum(level.quantity for level in book.bids[:10]) / 10 if len(book.bids) >= 10 else Decimal('0')
        avg_ask_size = sum(level.quantity for level in book.asks[:10]) / 10 if len(book.asks) >= 10 else Decimal('0')
        self.level_sizes[symbol].append((avg_bid_size + avg_ask_size) / 2)

        # Detect spoofing patterns
        spoofing_detected = self._detect_spoofing(symbol, book)

        if spoofing_detected:
            for event in spoofing_detected:
                self.spoofing_events[symbol].append(event)

        # Clean old spoofing events
        cutoff_time = current_time - timedelta(seconds=self.lookback_window)
        while self.spoofing_events[symbol] and self.spoofing_events[symbol][0].timestamp < cutoff_time:
            self.spoofing_events[symbol].popleft()

        # Generate signals based on spoofing pattern
        if len(self.spoofing_events[symbol]) >= self.min_events_for_signal:
            signal = self._generate_anti_spoof_signal(symbol, book)
            if signal:
                signals.append(signal)

        return signals

    def on_alert(self, alert: Alert) -> List[Signal]:
        """Handle pattern detection alert - enhanced spoofing detection."""
        signals = []

        # React to high-confidence spoofing alerts
        if alert.pattern == "spoofing" and alert.confidence >= self.confidence_threshold:
            symbol = alert.symbol

            if symbol in self.last_book and not self.has_position(symbol):
                book = self.last_book[symbol]

                # Trade opposite to the spoofing direction
                spoof_side = alert.context.get('side', '')
                if spoof_side == 'bid':
                    # Spoofer showing fake buy interest -> they want to sell
                    # We should buy (front-run the spoofer)
                    signal = self.generate_signal(
                        symbol=symbol,
                        direction=SignalDirection.LONG,
                        strength=alert.confidence,
                        reason=f"Spoofing detected on bid side (confidence: {alert.confidence:.2f}) - trading against manipulation",
                        alert_id=alert.id,
                        spoof_side=spoof_side,
                        mid_price=float(book.mid_price)
                    )
                    signals.append(signal)

                elif spoof_side == 'ask':
                    # Spoofer showing fake sell interest -> they want to buy
                    # We should sell (front-run the spoofer)
                    signal = self.generate_signal(
                        symbol=symbol,
                        direction=SignalDirection.SHORT,
                        strength=alert.confidence,
                        reason=f"Spoofing detected on ask side (confidence: {alert.confidence:.2f}) - trading against manipulation",
                        alert_id=alert.id,
                        spoof_side=spoof_side,
                        mid_price=float(book.mid_price)
                    )
                    signals.append(signal)

        return signals

    def on_trade(self, trade: Trade) -> List[Signal]:
        """Handle trade event."""
        self.last_trade[trade.symbol] = trade

        # Check for exit conditions if we have a position
        if self.has_position(trade.symbol):
            position = self.get_position(trade.symbol)

            # Exit if large trade goes against us (spoofer might be executing)
            avg_size = sum(self.level_sizes[trade.symbol]) / len(self.level_sizes[trade.symbol]) if self.level_sizes[trade.symbol] else Decimal('1')

            if trade.quantity > avg_size * Decimal('5'):  # Very large trade
                if (position.side == OrderSide.BUY and trade.side == OrderSide.SELL) or \
                   (position.side == OrderSide.SELL and trade.side == OrderSide.BUY):
                    signal = self.generate_signal(
                        symbol=trade.symbol,
                        direction=SignalDirection.CLOSE,
                        strength=1.0,
                        reason=f"Large trade against position - potential spoofer execution",
                        trade_size=float(trade.quantity),
                        trade_price=float(trade.price)
                    )
                    return [signal]

        return []

    def _detect_spoofing(self, symbol: str, current_book: OrderBookSnapshot) -> List[SpoofingEvent]:
        """
        Detect potential spoofing by analyzing order book changes.

        Look for:
        1. Large orders that appear and disappear quickly
        2. Layered orders at multiple price levels that cancel together
        3. Orders significantly larger than average
        """
        events = []

        if len(self.book_history[symbol]) < 2:
            return events

        # Get previous book
        prev_time, prev_book = self.book_history[symbol][-2]
        time_diff = (current_book.timestamp - prev_time).total_seconds()

        if time_diff > self.cancel_time_threshold:
            return events  # Too much time passed

        # Calculate average level size
        if not self.level_sizes[symbol]:
            return events

        avg_size = sum(self.level_sizes[symbol]) / len(self.level_sizes[symbol])
        threshold_size = avg_size * Decimal(str(self.size_threshold_multiplier))

        # Check for disappeared large bid orders (potential bid spoofing)
        for prev_level in prev_book.bids[:5]:
            if prev_level.quantity > threshold_size:
                # Check if this large order disappeared
                found = False
                for curr_level in current_book.bids[:5]:
                    if abs(curr_level.price - prev_level.price) < Decimal('0.01'):
                        if curr_level.quantity >= prev_level.quantity * Decimal('0.8'):
                            found = True
                            break

                if not found:
                    # Large bid disappeared - potential spoofing
                    event = SpoofingEvent(
                        timestamp=current_book.timestamp,
                        symbol=symbol,
                        side='bid',
                        price=prev_level.price,
                        size=prev_level.quantity,
                        levels_affected=1,
                        confidence=min(1.0, float(prev_level.quantity / threshold_size) * 0.5)
                    )
                    events.append(event)

        # Check for disappeared large ask orders (potential ask spoofing)
        for prev_level in prev_book.asks[:5]:
            if prev_level.quantity > threshold_size:
                # Check if this large order disappeared
                found = False
                for curr_level in current_book.asks[:5]:
                    if abs(curr_level.price - prev_level.price) < Decimal('0.01'):
                        if curr_level.quantity >= prev_level.quantity * Decimal('0.8'):
                            found = True
                            break

                if not found:
                    # Large ask disappeared - potential spoofing
                    event = SpoofingEvent(
                        timestamp=current_book.timestamp,
                        symbol=symbol,
                        side='ask',
                        price=prev_level.price,
                        size=prev_level.quantity,
                        levels_affected=1,
                        confidence=min(1.0, float(prev_level.quantity / threshold_size) * 0.5)
                    )
                    events.append(event)

        return events

    def _generate_anti_spoof_signal(self, symbol: str, book: OrderBookSnapshot) -> Optional[Signal]:
        """Generate signal to trade against detected spoofing."""
        if self.has_position(symbol):
            return None

        # Analyze recent spoofing events
        recent_events = list(self.spoofing_events[symbol])
        if not recent_events:
            return None

        # Count spoofing by side
        bid_spoofs = sum(1 for e in recent_events if e.side == 'bid')
        ask_spoofs = sum(1 for e in recent_events if e.side == 'ask')

        # Determine dominant spoofing side
        if bid_spoofs > ask_spoofs * 1.5:
            # More bid spoofing - spoofer likely wants to sell
            # We buy to front-run
            avg_confidence = sum(e.confidence for e in recent_events if e.side == 'bid') / bid_spoofs

            return self.generate_signal(
                symbol=symbol,
                direction=SignalDirection.LONG,
                strength=min(1.0, avg_confidence),
                reason=f"Multiple bid spoofing events detected ({bid_spoofs} events) - trading against manipulation",
                bid_spoofs=bid_spoofs,
                ask_spoofs=ask_spoofs,
                avg_confidence=avg_confidence,
                mid_price=float(book.mid_price)
            )

        elif ask_spoofs > bid_spoofs * 1.5:
            # More ask spoofing - spoofer likely wants to buy
            # We sell to front-run
            avg_confidence = sum(e.confidence for e in recent_events if e.side == 'ask') / ask_spoofs

            return self.generate_signal(
                symbol=symbol,
                direction=SignalDirection.SHORT,
                strength=min(1.0, avg_confidence),
                reason=f"Multiple ask spoofing events detected ({ask_spoofs} events) - trading against manipulation",
                bid_spoofs=bid_spoofs,
                ask_spoofs=ask_spoofs,
                avg_confidence=avg_confidence,
                mid_price=float(book.mid_price)
            )

        return None

    def reset(self):
        """Reset strategy state."""
        super().reset()

        # Clear all state
        self.book_history.clear()
        self.spoofing_events.clear()
        self.level_sizes.clear()
        self.large_orders.clear()

        # Reinitialize
        for symbol in self.symbols:
            self.book_history[symbol] = deque(maxlen=100)
            self.spoofing_events[symbol] = deque()
            self.level_sizes[symbol] = deque(maxlen=50)
            self.large_orders[symbol] = []