"""Unit tests for the analytics engine and metric wiring."""

from decimal import Decimal

from app.analytics.engine import AnalyticsEngine


def _book_levels():
    bids = [
        (Decimal("49999"), Decimal("4.0")),
        (Decimal("49998"), Decimal("2.0")),
        (Decimal("49997"), Decimal("1.0")),
    ]
    asks = [
        (Decimal("50001"), Decimal("3.0")),
        (Decimal("50002"), Decimal("2.5")),
        (Decimal("50003"), Decimal("1.5")),
    ]
    return bids, asks


def test_process_order_book_produces_core_book_metrics():
    engine = AnalyticsEngine()
    bids, asks = _book_levels()

    metrics = engine.process_order_book(bids=bids, asks=asks, timestamp_ms=1_700_000_000_000)

    assert "spread_absolute" in metrics
    assert "spread_relative_bps" in metrics
    assert "midpoint" in metrics
    assert "obi" in metrics
    assert -1.0 <= metrics["obi"] <= 1.0


def test_process_trade_updates_vwap_outputs():
    engine = AnalyticsEngine()
    timestamp_ms = 1_700_000_000_000

    # First trade seeds last price, second trade drives VPIN/update paths.
    engine.process_trade(timestamp_ms, Decimal("50000"), Decimal("1.0"), side="buy")
    trade_metrics = engine.process_trade(timestamp_ms + 1_000, Decimal("50010"), Decimal("2.0"), side="buy")

    assert "vwap_1m" in trade_metrics
    assert "vwap_5m" in trade_metrics
    assert "vwap_15m" in trade_metrics
    assert trade_metrics["vwap_1m"] is not None


def test_process_ohlc_bar_generates_volatility_metrics_after_warmup():
    engine = AnalyticsEngine()

    metrics = {}
    for i in range(30):
        metrics = engine.process_ohlc_bar(
            open_=100.0 + i,
            high=100.5 + i,
            low=99.5 + i,
            close=100.2 + i,
            volume=10_000.0,
            timestamp_ms=1_700_000_000_000 + (i * 60_000),
        )

    assert "garman_klass_vol" in metrics
    assert "parkinson_vol" in metrics


def test_get_all_metrics_returns_structured_snapshot():
    engine = AnalyticsEngine()
    bids, asks = _book_levels()

    engine.process_order_book(bids=bids, asks=asks, timestamp_ms=1_700_000_000_000)
    engine.process_trade(1_700_000_000_000, Decimal("50000"), Decimal("1.0"), side="buy")
    engine.process_trade(1_700_000_001_000, Decimal("50001"), Decimal("1.5"), side="sell")

    snapshot = engine.get_all_metrics()

    assert "timestamp" in snapshot
    assert "obi" in snapshot
    assert "vwap_1m" in snapshot
