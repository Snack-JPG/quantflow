"""Spoofing pattern detection.

Detects large orders placed and rapidly cancelled to manipulate price perception.
"""

from collections import defaultdict
from decimal import Decimal
from typing import Optional, List, Dict, Tuple
from datetime import datetime, timedelta

from .base import BaseDetector
from .models import Alert, OrderEvent
from ..models.market_data import OrderBookSnapshot, Trade


class SpoofingDetector(BaseDetector):
    """
    Detect spoofing: large orders placed and rapidly cancelled.

    Signals:
    - Large order relative to typical size at that level
    - Short lifespan (placed and cancelled within threshold)
    - Repeated pattern by same participant (if identifiable)
    - Price moved in favorable direction during order's lifespan
    """

    def __init__(self,
                 exchange: str,
                 symbol: str,
                 cancel_window_ms: int = 2000,      # Max time before cancel for suspicion
                 size_multiple: float = 3.0,        # Size vs average to flag
                 min_pattern_count: int = 3,        # Minimum occurrences to flag
                 lookback_minutes: int = 5):
        super().__init__(exchange, symbol)
        self.cancel_window_ms = cancel_window_ms
        self.size_multiple = size_multiple
        self.min_pattern_count = min_pattern_count
        self.lookback_ms = lookback_minutes * 60 * 1000

        self.active_orders: Dict[Tuple[Decimal, str], Tuple[int, Decimal]] = {}
        self.avg_level_size: Dict[Tuple[Decimal, str], float] = {}
        self.spoof_candidates = []
        self.last_mid_price = None

    def on_order_placed(self, event: OrderEvent):
        """Track order placement."""
        key = (event.price, event.side)
        self.active_orders[key] = (event.timestamp_ms, event.quantity)

        # Update average size at this level (exponential moving average)
        if key not in self.avg_level_size:
            self.avg_level_size[key] = float(event.quantity)
        else:
            alpha = 0.05
            self.avg_level_size[key] = (
                alpha * float(event.quantity) +
                (1 - alpha) * self.avg_level_size[key]
            )

    def on_order_cancelled(self, event: OrderEvent, mid_price: Optional[Decimal] = None) -> Optional[Dict]:
        """Check if cancellation matches spoofing pattern."""
        key = (event.price, event.side)

        if key not in self.active_orders:
            return None

        place_ts, place_qty = self.active_orders.pop(key)
        lifespan_ms = event.timestamp_ms - place_ts

        avg_size = self.avg_level_size.get(key, float(place_qty))
        size_ratio = float(place_qty) / avg_size if avg_size > 0 else 1.0

        # Check if price moved favorably during order lifespan
        price_moved_favorably = False
        if self.last_mid_price and mid_price:
            if event.side == 'ask':
                # Sell order - favorable if price went down (inducing others to sell)
                price_moved_favorably = mid_price < self.last_mid_price
            else:
                # Buy order - favorable if price went up (inducing others to buy)
                price_moved_favorably = mid_price > self.last_mid_price

        # Spoofing criteria
        is_suspicious = (
            lifespan_ms < self.cancel_window_ms and
            size_ratio > self.size_multiple and
            (price_moved_favorably or lifespan_ms < 1000)  # Very fast cancel is suspicious regardless
        )

        if is_suspicious:
            candidate = {
                'timestamp': event.timestamp_ms,
                'price': event.price,
                'quantity': place_qty,
                'side': event.side,
                'lifespan_ms': lifespan_ms,
                'size_ratio': size_ratio,
            }
            self.spoof_candidates.append(candidate)
            return candidate

        return None

    def get_spoof_score(self) -> float:
        """Calculate 0-1 score of current spoofing likelihood."""
        if not self.spoof_candidates:
            return 0.0

        current_time = self.spoof_candidates[-1]['timestamp']
        recent = [
            c for c in self.spoof_candidates
            if c['timestamp'] > (current_time - self.lookback_ms)
        ]

        if len(recent) < self.min_pattern_count:
            return 0.0

        # Score based on frequency and size
        return min(1.0, len(recent) / (self.min_pattern_count * 3))

    def detect(self,
               book_snapshot: Optional[OrderBookSnapshot] = None,
               trades: Optional[List[Trade]] = None,
               order_events: Optional[List[OrderEvent]] = None) -> Optional[Alert]:
        """
        Detect spoofing patterns in order events.
        """
        if not order_events:
            return None

        # Update mid price if we have book snapshot
        if book_snapshot and book_snapshot.bids and book_snapshot.asks:
            self.last_mid_price = (book_snapshot.bids[0].price + book_snapshot.asks[0].price) / 2

        detected_spoofs = []

        for event in order_events:
            if event.event_type == 'place':
                self.on_order_placed(event)
            elif event.event_type == 'cancel':
                spoof = self.on_order_cancelled(event, self.last_mid_price)
                if spoof:
                    detected_spoofs.append(spoof)

        # Check if we have enough evidence for spoofing
        score = self.get_spoof_score()

        if score > 0.3 and len(detected_spoofs) > 0:  # Threshold for alert
            latest_spoof = detected_spoofs[-1]

            # Determine severity based on score and pattern count
            if score > 0.8:
                severity = 'critical'
            elif score > 0.5:
                severity = 'warning'
            else:
                severity = 'info'

            context = {
                'spoof_count': len([c for c in self.spoof_candidates
                                   if c['timestamp'] > (latest_spoof['timestamp'] - self.lookback_ms)]),
                'avg_lifespan_ms': sum(s['lifespan_ms'] for s in detected_spoofs) / len(detected_spoofs),
                'avg_size_ratio': sum(s['size_ratio'] for s in detected_spoofs) / len(detected_spoofs),
                'latest_side': latest_spoof['side'],
                'latest_price': str(latest_spoof['price']),
                'latest_quantity': str(latest_spoof['quantity'])
            }

            explanation = (f"Detected spoofing pattern: {context['spoof_count']} large orders "
                         f"(avg {context['avg_size_ratio']:.1f}x normal size) placed and cancelled "
                         f"within {context['avg_lifespan_ms']:.0f}ms on the {latest_spoof['side']} side. "
                         f"Latest: {latest_spoof['quantity']} @ {latest_spoof['price']}")

            return self.create_alert(
                pattern='spoofing',
                severity=severity,
                confidence=score,
                context=context,
                explanation=explanation
            )

        return None