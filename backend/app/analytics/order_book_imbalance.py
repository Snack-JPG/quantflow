"""Order Book Imbalance (OBI) implementation.

Source: Widely used in market microstructure; formalized in Cao, Chen & Griffin (2005),
"Informational Content of Option Volume Prior to Takeovers."
"""

from decimal import Decimal
from typing import List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class OrderBookImbalance:
    """
    Calculates Order Book Imbalance (OBI) metrics.

    OBI measures the relative balance between bid-side and ask-side liquidity
    in the order book. A strong predictor of short-term price direction.
    """

    def __init__(self, default_levels: int = 10):
        """
        Initialize OBI calculator.

        Args:
            default_levels: Default number of levels to use for calculation
        """
        self.default_levels = default_levels
        self.last_obi = Decimal('0')
        self.last_weighted_obi = 0.0

    def calculate(
        self,
        bids: List[Tuple[Decimal, Decimal]],
        asks: List[Tuple[Decimal, Decimal]],
        levels: Optional[int] = None
    ) -> Decimal:
        """
        Calculate standard Order Book Imbalance.

        OBI = (V_bid - V_ask) / (V_bid + V_ask)

        Args:
            bids: List of (price, quantity) tuples, sorted descending
            asks: List of (price, quantity) tuples, sorted ascending
            levels: Number of levels to include (default: self.default_levels)

        Returns:
            OBI value in [-1, 1]
            - OBI → +1: heavy bid pressure (bullish)
            - OBI → -1: heavy ask pressure (bearish)
            - OBI ≈  0: balanced book
        """
        if levels is None:
            levels = self.default_levels

        try:
            # Calculate total volume on each side
            bid_vol = sum(qty for _, qty in bids[:levels])
            ask_vol = sum(qty for _, qty in asks[:levels])

            total = bid_vol + ask_vol
            if total == 0:
                self.last_obi = Decimal('0')
                return Decimal('0')

            self.last_obi = (bid_vol - ask_vol) / total

            logger.debug(f"OBI: {self.last_obi:.4f} (bid_vol={bid_vol:.2f}, ask_vol={ask_vol:.2f})")

            return self.last_obi

        except Exception as e:
            logger.error(f"Error calculating OBI: {e}")
            return Decimal('0')

    def calculate_weighted(
        self,
        bids: List[Tuple[Decimal, Decimal]],
        asks: List[Tuple[Decimal, Decimal]],
        levels: Optional[int] = None,
        decay: float = 0.85
    ) -> float:
        """
        Calculate distance-weighted Order Book Imbalance.

        Levels closer to the midpoint get higher weight (exponential decay).

        Args:
            bids: List of (price, quantity) tuples, sorted descending
            asks: List of (price, quantity) tuples, sorted ascending
            levels: Number of levels to include
            decay: Decay factor for distance weighting (0 < decay < 1)

        Returns:
            Weighted OBI value in [-1, 1]
        """
        if levels is None:
            levels = self.default_levels

        try:
            # Calculate weighted volumes
            bid_weighted = sum(
                float(qty) * (decay ** i) for i, (_, qty) in enumerate(bids[:levels])
            )
            ask_weighted = sum(
                float(qty) * (decay ** i) for i, (_, qty) in enumerate(asks[:levels])
            )

            total = bid_weighted + ask_weighted
            if total == 0:
                self.last_weighted_obi = 0.0
                return 0.0

            self.last_weighted_obi = (bid_weighted - ask_weighted) / total

            logger.debug(f"Weighted OBI: {self.last_weighted_obi:.4f} (decay={decay})")

            return self.last_weighted_obi

        except Exception as e:
            logger.error(f"Error calculating weighted OBI: {e}")
            return 0.0

    def get_imbalance_signal(self, threshold: float = 0.3) -> str:
        """
        Get directional signal based on OBI.

        Args:
            threshold: Threshold for significant imbalance

        Returns:
            'bullish', 'bearish', or 'neutral'
        """
        if self.last_obi > threshold:
            return 'bullish'
        elif self.last_obi < -threshold:
            return 'bearish'
        else:
            return 'neutral'

    def get_last_values(self) -> dict:
        """Get last calculated OBI values."""
        return {
            'obi': float(self.last_obi),
            'weighted_obi': self.last_weighted_obi,
            'signal': self.get_imbalance_signal()
        }