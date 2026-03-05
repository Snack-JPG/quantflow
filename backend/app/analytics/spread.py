"""Bid-Ask Spread metrics implementation.

Source: Market microstructure fundamentals; formalized in Demsetz (1968),
"The Cost of Transacting."
"""

from decimal import Decimal
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class BidAskSpread:
    """
    Calculates bid-ask spread metrics: absolute, relative (bps), and effective.

    The bid-ask spread measures the cost of immediate execution — the premium a
    liquidity taker pays to transact immediately rather than waiting for a counterparty.
    """

    def __init__(self):
        """Initialize the BidAskSpread calculator."""
        self.last_spread_metrics: Optional[Dict[str, Decimal]] = None

    def calculate_spread(self, best_bid: Decimal, best_ask: Decimal) -> Dict[str, Decimal]:
        """
        Calculate all spread variants.

        Args:
            best_bid: The best (highest) bid price
            best_ask: The best (lowest) ask price

        Returns:
            Dictionary containing:
            - absolute: Absolute spread (ask - bid)
            - midpoint: Midpoint price
            - relative_bps: Relative spread in basis points
        """
        try:
            if best_bid <= 0 or best_ask <= 0:
                logger.warning(f"Invalid prices: bid={best_bid}, ask={best_ask}")
                return {
                    'absolute': Decimal('0'),
                    'midpoint': Decimal('0'),
                    'relative_bps': Decimal('0')
                }

            midpoint = (best_bid + best_ask) / 2
            absolute = best_ask - best_bid

            if midpoint > 0:
                relative_bps = (absolute / midpoint) * Decimal('10000')
            else:
                relative_bps = Decimal('0')

            self.last_spread_metrics = {
                'absolute': absolute,
                'midpoint': midpoint,
                'relative_bps': relative_bps
            }

            logger.debug(f"Spread: abs={absolute:.8f}, mid={midpoint:.8f}, bps={relative_bps:.2f}")

            return self.last_spread_metrics

        except Exception as e:
            logger.error(f"Error calculating spread: {e}")
            return {
                'absolute': Decimal('0'),
                'midpoint': Decimal('0'),
                'relative_bps': Decimal('0')
            }

    def calculate_effective_spread(
        self,
        trade_price: Decimal,
        best_bid: Decimal,
        best_ask: Decimal
    ) -> Decimal:
        """
        Calculate the effective spread for a single trade.

        The effective spread measures actual execution cost, accounting for trades
        that execute at or inside the quoted spread.

        Args:
            trade_price: The actual execution price
            best_bid: The best bid at time of trade
            best_ask: The best ask at time of trade

        Returns:
            Effective spread (2 × |trade_price - midpoint|)
        """
        try:
            if best_bid <= 0 or best_ask <= 0:
                return Decimal('0')

            midpoint = (best_bid + best_ask) / 2
            effective_spread = 2 * abs(trade_price - midpoint)

            logger.debug(f"Effective spread: {effective_spread:.8f} (trade={trade_price:.8f})")

            return effective_spread

        except Exception as e:
            logger.error(f"Error calculating effective spread: {e}")
            return Decimal('0')

    def get_last_metrics(self) -> Optional[Dict[str, Decimal]]:
        """Get the last calculated spread metrics."""
        return self.last_spread_metrics