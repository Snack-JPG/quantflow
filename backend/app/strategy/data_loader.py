"""
Historical data downloader and loader for backtesting.

Downloads data from Binance public data repository (data.binance.vision).
"""
import asyncio
import aiohttp
import zipfile
import csv
import json
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
import logging
from io import BytesIO, StringIO

from .models import OrderBookSnapshot, Trade, PriceLevel, OrderSide
from .backtesting import DataFeed


class BinanceDataLoader:
    """
    Download and load historical data from Binance.

    Binance provides free historical data at:
    https://data.binance.vision/
    """

    BASE_URL = "https://data.binance.vision/data/spot"

    def __init__(self, data_dir: str = "./data"):
        """
        Initialize data loader.

        Args:
            data_dir: Directory to store downloaded data
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger("data_loader")

    async def download_trades(
        self,
        symbol: str,
        date: datetime,
        save_local: bool = True
    ) -> Optional[List[Trade]]:
        """
        Download trade data for a specific date.

        Args:
            symbol: Trading pair (e.g., 'BTCUSDT')
            date: Date to download
            save_local: Save to local file

        Returns:
            List of trades or None if download failed
        """
        # Format date for Binance URL
        date_str = date.strftime("%Y-%m-%d")

        # Construct URL for daily trades
        url = f"{self.BASE_URL}/daily/trades/{symbol}/{symbol}-trades-{date_str}.zip"

        self.logger.info(f"Downloading trades for {symbol} on {date_str}")

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        self.logger.error(f"Failed to download trades: {response.status}")
                        return None

                    data = await response.read()

                    # Save locally if requested
                    if save_local:
                        file_path = self.data_dir / f"{symbol}-trades-{date_str}.zip"
                        with open(file_path, 'wb') as f:
                            f.write(data)

                    # Extract and parse trades
                    return self._parse_trades_zip(data, symbol)

        except Exception as e:
            self.logger.error(f"Error downloading trades: {e}")
            return None

    async def download_klines(
        self,
        symbol: str,
        interval: str,
        date: datetime,
        save_local: bool = True
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Download kline/candlestick data.

        Args:
            symbol: Trading pair
            interval: Kline interval (1m, 5m, 15m, 1h, etc.)
            date: Date to download
            save_local: Save to local file

        Returns:
            List of klines or None if download failed
        """
        date_str = date.strftime("%Y-%m-%d")

        # Construct URL for daily klines
        url = f"{self.BASE_URL}/daily/klines/{symbol}/{interval}/{symbol}-{interval}-{date_str}.zip"

        self.logger.info(f"Downloading {interval} klines for {symbol} on {date_str}")

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        self.logger.error(f"Failed to download klines: {response.status}")
                        return None

                    data = await response.read()

                    if save_local:
                        file_path = self.data_dir / f"{symbol}-{interval}-{date_str}.zip"
                        with open(file_path, 'wb') as f:
                            f.write(data)

                    return self._parse_klines_zip(data)

        except Exception as e:
            self.logger.error(f"Error downloading klines: {e}")
            return None

    async def download_orderbook_snapshots(
        self,
        symbol: str,
        date: datetime,
        depth: int = 20
    ) -> Optional[List[OrderBookSnapshot]]:
        """
        Download order book snapshot data.

        Note: Binance provides limited order book snapshot data.
        For real backtesting, you may need to reconstruct from L2 updates.

        Args:
            symbol: Trading pair
            date: Date to download
            depth: Order book depth

        Returns:
            List of order book snapshots
        """
        # Binance doesn't provide direct order book snapshots in their public data
        # We'll simulate by using kline data and adding synthetic depth
        # For production, you'd want to use their websocket recording or paid data

        klines = await self.download_klines(symbol, "1m", date)
        if not klines:
            return None

        # Convert klines to synthetic order book snapshots
        snapshots = []
        for i, kline in enumerate(klines):
            snapshot = self._create_synthetic_orderbook(
                symbol=symbol,
                timestamp=kline['timestamp'],
                price=Decimal(str(kline['close'])),
                volume=Decimal(str(kline['volume'])),
                depth=depth,
                sequence=i
            )
            snapshots.append(snapshot)

        return snapshots

    def _parse_trades_zip(self, zip_data: bytes, symbol: str) -> List[Trade]:
        """Parse trades from zip file."""
        trades = []

        with zipfile.ZipFile(BytesIO(zip_data)) as zf:
            for filename in zf.namelist():
                if filename.endswith('.csv'):
                    with zf.open(filename) as f:
                        content = f.read().decode('utf-8')
                        reader = csv.DictReader(StringIO(content))

                        for row in reader:
                            trade = Trade(
                                exchange="binance",
                                symbol=symbol,
                                timestamp_us=int(float(row['time']) * 1000),  # Convert to microseconds
                                price=Decimal(row['price']),
                                quantity=Decimal(row['qty']),
                                side=OrderSide.BUY if row.get('is_buyer_maker', 'false') == 'false' else OrderSide.SELL,
                                trade_id=str(row['id'])
                            )
                            trades.append(trade)

        return trades

    def _parse_klines_zip(self, zip_data: bytes) -> List[Dict[str, Any]]:
        """Parse klines from zip file."""
        klines = []

        with zipfile.ZipFile(BytesIO(zip_data)) as zf:
            for filename in zf.namelist():
                if filename.endswith('.csv'):
                    with zf.open(filename) as f:
                        content = f.read().decode('utf-8')
                        reader = csv.reader(StringIO(content))

                        for row in reader:
                            # Binance kline format:
                            # 0: timestamp, 1: open, 2: high, 3: low, 4: close,
                            # 5: volume, 6: close_time, 7: quote_volume, 8: trades,
                            # 9: taker_buy_volume, 10: taker_buy_quote_volume, 11: ignore
                            kline = {
                                'timestamp': int(row[0]),
                                'open': float(row[1]),
                                'high': float(row[2]),
                                'low': float(row[3]),
                                'close': float(row[4]),
                                'volume': float(row[5]),
                                'trades': int(row[8]),
                                'taker_buy_volume': float(row[9])
                            }
                            klines.append(kline)

        return klines

    def _create_synthetic_orderbook(
        self,
        symbol: str,
        timestamp: int,
        price: Decimal,
        volume: Decimal,
        depth: int,
        sequence: int
    ) -> OrderBookSnapshot:
        """
        Create synthetic order book snapshot from price/volume data.

        This is a simplified simulation for testing purposes.
        Real order book data would come from L2 updates or snapshots.
        """
        bids = []
        asks = []

        # Create synthetic bid levels (below current price)
        for i in range(depth):
            level_price = price * Decimal(str(1 - (i + 1) * 0.0001))  # 0.01% steps
            level_qty = volume * Decimal(str(0.1 * (1 - i * 0.05)))  # Decreasing quantity
            bids.append(PriceLevel(
                price=level_price,
                quantity=level_qty,
                order_count=5 - i  # Fewer orders at deeper levels
            ))

        # Create synthetic ask levels (above current price)
        for i in range(depth):
            level_price = price * Decimal(str(1 + (i + 1) * 0.0001))  # 0.01% steps
            level_qty = volume * Decimal(str(0.1 * (1 - i * 0.05)))  # Decreasing quantity
            asks.append(PriceLevel(
                price=level_price,
                quantity=level_qty,
                order_count=5 - i
            ))

        return OrderBookSnapshot(
            exchange="binance",
            symbol=symbol,
            timestamp_us=timestamp * 1000,  # Convert to microseconds
            sequence=sequence,
            bids=bids,
            asks=asks
        )

    async def load_historical_data(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        include_trades: bool = True,
        include_orderbook: bool = True
    ) -> DataFeed:
        """
        Load historical data for a date range.

        Args:
            symbol: Trading pair
            start_date: Start date
            end_date: End date
            include_trades: Include trade data
            include_orderbook: Include order book data

        Returns:
            DataFeed with historical data
        """
        all_trades = []
        all_orderbooks = []

        # Iterate through dates
        current_date = start_date
        while current_date <= end_date:
            self.logger.info(f"Loading data for {current_date.strftime('%Y-%m-%d')}")

            # Download trades
            if include_trades:
                trades = await self.download_trades(symbol, current_date)
                if trades:
                    all_trades.extend(trades)

            # Download order book snapshots (synthetic)
            if include_orderbook:
                snapshots = await self.download_orderbook_snapshots(symbol, current_date)
                if snapshots:
                    all_orderbooks.extend(snapshots)

            current_date += timedelta(days=1)

        return DataFeed(
            order_books=all_orderbooks,
            trades=all_trades,
            alerts=[]  # No alerts in historical data
        )

    def load_local_data(self, file_path: str) -> Optional[DataFeed]:
        """
        Load data from local file.

        Args:
            file_path: Path to local data file

        Returns:
            DataFeed or None if loading failed
        """
        path = Path(file_path)

        if not path.exists():
            self.logger.error(f"File not found: {file_path}")
            return None

        try:
            if path.suffix == '.json':
                with open(path, 'r') as f:
                    data = json.load(f)
                    return self._parse_json_data(data)
            elif path.suffix == '.csv':
                return self._parse_csv_data(path)
            elif path.suffix == '.zip':
                with open(path, 'rb') as f:
                    zip_data = f.read()
                    # Determine content type and parse accordingly
                    if 'trades' in path.stem:
                        symbol = path.stem.split('-')[0]
                        trades = self._parse_trades_zip(zip_data, symbol)
                        return DataFeed(order_books=[], trades=trades)
                    elif any(interval in path.stem for interval in ['1m', '5m', '15m', '1h']):
                        klines = self._parse_klines_zip(zip_data)
                        # Convert klines to synthetic order books
                        # Implementation depends on requirements
                        return DataFeed(order_books=[], trades=[])
            else:
                self.logger.error(f"Unsupported file format: {path.suffix}")
                return None

        except Exception as e:
            self.logger.error(f"Error loading local data: {e}")
            return None

    def _parse_json_data(self, data: Dict[str, Any]) -> DataFeed:
        """Parse JSON formatted data."""
        # Implementation depends on JSON structure
        # This is a placeholder
        return DataFeed(order_books=[], trades=[])

    def _parse_csv_data(self, file_path: Path) -> DataFeed:
        """Parse CSV formatted data."""
        # Implementation depends on CSV structure
        # This is a placeholder
        return DataFeed(order_books=[], trades=[])