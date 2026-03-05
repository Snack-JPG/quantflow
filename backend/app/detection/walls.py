"""Order book walls detection.

Detects single price levels with abnormally large quantity that persists.
"""

from decimal import Decimal
from typing import Optional, List, Dict, Tuple
from datetime import datetime
import statistics

from .base import BaseDetector
from .models import Alert
from ..models.market_data import OrderBookSnapshot, Trade, PriceLevel


class WallsDetector(BaseDetector):
    """
    Detect walls: single price level with >3σ quantity vs mean level size,
    persisting for >30 seconds.
    """

    def __init__(self,
                 exchange: str,
                 symbol: str,
                 sigma_threshold: float = 3.0,
                 min_persistence_ms: int = 30000,
                 depth_levels: int = 20):
        super().__init__(exchange, symbol)
        self.sigma_threshold = sigma_threshold
        self.min_persistence_ms = min_persistence_ms
        self.depth_levels = depth_levels

        # Track wall candidates over time
        self.wall_candidates: Dict[Tuple[str, Decimal], Dict] = {}  # (side, price) -> wall info

    def detect(self,
               book_snapshot: Optional[OrderBookSnapshot] = None,
               trades: Optional[List[Trade]] = None,
               order_events: Optional[List] = None) -> Optional[Alert]:
        """Detect wall patterns in order book."""
        if not book_snapshot:
            return None

        current_time_ms = int(datetime.utcnow().timestamp() * 1000)
        walls_found = []

        # Check both bid and ask sides
        for side, levels in [('bid', book_snapshot.bids[:self.depth_levels]),
                            ('ask', book_snapshot.asks[:self.depth_levels])]:
            if len(levels) < 5:  # Need enough levels for statistics
                continue

            # Calculate statistics for normal level sizes
            quantities = [float(level.quantity) for level in levels]
            if not quantities:
                continue

            mean_qty = statistics.mean(quantities)
            if len(quantities) > 1:
                stdev_qty = statistics.stdev(quantities)
            else:
                stdev_qty = 0

            if stdev_qty == 0:  # All same size, no walls
                continue

            # Check each level for wall pattern
            for level in levels:
                qty = float(level.quantity)
                z_score = (qty - mean_qty) / stdev_qty if stdev_qty > 0 else 0

                if z_score > self.sigma_threshold:
                    key = (side, level.price)

                    if key in self.wall_candidates:
                        # Update existing wall candidate
                        wall = self.wall_candidates[key]
                        wall['last_seen_ms'] = current_time_ms
                        wall['quantity'] = level.quantity
                        wall['z_score'] = z_score

                        # Check if wall has persisted long enough
                        duration = current_time_ms - wall['first_seen_ms']
                        if duration >= self.min_persistence_ms:
                            wall['duration_ms'] = duration
                            walls_found.append(wall)
                    else:
                        # New wall candidate
                        self.wall_candidates[key] = {
                            'side': side,
                            'price': level.price,
                            'quantity': level.quantity,
                            'z_score': z_score,
                            'first_seen_ms': current_time_ms,
                            'last_seen_ms': current_time_ms,
                            'mean_qty': mean_qty,
                            'stdev_qty': stdev_qty
                        }

        # Clean up old candidates that are no longer visible
        keys_to_remove = []
        for key, wall in self.wall_candidates.items():
            if current_time_ms - wall['last_seen_ms'] > 5000:  # Not seen for 5 seconds
                keys_to_remove.append(key)
        for key in keys_to_remove:
            del self.wall_candidates[key]

        # Return alert for the most significant wall
        if walls_found:
            # Sort by z-score (most significant first)
            walls_found.sort(key=lambda w: w['z_score'], reverse=True)
            wall = walls_found[0]

            # Determine severity based on z-score and duration
            if wall['z_score'] > 5 and wall['duration_ms'] > 60000:
                severity = 'critical'
            elif wall['z_score'] > 4 or wall['duration_ms'] > 45000:
                severity = 'warning'
            else:
                severity = 'info'

            # Calculate confidence
            confidence = min(1.0, (wall['z_score'] / 10) * 0.7 +
                           (min(wall['duration_ms'], 120000) / 120000) * 0.3)

            context = {
                'side': wall['side'],
                'price': str(wall['price']),
                'quantity': str(wall['quantity']),
                'z_score': round(wall['z_score'], 2),
                'duration_seconds': wall['duration_ms'] / 1000,
                'mean_level_size': round(wall['mean_qty'], 2),
                'stdev_level_size': round(wall['stdev_qty'], 2)
            }

            explanation = (f"Detected {wall['side']} wall at {wall['price']}: "
                         f"quantity {wall['quantity']} is {wall['z_score']:.1f}σ above mean "
                         f"({wall['mean_qty']:.2f}), persisting for {wall['duration_ms']/1000:.0f}s")

            return self.create_alert(
                pattern='walls',
                severity=severity,
                confidence=confidence,
                context=context,
                explanation=explanation
            )

        return None