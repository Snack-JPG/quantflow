"""
QuantFlow - Main FastAPI application
Production-grade order book intelligence platform
"""

import asyncio
import logging
import uuid
from contextlib import asynccontextmanager
from typing import Dict, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .connectors import BinanceConnector, CoinbaseConnector, KrakenConnector
from .core import OrderBookManager
from .models import OrderBookSnapshot, Trade
from .utils import ConnectionManager
from .analytics import AnalyticsEngine
from .detection import DetectionEngine, Alert
from .arbitrage import (
    PriceDiscrepancyMonitor,
    TriangularArbitrageScanner,
    LeadLagAnalyzer
)


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global instances
order_book_manager = OrderBookManager()
connection_manager = ConnectionManager()
analytics_engine = AnalyticsEngine()
detection_engines: Dict[str, DetectionEngine] = {}  # Per-symbol detection engines
exchange_connectors: Dict[str, any] = {}  # Multiple exchange types

# Arbitrage detection instances
price_discrepancy_monitor = PriceDiscrepancyMonitor()
triangular_scanner = TriangularArbitrageScanner()
lead_lag_analyzer = LeadLagAnalyzer()


async def on_book_snapshot(snapshot: OrderBookSnapshot) -> None:
    """Handle incoming order book snapshot."""
    # Update order book
    book = await order_book_manager.get_or_create_book(snapshot.exchange, snapshot.symbol)
    await book.apply_snapshot(snapshot)

    # Broadcast to clients
    await connection_manager.broadcast_orderbook(snapshot)

    # Update arbitrage detectors
    await price_discrepancy_monitor.update_order_book(snapshot)
    await triangular_scanner.update_order_book(snapshot)
    await lead_lag_analyzer.update_order_book(snapshot)

    # Calculate analytics metrics
    bids = [(level.price, level.quantity) for level in snapshot.bids]
    asks = [(level.price, level.quantity) for level in snapshot.asks]
    analytics = analytics_engine.process_order_book(bids, asks, snapshot.timestamp_us)

    # Calculate and broadcast stats
    stats = {
        "mid_price": str(book.get_mid_price()) if book.get_mid_price() else None,
        "spread": str(book.get_spread()) if book.get_spread() else None,
        "spread_bps": str(book.get_spread_bps()) if book.get_spread_bps() else None,
        "imbalance": book.get_imbalance(levels=10),
        "bid_depth_10bps": str(book.get_depth_at_bps(10)[0]),
        "ask_depth_10bps": str(book.get_depth_at_bps(10)[1]),
        # Add microstructure analytics
        **analytics
    }
    await connection_manager.broadcast_stats(snapshot.symbol, stats)

    # Run pattern detection
    detection_key = f"{snapshot.exchange}:{snapshot.symbol}"
    if detection_key not in detection_engines:
        detection_engines[detection_key] = DetectionEngine(snapshot.exchange, snapshot.symbol)

    detection_engine = detection_engines[detection_key]

    # Create empty lists for trades and order events for now
    # In production, these would be populated from actual exchange data
    alerts = await detection_engine.detect_patterns(
        book_snapshot=snapshot,
        trades=[],  # Will be populated when we have recent trades
        order_events=None  # Would need L3 data for this
    )

    # Broadcast any alerts detected
    for alert in alerts:
        await connection_manager.broadcast_alert(alert.to_dict())


async def on_trade(trade: Trade) -> None:
    """Handle incoming trade."""
    # Process trade through analytics
    trade_metrics = analytics_engine.process_trade(
        timestamp_ms=trade.timestamp_us // 1000,
        price=trade.price,
        quantity=trade.quantity,
        side=trade.side if hasattr(trade, 'side') else None
    )

    # Update lead-lag analyzer with trade data
    await lead_lag_analyzer.update_trade(trade)

    # Add metrics to trade data
    trade_with_metrics = {
        "exchange": trade.exchange,
        "symbol": trade.symbol,
        "timestamp": trade.timestamp_us,
        "price": str(trade.price),
        "quantity": str(trade.quantity),
        "metrics": trade_metrics
    }

    # Broadcast to clients
    await connection_manager.broadcast_trade(trade)

    # Broadcast analytics update
    if trade_metrics:
        await connection_manager.broadcast_analytics(trade.symbol, trade_metrics)

    # Process trade through detection engine
    detection_key = f"{trade.exchange}:{trade.symbol}"
    if detection_key in detection_engines:
        # Run detection with the new trade
        alerts = await detection_engines[detection_key].detect_patterns(
            book_snapshot=None,
            trades=[trade],
            order_events=None
        )

        # Broadcast any alerts
        for alert in alerts:
            await connection_manager.broadcast_alert(alert.to_dict())


