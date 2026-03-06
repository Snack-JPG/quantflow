"""
Integration tests for exchange connectors.
Tests WebSocket connections, message parsing, and error handling with mock WebSocket servers.
"""

import pytest
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime


class MockWebSocket:
    """Mock WebSocket for testing"""

    def __init__(self, messages=None):
        self.messages = messages or []
        self.message_index = 0
        self.closed = False

    async def recv(self):
        """Simulate receiving messages"""
        if self.message_index < len(self.messages):
            msg = self.messages[self.message_index]
            self.message_index += 1
            return json.dumps(msg)
        await asyncio.sleep(1)
        return None

    async def send(self, message):
        """Simulate sending messages"""
        pass

    async def close(self):
        """Simulate closing connection"""
        self.closed = True


class TestBinanceConnector:
    """Test suite for Binance connector"""

    @pytest.fixture
    def binance_messages(self):
        """Sample Binance WebSocket messages"""
        return [
            {
                "e": "depthUpdate",
                "E": 1640000000000,
                "s": "BTCUSDT",
                "U": 12345,
                "u": 12346,
                "b": [["50000.00", "1.5"], ["49999.00", "2.0"]],
                "a": [["50001.00", "1.2"], ["50002.00", "2.5"]]
            },
            {
                "e": "trade",
                "E": 1640000001000,
                "s": "BTCUSDT",
                "t": 123456,
                "p": "50000.50",
                "q": "0.5",
                "m": False  # Buyer is maker (sell)
            }
        ]

    @pytest.mark.asyncio
    async def test_binance_connection(self, binance_messages):
        """Test Binance WebSocket connection and message handling"""
        from app.connectors.binance_connector import BinanceConnector

        with patch('websockets.connect') as mock_connect:
            mock_ws = MockWebSocket(binance_messages)
            mock_connect.return_value.__aenter__.return_value = mock_ws

            connector = BinanceConnector()
            processed_messages = []

            async def message_handler(msg):
                processed_messages.append(msg)

            connector.on_message = message_handler

            # Run connector for a short time
            task = asyncio.create_task(connector.connect())
            await asyncio.sleep(0.1)
            task.cancel()

            # Verify messages were processed
            assert len(processed_messages) > 0

            # Check depth update processing
            depth_msg = next((m for m in processed_messages if m.get('type') == 'depth'), None)
            assert depth_msg is not None
            assert depth_msg['symbol'] == 'BTCUSDT'
            assert len(depth_msg['bids']) == 2
            assert len(depth_msg['asks']) == 2

            # Check trade processing
            trade_msg = next((m for m in processed_messages if m.get('type') == 'trade'), None)
            assert trade_msg is not None
            assert trade_msg['price'] == 50000.50
            assert trade_msg['volume'] == 0.5

    @pytest.mark.asyncio
    async def test_binance_reconnection(self):
        """Test automatic reconnection on disconnect"""
        from app.connectors.binance_connector import BinanceConnector

        with patch('websockets.connect') as mock_connect:
            # Simulate connection failure then success
            mock_connect.side_effect = [
                Exception("Connection failed"),
                AsyncMock(return_value=MockWebSocket())
            ]

            connector = BinanceConnector()
            connector.max_reconnect_attempts = 2

            await connector.connect_with_retry()

            # Should have attempted to connect twice
            assert mock_connect.call_count == 2


class TestCoinbaseConnector:
    """Test suite for Coinbase connector"""

    @pytest.fixture
    def coinbase_messages(self):
        """Sample Coinbase WebSocket messages"""
        return [
            {
                "type": "snapshot",
                "product_id": "BTC-USD",
                "bids": [["50000.00", "1.5"], ["49999.00", "2.0"]],
                "asks": [["50001.00", "1.2"], ["50002.00", "2.5"]]
            },
            {
                "type": "l2update",
                "product_id": "BTC-USD",
                "changes": [
                    ["buy", "49998.00", "1.0"],
                    ["sell", "50003.00", "0.5"]
                ],
                "time": "2024-01-01T00:00:00.000Z"
            },
            {
                "type": "match",
                "product_id": "BTC-USD",
                "price": "50000.50",
                "size": "0.5",
                "side": "sell",
                "time": "2024-01-01T00:00:01.000Z"
            }
        ]

    @pytest.mark.asyncio
    async def test_coinbase_connection(self, coinbase_messages):
        """Test Coinbase WebSocket connection and message handling"""
        from app.connectors.coinbase_connector import CoinbaseConnector

        with patch('websockets.connect') as mock_connect:
            mock_ws = MockWebSocket(coinbase_messages)
            mock_connect.return_value.__aenter__.return_value = mock_ws

            connector = CoinbaseConnector()
            processed_messages = []

            async def message_handler(msg):
                processed_messages.append(msg)

            connector.on_message = message_handler

            # Run connector
            task = asyncio.create_task(connector.connect())
            await asyncio.sleep(0.1)
            task.cancel()

            # Verify snapshot processing
            snapshot = next((m for m in processed_messages if m.get('type') == 'snapshot'), None)
            assert snapshot is not None
            assert len(snapshot['bids']) == 2
            assert len(snapshot['asks']) == 2

            # Verify l2update processing
            update = next((m for m in processed_messages if m.get('type') == 'l2update'), None)
            assert update is not None
            assert len(update['changes']) == 2

            # Verify trade processing
            trade = next((m for m in processed_messages if m.get('type') == 'trade'), None)
            assert trade is not None
            assert trade['price'] == 50000.50

    @pytest.mark.asyncio
    async def test_coinbase_subscription(self):
        """Test Coinbase subscription message"""
        from app.connectors.coinbase_connector import CoinbaseConnector

        connector = CoinbaseConnector()
        sub_msg = connector.get_subscription_message()

        assert sub_msg['type'] == 'subscribe'
        assert 'BTC-USD' in sub_msg['product_ids']
        assert 'level2' in sub_msg['channels']
        assert 'matches' in sub_msg['channels']


