"""Momentum ignition detection.

Detects bursts of aggressive orders designed to trigger stop-losses and momentum strategies.
"""

from collections import deque
from decimal import Decimal
from typing import Optional, List, Dict, Tuple
from datetime import datetime

from .base import BaseDetector
from .models import Alert
from ..models.market_data import OrderBookSnapshot, Trade


class MomentumIgnitionDetector(BaseDetector):
    """
    Detect momentum ignition: sudden burst of aggressive orders (>5 in 2s)
    in one direction, followed by reversal.
    """

    def __init__(self,
                 exchange: str,
                 symbol: str,
                 burst_window_ms: int = 2000,
                 min_burst_trades: int = 5,
                 reversal_window_ms: int = 30000,
                 reversal_threshold: float = 0.5,
                 imbalance_threshold: float = 0.85):
        super().__init__(exchange, symbol)
        self.burst_window_ms = burst_window_ms
        self.min_burst_trades = min_burst_trades
        self.reversal_window_ms = reversal_window_ms
        self.reversal_threshold = reversal_threshold
        self.imbalance_threshold = imbalance_threshold

        self.trades = deque(maxlen=1000)
        self.bursts = []

    def on_trade(self, timestamp_ms: int, price: float,
                 qty: float, is_buy: bool) -> Optional[Dict]:
        """Process trade and detect burst patterns."""
        self.trades.append((timestamp_ms, price, qty, is_buy))

        # Detect burst: sudden one-sided volume
        cutoff = timestamp_ms - self.burst_window_ms
        recent = [(ts, p, q, b) for ts, p, q, b in self.trades if ts >= cutoff]

        if len(recent) < self.min_burst_trades:
            return None

        buy_vol = sum(q for _, _, q, b in recent if b)
        sell_vol = sum(q for _, _, q, b in recent if not b)
        total = buy_vol + sell_vol

        if total == 0:
            return None

        imbalance = abs(buy_vol - sell_vol) / total

        if imbalance > self.imbalance_threshold:  # >85% one-sided
            direction = 'buy' if buy_vol > sell_vol else 'sell'
            burst_start_price = recent[0][1]
            burst_end_price = recent[-1][1]

            burst = {
                'timestamp': timestamp_ms,
                'direction': direction,
                'start_price': burst_start_price,
                'end_price': burst_end_price,
                'volume': total,
                'imbalance': imbalance,
                'num_trades': len(recent)
            }
            self.bursts.append(burst)

            # Check for reversal of previous burst
            reversal = self._check_reversal(timestamp_ms, price)
            if reversal:
                return reversal
            return burst

        return None

    def _check_reversal(self, current_ts: int, current_price: float) -> Optional[Dict]:
        """Check if current price represents a reversal of a previous burst."""
        for burst in self.bursts:
            elapsed = current_ts - burst['timestamp']
            if self.burst_window_ms < elapsed < self.reversal_window_ms:
                move = burst['end_price'] - burst['start_price']
                reversal = current_price - burst['end_price']

                if move != 0 and abs(reversal) / abs(move) > self.reversal_threshold:
                    if (move > 0 and reversal < 0) or (move < 0 and reversal > 0):
                        return {
                            'detected': True,
                            'type': 'momentum_ignition_with_reversal',
                            'original_direction': burst['direction'],
                            'burst_move': move,
                            'reversal': reversal,
                            'reversal_ratio': abs(reversal / move),
                            'burst_volume': burst['volume'],
                            'burst_trades': burst['num_trades'],
                            'time_to_reversal_ms': elapsed
                        }
        return None

    def detect(self,
               book_snapshot: Optional[OrderBookSnapshot] = None,
               trades: Optional[List[Trade]] = None,
               order_events: Optional[List] = None) -> Optional[Alert]:
        """Detect momentum ignition patterns from trades."""
        if not trades:
            return None

        ignition_detected = None
        current_time_ms = int(datetime.utcnow().timestamp() * 1000)

        # Process all trades
        for trade in trades:
            timestamp_ms = int(trade.timestamp.timestamp() * 1000)
            is_buy = trade.side == 'buy'
            result = self.on_trade(timestamp_ms, float(trade.price),
                                 float(trade.quantity), is_buy)
            if result and result.get('detected'):
                ignition_detected = result
            elif result and not ignition_detected:
                # Store burst even without reversal yet
                ignition_detected = result

        if ignition_detected:
            if ignition_detected.get('type') == 'momentum_ignition_with_reversal':
                # Full pattern with reversal detected
                severity = 'critical'
                confidence = 0.9

                context = {
                    'original_direction': ignition_detected['original_direction'],
                    'burst_move': round(ignition_detected['burst_move'], 4),
                    'reversal': round(ignition_detected['reversal'], 4),
                    'reversal_ratio': round(ignition_detected['reversal_ratio'], 2),
                    'burst_volume': round(ignition_detected['burst_volume'], 2),
                    'burst_trades': ignition_detected['burst_trades'],
                    'time_to_reversal_seconds': ignition_detected['time_to_reversal_ms'] / 1000
                }

                explanation = (f"Detected momentum ignition with reversal: "
                             f"{ignition_detected['burst_trades']} aggressive {ignition_detected['original_direction']} trades "
                             f"moved price {ignition_detected['burst_move']:.4f}, "
                             f"then reversed {ignition_detected['reversal']:.4f} "
                             f"({ignition_detected['reversal_ratio']:.0%} retracement)")

            else:
                # Just burst detected, no reversal yet
                severity = 'warning'
                confidence = 0.6

                context = {
                    'direction': ignition_detected['direction'],
                    'price_move': round(ignition_detected['end_price'] - ignition_detected['start_price'], 4),
                    'volume': round(ignition_detected['volume'], 2),
                    'imbalance': round(ignition_detected['imbalance'], 2),
                    'num_trades': ignition_detected['num_trades']
                }

                explanation = (f"Detected aggressive momentum burst: "
                             f"{ignition_detected['num_trades']} trades ({ignition_detected['imbalance']:.0%} {ignition_detected['direction']}) "
                             f"in {self.burst_window_ms/1000:.1f}s, "
                             f"volume {ignition_detected['volume']:.2f}")

            return self.create_alert(
                pattern='momentum_ignition',
                severity=severity,
                confidence=confidence,
                context=context,
                explanation=explanation
            )

        return None