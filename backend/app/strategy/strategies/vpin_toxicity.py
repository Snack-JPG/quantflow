"""
VPIN (Volume-Synchronized Probability of Informed Trading) Toxicity Fade Strategy.

This strategy uses VPIN to measure order flow toxicity and trade in the direction
of informed flow. High VPIN indicates toxic/informed flow that we should follow,
not fade.
"""
from typing import List, Dict, Any, Optional
from decimal import Decimal
from datetime import datetime
from collections import deque
import numpy as np

from ..base import Strategy
from ..models import (
    OrderBookSnapshot,
    Trade,
    Alert,
    Signal,
    SignalDirection,
    OrderSide
)


class VPINToxicityStrategy(Strategy):
    """
    VPIN Toxicity Fade Strategy.

    When VPIN is high (toxic flow), follow the direction of the flow.
    The strategy assumes informed traders move the market.

    Parameters:
    - volume_bucket_size: Size of volume buckets (default 100 BTC)
    - num_buckets: Number of buckets for VPIN calculation (default 50)
    - vpin_threshold: VPIN threshold to trigger signal (default 0.7)
    - momentum_periods: Periods to measure price momentum (default 10)
    - exit_on_vpin_drop: Exit when VPIN drops below threshold (default True)
    """

    def __init__(
        self,
        name: str = "VPIN_Toxicity",
        symbols: List[str] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """Initialize VPIN Toxicity strategy."""
        super().__init__(name, symbols or ['BTCUSDT'], config)

        # Strategy parameters
        self.volume_bucket_size = Decimal(str(self.config.get('volume_bucket_size', 100)))
        self.num_buckets = self.config.get('num_buckets', 50)
        self.vpin_threshold = self.config.get('vpin_threshold', 0.7)
        self.momentum_periods = self.config.get('momentum_periods', 10)
        self.exit_on_vpin_drop = self.config.get('exit_on_vpin_drop', True)

        # VPIN calculation state
        self.volume_buckets: Dict[str, deque] = {}
        self.current_bucket_volume: Dict[str, Decimal] = {}
        self.current_bucket_imbalance: Dict[str, Decimal] = {}
        self.price_history: Dict[str, deque] = {}
        self.vpin_history: Dict[str, deque] = {}

        # Position tracking
        self.entry_vpin: Dict[str, float] = {}

        # Initialize state
        for symbol in self.symbols:
            self.volume_buckets[symbol] = deque(maxlen=self.num_buckets)
            self.current_bucket_volume[symbol] = Decimal('0')
            self.current_bucket_imbalance[symbol] = Decimal('0')
            self.price_history[symbol] = deque(maxlen=self.momentum_periods)
            self.vpin_history[symbol] = deque(maxlen=20)

    def on_trade(self, trade: Trade) -> List[Signal]:
        """Handle trade event - main driver for VPIN calculation."""
        signals = []
        symbol = trade.symbol

        # Update last trade
        self.last_trade[symbol] = trade

        # Classify trade as buy or sell volume
        # Using tick rule: compare to previous trade price
        buy_volume = Decimal('0')
        sell_volume = Decimal('0')

        if len(self.price_history[symbol]) > 0:
            prev_price = self.price_history[symbol][-1]
            if trade.price > prev_price:
                buy_volume = trade.quantity
            elif trade.price < prev_price:
                sell_volume = trade.quantity
            else:
                # Price unchanged, use aggressor side
                if trade.side == OrderSide.BUY:
                    buy_volume = trade.quantity
                else:
                    sell_volume = trade.quantity
        else:
            # First trade, use aggressor side
            if trade.side == OrderSide.BUY:
                buy_volume = trade.quantity
            else:
                sell_volume = trade.quantity

        # Update price history
        self.price_history[symbol].append(trade.price)

        # Update current bucket
        self.current_bucket_volume[symbol] += trade.quantity
        self.current_bucket_imbalance[symbol] += (buy_volume - sell_volume)

        # Check if bucket is full
        if self.current_bucket_volume[symbol] >= self.volume_bucket_size:
            # Calculate bucket order imbalance
            imbalance = abs(self.current_bucket_imbalance[symbol])

            # Add to bucket history
            self.volume_buckets[symbol].append(imbalance)

            # Reset current bucket
            overflow = self.current_bucket_volume[symbol] - self.volume_bucket_size
            self.current_bucket_volume[symbol] = overflow
            self.current_bucket_imbalance[symbol] = Decimal('0')

            # Calculate VPIN if we have enough buckets
            if len(self.volume_buckets[symbol]) >= self.num_buckets:
                vpin = self._calculate_vpin(symbol)
                self.vpin_history[symbol].append(vpin)

                # Generate trading signals
                signals.extend(self._generate_vpin_signals(symbol, vpin, trade))

        return signals

    def on_book_update(self, book: OrderBookSnapshot) -> List[Signal]:
        """Handle order book update."""
        # Store last book for reference
        self.last_book[book.symbol] = book

        # Could use book imbalance to confirm VPIN signals
        return []

    def on_alert(self, alert: Alert) -> List[Signal]:
        """Handle pattern detection alert."""
        # Could use alerts to enhance VPIN interpretation
        return []

    def _calculate_vpin(self, symbol: str) -> float:
        """
        Calculate VPIN metric.

        VPIN = Σ|Order Imbalance| / Σ(Total Volume)
        """
        if not self.volume_buckets[symbol]:
            return 0.0

        total_imbalance = sum(self.volume_buckets[symbol])
        total_volume = self.volume_bucket_size * len(self.volume_buckets[symbol])

        if total_volume == 0:
            return 0.0

        return float(total_imbalance / total_volume)

    def _calculate_momentum(self, symbol: str) -> float:
        """Calculate price momentum."""
        if len(self.price_history[symbol]) < 2:
            return 0.0

        prices = list(self.price_history[symbol])
        returns = [(prices[i] - prices[i-1]) / prices[i-1]
                  for i in range(1, len(prices))]

        if not returns:
            return 0.0

        return sum(float(r) for r in returns) / len(returns)

    def _generate_vpin_signals(
        self,
        symbol: str,
        vpin: float,
        trade: Trade
    ) -> List[Signal]:
        """Generate signals based on VPIN and market conditions."""
        signals = []

        # Calculate price momentum
        momentum = self._calculate_momentum(symbol)

        # Check for existing position
        if self.has_position(symbol):
            position = self.get_position(symbol)

            # Exit conditions
            should_exit = False
            exit_reason = ""

            if self.exit_on_vpin_drop and vpin < self.vpin_threshold * 0.7:
                should_exit = True
                exit_reason = f"VPIN dropped below threshold ({vpin:.3f})"

            # Exit if momentum reverses strongly
            if position.side == OrderSide.BUY and momentum < -0.002:
                should_exit = True
                exit_reason = "Momentum reversed bearish"
            elif position.side == OrderSide.SELL and momentum > 0.002:
                should_exit = True
                exit_reason = "Momentum reversed bullish"

            if should_exit:
                signal = self.generate_signal(
                    symbol=symbol,
                    direction=SignalDirection.CLOSE,
                    strength=1.0,
                    reason=f"Exit: {exit_reason}",
                    vpin=vpin,
                    momentum=momentum
                )
                signals.append(signal)

                # Clean up state
                if symbol in self.entry_vpin:
                    del self.entry_vpin[symbol]

        else:
            # Entry signals - follow toxic flow
            if vpin > self.vpin_threshold:
                # High VPIN - toxic/informed flow detected
                # Trade in direction of momentum (follow informed traders)

                if momentum > 0.001:  # Bullish momentum
                    signal = self.generate_signal(
                        symbol=symbol,
                        direction=SignalDirection.LONG,
                        strength=min(1.0, vpin),  # Scale by VPIN level
                        reason=f"High VPIN ({vpin:.3f}) with bullish momentum - following informed flow",
                        vpin=vpin,
                        momentum=momentum,
                        last_price=float(trade.price)
                    )
                    signals.append(signal)
                    self.entry_vpin[symbol] = vpin

                elif momentum < -0.001:  # Bearish momentum
                    signal = self.generate_signal(
                        symbol=symbol,
                        direction=SignalDirection.SHORT,
                        strength=min(1.0, vpin),
                        reason=f"High VPIN ({vpin:.3f}) with bearish momentum - following informed flow",
                        vpin=vpin,
                        momentum=momentum,
                        last_price=float(trade.price)
                    )
                    signals.append(signal)
                    self.entry_vpin[symbol] = vpin

        return signals

    def reset(self):
        """Reset strategy state."""
        super().reset()

        # Clear all state
        self.volume_buckets.clear()
        self.current_bucket_volume.clear()
        self.current_bucket_imbalance.clear()
        self.price_history.clear()
        self.vpin_history.clear()
        self.entry_vpin.clear()

        # Reinitialize
        for symbol in self.symbols:
            self.volume_buckets[symbol] = deque(maxlen=self.num_buckets)
            self.current_bucket_volume[symbol] = Decimal('0')
            self.current_bucket_imbalance[symbol] = Decimal('0')
            self.price_history[symbol] = deque(maxlen=self.momentum_periods)
            self.vpin_history[symbol] = deque(maxlen=20)