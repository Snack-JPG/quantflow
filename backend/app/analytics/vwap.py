"""Volume Weighted Average Price (VWAP) implementation.

Source: Standard institutional execution benchmark. Formalized in
Berkowitz, Logue & Noser (1988).
"""

from collections import deque
from decimal import Decimal
from typing import Dict, Optional, List
import logging
import time

logger = logging.getLogger(__name__)


class VWAP:
    """
    Volume Weighted Average Price calculator with multiple rolling windows.

    VWAP is the average price of an asset weighted by volume over a time window.
    Used as a benchmark for execution quality — executing at or better than VWAP
    means you didn't move the market against yourself.
    """

    def __init__(self, window_seconds: List[int] = [60, 300, 900]):  # 1m, 5m, 15m
        """
        Initialize VWAP calculator with multiple window sizes.

        Args:
            window_seconds: List of window sizes in seconds [60, 300, 900] for 1m, 5m, 15m
        """
        self.windows = {}
        for window in window_seconds:
            self.windows[window] = RollingVWAPWindow(window)

    def add_trade(self, timestamp_ms: int, price: Decimal, quantity: Decimal):
        """
        Add a trade to all VWAP windows.

        Args:
            timestamp_ms: Trade timestamp in milliseconds
            price: Trade price
            quantity: Trade volume/quantity
        """
        for window in self.windows.values():
            window.add_trade(timestamp_ms, price, quantity)

    def get_values(self) -> Dict[str, Optional[Decimal]]:
        """
        Get current VWAP values for all windows.

        Returns:
            Dictionary mapping window name to VWAP value
            e.g., {'vwap_1m': Decimal('50000'), 'vwap_5m': Decimal('49950'), ...}
        """
        result = {}
        for window_seconds, calculator in self.windows.items():
            if window_seconds == 60:
                key = 'vwap_1m'
            elif window_seconds == 300:
                key = 'vwap_5m'
            elif window_seconds == 900:
                key = 'vwap_15m'
            else:
                key = f'vwap_{window_seconds}s'

            result[key] = calculator.value()

        return result


class RollingVWAPWindow:
    """Rolling VWAP over a fixed time window."""

    def __init__(self, window_seconds: int):
        """
        Initialize a rolling VWAP window.

        Args:
            window_seconds: Window size in seconds
        """
        self.window_seconds = window_seconds
        self.trades = deque()  # (timestamp_ms, price × volume, volume)
        self.sum_pv = Decimal('0')  # Σ(price × volume)
        self.sum_v = Decimal('0')  # Σ(volume)

    def add_trade(self, timestamp_ms: int, price: Decimal, quantity: Decimal):
        """
        Add a trade and update VWAP.

        Args:
            timestamp_ms: Trade timestamp in milliseconds
            price: Trade price
            quantity: Trade volume
        """
        try:
            pv = price * quantity
            self.trades.append((timestamp_ms, pv, quantity))
            self.sum_pv += pv
            self.sum_v += quantity
            self._evict_old(timestamp_ms)

            logger.debug(f"VWAP window {self.window_seconds}s: added trade p={price}, q={quantity}")

        except Exception as e:
            logger.error(f"Error adding trade to VWAP: {e}")

    def _evict_old(self, current_ts: int):
        """Remove trades outside the time window."""
        cutoff = current_ts - (self.window_seconds * 1000)

        while self.trades and self.trades[0][0] < cutoff:
            _, old_pv, old_v = self.trades.popleft()
            self.sum_pv -= old_pv
            self.sum_v -= old_v

    def value(self) -> Optional[Decimal]:
        """
        Get current VWAP value.

        Returns:
            VWAP value or None if no trades in window
        """
        if self.sum_v == 0:
            return None
        return self.sum_pv / self.sum_v

    def trade_count(self) -> int:
        """Get number of trades in current window."""
        return len(self.trades)