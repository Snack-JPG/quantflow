"""
Performance benchmarks for critical system components.
Measures throughput, latency, and resource usage.
"""

import pytest
import time
import numpy as np
import asyncio
from datetime import datetime
import psutil
import json
from concurrent.futures import ThreadPoolExecutor


class TestPerformanceBenchmarks:
    """Performance benchmark suite"""

    @pytest.fixture
    def large_order_book_data(self):
        """Generate large order book dataset for benchmarking"""
        bids = [(100 - i*0.01, np.random.uniform(1, 100)) for i in range(1000)]
        asks = [(100 + i*0.01, np.random.uniform(1, 100)) for i in range(1000)]
        return {'bids': bids, 'asks': asks}

    @pytest.fixture
    def trade_stream_data(self):
        """Generate trade stream data for benchmarking"""
        trades = []
        base_time = datetime.now()
        for i in range(10000):
            trades.append({
                'timestamp': base_time.timestamp() + i,
                'price': 100 + np.random.normal(0, 1),
                'volume': np.random.uniform(0.1, 10),
                'side': 'buy' if i % 2 == 0 else 'sell'
            })
        return trades

    @pytest.mark.benchmark
    def test_order_book_update_throughput(self, benchmark, large_order_book_data):
        """Benchmark order book update throughput"""
        from app.models.order_book import OrderBook

        book = OrderBook('BTCUSDT', 'binance')

        def update_book():
            # Simulate high-frequency updates
            for bid in large_order_book_data['bids'][:100]:
                book.update_bid(bid[0], bid[1])
            for ask in large_order_book_data['asks'][:100]:
                book.update_ask(ask[0], ask[1])

        result = benchmark(update_book)

        # Verify performance metrics
        assert benchmark.stats['mean'] < 0.1  # Should complete in < 100ms
        print(f"Order book updates/sec: {200 / benchmark.stats['mean']:.0f}")

    @pytest.mark.benchmark
    def test_vpin_calculation_performance(self, benchmark, trade_stream_data):
        """Benchmark VPIN calculation performance"""
        from app.services.microstructure import calculate_vpin

        prices = [t['price'] for t in trade_stream_data]
        volumes = [t['volume'] for t in trade_stream_data]
        sides = [t['side'] for t in trade_stream_data]

        def calculate():
            return calculate_vpin(prices, volumes, sides, window=50)

        result = benchmark(calculate)

        # Should handle 10k trades quickly
        assert benchmark.stats['mean'] < 1.0  # Less than 1 second
        print(f"VPIN calculations/sec: {len(trade_stream_data) / benchmark.stats['mean']:.0f}")

    @pytest.mark.benchmark
    def test_kyle_lambda_performance(self, benchmark, trade_stream_data):
        """Benchmark Kyle's Lambda calculation"""
        from app.services.microstructure import calculate_kyle_lambda

        def calculate():
            return calculate_kyle_lambda(trade_stream_data)

        result = benchmark(calculate)

        assert benchmark.stats['mean'] < 0.5  # Less than 500ms
        print(f"Kyle Lambda calc time: {benchmark.stats['mean']*1000:.2f}ms")

    @pytest.mark.benchmark
    def test_websocket_message_processing(self, benchmark):
        """Benchmark WebSocket message processing throughput"""
        from app.connectors.message_processor import MessageProcessor

        processor = MessageProcessor()

        # Generate sample messages
        messages = []
        for i in range(1000):
            messages.append(json.dumps({
                'type': 'trade',
                'price': 100 + i*0.01,
                'volume': 1.0,
                'timestamp': time.time()
            }))

        def process_messages():
            for msg in messages:
                processor.process(msg)

        result = benchmark(process_messages)

        throughput = len(messages) / benchmark.stats['mean']
        print(f"Message processing throughput: {throughput:.0f} msg/sec")
        assert throughput > 5000  # Should handle > 5000 msg/sec

    @pytest.mark.benchmark
    def test_backtest_engine_performance(self, benchmark):
        """Benchmark backtest engine performance"""
        from app.services.backtesting import BacktestEngine, Strategy

        class DummyStrategy(Strategy):
            def on_data(self, timestamp, price, volume, order_book):
                if len(self.price_history) % 100 == 0:
                    self.buy(1.0)
                elif len(self.price_history) % 100 == 50:
                    self.sell(1.0)

        # Generate test data
        data = []
        for i in range(10000):  # 10k data points
            data.append({
                'timestamp': datetime.now().timestamp() + i,
                'price': 100 + np.sin(i/100) * 10,
                'volume': 1.0
            })

        def run_backtest():
            engine = BacktestEngine(10000)
            strategy = DummyStrategy()
            return engine.run(strategy, data)

        result = benchmark(run_backtest)

        bars_per_second = 10000 / benchmark.stats['mean']
        print(f"Backtest throughput: {bars_per_second:.0f} bars/sec")
        assert bars_per_second > 1000  # Should handle > 1000 bars/sec

    @pytest.mark.benchmark
    def test_ai_pattern_detection_performance(self, benchmark):
        """Benchmark AI pattern detection performance"""
        from app.services.ai_detection import PatternDetector

        detector = PatternDetector()

        # Generate sample data
        data = {
            'prices': np.random.normal(100, 5, 1000).tolist(),
            'volumes': np.random.uniform(1, 100, 1000).tolist(),
            'timestamps': list(range(1000))
        }

        def detect_patterns():
            return detector.detect(data)

        result = benchmark(detect_patterns)

        print(f"Pattern detection time: {benchmark.stats['mean']*1000:.2f}ms for 1000 bars")
        assert benchmark.stats['mean'] < 2.0  # Less than 2 seconds

    @pytest.mark.asyncio
    @pytest.mark.benchmark
    async def test_concurrent_order_book_updates(self, benchmark):
        """Benchmark concurrent order book updates"""
        from app.models.order_book import OrderBook
        import asyncio

        books = {
            'binance': OrderBook('BTCUSDT', 'binance'),
            'coinbase': OrderBook('BTC-USD', 'coinbase'),
            'kraken': OrderBook('XBTUSD', 'kraken')
        }

        async def update_books():
            tasks = []
            for _ in range(100):  # 100 updates per exchange
                for exchange, book in books.items():
                    price = 100 + np.random.normal(0, 1)
                    volume = np.random.uniform(1, 10)
                    tasks.append(asyncio.create_task(
                        asyncio.to_thread(book.update_bid, price, volume)
                    ))
            await asyncio.gather(*tasks)

        start = time.time()
        await update_books()
        elapsed = time.time() - start

        updates_per_second = 300 / elapsed  # 300 total updates
        print(f"Concurrent updates/sec: {updates_per_second:.0f}")
        assert updates_per_second > 1000

    @pytest.mark.benchmark
    def test_memory_usage_order_book(self):
        """Benchmark memory usage for large order books"""
        from app.models.order_book import OrderBook
        import tracemalloc

        tracemalloc.start()

        books = []
        for i in range(10):  # 10 order books
            book = OrderBook(f'PAIR{i}', 'exchange')
            # Add 1000 levels each
            for j in range(1000):
                book.update_bid(100 - j*0.01, np.random.uniform(1, 100))
                book.update_ask(100 + j*0.01, np.random.uniform(1, 100))
            books.append(book)

        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        memory_mb = peak / 1024 / 1024
        print(f"Peak memory for 10 books with 1000 levels each: {memory_mb:.2f} MB")
        assert memory_mb < 100  # Should use less than 100MB

    @pytest.mark.benchmark
    def test_cross_exchange_arbitrage_detection(self, benchmark):
        """Benchmark cross-exchange arbitrage detection"""
        from app.services.arbitrage import ArbitrageDetector

        detector = ArbitrageDetector()

        # Generate order books for multiple exchanges
        order_books = {}
        for exchange in ['binance', 'coinbase', 'kraken']:
            order_books[exchange] = {
                'bids': [(100 - i*0.01, np.random.uniform(1, 10)) for i in range(100)],
                'asks': [(100 + i*0.01, np.random.uniform(1, 10)) for i in range(100)]
            }

        def detect_arbitrage():
            return detector.find_opportunities(order_books)

        result = benchmark(detect_arbitrage)

        detections_per_second = 1 / benchmark.stats['mean']
        print(f"Arbitrage detection rate: {detections_per_second:.0f}/sec")
        assert detections_per_second > 100

    @pytest.mark.benchmark
    def test_database_write_performance(self, benchmark):
        """Benchmark database write performance"""
        import sqlite3
        import tempfile
        import os

        # Create temporary database
        temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        conn = sqlite3.connect(temp_db.name)
        cursor = conn.cursor()

        # Create table
        cursor.execute('''
            CREATE TABLE trades (
                timestamp REAL,
                price REAL,
                volume REAL,
                exchange TEXT
            )
        ''')

        # Generate test data
        trades = []
        for i in range(10000):
            trades.append((
                time.time() + i,
                100 + np.random.normal(0, 1),
                np.random.uniform(0.1, 10),
                'binance'
            ))

        def write_trades():
            cursor.executemany('INSERT INTO trades VALUES (?,?,?,?)', trades)
            conn.commit()

        result = benchmark(write_trades)

        writes_per_second = 10000 / benchmark.stats['mean']
        print(f"Database writes/sec: {writes_per_second:.0f}")

        # Cleanup
        conn.close()
        os.unlink(temp_db.name)

        assert writes_per_second > 1000

    @pytest.mark.benchmark
    def test_api_response_time(self, benchmark):
        """Benchmark API endpoint response times"""
        from fastapi.testclient import TestClient
        from app.main import app

        client = TestClient(app)

        def make_requests():
            responses = []
            for _ in range(100):
                response = client.get("/api/v1/market/summary")
                responses.append(response)
            return responses

        result = benchmark(make_requests)

        avg_response_time = benchmark.stats['mean'] / 100 * 1000  # ms per request
        print(f"Average API response time: {avg_response_time:.2f}ms")
        assert avg_response_time < 50  # Less than 50ms per request

    def test_system_resource_usage(self):
        """Test overall system resource usage"""
        process = psutil.Process()

        # Get initial metrics
        initial_cpu = process.cpu_percent()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Run intensive operations
        from app.models.order_book import OrderBook
        from app.services.microstructure import MicrostructureAnalyzer

        books = []
        for i in range(5):
            book = OrderBook(f'PAIR{i}', 'exchange')
            for j in range(500):
                book.update_bid(100 - j*0.01, np.random.uniform(1, 100))
                book.update_ask(100 + j*0.01, np.random.uniform(1, 100))
            books.append(book)

        # Calculate metrics
        analyzer = MicrostructureAnalyzer()
        for book in books:
            analyzer.calculate_spread_metrics(book)

        # Get final metrics
        final_cpu = process.cpu_percent()
        final_memory = process.memory_info().rss / 1024 / 1024  # MB

        memory_increase = final_memory - initial_memory

        print(f"CPU usage: {final_cpu}%")
        print(f"Memory usage: {final_memory:.2f} MB")
        print(f"Memory increase: {memory_increase:.2f} MB")

        # Assert reasonable resource usage
        assert final_cpu < 80  # Less than 80% CPU
        assert memory_increase < 500  # Less than 500MB increase