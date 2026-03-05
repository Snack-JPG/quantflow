"""Base class for all pattern detectors."""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal

from .models import Alert, OrderEvent
from ..models.market_data import OrderBookSnapshot, Trade


class BaseDetector(ABC):
    """Abstract base class for pattern detection algorithms."""

    def __init__(self, exchange: str, symbol: str):
        self.exchange = exchange
        self.symbol = symbol
        self.last_detection_time = None

    @abstractmethod
    def detect(self,
               book_snapshot: Optional[OrderBookSnapshot] = None,
               trades: Optional[List[Trade]] = None,
               order_events: Optional[List[OrderEvent]] = None) -> Optional[Alert]:
        """
        Detect patterns in the provided data.

        Args:
            book_snapshot: Current order book snapshot
            trades: Recent trades
            order_events: Recent order placement/cancellation events

        Returns:
            Alert if pattern detected, None otherwise
        """
        pass

    def create_alert(self,
                    pattern: str,
                    severity: str,
                    confidence: float,
                    context: Dict[str, Any],
                    explanation: str) -> Alert:
        """Helper to create alert with common fields."""
        from .models import AlertSeverity

        severity_map = {
            'info': AlertSeverity.INFO,
            'warning': AlertSeverity.WARNING,
            'critical': AlertSeverity.CRITICAL
        }

        return Alert(
            timestamp=datetime.utcnow(),
            pattern=pattern,
            severity=severity_map.get(severity, AlertSeverity.INFO),
            confidence=confidence,
            exchange=self.exchange,
            symbol=self.symbol,
            context=context,
            explanation=explanation,
            ai_generated=False
        )