class TestKrakenConnector:
    """Test suite for Kraken connector"""

    @pytest.fixture
    def kraken_messages(self):
        """Sample Kraken WebSocket messages"""
        return [
            [
                0,  # Channel ID
                {
                    "as": [["50001.00", "1.2", "1640000000.123"]],
                    "bs": [["50000.00", "1.5", "1640000000.123"]]
                },
                "book-10",
                "XBT/USD"
            ],
            [
                1,  # Channel ID
                [[
                    "50000.50",  # Price
                    "0.5",       # Volume
                    "1640000001.123",  # Time
                    "s",         # Side (sell)
                    "m"          # Order type (market)
                ]],
                "trade",
                "XBT/USD"
            ]
        ]

    @pytest.mark.asyncio
    async def test_kraken_connection(self, kraken_messages):
        """Test Kraken WebSocket connection and message handling"""
        from app.connectors.kraken_connector import KrakenConnector

        with patch('websockets.connect') as mock_connect:
            mock_ws = MockWebSocket(kraken_messages)
            mock_connect.return_value.__aenter__.return_value = mock_ws

            connector = KrakenConnector()
            processed_messages = []

            async def message_handler(msg):
                processed_messages.append(msg)

            connector.on_message = message_handler

            # Run connector
            task = asyncio.create_task(connector.connect())
            await asyncio.sleep(0.1)
            task.cancel()

            # Verify book processing
            book_msg = next((m for m in processed_messages if m.get('type') == 'book'), None)
            assert book_msg is not None
            assert book_msg['symbol'] == 'XBT/USD'
            assert len(book_msg['asks']) == 1
            assert len(book_msg['bids']) == 1

            # Verify trade processing
            trade_msg = next((m for m in processed_messages if m.get('type') == 'trade'), None)
            assert trade_msg is not None
            assert trade_msg['price'] == 50000.50
            assert trade_msg['volume'] == 0.5
            assert trade_msg['side'] == 'sell'


class TestConnectorErrorHandling:
    """Test error handling across all connectors"""

    @pytest.mark.asyncio
    async def test_malformed_message_handling(self):
        """Test handling of malformed messages"""
        from app.connectors.binance_connector import BinanceConnector

        malformed_messages = [
            {"invalid": "message"},
            "not a json",
            None,
            {"e": "unknown_event"}
        ]

        with patch('websockets.connect') as mock_connect:
            mock_ws = MockWebSocket(malformed_messages)
            mock_connect.return_value.__aenter__.return_value = mock_ws

            connector = BinanceConnector()
            errors = []

            def error_handler(error):
                errors.append(error)

            connector.on_error = error_handler

            # Run connector
            task = asyncio.create_task(connector.connect())
            await asyncio.sleep(0.1)
            task.cancel()

            # Should handle errors gracefully without crashing
            assert len(errors) == 0 or all(isinstance(e, Exception) for e in errors)

    @pytest.mark.asyncio
    async def test_connection_timeout(self):
        """Test connection timeout handling"""
        from app.connectors.binance_connector import BinanceConnector

        with patch('websockets.connect') as mock_connect:
            # Simulate timeout
            mock_connect.side_effect = asyncio.TimeoutError()

            connector = BinanceConnector()
            connector.connection_timeout = 1

            with pytest.raises(asyncio.TimeoutError):
                await connector.connect()

    @pytest.mark.asyncio
    async def test_rate_limiting(self):
        """Test rate limiting implementation"""
        from app.connectors.binance_connector import BinanceConnector

        connector = BinanceConnector()
        connector.max_messages_per_second = 10

        start_time = asyncio.get_event_loop().time()

        # Try to process 20 messages
        for i in range(20):
            await connector.rate_limit()

        elapsed = asyncio.get_event_loop().time() - start_time

        # Should take at least 1 second due to rate limiting
        assert elapsed >= 1.0