"""Detection engine that orchestrates all pattern detectors."""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import asyncio
import logging

from .base import BaseDetector
from .models import Alert, OrderEvent
from .spoofing import SpoofingDetector
from .layering import LayeringDetector
from .walls import WallsDetector
from .iceberg import IcebergDetector
from .momentum_ignition import MomentumIgnitionDetector
from .wash_trading import WashTradingDetector
from .tape_painting import TapePaintingDetector
from .front_running import FrontRunningDetector
from .claude_analyzer import ClaudeAnalyzer

from ..models.market_data import OrderBookSnapshot, Trade

logger = logging.getLogger(__name__)


class DetectionEngine:
    """
    Orchestrates all pattern detection algorithms.
    Runs Tier 1 (rule-based) detectors in parallel for speed.
    Manages Tier 2 (Claude API) analysis with rate limiting.
    """

    def __init__(self, exchange: str, symbol: str):
        self.exchange = exchange
        self.symbol = symbol

        # Initialize all detectors
        self.detectors: List[BaseDetector] = [
            SpoofingDetector(exchange, symbol),
            LayeringDetector(exchange, symbol),
            WallsDetector(exchange, symbol),
            IcebergDetector(exchange, symbol),
            MomentumIgnitionDetector(exchange, symbol),
            WashTradingDetector(exchange, symbol),
            TapePaintingDetector(exchange, symbol),
            FrontRunningDetector(exchange, symbol)
        ]

        # Claude API analyzer (Tier 2)
        self.claude_analyzer = ClaudeAnalyzer(exchange, symbol)

        # Alert history for deduplication
        self.recent_alerts: List[Alert] = []
        self.alert_dedup_window = timedelta(minutes=5)

        # Metrics
        self.detection_stats = {
            'total_detections': 0,
            'by_pattern': {},
            'by_severity': {'info': 0, 'warning': 0, 'critical': 0}
        }

    async def detect_patterns(self,
                             book_snapshot: Optional[OrderBookSnapshot] = None,
                             trades: Optional[List[Trade]] = None,
                             order_events: Optional[List[OrderEvent]] = None) -> List[Alert]:
        """
        Run all detectors on the provided data.
        Returns list of alerts for detected patterns.
        """
        alerts = []

        # Run all Tier 1 detectors in parallel
        detection_tasks = []
        for detector in self.detectors:
            task = asyncio.create_task(
                self._run_detector(detector, book_snapshot, trades, order_events)
            )
            detection_tasks.append(task)

        # Wait for all detectors to complete
        results = await asyncio.gather(*detection_tasks, return_exceptions=True)

        # Process results
        for result in results:
            if isinstance(result, Alert):
                if not self._is_duplicate(result):
                    alerts.append(result)
                    self._update_stats(result)
            elif isinstance(result, Exception):
                logger.error(f"Detector error: {result}")

        # Run Claude analysis if conditions are met
        claude_alert = await self._run_claude_analysis(book_snapshot, trades, alerts)
        if claude_alert:
            alerts.append(claude_alert)
            self._update_stats(claude_alert)

        # Update alert history
        self.recent_alerts.extend(alerts)
        self._cleanup_alert_history()

        return alerts

    async def _run_detector(self,
                           detector: BaseDetector,
                           book_snapshot: Optional[OrderBookSnapshot],
                           trades: Optional[List[Trade]],
                           order_events: Optional[List[OrderEvent]]) -> Optional[Alert]:
        """Run a single detector asynchronously."""
        try:
            # Most detectors are synchronous, wrap in executor
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None,
                detector.detect,
                book_snapshot,
                trades,
                order_events
            )
        except Exception as e:
            logger.error(f"Error in {detector.__class__.__name__}: {e}")
            return None

    async def _run_claude_analysis(self,
                                  book_snapshot: Optional[OrderBookSnapshot],
                                  trades: Optional[List[Trade]],
                                  rule_alerts: List[Alert]) -> Optional[Alert]:
        """
        Run Claude API analysis if rate limit allows.
        This provides deeper pattern recognition beyond rules.
        """
        try:
            # Check if we should run Claude analysis
            if not self.claude_analyzer.should_analyze():
                return None

            # Only run if we have interesting data
            if not (book_snapshot or trades) and not rule_alerts:
                return None

            # Run analysis
            return await self.claude_analyzer.analyze(
                book_snapshot,
                trades,
                rule_alerts
            )
        except Exception as e:
            logger.error(f"Claude analysis error: {e}")
            return None

    def _is_duplicate(self, alert: Alert) -> bool:
        """Check if alert is duplicate of recent alert."""
        cutoff = datetime.utcnow() - self.alert_dedup_window

        for recent in self.recent_alerts:
            if recent.timestamp < cutoff:
                continue

            # Same pattern, same exchange/symbol, within time window
            if (recent.pattern == alert.pattern and
                recent.exchange == alert.exchange and
                recent.symbol == alert.symbol):

                # Check if context is similar
                if self._similar_context(recent.context, alert.context):
                    return True

        return False

    def _similar_context(self, ctx1: Dict[str, Any], ctx2: Dict[str, Any]) -> bool:
        """Check if two alert contexts are similar enough to be duplicates."""
        # Simple similarity check - can be made more sophisticated
        key_fields = ['side', 'price', 'direction']

        for field in key_fields:
            if field in ctx1 and field in ctx2:
                if ctx1[field] != ctx2[field]:
                    return False

        return True

    def _update_stats(self, alert: Alert):
        """Update detection statistics."""
        self.detection_stats['total_detections'] += 1

        pattern = alert.pattern
        if pattern not in self.detection_stats['by_pattern']:
            self.detection_stats['by_pattern'][pattern] = 0
        self.detection_stats['by_pattern'][pattern] += 1

        severity = alert.severity.value
        self.detection_stats['by_severity'][severity] += 1

    def _cleanup_alert_history(self):
        """Remove old alerts from history."""
        cutoff = datetime.utcnow() - self.alert_dedup_window * 2
        self.recent_alerts = [a for a in self.recent_alerts
                             if a.timestamp > cutoff]

    def get_stats(self) -> Dict[str, Any]:
        """Get detection statistics."""
        return {
            **self.detection_stats,
            'recent_alerts_count': len(self.recent_alerts),
            'claude_api_calls': self.claude_analyzer.api_calls_made,
            'claude_remaining_calls': self.claude_analyzer.get_remaining_calls()
        }