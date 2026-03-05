"""Claude API analyzer for advanced pattern detection.

Tier 2 detection using Claude API for complex patterns that rules can't catch.
"""

import os
import json
import asyncio
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import logging
from decimal import Decimal

import httpx

from .models import Alert, AlertSeverity
from ..models.market_data import OrderBookSnapshot, Trade

logger = logging.getLogger(__name__)


class ClaudeAnalyzer:
    """
    Claude API-based analyzer for complex market manipulation patterns.
    Rate-limited to 1 call per 10 seconds max.
    """

    def __init__(self,
                 exchange: str,
                 symbol: str,
                 rate_limit_seconds: int = 10,
                 snapshot_duration_seconds: int = 60):
        self.exchange = exchange
        self.symbol = symbol
        self.rate_limit_seconds = rate_limit_seconds
        self.snapshot_duration_seconds = snapshot_duration_seconds

        # Get API key from environment
        self.api_key = os.environ.get('ANTHROPIC_API_KEY')
        if not self.api_key:
            logger.warning("ANTHROPIC_API_KEY not set. Claude analysis disabled.")

        # Rate limiting
        self.last_api_call = None
        self.api_calls_made = 0

        # Data buffer for analysis
        self.book_buffer = []
        self.trade_buffer = []
        self.alert_buffer = []

        # Claude API endpoint
        self.api_url = "https://api.anthropic.com/v1/messages"

    def should_analyze(self) -> bool:
        """Check if we should run Claude analysis based on rate limits."""
        if not self.api_key:
            return False

        if self.last_api_call is None:
            return True

        elapsed = (datetime.utcnow() - self.last_api_call).total_seconds()
        return elapsed >= self.rate_limit_seconds

    def get_remaining_calls(self) -> int:
        """Get approximate remaining API calls for the hour."""
        # Conservative estimate: 360 calls per hour max
        max_calls_per_hour = 360
        if self.api_calls_made >= max_calls_per_hour:
            return 0
        return max_calls_per_hour - self.api_calls_made

    async def analyze(self,
                     book_snapshot: Optional[OrderBookSnapshot],
                     trades: Optional[List[Trade]],
                     rule_alerts: Optional[List[Alert]] = None) -> Optional[Alert]:
        """
        Analyze market data using Claude API.
        Returns Alert if manipulation pattern detected.
        """
        if not self.should_analyze():
            return None

        # Prepare data for Claude
        analysis_data = self._prepare_analysis_data(book_snapshot, trades, rule_alerts)
        if not analysis_data:
            return None

        # Create prompt for Claude
        prompt = self._create_analysis_prompt(analysis_data)

        try:
            # Call Claude API
            response = await self._call_claude_api(prompt)

            # Parse response
            alert = self._parse_claude_response(response)

            # Update rate limiting
            self.last_api_call = datetime.utcnow()
            self.api_calls_made += 1

            return alert

        except Exception as e:
            logger.error(f"Claude API error: {e}")
            return None

    def _prepare_analysis_data(self,
                              book_snapshot: Optional[OrderBookSnapshot],
                              trades: Optional[List[Trade]],
                              rule_alerts: Optional[List[Alert]]) -> Optional[Dict]:
        """Prepare structured data for Claude analysis."""
        data = {
            'timestamp': datetime.utcnow().isoformat(),
            'exchange': self.exchange,
            'symbol': self.symbol
        }

        # Add order book data
        if book_snapshot:
            data['order_book'] = {
                'bids': [
                    {'price': str(level.price), 'quantity': str(level.quantity)}
                    for level in book_snapshot.bids[:10]
                ],
                'asks': [
                    {'price': str(level.price), 'quantity': str(level.quantity)}
                    for level in book_snapshot.asks[:10]
                ],
                'mid_price': str((book_snapshot.bids[0].price + book_snapshot.asks[0].price) / 2)
                if book_snapshot.bids and book_snapshot.asks else None
            }

        # Add recent trades
        if trades:
            data['recent_trades'] = [
                {
                    'timestamp': trade.timestamp.isoformat(),
                    'price': str(trade.price),
                    'quantity': str(trade.quantity),
                    'side': trade.side
                }
                for trade in trades[-50:]  # Last 50 trades
            ]

        # Add rule-based alerts
        if rule_alerts:
            data['rule_alerts'] = [
                {
                    'pattern': alert.pattern,
                    'severity': alert.severity.value,
                    'confidence': alert.confidence,
                    'explanation': alert.explanation
                }
                for alert in rule_alerts
            ]

        return data if (book_snapshot or trades or rule_alerts) else None

    def _create_analysis_prompt(self, data: Dict) -> str:
        """Create prompt for Claude to analyze market data."""
        prompt = f"""Analyze this cryptocurrency market data for complex manipulation patterns.

Exchange: {data['exchange']}
Symbol: {data['symbol']}
Timestamp: {data['timestamp']}

"""

        if 'order_book' in data:
            prompt += f"""
Order Book Snapshot:
Top 10 Bids: {json.dumps(data['order_book']['bids'][:5], indent=2)}
Top 10 Asks: {json.dumps(data['order_book']['asks'][:5], indent=2)}
Mid Price: {data['order_book'].get('mid_price', 'N/A')}
"""

        if 'recent_trades' in data:
            prompt += f"""
Recent Trades (last 50):
{json.dumps(data['recent_trades'][:10], indent=2)}
... ({len(data['recent_trades'])} total trades)
"""

        if 'rule_alerts' in data:
            prompt += f"""
Rule-Based Detections:
{json.dumps(data['rule_alerts'], indent=2)}
"""

        prompt += """

Analyze for:
1. Market regime (Wyckoff: accumulation, distribution, markup, markdown)
2. Complex multi-step manipulation beyond simple patterns
3. Coordinated trading activity
4. Unusual order flow patterns
5. Hidden liquidity indicators

Respond in JSON format:
{
  "pattern_detected": true/false,
  "pattern_type": "string",
  "market_regime": "accumulation|distribution|markup|markdown|neutral",
  "confidence": 0.0-1.0,
  "severity": "info|warning|critical",
  "explanation": "detailed explanation",
  "indicators": ["list", "of", "observed", "indicators"]
}

Be conservative - only flag clear manipulation patterns with high confidence."""

        return prompt

    async def _call_claude_api(self, prompt: str) -> Dict:
        """Call Claude API with the analysis prompt."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.api_url,
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                },
                json={
                    "model": "claude-3-haiku-20240307",  # Fast, cost-effective model
                    "max_tokens": 500,
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "temperature": 0.3  # Lower temperature for more consistent analysis
                },
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()

    def _parse_claude_response(self, response: Dict) -> Optional[Alert]:
        """Parse Claude API response into an Alert object."""
        try:
            # Extract content from Claude's response
            content = response.get('content', [{}])[0].get('text', '{}')

            # Parse JSON response
            # Find JSON block in response
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if not json_match:
                logger.warning("No JSON found in Claude response")
                return None

            analysis = json.loads(json_match.group())

            if not analysis.get('pattern_detected'):
                return None

            # Map severity
            severity_map = {
                'info': AlertSeverity.INFO,
                'warning': AlertSeverity.WARNING,
                'critical': AlertSeverity.CRITICAL
            }

            # Create alert from Claude's analysis
            return Alert(
                timestamp=datetime.utcnow(),
                pattern=analysis.get('pattern_type', 'complex_manipulation'),
                severity=severity_map.get(analysis.get('severity', 'info'), AlertSeverity.INFO),
                confidence=float(analysis.get('confidence', 0.5)),
                exchange=self.exchange,
                symbol=self.symbol,
                context={
                    'market_regime': analysis.get('market_regime', 'unknown'),
                    'indicators': analysis.get('indicators', [])
                },
                explanation=analysis.get('explanation', 'Claude detected complex pattern'),
                ai_generated=True
            )

        except Exception as e:
            logger.error(f"Error parsing Claude response: {e}")
            return None