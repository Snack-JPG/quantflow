"""Lead-lag analysis for cross-exchange price discovery."""

import asyncio
import logging
import numpy as np
from collections import defaultdict, deque
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple, Callable
from scipy import signal, stats

from ..models import OrderBookSnapshot, Trade
from .models import LeadLagResult, ExchangeCorrelation


logger = logging.getLogger(__name__)


class LeadLagAnalyzer:
    """
    Analyzes lead-lag relationships between exchanges to identify
    which exchange leads price discovery.

    Uses:
    - Cross-correlation analysis with lag optimization
    - Granger causality tests
    - Information transfer metrics
    """

    def __init__(
        self,
        window_size: int = 1000,  # Number of price points to keep
        max_lag_ms: int = 5000,  # Maximum lag to test (5 seconds)
        min_correlation: float = 0.7,  # Minimum correlation to consider significant
        on_lead_detected: Optional[Callable[[LeadLagResult], None]] = None
    ):
        """
        Initialize the lead-lag analyzer.

        Args:
            window_size: Size of rolling window for price history
            max_lag_ms: Maximum lag to test in milliseconds
            min_correlation: Minimum correlation threshold
            on_lead_detected: Callback when lead-lag relationship is detected
        """
        self.window_size = window_size
        self.max_lag_ms = max_lag_ms
        self.min_correlation = min_correlation
        self.on_lead_detected = on_lead_detected

        # Store price histories by exchange and symbol
        # Structure: {exchange: {symbol: deque([(timestamp_ms, price), ...])}}
        self._price_histories: Dict[str, Dict[str, deque]] = defaultdict(
            lambda: defaultdict(lambda: deque(maxlen=window_size))
        )

        # Store mid-price series for analysis
        self._mid_prices: Dict[str, Dict[str, deque]] = defaultdict(
            lambda: defaultdict(lambda: deque(maxlen=window_size))
        )

        # Cache for correlation results
        self._correlation_cache: Dict[str, ExchangeCorrelation] = {}

        # Track lead-lag results
        self._results: List[LeadLagResult] = []

        # Statistics
        self._stats = {
            "analyses_performed": 0,
            "lead_relationships_found": 0,
            "avg_lead_time_ms": 0.0,
            "strongest_correlation": 0.0
        }

    async def update_order_book(self, snapshot: OrderBookSnapshot) -> None:
        """
        Update price history with new order book snapshot.

        Args:
            snapshot: Order book snapshot
        """
        if not snapshot.mid_price:
            return

        exchange = snapshot.exchange
        symbol = snapshot.symbol
        timestamp_ms = snapshot.timestamp_us / 1000
        mid_price = float(snapshot.mid_price)

        # Store price point
        self._price_histories[exchange][symbol].append((timestamp_ms, mid_price))
        self._mid_prices[exchange][symbol].append(mid_price)

        # Check if we have enough data to analyze
        await self._check_analysis_trigger(symbol)

    async def update_trade(self, trade: Trade) -> None:
        """
        Update price history with trade data.

        Args:
            trade: Trade execution
        """
        exchange = trade.exchange
        symbol = trade.symbol
        timestamp_ms = trade.timestamp_us / 1000
        price = float(trade.price)

        # Store trade price
        self._price_histories[exchange][symbol].append((timestamp_ms, price))

    async def _check_analysis_trigger(self, symbol: str) -> None:
        """
        Check if we should trigger lead-lag analysis for a symbol.

        Args:
            symbol: Trading symbol
        """
        # Get exchanges that have this symbol
        exchanges_with_data = [
            exchange for exchange, symbols in self._mid_prices.items()
            if symbol in symbols and len(symbols[symbol]) >= 100
        ]

        # Need at least 2 exchanges with sufficient data
        if len(exchanges_with_data) < 2:
            return

        # Analyze all exchange pairs
        for i, exchange1 in enumerate(exchanges_with_data):
            for exchange2 in exchanges_with_data[i + 1:]:
                result = await self._analyze_pair(symbol, exchange1, exchange2)
                if result:
                    await self._handle_result(result)

    async def _analyze_pair(
        self,
        symbol: str,
        exchange1: str,
        exchange2: str
    ) -> Optional[LeadLagResult]:
        """
        Analyze lead-lag relationship between two exchanges.

        Args:
            symbol: Trading symbol
            exchange1: First exchange
            exchange2: Second exchange

        Returns:
            LeadLagResult if significant relationship found, None otherwise
        """
        prices1 = self._mid_prices[exchange1][symbol]
        prices2 = self._mid_prices[exchange2][symbol]

        if len(prices1) < 100 or len(prices2) < 100:
            return None

        # Convert to numpy arrays
        series1 = np.array(list(prices1))
        series2 = np.array(list(prices2))

        # Normalize series (remove mean and scale by std)
        series1 = (series1 - np.mean(series1)) / np.std(series1)
        series2 = (series2 - np.mean(series2)) / np.std(series2)

        # Calculate cross-correlation with different lags
        correlations = self._calculate_cross_correlation(series1, series2)

        # Find optimal lag
        optimal_lag, max_correlation = self._find_optimal_lag(correlations)

        if abs(max_correlation) < self.min_correlation:
            return None  # No significant correlation

        # Determine lead-lag relationship
        if optimal_lag > 0:
            # exchange1 leads exchange2
            lead_exchange = exchange1
            lag_exchange = exchange2
            lag_ms = optimal_lag * 100  # Assuming 100ms sampling
        else:
            # exchange2 leads exchange1
            lead_exchange = exchange2
            lag_exchange = exchange1
            lag_ms = abs(optimal_lag) * 100

        # Calculate Granger causality (simplified version)
        granger_pvalue = self._granger_causality_test(series1, series2, abs(optimal_lag))

        # Calculate information transfer rate
        info_transfer = self._calculate_information_transfer(series1, series2, optimal_lag)

        # Calculate predictive power
        predictive_power = self._calculate_predictive_power(series1, series2, optimal_lag)

        self._stats["analyses_performed"] += 1

        return LeadLagResult(
            timestamp=datetime.now(),
            symbol=symbol,
            lead_exchange=lead_exchange,
            lag_exchange=lag_exchange,
            lag_ms=lag_ms,
            correlation=max_correlation,
            granger_causality_pvalue=granger_pvalue,
            information_transfer_rate=info_transfer,
            predictive_power=predictive_power,
            sample_size=min(len(series1), len(series2)),
            time_window_seconds=len(series1) * 0.1  # 100ms per sample
        )

    def _calculate_cross_correlation(
        self,
        series1: np.ndarray,
        series2: np.ndarray
    ) -> np.ndarray:
        """
        Calculate cross-correlation between two time series.

        Args:
            series1: First price series
            series2: Second price series

        Returns:
            Array of correlation coefficients at different lags
        """
        # Use scipy's correlate for efficiency
        correlation = signal.correlate(series1, series2, mode='same', method='auto')

        # Normalize to get correlation coefficients
        norm_factor = np.sqrt(np.sum(series1**2) * np.sum(series2**2))
        if norm_factor > 0:
            correlation = correlation / norm_factor

        return correlation

    def _find_optimal_lag(
        self,
        correlations: np.ndarray
    ) -> Tuple[int, float]:
        """
        Find the lag with maximum correlation.

        Args:
            correlations: Array of correlation coefficients

        Returns:
            Tuple of (optimal_lag_index, max_correlation)
        """
        # Limit search to max_lag_ms
        max_lag_samples = min(self.max_lag_ms // 100, len(correlations) // 2)
        center = len(correlations) // 2

        # Search within lag window
        search_range = correlations[center - max_lag_samples:center + max_lag_samples + 1]

        # Find maximum absolute correlation
        max_idx = np.argmax(np.abs(search_range))
        max_corr = search_range[max_idx]

        # Convert to lag (negative = series1 lags, positive = series1 leads)
        optimal_lag = max_idx - max_lag_samples

        return optimal_lag, max_corr

    def _granger_causality_test(
        self,
        series1: np.ndarray,
        series2: np.ndarray,
        lag: int
    ) -> float:
        """
        Simplified Granger causality test.

        Args:
            series1: First series
            series2: Second series
            lag: Lag to test

        Returns:
            P-value (lower = stronger causality)
        """
        if lag == 0:
            return 1.0  # No causality at zero lag

        # Simplified test using correlation ratio
        # In practice, would use statsmodels.tsa.stattools.grangercausalitytests

        # Shift series by lag
        if lag > 0:
            x = series1[:-lag]
            y = series2[lag:]
        else:
            x = series2[:-abs(lag)]
            y = series1[abs(lag):]

        if len(x) < 10 or len(y) < 10:
            return 1.0

        # Calculate correlation coefficient
        corr_coef, p_value = stats.pearsonr(x, y)

        return p_value

    def _calculate_information_transfer(
        self,
        series1: np.ndarray,
        series2: np.ndarray,
        lag: int
    ) -> float:
        """
        Calculate information transfer rate between series.

        Args:
            series1: First series
            series2: Second series
            lag: Optimal lag

        Returns:
            Information transfer rate (bits per second)
        """
        # Simplified mutual information calculation
        # In practice, would use transfer entropy

        if lag == 0:
            return 0.0

        # Shift series by lag
        if lag > 0:
            x = series1[:-lag]
            y = series2[lag:]
        else:
            x = series2[:-abs(lag)]
            y = series1[abs(lag):]

        if len(x) < 10 or len(y) < 10:
            return 0.0

        # Calculate mutual information (simplified)
        # Using correlation as proxy
        corr_coef, _ = stats.pearsonr(x, y)

        # Convert to information rate (simplified)
        # Max information = log2(n) where n is number of distinct values
        # Using correlation^2 as efficiency factor
        info_rate = abs(corr_coef) ** 2 * 10  # 10 bits/sec max for price data

        return info_rate

    def _calculate_predictive_power(
        self,
        series1: np.ndarray,
        series2: np.ndarray,
        lag: int
    ) -> float:
        """
        Calculate predictive power of leading series.

        Args:
            series1: First series
            series2: Second series
            lag: Optimal lag

        Returns:
            Predictive power (0.0 to 1.0)
        """
        if lag == 0:
            return 0.0

        # Shift series by lag
        if lag > 0:
            x = series1[:-lag]
            y = series2[lag:]
        else:
            x = series2[:-abs(lag)]
            y = series1[abs(lag):]

        if len(x) < 10 or len(y) < 10:
            return 0.0

        # Calculate R-squared as predictive power
        corr_coef, _ = stats.pearsonr(x, y)
        r_squared = corr_coef ** 2

        return r_squared

    async def _handle_result(self, result: LeadLagResult) -> None:
        """
        Handle a detected lead-lag relationship.

        Args:
            result: Lead-lag analysis result
        """
        # Update statistics
        self._stats["lead_relationships_found"] += 1
        self._stats["avg_lead_time_ms"] = (
            (self._stats["avg_lead_time_ms"] * (self._stats["lead_relationships_found"] - 1) +
             result.lag_ms) / self._stats["lead_relationships_found"]
        )
        self._stats["strongest_correlation"] = max(
            self._stats["strongest_correlation"],
            abs(result.correlation)
        )

        # Store result
        self._results.append(result)

        # Log significant relationships
        if result.correlation > self.min_correlation and result.granger_causality_pvalue < 0.05:
            logger.info(
                f"Lead-lag detected: {result.symbol} "
                f"{result.lead_exchange} leads {result.lag_exchange} "
                f"by {result.lag_ms}ms (correlation: {result.correlation:.3f}, "
                f"p-value: {result.granger_causality_pvalue:.4f})"
            )

        # Trigger callback
        if self.on_lead_detected:
            await asyncio.create_task(self.on_lead_detected(result))

    def get_correlations(
        self,
        symbol: str,
        min_correlation: Optional[float] = None
    ) -> List[ExchangeCorrelation]:
        """
        Get exchange correlations for a symbol.

        Args:
            symbol: Trading symbol
            min_correlation: Minimum correlation filter

        Returns:
            List of exchange correlations
        """
        correlations = []
        exchanges = list(self._mid_prices.keys())

        for i, exchange1 in enumerate(exchanges):
            if symbol not in self._mid_prices[exchange1]:
                continue

            for exchange2 in exchanges[i + 1:]:
                if symbol not in self._mid_prices[exchange2]:
                    continue

                prices1 = np.array(list(self._mid_prices[exchange1][symbol]))
                prices2 = np.array(list(self._mid_prices[exchange2][symbol]))

                if len(prices1) < 10 or len(prices2) < 10:
                    continue

                # Ensure same length
                min_len = min(len(prices1), len(prices2))
                prices1 = prices1[-min_len:]
                prices2 = prices2[-min_len:]

                # Calculate correlation
                corr_coef, _ = stats.pearsonr(prices1, prices2)

                if min_correlation and abs(corr_coef) < min_correlation:
                    continue

                # Calculate lag correlations
                lag_correlations = {}
                for lag in range(-10, 11):  # -1 to +1 second in 100ms steps
                    if lag == 0:
                        lag_corr = corr_coef
                    elif lag > 0:
                        if len(prices1[:-lag]) > 10 and len(prices2[lag:]) > 10:
                            lag_corr, _ = stats.pearsonr(prices1[:-lag], prices2[lag:])
                        else:
                            lag_corr = 0.0
                    else:
                        if len(prices2[:-abs(lag)]) > 10 and len(prices1[abs(lag):]) > 10:
                            lag_corr, _ = stats.pearsonr(prices2[:-abs(lag)], prices1[abs(lag):])
                        else:
                            lag_corr = 0.0

                    lag_correlations[lag * 100] = lag_corr

                # Find optimal lag
                optimal_lag_ms = max(lag_correlations, key=lambda k: abs(lag_correlations[k]))
                max_correlation = lag_correlations[optimal_lag_ms]

                # Calculate volatility ratio
                vol1 = np.std(prices1)
                vol2 = np.std(prices2)
                vol_ratio = vol1 / vol2 if vol2 > 0 else 0.0

                correlations.append(ExchangeCorrelation(
                    symbol=symbol,
                    exchange1=exchange1,
                    exchange2=exchange2,
                    correlation=corr_coef,
                    lag_correlation=lag_correlations,
                    optimal_lag_ms=optimal_lag_ms,
                    max_correlation=max_correlation,
                    cointegration_pvalue=1.0,  # Simplified, would use statsmodels
                    volatility_ratio=vol_ratio
                ))

        return correlations

    def get_lead_lag_results(
        self,
        symbol: Optional[str] = None,
        lead_exchange: Optional[str] = None,
        min_correlation: Optional[float] = None
    ) -> List[LeadLagResult]:
        """
        Get lead-lag analysis results.

        Args:
            symbol: Filter by symbol
            lead_exchange: Filter by leading exchange
            min_correlation: Minimum correlation filter

        Returns:
            List of lead-lag results
        """
        results = self._results.copy()

        if symbol:
            results = [r for r in results if r.symbol == symbol]

        if lead_exchange:
            results = [r for r in results if r.lead_exchange == lead_exchange]

        if min_correlation:
            results = [r for r in results if abs(r.correlation) >= min_correlation]

        # Sort by correlation strength
        results.sort(key=lambda x: abs(x.correlation), reverse=True)

        return results

    def get_statistics(self) -> Dict:
        """
        Get analyzer statistics.

        Returns:
            Dictionary of statistics
        """
        return {
            **self._stats,
            "tracked_exchanges": len(self._price_histories),
            "tracked_symbols": sum(
                len(symbols) for symbols in self._price_histories.values()
            ),
            "total_price_points": sum(
                sum(len(history) for history in symbols.values())
                for symbols in self._price_histories.values()
            )
        }