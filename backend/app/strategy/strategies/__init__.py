"""
Built-in trading strategies.
"""
from .obi_mean_reversion import OBIMeanReversionStrategy
from .vpin_toxicity import VPINToxicityStrategy
from .spoofing_alpha import SpoofingAlphaStrategy
from .cross_exchange_arb import CrossExchangeArbStrategy

__all__ = [
    'OBIMeanReversionStrategy',
    'VPINToxicityStrategy',
    'SpoofingAlphaStrategy',
    'CrossExchangeArbStrategy'
]

# Strategy registry for easy access
STRATEGIES = {
    'obi_mean_reversion': OBIMeanReversionStrategy,
    'vpin_toxicity': VPINToxicityStrategy,
    'spoofing_alpha': SpoofingAlphaStrategy,
    'cross_exchange_arb': CrossExchangeArbStrategy
}