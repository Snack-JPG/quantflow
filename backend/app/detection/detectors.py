"""
All pattern detection implementations
"""
from collections import defaultdict, deque
from decimal import Decimal
from typing import Optional, List, Dict, Tuple, Any
from datetime import datetime, timedelta
import statistics

from .base import BaseDetector
from .models import Alert, OrderEvent, AlertSeverity
from .spoofing import SpoofingDetector
from ..models.market_data import OrderBookSnapshot, Trade, PriceLevel


class LayeringDetector(BaseDetector):
    """
    Detect layering: coordinated placement and cancellation of
    multiple orders at different price levels.
    """

    def __init__(self,
                 exchange: str,
                 symbol: str,
                 min_layers: int = 3,
                 sync_window_ms: int = 500,
                 size_threshold: float = 2.0):
        super().__init__(exchange, symbol)
        self.min_layers = min_layers
        self.sync_window_ms = sync_window_ms
        self.size_threshold = size_threshold
        self.order_groups = []
        self.active_orders: Dict[Decimal, OrderEvent] = {}

    def detect(self,
               book_snapshot: Optional[OrderBookSnapshot] = None,
               trades: Optional[List[Trade]] = None,
               order_events: Optional[List[OrderEvent]] = None) -> Optional[Alert]:

        if not order_events:
            return None

        # Track order placements and cancellations
        placed_orders = []
        cancelled_orders = []

        for event in order_events:
            if event.event_type == 'place':
                self.active_orders[event.price] = event
                placed_orders.append(event)
            elif event.event_type == 'cancel':
                if event.price in self.active_orders:
                    cancelled_orders.append(event)
                    del self.active_orders[event.price]

        # Check for synchronized placements
        if len(placed_orders) >= self.min_layers:
            # Check if orders are at sequential price levels
            prices = sorted([float(o.price) for o in placed_orders])
            time_range = max(o.timestamp_ms for o in placed_orders) - min(o.timestamp_ms for o in placed_orders)

            if time_range < self.sync_window_ms:
                # Check for sequential price levels
                sequential = True
                for i in range(1, len(prices)):
                    if prices[i] - prices[i-1] > float(book_snapshot.bids[0].price if book_snapshot else 1) * 0.001:
                        sequential = False
                        break

                if sequential:
                    avg_qty = sum(float(o.quantity) for o in placed_orders) / len(placed_orders)
                    context = {
                        'layer_count': len(placed_orders),
                        'price_range': f"{min(prices):.2f} - {max(prices):.2f}",
                        'total_volume': sum(float(o.quantity) for o in placed_orders),
                        'avg_quantity': avg_qty,
                        'time_window_ms': time_range
                    }

                    return self.create_alert(
                        pattern='layering',
                        severity='warning',
                        confidence=0.7,
                        context=context,
                        explanation=f"Detected layering pattern: {len(placed_orders)} orders placed across "
                                  f"{len(set(prices))} price levels within {time_range}ms"
                    )

        # Check for synchronized cancellations
        if len(cancelled_orders) >= self.min_layers:
            time_range = max(o.timestamp_ms for o in cancelled_orders) - min(o.timestamp_ms for o in cancelled_orders)

            if time_range < self.sync_window_ms:
                context = {
                    'cancelled_count': len(cancelled_orders),
                    'time_window_ms': time_range
                }

                return self.create_alert(
                    pattern='layering',
                    severity='critical',
                    confidence=0.9,
                    context=context,
                    explanation=f"Detected synchronized cancellation: {len(cancelled_orders)} orders "
                                  f"cancelled within {time_range}ms"
                )

        return None


