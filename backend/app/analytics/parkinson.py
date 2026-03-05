"""Parkinson Volatility implementation.

Source: Parkinson (1980), "The Extreme Value Method for Estimating the Variance
of the Rate of Return," Journal of Business, 53(1), 61-65.
"""

import math
from collections import deque
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class ParkinsonVolatility:
    """
    Parkinson (1980) high-low range volatility estimator.

    Uses only high-low range to estimate volatility. 5.2x more efficient than
    close-to-close. Particularly useful when you only have high/low data.
    """

    def __init__(self, window: int = 20):
        """
        Initialize Parkinson volatility calculator.

        Args:
            window: Number of bars for rolling calculation
        """
        self.window = window
        self.log_ranges_sq = deque(maxlen=window)
        self.last_value: Optional[float] = None

    def add_bar(self, high: float, low: float):
        """
        Add a high-low bar and calculate volatility component.

        Args:
            high: High price
            low: Low price
        """
        try:
            if low <= 0:
                logger.warning(f"Invalid high-low data: H={high}, L={low}")
                return

            # Log of high/low ratio
            log_range = math.log(high / low)
            self.log_ranges_sq.append(log_range ** 2)

            # Update volatility
            self._update_volatility()

            logger.debug(f"Parkinson bar: H={high:.2f}, L={low:.2f}, log_range²={log_range**2:.8f}")

        except Exception as e:
            logger.error(f"Error adding bar to Parkinson volatility: {e}")

    def _update_volatility(self):
        """Calculate current Parkinson volatility."""
        n = len(self.log_ranges_sq)
        if n < 2:
            return

        # Parkinson formula: σ² = (1 / (4 × N × ln2)) × Σ[ln(H/L)]²
        sum_sq = sum(self.log_ranges_sq)
        variance = sum_sq / (4 * n * math.log(2))
        self.last_value = math.sqrt(variance)

    def value(self) -> Optional[float]:
        """
        Get current Parkinson volatility.

        Returns:
            Volatility estimate or None if insufficient data
        """
        return self.last_value

    def annualized(self, bars_per_year: int = 365 * 24 * 60) -> Optional[float]:
        """
        Get annualized Parkinson volatility.

        Args:
            bars_per_year: Number of bars in a year (default: 1-minute bars)

        Returns:
            Annualized volatility
        """
        if self.last_value is None:
            return None

        return self.last_value * math.sqrt(bars_per_year)

    def compare_efficiency(self, realized_vol: Optional[float]) -> Optional[str]:
        """
        Compare Parkinson to realized volatility to detect market characteristics.

        Args:
            realized_vol: Realized volatility for comparison

        Returns:
            Market characteristic assessment
        """
        if self.last_value is None or realized_vol is None:
            return None

        ratio = self.last_value / realized_vol if realized_vol > 0 else 0

        if ratio > 1.3:
            return 'intrabar_extremes'  # Wicks, liquidations
        elif ratio < 0.7:
            return 'noise_dominated'  # Microstructure noise
        else:
            return 'normal'

    def get_metrics(self) -> dict:
        """Get current Parkinson volatility metrics."""
        return {
            'parkinson_volatility': self.last_value,
            'parkinson_annualized': self.annualized(),
            'observations': len(self.log_ranges_sq)
        }