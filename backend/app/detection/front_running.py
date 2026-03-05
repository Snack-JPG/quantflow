"""Front-running detection.

Detects large orders appearing, small orders executing ahead, then large order moving price.
"""

from collections import deque
from decimal import Decimal
from typing import Optional, List, Dict
from datetime import datetime
import statistics

from .base import BaseDetector
from .models import Alert
from ..models.market_data import OrderBookSnapshot, Trade


class FrontRunningDetector(BaseDetector):
    """
    Detect potential front-running: small trades appearing
    just before large trades in the same direction.
    """

    def __init__(self,
                 exchange: str,
                 symbol: str,
                 leader_window_ms: int = 100,
                 size_ratio: float = 10.0,
                 min_leaders: int = 2):
        super().__init__(exchange, symbol)
        self.leader_window_ms = leader_window_ms
        self.size_ratio = size_ratio
        self.min_leaders = min_leaders

        self.recent_trades = deque(maxlen=1000)
        self.avg_size = None
        self.large_trade_threshold = None

    def update_avg_size(self, qty: float):
        """Update average trade size."""
        if self.avg_size is None:
            self.avg_size = qty
        else:
            # Exponential moving average
            self.avg_size = 0.05 * qty + 0.95 * self.avg_size

        # Update large trade threshold
        self.large_trade_threshold = self.avg_size * self.size_ratio

    def on_trade(self, timestamp_ms: int, price: float,
                 qty: float, is_buy: bool) -> Optional[Dict]:
        """Process trade and check for front-running pattern."""
        self.recent_trades.append((timestamp_ms, price, qty, is_buy))
        self.update_avg_size(qty)

        if self.avg_size is None or self.large_trade_threshold is None:
            return None

        # Check if this is a "large" trade that might have been front-run
        if qty > self.large_trade_threshold:
            # Look for small trades in same direction just before
            leaders = [
                (ts, p, q) for ts, p, q, b in self.recent_trades
                if b == is_buy
                and timestamp_ms - ts <= self.leader_window_ms
                and timestamp_ms - ts > 0
                and q < self.avg_size  # Small trade
            ]

            if len(leaders) >= self.min_leaders:
                # Calculate aggregate leader statistics
                leader_volume = sum(q for _, _, q in leaders)
                leader_avg_price = sum(p * q for _, p, q in leaders) / leader_volume
                lead_time_ms = timestamp_ms - leaders[0][0]

                # Check if leaders got better price
                if is_buy:
                    # For buy orders, leaders should have bought cheaper
                    price_advantage = price - leader_avg_price
                else:
                    # For sell orders, leaders should have sold higher
                    price_advantage = leader_avg_price - price

                if price_advantage > 0:
                    return {
                        'detected': True,
                        'large_trade_size': qty,
                        'large_trade_price': price,
                        'is_buy': is_buy,
                        'leader_count': len(leaders),
                        'leader_total_size': leader_volume,
                        'leader_avg_price': leader_avg_price,
                        'price_advantage': price_advantage,
                        'lead_time_ms': lead_time_ms
                    }

        return None

    def detect(self,
               book_snapshot: Optional[OrderBookSnapshot] = None,
               trades: Optional[List[Trade]] = None,
               order_events: Optional[List] = None) -> Optional[Alert]:
        """Detect front-running patterns from trades."""
        if not trades:
            return None

        front_running_detected = None

        # Process all trades
        for trade in trades:
            timestamp_ms = int(trade.timestamp.timestamp() * 1000)
            is_buy = trade.side == 'buy'
            result = self.on_trade(timestamp_ms, float(trade.price),
                                 float(trade.quantity), is_buy)
            if result and result.get('detected'):
                front_running_detected = result

        if front_running_detected:
            # Determine severity based on price advantage and volume
            price_adv_bps = (front_running_detected['price_advantage'] /
                           front_running_detected['large_trade_price'] * 10000)

            if price_adv_bps > 10 or front_running_detected['leader_count'] >= 5:
                severity = 'critical'
            elif price_adv_bps > 5 or front_running_detected['leader_count'] >= 3:
                severity = 'warning'
            else:
                severity = 'info'

            # Calculate confidence
            confidence = min(1.0,
                           (front_running_detected['leader_count'] / 5) * 0.5 +
                           (min(price_adv_bps, 20) / 20) * 0.5)

            side = 'buy' if front_running_detected['is_buy'] else 'sell'

            context = {
                'large_trade_size': round(front_running_detected['large_trade_size'], 4),
                'large_trade_price': round(front_running_detected['large_trade_price'], 6),
                'side': side,
                'leader_count': front_running_detected['leader_count'],
                'leader_total_size': round(front_running_detected['leader_total_size'], 4),
                'leader_avg_price': round(front_running_detected['leader_avg_price'], 6),
                'price_advantage': round(front_running_detected['price_advantage'], 6),
                'price_advantage_bps': round(price_adv_bps, 2),
                'lead_time_ms': front_running_detected['lead_time_ms'],
                'avg_trade_size': round(self.avg_size, 4)
            }

            explanation = (f"Detected potential front-running: "
                         f"{front_running_detected['leader_count']} small {side} orders "
                         f"(total {front_running_detected['leader_total_size']:.4f}) "
                         f"executed {front_running_detected['lead_time_ms']}ms before "
                         f"large {side} order ({front_running_detected['large_trade_size']:.4f}). "
                         f"Leaders got {price_adv_bps:.2f} bps better price")

            return self.create_alert(
                pattern='front_running',
                severity=severity,
                confidence=confidence,
                context=context,
                explanation=explanation
            )

        return None