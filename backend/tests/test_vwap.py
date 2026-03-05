"""Unit tests for VWAP (Volume Weighted Average Price) implementation."""

import unittest
from decimal import Decimal
import time
from app.analytics.vwap import VWAP, RollingVWAPWindow


class TestVWAP(unittest.TestCase):
    """Test cases for VWAP calculator."""

    def test_single_trade_vwap(self):
        """Test VWAP with a single trade."""
        vwap = RollingVWAPWindow(window_seconds=60)
        timestamp_ms = int(time.time() * 1000)
        price = Decimal('50000')
        quantity = Decimal('1.5')

        vwap.add_trade(timestamp_ms, price, quantity)

        # VWAP of single trade should equal the price
        self.assertEqual(vwap.value(), price)

    def test_multiple_trades_same_price(self):
        """Test VWAP with multiple trades at the same price."""
        vwap = RollingVWAPWindow(window_seconds=60)
        timestamp_ms = int(time.time() * 1000)
        price = Decimal('50000')

        for i in range(5):
            vwap.add_trade(timestamp_ms + i * 100, price, Decimal('1'))

        # VWAP should equal the constant price
        self.assertEqual(vwap.value(), price)

    def test_weighted_average_calculation(self):
        """Test VWAP correctly calculates weighted average."""
        vwap = RollingVWAPWindow(window_seconds=60)
        base_ts = int(time.time() * 1000)

        # Trade 1: 100 @ 1 unit = 100
        # Trade 2: 200 @ 2 units = 400
        # Trade 3: 300 @ 1 unit = 300
        # Total: 800 / 4 units = 200

        vwap.add_trade(base_ts, Decimal('100'), Decimal('1'))
        vwap.add_trade(base_ts + 100, Decimal('200'), Decimal('2'))
        vwap.add_trade(base_ts + 200, Decimal('300'), Decimal('1'))

        expected = Decimal('200')
        self.assertEqual(vwap.value(), expected)

    def test_window_eviction(self):
        """Test that old trades are evicted from the window."""
        window_seconds = 1  # 1 second window
        vwap = RollingVWAPWindow(window_seconds=window_seconds)
        base_ts = int(time.time() * 1000)

        # Add trade within window
        vwap.add_trade(base_ts, Decimal('100'), Decimal('1'))
        self.assertEqual(vwap.value(), Decimal('100'))

        # Add trade after window expires (2 seconds later)
        new_ts = base_ts + 2000
        vwap.add_trade(new_ts, Decimal('200'), Decimal('1'))

        # Old trade should be evicted, only new trade remains
        self.assertEqual(vwap.value(), Decimal('200'))

    def test_multiple_windows(self):
        """Test VWAP with multiple window sizes."""
        vwap = VWAP(window_seconds=[60, 300, 900])
        base_ts = int(time.time() * 1000)

        # Add some trades
        vwap.add_trade(base_ts, Decimal('100'), Decimal('1'))
        vwap.add_trade(base_ts + 1000, Decimal('150'), Decimal('2'))
        vwap.add_trade(base_ts + 2000, Decimal('200'), Decimal('1'))

        values = vwap.get_values()

        # Check all windows have values
        self.assertIn('vwap_1m', values)
        self.assertIn('vwap_5m', values)
        self.assertIn('vwap_15m', values)

        # All windows should have same value since all trades are within 1 minute
        expected = (Decimal('100') + Decimal('300') + Decimal('200')) / Decimal('4')
        self.assertEqual(values['vwap_1m'], expected)
        self.assertEqual(values['vwap_5m'], expected)
        self.assertEqual(values['vwap_15m'], expected)

    def test_empty_window(self):
        """Test VWAP with no trades returns None."""
        vwap = RollingVWAPWindow(window_seconds=60)
        self.assertIsNone(vwap.value())

    def test_zero_volume(self):
        """Test VWAP handles zero volume gracefully."""
        vwap = RollingVWAPWindow(window_seconds=60)
        timestamp_ms = int(time.time() * 1000)

        # This should not cause division by zero
        vwap.add_trade(timestamp_ms, Decimal('100'), Decimal('0'))
        self.assertIsNone(vwap.value())

    def test_precise_decimal_calculation(self):
        """Test VWAP maintains decimal precision."""
        vwap = RollingVWAPWindow(window_seconds=60)
        base_ts = int(time.time() * 1000)

        # Use precise decimal values
        price1 = Decimal('50000.123456')
        quantity1 = Decimal('0.123456789')
        price2 = Decimal('50001.987654')
        quantity2 = Decimal('0.987654321')

        vwap.add_trade(base_ts, price1, quantity1)
        vwap.add_trade(base_ts + 100, price2, quantity2)

        result = vwap.value()
        self.assertIsInstance(result, Decimal)

        # Calculate expected VWAP
        pv1 = price1 * quantity1
        pv2 = price2 * quantity2
        expected = (pv1 + pv2) / (quantity1 + quantity2)

        # Check precision is maintained (within rounding)
        self.assertAlmostEqual(float(result), float(expected), places=6)


if __name__ == '__main__':
    unittest.main()