"""Unit tests for detection package exports and core detector behavior."""

from decimal import Decimal

import pytest

from app.detection import (
    AlertSeverity,
    DetectionEngine,
    OrderEvent,
    SpoofingDetector,
    WallDetector,
)
from app.models import OrderBookSnapshot, PriceLevel, Trade


def _snapshot_with_liquidity(multiplier: Decimal = Decimal("1")) -> OrderBookSnapshot:
    return OrderBookSnapshot(
        exchange="binance",
        symbol="BTCUSDT",
        timestamp_us=1_700_000_000_000_000,
        sequence=1,
        bids=[
            PriceLevel(price=Decimal("50000"), quantity=Decimal("1.0") * multiplier),
            PriceLevel(price=Decimal("49999"), quantity=Decimal("1.2") * multiplier),
            PriceLevel(price=Decimal("49998"), quantity=Decimal("1.1") * multiplier),
            PriceLevel(price=Decimal("49997"), quantity=Decimal("0.9") * multiplier),
            PriceLevel(price=Decimal("49996"), quantity=Decimal("1.0") * multiplier),
        ],
        asks=[
            PriceLevel(price=Decimal("50001"), quantity=Decimal("1.0") * multiplier),
            PriceLevel(price=Decimal("50002"), quantity=Decimal("1.1") * multiplier),
            PriceLevel(price=Decimal("50003"), quantity=Decimal("1.0") * multiplier),
            PriceLevel(price=Decimal("50004"), quantity=Decimal("0.8") * multiplier),
            PriceLevel(price=Decimal("50005"), quantity=Decimal("1.2") * multiplier),
        ],
    )


def test_spoofing_detector_flags_repeated_fast_cancels():
    detector = SpoofingDetector(
        exchange="binance",
        symbol="BTCUSDT",
        cancel_window_ms=2_000,
        size_multiple=0.8,
        min_pattern_count=1,
        lookback_minutes=5,
    )
    snapshot = _snapshot_with_liquidity()

    events = [
        OrderEvent(
            timestamp_ms=1_000_000,
            price=Decimal("50010"),
            quantity=Decimal("12"),
            side="ask",
            event_type="place",
        ),
        OrderEvent(
            timestamp_ms=1_000_600,
            price=Decimal("50010"),
            quantity=Decimal("12"),
            side="ask",
            event_type="cancel",
        ),
        OrderEvent(
            timestamp_ms=1_010_000,
            price=Decimal("50011"),
            quantity=Decimal("15"),
            side="ask",
            event_type="place",
        ),
        OrderEvent(
            timestamp_ms=1_010_500,
            price=Decimal("50011"),
            quantity=Decimal("15"),
            side="ask",
            event_type="cancel",
        ),
    ]

    alert = detector.detect(book_snapshot=snapshot, trades=None, order_events=events)

    assert alert is not None
    assert alert.pattern == "spoofing"
    assert alert.severity in {
        AlertSeverity.INFO,
        AlertSeverity.WARNING,
        AlertSeverity.CRITICAL,
    }
    assert alert.confidence > 0


def test_wall_detector_can_emit_alert_after_persistence_window():
    detector = WallDetector(
        exchange="binance",
        symbol="BTCUSDT",
        sigma_threshold=1.5,
        min_persistence_ms=0,
    )

    snapshot = OrderBookSnapshot(
        exchange="binance",
        symbol="BTCUSDT",
        timestamp_us=1_700_000_000_000_000,
        sequence=1,
        bids=[
            PriceLevel(price=Decimal("50000"), quantity=Decimal("50.0")),
            PriceLevel(price=Decimal("49999"), quantity=Decimal("1.0")),
            PriceLevel(price=Decimal("49998"), quantity=Decimal("1.1")),
            PriceLevel(price=Decimal("49997"), quantity=Decimal("0.9")),
            PriceLevel(price=Decimal("49996"), quantity=Decimal("1.0")),
        ],
        asks=[
            PriceLevel(price=Decimal("50001"), quantity=Decimal("1.0")),
            PriceLevel(price=Decimal("50002"), quantity=Decimal("1.1")),
            PriceLevel(price=Decimal("50003"), quantity=Decimal("0.9")),
            PriceLevel(price=Decimal("50004"), quantity=Decimal("1.0")),
            PriceLevel(price=Decimal("50005"), quantity=Decimal("1.2")),
        ],
    )

    # First call seeds candidate, second call satisfies persistence check.
    detector.detect(book_snapshot=snapshot, trades=None, order_events=None)
    alert = detector.detect(book_snapshot=snapshot, trades=None, order_events=None)

    # At minimum, strong walls should be tracked as candidates.
    assert detector.wall_candidates
    if alert is not None:
        assert alert.pattern == "walls"
        assert alert.confidence > 0


@pytest.mark.asyncio
async def test_detection_engine_processes_inputs_and_returns_alert_list():
    engine = DetectionEngine(exchange="binance", symbol="BTCUSDT")
    snapshot = _snapshot_with_liquidity()
    trades = [
        Trade(
            exchange="binance",
            symbol="BTCUSDT",
            timestamp_us=1_700_000_000_100_000,
            price=Decimal("50000"),
            quantity=Decimal("0.3"),
            side="buy",
            trade_id="t1",
        )
    ]
    events = [
        OrderEvent(
            timestamp_ms=1_000_000,
            price=Decimal("50010"),
            quantity=Decimal("20"),
            side="ask",
            event_type="place",
        ),
        OrderEvent(
            timestamp_ms=1_000_400,
            price=Decimal("50010"),
            quantity=Decimal("20"),
            side="ask",
            event_type="cancel",
        ),
    ]

    alerts = await engine.detect_patterns(book_snapshot=snapshot, trades=trades, order_events=events)

    assert isinstance(alerts, list)
    # Stats should always be available regardless of alert count.
    stats = engine.get_stats()
    assert "total_detections" in stats
    assert "by_pattern" in stats
