"""
Alert system for pattern detection
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal, Dict, Any, List, Optional
from uuid import uuid4
import json
import asyncio
from collections import deque

@dataclass
class Alert:
    """Represents a detected pattern or anomaly"""
    id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)
    pattern: str = ""  # "spoofing", "layering", "wall", etc.
    severity: Literal["info", "warning", "critical"] = "info"
    confidence: float = 0.0  # 0.0 - 1.0
    exchange: str = ""
    symbol: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
    explanation: str = ""
    ai_generated: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert alert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat(),
            'pattern': self.pattern,
            'severity': self.severity,
            'confidence': self.confidence,
            'exchange': self.exchange,
            'symbol': self.symbol,
            'context': self.context,
            'explanation': self.explanation,
            'ai_generated': self.ai_generated
        }

    def to_json(self) -> str:
        """Convert alert to JSON string"""
        return json.dumps(self.to_dict())


class AlertManager:
    """Manages and broadcasts alerts"""

    def __init__(self, max_alerts: int = 1000):
        self.alerts: deque[Alert] = deque(maxlen=max_alerts)
        self.subscribers: List[asyncio.Queue] = []
        self._lock = asyncio.Lock()

    async def add_alert(self, alert: Alert) -> None:
        """Add an alert and broadcast to subscribers"""
        async with self._lock:
            self.alerts.append(alert)

            # Broadcast to all subscribers
            for queue in self.subscribers:
                try:
                    await queue.put(alert)
                except asyncio.QueueFull:
                    # Skip if subscriber's queue is full
                    pass

    async def subscribe(self) -> asyncio.Queue:
        """Subscribe to alert stream"""
        queue = asyncio.Queue(maxsize=100)
        async with self._lock:
            self.subscribers.append(queue)
        return queue

    async def unsubscribe(self, queue: asyncio.Queue) -> None:
        """Unsubscribe from alert stream"""
        async with self._lock:
            if queue in self.subscribers:
                self.subscribers.remove(queue)

    def get_recent_alerts(self, count: int = 50) -> List[Alert]:
        """Get most recent alerts"""
        return list(self.alerts)[-count:]

    def get_alerts_by_pattern(self, pattern: str) -> List[Alert]:
        """Get alerts matching a specific pattern"""
        return [a for a in self.alerts if a.pattern == pattern]

    def get_alerts_by_severity(self, severity: str) -> List[Alert]:
        """Get alerts matching a specific severity"""
        return [a for a in self.alerts if a.severity == severity]

    def get_critical_alerts(self) -> List[Alert]:
        """Get all critical alerts"""
        return self.get_alerts_by_severity("critical")

    def clear_alerts(self) -> None:
        """Clear all alerts"""
        self.alerts.clear()