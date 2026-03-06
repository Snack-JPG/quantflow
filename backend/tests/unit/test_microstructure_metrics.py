"""
Unit tests for microstructure metrics.
Validates all market microstructure calculations against known values.
"""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from app.services.microstructure import MicrostructureAnalyzer


class TestMicrostructureMetrics:
    """Test suite for microstructure metrics"""

    @pytest.fixture
    def sample_trades(self):
        """Generate sample trade data for testing"""
        base_time = datetime.now()
        trades = []

        # Generate synthetic trades with known patterns
        for i in range(100):
            trades.append({
                'timestamp': base_time + timedelta(seconds=i),
                'price': 100 + np.sin(i/10) * 2,  # Oscillating price
                'volume': np.random.uniform(0.1, 2.0),
                'side': 'buy' if i % 2 == 0 else 'sell'
            })

        return pd.DataFrame(trades)

    @pytest.fixture
    def sample_order_book(self):
        """Generate sample order book data"""
        return {
            'bids': [
                {'price': 99.8, 'quantity': 1.5},
                {'price': 99.6, 'quantity': 2.0},
                {'price': 99.4, 'quantity': 2.5}
            ],
            'asks': [
                {'price': 100.2, 'quantity': 1.2},
                {'price': 100.4, 'quantity': 2.3},
                {'price': 100.6, 'quantity': 1.8}
            ]
        }

    def test_kyle_lambda_calculation(self, sample_trades):
        """Test Kyle's Lambda (price impact) calculation"""
        analyzer = MicrostructureAnalyzer()

        # Calculate Kyle's Lambda
        lambda_value = analyzer.calculate_kyle_lambda(sample_trades)

        # Kyle's Lambda should be positive (price impact exists)
        assert lambda_value > 0

        # Test with perfect linear relationship
        synthetic_trades = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=100, freq='1min'),
            'price': np.arange(100, 200, 1),  # Linear price increase
            'volume': np.ones(100),
            'side': ['buy'] * 100  # All buys
        })

        linear_lambda = analyzer.calculate_kyle_lambda(synthetic_trades)
        assert linear_lambda > 0.5  # Strong price impact expected

    def test_roll_spread_estimator(self, sample_trades):
        """Test Roll spread estimator calculation"""
        analyzer = MicrostructureAnalyzer()

        # Calculate Roll spread
        roll_spread = analyzer.calculate_roll_spread(sample_trades['price'].values)

        # Roll spread should be non-negative
        assert roll_spread >= 0

        # Test with known bid-ask bounce pattern
        # Alternating between bid and ask prices
        prices = []
        bid, ask = 99.5, 100.5
        for i in range(100):
            prices.append(bid if i % 2 == 0 else ask)

        known_spread = analyzer.calculate_roll_spread(np.array(prices))
        # Should approximate the true spread (1.0)
        assert 0.8 < known_spread < 1.2

    def test_amihud_illiquidity(self, sample_trades):
        """Test Amihud illiquidity ratio calculation"""
        analyzer = MicrostructureAnalyzer()

        # Calculate Amihud ratio
        amihud = analyzer.calculate_amihud_ratio(sample_trades)

        # Amihud ratio should be positive
        assert amihud > 0

        # Test with high liquidity scenario (large volume, small price change)
        liquid_trades = sample_trades.copy()
        liquid_trades['volume'] *= 1000  # Increase volume
        liquid_trades['price'] = 100  # Stable price

        liquid_amihud = analyzer.calculate_amihud_ratio(liquid_trades)
        assert liquid_amihud < amihud  # More liquid = lower ratio

    def test_realized_volatility(self, sample_trades):
        """Test realized volatility calculation"""
        analyzer = MicrostructureAnalyzer()

        # Calculate realized volatility
        volatility = analyzer.calculate_realized_volatility(
            sample_trades['price'].values,
            window=20
        )

        # Volatility should be positive
        assert all(v >= 0 for v in volatility if not np.isnan(v))

        # Test with constant prices (zero volatility)
        constant_prices = np.ones(100) * 100
        const_vol = analyzer.calculate_realized_volatility(constant_prices, window=10)
        assert all(v == 0 for v in const_vol[10:])  # After initial window

    def test_order_flow_imbalance(self, sample_trades):
        """Test order flow imbalance calculation"""
        analyzer = MicrostructureAnalyzer()

        # Calculate OFI
        ofi = analyzer.calculate_order_flow_imbalance(sample_trades)

        # OFI should be between -1 and 1
        assert -1 <= ofi <= 1

        # Test with all buy orders
        all_buys = sample_trades.copy()
        all_buys['side'] = 'buy'
        buy_ofi = analyzer.calculate_order_flow_imbalance(all_buys)
        assert buy_ofi == 1.0

        # Test with balanced flow
        balanced = sample_trades.copy()
        half = len(balanced) // 2
        balanced.loc[:half, 'side'] = 'buy'
        balanced.loc[half:, 'side'] = 'sell'
        balanced_ofi = analyzer.calculate_order_flow_imbalance(balanced)
        assert abs(balanced_ofi) < 0.1

    def test_effective_spread(self, sample_order_book):
        """Test effective spread calculation"""
        analyzer = MicrostructureAnalyzer()

        # Calculate effective spread
        eff_spread = analyzer.calculate_effective_spread(
            trade_price=100.1,
            midpoint=100.0
        )

        assert eff_spread == 0.2  # 2 * |100.1 - 100.0|

    def test_price_impact(self):
        """Test price impact measurement"""
        analyzer = MicrostructureAnalyzer()

        # Test temporary impact
        temp_impact = analyzer.calculate_temporary_impact(
            pre_trade_mid=100.0,
            trade_price=100.5,
            post_trade_mid=100.2
        )

        assert temp_impact == 0.3  # (100.5 - 100.0) - (100.2 - 100.0)

        # Test permanent impact
        perm_impact = analyzer.calculate_permanent_impact(
            pre_trade_mid=100.0,
            post_trade_mid=100.2
        )

        assert perm_impact == 0.2  # 100.2 - 100.0

    def test_microstructure_noise(self, sample_trades):
        """Test microstructure noise estimation"""
        analyzer = MicrostructureAnalyzer()

        # Add noise to prices
        noisy_prices = sample_trades['price'].values + np.random.normal(0, 0.1, len(sample_trades))

        noise_estimate = analyzer.estimate_microstructure_noise(noisy_prices)

        # Noise should be positive
        assert noise_estimate > 0

        # Test with no noise (smooth prices)
        smooth_prices = np.linspace(100, 110, 100)
        smooth_noise = analyzer.estimate_microstructure_noise(smooth_prices)
        assert smooth_noise < noise_estimate

    def test_quote_asymmetry(self, sample_order_book):
        """Test quote asymmetry metrics"""
        analyzer = MicrostructureAnalyzer()

        # Calculate depth imbalance
        depth_imbalance = analyzer.calculate_depth_imbalance(sample_order_book)

        # Test calculation
        bid_depth = sum(b['quantity'] for b in sample_order_book['bids'])
        ask_depth = sum(a['quantity'] for a in sample_order_book['asks'])
        expected = (bid_depth - ask_depth) / (bid_depth + ask_depth)

        assert abs(depth_imbalance - expected) < 0.01

    def test_realized_spread(self):
        """Test realized spread calculation"""
        analyzer = MicrostructureAnalyzer()

        # Calculate realized spread
        realized = analyzer.calculate_realized_spread(
            trade_price=100.5,
            trade_side='buy',
            midpoint_before=100.0,
            midpoint_after=100.2
        )

        # For buy: 2 * (100.5 - 100.2) = 0.6
        assert realized == 0.6

    def test_information_share(self, sample_trades):
        """Test Hasbrouck information share calculation"""
        analyzer = MicrostructureAnalyzer()

        # Create multi-exchange data
        exchanges = ['binance', 'coinbase', 'kraken']
        multi_exchange_data = []

        for exchange in exchanges:
            exchange_trades = sample_trades.copy()
            exchange_trades['exchange'] = exchange
            # Add some price variation
            exchange_trades['price'] += np.random.normal(0, 0.1, len(exchange_trades))
            multi_exchange_data.append(exchange_trades)

        combined = pd.concat(multi_exchange_data)

        info_shares = analyzer.calculate_information_share(combined)

        # Sum of information shares should be 1
        assert abs(sum(info_shares.values()) - 1.0) < 0.01

        # Each share should be between 0 and 1
        for share in info_shares.values():
            assert 0 <= share <= 1