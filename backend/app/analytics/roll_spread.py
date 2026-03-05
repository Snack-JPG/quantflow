"""Roll Spread Estimator implementation.

Source: Roll (1984), "A Simple Implicit Measure of the Effective Bid-Ask Spread
in an Efficient Market," Journal of Finance, 39(4), 1127-1139.
"""

import numpy as np
from collections import deque
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class RollSpread:
    """
    Roll (1984) implied spread estimator.

    Roll's model infers the effective spread from the autocovariance of consecutive
    price changes. The intuition: if a market bounces between bid and ask,
    consecutive returns will be negatively autocorrelated.
    """

    def __init__(self, window: int = 100):
        """
        Initialize Roll Spread estimator.

        Args:
            window: Number of prices to keep for calculation
        """
        self.window = window
        self.prices = deque(maxlen=window + 2)
        self.last_spread: Optional[float] = None

    def update(self, price: float) -> Optional[float]:
        """
        Update with new price and calculate Roll spread.

        The formula: Cov(ΔP_t, ΔP_{t-1}) = -c²/4
        Therefore: Roll_Spread = 2 × √(-Cov(ΔP_t, ΔP_{t-1}))

        Args:
            price: Current price

        Returns:
            Estimated spread or None if insufficient data
        """
        self.prices.append(price)

        if len(self.prices) < 4:
            return None

        try:
            # Calculate price changes
            prices = np.array(self.prices)
            returns = np.diff(prices)  # ΔP series

            # Calculate autocovariance at lag 1
            n = len(returns)
            if n < 2:
                return None

            r1 = returns[1:]
            r0 = returns[:-1]

            # Covariance calculation
            cov = np.mean(r1 * r0) - np.mean(r1) * np.mean(r0)

            if cov >= 0:
                # Undefined in trending regime (positive autocovariance)
                self.last_spread = 0.0
                logger.debug("Roll spread undefined (trending market)")
                return 0.0

            # Roll spread formula
            self.last_spread = 2.0 * np.sqrt(-cov)

            logger.debug(f"Roll spread: {self.last_spread:.6f} (cov={cov:.8f})")

            return self.last_spread

        except Exception as e:
            logger.error(f"Error calculating Roll spread: {e}")
            return None

    def value(self) -> Optional[float]:
        """Get last calculated Roll spread."""
        return self.last_spread

    def get_market_regime(self) -> str:
        """
        Determine market regime based on spread calculation.

        Returns:
            'mean_reverting' if Roll spread is defined, 'trending' otherwise
        """
        if self.last_spread is None:
            return 'unknown'
        elif self.last_spread > 0:
            return 'mean_reverting'
        else:
            return 'trending'

    def get_metrics(self) -> dict:
        """Get current Roll spread metrics."""
        return {
            'roll_spread': self.last_spread,
            'market_regime': self.get_market_regime(),
            'observations': len(self.prices)
        }