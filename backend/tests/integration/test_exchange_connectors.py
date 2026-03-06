"""Integration-style tests for exchange connector message parsing."""

from decimal import Decimal

import pytest

from app.connectors.binance import BinanceConnector
from app.connectors.coinbase import CoinbaseConnector
from app.connectors.kraken import KrakenConnector


@pytest.mark.asyncio
async def test_binance_connector_parses_depth_and_trade_messages():
    snapshots = []
    trades = []

    async def on_snapshot(snapshot):
        snapshots.append(snapshot)

    async def on_trade(trade):
        trades.append(trade)

    connector = BinanceConnector(
        symbols=["BTCUSDT"],
        on_book_snapshot=on_snapshot,
        on_trade=on_trade,
    )

    await connector._handle_message(
        {
            "stream": "btcusdt@depth20@100ms",
            "data": {
                "lastUpdateId": 42,
                "bids": [["50000.00", "1.5"], ["49999.00", "2.0"]],
                "asks": [["50001.00", "1.2"], ["50002.00", "2.5"]],
            },
        }
    )
    await connector._handle_message(
        {
            "stream": "btcusdt@trade",
            "data": {
                "T": 1_700_000_000_000,
                "p": "50000.50",
                "q": "0.50",
                "m": False,
                "t": 123456,
            },
        }
    )

    assert len(snapshots) == 1
    assert snapshots[0].symbol == "BTCUSDT"
    assert snapshots[0].bids[0].price == Decimal("50000.00")
    assert len(trades) == 1
    assert trades[0].side == "buy"
    assert trades[0].price == Decimal("50000.50")


@pytest.mark.asyncio
async def test_coinbase_connector_parses_snapshot_update_and_trade():
    snapshots = []
    trades = []

    async def on_snapshot(snapshot):
        snapshots.append(snapshot)

    async def on_trade(trade):
        trades.append(trade)

    connector = CoinbaseConnector(
        symbols=["BTCUSDT"],
        on_book_snapshot=on_snapshot,
        on_trade=on_trade,
    )

    await connector._handle_message(
        {
            "type": "snapshot",
            "product_id": "BTC-USD",
            "bids": [["50000.00", "1.5"]],
            "asks": [["50001.00", "1.2"]],
        }
    )
    await connector._handle_message(
        {
            "type": "l2update",
            "product_id": "BTC-USD",
            "changes": [["buy", "49999.00", "1.0"], ["sell", "50002.00", "0.9"]],
        }
    )
    await connector._handle_message(
        {
            "type": "match",
            "product_id": "BTC-USD",
            "time": "2024-01-01T00:00:01.000Z",
            "price": "50000.75",
            "size": "0.25",
            "side": "sell",
            "trade_id": "77",
        }
    )

    assert len(snapshots) >= 2  # snapshot + update output
    assert snapshots[-1].symbol == "BTCUSDT"
    assert len(trades) == 1
    assert trades[0].price == Decimal("50000.75")
    assert trades[0].side == "sell"


@pytest.mark.asyncio
async def test_kraken_connector_parses_book_and_trade_messages():
    snapshots = []
    trades = []

    async def on_snapshot(snapshot):
        snapshots.append(snapshot)

    async def on_trade(trade):
        trades.append(trade)

    connector = KrakenConnector(
        symbols=["BTCUSDT"],
        on_book_snapshot=on_snapshot,
        on_trade=on_trade,
    )

    await connector._handle_message(
        [
            10,
            {
                "as": [["50001.00", "1.2", "1700000000.123"]],
                "bs": [["50000.00", "1.5", "1700000000.123"]],
            },
            "book-25",
            "XBT/USD",
        ]
    )
    await connector._handle_message(
        [
            11,
            [["50000.50", "0.5", "1700000001.123", "s", "m"]],
            "trade",
            "XBT/USD",
        ]
    )

    assert len(snapshots) == 1
    assert snapshots[0].symbol == "BTCUSDT"
    assert len(trades) == 1
    assert trades[0].symbol == "BTCUSDT"
    assert trades[0].side == "sell"
