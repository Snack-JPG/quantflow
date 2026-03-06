"""Triangular arbitrage scanner for cryptocurrency markets."""

import asyncio
import logging
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Set, Tuple, Callable

from ..models import OrderBookSnapshot
from .models import TriangularArbitrageOpportunity


logger = logging.getLogger(__name__)


class TriangularArbitrageScanner:
    """
    Scans for triangular arbitrage opportunities within and across exchanges.

    Example paths:
    - BTC/USDT -> ETH/USDT -> ETH/BTC -> BTC (profit if product != 1)
    - BTC/USDT -> LTC/BTC -> LTC/USDT -> USDT
    """

    def __init__(
        self,
        fee_rate: Decimal = Decimal("0.001"),  # 0.1% per trade
        min_profit_threshold_pct: Decimal = Decimal("0.3"),  # 0.3% minimum profit (3 trades)
        max_depth: int = 3,  # Maximum path depth (3 = triangular)
        on_opportunity: Optional[Callable[[TriangularArbitrageOpportunity], None]] = None
    ):
        """
        Initialize the triangular arbitrage scanner.

        Args:
            fee_rate: Trading fee rate per transaction
            min_profit_threshold_pct: Minimum profit percentage to consider
            max_depth: Maximum trading path depth
            on_opportunity: Callback when opportunity is detected
        """
        self.fee_rate = fee_rate
        self.min_profit_threshold_pct = min_profit_threshold_pct
        self.max_depth = max_depth
        self.on_opportunity = on_opportunity

        # Track order books by exchange and symbol
        self._order_books: Dict[str, Dict[str, OrderBookSnapshot]] = defaultdict(dict)

        # Track available trading pairs and their relationships
        self._trading_graph: Dict[str, Dict[str, Set[str]]] = defaultdict(lambda: defaultdict(set))

        # Cache for parsed symbols
        self._symbol_cache: Dict[str, Tuple[str, str]] = {}

        # Track detected opportunities
        self._opportunities: List[TriangularArbitrageOpportunity] = []

        # Statistics
        self._stats = {
            "paths_checked": 0,
            "opportunities_found": 0,
            "total_potential_profit": Decimal("0"),
            "best_opportunity": Decimal("0")
        }

    def _parse_symbol(self, symbol: str) -> Tuple[str, str]:
        """
        Parse a symbol into base and quote currencies.

        Args:
            symbol: Trading symbol (e.g., "BTCUSDT", "ETHBTC")

        Returns:
            Tuple of (base, quote) currencies
        """
        if symbol in self._symbol_cache:
            return self._symbol_cache[symbol]

        # Common patterns
        if symbol.endswith("USDT"):
            base = symbol[:-4]
            quote = "USDT"
        elif symbol.endswith("USD"):
            base = symbol[:-3]
            quote = "USD"
        elif symbol.endswith("BTC"):
            base = symbol[:-3]
            quote = "BTC"
        elif symbol.endswith("ETH"):
            base = symbol[:-3]
            quote = "ETH"
        elif symbol.endswith("BNB"):
            base = symbol[:-3]
            quote = "BNB"
        else:
            # Default: assume 3-letter currencies
            if len(symbol) == 6:
                base = symbol[:3]
                quote = symbol[3:]
            else:
                base = symbol
                quote = "UNKNOWN"

        self._symbol_cache[symbol] = (base, quote)
        return base, quote

    async def update_order_book(self, snapshot: OrderBookSnapshot) -> None:
        """
        Update order book and check for triangular arbitrage opportunities.

        Args:
            snapshot: Order book snapshot
        """
        exchange = snapshot.exchange
        symbol = snapshot.symbol

        # Store the snapshot
        self._order_books[exchange][symbol] = snapshot

        # Update trading graph
        base, quote = self._parse_symbol(symbol)
        self._trading_graph[exchange][base].add(quote)
        self._trading_graph[exchange][quote].add(base)

        # Check for arbitrage opportunities
        await self._scan_triangular_paths(exchange)

    async def _scan_triangular_paths(self, exchange: str) -> None:
        """
        Scan for triangular arbitrage opportunities on an exchange.

        Args:
            exchange: Exchange to scan
        """
        if exchange not in self._trading_graph:
            return

        graph = self._trading_graph[exchange]
        order_books = self._order_books[exchange]

        # Common triangular paths to check
        triangular_paths = [
            # Classic triangular arbitrage
            ("USDT", "BTC", "ETH", "USDT"),
            ("USDT", "BTC", "LTC", "USDT"),
            ("USDT", "BTC", "XRP", "USDT"),
            ("USDT", "ETH", "BNB", "USDT"),
            ("BTC", "ETH", "BNB", "BTC"),

            # Extended paths
            ("USDT", "BTC", "ADA", "USDT"),
            ("USDT", "ETH", "MATIC", "USDT"),
            ("USDT", "BTC", "SOL", "USDT"),
        ]

        for path in triangular_paths:
            opportunity = await self._check_path(exchange, path, order_books)
            if opportunity:
                await self._handle_opportunity(opportunity)

        # Also scan for automatic path discovery
        await self._discover_paths(exchange)

    async def _discover_paths(self, exchange: str) -> None:
        """
        Automatically discover triangular arbitrage paths.

        Args:
            exchange: Exchange to scan
        """
        graph = self._trading_graph[exchange]
        order_books = self._order_books[exchange]

        # Start from major currencies
        start_currencies = ["USDT", "USD", "BTC", "ETH", "BNB"]

        for start in start_currencies:
            if start not in graph:
                continue

            # Find all 3-hop cycles back to start
            for mid1 in graph[start]:
                if mid1 == start:
                    continue

                for mid2 in graph[mid1]:
                    if mid2 == start or mid2 == mid1:
                        continue

                    # Check if we can get back to start
                    if start in graph[mid2]:
                        path = (start, mid1, mid2, start)
                        opportunity = await self._check_path(exchange, path, order_books)
                        if opportunity:
                            await self._handle_opportunity(opportunity)

                        self._stats["paths_checked"] += 1

    async def _check_path(
        self,
        exchange: str,
        path: Tuple[str, ...],
        order_books: Dict[str, OrderBookSnapshot]
    ) -> Optional[TriangularArbitrageOpportunity]:
        """
        Check if a path has arbitrage opportunity.

        Args:
            exchange: Exchange name
            path: Currency path (e.g., ("USDT", "BTC", "ETH", "USDT"))
            order_books: Order books for the exchange

        Returns:
            TriangularArbitrageOpportunity if profitable, None otherwise
        """
        if len(path) < 3:
            return None

        # Build trading steps
        steps = []
        prices = {}
        volumes = {}

        for i in range(len(path) - 1):
            from_currency = path[i]
            to_currency = path[i + 1]

            # Find the trading pair
            symbol, side = self._find_trading_pair(
                from_currency,
                to_currency,
                order_books
            )

            if not symbol:
                return None  # Path not available

            book = order_books.get(symbol)
            if not book or not book.best_bid or not book.best_ask:
                return None

            # Determine price and volume based on side
            if side == "buy":
                # We're buying the base currency
                price = book.best_ask.price
                volume = book.best_ask.quantity
            else:
                # We're selling the base currency
                price = book.best_bid.price
                volume = book.best_bid.quantity

            steps.append((symbol, side, exchange))
            prices[f"{from_currency}->{to_currency}"] = price
            volumes[symbol] = volume

        # Calculate profitability
        return self._calculate_triangular_profit(
            exchange,
            path,
            steps,
            prices,
            volumes
        )

    def _find_trading_pair(
        self,
        from_currency: str,
        to_currency: str,
        order_books: Dict[str, OrderBookSnapshot]
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Find the trading pair and side for converting currencies.

        Args:
            from_currency: Source currency
            to_currency: Target currency
            order_books: Available order books

        Returns:
            Tuple of (symbol, side) or (None, None) if not found
        """
        # Try direct pair (from/to)
        symbol1 = from_currency + to_currency
        if symbol1 in order_books:
            return symbol1, "sell"  # Sell from_currency for to_currency

        # Try inverse pair (to/from)
        symbol2 = to_currency + from_currency
        if symbol2 in order_books:
            return symbol2, "buy"  # Buy to_currency with from_currency

        # Try with common suffixes
        pairs_to_try = [
            (from_currency + to_currency + "T", "sell"),  # e.g., USDUSDT
            (to_currency + from_currency + "T", "buy"),
            (from_currency + "_" + to_currency, "sell"),
            (to_currency + "_" + from_currency, "buy"),
        ]

        for symbol, side in pairs_to_try:
            if symbol in order_books:
                return symbol, side

        return None, None

    def _calculate_triangular_profit(
        self,
        exchange: str,
        path: Tuple[str, ...],
        steps: List[Tuple[str, str, str]],
        prices: Dict[str, Decimal],
        volumes: Dict[str, Decimal]
    ) -> Optional[TriangularArbitrageOpportunity]:
        """
        Calculate profit for a triangular arbitrage path.

        Args:
            exchange: Exchange name
            path: Currency path
            steps: Trading steps [(symbol, side, exchange), ...]
            prices: Price mapping
            volumes: Volume mapping

        Returns:
            TriangularArbitrageOpportunity if profitable, None otherwise
        """
        # Start with 1 unit of the first currency
        initial_amount = Decimal("1")
        current_amount = initial_amount

        # Track minimum volume constraint
        min_volume_constraint = Decimal("999999")

        # Execute each step
        for i, (from_curr, to_curr) in enumerate(zip(path[:-1], path[1:])):
            price_key = f"{from_curr}->{to_curr}"

            if price_key not in prices:
                return None

            price = prices[price_key]
            symbol, side, _ = steps[i]

            # Calculate conversion
            if side == "buy":
                # Buying: from_amount / price = to_amount
                current_amount = current_amount / price
            else:
                # Selling: from_amount * price = to_amount
                current_amount = current_amount * price

            # Apply fees
            current_amount = current_amount * (Decimal("1") - self.fee_rate)

            # Track volume constraints
            if symbol in volumes:
                volume_in_base = volumes[symbol]
                # Convert to path currency if needed
                if side == "buy":
                    volume_constraint = volume_in_base * price
                else:
                    volume_constraint = volume_in_base

                min_volume_constraint = min(min_volume_constraint, volume_constraint)

        # Calculate profit
        final_amount = current_amount
        profit = final_amount - initial_amount
        profit_pct = (profit / initial_amount) * Decimal("100")

        # Check if profitable above threshold
        if profit_pct <= self.min_profit_threshold_pct:
            return None

        # Calculate fees
        num_trades = len(steps)
        total_fee_pct = self.fee_rate * num_trades * Decimal("100")

        # Estimate execution time (assume 100ms per trade)
        execution_time_ms = num_trades * 100

        # Calculate confidence based on profit margin
        confidence = min(1.0, float(profit_pct / Decimal("1")))

        return TriangularArbitrageOpportunity(
            timestamp=datetime.now(),
            exchange=exchange,
            path=steps,
            initial_amount=initial_amount,
            final_amount=final_amount,
            profit=profit,
            profit_pct=profit_pct,
            prices=prices,
            volumes=volumes,
            fees_total=total_fee_pct,
            execution_time_ms=execution_time_ms,
            confidence=confidence
        )

    async def _handle_opportunity(self, opportunity: TriangularArbitrageOpportunity) -> None:
        """
        Handle a detected triangular arbitrage opportunity.

        Args:
            opportunity: Detected opportunity
        """
        # Update statistics
        self._stats["opportunities_found"] += 1
        self._stats["total_potential_profit"] += opportunity.profit
        self._stats["best_opportunity"] = max(
            self._stats["best_opportunity"],
            opportunity.profit_pct
        )

        # Store opportunity
        self._opportunities.append(opportunity)

        # Log the opportunity
        path_str = " -> ".join([step[0] for step in opportunity.path])
        logger.info(
            f"Triangular arbitrage: {opportunity.exchange} "
            f"Path: {path_str} "
            f"Profit: {opportunity.profit_pct:.3f}% "
            f"Confidence: {opportunity.confidence:.2f}"
        )

        # Trigger callback
        if self.on_opportunity:
            await asyncio.create_task(self.on_opportunity(opportunity))

    def get_opportunities(
        self,
        exchange: Optional[str] = None,
        min_profit_pct: Optional[Decimal] = None,
        limit: int = 10
    ) -> List[TriangularArbitrageOpportunity]:
        """
        Get recent triangular arbitrage opportunities.

        Args:
            exchange: Filter by exchange (optional)
            min_profit_pct: Minimum profit percentage filter
            limit: Maximum number of opportunities to return

        Returns:
            List of opportunities sorted by profit
        """
        opportunities = self._opportunities.copy()

        if exchange:
            opportunities = [
                opp for opp in opportunities
                if opp.exchange == exchange
            ]

        if min_profit_pct is not None:
            opportunities = [
                opp for opp in opportunities
                if opp.profit_pct >= min_profit_pct
            ]

        # Sort by profit percentage and return top N
        opportunities.sort(key=lambda x: x.profit_pct, reverse=True)
        return opportunities[:limit]

    def get_statistics(self) -> Dict:
        """
        Get scanner statistics.

        Returns:
            Dictionary of statistics
        """
        return {
            **self._stats,
            "active_exchanges": len(self._order_books),
            "tracked_pairs": sum(
                len(books) for books in self._order_books.values()
            ),
            "graph_nodes": sum(
                len(graph) for graph in self._trading_graph.values()
            )
        }