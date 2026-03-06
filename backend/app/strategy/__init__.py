"""QuantFlow Strategy Engine - Event-driven backtesting framework."""

# Base classes
from .base import Strategy
from .models import (
    OrderBookSnapshot,
    Trade,
    Alert,
    Signal,
    SignalDirection,
    Position,
    BacktestConfig,
    BacktestResult,
    PerformanceMetrics,
    TradeRecord
)

# Backtesting
from .backtesting import (
    BacktestEngine,
    DataFeed,
    WalkForwardOptimizer,
    GridSearchOptimizer
)

# Built-in strategies
from .strategies import (
    OBIMeanReversionStrategy,
    VPINToxicityStrategy,
    SpoofingAlphaStrategy,
    CrossExchangeArbStrategy,
    STRATEGIES
)

# Data loading
try:
    from .data_loader import BinanceDataLoader
except ModuleNotFoundError:
    # Keep package importable even when optional loader dependencies are absent.
    BinanceDataLoader = None  # type: ignore[assignment]

__all__ = [
    # Base
    'Strategy',

    # Models
    'OrderBookSnapshot',
    'Trade',
    'Alert',
    'Signal',
    'SignalDirection',
    'Position',
    'BacktestConfig',
    'BacktestResult',
    'PerformanceMetrics',
    'TradeRecord',

    # Backtesting
    'BacktestEngine',
    'DataFeed',
    'WalkForwardOptimizer',
    'GridSearchOptimizer',

    # Strategies
    'OBIMeanReversionStrategy',
    'VPINToxicityStrategy',
    'SpoofingAlphaStrategy',
    'CrossExchangeArbStrategy',
    'STRATEGIES',

    # Data
    'BinanceDataLoader'
]
