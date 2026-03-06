#!/usr/bin/env python3
"""
Test script for the backtesting framework.

Demonstrates usage with synthetic data and all built-in strategies.
"""
import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
import random
import logging
import json

from models import (
    OrderBookSnapshot,
    Trade,
    Alert,
    PriceLevel,
    OrderSide,
    BacktestConfig
)
from backtesting import BacktestEngine, DataFeed
from strategies import (
    OBIMeanReversionStrategy,
    VPINToxicityStrategy,
    SpoofingAlphaStrategy,
    CrossExchangeArbStrategy
)


def generate_synthetic_data(
    symbol: str = "BTCUSDT",
    hours: int = 24,
    base_price: float = 50000
) -> DataFeed:
    """Generate synthetic market data for testing."""
    order_books = []
    trades = []
    alerts = []

    start_time = datetime.now() - timedelta(hours=hours)
    current_price = Decimal(str(base_price))

    # Generate data points every minute
    for i in range(hours * 60):
        timestamp = start_time + timedelta(minutes=i)
        timestamp_us = int(timestamp.timestamp() * 1_000_000)

        # Random walk for price
        price_change = Decimal(str(random.gauss(0, 50)))
        current_price += price_change
        current_price = max(current_price, Decimal('1000'))  # Floor price

        # Generate order book snapshot
        bids = []
        asks = []

        # Create bid levels
        for j in range(20):
            bid_price = current_price - Decimal(str((j + 1) * 10))
            bid_qty = Decimal(str(random.uniform(0.1, 2.0)))
            bids.append(PriceLevel(
                price=bid_price,
                quantity=bid_qty,
                order_count=random.randint(1, 10)
            ))

        # Create ask levels
        for j in range(20):
            ask_price = current_price + Decimal(str((j + 1) * 10))
            ask_qty = Decimal(str(random.uniform(0.1, 2.0)))
            asks.append(PriceLevel(
                price=ask_price,
                quantity=ask_qty,
                order_count=random.randint(1, 10)
            ))

        # Add order book snapshot
        order_books.append(OrderBookSnapshot(
            exchange="binance",
            symbol=symbol,
            timestamp_us=timestamp_us,
            sequence=i,
            bids=bids,
            asks=asks
        ))

        # Generate some trades
        for _ in range(random.randint(5, 20)):
            trade_price = current_price + Decimal(str(random.uniform(-5, 5)))
            trade_qty = Decimal(str(random.uniform(0.01, 0.5)))
            trade_side = random.choice([OrderSide.BUY, OrderSide.SELL])

            trades.append(Trade(
                exchange="binance",
                symbol=symbol,
                timestamp_us=timestamp_us + random.randint(0, 60000),
                price=trade_price,
                quantity=trade_qty,
                side=trade_side,
                trade_id=f"trade_{i}_{_}"
            ))

        # Occasionally generate alerts (spoofing patterns)
        if random.random() < 0.05:  # 5% chance
            alerts.append(Alert(
                id=f"alert_{i}",
                timestamp=timestamp,
                pattern="spoofing",
                severity="warning",
                confidence=random.uniform(0.6, 0.9),
                exchange="binance",
                symbol=symbol,
                context={'side': random.choice(['bid', 'ask'])},
                explanation="Large order detected and cancelled quickly"
            ))

    return DataFeed(
        order_books=order_books,
        trades=trades,
        alerts=alerts
    )


