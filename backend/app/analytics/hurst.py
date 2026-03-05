"""Hurst Exponent implementation.

Source: Mandelbrot (1971), "When Can Price Be Arbitraged Efficiently?";
formalized via R/S analysis by Hurst (1951).
"""

import numpy as np
from collections import deque
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class HurstExponent:
    """
    Estimate Hurst exponent via R/S analysis.

    The Hurst Exponent H measures the long-term memory of a time series:
    - H = 0.5: random walk (no memory, efficient market)
    - H > 0.5: trending / persistent (momentum)
    - H < 0.5: mean-reverting (anti-persistent)
    """

    def __init__(self, max_prices: int = 500, min_window: int = 10):
        """
        Initialize Hurst exponent calculator.

        Args:
            max_prices: Maximum number of prices to keep for analysis
            min_window: Minimum window size for R/S analysis
        """
        self.max_prices = max_prices
        self.min_window = min_window
        self.prices = deque(maxlen=max_prices)
        self.last_hurst: Optional[float] = None

    def add_price(self, price: float):
        """
        Add a price and recalculate if we have enough data.

        Args:
            price: Current price
        """
        self.prices.append(price)

        # Recalculate periodically (every 10 new prices after minimum)
        if len(self.prices) >= self.min_window * 4 and len(self.prices) % 10 == 0:
            self.last_hurst = self.calculate()

    def calculate(self) -> Optional[float]:
        """
        Calculate Hurst exponent using R/S analysis.

        For each sub-period of length n:
        1. Mean-adjusted series: Y_i = X_i - X̄
        2. Cumulative deviation: Z_i = Σ(j=1 to i) Y_j
        3. Range: R(n) = max(Z) - min(Z)
        4. Standard deviation: S(n) = std(X)
        5. Rescaled range: R(n) / S(n)

        The Hurst exponent H satisfies: E[R(n)/S(n)] = C × n^H

        Returns:
            Hurst exponent or None if insufficient data
        """
        if len(self.prices) < self.min_window * 4:
            return None

        try:
            prices = np.array(self.prices)
            log_returns = np.diff(np.log(prices))
            n = len(log_returns)

            # Generate window sizes (logarithmically spaced)
            max_window = n // 2
            window_sizes = []
            w = self.min_window
            while w <= max_window:
                window_sizes.append(w)
                w = int(w * 1.5)

            log_rs = []
            log_n = []

            for w in window_sizes:
                rs_values = []
                num_segments = n // w

                for i in range(num_segments):
                    segment = log_returns[i * w : (i + 1) * w]
                    mean = np.mean(segment)
                    deviations = segment - mean
                    cumulative = np.cumsum(deviations)

                    R = np.max(cumulative) - np.min(cumulative)
                    S = np.std(segment, ddof=1)

                    if S > 0:
                        rs_values.append(R / S)

                if rs_values:
                    log_rs.append(np.log(np.mean(rs_values)))
                    log_n.append(np.log(w))

            if len(log_rs) < 3:
                return None

            # Linear regression: log(R/S) = H × log(n) + c
            coeffs = np.polyfit(log_n, log_rs, 1)
            H = coeffs[0]

            # Clip to valid range
            H = float(np.clip(H, 0.0, 1.0))

            logger.debug(f"Hurst exponent: {H:.4f} (n={n} prices)")

            self.last_hurst = H
            return H

        except Exception as e:
            logger.error(f"Error calculating Hurst exponent: {e}")
            return None

    def value(self) -> Optional[float]:
        """Get last calculated Hurst exponent."""
        return self.last_hurst

    def get_market_regime(self) -> str:
        """
        Determine market regime based on Hurst exponent.

        Returns:
            'trending', 'random_walk', 'mean_reverting', or 'unknown'
        """
        if self.last_hurst is None:
            return 'unknown'

        if self.last_hurst > 0.55:
            return 'trending'
        elif self.last_hurst < 0.45:
            return 'mean_reverting'
        else:
            return 'random_walk'

    def get_strategy_recommendation(self) -> str:
        """
        Recommend trading strategy based on Hurst exponent.

        Returns:
            Strategy recommendation
        """
        regime = self.get_market_regime()

        if regime == 'trending':
            return 'momentum_breakout'
        elif regime == 'mean_reverting':
            return 'fade_extremes'
        elif regime == 'random_walk':
            return 'avoid_directional'
        else:
            return 'wait_for_data'

    def get_metrics(self) -> dict:
        """Get current Hurst exponent metrics."""
        return {
            'hurst_exponent': self.last_hurst,
            'market_regime': self.get_market_regime(),
            'strategy': self.get_strategy_recommendation(),
            'price_count': len(self.prices)
        }