class WallDetector(BaseDetector):
    """
    Detect walls: single price level with abnormally large quantity.
    """

    def __init__(self,
                 exchange: str,
                 symbol: str,
                 sigma_threshold: float = 3.0,
                 min_persistence_ms: int = 30000):
        super().__init__(exchange, symbol)
        self.sigma_threshold = sigma_threshold
        self.min_persistence_ms = min_persistence_ms
        self.wall_tracking = {}  # price -> {'start_time', 'quantity', 'side'}

    def detect(self,
               book_snapshot: Optional[OrderBookSnapshot] = None,
               trades: Optional[List[Trade]] = None,
               order_events: Optional[List[OrderEvent]] = None) -> Optional[Alert]:

        if not book_snapshot:
            return None

        current_time = datetime.utcnow()

        # Analyze both bid and ask sides
        for side, levels in [('bid', book_snapshot.bids), ('ask', book_snapshot.asks)]:
            if not levels:
                continue

            # Calculate statistics for level quantities
            quantities = [float(level.quantity) for level in levels[:20]]  # Top 20 levels
            if len(quantities) < 5:
                continue

            mean_qty = statistics.mean(quantities)
            std_qty = statistics.stdev(quantities) if len(quantities) > 1 else 0

            if std_qty == 0:
                continue

            # Check each level for walls
            for level in levels[:10]:  # Check top 10 levels
                z_score = (float(level.quantity) - mean_qty) / std_qty

                if z_score > self.sigma_threshold:
                    # Track wall persistence
                    wall_key = (level.price, side)

                    if wall_key not in self.wall_tracking:
                        self.wall_tracking[wall_key] = {
                            'start_time': current_time,
                            'quantity': level.quantity,
                            'side': side
                        }
                    else:
                        wall_info = self.wall_tracking[wall_key]
                        persistence_ms = int((current_time - wall_info['start_time']).total_seconds() * 1000)

                        if persistence_ms > self.min_persistence_ms:
                            context = {
                                'price': str(level.price),
                                'quantity': str(level.quantity),
                                'side': side,
                                'z_score': z_score,
                                'mean_quantity': mean_qty,
                                'std_quantity': std_qty,
                                'persistence_ms': persistence_ms
                            }

                            severity = 'critical' if z_score > 5 else 'warning'
                            confidence = min(0.95, 0.3 + (z_score - 3) * 0.1)

                            return self.create_alert(
                                pattern='wall',
                                severity=severity,
                                confidence=confidence,
                                context=context,
                                explanation=f"Large {side} wall detected at {level.price}: {level.quantity} "
                                          f"({z_score:.1f}σ above mean), persisted for {persistence_ms/1000:.1f}s"
                            )

            # Clean up old walls
            cutoff_time = current_time - timedelta(minutes=5)
            self.wall_tracking = {
                k: v for k, v in self.wall_tracking.items()
                if v['start_time'] > cutoff_time
            }

        return None


class IcebergDetector(BaseDetector):
    """
    Detect iceberg orders: repeated fills at the same price
    with consistent replenishment.
    """

    def __init__(self,
                 exchange: str,
                 symbol: str,
                 min_repeats: int = 3,
                 price_tolerance: Decimal = Decimal('0')):
        super().__init__(exchange, symbol)
        self.min_repeats = min_repeats
        self.price_tolerance = price_tolerance
        self.fill_history = defaultdict(list)  # price -> [(timestamp, quantity), ...]

    def detect(self,
               book_snapshot: Optional[OrderBookSnapshot] = None,
               trades: Optional[List[Trade]] = None,
               order_events: Optional[List[OrderEvent]] = None) -> Optional[Alert]:

        if not trades:
            return None

        for trade in trades:
            # Group trades by price (with tolerance)
            matched_price = None
            for price in self.fill_history.keys():
                if abs(price - trade.price) <= self.price_tolerance:
                    matched_price = price
                    break

            if matched_price is None:
                matched_price = trade.price

            self.fill_history[matched_price].append((trade.timestamp_us, trade.quantity))

            # Check for iceberg pattern
            fills = self.fill_history[matched_price]
            if len(fills) >= self.min_repeats:
                # Check for consistent quantities
                quantities = [float(q) for _, q in fills[-self.min_repeats:]]
                avg_qty = sum(quantities) / len(quantities)
                std_qty = statistics.stdev(quantities) if len(quantities) > 1 else 0

                # Low variance in quantities suggests iceberg
                if std_qty < avg_qty * 0.2:  # Less than 20% variation
                    context = {
                        'price': str(matched_price),
                        'fill_count': len(fills),
                        'avg_quantity': avg_qty,
                        'std_quantity': std_qty,
                        'total_filled': sum(quantities)
                    }

                    return self.create_alert(
                        pattern='iceberg',
                        severity='info',
                        confidence=0.6 + min(0.3, len(fills) * 0.05),
                        context=context,
                        explanation=f"Iceberg order detected at {matched_price}: {len(fills)} fills "
                                  f"with consistent size ~{avg_qty:.2f}"
                    )

        # Clean up old fills
        current_time = trades[-1].timestamp_us if trades else 0
        cutoff_time = current_time - 300_000_000  # 5 minutes in microseconds
        for price in list(self.fill_history.keys()):
            self.fill_history[price] = [
                (ts, q) for ts, q in self.fill_history[price]
                if ts > cutoff_time
            ]
            if not self.fill_history[price]:
                del self.fill_history[price]

        return None


