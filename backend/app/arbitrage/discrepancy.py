"""Price discrepancy monitor for cross-exchange arbitrage detection."""

import asyncio
import logging
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple, Callable

from ..models import OrderBookSnapshot
from .models import ArbitrageOpportunity, ExchangeLatency


logger = logging.getLogger(__name__)


class PriceDiscrepancyMonitor:
    """
    Monitors price discrepancies across exchanges for arbitrage opportunities.
    Accounts for latency, fees, and order book depth.
    """

    def __init__(
        self,
        fee_rates: Optional[Dict[str, Decimal]] = None,
        min_profit_threshold_pct: Decimal = Decimal("0.1"),  # 0.1% minimum profit
        latency_buffer_ms: int = 100,  # Additional latency buffer for safety
        on_opportunity: Optional[Callable[[ArbitrageOpportunity], None]] = None
    ):
        """
        Initialize the price discrepancy monitor.

        Args:
            fee_rates: Exchange fee rates (e.g., {"binance": 0.001, "coinbase": 0.005})
            min_profit_threshold_pct: Minimum profit percentage to consider an opportunity
            latency_buffer_ms: Additional latency buffer for execution risk
            on_opportunity: Callback when arbitrage opportunity is detected
        """
        # Default fee rates if not provided
        self.fee_rates = fee_rates or {
            "binance": Decimal("0.001"),  # 0.1%
            "coinbase": Decimal("0.005"),  # 0.5%
            "kraken": Decimal("0.0025"),  # 0.25%
            "bybit": Decimal("0.001"),
            "okx": Decimal("0.001")
        }

        self.min_profit_threshold_pct = min_profit_threshold_pct
        self.latency_buffer_ms = latency_buffer_ms
        self.on_opportunity = on_opportunity

        # Track latest order books by exchange and symbol
        self._order_books: Dict[str, Dict[str, OrderBookSnapshot]] = defaultdict(dict)

        # Track latencies for each exchange
        self._latencies: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        self._last_update_times: Dict[str, float] = {}

        # Track detected opportunities
        self._opportunities: List[ArbitrageOpportunity] = []
        self._opportunity_history: deque = deque(maxlen=1000)

        # Statistics
        self._stats = {
            "total_opportunities": 0,
            "profitable_opportunities": 0,
            "total_potential_profit": Decimal("0"),
            "largest_opportunity": Decimal("0")
        }

    async def update_order_book(self, snapshot: OrderBookSnapshot) -> None:
        """
        Update order book and check for arbitrage opportunities.

        Args:
            snapshot: Order book snapshot from an exchange
        """
        exchange = snapshot.exchange
        symbol = snapshot.symbol

        # Update latency tracking
        current_time = time.time()
        if exchange in self._last_update_times:
            latency_ms = (current_time - self._last_update_times[exchange]) * 1000
            self._latencies[exchange].append(latency_ms)
        self._last_update_times[exchange] = current_time

        # Store the snapshot
        self._order_books[exchange][symbol] = snapshot

        # Check for arbitrage opportunities
        await self._check_arbitrage(symbol)

    async def _check_arbitrage(self, symbol: str) -> None:
        """
        Check for arbitrage opportunities for a specific symbol across all exchanges.

        Args:
            symbol: Trading symbol to check
        """
        # Get all exchanges that have this symbol
        exchanges_with_symbol = [
            exchange for exchange, books in self._order_books.items()
            if symbol in books
        ]

        if len(exchanges_with_symbol) < 2:
            return  # Need at least 2 exchanges

        # Check all exchange pairs
        for i, exchange1 in enumerate(exchanges_with_symbol):
            for exchange2 in exchanges_with_symbol[i + 1:]:
                opportunity = self._analyze_pair(
                    symbol,
                    exchange1,
                    exchange2
                )

                if opportunity:
                    await self._handle_opportunity(opportunity)

    def _analyze_pair(
        self,
        symbol: str,
        exchange1: str,
        exchange2: str
    ) -> Optional[ArbitrageOpportunity]:
        """
        Analyze a pair of exchanges for arbitrage opportunity.

        Args:
            symbol: Trading symbol
            exchange1: First exchange
            exchange2: Second exchange

        Returns:
            ArbitrageOpportunity if found, None otherwise
        """
        book1 = self._order_books[exchange1].get(symbol)
        book2 = self._order_books[exchange2].get(symbol)

        if not book1 or not book2:
            return None

        # Check data freshness (skip if data is older than 5 seconds)
        current_time_us = int(time.time() * 1_000_000)
        if (current_time_us - book1.timestamp_us > 5_000_000 or
            current_time_us - book2.timestamp_us > 5_000_000):
            return None

        # Get best prices
        if not book1.best_bid or not book1.best_ask:
            return None
        if not book2.best_bid or not book2.best_ask:
            return None

        # Check for arbitrage opportunities in both directions
        opportunities = []

        # Direction 1: Buy on exchange1, sell on exchange2
        if book1.best_ask.price < book2.best_bid.price:
            opp = self._calculate_opportunity(
                symbol,
                exchange1,  # buy exchange
                exchange2,  # sell exchange
                book1.best_ask,  # buy price level
                book2.best_bid,  # sell price level
                book1,
                book2
            )
            if opp:
                opportunities.append(opp)

        # Direction 2: Buy on exchange2, sell on exchange1
        if book2.best_ask.price < book1.best_bid.price:
            opp = self._calculate_opportunity(
                symbol,
                exchange2,  # buy exchange
                exchange1,  # sell exchange
                book2.best_ask,  # buy price level
                book1.best_bid,  # sell price level
                book2,
                book1
            )
            if opp:
                opportunities.append(opp)

        # Return the most profitable opportunity
        if opportunities:
            return max(opportunities, key=lambda x: x.profit_pct)

        return None

    def _calculate_opportunity(
        self,
        symbol: str,
        buy_exchange: str,
        sell_exchange: str,
        buy_level: "PriceLevel",
        sell_level: "PriceLevel",
        buy_book: OrderBookSnapshot,
        sell_book: OrderBookSnapshot
    ) -> Optional[ArbitrageOpportunity]:
        """
        Calculate details of an arbitrage opportunity.

        Args:
            symbol: Trading symbol
            buy_exchange: Exchange to buy from
            sell_exchange: Exchange to sell to
            buy_level: Buy price level
            sell_level: Sell price level
            buy_book: Buy exchange order book
            sell_book: Sell exchange order book

        Returns:
            ArbitrageOpportunity if profitable, None otherwise
        """
        buy_price = buy_level.price
        sell_price = sell_level.price
        buy_volume = buy_level.quantity
        sell_volume = sell_level.quantity

        # Calculate spread
        spread = sell_price - buy_price
        spread_pct = (spread / buy_price) * Decimal("100")

        # Get fee rates
        buy_fee_rate = self.fee_rates.get(buy_exchange, Decimal("0.001"))
        sell_fee_rate = self.fee_rates.get(sell_exchange, Decimal("0.001"))

        # Calculate fees (as percentage of trade value)
        total_fee_pct = buy_fee_rate + sell_fee_rate

        # Calculate net profit percentage after fees
        net_profit_pct = spread_pct - (total_fee_pct * Decimal("100"))

        # Check if profitable above threshold
        if net_profit_pct <= self.min_profit_threshold_pct:
            return None

        # Calculate potential volume (limited by both sides)
        potential_volume = min(buy_volume, sell_volume)

        # Calculate estimated profit
        buy_cost = buy_price * potential_volume
        sell_revenue = sell_price * potential_volume
        buy_fees = buy_cost * buy_fee_rate
        sell_fees = sell_revenue * sell_fee_rate
        estimated_profit = sell_revenue - buy_cost - buy_fees - sell_fees

        # Calculate latency risk
        buy_latency = self._get_avg_latency(buy_exchange)
        sell_latency = self._get_avg_latency(sell_exchange)
        total_latency = buy_latency + sell_latency + self.latency_buffer_ms

        # Calculate confidence based on data freshness and latency
        data_age_ms = max(
            (time.time() * 1000) - (buy_book.timestamp_us / 1000),
            (time.time() * 1000) - (sell_book.timestamp_us / 1000)
        )

        # Confidence decreases with data age and latency
        confidence = max(0.0, min(1.0,
            1.0 - (data_age_ms / 5000) - (total_latency / 1000)
        ))

        return ArbitrageOpportunity(
            timestamp=datetime.now(),
            symbol=symbol,
            buy_exchange=buy_exchange,
            sell_exchange=sell_exchange,
            buy_price=buy_price,
            sell_price=sell_price,
            spread=spread,
            spread_pct=spread_pct,
            buy_volume=buy_volume,
            sell_volume=sell_volume,
            potential_volume=potential_volume,
            estimated_profit=estimated_profit,
            buy_fees=buy_fees,
            sell_fees=sell_fees,
            latency_risk_ms=int(total_latency),
            confidence=confidence
        )

    def _get_avg_latency(self, exchange: str) -> float:
        """
        Get average latency for an exchange.

        Args:
            exchange: Exchange name

        Returns:
            Average latency in milliseconds
        """
        if exchange not in self._latencies or not self._latencies[exchange]:
            return 50.0  # Default estimate

        return sum(self._latencies[exchange]) / len(self._latencies[exchange])

    async def _handle_opportunity(self, opportunity: ArbitrageOpportunity) -> None:
        """
        Handle a detected arbitrage opportunity.

        Args:
            opportunity: Detected arbitrage opportunity
        """
        # Update statistics
        self._stats["total_opportunities"] += 1
        if opportunity.estimated_profit > 0:
            self._stats["profitable_opportunities"] += 1
            self._stats["total_potential_profit"] += opportunity.estimated_profit
            self._stats["largest_opportunity"] = max(
                self._stats["largest_opportunity"],
                opportunity.estimated_profit
            )

        # Store opportunity
        self._opportunities.append(opportunity)
        self._opportunity_history.append(opportunity)

        # Log the opportunity
        logger.info(
            f"Arbitrage opportunity: {opportunity.symbol} "
            f"Buy {opportunity.buy_exchange} @ {opportunity.buy_price:.2f} "
            f"Sell {opportunity.sell_exchange} @ {opportunity.sell_price:.2f} "
            f"Profit: {opportunity.profit_pct:.3f}% "
            f"Volume: {opportunity.potential_volume:.4f} "
            f"Est. Profit: ${opportunity.estimated_profit:.2f}"
        )

        # Trigger callback
        if self.on_opportunity:
            await asyncio.create_task(self.on_opportunity(opportunity))

    def get_opportunities(
        self,
        symbol: Optional[str] = None,
        min_profit_pct: Optional[Decimal] = None,
        max_age_seconds: int = 60
    ) -> List[ArbitrageOpportunity]:
        """
        Get recent arbitrage opportunities.

        Args:
            symbol: Filter by symbol (optional)
            min_profit_pct: Minimum profit percentage filter
            max_age_seconds: Maximum age of opportunities to return

        Returns:
            List of recent arbitrage opportunities
        """
        cutoff_time = datetime.now() - timedelta(seconds=max_age_seconds)

        opportunities = [
            opp for opp in self._opportunities
            if opp.timestamp > cutoff_time
        ]

        if symbol:
            opportunities = [
                opp for opp in opportunities
                if opp.symbol == symbol
            ]

        if min_profit_pct is not None:
            opportunities = [
                opp for opp in opportunities
                if opp.profit_pct >= min_profit_pct
            ]

        return sorted(opportunities, key=lambda x: x.profit_pct, reverse=True)

    def get_statistics(self) -> Dict:
        """
        Get monitor statistics.

        Returns:
            Dictionary of statistics
        """
        return {
            **self._stats,
            "active_exchanges": len(self._order_books),
            "tracked_symbols": len(set(
                symbol
                for books in self._order_books.values()
                for symbol in books.keys()
            )),
            "avg_latencies_ms": {
                exchange: self._get_avg_latency(exchange)
                for exchange in self._latencies
            }
        }

    def get_exchange_latencies(self) -> Dict[str, ExchangeLatency]:
        """
        Get detailed latency metrics for each exchange.

        Returns:
            Dictionary of exchange latencies
        """
        result = {}

        for exchange, latencies in self._latencies.items():
            if not latencies:
                continue

            sorted_latencies = sorted(latencies)
            p95_index = int(len(sorted_latencies) * 0.95)

            result[exchange] = ExchangeLatency(
                exchange=exchange,
                avg_latency_ms=sum(latencies) / len(latencies),
                min_latency_ms=min(latencies),
                max_latency_ms=max(latencies),
                p95_latency_ms=sorted_latencies[p95_index] if p95_index < len(sorted_latencies) else max(latencies),
                last_updated=datetime.now()
            )

        return result