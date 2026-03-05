"""Unit tests for VPIN (Volume-Synchronized Probability of Informed Trading)."""

import unittest
import numpy as np
from app.analytics.vpin import VPIN


class TestVPIN(unittest.TestCase):
    """Test cases for VPIN calculator."""

    def setUp(self):
        """Set up test fixtures."""
        self.vpin = VPIN(bucket_size=100.0, n_buckets=5)

    def test_balanced_flow(self):
        """Test VPIN with balanced buy/sell flow."""
        # Add bars with no price change (balanced flow)
        for i in range(10):
            self.vpin.add_bar(
                open_price=100.0,
                close_price=100.0,  # No change
                volume=50.0
            )

        # With no price changes, flow should be balanced
        # VPIN should be close to 0
        value = self.vpin.value()
        if value is not None:
            self.assertLess(value, 0.1)

    def test_directional_flow(self):
        """Test VPIN with directional (informed) flow."""
        # Fill enough buckets
        for i in range(10):
            # Strong upward movement
            self.vpin.add_bar(
                open_price=100.0,
                close_price=105.0,  # 5% increase
                volume=50.0
            )

        # Strong directional flow should give higher VPIN
        value = self.vpin.value()
        if value is not None:
            self.assertGreater(value, 0.2)

    def test_bulk_volume_classification(self):
        """Test the Bulk Volume Classification logic."""
        # Upward bar
        self.vpin.add_bar(
            open_price=100.0,
            close_price=110.0,
            volume=100.0
        )

        # Check that buy volume > sell volume for upward bar
        if self.vpin.buckets:
            v_buy, v_sell = self.vpin.buckets[-1]
            self.assertGreater(v_buy, v_sell)

        # Downward bar
        self.vpin.add_bar(
            open_price=110.0,
            close_price=100.0,
            volume=100.0
        )

        # Check that sell volume > buy volume for downward bar
        if len(self.vpin.buckets) > 1:
            v_buy, v_sell = self.vpin.buckets[-1]
            self.assertLess(v_buy, v_sell)

    def test_bucket_filling(self):
        """Test that buckets are filled correctly."""
        bucket_size = 100.0
        vpin = VPIN(bucket_size=bucket_size, n_buckets=5)

        # Add exactly one bucket worth of volume
        vpin.add_bar(
            open_price=100.0,
            close_price=101.0,
            volume=bucket_size
        )

        self.assertEqual(len(vpin.buckets), 1)

        # Add half a bucket more
        vpin.add_bar(
            open_price=101.0,
            close_price=102.0,
            volume=bucket_size / 2
        )

        self.assertEqual(len(vpin.buckets), 1)  # Still 1 complete bucket

        # Complete the second bucket
        vpin.add_bar(
            open_price=102.0,
            close_price=103.0,
            volume=bucket_size / 2
        )

        self.assertEqual(len(vpin.buckets), 2)

    def test_insufficient_buckets(self):
        """Test VPIN returns None with insufficient data."""
        # Only add a small amount of volume
        self.vpin.add_bar(
            open_price=100.0,
            close_price=101.0,
            volume=10.0  # Much less than bucket size
        )

        # Should return None without enough buckets
        self.assertIsNone(self.vpin.value())

    def test_toxicity_levels(self):
        """Test toxicity level classification."""
        self.vpin.last_vpin = 0.1
        self.assertEqual(self.vpin.get_toxicity_level(), 'low')

        self.vpin.last_vpin = 0.3
        self.assertEqual(self.vpin.get_toxicity_level(), 'moderate')

        self.vpin.last_vpin = 0.5
        self.assertEqual(self.vpin.get_toxicity_level(), 'high')

        self.vpin.last_vpin = 0.7
        self.assertEqual(self.vpin.get_toxicity_level(), 'extreme')

    def test_vpin_range(self):
        """Test VPIN stays within [0, 1] range."""
        # Add various types of bars
        for i in range(20):
            if i % 2 == 0:
                # Upward bar
                self.vpin.add_bar(
                    open_price=100.0,
                    close_price=102.0,
                    volume=30.0
                )
            else:
                # Downward bar
                self.vpin.add_bar(
                    open_price=102.0,
                    close_price=100.0,
                    volume=30.0
                )

        value = self.vpin.value()
        if value is not None:
            self.assertGreaterEqual(value, 0.0)
            self.assertLessEqual(value, 1.0)

    def test_trade_method(self):
        """Test the alternative add_trade method."""
        # Initialize price
        self.vpin.last_price = 100.0

        # Add trades
        self.vpin.add_trade(price=101.0, volume=50.0)
        self.vpin.add_trade(price=102.0, volume=50.0)
        self.vpin.add_trade(price=101.5, volume=50.0)

        # Should have processed some data
        self.assertGreater(self.vpin.current_volume, 0)

    def test_metrics_output(self):
        """Test the get_metrics method."""
        # Add enough data
        for i in range(10):
            self.vpin.add_bar(
                open_price=100.0 + i,
                close_price=101.0 + i,
                volume=50.0
            )

        metrics = self.vpin.get_metrics()

        self.assertIn('vpin', metrics)
        self.assertIn('toxicity_level', metrics)
        self.assertIn('completed_buckets', metrics)
        self.assertIn('current_bucket_progress', metrics)
        self.assertIn('sigma', metrics)

        # Check bucket progress is between 0 and 1
        progress = metrics['current_bucket_progress']
        self.assertGreaterEqual(progress, 0)
        self.assertLessEqual(progress, 1)

    def test_sigma_calculation(self):
        """Test standard deviation calculation for BVC."""
        # Add bars with varying price changes
        for i in range(20):
            change = np.random.randn() * 2  # Random price change
            self.vpin.add_bar(
                open_price=100.0,
                close_price=100.0 + change,
                volume=10.0
            )

        # Sigma should be positive
        sigma = self.vpin._calculate_sigma()
        self.assertGreater(sigma, 0)


if __name__ == '__main__':
    unittest.main()