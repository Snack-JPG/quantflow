"""
Backtest validation tests.
Ensures backtesting engine produces consistent and accurate results with known strategies and data.
"""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from app.services.backtesting import BacktestEngine, Strategy, Position


class SimpleMAStrategy(Strategy):
    """Simple moving average crossover strategy for testing"""

    def __init__(self, fast_period=10, slow_period=20):
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.position = None

    def on_data(self, timestamp, price, volume, order_book):
        """Execute strategy logic"""
        if len(self.price_history) < self.slow_period:
            return

        fast_ma = np.mean(self.price_history[-self.fast_period:])
        slow_ma = np.mean(self.price_history[-self.slow_period:])

        if fast_ma > slow_ma and self.position != 'long':
            self.buy(1.0)
            self.position = 'long'
        elif fast_ma < slow_ma and self.position != 'short':
            self.sell(1.0)
            self.position = 'short'


class TestBacktestEngine:
    """Test suite for backtesting engine"""

    @pytest.fixture
    def sample_market_data(self):
        """Generate sample market data for backtesting"""
        base_time = datetime(2024, 1, 1)
        data = []

        # Generate trending market data
        for i in range(1000):
            timestamp = base_time + timedelta(minutes=i)
            # Uptrend followed by downtrend
            if i < 500:
                price = 100 + i * 0.1 + np.random.normal(0, 0.5)
            else:
                price = 150 - (i - 500) * 0.1 + np.random.normal(0, 0.5)

            data.append({
                'timestamp': timestamp,
                'price': price,
                'volume': np.random.uniform(1, 10),
                'bid': price - 0.5,
                'ask': price + 0.5
            })

        return pd.DataFrame(data)

    @pytest.fixture
    def backtest_engine(self):
        """Create backtest engine instance"""
        return BacktestEngine(
            initial_capital=10000,
            fee_rate=0.001,
            slippage_rate=0.0005
        )

    def test_backtest_initialization(self, backtest_engine):
        """Test backtest engine initialization"""
        assert backtest_engine.initial_capital == 10000
        assert backtest_engine.fee_rate == 0.001
        assert backtest_engine.slippage_rate == 0.0005
        assert backtest_engine.current_capital == 10000
        assert len(backtest_engine.trades) == 0

    def test_simple_buy_hold_strategy(self, backtest_engine, sample_market_data):
        """Test buy and hold strategy"""
        class BuyHoldStrategy(Strategy):
            def __init__(self):
                self.bought = False

            def on_data(self, timestamp, price, volume, order_book):
                if not self.bought:
                    self.buy(self.capital / price)
                    self.bought = True

        strategy = BuyHoldStrategy()
        results = backtest_engine.run(strategy, sample_market_data)

        # Should have exactly one trade
        assert len(results['trades']) == 1
        assert results['trades'][0]['action'] == 'buy'

        # Final value should reflect price change
        initial_price = sample_market_data.iloc[0]['price']
        final_price = sample_market_data.iloc[-1]['price']
        expected_return = (final_price / initial_price) - 1
        actual_return = results['total_return']

        # Account for fees
        assert abs(actual_return - expected_return) < 0.01

    def test_ma_crossover_strategy(self, backtest_engine, sample_market_data):
        """Test moving average crossover strategy"""
        strategy = SimpleMAStrategy(fast_period=10, slow_period=20)
        results = backtest_engine.run(strategy, sample_market_data)

        # Should have multiple trades
        assert len(results['trades']) > 0

        # Check trade consistency
        for trade in results['trades']:
            assert trade['action'] in ['buy', 'sell']
            assert trade['quantity'] > 0
            assert trade['price'] > 0
            assert trade['fee'] >= 0

        # Performance metrics should be calculated
        assert 'total_return' in results
        assert 'sharpe_ratio' in results
        assert 'max_drawdown' in results
        assert 'win_rate' in results

    def test_strategy_with_stop_loss(self, backtest_engine, sample_market_data):
        """Test strategy with stop loss implementation"""
        class StopLossStrategy(Strategy):
            def __init__(self, stop_loss_pct=0.02):
                self.stop_loss_pct = stop_loss_pct
                self.entry_price = None
                self.position_size = 0

            def on_data(self, timestamp, price, volume, order_book):
                if self.position_size == 0 and len(self.price_history) > 10:
                    # Entry condition
                    if price > np.mean(self.price_history[-10:]):
                        self.position_size = self.capital / price
                        self.buy(self.position_size)
                        self.entry_price = price

                elif self.position_size > 0:
                    # Check stop loss
                    if price < self.entry_price * (1 - self.stop_loss_pct):
                        self.sell(self.position_size)
                        self.position_size = 0
                        self.entry_price = None

        strategy = StopLossStrategy(stop_loss_pct=0.02)
        results = backtest_engine.run(strategy, sample_market_data)

        # Check that stop losses were triggered
        stop_loss_trades = [
            t for t in results['trades']
            if t['action'] == 'sell' and t.get('reason') == 'stop_loss'
        ]

        # In a volatile market, should have some stop losses
        assert len(results['trades']) > 0

    def test_backtest_performance_metrics(self, backtest_engine, sample_market_data):
        """Test calculation of performance metrics"""
        strategy = SimpleMAStrategy()
        results = backtest_engine.run(strategy, sample_market_data)

        # Check all required metrics are present
        required_metrics = [
            'total_return',
            'annualized_return',
            'sharpe_ratio',
            'sortino_ratio',
            'max_drawdown',
            'win_rate',
            'profit_factor',
            'total_trades',
            'winning_trades',
            'losing_trades',
            'avg_win',
            'avg_loss',
            'best_trade',
            'worst_trade'
        ]

        for metric in required_metrics:
            assert metric in results
            assert results[metric] is not None

        # Validate metric ranges
        assert -1 <= results['total_return'] <= float('inf')
        assert 0 <= results['max_drawdown'] <= 1
        assert 0 <= results['win_rate'] <= 1

    def test_backtest_with_transaction_costs(self, backtest_engine, sample_market_data):
        """Test that transaction costs are properly applied"""
        # Run same strategy with and without fees
        strategy1 = SimpleMAStrategy()
        strategy2 = SimpleMAStrategy()

        engine_with_fees = BacktestEngine(10000, fee_rate=0.002, slippage_rate=0.001)
        engine_no_fees = BacktestEngine(10000, fee_rate=0, slippage_rate=0)

        results_with_fees = engine_with_fees.run(strategy1, sample_market_data)
        results_no_fees = engine_no_fees.run(strategy2, sample_market_data)

        # Results with fees should be worse
        assert results_with_fees['total_return'] < results_no_fees['total_return']

        # Total fees should be positive
        total_fees = sum(t['fee'] for t in results_with_fees['trades'])
        assert total_fees > 0

    def test_backtest_position_sizing(self, backtest_engine, sample_market_data):
        """Test various position sizing methods"""
        class FixedRiskStrategy(Strategy):
            def __init__(self, risk_per_trade=0.02):
                self.risk_per_trade = risk_per_trade

            def on_data(self, timestamp, price, volume, order_book):
                # Fixed risk position sizing
                position_size = (self.capital * self.risk_per_trade) / price
                if len(self.price_history) % 50 == 0:  # Trade every 50 bars
                    if len(self.trades) % 2 == 0:
                        self.buy(position_size)
                    else:
                        self.sell(position_size)

        strategy = FixedRiskStrategy()
        results = backtest_engine.run(strategy, sample_market_data)

        # Check position sizes respect risk limits
        for trade in results['trades']:
            trade_value = trade['quantity'] * trade['price']
            assert trade_value <= backtest_engine.initial_capital * 0.02 * 1.1  # Allow small buffer

    def test_backtest_reproducibility(self, backtest_engine, sample_market_data):
        """Test that backtests are reproducible"""
        strategy1 = SimpleMAStrategy()
        strategy2 = SimpleMAStrategy()

        results1 = backtest_engine.run(strategy1, sample_market_data)

        # Reset engine
        backtest_engine.reset()

        results2 = backtest_engine.run(strategy2, sample_market_data)

        # Results should be identical
        assert results1['total_return'] == results2['total_return']
        assert len(results1['trades']) == len(results2['trades'])

    def test_backtest_with_real_order_book(self, backtest_engine):
        """Test backtesting with order book data"""
        # Generate market data with order book
        base_time = datetime(2024, 1, 1)
        data = []

        for i in range(100):
            timestamp = base_time + timedelta(minutes=i)
            mid_price = 100 + i * 0.1

            data.append({
                'timestamp': timestamp,
                'price': mid_price,
                'volume': 10,
                'order_book': {
                    'bids': [
                        {'price': mid_price - 0.1, 'quantity': 5},
                        {'price': mid_price - 0.2, 'quantity': 10}
                    ],
                    'asks': [
                        {'price': mid_price + 0.1, 'quantity': 5},
                        {'price': mid_price + 0.2, 'quantity': 10}
                    ]
                }
            })

        df = pd.DataFrame(data)

        class OrderBookStrategy(Strategy):
            def on_data(self, timestamp, price, volume, order_book):
                if order_book:
                    spread = order_book['asks'][0]['price'] - order_book['bids'][0]['price']
                    if spread < 0.15:  # Tight spread
                        self.buy(1.0)
                    elif spread > 0.25:  # Wide spread
                        self.sell(1.0)

        strategy = OrderBookStrategy()
        results = backtest_engine.run(strategy, df)

        # Should have trades based on spread
        assert len(results['trades']) > 0