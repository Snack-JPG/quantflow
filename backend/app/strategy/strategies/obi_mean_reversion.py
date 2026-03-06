"""
Order Book Imbalance (OBI) Mean Reversion Strategy.

This strategy trades on the assumption that extreme order book imbalances
will revert to the mean. When OBI is very positive (lots of bids), we expect
price to rise temporarily then revert. When OBI is very negative (lots of asks),
we expect price to fall temporarily then revert.
"""
from typing import List, Dict, Any, Optional
from decimal import Decimal
from datetime import datetime, timedelta
from collections import deque

from ..base import Strategy
from ..models import (
    OrderBookSnapshot,
    Trade,
    Alert,
    Signal,
    SignalDirection
)


class OBIMeanReversionStrategy(Strategy):
    """
    Order Book Imbalance Mean Reversion Strategy.

    Parameters:
    - obi_threshold: OBI threshold to trigger signal (default 0.7)
    - lookback_periods: Number of periods for mean calculation (default 20)
    - exit_on_mean_cross: Exit when OBI crosses mean (default True)
    - max_holding_period: Maximum holding period in seconds (default 300)
    - levels: Number of order book levels to use for OBI (default 5)
    """

    def __init__(
        self,
        name: str = "OBI_MeanReversion",
        symbols: List[str] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """Initialize OBI Mean Reversion strategy."""
        super().__init__(name, symbols or ['BTCUSDT'], config)

        # Strategy parameters
        self.obi_threshold = self.config.get('obi_threshold', 0.7)
        self.lookback_periods = self.config.get('lookback_periods', 20)
        self.exit_on_mean_cross = self.config.get('exit_on_mean_cross', True)
        self.max_holding_period = self.config.get('max_holding_period', 300)  # seconds
        self.levels = self.config.get('levels', 5)

        # Internal state
        self.obi_history: Dict[str, deque] = {}
        self.entry_time: Dict[str, datetime] = {}
        self.entry_obi: Dict[str, float] = {}

        # Initialize history buffers
        for symbol in self.symbols:
            self.obi_history[symbol] = deque(maxlen=self.lookback_periods)

    def on_book_update(self, book: OrderBookSnapshot) -> List[Signal]:
        """Handle order book update."""
        signals = []
        symbol = book.symbol

        # Calculate current OBI
        current_obi = book.get_order_book_imbalance(self.levels)

        # Update history
        if symbol not in self.obi_history:
            self.obi_history[symbol] = deque(maxlen=self.lookback_periods)
        self.obi_history[symbol].append(current_obi)

        # Store last book for reference
        self.last_book[symbol] = book

        # Need enough history for mean calculation
        if len(self.obi_history[symbol]) < self.lookback_periods:
            return signals

        # Calculate mean and standard deviation
        obi_mean = sum(self.obi_history[symbol]) / len(self.obi_history[symbol])
        obi_std = self._calculate_std(self.obi_history[symbol], obi_mean)

        # Check for existing position
        if self.has_position(symbol):
            # Check exit conditions
            position = self.get_position(symbol)
            should_exit = False
            exit_reason = ""

            # Exit on mean cross
            if self.exit_on_mean_cross:
                if position.side.value == "buy" and current_obi <= obi_mean:
                    should_exit = True
                    exit_reason = "OBI crossed below mean"
                elif position.side.value == "sell" and current_obi >= obi_mean:
                    should_exit = True
                    exit_reason = "OBI crossed above mean"

            # Exit on max holding period
            if symbol in self.entry_time:
                holding_time = (book.timestamp - self.entry_time[symbol]).total_seconds()
                if holding_time > self.max_holding_period:
                    should_exit = True
                    exit_reason = f"Max holding period ({self.max_holding_period}s) reached"

            # Exit if OBI reverses significantly
            if symbol in self.entry_obi:
                obi_change = abs(current_obi - self.entry_obi[symbol])
                if obi_change > 2 * obi_std and obi_std > 0:
                    should_exit = True
                    exit_reason = "OBI reversed significantly"

            if should_exit:
                signal = self.generate_signal(
                    symbol=symbol,
                    direction=SignalDirection.CLOSE,
                    strength=1.0,
                    reason=f"Exit: {exit_reason}",
                    obi=current_obi,
                    obi_mean=obi_mean,
                    obi_std=obi_std
                )
                signals.append(signal)

                # Clean up state
                if symbol in self.entry_time:
                    del self.entry_time[symbol]
                if symbol in self.entry_obi:
                    del self.entry_obi[symbol]

        else:
            # Look for entry signals
            # Calculate z-score
            z_score = (current_obi - obi_mean) / obi_std if obi_std > 0 else 0

            # Mean reversion signals (counter-trend)
            if current_obi > self.obi_threshold and z_score > 2:
                # High OBI - expect mean reversion down, so SHORT
                signal = self.generate_signal(
                    symbol=symbol,
                    direction=SignalDirection.SHORT,
                    strength=min(1.0, abs(z_score) / 3),  # Scale strength by extremeness
                    reason=f"OBI extreme high ({current_obi:.3f}), expecting mean reversion",
                    obi=current_obi,
                    obi_mean=obi_mean,
                    obi_std=obi_std,
                    z_score=z_score
                )
                signals.append(signal)

                # Store entry state
                self.entry_time[symbol] = book.timestamp
                self.entry_obi[symbol] = current_obi

            elif current_obi < -self.obi_threshold and z_score < -2:
                # Low OBI - expect mean reversion up, so LONG
                signal = self.generate_signal(
                    symbol=symbol,
                    direction=SignalDirection.LONG,
                    strength=min(1.0, abs(z_score) / 3),
                    reason=f"OBI extreme low ({current_obi:.3f}), expecting mean reversion",
                    obi=current_obi,
                    obi_mean=obi_mean,
                    obi_std=obi_std,
                    z_score=z_score
                )
                signals.append(signal)

                # Store entry state
                self.entry_time[symbol] = book.timestamp
                self.entry_obi[symbol] = current_obi

        return signals

    def on_trade(self, trade: Trade) -> List[Signal]:
        """Handle trade event."""
        # This strategy primarily uses order book data
        # Could use trade data to confirm momentum
        self.last_trade[trade.symbol] = trade
        return []

    def on_alert(self, alert: Alert) -> List[Signal]:
        """Handle pattern detection alert."""
        # Could use alerts to filter signals
        # For example, avoid trading during detected manipulation
        return []

    def _calculate_std(self, values: deque, mean: float) -> float:
        """Calculate standard deviation."""
        if len(values) < 2:
            return 0.0

        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return variance ** 0.5

    def reset(self):
        """Reset strategy state."""
        super().reset()
        self.obi_history.clear()
        self.entry_time.clear()
        self.entry_obi.clear()

        # Reinitialize history buffers
        for symbol in self.symbols:
            self.obi_history[symbol] = deque(maxlen=self.lookback_periods)