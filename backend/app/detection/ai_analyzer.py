"""
AI-powered market analysis using Claude API
"""
import os
import json
import asyncio
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from decimal import Decimal
import httpx

from .models import Alert, AlertSeverity
from ..models.market_data import OrderBookSnapshot, Trade


class AIAnalyzer:
    """
    AI-powered market regime analysis using Claude API.
    Rate-limited to prevent excessive API calls.
    """

    def __init__(self,
                 exchange: str,
                 symbol: str,
                 api_key: Optional[str] = None,
                 rate_limit_seconds: int = 10):
        self.exchange = exchange
        self.symbol = symbol
        self.api_key = api_key or os.getenv('ANTHROPIC_API_KEY')
        self.rate_limit_seconds = rate_limit_seconds
        self.last_call_time = None
        self.api_url = "https://api.anthropic.com/v1/messages"

    async def analyze(self,
                     snapshots: List[OrderBookSnapshot],
                     trades: List[Trade]) -> Optional[Alert]:
        """
        Analyze market data using Claude API for complex pattern detection.
        """
        # Check rate limiting
        if not self._can_make_request():
            return None

        if not self.api_key:
            print("Warning: ANTHROPIC_API_KEY not set, skipping AI analysis")
            return None

        # Prepare data for analysis
        analysis_data = self._prepare_market_data(snapshots, trades)

        try:
            # Make API request to Claude
            analysis_result = await self._call_claude_api(analysis_data)

            if analysis_result:
                return self._create_alert_from_analysis(analysis_result)

        except Exception as e:
            print(f"Error in AI analysis: {e}")

        return None

    def _can_make_request(self) -> bool:
        """Check if we can make a request based on rate limiting."""
        if self.last_call_time is None:
            return True

        elapsed = (datetime.utcnow() - self.last_call_time).total_seconds()
        return elapsed >= self.rate_limit_seconds

    def _prepare_market_data(self,
                            snapshots: List[OrderBookSnapshot],
                            trades: List[Trade]) -> Dict[str, Any]:
        """Prepare market data for AI analysis."""
        # Take last 60 seconds of data
        if not snapshots:
            return {}

        latest_snapshot = snapshots[-1]
        cutoff_time = latest_snapshot.timestamp_us - 60_000_000  # 60 seconds

        recent_snapshots = [s for s in snapshots if s.timestamp_us >= cutoff_time]
        recent_trades = [t for t in trades if t.timestamp_us >= cutoff_time] if trades else []

        # Calculate key metrics
        bid_ask_spreads = []
        order_book_imbalances = []
        mid_prices = []

        for snapshot in recent_snapshots[-20:]:  # Last 20 snapshots
            if snapshot.bids and snapshot.asks:
                bid = float(snapshot.bids[0].price)
                ask = float(snapshot.asks[0].price)
                mid = (bid + ask) / 2
                spread = ask - bid

                bid_ask_spreads.append(spread)
                mid_prices.append(mid)

                # Calculate order book imbalance
                bid_vol = sum(float(b.quantity) for b in snapshot.bids[:5])
                ask_vol = sum(float(a.quantity) for a in snapshot.asks[:5])
                if bid_vol + ask_vol > 0:
                    imbalance = (bid_vol - ask_vol) / (bid_vol + ask_vol)
                    order_book_imbalances.append(imbalance)

        # Trade flow analysis
        buy_volume = sum(float(t.quantity) for t in recent_trades if t.side == 'buy')
        sell_volume = sum(float(t.quantity) for t in recent_trades if t.side == 'sell')
        trade_count = len(recent_trades)

        # Price movement
        price_change = 0
        if len(mid_prices) >= 2:
            price_change = (mid_prices[-1] - mid_prices[0]) / mid_prices[0] * 100

        return {
            'exchange': self.exchange,
            'symbol': self.symbol,
            'timestamp': datetime.utcnow().isoformat(),
            'price_change_pct': round(price_change, 4),
            'current_mid_price': mid_prices[-1] if mid_prices else 0,
            'avg_spread': sum(bid_ask_spreads) / len(bid_ask_spreads) if bid_ask_spreads else 0,
            'avg_order_book_imbalance': sum(order_book_imbalances) / len(order_book_imbalances) if order_book_imbalances else 0,
            'buy_volume': buy_volume,
            'sell_volume': sell_volume,
            'trade_count': trade_count,
            'snapshot_count': len(recent_snapshots),
            'order_book_depth': {
                'bids': [
                    {'price': str(b.price), 'quantity': str(b.quantity)}
                    for b in latest_snapshot.bids[:10]
                ] if latest_snapshot.bids else [],
                'asks': [
                    {'price': str(a.price), 'quantity': str(a.quantity)}
                    for a in latest_snapshot.asks[:10]
                ] if latest_snapshot.asks else []
            }
        }

    async def _call_claude_api(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Call Claude API for market analysis."""
        self.last_call_time = datetime.utcnow()

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }

        prompt = f"""Analyze this cryptocurrency order book and trading data for market manipulation or regime classification.

Market Data:
- Exchange: {market_data.get('exchange')}
- Symbol: {market_data.get('symbol')}
- Price Change: {market_data.get('price_change_pct', 0):.2f}%
- Current Mid Price: ${market_data.get('current_mid_price', 0):.2f}
- Average Spread: ${market_data.get('avg_spread', 0):.4f}
- Order Book Imbalance: {market_data.get('avg_order_book_imbalance', 0):.3f}
- Buy Volume: {market_data.get('buy_volume', 0):.2f}
- Sell Volume: {market_data.get('sell_volume', 0):.2f}
- Trade Count: {market_data.get('trade_count', 0)}

Order Book Depth:
Bids: {json.dumps(market_data.get('order_book_depth', {}).get('bids', [])[:5], indent=2)}
Asks: {json.dumps(market_data.get('order_book_depth', {}).get('asks', [])[:5], indent=2)}

Classify the market regime using Wyckoff methodology (accumulation, distribution, markup, markdown) and identify any complex manipulation patterns that simple rules might miss.

Respond with a JSON object containing:
- regime: string (accumulation/distribution/markup/markdown/neutral)
- confidence: float (0.0-1.0)
- patterns_detected: list of strings
- explanation: string (brief explanation)
- severity: string (info/warning/critical)
"""

        payload = {
            "model": "claude-3-haiku-20240307",
            "max_tokens": 500,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.3
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    self.api_url,
                    headers=headers,
                    json=payload
                )

                if response.status_code == 200:
                    result = response.json()
                    content = result.get('content', [{}])[0].get('text', '')

                    # Parse JSON response
                    try:
                        # Extract JSON from the response
                        import re
                        json_match = re.search(r'\{.*\}', content, re.DOTALL)
                        if json_match:
                            analysis = json.loads(json_match.group())
                            return analysis
                    except json.JSONDecodeError:
                        print(f"Failed to parse Claude response as JSON: {content}")

                else:
                    print(f"Claude API error: {response.status_code} - {response.text}")

        except Exception as e:
            print(f"Error calling Claude API: {e}")

        return None

    def _create_alert_from_analysis(self, analysis: Dict[str, Any]) -> Alert:
        """Create an Alert from AI analysis results."""
        severity_map = {
            'info': AlertSeverity.INFO,
            'warning': AlertSeverity.WARNING,
            'critical': AlertSeverity.CRITICAL
        }

        patterns = analysis.get('patterns_detected', [])
        pattern_name = patterns[0] if patterns else f"ai_regime_{analysis.get('regime', 'unknown')}"

        return Alert(
            timestamp=datetime.utcnow(),
            pattern=pattern_name,
            severity=severity_map.get(analysis.get('severity', 'info'), AlertSeverity.INFO),
            confidence=float(analysis.get('confidence', 0.5)),
            exchange=self.exchange,
            symbol=self.symbol,
            context={
                'regime': analysis.get('regime', 'unknown'),
                'patterns': patterns,
                'ai_analysis': True
            },
            explanation=analysis.get('explanation', 'AI-detected market regime change'),
            ai_generated=True
        )