def run_backtest_example():
    """Run example backtests with all strategies."""
    logging.basicConfig(level=logging.INFO)

    print("=" * 60)
    print("QuantFlow Backtesting Framework Test")
    print("=" * 60)

    # Generate synthetic data
    print("\n1. Generating synthetic market data...")
    data = generate_synthetic_data(hours=24, base_price=50000)
    print(f"   - Generated {len(data.order_books)} order book snapshots")
    print(f"   - Generated {len(data.trades)} trades")
    print(f"   - Generated {len(data.alerts)} alerts")

    # Backtesting configuration
    config = BacktestConfig(
        initial_capital=Decimal('10000'),
        commission_bps=10,  # 0.1%
        slippage_model="proportional",
        slippage_bps=5,
        position_sizing="fixed",
        fixed_position_size=Decimal('1000'),
        max_position_pct=0.2,
        max_positions=3
    )

    # Initialize backtesting engine
    engine = BacktestEngine()

    # Test each strategy
    strategies = [
        ("OBI Mean Reversion", OBIMeanReversionStrategy(
            symbols=['BTCUSDT'],
            config={'obi_threshold': 0.6, 'lookback_periods': 20}
        )),
        ("VPIN Toxicity", VPINToxicityStrategy(
            symbols=['BTCUSDT'],
            config={'volume_bucket_size': 50, 'vpin_threshold': 0.6}
        )),
        ("Spoofing Alpha", SpoofingAlphaStrategy(
            symbols=['BTCUSDT'],
            config={'confidence_threshold': 0.7, 'min_events_for_signal': 2}
        )),
        ("Cross-Exchange Arbitrage", CrossExchangeArbStrategy(
            symbols=['BTCUSDT'],
            config={'min_spread_bps': 20, 'fee_bps': 10}
        ))
    ]

    results = []

    print("\n2. Running backtests for each strategy...")
    print("-" * 60)

    for name, strategy in strategies:
        print(f"\nTesting: {name}")
        print("-" * 30)

        try:
            # Run backtest
            result = engine.run(strategy, data, config)
            results.append((name, result))

            # Print key metrics
            metrics = result.metrics
            print(f"  Total Return: {metrics.total_return:.2f}%")
            print(f"  Sharpe Ratio: {metrics.sharpe_ratio:.2f}")
            print(f"  Max Drawdown: {metrics.max_drawdown:.2f}%")
            print(f"  Win Rate: {metrics.win_rate:.2f}%")
            print(f"  Total Trades: {metrics.total_trades}")
            print(f"  Profit Factor: {metrics.profit_factor:.2f}")

            # Print sample trades
            if result.trades:
                print(f"\n  Sample Trades (first 3):")
                for trade in result.trades[:3]:
                    print(f"    - {trade.side.value} {trade.quantity:.4f} @ {trade.price:.2f}")

        except Exception as e:
            print(f"  ERROR: {e}")
            import traceback
            traceback.print_exc()

    # Summary comparison
    print("\n" + "=" * 60)
    print("STRATEGY COMPARISON")
    print("=" * 60)
    print(f"{'Strategy':<25} {'Return %':<12} {'Sharpe':<10} {'Max DD %':<12} {'Trades':<10}")
    print("-" * 60)

    for name, result in results:
        metrics = result.metrics
        print(f"{name:<25} {metrics.total_return:<12.2f} {metrics.sharpe_ratio:<10.2f} "
              f"{metrics.max_drawdown:<12.2f} {metrics.total_trades:<10}")

    # Save results to file
    print("\n3. Saving results to backtest_results.json...")
    output = {
        'test_date': datetime.now().isoformat(),
        'config': {
            'initial_capital': str(config.initial_capital),
            'commission_bps': config.commission_bps,
            'slippage_model': config.slippage_model
        },
        'results': {}
    }

    for name, result in results:
        output['results'][name] = result.metrics.to_dict()

    with open('backtest_results.json', 'w') as f:
        json.dump(output, f, indent=2, default=str)

    print("\nBacktest complete! Results saved to backtest_results.json")
    print("=" * 60)


async def test_data_loader():
    """Test the Binance data loader (requires internet connection)."""
    from data_loader import BinanceDataLoader

    print("\n" + "=" * 60)
    print("Testing Binance Data Loader")
    print("=" * 60)

    loader = BinanceDataLoader(data_dir="./test_data")

    # Test downloading one day of data
    symbol = "BTCUSDT"
    test_date = datetime(2024, 1, 1)  # Historical date

    print(f"\nDownloading data for {symbol} on {test_date.date()}...")

    try:
        # Download klines
        klines = await loader.download_klines(symbol, "1h", test_date)
        if klines:
            print(f"  - Downloaded {len(klines)} hourly klines")
            print(f"  - Sample: Open={klines[0]['open']}, Close={klines[0]['close']}")
        else:
            print("  - No kline data available (might be too recent)")

        # Download trades (this might be large)
        print("\n  Note: Trade data download skipped (very large files)")
        # trades = await loader.download_trades(symbol, test_date)

    except Exception as e:
        print(f"  ERROR downloading data: {e}")
        print("  This is normal if you're offline or if Binance data is unavailable")


if __name__ == "__main__":
    # Run the backtest example
    run_backtest_example()

    # Optionally test data loader (requires internet)
    print("\n" + "=" * 60)
    response = input("Test Binance data loader? (requires internet) [y/N]: ")
    if response.lower() == 'y':
        asyncio.run(test_data_loader())

    print("\nAll tests complete!")