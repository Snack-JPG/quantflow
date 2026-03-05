"""Realized Volatility implementation.

Source: Andersen & Bollerslev (1998), "Answering the Skeptics: Yes, Standard
Volatility Models Do Provide Accurate Forecasts," International Economic Review.
"""

import numpy as np
from collections import deque
import math
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class RealizedVolatility:
    """
    Realized volatility from trade returns with multiple window sizes.

    RV is the sum of squared returns computed from high-frequency data.
    It's a model-free estimate of true volatility over a given window.
    """

    def __init__(self, windows: List[int] = [60, 300, 900, 3600]):
        """
        Initialize realized volatility calculator.

        Args:
            windows: List of lookback periods in seconds [60, 300, 900, 3600]
                    for 1m, 5m, 15m, 1h
        """
        self.windows = windows
        self.log_returns = deque()  # (timestamp_ms, log_return)
        self.last_price: Optional[float] = None
        self.last_values: Dict[int, float] = {}

    def add_trade(self, timestamp_ms: int, price: float):
        """
        Add a trade and calculate log return.

        Args:
            timestamp_ms: Trade timestamp in milliseconds
            price: Trade price
        """
        try:
            if self.last_price is not None and self.last_price > 0:
                lr = math.log(price / self.last_price)
                self.log_returns.append((timestamp_ms, lr))

                logger.debug(f"RV: price={price:.2f}, log_return={lr:.6f}")

            self.last_price = price

            # Evict old returns (keep max window + buffer)
            max_window_ms = max(self.windows) * 1000 + 60000
            cutoff = timestamp_ms - max_window_ms
            while self.log_returns and self.log_returns[0][0] < cutoff:
                self.log_returns.popleft()

            # Update calculations
            self.last_values = self.compute(timestamp_ms)

        except Exception as e:
            logger.error(f"Error adding trade to RV: {e}")

    def compute(self, current_ts_ms: int) -> Dict[int, float]:
        """
        Compute realized volatility for each window size.

        RV = √(Σ r_i²)

        Args:
            current_ts_ms: Current timestamp in milliseconds

        Returns:
            Dictionary mapping window size to RV value
        """
        result = {}

        for w in self.windows:
            cutoff = current_ts_ms - (w * 1000)
            returns = [lr for ts, lr in self.log_returns if ts >= cutoff]

            if len(returns) < 2:
                result[w] = 0.0
            else:
                # Sum of squared returns
                sum_sq = sum(r * r for r in returns)
                result[w] = math.sqrt(sum_sq)

        return result

    def get_annualized(self, current_ts_ms: Optional[int] = None) -> Dict[str, float]:
        """
        Get annualized realized volatility for all windows.

        Crypto trades 365 days: RV_annual = RV_period × √(365 × 24 × 3600 / period_seconds)

        Args:
            current_ts_ms: Current timestamp (uses last values if None)

        Returns:
            Dictionary with annualized volatilities
        """
        if current_ts_ms is not None:
            values = self.compute(current_ts_ms)
        else:
            values = self.last_values

        result = {}
        seconds_per_year = 365 * 24 * 3600

        for window_seconds, rv in values.items():
            # Annualization factor
            periods_per_year = seconds_per_year / window_seconds
            annualized = rv * math.sqrt(periods_per_year)

            # Create readable key
            if window_seconds == 60:
                key = 'rv_1m_annual'
            elif window_seconds == 300:
                key = 'rv_5m_annual'
            elif window_seconds == 900:
                key = 'rv_15m_annual'
            elif window_seconds == 3600:
                key = 'rv_1h_annual'
            else:
                key = f'rv_{window_seconds}s_annual'

            result[key] = annualized

        return result

    def get_term_structure(self) -> str:
        """
        Analyze volatility term structure.

        Returns:
            'spike' if short-term >> long-term
            'compression' if short-term << long-term
            'normal' otherwise
        """
        if len(self.last_values) < 2:
            return 'unknown'

        sorted_windows = sorted(self.last_values.keys())
        if len(sorted_windows) < 2:
            return 'unknown'

        short_term = self.last_values[sorted_windows[0]]
        long_term = self.last_values[sorted_windows[-1]]

        if short_term > long_term * 1.5:
            return 'spike'
        elif short_term < long_term * 0.7:
            return 'compression'
        else:
            return 'normal'

    def get_metrics(self) -> dict:
        """Get comprehensive volatility metrics."""
        return {
            'realized_vol': self.last_values,
            'annualized': self.get_annualized(),
            'term_structure': self.get_term_structure(),
            'return_count': len(self.log_returns)
        }