async def start_exchange_connectors():
    """Start exchange connectors."""
    global exchange_connectors

    # Default symbols to track
    symbols = ["BTCUSDT", "ETHUSDT", "ETHBTC"]  # Added ETHBTC for triangular arbitrage

    # Start Binance connector
    binance = BinanceConnector(
        symbols=symbols,
        on_book_snapshot=on_book_snapshot,
        on_trade=on_trade,
    )
    exchange_connectors["binance"] = binance

    # Start Coinbase connector
    coinbase = CoinbaseConnector(
        symbols=symbols,
        on_book_snapshot=on_book_snapshot,
        on_trade=on_trade,
    )
    exchange_connectors["coinbase"] = coinbase

    # Start Kraken connector
    kraken = KrakenConnector(
        symbols=symbols,
        on_book_snapshot=on_book_snapshot,
        on_trade=on_trade,
    )
    exchange_connectors["kraken"] = kraken

    # Run connectors in background
    asyncio.create_task(binance.run())
    asyncio.create_task(coinbase.run())
    asyncio.create_task(kraken.run())

    logger.info(f"Started exchange connectors for symbols: {symbols}")
    logger.info("Active exchanges: Binance, Coinbase, Kraken")


async def stop_exchange_connectors():
    """Stop all exchange connectors."""
    for name, connector in exchange_connectors.items():
        await connector.stop()
        logger.info(f"Stopped {name} connector")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting QuantFlow backend...")
    await start_exchange_connectors()

    yield

    # Shutdown
    logger.info("Shutting down QuantFlow backend...")
    await stop_exchange_connectors()


# Create FastAPI app
app = FastAPI(
    title="QuantFlow",
    description="Production-grade order book intelligence platform",
    version="0.1.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3001", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "QuantFlow",
        "version": "0.1.0",
        "status": "running",
        "exchanges": list(exchange_connectors.keys()),
    }


@app.get("/api/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "connectors": {
            name: connector.is_connected
            for name, connector in exchange_connectors.items()
        },
        "active_connections": len(connection_manager.active_connections),
    }


@app.get("/api/symbols")
async def get_symbols():
    """Get list of available symbols."""
    symbols = set()
    for book in (await order_book_manager.get_all_books()).values():
        symbols.add(book.symbol)
    return {"symbols": sorted(list(symbols))}


@app.get("/api/orderbook/{exchange}/{symbol}")
async def get_orderbook(exchange: str, symbol: str, depth: int = 20):
    """Get current order book snapshot."""
    book = await order_book_manager.get_book(exchange, symbol)
    if not book:
        return JSONResponse(
            status_code=404,
            content={"error": f"Order book not found for {exchange}:{symbol}"}
        )

    snapshot = await book.get_snapshot(depth=depth)
    return {
        "exchange": snapshot.exchange,
        "symbol": snapshot.symbol,
        "timestamp": snapshot.timestamp_us,
        "bids": [[str(level.price), str(level.quantity)] for level in snapshot.bids],
        "asks": [[str(level.price), str(level.quantity)] for level in snapshot.asks],
        "mid_price": str(snapshot.mid_price) if snapshot.mid_price else None,
        "spread": str(snapshot.spread) if snapshot.spread else None,
        "spread_bps": str(snapshot.spread_bps) if snapshot.spread_bps else None,
    }


@app.get("/api/stats/{symbol}")
async def get_stats(symbol: str):
    """Get aggregated stats for a symbol."""
    # Get aggregated book
    book = await order_book_manager.get_book("binance", symbol)  # Default to binance for now
    if not book:
        return JSONResponse(
            status_code=404,
            content={"error": f"No data available for {symbol}"}
        )

    return {
        "symbol": symbol,
        "mid_price": str(book.get_mid_price()) if book.get_mid_price() else None,
        "spread": str(book.get_spread()) if book.get_spread() else None,
        "spread_bps": str(book.get_spread_bps()) if book.get_spread_bps() else None,
        "imbalance": book.get_imbalance(levels=10),
        "bid_depth_10bps": str(book.get_depth_at_bps(10)[0]),
        "ask_depth_10bps": str(book.get_depth_at_bps(10)[1]),
        "bid_depth_25bps": str(book.get_depth_at_bps(25)[0]),
        "ask_depth_25bps": str(book.get_depth_at_bps(25)[1]),
    }


@app.get("/api/analytics/{symbol}")
async def get_analytics(symbol: str):
    """Get comprehensive microstructure analytics for a symbol."""
    # Get all current metrics from the analytics engine
    metrics = analytics_engine.get_all_metrics()

    # Add symbol for context
    metrics["symbol"] = symbol

    return metrics


@app.get("/api/alerts")
async def get_alerts(limit: int = 50):
    """Get recent alerts across all symbols."""
    all_alerts = []
    for detection_engine in detection_engines.values():
        # Get recent alerts from the engine's history
        engine_alerts = detection_engine.recent_alerts[-limit:] if hasattr(detection_engine, 'recent_alerts') else []
        all_alerts.extend([alert.to_dict() for alert in engine_alerts])

    # Sort by timestamp and limit
    all_alerts.sort(key=lambda x: x['timestamp'], reverse=True)
    return {"alerts": all_alerts[:limit]}


