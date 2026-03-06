"""Base strategy class for all trading strategies."""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from decimal import Decimal
from datetime import datetime
import logging

from ..models import (
    OrderBookSnapshot,
    Trade,
    Alert,
    Signal,
    SignalDirection,
    Position,
    BacktestConfig
)


class Strategy(ABC):
    """
    Abstract base class for all trading strategies.

    Strategies receive market events and generate trading signals.
    They maintain their own state and can access historical data.
    """

    def __init__(
        self,
        name: str,
        symbols: List[str],
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize strategy.

        Args:
            name: Strategy name
            symbols: List of symbols to trade
            config: Strategy-specific configuration
        """
        self.name = name
        self.symbols = symbols
        self.config = config or {}

        # Internal state
        self.positions: Dict[str, Position] = {}  # symbol -> Position
        self.signals_history: List[Signal] = []
        self.last_book: Dict[str, OrderBookSnapshot] = {}  # symbol -> last book
        self.last_trade: Dict[str, Trade] = {}  # symbol -> last trade

        # Performance tracking
        self.total_signals = 0
        self.profitable_signals = 0

        # Logging
        self.logger = logging.getLogger(f"strategy.{name}")

    @abstractmethod
    def on_book_update(self, book: OrderBookSnapshot) -> List[Signal]:
        """
        Handle order book update event.

        Args:
            book: Updated order book snapshot

        Returns:
            List of signals generated (can be empty)
        """
        pass

    @abstractmethod
    def on_trade(self, trade: Trade) -> List[Signal]:
        """
        Handle trade execution event.

        Args:
            trade: Executed trade

        Returns:
            List of signals generated (can be empty)
        """
        pass

    @abstractmethod
    def on_alert(self, alert: Alert) -> List[Signal]:
        """
        Handle pattern detection alert.

        Args:
            alert: Pattern detection alert

        Returns:
            List of signals generated (can be empty)
        """
        pass

    def on_position_opened(self, position: Position):
        """
        Callback when a position is opened.

        Args:
            position: Newly opened position
        """
        self.positions[position.symbol] = position
        self.logger.info(
            f"Position opened: {position.symbol} {position.side.value} "
            f"{position.quantity} @ {position.entry_price}"
        )

    def on_position_closed(self, position: Position):
        """
        Callback when a position is closed.

        Args:
            position: Closed position
        """
        if position.symbol in self.positions:
            del self.positions[position.symbol]

        if position.pnl and position.pnl > 0:
            self.profitable_signals += 1

        self.logger.info(
            f"Position closed: {position.symbol} PnL: {position.pnl} "
            f"({position.pnl_pct:.2f}%)"
        )

    def has_position(self, symbol: str) -> bool:
        """Check if strategy has open position for symbol."""
        return symbol in self.positions

    def get_position(self, symbol: str) -> Optional[Position]:
        """Get open position for symbol if exists."""
        return self.positions.get(symbol)

    def generate_signal(
        self,
        symbol: str,
        direction: SignalDirection,
        strength: float,
        reason: str,
        **kwargs
    ) -> Signal:
        """
        Helper to generate a signal.

        Args:
            symbol: Trading symbol
            direction: Signal direction (long/short/close/neutral)
            strength: Signal strength (-1 to 1)
            reason: Signal reason/description
            **kwargs: Additional metadata

        Returns:
            Generated signal
        """
        signal = Signal(
            timestamp=datetime.now(),
            direction=direction,
            strength=max(-1.0, min(1.0, strength)),  # Clamp to [-1, 1]
            reason=reason,
            metadata={
                'strategy': self.name,
                'symbol': symbol,
                **kwargs
            }
        )

        self.signals_history.append(signal)
        self.total_signals += 1

        return signal

    def calculate_position_size(
        self,
        symbol: str,
        capital: Decimal,
        config: BacktestConfig,
        signal_strength: float
    ) -> Decimal:
        """
        Calculate position size based on signal and risk management.

        Args:
            symbol: Trading symbol
            capital: Available capital
            config: Backtesting configuration
            signal_strength: Signal strength (0-1)

        Returns:
            Position size in quote currency
        """
        if config.position_sizing == "fixed":
            size = config.fixed_position_size
        elif config.position_sizing == "kelly":
            # Kelly criterion sizing
            win_rate = self.profitable_signals / max(1, self.total_signals)
            avg_win_loss_ratio = 2.0  # Placeholder, should calculate from history

            kelly_pct = (win_rate * avg_win_loss_ratio - (1 - win_rate)) / avg_win_loss_ratio
            kelly_pct = max(0, min(kelly_pct, 0.25))  # Cap at 25%

            size = capital * Decimal(str(kelly_pct))
        elif config.position_sizing == "risk_parity":
            # Equal risk allocation
            num_positions = len(self.positions) + 1
            size = capital / Decimal(str(num_positions))
        else:  # equal_weight
            size = capital * Decimal(str(config.max_position_pct))

        # Apply signal strength scaling
        size = size * Decimal(str(abs(signal_strength)))

        # Apply maximum position limit
        max_size = capital * Decimal(str(config.max_position_pct))
        size = min(size, max_size)

        return size

    def reset(self):
        """Reset strategy state for new backtest run."""
        self.positions.clear()
        self.signals_history.clear()
        self.last_book.clear()
        self.last_trade.clear()
        self.total_signals = 0
        self.profitable_signals = 0
        self.logger.info(f"Strategy {self.name} reset")

    def get_statistics(self) -> Dict[str, Any]:
        """Get strategy statistics."""
        return {
            'name': self.name,
            'total_signals': self.total_signals,
            'profitable_signals': self.profitable_signals,
            'win_rate': self.profitable_signals / max(1, self.total_signals),
            'open_positions': len(self.positions),
            'symbols_traded': self.symbols
        }
