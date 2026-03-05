"""Detection system data models."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional
from decimal import Decimal
import uuid


class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class Alert:
    """Alert data structure for detected patterns."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)
    pattern: str = ""  # "spoofing", "layering", "walls", etc.
    severity: AlertSeverity = AlertSeverity.INFO
    confidence: float = 0.0  # 0.0 - 1.0
    exchange: str = ""
    symbol: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
    explanation: str = ""
    ai_generated: bool = False  # False = rule-based, True = AI

    def to_dict(self) -> dict:
        """Convert alert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat(),
            'pattern': self.pattern,
            'severity': self.severity.value,
            'confidence': self.confidence,
            'exchange': self.exchange,
            'symbol': self.symbol,
            'context': self.context,
            'explanation': self.explanation,
            'ai_generated': self.ai_generated
        }


@dataclass
class OrderEvent:
    """Order book event for pattern detection."""
    timestamp_ms: int
    price: Decimal
    quantity: Decimal
    side: str  # 'bid' or 'ask'
    event_type: str  # 'place', 'cancel', 'fill'