class MomentumIgnitionDetector(BaseDetector):
    """
    Detect momentum ignition: burst of aggressive orders in one direction.
    """

    def __init__(self,
                 exchange: str,
                 symbol: str,
                 burst_window_ms: int = 2000,
                 min_orders: int = 5,
                 volume_sigma: float = 2.0):
        super().__init__(exchange, symbol)
        self.burst_window_ms = burst_window_ms
        self.min_orders = min_orders
        self.volume_sigma = volume_sigma
        self.trade_history = deque(maxlen=1000)
        self.baseline_volumes = deque(maxlen=100)

    def detect(self,
               book_snapshot: Optional[OrderBookSnapshot] = None,
               trades: Optional[List[Trade]] = None,
               order_events: Optional[List[OrderEvent]] = None) -> Optional[Alert]:

        if not trades:
            return None

        current_time = trades[-1].timestamp_us if trades else 0

        # Add trades to history
        for trade in trades:
            self.trade_history.append(trade)

        # Calculate baseline volume (older trades)
        old_trades = [t for t in self.trade_history
                     if current_time - t.timestamp_us > self.burst_window_ms * 1000]
        if old_trades:
            baseline_vol = sum(float(t.quantity) for t in old_trades[-20:]) / min(20, len(old_trades))
            self.baseline_volumes.append(baseline_vol)

        if len(self.baseline_volumes) < 5:
            return None

        # Check for bursts in recent window
        recent_trades = [t for t in trades
                        if current_time - t.timestamp_us < self.burst_window_ms * 1000]

        if len(recent_trades) >= self.min_orders:
            # Check directionality
            buy_volume = sum(float(t.quantity) for t in recent_trades if t.side == 'buy')
            sell_volume = sum(float(t.quantity) for t in recent_trades if t.side == 'sell')
            total_volume = buy_volume + sell_volume

            # Calculate if volume is abnormal
            mean_baseline = statistics.mean(self.baseline_volumes)
            std_baseline = statistics.stdev(self.baseline_volumes) if len(self.baseline_volumes) > 1 else mean_baseline * 0.3

            if std_baseline > 0:
                z_score = (total_volume - mean_baseline) / std_baseline

                if z_score > self.volume_sigma:
                    # Strong directional bias indicates momentum ignition
                    directional_ratio = max(buy_volume, sell_volume) / total_volume if total_volume > 0 else 0

                    if directional_ratio > 0.8:  # 80% in one direction
                        direction = 'buy' if buy_volume > sell_volume else 'sell'

                        context = {
                            'trade_count': len(recent_trades),
                            'burst_window_ms': self.burst_window_ms,
                            'total_volume': total_volume,
                            'buy_volume': buy_volume,
                            'sell_volume': sell_volume,
                            'direction': direction,
                            'directional_ratio': directional_ratio,
                            'volume_z_score': z_score
                        }

                        return self.create_alert(
                            pattern='momentum_ignition',
                            severity='warning' if z_score < 3 else 'critical',
                            confidence=min(0.95, 0.5 + directional_ratio * 0.3),
                            context=context,
                            explanation=f"Momentum ignition detected: {len(recent_trades)} aggressive {direction} orders "
                                      f"in {self.burst_window_ms}ms, volume {z_score:.1f}σ above normal"
                        )

        return None


