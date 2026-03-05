"""Volume-Synchronized Probability of Informed Trading (VPIN) implementation.

Source: Easley, López de Prado & O'Hara (2012), "Flow Toxicity and Liquidity
in a High-Frequency World," Review of Financial Studies, 25(5), 1457-1493.
"""

import numpy as np
from scipy.stats import norm
from collections import deque
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class VPIN:
    """
    VPIN estimates the probability that informed traders are active in the market.

    Unlike time-based metrics, VPIN is synchronized on volume — it uses fixed-volume
    buckets rather than fixed-time intervals, which better captures information
    arrival in fast markets.
    """

    def __init__(self, bucket_size: float = 10000.0, n_buckets: int = 50):
        """
        Initialize VPIN calculator.

        Args:
            bucket_size: Size of each volume bucket (e.g., 10000 units)
            n_buckets: Number of buckets for rolling window (typically 50)
        """
        self.bucket_size = bucket_size
        self.n_buckets = n_buckets

        # Completed buckets: (v_buy, v_sell) per bucket
        self.buckets = deque(maxlen=n_buckets)

        # Current partial bucket accumulation
        self.current_buy = 0.0
        self.current_sell = 0.0
        self.current_volume = 0.0

        # For sigma estimation (standard deviation of price changes)
        self.price_changes = deque(maxlen=200)
        self.last_price: Optional[float] = None

        # Last calculated VPIN
        self.last_vpin: Optional[float] = None

    def _calculate_sigma(self) -> float:
        """
        Calculate standard deviation of price changes for BVC.

        Returns:
            Standard deviation or small epsilon if insufficient data
        """
        if len(self.price_changes) < 10:
            return 1e-8  # avoid division by zero

        return float(np.std(self.price_changes)) or 1e-8

    def add_bar(self, open_price: float, close_price: float, volume: float):
        """
        Process a time bar (e.g., 1-second or 1-minute bar) using Bulk Volume Classification.

        BVC classifies trade volume probabilistically using the price change within a bar:
        V_buy = V × Φ((P_close - P_open) / σ_ΔP)
        V_sell = V - V_buy

        Args:
            open_price: Opening price of the bar
            close_price: Closing price of the bar
            volume: Total volume in the bar
        """
        try:
            # Track price changes for sigma estimation
            dp = close_price - open_price
            self.price_changes.append(dp)

            # Bulk Volume Classification
            sigma = self._calculate_sigma()
            z = dp / sigma
            buy_fraction = norm.cdf(z)  # Standard normal CDF

            v_buy = volume * buy_fraction
            v_sell = volume * (1 - buy_fraction)

            # Add to current bucket
            self.current_buy += v_buy
            self.current_sell += v_sell
            self.current_volume += volume

            # Fill buckets when we have enough volume
            while self.current_volume >= self.bucket_size:
                # Scale to exact bucket size
                scale = self.bucket_size / self.current_volume
                bucket_buy = self.current_buy * scale
                bucket_sell = self.current_sell * scale

                self.buckets.append((bucket_buy, bucket_sell))

                # Remainder carries over to next bucket
                self.current_buy -= bucket_buy
                self.current_sell -= bucket_sell
                self.current_volume -= self.bucket_size

                logger.debug(f"Completed bucket: buy={bucket_buy:.2f}, sell={bucket_sell:.2f}")

            # Update VPIN calculation
            self._update_vpin()

        except Exception as e:
            logger.error(f"Error adding bar to VPIN: {e}")

    def add_trade(self, price: float, volume: float):
        """
        Alternative method: Add individual trades (will be aggregated into bars internally).

        For simplicity, this creates a micro-bar from each trade.

        Args:
            price: Trade price
            volume: Trade volume
        """
        if self.last_price is not None:
            self.add_bar(self.last_price, price, volume)
        self.last_price = price

    def _update_vpin(self):
        """Calculate current VPIN value from completed buckets."""
        if len(self.buckets) < self.n_buckets:
            # Not enough buckets yet
            return

        # VPIN = (1/n) × Σ |V_buy_i - V_sell_i| / V_bucket
        total_imbalance = sum(
            abs(v_buy - v_sell) for v_buy, v_sell in self.buckets
        )
        self.last_vpin = total_imbalance / (self.n_buckets * self.bucket_size)

        logger.debug(f"VPIN updated: {self.last_vpin:.4f}")

    def value(self) -> Optional[float]:
        """
        Get current VPIN estimate.

        Returns:
            VPIN value in [0, 1] or None if insufficient data
            - VPIN → 0: uninformed flow dominates (balanced buy/sell)
            - VPIN → 1: informed flow dominates (one-sided pressure)
        """
        return self.last_vpin

    def get_toxicity_level(self) -> str:
        """
        Assess flow toxicity based on VPIN value.

        Returns:
            'low', 'moderate', 'high', 'extreme', or 'unknown'
        """
        if self.last_vpin is None:
            return 'unknown'

        if self.last_vpin < 0.2:
            return 'low'
        elif self.last_vpin < 0.4:
            return 'moderate'
        elif self.last_vpin < 0.6:
            return 'high'
        else:
            return 'extreme'

    def get_metrics(self) -> dict:
        """Get current VPIN metrics and status."""
        return {
            'vpin': self.last_vpin,
            'toxicity_level': self.get_toxicity_level(),
            'completed_buckets': len(self.buckets),
            'current_bucket_progress': self.current_volume / self.bucket_size if self.bucket_size > 0 else 0,
            'sigma': self._calculate_sigma()
        }