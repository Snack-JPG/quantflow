"""Unit tests for Order Book Imbalance (OBI) implementation."""

import unittest
from decimal import Decimal
from app.analytics.order_book_imbalance import OrderBookImbalance


class TestOrderBookImbalance(unittest.TestCase):
    """Test cases for OBI calculator."""

    def setUp(self):
        """Set up test fixtures."""
        self.obi = OrderBookImbalance(default_levels=5)

    def test_balanced_order_book(self):
        """Test OBI with perfectly balanced order book."""
        bids = [
            (Decimal('100'), Decimal('10')),
            (Decimal('99'), Decimal('10')),
            (Decimal('98'), Decimal('10')),
        ]
        asks = [
            (Decimal('101'), Decimal('10')),
            (Decimal('102'), Decimal('10')),
            (Decimal('103'), Decimal('10')),
        ]

        result = self.obi.calculate(bids, asks, levels=3)

        # Equal volumes on both sides should give OBI = 0
        self.assertEqual(result, Decimal('0'))

    def test_bid_heavy_imbalance(self):
        """Test OBI with more volume on bid side."""
        bids = [
            (Decimal('100'), Decimal('20')),
            (Decimal('99'), Decimal('15')),
            (Decimal('98'), Decimal('10')),
        ]
        asks = [
            (Decimal('101'), Decimal('5')),
            (Decimal('102'), Decimal('5')),
            (Decimal('103'), Decimal('5')),
        ]

        result = self.obi.calculate(bids, asks, levels=3)

        # Bid volume = 45, Ask volume = 15
        # OBI = (45 - 15) / (45 + 15) = 30/60 = 0.5
        self.assertEqual(result, Decimal('0.5'))
        self.assertEqual(self.obi.get_imbalance_signal(), 'bullish')

    def test_ask_heavy_imbalance(self):
        """Test OBI with more volume on ask side."""
        bids = [
            (Decimal('100'), Decimal('5')),
            (Decimal('99'), Decimal('5')),
            (Decimal('98'), Decimal('5')),
        ]
        asks = [
            (Decimal('101'), Decimal('20')),
            (Decimal('102'), Decimal('15')),
            (Decimal('103'), Decimal('10')),
        ]

        result = self.obi.calculate(bids, asks, levels=3)

        # Bid volume = 15, Ask volume = 45
        # OBI = (15 - 45) / (15 + 45) = -30/60 = -0.5
        self.assertEqual(result, Decimal('-0.5'))
        self.assertEqual(self.obi.get_imbalance_signal(), 'bearish')

    def test_weighted_obi(self):
        """Test distance-weighted OBI calculation."""
        bids = [
            (Decimal('100'), Decimal('100')),  # Closest to mid
            (Decimal('99'), Decimal('10')),
            (Decimal('98'), Decimal('10')),
        ]
        asks = [
            (Decimal('101'), Decimal('10')),   # Closest to mid
            (Decimal('102'), Decimal('10')),
            (Decimal('103'), Decimal('100')),
        ]

        # Standard OBI should be balanced
        standard = self.obi.calculate(bids, asks, levels=3)
        self.assertEqual(standard, Decimal('0'))

        # Weighted OBI should favor bids (100 at top level)
        weighted = self.obi.calculate_weighted(bids, asks, levels=3, decay=0.5)
        self.assertGreater(weighted, 0)  # Should be positive (bid-heavy)

    def test_partial_levels(self):
        """Test OBI with fewer levels than requested."""
        bids = [
            (Decimal('100'), Decimal('10')),
            (Decimal('99'), Decimal('10')),
        ]
        asks = [
            (Decimal('101'), Decimal('10')),
            (Decimal('102'), Decimal('10')),
        ]

        # Request 10 levels but only 2 available
        result = self.obi.calculate(bids, asks, levels=10)
        self.assertEqual(result, Decimal('0'))  # Should handle gracefully

    def test_empty_order_book(self):
        """Test OBI with empty order book."""
        result = self.obi.calculate([], [], levels=5)
        self.assertEqual(result, Decimal('0'))

    def test_one_sided_book(self):
        """Test OBI with only bids or only asks."""
        bids = [
            (Decimal('100'), Decimal('10')),
            (Decimal('99'), Decimal('10')),
        ]

        # Only bids
        result = self.obi.calculate(bids, [], levels=2)
        self.assertEqual(result, Decimal('1'))  # Maximum bid imbalance

        # Only asks
        result = self.obi.calculate([], bids, levels=2)  # Using bids as asks
        self.assertEqual(result, Decimal('-1'))  # Maximum ask imbalance

    def test_signal_thresholds(self):
        """Test imbalance signal generation."""
        # Neutral signal
        self.obi.last_obi = Decimal('0.1')
        self.assertEqual(self.obi.get_imbalance_signal(threshold=0.3), 'neutral')

        # Bullish signal
        self.obi.last_obi = Decimal('0.4')
        self.assertEqual(self.obi.get_imbalance_signal(threshold=0.3), 'bullish')

        # Bearish signal
        self.obi.last_obi = Decimal('-0.4')
        self.assertEqual(self.obi.get_imbalance_signal(threshold=0.3), 'bearish')

    def test_decay_parameter(self):
        """Test different decay parameters for weighted OBI."""
        bids = [
            (Decimal('100'), Decimal('10')),
            (Decimal('99'), Decimal('10')),
            (Decimal('98'), Decimal('10')),
        ]
        asks = [
            (Decimal('101'), Decimal('10')),
            (Decimal('102'), Decimal('10')),
            (Decimal('103'), Decimal('10')),
        ]

        # Higher decay = less weight on distant levels
        high_decay = self.obi.calculate_weighted(bids, asks, levels=3, decay=0.9)
        low_decay = self.obi.calculate_weighted(bids, asks, levels=3, decay=0.1)

        # With uniform book, both should be close to 0
        self.assertAlmostEqual(high_decay, 0, places=2)
        self.assertAlmostEqual(low_decay, 0, places=2)

    def test_get_last_values(self):
        """Test retrieving last calculated values."""
        bids = [(Decimal('100'), Decimal('15'))]
        asks = [(Decimal('101'), Decimal('5'))]

        self.obi.calculate(bids, asks, levels=1)
        self.obi.calculate_weighted(bids, asks, levels=1)

        values = self.obi.get_last_values()
        self.assertIn('obi', values)
        self.assertIn('weighted_obi', values)
        self.assertIn('signal', values)
        self.assertEqual(values['signal'], 'bullish')


if __name__ == '__main__':
    unittest.main()