class WashTradingDetector(BaseDetector):
    """
    Detect wash trading: buy and sell at same price within short time.
    """

    def __init__(self,
                 exchange: str,
                 symbol: str,
                 time_window_ms: int = 1000,
                 price_tolerance: Decimal = Decimal('0.00001'),
                 quantity_tolerance: float = 0.1):
        super().__init__(exchange, symbol)
        self.time_window_ms = time_window_ms
        self.price_tolerance = price_tolerance
        self.quantity_tolerance = quantity_tolerance
        self.recent_trades = deque(maxlen=100)

    def detect(self,
               book_snapshot: Optional[OrderBookSnapshot] = None,
               trades: Optional[List[Trade]] = None,
               order_events: Optional[List[OrderEvent]] = None) -> Optional[Alert]:

        if not trades:
            return None

        for trade in trades:
            self.recent_trades.append(trade)

        # Look for matching buy/sell pairs
        for i, trade1 in enumerate(self.recent_trades):
            for trade2 in list(self.recent_trades)[i+1:]:
                time_diff = abs(trade1.timestamp_us - trade2.timestamp_us)

                if time_diff > self.time_window_ms * 1000:
                    continue

                # Check if trades match wash trading pattern
                price_match = abs(trade1.price - trade2.price) <= self.price_tolerance
                opposite_sides = trade1.side != trade2.side
                quantity_match = abs(float(trade1.quantity) - float(trade2.quantity)) / float(trade1.quantity) < self.quantity_tolerance

                if price_match and opposite_sides and quantity_match:
                    context = {
                        'price': str(trade1.price),
                        'quantity1': str(trade1.quantity),
                        'quantity2': str(trade2.quantity),
                        'time_diff_ms': time_diff / 1000,
                        'trade1_side': trade1.side,
                        'trade2_side': trade2.side
                    }

                    return self.create_alert(
                        pattern='wash_trading',
                        severity='warning',
                        confidence=0.75,
                        context=context,
                        explanation=f"Potential wash trade: {trade1.side} {trade1.quantity} and "
                                  f"{trade2.side} {trade2.quantity} at {trade1.price} within {time_diff/1000:.0f}ms"
                    )

        return None


