"""Models for arbitrage detection and analysis."""

from dataclasses import dataclass
from decimal import Decimal
from typing import List, Dict, Optional, Tuple
from datetime import datetime


@dataclass
class ArbitrageOpportunity:
    """
    Represents a price discrepancy arbitrage opportunity between exchanges.
    """
    timestamp: datetime
    symbol: str
    buy_exchange: str
    sell_exchange: str
    buy_price: Decimal
    sell_price: Decimal
    spread: Decimal  # Absolute spread
    spread_pct: Decimal  # Percentage spread
    buy_volume: Decimal  # Available volume at buy price
    sell_volume: Decimal  # Available volume at sell price
    potential_volume: Decimal  # Min of buy/sell volume
    estimated_profit: Decimal  # After fees
    buy_fees: Decimal  # Estimated buy fees
    sell_fees: Decimal  # Estimated sell fees
    latency_risk_ms: int  # Combined latency to both exchanges
    confidence: float  # 0.0 to 1.0


@dataclass
class TriangularArbitrageOpportunity:
    """
    Represents a triangular arbitrage opportunity within or across exchanges.
    """
    timestamp: datetime
    exchange: str  # Primary exchange (or "cross-exchange" for multi-exchange)
    path: List[Tuple[str, str, str]]  # [(symbol, side, exchange), ...]
    initial_amount: Decimal
    final_amount: Decimal
    profit: Decimal
    profit_pct: Decimal
    prices: Dict[str, Decimal]  # symbol -> price mapping
    volumes: Dict[str, Decimal]  # symbol -> available volume
    fees_total: Decimal
    execution_time_ms: int  # Estimated time to execute all trades
    confidence: float


@dataclass
class LeadLagResult:
    """
    Results from lead-lag analysis between exchanges.
    """
    timestamp: datetime
    symbol: str
    lead_exchange: str
    lag_exchange: str
    lag_ms: int  # How much the lag exchange lags behind
    correlation: float  # Correlation coefficient
    granger_causality_pvalue: float  # P-value from Granger causality test
    information_transfer_rate: float  # Bits per second
    predictive_power: float  # 0.0 to 1.0
    sample_size: int
    time_window_seconds: int


@dataclass
class ExchangeCorrelation:
    """
    Correlation metrics between exchanges for a symbol.
    """
    symbol: str
    exchange1: str
    exchange2: str
    correlation: float  # Pearson correlation
    lag_correlation: Dict[int, float]  # lag_ms -> correlation
    optimal_lag_ms: int  # Lag with highest correlation
    max_correlation: float  # Correlation at optimal lag
    cointegration_pvalue: float  # Test for long-term relationship
    volatility_ratio: float  # Ratio of volatilities


@dataclass
class ExchangeLatency:
    """
    Tracks latency metrics for an exchange.
    """
    exchange: str
    avg_latency_ms: float
    min_latency_ms: float
    max_latency_ms: float
    p95_latency_ms: float
    last_updated: datetime