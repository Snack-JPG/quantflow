"""
Event-driven backtesting engine with realistic execution simulation.
"""
from typing import List, Dict, Any, Optional, Tuple
from decimal import Decimal
from datetime import datetime, timedelta
from collections import defaultdict
import logging
import uuid
from dataclasses import dataclass

from ..models import (
    OrderBookSnapshot,
    Trade,
    Alert,
    Signal,
    SignalDirection,
    Position,
    OrderSide,
    PositionStatus,
    BacktestConfig,
    TradeRecord,
    BacktestResult,
    PerformanceMetrics
)
from ..base import Strategy
from .metrics import MetricsCalculator


@dataclass
class DataFeed:
    """Container for historical data."""
    order_books: List[OrderBookSnapshot]
    trades: List[Trade]
    alerts: List[Alert] = None

    def __post_init__(self):
        if self.alerts is None:
            self.alerts = []

        # Sort by timestamp
        self.order_books.sort(key=lambda x: x.timestamp_us)
        self.trades.sort(key=lambda x: x.timestamp_us)
        if self.alerts:
            self.alerts.sort(key=lambda x: x.timestamp)

    @property
    def start_time(self) -> datetime:
        """Get earliest timestamp in data."""
        times = []
        if self.order_books:
            times.append(self.order_books[0].timestamp)
        if self.trades:
            times.append(self.trades[0].timestamp)
        if self.alerts:
            times.append(self.alerts[0].timestamp)
        return min(times) if times else datetime.now()

    @property
    def end_time(self) -> datetime:
        """Get latest timestamp in data."""
        times = []
        if self.order_books:
            times.append(self.order_books[-1].timestamp)
        if self.trades:
            times.append(self.trades[-1].timestamp)
        if self.alerts:
            times.append(self.alerts[-1].timestamp)
        return max(times) if times else datetime.now()


