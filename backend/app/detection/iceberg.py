"""Iceberg order detection.

Detects large orders split into smaller visible portions that replenish at same price.
"""

from collections import defaultdict
from decimal import Decimal
from typing import Optional, List, Dict, Tuple
from datetime import datetime

from .base import BaseDetector
from .models import Alert
from ..models.market_data import OrderBookSnapshot, Trade


class IcebergDetector(BaseDetector):
    """
    Detect iceberg orders: repeated fills at the same price
    with consistent replenishment.
    """

    def __init__(self,
                 exchange: str,
                 symbol: str,
                 min_repeats: int = 3,
                 price_tolerance: Decimal = Decimal('0'),
                 size_consistency_threshold: float = 0.2,
                 time_window_ms: int = 60000):
        super().__init__(exchange, symbol)
        self.min_repeats = min_repeats
        self.price_tolerance = price_tolerance
        self.size_consistency_threshold = size_consistency_threshold
        self.time_window_ms = time_window_ms

        # Track fill history: price -> [(timestamp_ms, quantity), ...]
        self.fill_history: Dict[Decimal, List[Tuple[int, Decimal]]] = defaultdict(list)

    def on_trade(self, timestamp_ms: int, price: Decimal, quantity: Decimal) -> Optional[Dict]:
        """Process a trade and check for iceberg pattern."""
        self.fill_history[price].append((timestamp_ms, quantity))

        # Check for iceberg pattern at this price
        fills = self.fill_history[price]

        # Only look at recent fills (within time window)
        recent = [(ts, qty) for ts, qty in fills
                 if timestamp_ms - ts < self.time_window_ms]

        if len(recent) < self.min_repeats:
            return None

        # Check for consistent size (within tolerance)
        quantities = [float(qty) for _, qty in recent]
        avg_qty = sum(quantities) / len(quantities)

        consistent = all(
            abs(q - avg_qty) / avg_qty < self.size_consistency_threshold
            for q in quantities
        )

        if consistent and len(recent) >= self.min_repeats:
            return {
                'detected': True,
                'price': price,
                'visible_size': avg_qty,
                'estimated_total': avg_qty * len(recent),  # Lower bound estimate
                'num_refills': len(recent),
                'still_active': True,  # Assume active if recent
                'time_span_ms': timestamp_ms - recent[0][0]
            }

        return None

    def detect(self,
               book_snapshot: Optional[OrderBookSnapshot] = None,
               trades: Optional[List[Trade]] = None,
               order_events: Optional[List] = None) -> Optional[Alert]:
        """Detect iceberg orders from trade data."""
        if not trades:
            return None

        icebergs_detected = []
        current_time_ms = int(datetime.utcnow().timestamp() * 1000)

        # Process all trades
        for trade in trades:
            timestamp_ms = int(trade.timestamp.timestamp() * 1000)
            iceberg = self.on_trade(timestamp_ms, trade.price, trade.quantity)
            if iceberg:
                icebergs_detected.append(iceberg)

        # Clean up old fill history
        prices_to_clean = []
        for price, fills in self.fill_history.items():
            # Remove old fills
            self.fill_history[price] = [(ts, qty) for ts, qty in fills
                                       if current_time_ms - ts < self.time_window_ms * 2]
            if not self.fill_history[price]:
                prices_to_clean.append(price)

        for price in prices_to_clean:
            del self.fill_history[price]

        # Return alert for the most significant iceberg
        if icebergs_detected:
            # Sort by estimated total size (largest first)
            icebergs_detected.sort(key=lambda i: i['estimated_total'], reverse=True)
            iceberg = icebergs_detected[0]

            # Determine severity based on number of refills and estimated size
            if iceberg['num_refills'] >= 10:
                severity = 'warning'
            elif iceberg['num_refills'] >= 5:
                severity = 'info'
            else:
                severity = 'info'

            # Calculate confidence based on pattern consistency
            confidence = min(1.0, (iceberg['num_refills'] / 10) * 0.7 + 0.3)

            context = {
                'price': str(iceberg['price']),
                'visible_size': round(iceberg['visible_size'], 4),
                'estimated_total': round(iceberg['estimated_total'], 2),
                'num_refills': iceberg['num_refills'],
                'time_span_seconds': iceberg['time_span_ms'] / 1000,
                'still_active': iceberg['still_active']
            }

            explanation = (f"Detected iceberg order at {iceberg['price']}: "
                         f"{iceberg['num_refills']} fills of ~{iceberg['visible_size']:.4f} each "
                         f"over {iceberg['time_span_ms']/1000:.0f}s. "
                         f"Estimated total size: {iceberg['estimated_total']:.2f}")

            return self.create_alert(
                pattern='iceberg',
                severity=severity,
                confidence=confidence,
                context=context,
                explanation=explanation
            )

        return None