"""Tape painting detection.

Detects small trades at progressively higher/lower prices to create false trend appearance.
"""

from collections import deque
from decimal import Decimal
from typing import Optional, List, Dict
from datetime import datetime

from .base import BaseDetector
from .models import Alert
from ..models.market_data import OrderBookSnapshot, Trade


class TapePaintingDetector(BaseDetector):
    """
    Detect tape painting: sequential small trades at
    monotonically increasing/decreasing prices.
    """

    def __init__(self,
                 exchange: str,
                 symbol: str,
                 min_streak: int = 5,
                 max_trade_size_pct: float = 0.01,
                 price_increment_threshold: float = 0.0001):
        super().__init__(exchange, symbol)
        self.min_streak = min_streak
        self.max_trade_size_pct = max_trade_size_pct
        self.price_increment_threshold = price_increment_threshold

        self.trades = deque(maxlen=200)
        self.avg_trade_size = None

    def on_trade(self, timestamp_ms: int, price: float, qty: float):
        """Process trade and update average size."""
        self.trades.append((timestamp_ms, price, qty))

        # Update average trade size (exponential moving average)
        if self.avg_trade_size is None:
            self.avg_trade_size = qty
        else:
            self.avg_trade_size = 0.01 * qty + 0.99 * self.avg_trade_size

    def detect_pattern(self) -> Optional[Dict]:
        """Detect monotonic price sequences with small trades."""
        if len(self.trades) < self.min_streak or self.avg_trade_size is None:
            return None

        recent = list(self.trades)[-self.min_streak * 2:]

        # Find monotonic sequences of small trades
        best_up_streak = []
        best_down_streak = []
        current_up_streak = []
        current_down_streak = []

        for i in range(1, len(recent)):
            ts, price, qty = recent[i]
            _, prev_price, _ = recent[i - 1]

            # Check if trade is "small" relative to average
            is_small = qty < self.avg_trade_size * self.max_trade_size_pct * 100

            if is_small and price > prev_price:
                # Upward movement with small trade
                current_up_streak.append((ts, price, qty))
                if len(current_up_streak) > len(best_up_streak):
                    best_up_streak = list(current_up_streak)
                current_down_streak = []

            elif is_small and price < prev_price:
                # Downward movement with small trade
                current_down_streak.append((ts, price, qty))
                if len(current_down_streak) > len(best_down_streak):
                    best_down_streak = list(current_down_streak)
                current_up_streak = []

            else:
                # Streak broken
                current_up_streak = []
                current_down_streak = []

        # Check if we found a significant pattern
        if len(best_up_streak) >= self.min_streak:
            start_price = recent[recent.index(best_up_streak[0]) - 1][1]
            end_price = best_up_streak[-1][1]
            return {
                'detected': True,
                'direction': 'up',
                'streak': len(best_up_streak) + 1,  # Include starting trade
                'start_price': start_price,
                'end_price': end_price,
                'price_change': end_price - start_price,
                'avg_trade_size': sum(t[2] for t in best_up_streak) / len(best_up_streak)
            }

        if len(best_down_streak) >= self.min_streak:
            start_price = recent[recent.index(best_down_streak[0]) - 1][1]
            end_price = best_down_streak[-1][1]
            return {
                'detected': True,
                'direction': 'down',
                'streak': len(best_down_streak) + 1,  # Include starting trade
                'start_price': start_price,
                'end_price': end_price,
                'price_change': end_price - start_price,
                'avg_trade_size': sum(t[2] for t in best_down_streak) / len(best_down_streak)
            }

        return None

    def detect(self,
               book_snapshot: Optional[OrderBookSnapshot] = None,
               trades: Optional[List[Trade]] = None,
               order_events: Optional[List] = None) -> Optional[Alert]:
        """Detect tape painting patterns from trades."""
        if not trades:
            return None

        # Process all trades
        for trade in trades:
            timestamp_ms = int(trade.timestamp.timestamp() * 1000)
            self.on_trade(timestamp_ms, float(trade.price), float(trade.quantity))

        # Check for painting pattern
        pattern = self.detect_pattern()

        if pattern and pattern.get('detected'):
            # Determine severity based on streak length and price impact
            if pattern['streak'] >= 10:
                severity = 'warning'
            elif pattern['streak'] >= 7:
                severity = 'info'
            else:
                severity = 'info'

            # Calculate confidence
            confidence = min(1.0, (pattern['streak'] / 15) * 0.7 + 0.3)

            context = {
                'direction': pattern['direction'],
                'streak_length': pattern['streak'],
                'start_price': round(pattern['start_price'], 6),
                'end_price': round(pattern['end_price'], 6),
                'price_change': round(pattern['price_change'], 6),
                'price_change_pct': round((pattern['price_change'] / pattern['start_price']) * 100, 4),
                'avg_trade_size': round(pattern['avg_trade_size'], 4),
                'avg_normal_size': round(self.avg_trade_size, 4),
                'size_ratio': round(pattern['avg_trade_size'] / self.avg_trade_size, 4)
            }

            explanation = (f"Detected tape painting: {pattern['streak']} consecutive small trades "
                         f"({pattern['avg_trade_size']:.4f} avg, {context['size_ratio']:.1%} of normal) "
                         f"moving price {pattern['direction']} from {pattern['start_price']:.6f} "
                         f"to {pattern['end_price']:.6f} ({context['price_change_pct']:.2f}%)")

            return self.create_alert(
                pattern='tape_painting',
                severity=severity,
                confidence=confidence,
                context=context,
                explanation=explanation
            )

        return None