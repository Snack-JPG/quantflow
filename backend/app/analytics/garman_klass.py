"""Garman-Klass Volatility implementation.

Source: Garman & Klass (1980), "On the Estimation of Security Price Volatilities
from Historical Data," Journal of Business, 53(1), 67-78.
"""

import math
from collections import deque
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class GarmanKlassVolatility:
    """
    Garman-Klass (1980) OHLC volatility estimator.

    An OHLC-based volatility estimator that is 7.4x more efficient than the
    close-to-close estimator. Uses the full price range information within each bar.
    """

    def __init__(self, window: int = 20):
        """
        Initialize Garman-Klass volatility calculator.

        Args:
            window: Number of bars for rolling calculation
        """
        self.window = window
        self.estimates = deque(maxlen=window)
        self.last_value: Optional[float] = None

    def add_bar(self, open_: float, high: float, low: float, close: float):
        """
        Add an OHLC bar and calculate volatility component.

        σ²_GK = 0.5 × [ln(H/L)]² - (2ln2 - 1) × [ln(C/O)]²

        Args:
            open_: Opening price
            high: High price
            low: Low price
            close: Closing price
        """
        try:
            if low <= 0 or open_ <= 0:
                logger.warning(f"Invalid OHLC data: O={open_}, L={low}")
                return

            # Garman-Klass formula components
            log_hl = math.log(high / low)
            log_co = math.log(close / open_)

            # Variance estimate for this bar
            sigma2 = 0.5 * log_hl ** 2 - (2 * math.log(2) - 1) * log_co ** 2

            self.estimates.append(sigma2)

            # Update volatility calculation
            self._update_volatility()

            logger.debug(f"GK bar: O={open_:.2f}, H={high:.2f}, L={low:.2f}, C={close:.2f}, σ²={sigma2:.8f}")

        except Exception as e:
            logger.error(f"Error adding bar to GK volatility: {e}")

    def _update_volatility(self):
        """Calculate current Garman-Klass volatility."""
        if len(self.estimates) < 2:
            return

        # Average variance over window
        avg_var = sum(self.estimates) / len(self.estimates)

        # Handle numerical issues
        if avg_var < 0:
            avg_var = 0

        self.last_value = math.sqrt(avg_var)

    def value(self) -> Optional[float]:
        """
        Get current Garman-Klass volatility.

        Returns:
            Volatility estimate or None if insufficient data
        """
        return self.last_value

    def annualized(self, bars_per_year: int = 365 * 24 * 60) -> Optional[float]:
        """
        Get annualized Garman-Klass volatility.

        Args:
            bars_per_year: Number of bars in a year (default: 1-minute bars)

        Returns:
            Annualized volatility
        """
        if self.last_value is None:
            return None

        return self.last_value * math.sqrt(bars_per_year)

    def get_metrics(self) -> dict:
        """Get current Garman-Klass metrics."""
        return {
            'gk_volatility': self.last_value,
            'gk_annualized': self.annualized(),
            'observations': len(self.estimates)
        }