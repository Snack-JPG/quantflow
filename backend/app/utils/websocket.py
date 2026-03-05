"""WebSocket connection management for broadcasting to frontend clients."""

import asyncio
import json
import logging
from typing import Dict, List, Set

from fastapi import WebSocket
from starlette.websockets import WebSocketState

from ..models import OrderBookSnapshot, Trade


logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections and broadcasts data to clients."""

    def __init__(self):
        """Initialize connection manager."""
        # Active connections by client ID
        self.active_connections: Dict[str, WebSocket] = {}

        # Subscriptions: symbol -> set of client IDs
        self.subscriptions: Dict[str, Set[str]] = {}

        # Lock for thread-safe operations
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, client_id: str) -> None:
        """Accept new WebSocket connection."""
        await websocket.accept()
        async with self._lock:
            self.active_connections[client_id] = websocket
            logger.info(f"Client {client_id} connected. Total connections: {len(self.active_connections)}")

    async def disconnect(self, client_id: str) -> None:
        """Remove WebSocket connection."""
        async with self._lock:
            if client_id in self.active_connections:
                del self.active_connections[client_id]

                # Remove from all subscriptions
                for symbol_subs in self.subscriptions.values():
                    symbol_subs.discard(client_id)

                logger.info(f"Client {client_id} disconnected. Remaining connections: {len(self.active_connections)}")

    async def subscribe(self, client_id: str, symbol: str) -> None:
        """Subscribe client to symbol updates."""
        async with self._lock:
            if symbol not in self.subscriptions:
                self.subscriptions[symbol] = set()
            self.subscriptions[symbol].add(client_id)
            logger.info(f"Client {client_id} subscribed to {symbol}")

    async def unsubscribe(self, client_id: str, symbol: str) -> None:
        """Unsubscribe client from symbol updates."""
        async with self._lock:
            if symbol in self.subscriptions:
                self.subscriptions[symbol].discard(client_id)
                logger.info(f"Client {client_id} unsubscribed from {symbol}")

    async def send_personal_message(self, message: dict, client_id: str) -> None:
        """Send message to specific client."""
        if client_id in self.active_connections:
            websocket = self.active_connections[client_id]
            if websocket.client_state == WebSocketState.CONNECTED:
                try:
                    await websocket.send_json(message)
                except Exception as e:
                    logger.error(f"Error sending message to {client_id}: {e}")
                    await self.disconnect(client_id)

    async def broadcast_orderbook(self, snapshot: OrderBookSnapshot) -> None:
        """Broadcast order book snapshot to subscribed clients."""
        # Get subscribed clients
        client_ids = self.subscriptions.get(snapshot.symbol, set()).copy()

        if not client_ids:
            return

        # Prepare message
        message = {
            "type": "orderbook",
            "data": {
                "exchange": snapshot.exchange,
                "symbol": snapshot.symbol,
                "timestamp": snapshot.timestamp_us,
                "sequence": snapshot.sequence,
                "bids": [[str(level.price), str(level.quantity)] for level in snapshot.bids[:20]],
                "asks": [[str(level.price), str(level.quantity)] for level in snapshot.asks[:20]],
                "mid_price": str(snapshot.mid_price) if snapshot.mid_price else None,
                "spread": str(snapshot.spread) if snapshot.spread else None,
                "spread_bps": str(snapshot.spread_bps) if snapshot.spread_bps else None,
            }
        }

        # Send to all subscribed clients
        tasks = []
        for client_id in client_ids:
            if client_id in self.active_connections:
                tasks.append(self.send_personal_message(message, client_id))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def broadcast_trade(self, trade: Trade) -> None:
        """Broadcast trade to subscribed clients."""
        # Get subscribed clients
        client_ids = self.subscriptions.get(trade.symbol, set()).copy()

        if not client_ids:
            return

        # Prepare message
        message = {
            "type": "trade",
            "data": {
                "exchange": trade.exchange,
                "symbol": trade.symbol,
                "timestamp": trade.timestamp_us,
                "price": str(trade.price),
                "quantity": str(trade.quantity),
                "side": trade.side,
                "trade_id": trade.trade_id,
                "value": str(trade.value),
            }
        }

        # Send to all subscribed clients
        tasks = []
        for client_id in client_ids:
            if client_id in self.active_connections:
                tasks.append(self.send_personal_message(message, client_id))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def broadcast_stats(self, symbol: str, stats: dict) -> None:
        """Broadcast market stats to subscribed clients."""
        # Get subscribed clients
        client_ids = self.subscriptions.get(symbol, set()).copy()

        if not client_ids:
            return

        # Prepare message
        message = {
            "type": "stats",
            "data": {
                "symbol": symbol,
                **stats
            }
        }

        # Send to all subscribed clients
        tasks = []
        for client_id in client_ids:
            if client_id in self.active_connections:
                tasks.append(self.send_personal_message(message, client_id))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def broadcast_analytics(self, symbol: str, analytics: dict) -> None:
        """Broadcast microstructure analytics to subscribed clients."""
        # Get subscribed clients
        client_ids = self.subscriptions.get(symbol, set()).copy()

        if not client_ids:
            return

        # Prepare message
        message = {
            "type": "analytics",
            "data": {
                "symbol": symbol,
                **analytics
            }
        }

        # Send to all subscribed clients
        tasks = []
        for client_id in client_ids:
            if client_id in self.active_connections:
                tasks.append(self.send_personal_message(message, client_id))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)