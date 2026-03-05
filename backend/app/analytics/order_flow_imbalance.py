"""Order Flow Imbalance (OFI) implementation.

Source: Cont, Kukanov & Stoikov (2014), "The Price Impact of Order Book Events,"
Quantitative Finance.
"""

from decimal import Decimal
from dataclasses import dataclass
from collections import deque
from typing import Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class BookTop:
    """Top of book snapshot."""
    bid_price: Decimal
    bid_qty: Decimal
    ask_price: Decimal
    ask_qty: Decimal


class OrderFlowImbalance:
    """
    Calculates Order Flow Imbalance per Cont, Kukanov & Stoikov (2014).

    OFI captures the change in order book state between snapshots — not just the
    static imbalance, but the dynamics of how liquidity is being added and removed.
    It's a more robust predictor of price changes than static OBI because it
    captures aggressive order flow.
    """

    def __init__(self, cumulative_window: int = 50):
        """
        Initialize OFI calculator.

        Args:
            cumulative_window: Window size for cumulative OFI calculation
        """
        self.prev: Optional[BookTop] = None
        self.cumulative_window = cumulative_window
        self.ofi_buffer = deque(maxlen=cumulative_window)
        self.last_ofi = Decimal('0')
        self.cumulative_ofi = Decimal('0')

    def update(self, current: BookTop) -> Optional[Decimal]:
        """
        Calculate OFI from current book top.

        The formula captures order book events:
        - If bid price increases: e_b = +Q_bid(t) (new aggressive bid)
        - If bid price unchanged: e_b = Q_bid(t) - Q_bid(t-1) (quantity change)
        - If bid price decreases: e_b = -Q_bid(t-1) (bid pulled/consumed)

        Similar logic for ask side, then OFI = e_b - e_a

        Args:
            current: Current top of book snapshot

        Returns:
            OFI value or None for first update
        """
        if self.prev is None:
            self.prev = current
            return None

        try:
            # Calculate bid-side event
            if current.bid_price > self.prev.bid_price:
                # New aggressive bid
                e_b = current.bid_qty
            elif current.bid_price == self.prev.bid_price:
                # Quantity change at same level
                e_b = current.bid_qty - self.prev.bid_qty
            else:
                # Bid pulled or consumed
                e_b = -self.prev.bid_qty

            # Calculate ask-side event
            if current.ask_price < self.prev.ask_price:
                # New aggressive ask
                e_a = current.ask_qty
            elif current.ask_price == self.prev.ask_price:
                # Quantity change at same level
                e_a = current.ask_qty - self.prev.ask_qty
            else:
                # Ask pulled or consumed
                e_a = -self.prev.ask_qty

            # Order Flow Imbalance
            ofi = e_b - e_a

            self.last_ofi = ofi
            self.ofi_buffer.append(ofi)
            self.cumulative_ofi = sum(self.ofi_buffer)

            logger.debug(f"OFI: {ofi:.2f} (e_b={e_b:.2f}, e_a={e_a:.2f}), cumulative={self.cumulative_ofi:.2f}")

            self.prev = current
            return ofi

        except Exception as e:
            logger.error(f"Error calculating OFI: {e}")
            return Decimal('0')

    def get_cumulative(self) -> Decimal:
        """
        Get cumulative OFI over the rolling window.

        Returns:
            Sum of OFI values in the buffer
        """
        return self.cumulative_ofi

    def get_signal(self, threshold: Decimal = Decimal('100')) -> str:
        """
        Get directional signal based on cumulative OFI.

        Args:
            threshold: Threshold for significant flow imbalance

        Returns:
            'buy_pressure', 'sell_pressure', or 'neutral'
        """
        if self.cumulative_ofi > threshold:
            return 'buy_pressure'
        elif self.cumulative_ofi < -threshold:
            return 'sell_pressure'
        else:
            return 'neutral'

    def get_metrics(self) -> dict:
        """Get current OFI metrics."""
        return {
            'ofi': float(self.last_ofi),
            'cumulative_ofi': float(self.cumulative_ofi),
            'window_size': len(self.ofi_buffer),
            'signal': self.get_signal()
        }