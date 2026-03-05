"""Wash trading detection.

Detects buy and sell at same price within 1s with similar quantities.
"""

from collections import defaultdict, deque
from decimal import Decimal
from typing import Optional, List, Dict
from datetime import datetime
import statistics

from .base import BaseDetector
from .models import Alert
from ..models.market_data import OrderBookSnapshot, Trade


class WashTradingDetector(BaseDetector):
    """
    Detect wash trading patterns:
    - Buy and sell at same price within 1s
    - Similar quantities
    - High volume with minimal price impact
    """

    def __init__(self,
                 exchange: str,
                 symbol: str,
                 time_window_ms: int = 1000,
                 quantity_tolerance: float = 0.1,
                 min_wash_pairs: int = 3,
                 analysis_window_seconds: int = 300):
        super().__init__(exchange, symbol)
        self.time_window_ms = time_window_ms
        self.quantity_tolerance = quantity_tolerance
        self.min_wash_pairs = min_wash_pairs
        self.analysis_window_seconds = analysis_window_seconds

        self.trades = deque(maxlen=5000)
        self.wash_candidates = []

    def analyze(self) -> Dict:
        """
        Analyze trades for wash trading indicators.
        Without account-level data, we look for statistical anomalies.
        """
        if len(self.trades) < 20:
            return {'wash_score': 0.0}

        scores = []

        # 1. Buy-sell volume symmetry at exact same prices
        price_buys = defaultdict(float)
        price_sells = defaultdict(float)
        for ts, p, q, is_buy in self.trades:
            p_rounded = round(p, 2)
            if is_buy:
                price_buys[p_rounded] += q
            else:
                price_sells[p_rounded] += q

        # If buys and sells match closely at many price levels → suspicious
        matched_volume = 0
        total_volume = 0
        for price in set(price_buys) & set(price_sells):
            matched = min(price_buys[price], price_sells[price])
            matched_volume += matched * 2  # Count both sides
            total_volume += price_buys[price] + price_sells[price]

        if total_volume > 0:
            symmetry_score = matched_volume / total_volume
            scores.append(symmetry_score)

        # 2. Unusually regular inter-trade intervals
        if len(self.trades) > 10:
            timestamps = [t for t, _, _, _ in self.trades]
            intervals = [timestamps[i+1] - timestamps[i]
                        for i in range(len(timestamps)-1)]
            if intervals:
                mean_interval = statistics.mean(intervals)
                if mean_interval > 0 and len(intervals) > 1:
                    cv = statistics.stdev(intervals) / mean_interval
                    # Low coefficient of variation = suspiciously regular
                    regularity_score = max(0, 1 - cv)
                    scores.append(regularity_score)

        # 3. Volume anomaly: high volume with no price impact
        if self.trades:
            prices = [p for _, p, _, _ in self.trades]
            volumes = [q for _, _, q, _ in self.trades]
            if prices and max(prices) > 0:
                price_range = max(prices) - min(prices)
                total_vol = sum(volumes)
                avg_price = sum(prices) / len(prices)

                if total_vol > 0 and avg_price > 0:
                    # Calculate price impact ratio
                    impact_ratio = (price_range / avg_price) / (total_vol ** 0.5)
                    # Very low impact per unit volume = suspicious
                    no_impact_score = max(0, 1 - impact_ratio * 100)
                    scores.append(no_impact_score)

        return {
            'wash_score': sum(scores) / len(scores) if scores else 0.0,
            'symmetry': scores[0] if len(scores) > 0 else 0,
            'regularity': scores[1] if len(scores) > 1 else 0,
            'no_impact': scores[2] if len(scores) > 2 else 0,
        }

    def find_wash_pairs(self) -> List[Dict]:
        """Find potential wash trading pairs (buy/sell at same price, similar quantity)."""
        wash_pairs = []
        current_time_ms = int(datetime.utcnow().timestamp() * 1000)

        # Sort trades by timestamp
        sorted_trades = sorted(self.trades, key=lambda x: x[0])

        for i, (ts1, p1, q1, is_buy1) in enumerate(sorted_trades):
            # Only check recent trades
            if current_time_ms - ts1 > self.analysis_window_seconds * 1000:
                continue

            for j in range(i + 1, min(i + 20, len(sorted_trades))):  # Check next 20 trades
                ts2, p2, q2, is_buy2 = sorted_trades[j]

                # Check time window
                if ts2 - ts1 > self.time_window_ms:
                    break

                # Check for opposite sides, same price, similar quantity
                if (is_buy1 != is_buy2 and
                    abs(p1 - p2) < 0.00001 and  # Same price (with floating point tolerance)
                    abs(q1 - q2) / max(q1, q2) < self.quantity_tolerance):

                    wash_pairs.append({
                        'timestamp': ts2,
                        'price': p1,
                        'buy_qty': q1 if is_buy1 else q2,
                        'sell_qty': q2 if is_buy1 else q1,
                        'time_diff_ms': ts2 - ts1
                    })

        return wash_pairs

    def detect(self,
               book_snapshot: Optional[OrderBookSnapshot] = None,
               trades: Optional[List[Trade]] = None,
               order_events: Optional[List] = None) -> Optional[Alert]:
        """Detect wash trading patterns from trades."""
        if not trades:
            return None

        # Add new trades to our history
        for trade in trades:
            timestamp_ms = int(trade.timestamp.timestamp() * 1000)
            is_buy = trade.side == 'buy'
            self.trades.append((timestamp_ms, float(trade.price),
                              float(trade.quantity), is_buy))

        # Clean up old trades
        current_time_ms = int(datetime.utcnow().timestamp() * 1000)
        cutoff = current_time_ms - self.analysis_window_seconds * 1000
        while self.trades and self.trades[0][0] < cutoff:
            self.trades.popleft()

        # Find wash pairs
        wash_pairs = self.find_wash_pairs()

        # Analyze overall patterns
        analysis = self.analyze()

        # Determine if we should alert
        if len(wash_pairs) >= self.min_wash_pairs or analysis['wash_score'] > 0.7:
            # Determine severity
            if len(wash_pairs) >= 10 or analysis['wash_score'] > 0.85:
                severity = 'critical'
            elif len(wash_pairs) >= 5 or analysis['wash_score'] > 0.7:
                severity = 'warning'
            else:
                severity = 'info'

            # Calculate confidence
            confidence = min(1.0,
                           (len(wash_pairs) / 10) * 0.5 +
                           analysis['wash_score'] * 0.5)

            context = {
                'wash_pairs_count': len(wash_pairs),
                'wash_score': round(analysis['wash_score'], 2),
                'symmetry_score': round(analysis['symmetry'], 2),
                'regularity_score': round(analysis['regularity'], 2),
                'no_impact_score': round(analysis['no_impact'], 2),
            }

            if wash_pairs:
                latest = wash_pairs[-1]
                context.update({
                    'latest_price': str(latest['price']),
                    'latest_buy_qty': round(latest['buy_qty'], 4),
                    'latest_sell_qty': round(latest['sell_qty'], 4),
                    'latest_time_diff_ms': latest['time_diff_ms']
                })

            explanation = (f"Detected wash trading indicators: "
                         f"{len(wash_pairs)} buy/sell pairs at same price within {self.time_window_ms}ms, "
                         f"wash score {analysis['wash_score']:.2f} "
                         f"(symmetry: {analysis['symmetry']:.2f}, "
                         f"regularity: {analysis['regularity']:.2f}, "
                         f"low impact: {analysis['no_impact']:.2f})")

            return self.create_alert(
                pattern='wash_trading',
                severity=severity,
                confidence=confidence,
                context=context,
                explanation=explanation
            )

        return None