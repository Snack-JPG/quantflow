"""Analytics Engine that orchestrates all market microstructure metrics."""

from decimal import Decimal
from typing import Dict, List, Tuple, Optional, Any
import logging
import time

from .spread import BidAskSpread
from .vwap import VWAP
from .order_book_imbalance import OrderBookImbalance
from .order_flow_imbalance import OrderFlowImbalance, BookTop
from .kyles_lambda import KylesLambda
from .vpin import VPIN
from .amihud import AmihudIlliquidity
from .roll_spread import RollSpread
from .realized_volatility import RealizedVolatility
from .garman_klass import GarmanKlassVolatility
from .parkinson import ParkinsonVolatility
from .hurst import HurstExponent

logger = logging.getLogger(__name__)


class AnalyticsEngine:
    """
    Central analytics engine that coordinates all market microstructure metrics.

    This engine processes order book snapshots, trades, and OHLC data to compute
    comprehensive market microstructure analytics in real-time.
    """

    def __init__(self):
        """Initialize all analytics components."""
        # Spread metrics
        self.spread_calculator = BidAskSpread()

        # VWAP with multiple windows (1m, 5m, 15m)
        self.vwap = VWAP(window_seconds=[60, 300, 900])

        # Order book imbalance
        self.obi = OrderBookImbalance(default_levels=10)

        # Order flow imbalance
        self.ofi = OrderFlowImbalance(cumulative_window=50)

        # Kyle's Lambda
        self.kyles_lambda = KylesLambda(window_size=100)
        self.interval_signed_volume = 0.0
        self.interval_start_price: Optional[float] = None
        self.interval_trade_count = 0

        # VPIN
        self.vpin = VPIN(bucket_size=10000.0, n_buckets=50)

        # Amihud illiquidity
        self.amihud = AmihudIlliquidity(window=20)

        # Roll spread
        self.roll_spread = RollSpread(window=100)

        # Realized volatility
        self.realized_vol = RealizedVolatility(windows=[60, 300, 900, 3600])

        # Garman-Klass volatility
        self.garman_klass = GarmanKlassVolatility(window=20)

        # Parkinson volatility
        self.parkinson = ParkinsonVolatility(window=20)

        # Hurst exponent
        self.hurst = HurstExponent(max_prices=500)

        # Track last trade price for various calculations
        self.last_trade_price: Optional[float] = None

        # OHLC accumulator for bar-based metrics
        self.current_bar = {
            'open': None,
            'high': None,
            'low': None,
            'close': None,
            'volume': 0.0,
            'start_ts': None
        }

        logger.info("Analytics Engine initialized with all 12+ metrics")

    def process_order_book(
        self,
        bids: List[Tuple[Decimal, Decimal]],
        asks: List[Tuple[Decimal, Decimal]],
        timestamp_ms: int
    ) -> Dict[str, Any]:
        """
        Process order book snapshot and calculate book-based metrics.

        Args:
            bids: List of (price, quantity) tuples, sorted descending
            asks: List of (price, quantity) tuples, sorted ascending
            timestamp_ms: Timestamp in milliseconds

        Returns:
            Dictionary of order book metrics
        """
        metrics = {}

        if not bids or not asks:
            logger.warning("Empty order book data")
            return metrics

        try:
            # Calculate spreads
            best_bid = bids[0][0]
            best_ask = asks[0][0]
            spread_metrics = self.spread_calculator.calculate_spread(best_bid, best_ask)
            metrics.update({
                'spread_absolute': float(spread_metrics['absolute']),
                'spread_relative_bps': float(spread_metrics['relative_bps']),
                'midpoint': float(spread_metrics['midpoint'])
            })

            # Order book imbalance
            obi_value = self.obi.calculate(bids, asks, levels=10)
            weighted_obi = self.obi.calculate_weighted(bids, asks, levels=10, decay=0.85)
            metrics['obi'] = float(obi_value)
            metrics['weighted_obi'] = weighted_obi
            metrics['obi_signal'] = self.obi.get_imbalance_signal()

            # Order flow imbalance
            book_top = BookTop(
                bid_price=best_bid,
                bid_qty=bids[0][1],
                ask_price=best_ask,
                ask_qty=asks[0][1]
            )
            ofi_value = self.ofi.update(book_top)
            if ofi_value is not None:
                metrics['ofi'] = float(ofi_value)
                metrics['cumulative_ofi'] = float(self.ofi.get_cumulative())
                metrics['ofi_signal'] = self.ofi.get_signal()

            # Update prices for other metrics
            mid_price = float((best_bid + best_ask) / 2)
            self.roll_spread.update(mid_price)
            self.hurst.add_price(mid_price)

        except Exception as e:
            logger.error(f"Error processing order book: {e}")

        return metrics

    def process_trade(
        self,
        timestamp_ms: int,
        price: Decimal,
        quantity: Decimal,
        side: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process a trade and update trade-based metrics.

        Args:
            timestamp_ms: Trade timestamp in milliseconds
            price: Trade price
            quantity: Trade volume
            side: 'buy' or 'sell' (aggressor side)

        Returns:
            Dictionary of trade-based metrics
        """
        metrics = {}

        try:
            price_float = float(price)
            quantity_float = float(quantity)

            # VWAP
            self.vwap.add_trade(timestamp_ms, price, quantity)
            vwap_values = self.vwap.get_values()
            metrics.update(vwap_values)

            # Realized volatility
            self.realized_vol.add_trade(timestamp_ms, price_float)
            rv_metrics = self.realized_vol.get_metrics()
            metrics['realized_vol'] = rv_metrics['realized_vol']
            metrics['vol_term_structure'] = rv_metrics['term_structure']

            # Amihud illiquidity
            amihud_value = self.amihud.update(price_float, quantity_float)
            if amihud_value is not None:
                metrics['amihud'] = amihud_value
                metrics['amihud_liquidity'] = self.amihud.get_liquidity_assessment()

            # VPIN (aggregate trades into bars)
            if self.last_trade_price is not None:
                self.vpin.add_bar(self.last_trade_price, price_float, quantity_float)
                vpin_value = self.vpin.value()
                if vpin_value is not None:
                    metrics['vpin'] = vpin_value
                    metrics['vpin_toxicity'] = self.vpin.get_toxicity_level()

            # Update OHLC bar
            self._update_ohlc_bar(timestamp_ms, price_float, quantity_float)

            # Kyle's Lambda interval tracking
            if self.interval_start_price is None:
                self.interval_start_price = price_float

            # Track for next iteration
            self.last_trade_price = price_float
            self.interval_trade_count += 1

        except Exception as e:
            logger.error(f"Error processing trade: {e}")

        return metrics

    def process_ohlc_bar(
        self,
        open_: float,
        high: float,
        low: float,
        close: float,
        volume: float,
        timestamp_ms: int
    ) -> Dict[str, Any]:
        """
        Process an OHLC bar for bar-based metrics.

        Args:
            open_: Opening price
            high: High price
            low: Low price
            close: Closing price
            volume: Bar volume
            timestamp_ms: Bar close timestamp

        Returns:
            Dictionary of OHLC-based metrics
        """
        metrics = {}

        try:
            # Garman-Klass volatility
            self.garman_klass.add_bar(open_, high, low, close)
            gk_vol = self.garman_klass.value()
            if gk_vol is not None:
                metrics['garman_klass_vol'] = gk_vol
                metrics['garman_klass_annual'] = self.garman_klass.annualized()

            # Parkinson volatility
            self.parkinson.add_bar(high, low)
            park_vol = self.parkinson.value()
            if park_vol is not None:
                metrics['parkinson_vol'] = park_vol
                metrics['parkinson_annual'] = self.parkinson.annualized()

            # VPIN
            self.vpin.add_bar(open_, close, volume)
            vpin_value = self.vpin.value()
            if vpin_value is not None:
                metrics['vpin'] = vpin_value
                metrics['vpin_toxicity'] = self.vpin.get_toxicity_level()

            # Kyle's Lambda (process accumulated interval)
            if self.interval_start_price is not None and self.interval_trade_count > 0:
                self.kyles_lambda.add_interval(close, self.interval_signed_volume)
                lambda_metrics = self.kyles_lambda.get_metrics()
                if lambda_metrics['lambda'] is not None:
                    metrics['kyles_lambda'] = lambda_metrics['lambda']
                    metrics['price_impact'] = lambda_metrics['price_impact_per_unit']
                    metrics['lambda_r_squared'] = lambda_metrics['r_squared']

                # Reset interval tracking
                self.interval_signed_volume = 0.0
                self.interval_start_price = close
                self.interval_trade_count = 0

        except Exception as e:
            logger.error(f"Error processing OHLC bar: {e}")

        return metrics

    def _update_ohlc_bar(self, timestamp_ms: int, price: float, volume: float):
        """Update internal OHLC bar accumulator."""
        # Initialize bar if needed
        if self.current_bar['start_ts'] is None:
            self.current_bar['start_ts'] = timestamp_ms
            self.current_bar['open'] = price
            self.current_bar['high'] = price
            self.current_bar['low'] = price

        # Update OHLC
        self.current_bar['high'] = max(self.current_bar['high'], price)
        self.current_bar['low'] = min(self.current_bar['low'], price)
        self.current_bar['close'] = price
        self.current_bar['volume'] += volume

        # Check if we should close the bar (1-minute bars)
        if timestamp_ms - self.current_bar['start_ts'] >= 60000:
            # Process the completed bar
            self.process_ohlc_bar(
                self.current_bar['open'],
                self.current_bar['high'],
                self.current_bar['low'],
                self.current_bar['close'],
                self.current_bar['volume'],
                timestamp_ms
            )

            # Reset for next bar
            self.current_bar = {
                'open': None,
                'high': None,
                'low': None,
                'close': None,
                'volume': 0.0,
                'start_ts': None
            }

    def get_all_metrics(self) -> Dict[str, Any]:
        """
        Get comprehensive snapshot of all current metric values.

        Returns:
            Dictionary containing all available metrics
        """
        metrics = {}

        try:
            # Spread metrics
            if self.spread_calculator.last_spread_metrics:
                metrics.update({
                    'spread_absolute': float(self.spread_calculator.last_spread_metrics['absolute']),
                    'spread_relative_bps': float(self.spread_calculator.last_spread_metrics['relative_bps']),
                    'midpoint': float(self.spread_calculator.last_spread_metrics['midpoint'])
                })

            # VWAP
            metrics.update(self.vwap.get_values())

            # Order book imbalance
            metrics.update(self.obi.get_last_values())

            # Order flow imbalance
            metrics.update(self.ofi.get_metrics())

            # Kyle's Lambda
            lambda_metrics = self.kyles_lambda.get_metrics()
            if lambda_metrics['lambda'] is not None:
                metrics['kyles_lambda'] = lambda_metrics['lambda']
                metrics['price_impact'] = lambda_metrics['price_impact_per_unit']
                metrics['lambda_liquidity'] = self.kyles_lambda.get_liquidity_assessment()

            # VPIN
            vpin_metrics = self.vpin.get_metrics()
            if vpin_metrics['vpin'] is not None:
                metrics['vpin'] = vpin_metrics['vpin']
                metrics['vpin_toxicity'] = vpin_metrics['toxicity_level']

            # Amihud
            amihud_metrics = self.amihud.get_metrics()
            if amihud_metrics['amihud'] is not None:
                metrics['amihud'] = amihud_metrics['amihud']
                metrics['amihud_liquidity'] = amihud_metrics['liquidity']

            # Roll spread
            roll_metrics = self.roll_spread.get_metrics()
            if roll_metrics['roll_spread'] is not None:
                metrics['roll_spread'] = roll_metrics['roll_spread']
                metrics['roll_regime'] = roll_metrics['market_regime']

            # Realized volatility
            rv_metrics = self.realized_vol.get_metrics()
            metrics['realized_vol'] = rv_metrics['realized_vol']
            metrics['vol_annualized'] = rv_metrics['annualized']
            metrics['vol_term_structure'] = rv_metrics['term_structure']

            # Garman-Klass
            gk_metrics = self.garman_klass.get_metrics()
            if gk_metrics['gk_volatility'] is not None:
                metrics['garman_klass_vol'] = gk_metrics['gk_volatility']
                metrics['garman_klass_annual'] = gk_metrics['gk_annualized']

            # Parkinson
            park_metrics = self.parkinson.get_metrics()
            if park_metrics['parkinson_volatility'] is not None:
                metrics['parkinson_vol'] = park_metrics['parkinson_volatility']
                metrics['parkinson_annual'] = park_metrics['parkinson_annualized']

            # Hurst exponent
            hurst_metrics = self.hurst.get_metrics()
            if hurst_metrics['hurst_exponent'] is not None:
                metrics['hurst_exponent'] = hurst_metrics['hurst_exponent']
                metrics['hurst_regime'] = hurst_metrics['market_regime']
                metrics['hurst_strategy'] = hurst_metrics['strategy']

            # Add timestamp
            metrics['timestamp'] = int(time.time() * 1000)

        except Exception as e:
            logger.error(f"Error getting all metrics: {e}")

        return metrics