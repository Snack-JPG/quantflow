"""Configuration and data classes for backtesting."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Literal, Optional
from enum import Enum


class SlippageModel(str, Enum):
    """Available slippage models."""
    FIXED = "fixed"  # Fixed amount/percentage
    PROPORTIONAL = "proportional"  # Proportional to order size
    ORDER_BOOK = "order_book"  # Based on actual order book depth


class PositionSizing(str, Enum):
    """Position sizing methods."""
    FIXED = "fixed"  # Fixed amount per trade
    KELLY = "kelly"  # Kelly criterion
    RISK_PARITY = "risk_parity"  # Risk parity allocation


@dataclass
class BacktestConfig:
    """Configuration for backtest execution."""

    initial_capital: Decimal = Decimal('100000')
    commission_bps: float = 10.0  # Basis points (0.1% = 10bps)
    slippage_model: SlippageModel = SlippageModel.PROPORTIONAL
    slippage_bps: float = 5.0  # For fixed/proportional models
    position_sizing: PositionSizing = PositionSizing.FIXED
    max_position_pct: float = 0.1  # Max 10% of capital per position
    max_positions: int = 10  # Maximum concurrent positions
    use_shorts: bool = True  # Allow short positions
    rebalance_frequency: Optional[timedelta] = None  # For portfolio strategies
    warmup_period: Optional[timedelta] = timedelta(hours=1)  # Data warmup before trading

    # Risk management
    stop_loss_pct: Optional[float] = None  # Optional stop loss %
    take_profit_pct: Optional[float] = None  # Optional take profit %
    max_drawdown_pct: Optional[float] = None  # Stop if drawdown exceeds this

    # Kelly criterion parameters (if using Kelly sizing)
    kelly_fraction: float = 0.25  # Fractional Kelly (reduce for safety)

    def get_commission_decimal(self) -> Decimal:
        """Convert commission from basis points to decimal."""
        return Decimal(str(self.commission_bps / 10000))

    def get_slippage_decimal(self) -> Decimal:
        """Convert slippage from basis points to decimal."""
        return Decimal(str(self.slippage_bps / 10000))


@dataclass
class Position:
    """Represents an open position."""

    symbol: str
    side: Literal["long", "short"]
    entry_price: Decimal
    quantity: Decimal
    entry_time: datetime
    entry_value: Decimal  # Position value at entry
    current_price: Optional[Decimal] = None
    exit_price: Optional[Decimal] = None
    exit_time: Optional[datetime] = None
    stop_loss: Optional[Decimal] = None
    take_profit: Optional[Decimal] = None
    commission_paid: Decimal = Decimal('0')
    slippage_paid: Decimal = Decimal('0')
    unrealized_pnl: Decimal = Decimal('0')
    realized_pnl: Optional[Decimal] = None
    metadata: dict = field(default_factory=dict)

    @property
    def is_open(self) -> bool:
        """Check if position is still open."""
        return self.exit_price is None

    @property
    def current_value(self) -> Decimal:
        """Calculate current position value."""
        if self.current_price:
            if self.side == "long":
                return self.quantity * self.current_price
            else:  # short
                # Short value = entry_value - (current_price - entry_price) * quantity
                price_change = self.current_price - self.entry_price
                return self.entry_value - (price_change * self.quantity)
        return self.entry_value

    def update_price(self, price: Decimal):
        """Update current price and unrealized PnL."""
        self.current_price = price
        if self.side == "long":
            self.unrealized_pnl = (price - self.entry_price) * self.quantity
        else:  # short
            self.unrealized_pnl = (self.entry_price - price) * self.quantity
        self.unrealized_pnl -= (self.commission_paid + self.slippage_paid)

    def close(self, exit_price: Decimal, exit_time: datetime,
              commission: Decimal = Decimal('0'), slippage: Decimal = Decimal('0')):
        """Close the position."""
        self.exit_price = exit_price
        self.exit_time = exit_time
        self.commission_paid += commission
        self.slippage_paid += slippage

        if self.side == "long":
            gross_pnl = (exit_price - self.entry_price) * self.quantity
        else:  # short
            gross_pnl = (self.entry_price - exit_price) * self.quantity

        self.realized_pnl = gross_pnl - self.commission_paid - self.slippage_paid
        self.unrealized_pnl = Decimal('0')


@dataclass
class TradeRecord:
    """Record of a completed trade."""

    trade_id: str
    symbol: str
    side: Literal["long", "short"]
    entry_time: datetime
    entry_price: Decimal
    exit_time: datetime
    exit_price: Decimal
    quantity: Decimal
    gross_pnl: Decimal
    commission: Decimal
    slippage: Decimal
    net_pnl: Decimal
    return_pct: float
    holding_period: timedelta
    entry_signal_reason: str
    exit_signal_reason: str
    max_profit: Decimal  # Maximum profit during trade
    max_loss: Decimal  # Maximum loss during trade
    metadata: dict = field(default_factory=dict)

    @classmethod
    def from_position(cls, position: Position, exit_signal_reason: str,
                      trade_id: str) -> 'TradeRecord':
        """Create trade record from closed position."""
        if not position.exit_price or not position.exit_time:
            raise ValueError("Position must be closed to create trade record")

        if position.side == "long":
            gross_pnl = (position.exit_price - position.entry_price) * position.quantity
        else:
            gross_pnl = (position.entry_price - position.exit_price) * position.quantity

        return_pct = float(position.realized_pnl / position.entry_value) * 100

        return cls(
            trade_id=trade_id,
            symbol=position.symbol,
            side=position.side,
            entry_time=position.entry_time,
            entry_price=position.entry_price,
            exit_time=position.exit_time,
            exit_price=position.exit_price,
            quantity=position.quantity,
            gross_pnl=gross_pnl,
            commission=position.commission_paid,
            slippage=position.slippage_paid,
            net_pnl=position.realized_pnl,
            return_pct=return_pct,
            holding_period=position.exit_time - position.entry_time,
            entry_signal_reason=position.metadata.get('entry_reason', ''),
            exit_signal_reason=exit_signal_reason,
            max_profit=position.metadata.get('max_profit', Decimal('0')),
            max_loss=position.metadata.get('max_loss', Decimal('0')),
            metadata=position.metadata
        )