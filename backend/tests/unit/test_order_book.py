"""
Unit tests for order book operations.
Tests all critical order book functionality including updates, snapshots, and integrity.
"""

import pytest
import numpy as np
from datetime import datetime
from app.models.order_book import OrderBook, OrderBookLevel


class TestOrderBook:
    """Test suite for OrderBook class"""

    @pytest.fixture
    def empty_book(self):
        """Create an empty order book"""
        return OrderBook(symbol="BTCUSDT", exchange="binance")

    @pytest.fixture
    def populated_book(self):
        """Create a populated order book with test data"""
        book = OrderBook(symbol="BTCUSDT", exchange="binance")

        # Add bids
        book.update_bid(100.0, 1.5)
        book.update_bid(99.5, 2.0)
        book.update_bid(99.0, 1.0)

        # Add asks
        book.update_ask(100.5, 1.2)
        book.update_ask(101.0, 2.5)
        book.update_ask(101.5, 0.8)

        return book

    def test_order_book_initialization(self, empty_book):
        """Test order book initialization"""
        assert empty_book.symbol == "BTCUSDT"
        assert empty_book.exchange == "binance"
        assert len(empty_book.bids) == 0
        assert len(empty_book.asks) == 0
        assert empty_book.last_update is None

    def test_bid_insertion(self, empty_book):
        """Test inserting bids into order book"""
        empty_book.update_bid(100.0, 1.5)
        empty_book.update_bid(99.5, 2.0)

        assert len(empty_book.bids) == 2
        assert empty_book.bids[0].price == 100.0  # Highest bid first
        assert empty_book.bids[0].quantity == 1.5
        assert empty_book.bids[1].price == 99.5
        assert empty_book.bids[1].quantity == 2.0

    def test_ask_insertion(self, empty_book):
        """Test inserting asks into order book"""
        empty_book.update_ask(100.5, 1.2)
        empty_book.update_ask(101.0, 2.5)

        assert len(empty_book.asks) == 2
        assert empty_book.asks[0].price == 100.5  # Lowest ask first
        assert empty_book.asks[0].quantity == 1.2
        assert empty_book.asks[1].price == 101.0
        assert empty_book.asks[1].quantity == 2.5

    def test_bid_update(self, populated_book):
        """Test updating existing bid levels"""
        populated_book.update_bid(99.5, 3.0)  # Update existing level

        bid = next((b for b in populated_book.bids if b.price == 99.5), None)
        assert bid is not None
        assert bid.quantity == 3.0

    def test_ask_update(self, populated_book):
        """Test updating existing ask levels"""
        populated_book.update_ask(101.0, 5.0)  # Update existing level

        ask = next((a for a in populated_book.asks if a.price == 101.0), None)
        assert ask is not None
        assert ask.quantity == 5.0

    def test_bid_removal(self, populated_book):
        """Test removing bid levels (quantity = 0)"""
        initial_count = len(populated_book.bids)
        populated_book.update_bid(99.5, 0)  # Remove level

        assert len(populated_book.bids) == initial_count - 1
        assert not any(b.price == 99.5 for b in populated_book.bids)

    def test_ask_removal(self, populated_book):
        """Test removing ask levels (quantity = 0)"""
        initial_count = len(populated_book.asks)
        populated_book.update_ask(101.0, 0)  # Remove level

        assert len(populated_book.asks) == initial_count - 1
        assert not any(a.price == 101.0 for a in populated_book.asks)

    def test_best_bid_ask(self, populated_book):
        """Test getting best bid and ask"""
        best_bid = populated_book.get_best_bid()
        best_ask = populated_book.get_best_ask()

        assert best_bid is not None
        assert best_bid.price == 100.0
        assert best_bid.quantity == 1.5

        assert best_ask is not None
        assert best_ask.price == 100.5
        assert best_ask.quantity == 1.2

    def test_spread_calculation(self, populated_book):
        """Test bid-ask spread calculation"""
        spread = populated_book.get_spread()

        assert spread == 0.5  # 100.5 - 100.0

    def test_midpoint_calculation(self, populated_book):
        """Test midpoint price calculation"""
        midpoint = populated_book.get_midpoint()

        assert midpoint == 100.25  # (100.0 + 100.5) / 2

    def test_depth_calculation(self, populated_book):
        """Test order book depth calculation"""
        bid_depth = populated_book.get_bid_depth(levels=2)
        ask_depth = populated_book.get_ask_depth(levels=2)

        assert bid_depth == 3.5  # 1.5 + 2.0
        assert ask_depth == 3.7  # 1.2 + 2.5

    def test_vwap_calculation(self, populated_book):
        """Test volume-weighted average price calculation"""
        bid_vwap = populated_book.get_bid_vwap(levels=3)
        ask_vwap = populated_book.get_ask_vwap(levels=3)

        # VWAP = sum(price * quantity) / sum(quantity)
        expected_bid_vwap = (100.0*1.5 + 99.5*2.0 + 99.0*1.0) / (1.5 + 2.0 + 1.0)
        expected_ask_vwap = (100.5*1.2 + 101.0*2.5 + 101.5*0.8) / (1.2 + 2.5 + 0.8)

        assert abs(bid_vwap - expected_bid_vwap) < 0.01
        assert abs(ask_vwap - expected_ask_vwap) < 0.01

    def test_order_book_snapshot(self, populated_book):
        """Test taking order book snapshot"""
        snapshot = populated_book.get_snapshot(levels=2)

        assert len(snapshot['bids']) == 2
        assert len(snapshot['asks']) == 2
        assert snapshot['symbol'] == "BTCUSDT"
        assert snapshot['exchange'] == "binance"
        assert 'timestamp' in snapshot

    def test_order_book_clear(self, populated_book):
        """Test clearing order book"""
        populated_book.clear()

        assert len(populated_book.bids) == 0
        assert len(populated_book.asks) == 0

    def test_order_book_integrity(self, populated_book):
        """Test order book maintains price ordering integrity"""
        # Bids should be sorted descending
        bid_prices = [b.price for b in populated_book.bids]
        assert bid_prices == sorted(bid_prices, reverse=True)

        # Asks should be sorted ascending
        ask_prices = [a.price for a in populated_book.asks]
        assert ask_prices == sorted(ask_prices)

        # Best bid should be less than best ask
        assert populated_book.get_best_bid().price < populated_book.get_best_ask().price

    def test_large_order_book(self, empty_book):
        """Test order book with many levels"""
        # Add 100 bid and ask levels
        for i in range(100):
            empty_book.update_bid(100.0 - i*0.1, np.random.uniform(0.1, 10.0))
            empty_book.update_ask(100.5 + i*0.1, np.random.uniform(0.1, 10.0))

        assert len(empty_book.bids) == 100
        assert len(empty_book.asks) == 100

        # Check ordering is maintained
        bid_prices = [b.price for b in empty_book.bids]
        ask_prices = [a.price for a in empty_book.asks]
        assert bid_prices == sorted(bid_prices, reverse=True)
        assert ask_prices == sorted(ask_prices)