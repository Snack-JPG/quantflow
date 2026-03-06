"""Unit tests for the async order book engine."""

from decimal import Decimal

import pytest

from app.core.order_book import OrderBook
from app.models import OrderBookDelta, OrderBookSnapshot, PriceLevel


def _snapshot(sequence: int = 1) -> OrderBookSnapshot:
    return OrderBookSnapshot(
        exchange="binance",
        symbol="BTCUSDT",
        timestamp_us=1_700_000_000_000_000 + sequence,
        sequence=sequence,
        bids=[
            PriceLevel(price=Decimal("50000"), quantity=Decimal("2.0")),
            PriceLevel(price=Decimal("49999"), quantity=Decimal("1.0")),
        ],
        asks=[
            PriceLevel(price=Decimal("50001"), quantity=Decimal("1.5")),
            PriceLevel(price=Decimal("50002"), quantity=Decimal("1.2")),
        ],
    )


@pytest.mark.asyncio
async def test_apply_snapshot_sets_best_bid_and_ask():
    book = OrderBook(exchange="binance", symbol="BTCUSDT")
    await book.apply_snapshot(_snapshot())

    assert book.get_best_bid() == (Decimal("50000"), Decimal("2.0"))
    assert book.get_best_ask() == (Decimal("50001"), Decimal("1.5"))
    assert book.get_spread() == Decimal("1")
    assert book.get_mid_price() == Decimal("50000.5")


@pytest.mark.asyncio
async def test_apply_delta_updates_and_removes_levels():
    book = OrderBook(exchange="binance", symbol="BTCUSDT")
    await book.apply_snapshot(_snapshot(sequence=10))

    delta = OrderBookDelta(
        exchange="binance",
        symbol="BTCUSDT",
        timestamp_us=1_700_000_000_010_000,
        sequence=11,
        bids=[
            PriceLevel(price=Decimal("50000"), quantity=Decimal("3.0")),  # update
            PriceLevel(price=Decimal("49999"), quantity=Decimal("0")),  # remove
        ],
        asks=[
            PriceLevel(price=Decimal("50001"), quantity=Decimal("0")),  # remove best ask
            PriceLevel(price=Decimal("50003"), quantity=Decimal("2.2")),  # add
        ],
        first_update_id=11,
        final_update_id=11,
    )

    await book.apply_delta(delta)

    assert book.get_best_bid() == (Decimal("50000"), Decimal("3.0"))
    assert book.get_best_ask() == (Decimal("50002"), Decimal("1.2"))
    assert Decimal("49999") not in book.bids
    assert Decimal("50001") not in book.asks
    assert Decimal("50003") in book.asks


@pytest.mark.asyncio
async def test_get_snapshot_returns_sorted_depth():
    book = OrderBook(exchange="binance", symbol="BTCUSDT")
    await book.apply_snapshot(_snapshot())

    snap = await book.get_snapshot(depth=1)
    assert len(snap.bids) == 1
    assert len(snap.asks) == 1
    assert snap.bids[0].price == Decimal("50000")
    assert snap.asks[0].price == Decimal("50001")


@pytest.mark.asyncio
async def test_depth_and_imbalance_metrics():
    book = OrderBook(exchange="binance", symbol="BTCUSDT")
    await book.apply_snapshot(_snapshot())

    bid_depth, ask_depth = book.get_depth_at_bps(10)
    assert bid_depth > 0
    assert ask_depth > 0

    imbalance = book.get_imbalance(levels=2)
    assert -1.0 <= imbalance <= 1.0


@pytest.mark.asyncio
async def test_vwap_buy_and_sell_paths():
    book = OrderBook(exchange="binance", symbol="BTCUSDT")
    await book.apply_snapshot(_snapshot())

    buy_vwap = book.get_vwap(side="buy", quantity=Decimal("2.0"))
    sell_vwap = book.get_vwap(side="sell", quantity=Decimal("2.0"))

    assert buy_vwap is not None
    assert sell_vwap is not None
    assert buy_vwap > sell_vwap