class BacktestEngine:
    """
    Event-driven backtesting engine with realistic execution simulation.

    Features:
    - Realistic slippage models (fixed, proportional, order book based)
    - Commission calculation
    - Position sizing strategies
    - Walk-forward optimization support
    - Comprehensive performance metrics
    """

    def __init__(self):
        self.logger = logging.getLogger("backtest.engine")

    def run(
        self,
        strategy: Strategy,
        data: DataFeed,
        config: BacktestConfig
    ) -> BacktestResult:
        """
        Run backtest simulation.

        Args:
            strategy: Trading strategy to test
            data: Historical data feed
            config: Backtesting configuration

        Returns:
            Complete backtest results with metrics
        """
        self.logger.info(f"Starting backtest for {strategy.name}")

        # Initialize state
        strategy.reset()
        capital = config.initial_capital
        equity_curve = [(data.start_time, capital)]
        trades: List[TradeRecord] = []
        positions: List[Position] = []
        open_positions: Dict[str, Position] = {}

        # Create event queue by merging all data sources
        events = self._create_event_queue(data)

        # Process events sequentially
        for event_type, event in events:
            signals = []

            if event_type == "book":
                signals = strategy.on_book_update(event)
            elif event_type == "trade":
                signals = strategy.on_trade(event)
            elif event_type == "alert":
                signals = strategy.on_alert(event)

            # Process generated signals
            for signal in signals:
                symbol = signal.metadata.get('symbol')
                if not symbol:
                    continue

                # Check if we should execute the signal
                if signal.direction == SignalDirection.CLOSE:
                    # Close existing position
                    if symbol in open_positions:
                        position = open_positions[symbol]
                        exit_price = self._calculate_execution_price(
                            event if event_type == "book" else None,
                            position.side,
                            position.quantity,
                            config
                        )

                        if exit_price:
                            commission = self._calculate_commission(
                                exit_price, position.quantity, config
                            )
                            position.close(exit_price, signal.timestamp, commission)
                            strategy.on_position_closed(position)

                            # Update capital
                            capital += position.pnl

                            # Record trade
                            trades.append(TradeRecord(
                                timestamp=signal.timestamp,
                                symbol=symbol,
                                side=OrderSide.SELL if position.side == OrderSide.BUY else OrderSide.BUY,
                                quantity=position.quantity,
                                price=exit_price,
                                commission=commission,
                                slippage=position.slippage_cost,
                                position_id=position.id,
                                signal=signal
                            ))

                            positions.append(position)
                            del open_positions[symbol]

                elif signal.direction in [SignalDirection.LONG, SignalDirection.SHORT]:
                    # Check if we already have a position
                    if symbol in open_positions:
                        continue  # Skip if already have position

                    # Check max positions limit
                    if len(open_positions) >= config.max_positions:
                        continue

                    # Determine position size
                    size = strategy.calculate_position_size(
                        symbol, capital, config, signal.strength
                    )

                    if size < Decimal('10'):  # Minimum position size
                        continue

                    # Get execution price
                    side = OrderSide.BUY if signal.direction == SignalDirection.LONG else OrderSide.SELL
                    book = event if event_type == "book" else None

                    if not book and strategy.last_book.get(symbol):
                        book = strategy.last_book[symbol]

                    if book:
                        quantity = size / book.mid_price  # Convert to base currency
                        entry_price = self._calculate_execution_price(
                            book, side, quantity, config
                        )

                        if entry_price:
                            # Calculate costs
                            commission = self._calculate_commission(
                                entry_price, quantity, config
                            )
                            slippage = self._calculate_slippage(
                                book.mid_price, entry_price, quantity, config
                            )

                            # Check if we have enough capital
                            total_cost = (entry_price * quantity) + commission + slippage
                            if total_cost > capital:
                                continue

                            # Create position
                            position = Position(
                                id=str(uuid.uuid4()),
                                symbol=symbol,
                                side=side,
                                entry_price=entry_price,
                                quantity=quantity,
                                entry_time=signal.timestamp,
                                commission_paid=commission,
                                slippage_cost=slippage,
                                metadata={'signal': signal}
                            )

                            # Update capital
                            capital -= total_cost

                            # Record trade
                            trades.append(TradeRecord(
                                timestamp=signal.timestamp,
                                symbol=symbol,
                                side=side,
                                quantity=quantity,
                                price=entry_price,
                                commission=commission,
                                slippage=slippage,
                                position_id=position.id,
                                signal=signal
                            ))

                            open_positions[symbol] = position
                            strategy.on_position_opened(position)

            # Update equity curve
            current_equity = capital
            for pos in open_positions.values():
                # Mark to market
                if event_type == "book" and event.symbol == pos.symbol:
                    current_price = event.mid_price
                    if pos.side == OrderSide.BUY:
                        unrealized_pnl = (current_price - pos.entry_price) * pos.quantity
                    else:
                        unrealized_pnl = (pos.entry_price - current_price) * pos.quantity
                    current_equity += pos.value + unrealized_pnl

            timestamp = self._get_event_timestamp(event_type, event)
            equity_curve.append((timestamp, current_equity))

        # Close any remaining open positions at end
        for symbol, position in open_positions.items():
            if strategy.last_book.get(symbol):
                exit_price = strategy.last_book[symbol].mid_price
                commission = self._calculate_commission(
                    exit_price, position.quantity, config
                )
                position.close(exit_price, data.end_time, commission)
                capital += position.pnl
                positions.append(position)

        # Calculate performance metrics
        metrics_calc = MetricsCalculator()
        metrics = metrics_calc.calculate(
            positions=positions,
            equity_curve=equity_curve,
            config=config
        )

        # Generate monthly returns
        monthly_returns = self._calculate_monthly_returns(equity_curve)

        # Find drawdown periods
        drawdown_periods = self._find_drawdown_periods(equity_curve)

        return BacktestResult(
            strategy_name=strategy.name,
            config=config,
            start_date=data.start_time,
            end_date=data.end_time,
            trades=trades,
            positions=positions,
            equity_curve=equity_curve,
            metrics=metrics,
            daily_returns=metrics_calc.daily_returns,
            monthly_returns=monthly_returns,
            drawdown_periods=drawdown_periods
        )

    def _create_event_queue(
        self,
        data: DataFeed
    ) -> List[Tuple[str, Any]]:
        """
        Create chronologically ordered event queue.

        Returns:
            List of (event_type, event) tuples
        """
        events = []

        # Add all events with their types
        for book in data.order_books:
            events.append(("book", book))

        for trade in data.trades:
            events.append(("trade", trade))

        for alert in data.alerts:
            events.append(("alert", alert))

        # Sort by timestamp
        events.sort(key=lambda x: self._get_event_timestamp(x[0], x[1]))

        return events

    def _get_event_timestamp(self, event_type: str, event: Any) -> datetime:
        """Get timestamp from event."""
        if event_type in ["book", "trade"]:
            return event.timestamp
        else:  # alert
            return event.timestamp

    def _calculate_execution_price(
        self,
        book: Optional[OrderBookSnapshot],
        side: OrderSide,
        quantity: Decimal,
        config: BacktestConfig
    ) -> Optional[Decimal]:
        """
        Calculate realistic execution price with slippage.

        Args:
            book: Current order book (if available)
            side: Buy or sell
            quantity: Order quantity
            config: Backtest configuration

        Returns:
            Execution price or None if cannot execute
        """
        if not book:
            return None

        base_price = book.mid_price

        if config.slippage_model == "none":
            return base_price

        elif config.slippage_model == "fixed":
            # Fixed slippage in basis points
            slippage_mult = 1 + (config.slippage_bps / 10000)
            if side == OrderSide.BUY:
                return base_price * Decimal(str(slippage_mult))
            else:
                return base_price * Decimal(str(2 - slippage_mult))

        elif config.slippage_model == "proportional":
            # Slippage proportional to order size
            book_depth = sum(level.quantity for level in
                           (book.bids if side == OrderSide.SELL else book.asks)[:5])

            if book_depth == 0:
                return None

            # Higher impact for larger orders relative to book depth
            impact = float(quantity / book_depth) * config.slippage_bps / 10000
            slippage_mult = 1 + impact

            if side == OrderSide.BUY:
                return base_price * Decimal(str(slippage_mult))
            else:
                return base_price * Decimal(str(2 - slippage_mult))

        elif config.slippage_model == "order_book":
            # Walk through order book to get actual execution price
            return book.get_vwap(side.value, quantity)

        return base_price

    def _calculate_slippage(
        self,
        expected_price: Decimal,
        actual_price: Decimal,
        quantity: Decimal,
        config: BacktestConfig
    ) -> Decimal:
        """Calculate slippage cost."""
        price_diff = abs(actual_price - expected_price)
        return price_diff * quantity

    def _calculate_commission(
        self,
        price: Decimal,
        quantity: Decimal,
        config: BacktestConfig
    ) -> Decimal:
        """Calculate trading commission."""
        value = price * quantity
        return value * Decimal(str(config.commission_bps / 10000))

    def _calculate_monthly_returns(
        self,
        equity_curve: List[Tuple[datetime, Decimal]]
    ) -> Dict[str, float]:
        """Calculate monthly returns from equity curve."""
        monthly_returns = defaultdict(list)

        for i in range(1, len(equity_curve)):
            date, equity = equity_curve[i]
            prev_equity = equity_curve[i-1][1]

            month_key = f"{date.year}-{date.month:02d}"
            daily_return = float((equity - prev_equity) / prev_equity)
            monthly_returns[month_key].append(daily_return)

        # Compound daily returns to get monthly returns
        result = {}
        for month, returns in monthly_returns.items():
            compounded = 1.0
            for r in returns:
                compounded *= (1 + r)
            result[month] = (compounded - 1) * 100  # Percentage

        return result

    def _find_drawdown_periods(
        self,
        equity_curve: List[Tuple[datetime, Decimal]]
    ) -> List[Tuple[datetime, datetime, float]]:
        """Find all drawdown periods from equity curve."""
        if len(equity_curve) < 2:
            return []

        periods = []
        peak = equity_curve[0][1]
        peak_date = equity_curve[0][0]
        in_drawdown = False
        dd_start = None

        for date, equity in equity_curve[1:]:
            if equity > peak:
                if in_drawdown:
                    # Drawdown ended
                    dd_pct = float((peak - equity) / peak * 100)
                    periods.append((dd_start, date, dd_pct))
                    in_drawdown = False

                peak = equity
                peak_date = date
            else:
                if not in_drawdown:
                    # Drawdown started
                    in_drawdown = True
                    dd_start = peak_date

        # Handle ongoing drawdown at end
        if in_drawdown:
            final_equity = equity_curve[-1][1]
            dd_pct = float((peak - final_equity) / peak * 100)
            periods.append((dd_start, equity_curve[-1][0], dd_pct))

        return periods