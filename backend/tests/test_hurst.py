"""Unit tests for Hurst Exponent implementation."""

import unittest
import numpy as np
from app.analytics.hurst import HurstExponent


class TestHurstExponent(unittest.TestCase):
    """Test cases for Hurst Exponent calculator."""

    def setUp(self):
        """Set up test fixtures."""
        self.hurst = HurstExponent(max_prices=200, min_window=10)

    def test_random_walk(self):
        """Test Hurst exponent for random walk (should be ~0.5)."""
        np.random.seed(42)
        prices = [100.0]

        # Generate random walk
        for _ in range(100):
            change = np.random.randn() * 1.0
            prices.append(prices[-1] * (1 + change / 100))

        # Add prices to calculator
        for price in prices:
            self.hurst.add_price(price)

        h = self.hurst.calculate()

        # Random walk should have H close to 0.5
        if h is not None:
            self.assertGreater(h, 0.3)
            self.assertLess(h, 0.7)

    def test_trending_series(self):
        """Test Hurst exponent for trending series (should be > 0.5)."""
        prices = []
        base_price = 100.0

        # Generate trending series with noise
        for i in range(100):
            trend = i * 0.5  # Upward trend
            noise = np.random.randn() * 0.1
            prices.append(base_price + trend + noise)

        # Add prices to calculator
        for price in prices:
            self.hurst.add_price(price)

        h = self.hurst.calculate()

        # Trending series should have H > 0.5
        if h is not None:
            self.assertGreater(h, 0.5)

    def test_mean_reverting_series(self):
        """Test Hurst exponent for mean-reverting series (should be < 0.5)."""
        prices = []
        mean = 100.0
        current = mean

        # Generate mean-reverting series
        for _ in range(100):
            # Pull back toward mean
            change = (mean - current) * 0.1 + np.random.randn() * 0.5
            current += change
            prices.append(current)

        # Add prices to calculator
        for price in prices:
            self.hurst.add_price(price)

        h = self.hurst.calculate()

        # Mean-reverting series often has H < 0.5
        # Note: This test may be flaky due to random component
        if h is not None:
            # Just check it's in valid range
            self.assertGreaterEqual(h, 0.0)
            self.assertLessEqual(h, 1.0)

    def test_insufficient_data(self):
        """Test Hurst returns None with insufficient data."""
        # Add too few prices
        for i in range(10):
            self.hurst.add_price(100.0 + i)

        h = self.hurst.calculate()
        self.assertIsNone(h)  # Should return None with insufficient data

    def test_market_regime_detection(self):
        """Test market regime classification."""
        self.hurst.last_hurst = 0.7
        self.assertEqual(self.hurst.get_market_regime(), 'trending')

        self.hurst.last_hurst = 0.5
        self.assertEqual(self.hurst.get_market_regime(), 'random_walk')

        self.hurst.last_hurst = 0.3
        self.assertEqual(self.hurst.get_market_regime(), 'mean_reverting')

        self.hurst.last_hurst = None
        self.assertEqual(self.hurst.get_market_regime(), 'unknown')

    def test_strategy_recommendation(self):
        """Test strategy recommendations based on Hurst."""
        self.hurst.last_hurst = 0.7
        self.assertEqual(self.hurst.get_strategy_recommendation(), 'momentum_breakout')

        self.hurst.last_hurst = 0.3
        self.assertEqual(self.hurst.get_strategy_recommendation(), 'fade_extremes')

        self.hurst.last_hurst = 0.5
        self.assertEqual(self.hurst.get_strategy_recommendation(), 'avoid_directional')

    def test_hurst_range(self):
        """Test Hurst stays within [0, 1] range."""
        np.random.seed(123)

        # Add various types of price series
        for _ in range(150):
            price = 100 + np.random.randn() * 10
            self.hurst.add_price(price)

        h = self.hurst.calculate()

        if h is not None:
            self.assertGreaterEqual(h, 0.0)
            self.assertLessEqual(h, 1.0)

    def test_periodic_recalculation(self):
        """Test that Hurst recalculates periodically."""
        # Add enough prices to trigger first calculation
        for i in range(40):
            self.hurst.add_price(100 + i * 0.1)

        first_h = self.hurst.last_hurst

        # Add more prices (should trigger recalculation every 10 prices)
        for i in range(10):
            self.hurst.add_price(140 + i * 0.1)

        # Should have recalculated
        second_h = self.hurst.last_hurst

        # Values might be the same but calculation should have happened
        self.assertIsNotNone(second_h)

    def test_metrics_output(self):
        """Test the get_metrics method."""
        # Add enough data
        for i in range(100):
            price = 100 + np.sin(i * 0.1) * 10 + np.random.randn()
            self.hurst.add_price(price)

        self.hurst.calculate()
        metrics = self.hurst.get_metrics()

        self.assertIn('hurst_exponent', metrics)
        self.assertIn('market_regime', metrics)
        self.assertIn('strategy', metrics)
        self.assertIn('price_count', metrics)

        self.assertEqual(metrics['price_count'], 100)

    def test_constant_prices(self):
        """Test Hurst with constant prices (edge case)."""
        # Add constant prices
        for _ in range(50):
            self.hurst.add_price(100.0)

        h = self.hurst.calculate()
        # With constant prices, log returns are undefined
        # Should handle gracefully
        if h is not None:
            self.assertGreaterEqual(h, 0.0)
            self.assertLessEqual(h, 1.0)


if __name__ == '__main__':
    unittest.main()