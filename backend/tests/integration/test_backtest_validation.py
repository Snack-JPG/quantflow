"""Integration tests for the strategy backtesting engine."""

from datetime import datetime
from decimal import Decimal

from app.strategy.backtesting import BacktestEngine, DataFeed
from app.strategy.base import Strategy
from app.strategy.models import (
    Alert,
    BacktestConfig,
    OrderBookSnapshot,
    PriceLevel,
    Signal,
    SignalDirection,
    Trade,
    OrderSide,
)


class BuyThenCloseStrategy(Strategy):
    """Minimal deterministic strategy used for integration validation."""

    def __init__(self):
        super().__init__(name="buy_then_close", symbols=["BTCUSDT"], config={})
        self.step = 0
        self.entered = False
        self.closed = False

    def on_book_update(self, book: OrderBookSnapshot) -> list[Signal]:
        self.step += 1
        if not self.entered:
            self.entered = True
            return [self.generate_signal(book.symbol, SignalDirection.LONG, 1.0, "initial entry")]

        if self.entered and not self.closed and self.has_position(book.symbol) and self.step >= 3:
            self.closed = True
            return [self.generate_signal(book.symbol, SignalDirection.CLOSE, 1.0, "scheduled exit")]

        return []

    def on_trade(self, trade: Trade) -> list[Signal]:
        return []

    def on_alert(self, alert: Alert) -> list[Signal]:
        return []


def _book(ts_us: int, bid: str, ask: str, seq: int) -> OrderBookSnapshot:
    return OrderBookSnapshot(
        exchange="binance",
        symbol="BTCUSDT",
        timestamp_us=ts_us,
        sequence=seq,
        bids=[PriceLevel(price=Decimal(bid), quantity=Decimal("5"))],
        asks=[PriceLevel(price=Decimal(ask), quantity=Decimal("5"))],
    )


def _trade(ts_us: int, price: str, qty: str, side: OrderSide, trade_id: str) -> Trade:
    return Trade(
        exchange="binance",
        symbol="BTCUSDT",
        timestamp_us=ts_us,
        price=Decimal(price),
        quantity=Decimal(qty),
        side=side,
        trade_id=trade_id,
    )


def _data_feed() -> DataFeed:
    return DataFeed(
        order_books=[
            _book(1_700_000_000_000_000, "50000", "50001", 1),
            _book(1_700_000_000_100_000, "50005", "50006", 2),
            _book(1_700_000_000_200_000, "50010", "50011", 3),
            _book(1_700_000_000_300_000, "50012", "50013", 4),
        ],
        trades=[
            _trade(1_700_000_000_050_000, "50000", "0.2", OrderSide.BUY, "t1"),
            _trade(1_700_000_000_150_000, "50006", "0.1", OrderSide.SELL, "t2"),
        ],
        alerts=[],
    )


def test_backtest_engine_executes_strategy_and_returns_metrics():
    engine = BacktestEngine()
    strategy = BuyThenCloseStrategy()
    config = BacktestConfig(initial_capital=Decimal("10000"))

    result = engine.run(strategy=strategy, data=_data_feed(), config=config)

    assert result.strategy_name == "buy_then_close"
    assert result.start_date <= result.end_date
    assert len(result.trades) >= 1
    assert len(result.positions) >= 1
    assert result.metrics.total_trades >= 1
    assert isinstance(result.metrics.total_pnl, Decimal)
    assert isinstance(result.start_date, datetime)


def test_backtest_is_deterministic_for_same_input():
    engine = BacktestEngine()
    config = BacktestConfig(initial_capital=Decimal("10000"))

    result_one = engine.run(strategy=BuyThenCloseStrategy(), data=_data_feed(), config=config)
    result_two = engine.run(strategy=BuyThenCloseStrategy(), data=_data_feed(), config=config)

    assert result_one.metrics.total_return == result_two.metrics.total_return
    assert result_one.metrics.total_trades == result_two.metrics.total_trades
