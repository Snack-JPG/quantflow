"""Layering pattern detection.

Detects multiple orders placed at different price levels, all cancelled together.
"""

from decimal import Decimal
from typing import Optional, List, Set, Dict, Any
from datetime import datetime

from .base import BaseDetector
from .models import Alert, OrderEvent
from ..models.market_data import OrderBookSnapshot, Trade


class LayeringDetector(BaseDetector):
    """
    Detect layering: coordinated placement and cancellation of
    multiple orders at different price levels.
    """

    def __init__(self,
                 exchange: str,
                 symbol: str,
                 min_layers: int = 3,
                 sync_window_ms: int = 500):
        super().__init__(exchange, symbol)
        self.min_layers = min_layers
        self.sync_window_ms = sync_window_ms
        self.order_groups = []  # groups of orders placed close together
        self.current_group = []
        self.last_event_ts = 0
        self.active_orders = {}  # Track all active orders by price

    def on_order_placed(self, timestamp_ms: int, price: Decimal,
                       qty: Decimal, side: str):
        """Group orders placed within sync window."""
        # Check if this is part of a new group
        if timestamp_ms - self.last_event_ts > self.sync_window_ms:
            if len(self.current_group) >= self.min_layers:
                self.order_groups.append(list(self.current_group))
            self.current_group = []

        self.current_group.append({
            'ts': timestamp_ms,
            'price': price,
            'qty': qty,
            'side': side,
            'cancelled': False
        })
        self.last_event_ts = timestamp_ms

        # Track active order
        key = (price, side)
        if key not in self.active_orders:
            self.active_orders[key] = []
        self.active_orders[key].append({
            'ts': timestamp_ms,
            'qty': qty
        })

    def on_orders_cancelled(self, timestamp_ms: int,
                           cancelled_prices: Set[Decimal],
                           side: str) -> Optional[Dict]:
        """Check if cancelled orders match a placed group."""
        # Clean up active orders
        for price in cancelled_prices:
            key = (price, side)
            if key in self.active_orders:
                del self.active_orders[key]

        # Check against our grouped orders
        for group in self.order_groups:
            group_prices = {o['price'] for o in group if o['side'] == side}
            overlap = group_prices & cancelled_prices

            if len(overlap) >= self.min_layers:
                # Check they're all on same side and at different prices
                prices = sorted(overlap)
                if len(prices) >= self.min_layers:
                    # Calculate the time since placement
                    avg_placement_time = sum(o['ts'] for o in group if o['price'] in overlap) / len(overlap)
                    duration_ms = timestamp_ms - avg_placement_time

                    return {
                        'detected': True,
                        'side': side,
                        'num_layers': len(prices),
                        'price_range': (min(prices), max(prices)),
                        'timestamp': timestamp_ms,
                        'duration_ms': duration_ms
                    }
        return None

    def detect(self,
               book_snapshot: Optional[OrderBookSnapshot] = None,
               trades: Optional[List[Trade]] = None,
               order_events: Optional[List[OrderEvent]] = None) -> Optional[Alert]:
        """Detect layering patterns in order events."""
        if not order_events:
            return None

        layering_detected = None
        cancelled_by_side = {'bid': set(), 'ask': set()}

        for event in order_events:
            if event.event_type == 'place':
                self.on_order_placed(event.timestamp_ms, event.price,
                                   event.quantity, event.side)
            elif event.event_type == 'cancel':
                # Accumulate cancellations by side
                cancelled_by_side[event.side].add(event.price)

        # Check for layering patterns in cancellations
        for side, cancelled_prices in cancelled_by_side.items():
            if len(cancelled_prices) >= self.min_layers:
                # Get the latest timestamp from events
                latest_ts = max(e.timestamp_ms for e in order_events
                              if e.event_type == 'cancel' and e.side == side)
                detection = self.on_orders_cancelled(latest_ts, cancelled_prices, side)
                if detection and detection.get('detected'):
                    layering_detected = detection
                    break

        if layering_detected:
            num_layers = layering_detected['num_layers']
            side = layering_detected['side']
            price_min, price_max = layering_detected['price_range']
            duration_ms = layering_detected.get('duration_ms', 0)

            # Determine severity based on number of layers
            if num_layers >= 10:
                severity = 'critical'
            elif num_layers >= 5:
                severity = 'warning'
            else:
                severity = 'info'

            # Calculate confidence based on pattern clarity
            confidence = min(1.0, (num_layers / 10) * 0.8 + 0.2)

            context = {
                'num_layers': num_layers,
                'side': side,
                'price_range_min': str(price_min),
                'price_range_max': str(price_max),
                'duration_ms': duration_ms
            }

            explanation = (f"Detected layering pattern: {num_layers} orders placed "
                         f"at sequential price levels on {side} side "
                         f"from {price_min} to {price_max}, "
                         f"all cancelled together after {duration_ms:.0f}ms")

            return self.create_alert(
                pattern='layering',
                severity=severity,
                confidence=confidence,
                context=context,
                explanation=explanation
            )

        return None