class TapePaintingDetector(BaseDetector):
    """
    Detect tape painting: sequential small trades at progressively higher/lower prices.
    """

    def __init__(self,
                 exchange: str,
                 symbol: str,
                 min_sequence: int = 5,
                 max_trade_size: Decimal = Decimal('0.1'),
                 price_increment_threshold: float = 0.0001):
        super().__init__(exchange, symbol)
        self.min_sequence = min_sequence
        self.max_trade_size = max_trade_size
        self.price_increment_threshold = price_increment_threshold
        self.trade_sequence = []

    def detect(self,
               book_snapshot: Optional[OrderBookSnapshot] = None,
               trades: Optional[List[Trade]] = None,
               order_events: Optional[List[OrderEvent]] = None) -> Optional[Alert]:

        if not trades:
            return None

        for trade in trades:
            # Only consider small trades
            if trade.quantity <= self.max_trade_size:
                self.trade_sequence.append(trade)

                # Check if we have a painting pattern
                if len(self.trade_sequence) >= self.min_sequence:
                    recent = self.trade_sequence[-self.min_sequence:]
                    prices = [float(t.price) for t in recent]

                    # Check for monotonic price movement
                    increasing = all(prices[i] >= prices[i-1] for i in range(1, len(prices)))
                    decreasing = all(prices[i] <= prices[i-1] for i in range(1, len(prices)))

                    if increasing or decreasing:
                        direction = 'up' if increasing else 'down'
                        price_change = abs(prices[-1] - prices[0])
                        avg_increment = price_change / (len(prices) - 1) if len(prices) > 1 else 0

                        if avg_increment > self.price_increment_threshold:
                            context = {
                                'trade_count': len(recent),
                                'direction': direction,
                                'start_price': prices[0],
                                'end_price': prices[-1],
                                'price_change': price_change,
                                'avg_trade_size': sum(float(t.quantity) for t in recent) / len(recent)
                            }

                            return self.create_alert(
                                pattern='tape_painting',
                                severity='info',
                                confidence=0.6,
                                context=context,
                                explanation=f"Tape painting detected: {len(recent)} small trades moving price "
                                          f"{direction} from {prices[0]:.4f} to {prices[-1]:.4f}"
                            )
            else:
                # Large trade breaks the sequence
                self.trade_sequence = []

        # Keep only recent trades
        if self.trade_sequence:
            current_time = trades[-1].timestamp_us
            self.trade_sequence = [
                t for t in self.trade_sequence
                if current_time - t.timestamp_us < 60_000_000  # 1 minute
            ]

        return None


class FrontRunningDetector(BaseDetector):
    """
    Detect front-running: small orders executing ahead of large orders.
    """

    def __init__(self,
                 exchange: str,
                 symbol: str,
                 large_order_threshold: Decimal = Decimal('10'),
                 front_run_window_ms: int = 500):
        super().__init__(exchange, symbol)
        self.large_order_threshold = large_order_threshold
        self.front_run_window_ms = front_run_window_ms
        self.order_sequence = deque(maxlen=100)

    def detect(self,
               book_snapshot: Optional[OrderBookSnapshot] = None,
               trades: Optional[List[Trade]] = None,
               order_events: Optional[List[OrderEvent]] = None) -> Optional[Alert]:

        if not order_events:
            return None

        for event in order_events:
            if event.event_type == 'place':
                self.order_sequence.append(event)

        # Look for front-running pattern
        for i, order in enumerate(self.order_sequence):
            if order.quantity >= self.large_order_threshold:
                # Found large order, check for front-runners
                front_runners = []

                # Look at orders placed just before
                for j in range(max(0, i - 10), i):
                    prev_order = self.order_sequence[j]
                    time_diff = order.timestamp_ms - prev_order.timestamp_ms

                    if time_diff < self.front_run_window_ms:
                        # Same side and smaller size suggests front-running
                        if (prev_order.side == order.side and
                            prev_order.quantity < order.quantity * Decimal('0.1')):
                            front_runners.append(prev_order)

                if len(front_runners) >= 2:
                    context = {
                        'large_order_price': str(order.price),
                        'large_order_quantity': str(order.quantity),
                        'large_order_side': order.side,
                        'front_runner_count': len(front_runners),
                        'total_front_run_volume': str(sum(o.quantity for o in front_runners)),
                        'time_window_ms': self.front_run_window_ms
                    }

                    return self.create_alert(
                        pattern='front_running',
                        severity='warning',
                        confidence=0.65,
                        context=context,
                        explanation=f"Potential front-running: {len(front_runners)} small {order.side} orders "
                                  f"placed within {self.front_run_window_ms}ms before large order of {order.quantity}"
                    )

        return None


# Export all detectors
__all__ = [
    'SpoofingDetector',
    'LayeringDetector',
    'WallDetector',
    'IcebergDetector',
    'MomentumIgnitionDetector',
    'WashTradingDetector',
    'TapePaintingDetector',
    'FrontRunningDetector'
]