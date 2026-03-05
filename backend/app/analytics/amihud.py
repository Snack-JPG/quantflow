"""Amihud Illiquidity Ratio implementation.

Source: Amihud (2002), "Illiquidity and Stock Returns: Cross-Section and
Time-Series Effects," Journal of Financial Markets, 5(1), 31-56.
"""

from decimal import Decimal
from collections import deque
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class AmihudIlliquidity:
    """
    Rolling Amihud illiquidity ratio calculator.

    The Amihud ratio measures price impact per unit of dollar volume.
    Higher values = less liquid (price moves more per dollar of volume).
    """

    def __init__(self, window: int = 20):
        """
        Initialize Amihud illiquidity calculator.

        Args:
            window: Rolling window size (number of periods)
        """
        self.window = window
        self.ratios = deque(maxlen=window)
        self.prev_price: Optional[float] = None
        self.last_amihud: Optional[float] = None

    def update(self, price: float, volume: float) -> Optional[float]:
        """
        Update with new price and volume data.

        ILLIQ_t = |r_t| / DollarVolume_t
        where r_t = (P_t - P_{t-1}) / P_{t-1}

        Args:
            price: Current price
            volume: Volume traded

        Returns:
            Current Amihud illiquidity ratio or None if insufficient data
        """
        try:
            if self.prev_price is None or self.prev_price == 0:
                self.prev_price = price
                return None

            # Calculate return
            ret = abs((price - self.prev_price) / self.prev_price)

            # Calculate dollar volume
            dollar_volume = price * volume

            if dollar_volume > 0:
                # Amihud ratio for this period
                ratio = ret / dollar_volume
                self.ratios.append(ratio)

                logger.debug(f"Amihud period: ret={ret:.6f}, $vol={dollar_volume:.2f}, ratio={ratio:.8f}")

            self.prev_price = price

            if len(self.ratios) < 2:
                return None

            # Average over window
            self.last_amihud = sum(self.ratios) / len(self.ratios)

            return self.last_amihud

        except Exception as e:
            logger.error(f"Error calculating Amihud ratio: {e}")
            return None

    def value(self) -> Optional[float]:
        """Get current Amihud illiquidity value."""
        return self.last_amihud

    def get_liquidity_assessment(self) -> str:
        """
        Assess liquidity based on Amihud ratio.

        Returns:
            'liquid', 'moderate', 'illiquid', or 'unknown'
        """
        if self.last_amihud is None:
            return 'unknown'

        # These thresholds are asset-specific
        if self.last_amihud < 1e-9:
            return 'liquid'
        elif self.last_amihud < 1e-7:
            return 'moderate'
        else:
            return 'illiquid'

    def get_metrics(self) -> dict:
        """Get current Amihud metrics."""
        return {
            'amihud': self.last_amihud,
            'liquidity': self.get_liquidity_assessment(),
            'observations': len(self.ratios)
        }