@app.get("/api/alerts/{exchange}/{symbol}")
async def get_symbol_alerts(exchange: str, symbol: str, limit: int = 50):
    """Get recent alerts for a specific symbol."""
    detection_key = f"{exchange}:{symbol}"
    if detection_key not in detection_engines:
        return {"alerts": []}

    engine = detection_engines[detection_key]
    alerts = engine.recent_alerts[-limit:] if hasattr(engine, 'recent_alerts') else []
    return {"alerts": [alert.to_dict() for alert in alerts]}


@app.get("/api/arbitrage/opportunities")
async def get_arbitrage_opportunities(
    symbol: Optional[str] = None,
    min_profit_pct: Optional[float] = None
):
    """Get current arbitrage opportunities across exchanges."""
    from decimal import Decimal

    opportunities = price_discrepancy_monitor.get_opportunities(
        symbol=symbol,
        min_profit_pct=Decimal(str(min_profit_pct)) if min_profit_pct else None
    )

    return {
        "opportunities": [
            {
                "timestamp": opp.timestamp.isoformat(),
                "symbol": opp.symbol,
                "buy_exchange": opp.buy_exchange,
                "sell_exchange": opp.sell_exchange,
                "buy_price": str(opp.buy_price),
                "sell_price": str(opp.sell_price),
                "spread_pct": str(opp.spread_pct),
                "potential_volume": str(opp.potential_volume),
                "estimated_profit": str(opp.estimated_profit),
                "confidence": opp.confidence,
                "latency_risk_ms": opp.latency_risk_ms
            }
            for opp in opportunities
        ],
        "statistics": price_discrepancy_monitor.get_statistics()
    }


@app.get("/api/arbitrage/triangular")
async def get_triangular_arbitrage(
    exchange: Optional[str] = None,
    min_profit_pct: Optional[float] = None
):
    """Get triangular arbitrage opportunities."""
    from decimal import Decimal

    opportunities = triangular_scanner.get_opportunities(
        exchange=exchange,
        min_profit_pct=Decimal(str(min_profit_pct)) if min_profit_pct else None
    )

    return {
        "opportunities": [
            {
                "timestamp": opp.timestamp.isoformat(),
                "exchange": opp.exchange,
                "path": [f"{step[0]} ({step[1]})" for step in opp.path],
                "profit_pct": str(opp.profit_pct),
                "confidence": opp.confidence,
                "execution_time_ms": opp.execution_time_ms
            }
            for opp in opportunities
        ],
        "statistics": triangular_scanner.get_statistics()
    }


@app.get("/api/arbitrage/lead-lag")
async def get_lead_lag_analysis(
    symbol: Optional[str] = None,
    min_correlation: Optional[float] = None
):
    """Get lead-lag analysis between exchanges."""
    results = lead_lag_analyzer.get_lead_lag_results(
        symbol=symbol,
        min_correlation=min_correlation
    )

    return {
        "results": [
            {
                "timestamp": result.timestamp.isoformat(),
                "symbol": result.symbol,
                "lead_exchange": result.lead_exchange,
                "lag_exchange": result.lag_exchange,
                "lag_ms": result.lag_ms,
                "correlation": result.correlation,
                "granger_pvalue": result.granger_causality_pvalue,
                "predictive_power": result.predictive_power
            }
            for result in results
        ],
        "statistics": lead_lag_analyzer.get_statistics()
    }


@app.get("/api/arbitrage/correlations/{symbol}")
async def get_exchange_correlations(symbol: str, min_correlation: Optional[float] = 0.5):
    """Get correlation analysis between exchanges for a symbol."""
    correlations = lead_lag_analyzer.get_correlations(
        symbol=symbol,
        min_correlation=min_correlation
    )

    return {
        "symbol": symbol,
        "correlations": [
            {
                "exchange1": corr.exchange1,
                "exchange2": corr.exchange2,
                "correlation": corr.correlation,
                "optimal_lag_ms": corr.optimal_lag_ms,
                "max_correlation": corr.max_correlation,
                "volatility_ratio": corr.volatility_ratio
            }
            for corr in correlations
        ]
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time data streaming."""
    client_id = str(uuid.uuid4())
    await connection_manager.connect(websocket, client_id)

    try:
        # Send initial connection message
        await websocket.send_json({
            "type": "connected",
            "client_id": client_id,
            "message": "Connected to QuantFlow WebSocket"
        })

        # Handle incoming messages
        while True:
            data = await websocket.receive_json()
            message_type = data.get("type")

            if message_type == "subscribe":
                symbol = data.get("symbol")
                if symbol:
                    await connection_manager.subscribe(client_id, symbol)
                    await websocket.send_json({
                        "type": "subscribed",
                        "symbol": symbol
                    })

            elif message_type == "unsubscribe":
                symbol = data.get("symbol")
                if symbol:
                    await connection_manager.unsubscribe(client_id, symbol)
                    await websocket.send_json({
                        "type": "unsubscribed",
                        "symbol": symbol
                    })

            elif message_type == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        await connection_manager.disconnect(client_id)
        logger.info(f"Client {client_id} disconnected")
    except Exception as e:
        logger.error(f"WebSocket error for client {client_id}: {e}")
        await connection_manager.disconnect(client_id)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)