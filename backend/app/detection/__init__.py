"""Market manipulation and pattern detection system."""

from .models import Alert, AlertSeverity, OrderEvent
from .engine import DetectionEngine
from .spoofing import SpoofingDetector
from .layering import LayeringDetector
from .walls import WallsDetector
from .iceberg import IcebergDetector
from .momentum_ignition import MomentumIgnitionDetector
from .wash_trading import WashTradingDetector
from .tape_painting import TapePaintingDetector
from .front_running import FrontRunningDetector

# Backward-compatible alias used by tests/docs.
WallDetector = WallsDetector

__all__ = [
    "Alert",
    "AlertSeverity",
    "OrderEvent",
    "DetectionEngine",
    "SpoofingDetector",
    "LayeringDetector",
    "WallsDetector",
    "WallDetector",
    "IcebergDetector",
    "MomentumIgnitionDetector",
    "WashTradingDetector",
    "TapePaintingDetector",
    "FrontRunningDetector",
]
