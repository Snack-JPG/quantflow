"""Kyle's Lambda price impact implementation.

Source: Kyle (1985), "Continuous Auctions and Insider Trading," Econometrica, 53(6), 1315-1335.
"""

import numpy as np
from decimal import Decimal
from collections import deque
from typing import Optional, Dict
import logging

logger = logging.getLogger(__name__)


class KylesLambda:
    """
    Kyle's Lambda measures the permanent price impact of order flow.

    It is the slope coefficient from regressing price changes on signed order flow.
    Higher λ means lower liquidity (each unit of volume moves the price more).
    """

    def __init__(self, window_size: int = 100, min_observations: int = 20):
        """
        Initialize Kyle's Lambda calculator.

        Args:
            window_size: Number of intervals to keep for regression
            min_observations: Minimum observations required for regression
        """
        self.window_size = window_size
        self.min_observations = min_observations

        # Buffers for regression
        self.price_changes = deque(maxlen=window_size)
        self.signed_volumes = deque(maxlen=window_size)

        # Last price for calculating changes
        self.last_price: Optional[float] = None
        self.last_midpoint: Optional[float] = None

        # Last calculated values
        self.lambda_coeff: Optional[float] = None
        self.alpha: Optional[float] = None
        self.r_squared: Optional[float] = None

    def classify_trade_direction(
        self,
        trade_price: float,
        bid: float,
        ask: float,
        prev_price: Optional[float] = None
    ) -> int:
        """
        Lee-Ready trade classification algorithm.

        Args:
            trade_price: Execution price
            bid: Best bid at time of trade
            ask: Best ask at time of trade
            prev_price: Previous trade price (for tick test)

        Returns:
            1 for buyer-initiated, -1 for seller-initiated, 0 for indeterminate
        """
        mid = (bid + ask) / 2

        if trade_price > mid:
            return 1  # buyer-initiated
        elif trade_price < mid:
            return -1  # seller-initiated
        else:
            # Tick test fallback
            if prev_price is not None:
                if trade_price > prev_price:
                    return 1
                elif trade_price < prev_price:
                    return -1
            return 0  # indeterminate

    def add_interval(
        self,
        price: float,
        signed_volume: float
    ):
        """
        Add a price change and signed volume for an interval.

        Args:
            price: Current price (end of interval)
            signed_volume: Net signed order flow for the interval
        """
        if self.last_price is not None:
            price_change = price - self.last_price
            self.price_changes.append(price_change)
            self.signed_volumes.append(signed_volume)

            # Recalculate lambda if we have enough observations
            if len(self.price_changes) >= self.min_observations:
                self._calculate_lambda()

        self.last_price = price

    def add_trade(
        self,
        trade_price: float,
        volume: float,
        bid: float,
        ask: float,
        prev_trade_price: Optional[float] = None
    ) -> Optional[float]:
        """
        Process a single trade and update signed volume accumulator.

        This is a helper method for accumulating signed volume over intervals.
        Call add_interval() periodically with accumulated signed volume.

        Args:
            trade_price: Trade execution price
            volume: Trade size
            bid: Best bid at time of trade
            ask: Best ask at time of trade
            prev_trade_price: Previous trade price

        Returns:
            Signed volume for this trade
        """
        direction = self.classify_trade_direction(trade_price, bid, ask, prev_trade_price)
        signed_vol = direction * volume

        logger.debug(f"Trade classified: price={trade_price:.2f}, direction={direction}, signed_vol={signed_vol:.2f}")

        return signed_vol

    def _calculate_lambda(self):
        """
        Estimate Kyle's Lambda via OLS regression.
        ΔP = α + λ × SignedVolume + ε
        """
        try:
            n = len(self.price_changes)
            if n < self.min_observations:
                return

            # Convert to numpy arrays
            price_changes = np.array(self.price_changes)
            signed_volumes = np.array(self.signed_volumes)

            # OLS: ΔP = α + λ × S
            X = np.column_stack([np.ones(n), signed_volumes])
            beta, residuals, rank, s = np.linalg.lstsq(X, price_changes, rcond=None)

            self.alpha = beta[0]
            self.lambda_coeff = beta[1]

            # Calculate R-squared
            y_hat = X @ beta
            ss_res = np.sum((price_changes - y_hat) ** 2)
            ss_tot = np.sum((price_changes - np.mean(price_changes)) ** 2)
            self.r_squared = 1 - ss_res / ss_tot if ss_tot > 0 else 0

            logger.debug(f"Kyle's Lambda: λ={self.lambda_coeff:.6f}, R²={self.r_squared:.3f}")

        except Exception as e:
            logger.error(f"Error calculating Kyle's Lambda: {e}")

    def get_metrics(self) -> Dict[str, Optional[float]]:
        """
        Get current Kyle's Lambda metrics.

        Returns:
            Dictionary with lambda coefficient, alpha, R-squared, and observation count
        """
        return {
            'lambda': self.lambda_coeff,
            'alpha': self.alpha,
            'r_squared': self.r_squared,
            'n_observations': len(self.price_changes),
            'price_impact_per_unit': self.lambda_coeff  # More intuitive name
        }

    def get_liquidity_assessment(self) -> str:
        """
        Assess market liquidity based on Kyle's Lambda.

        Returns:
            Liquidity assessment: 'deep', 'moderate', 'shallow', or 'unknown'
        """
        if self.lambda_coeff is None:
            return 'unknown'

        # These thresholds are asset-specific and should be calibrated
        if abs(self.lambda_coeff) < 0.00001:
            return 'deep'
        elif abs(self.lambda_coeff) < 0.0001:
            return 'moderate'
        else:
            return 'shallow'