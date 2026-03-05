"""Market data models using exact structures from the spec."""

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import List, Literal, Optional


class ExchangeType(str, Enum):
    """Supported exchanges."""
    BINANCE = "binance"
    COINBASE = "coinbase"
    KRAKEN = "kraken"
    BYBIT = "bybit"
    OKX = "okx"


@dataclass
class PriceLevel:
    """Single price level in an order book."""
    price: Decimal
    quantity: Decimal
    order_count: Optional[int] = None  # Some exchanges provide this

    def to_list(self) -> List[str]:
        """Convert to Binance-style list format."""
        return [str(self.price), str(self.quantity)]

    @classmethod
    def from_list(cls, data: List[str]) -> "PriceLevel":
        """Create from Binance-style list format."""
        return cls(
            price=Decimal(data[0]),
            quantity=Decimal(data[1]),
            order_count=None
        )


@dataclass
class OrderBookSnapshot:
    """Full order book snapshot at a point in time."""
    exchange: str
    symbol: str
    timestamp_us: int  # Microsecond precision
    sequence: int  # Exchange sequence number
    bids: List[PriceLevel]  # Sorted descending by price
    asks: List[PriceLevel]  # Sorted ascending by price

    @property
    def best_bid(self) -> Optional[PriceLevel]:
        """Get the best (highest) bid."""
        return self.bids[0] if self.bids else None

    @property
    def best_ask(self) -> Optional[PriceLevel]:
        """Get the best (lowest) ask."""
        return self.asks[0] if self.asks else None

    @property
    def mid_price(self) -> Optional[Decimal]:
        """Calculate mid price."""
        if self.best_bid and self.best_ask:
            return (self.best_bid.price + self.best_ask.price) / 2
        return None

    @property
    def spread(self) -> Optional[Decimal]:
        """Calculate absolute spread."""
        if self.best_bid and self.best_ask:
            return self.best_ask.price - self.best_bid.price
        return None

    @property
    def spread_bps(self) -> Optional[Decimal]:
        """Calculate spread in basis points."""
        mid = self.mid_price
        spread = self.spread
        if mid and spread and mid > 0:
            return (spread / mid) * Decimal('10000')
        return None


@dataclass
class OrderBookDelta:
    """Incremental order book update."""
    exchange: str
    symbol: str
    timestamp_us: int
    sequence: int
    bids: List[PriceLevel]  # Updates to bid side
    asks: List[PriceLevel]  # Updates to ask side
    first_update_id: int  # For Binance sequencing
    final_update_id: int  # For Binance sequencing


@dataclass
class Trade:
    """Individual trade/execution."""
    exchange: str
    symbol: str
    timestamp_us: int
    price: Decimal
    quantity: Decimal
    side: Literal["buy", "sell"]  # Aggressor side
    trade_id: str

    @property
    def value(self) -> Decimal:
        """Calculate trade value (price * quantity)."""
        return self.price * self.quantity