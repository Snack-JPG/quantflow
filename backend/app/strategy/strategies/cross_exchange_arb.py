"""
Cross-Exchange Arbitrage Strategy.

This strategy identifies and trades on price discrepancies between different exchanges.
It looks for opportunities where the price difference exceeds transaction costs.
"""
from typing import List, Dict, Any, Optional, Tuple
from decimal import Decimal
from datetime import datetime, timedelta
from collections import defaultdict, deque
from dataclasses import dataclass

from ..base import Strategy
from ..models import (
    OrderBookSnapshot,
    Trade,
    Alert,
    Signal,
    SignalDirection,
    OrderSide
)


@dataclass
class ArbitrageOpportunity:
    """Represents an arbitrage opportunity between exchanges."""
    timestamp: datetime
    symbol: str
    buy_exchange: str
    sell_exchange: str
    buy_price: Decimal
    sell_price: Decimal
    spread: Decimal
    spread_pct: float
    max_quantity: Decimal
    expected_profit: Decimal


class CrossExchangeArbStrategy(Strategy):
    """
    Cross-Exchange Arbitrage Strategy.

    Identifies price discrepancies between exchanges and generates signals
    to buy on the cheaper exchange and sell on the more expensive one.

    Parameters:
    - min_spread_bps: Minimum spread in basis points to trigger signal (default 30)
    - max_exposure_per_exchange: Max exposure per exchange (default 10000 USDT)
    - fee_bps: Exchange fee in basis points (default 10)
    - latency_buffer_ms: Latency buffer in milliseconds (default 100)
    - depth_check_levels: Order book levels to check for liquidity (default 3)
    """

    def __init__(
        self,
        name: str = "CrossExchange_Arb",
        symbols: List[str] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """Initialize Cross-Exchange Arbitrage strategy."""
        super().__init__(name, symbols or ['BTCUSDT'], config)

        # Strategy parameters
        self.min_spread_bps = self.config.get('min_spread_bps', 30)  # 0.3%
        self.max_exposure_per_exchange = Decimal(str(self.config.get('max_exposure_per_exchange', 10000)))
        self.fee_bps = self.config.get('fee_bps', 10)  # 0.1% per trade
        self.latency_buffer_ms = self.config.get('latency_buffer_ms', 100)
        self.depth_check_levels = self.config.get('depth_check_levels', 3)

        # Exchange order books (symbol -> exchange -> book)
        self.exchange_books: Dict[str, Dict[str, OrderBookSnapshot]] = defaultdict(dict)

        # Arbitrage opportunity tracking
        self.opportunities: Dict[str, deque] = {}
        self.active_arbs: Dict[str, ArbitrageOpportunity] = {}

        # Exchange exposure tracking
        self.exchange_exposure: Dict[str, Decimal] = defaultdict(Decimal)

        # Price history for each exchange
        self.price_history: Dict[str, Dict[str, deque]] = defaultdict(lambda: defaultdict(lambda: deque(maxlen=100)))

        # Initialize state
        for symbol in self.symbols:
            self.opportunities[symbol] = deque(maxlen=100)

    def on_book_update(self, book: OrderBookSnapshot) -> List[Signal]:
        """Handle order book update - main driver for arbitrage detection."""
        signals = []
        symbol = book.symbol
        exchange = book.exchange

        # Update exchange book
        self.exchange_books[symbol][exchange] = book

        # Update price history
        self.price_history[symbol][exchange].append((book.timestamp, book.mid_price))

        # Check for arbitrage opportunities across all exchanges
        if len(self.exchange_books[symbol]) >= 2:
            opportunities = self._find_arbitrage_opportunities(symbol)

            for opp in opportunities:
                self.opportunities[symbol].append(opp)

                # Generate signals if opportunity is profitable
                signal = self._generate_arbitrage_signal(opp)
                if signal:
                    signals.append(signal)

        # Check for exit conditions on existing positions
        if self.has_position(symbol):
            exit_signal = self._check_exit_conditions(symbol, book)
            if exit_signal:
                signals.append(exit_signal)

        return signals

    def on_trade(self, trade: Trade) -> List[Signal]:
        """Handle trade event."""
        self.last_trade[trade.symbol] = trade

        # Update exchange-specific last trade
        symbol = trade.symbol
        exchange = trade.exchange

        # Could use trade data to confirm arbitrage execution
        return []

    def on_alert(self, alert: Alert) -> List[Signal]:
        """Handle pattern detection alert."""
        # Could filter out arbitrage during manipulation events
        return []

    def _find_arbitrage_opportunities(self, symbol: str) -> List[ArbitrageOpportunity]:
        """Find arbitrage opportunities across exchanges."""
        opportunities = []
        books = self.exchange_books[symbol]

        if len(books) < 2:
            return opportunities

        # Get all exchange pairs
        exchanges = list(books.keys())

        for i in range(len(exchanges)):
            for j in range(i + 1, len(exchanges)):
                ex1, ex2 = exchanges[i], exchanges[j]
                book1, book2 = books[ex1], books[ex2]

                # Check staleness (books should be recent)
                time_diff = abs((book1.timestamp - book2.timestamp).total_seconds())
                if time_diff > self.latency_buffer_ms / 1000:
                    continue  # Books too far apart in time

                # Calculate best bid/ask across exchanges
                if book1.bids and book1.asks and book2.bids and book2.asks:
                    # Opportunity 1: Buy on ex1, sell on ex2
                    if book1.asks[0].price < book2.bids[0].price:
                        opp = self._calculate_opportunity(
                            symbol, ex1, ex2,
                            book1.asks[0].price,
                            book2.bids[0].price,
                            book1, book2
                        )
                        if opp:
                            opportunities.append(opp)

                    # Opportunity 2: Buy on ex2, sell on ex1
                    if book2.asks[0].price < book1.bids[0].price:
                        opp = self._calculate_opportunity(
                            symbol, ex2, ex1,
                            book2.asks[0].price,
                            book1.bids[0].price,
                            book2, book1
                        )
                        if opp:
                            opportunities.append(opp)

        return opportunities

    def _calculate_opportunity(
        self,
        symbol: str,
        buy_exchange: str,
        sell_exchange: str,
        buy_price: Decimal,
        sell_price: Decimal,
        buy_book: OrderBookSnapshot,
        sell_book: OrderBookSnapshot
    ) -> Optional[ArbitrageOpportunity]:
        """Calculate details of an arbitrage opportunity."""
        # Calculate spread
        spread = sell_price - buy_price
        spread_pct = float(spread / buy_price * 10000)  # in basis points

        # Account for fees (2x fee for round trip)
        total_fee_bps = self.fee_bps * 2
        net_spread_bps = spread_pct - total_fee_bps

        # Check if profitable after fees
        if net_spread_bps < self.min_spread_bps:
            return None

        # Calculate maximum quantity (limited by order book depth)
        max_buy_qty = sum(level.quantity for level in buy_book.asks[:self.depth_check_levels])
        max_sell_qty = sum(level.quantity for level in sell_book.bids[:self.depth_check_levels])
        max_quantity = min(max_buy_qty, max_sell_qty)

        # Limit by exposure constraints
        max_exposure = self.max_exposure_per_exchange
        max_qty_by_exposure = max_exposure / buy_price
        max_quantity = min(max_quantity, max_qty_by_exposure)

        if max_quantity <= 0:
            return None

        # Calculate expected profit
        gross_profit = spread * max_quantity
        fees = (buy_price * max_quantity * Decimal(str(self.fee_bps / 10000))) + \
               (sell_price * max_quantity * Decimal(str(self.fee_bps / 10000)))
        expected_profit = gross_profit - fees

        if expected_profit <= 0:
            return None

        return ArbitrageOpportunity(
            timestamp=datetime.now(),
            symbol=symbol,
            buy_exchange=buy_exchange,
            sell_exchange=sell_exchange,
            buy_price=buy_price,
            sell_price=sell_price,
            spread=spread,
            spread_pct=spread_pct,
            max_quantity=max_quantity,
            expected_profit=expected_profit
        )

    def _generate_arbitrage_signal(self, opp: ArbitrageOpportunity) -> Optional[Signal]:
        """Generate trading signal from arbitrage opportunity."""
        # Check if we already have a position
        if self.has_position(opp.symbol):
            return None

        # Check exchange exposure limits
        buy_exposure = self.exchange_exposure.get(opp.buy_exchange, Decimal('0'))
        sell_exposure = self.exchange_exposure.get(opp.sell_exchange, Decimal('0'))

        if buy_exposure >= self.max_exposure_per_exchange:
            return None
        if abs(sell_exposure) >= self.max_exposure_per_exchange:
            return None

        # Calculate signal strength based on spread size
        strength = min(1.0, opp.spread_pct / (self.min_spread_bps * 3))

        # Store active arbitrage
        self.active_arbs[opp.symbol] = opp

        # Generate signal (in real trading, this would be two orders)
        # For backtesting, we simulate as a single position
        return self.generate_signal(
            symbol=opp.symbol,
            direction=SignalDirection.LONG,  # Simplified for backtesting
            strength=strength,
            reason=f"Arbitrage: Buy {opp.buy_exchange} @ {opp.buy_price}, "
                  f"Sell {opp.sell_exchange} @ {opp.sell_price} "
                  f"(spread: {opp.spread_pct:.1f} bps)",
            buy_exchange=opp.buy_exchange,
            sell_exchange=opp.sell_exchange,
            buy_price=float(opp.buy_price),
            sell_price=float(opp.sell_price),
            spread_bps=opp.spread_pct,
            expected_profit=float(opp.expected_profit),
            max_quantity=float(opp.max_quantity)
        )

    def _check_exit_conditions(self, symbol: str, book: OrderBookSnapshot) -> Optional[Signal]:
        """Check if we should exit an arbitrage position."""
        if not self.has_position(symbol):
            return None

        position = self.get_position(symbol)

        # Get active arbitrage details
        if symbol not in self.active_arbs:
            # No record of arbitrage, close position
            return self.generate_signal(
                symbol=symbol,
                direction=SignalDirection.CLOSE,
                strength=1.0,
                reason="No active arbitrage record - closing position"
            )

        arb = self.active_arbs[symbol]

        # Check if spread has closed or reversed
        if arb.buy_exchange in self.exchange_books[symbol] and \
           arb.sell_exchange in self.exchange_books[symbol]:

            buy_book = self.exchange_books[symbol][arb.buy_exchange]
            sell_book = self.exchange_books[symbol][arb.sell_exchange]

            if buy_book.asks and sell_book.bids:
                current_spread = sell_book.bids[0].price - buy_book.asks[0].price
                current_spread_bps = float(current_spread / buy_book.asks[0].price * 10000)

                # Exit if spread has closed
                if current_spread_bps < self.fee_bps * 2:
                    del self.active_arbs[symbol]
                    return self.generate_signal(
                        symbol=symbol,
                        direction=SignalDirection.CLOSE,
                        strength=1.0,
                        reason=f"Arbitrage spread closed (current: {current_spread_bps:.1f} bps)",
                        current_spread_bps=current_spread_bps
                    )

                # Exit if spread reversed significantly
                if current_spread_bps < -self.min_spread_bps:
                    del self.active_arbs[symbol]
                    return self.generate_signal(
                        symbol=symbol,
                        direction=SignalDirection.CLOSE,
                        strength=1.0,
                        reason=f"Arbitrage spread reversed (current: {current_spread_bps:.1f} bps)",
                        current_spread_bps=current_spread_bps
                    )

        # Exit after maximum holding period (arbitrage should be quick)
        holding_time = (datetime.now() - position.entry_time).total_seconds()
        if holding_time > 60:  # 1 minute max for arbitrage
            if symbol in self.active_arbs:
                del self.active_arbs[symbol]
            return self.generate_signal(
                symbol=symbol,
                direction=SignalDirection.CLOSE,
                strength=1.0,
                reason=f"Max holding period reached ({holding_time:.0f}s)"
            )

        return None

    def _calculate_triangular_arbitrage(self, base_symbol: str) -> Optional[ArbitrageOpportunity]:
        """
        Calculate triangular arbitrage opportunities.

        For example: BTC/USDT -> ETH/USDT -> ETH/BTC -> BTC/USDT
        """
        # This would require multiple symbols to be tracked
        # Implementation depends on available trading pairs
        # Placeholder for future enhancement
        return None

    def reset(self):
        """Reset strategy state."""
        super().reset()

        # Clear all state
        self.exchange_books.clear()
        self.opportunities.clear()
        self.active_arbs.clear()
        self.exchange_exposure.clear()
        self.price_history.clear()

        # Reinitialize
        for symbol in self.symbols:
            self.opportunities[symbol] = deque(maxlen=100)