# QuantFlow API Documentation

## Base URL
```
http://localhost:8000
```

## Authentication
Currently, the API does not require authentication. In production, implement API key authentication.

## Endpoints

### Core Endpoints

#### GET /
Returns service information and status.

**Response:**
```json
{
  "name": "QuantFlow",
  "version": "0.1.0",
  "status": "running",
  "exchanges": ["binance", "coinbase", "kraken"]
}
```

#### GET /api/health
Health check endpoint for monitoring.

**Response:**
```json
{
  "status": "healthy",
  "connectors": {
    "binance": true,
    "coinbase": true,
    "kraken": false
  },
  "active_connections": 5
}
```

### Order Book Data

#### GET /api/orderbook/{exchange}/{symbol}
Get current order book snapshot for a specific exchange and symbol.

**Parameters:**
- `exchange` (path): Exchange name (binance, coinbase, kraken)
- `symbol` (path): Trading pair symbol (BTCUSDT, ETHUSDT, etc.)
- `depth` (query, optional): Number of price levels to return (default: 20)

**Response:**
```json
{
  "exchange": "binance",
  "symbol": "BTCUSDT",
  "timestamp": 1640000000000000,
  "bids": [
    ["50000.00", "1.5"],
    ["49999.00", "2.0"]
  ],
  "asks": [
    ["50001.00", "1.2"],
    ["50002.00", "0.8"]
  ],
  "mid_price": "50000.50",
  "spread": "1.00",
  "spread_bps": "2.00"
}
```

### Market Statistics

#### GET /api/stats/{symbol}
Get aggregated market statistics for a symbol across all exchanges.

**Parameters:**
- `symbol` (path): Trading pair symbol

**Response:**
```json
{
  "symbol": "BTCUSDT",
  "mid_price": "50000.50",
  "spread": "1.00",
  "spread_bps": "2.00",
  "imbalance": 0.15,
  "bid_depth_10bps": "125.5",
  "ask_depth_10bps": "98.3"
}
```

### Microstructure Metrics

#### GET /api/microstructure/{exchange}/{symbol}
Get advanced market microstructure metrics.

**Parameters:**
- `exchange` (path): Exchange name
- `symbol` (path): Trading pair symbol

**Response:**
```json
{
  "kyle_lambda": 0.00023,
  "vpin": 0.45,
  "amihud_illiquidity": 0.000012,
  "roll_spread": 0.98,
  "realized_volatility": 0.0234,
  "effective_spread": 1.02,
  "order_flow_imbalance": 0.12,
  "hurst_exponent": 0.48
}
```

### Pattern Detection & Alerts

#### GET /api/alerts/live
Get real-time pattern detection alerts.

**Query Parameters:**
- `severity` (optional): Filter by severity (info, warning, critical)
- `pattern` (optional): Filter by pattern type (spoofing, layering, etc.)
- `limit` (optional): Maximum number of alerts to return (default: 100)

**Response:**
```json
{
  "alerts": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "timestamp": "2024-01-01T12:00:00Z",
      "pattern": "spoofing",
      "severity": "warning",
      "confidence": 0.85,
      "exchange": "binance",
      "symbol": "BTCUSDT",
      "explanation": "Large buy order placed and cancelled within 2 seconds",
      "ai_generated": false
    }
  ]
}
```

### Cross-Exchange Arbitrage

#### GET /api/arbitrage/discrepancies
Get current price discrepancies across exchanges.

**Response:**
```json
{
  "discrepancies": [
    {
      "symbol": "BTCUSDT",
      "opportunity": {
        "buy_exchange": "kraken",
        "buy_price": "49995.00",
        "sell_exchange": "binance",
        "sell_price": "50005.00",
        "spread_pct": 0.02,
        "profit_after_fees": "8.50"
      }
    }
  ]
}
```

#### GET /api/arbitrage/triangular
Get triangular arbitrage opportunities.

**Response:**
```json
{
  "opportunities": [
    {
      "path": ["BTCUSDT", "ETHUSDT", "ETHBTC"],
      "profit_pct": 0.15,
      "required_capital": "10000.00",
      "expected_profit": "15.00"
    }
  ]
}
```

### Backtesting

#### POST /api/backtest/run
Run a backtest with specified strategy and parameters.

**Request Body:**
```json
{
  "strategy": "order_book_imbalance",
  "parameters": {
    "threshold": 0.7,
    "holding_period": 60
  },
  "start_date": "2024-01-01",
  "end_date": "2024-01-31",
  "initial_capital": 100000
}
```

**Response:**
```json
{
  "backtest_id": "bt_123456",
  "status": "completed",
  "results": {
    "total_return": 0.0234,
    "sharpe_ratio": 1.45,
    "sortino_ratio": 1.89,
    "max_drawdown": 0.0456,
    "win_rate": 0.58,
    "profit_factor": 1.34,
    "trades_count": 234
  }
}
```

#### GET /api/backtest/{backtest_id}/results
Get detailed results for a specific backtest.

**Response:**
```json
{
  "backtest_id": "bt_123456",
  "equity_curve": [[timestamp, value], ...],
  "trades": [
    {
      "entry_time": "2024-01-01T10:00:00Z",
      "exit_time": "2024-01-01T10:05:00Z",
      "side": "long",
      "entry_price": "50000.00",
      "exit_price": "50050.00",
      "pnl": "45.00",
      "return_pct": 0.001
    }
  ]
}
```

## WebSocket API

### Connection
```
ws://localhost:8000/ws
```

### Message Types

#### Subscribe to Symbol
```json
{
  "type": "subscribe",
  "symbol": "BTCUSDT"
}
```

#### Unsubscribe from Symbol
```json
{
  "type": "unsubscribe",
  "symbol": "BTCUSDT"
}
```

### Received Messages

#### Order Book Update
```json
{
  "type": "orderbook",
  "data": {
    "exchange": "binance",
    "symbol": "BTCUSDT",
    "timestamp": 1640000000000000,
    "bids": [...],
    "asks": [...],
    "mid_price": "50000.50"
  }
}
```

#### Trade
```json
{
  "type": "trade",
  "data": {
    "exchange": "binance",
    "symbol": "BTCUSDT",
    "timestamp": 1640000000000000,
    "price": "50000.00",
    "quantity": "0.5",
    "side": "buy"
  }
}
```

#### Market Statistics Update
```json
{
  "type": "stats",
  "data": {
    "symbol": "BTCUSDT",
    "mid_price": "50000.50",
    "spread": "1.00",
    "imbalance": 0.15,
    "metrics": {...}
  }
}
```

#### Alert
```json
{
  "type": "alert",
  "data": {
    "pattern": "spoofing",
    "severity": "warning",
    "exchange": "binance",
    "symbol": "BTCUSDT",
    "explanation": "Large order cancelled within 2 seconds"
  }
}
```

## Rate Limits

- **REST API**: 1000 requests per minute per IP
- **WebSocket**: 100 messages per second per connection

## Error Responses

All errors follow this format:
```json
{
  "error": "Error message",
  "detail": "Detailed explanation",
  "status_code": 400
}
```

### Common Error Codes
- `400` - Bad Request
- `404` - Resource Not Found
- `429` - Rate Limit Exceeded
- `500` - Internal Server Error
- `503` - Service Unavailable

## Data Types

### Decimal Precision
All numeric values are returned as strings to preserve decimal precision. Parse them using appropriate decimal libraries in your client.

### Timestamps
- Microsecond precision timestamps (Unix epoch * 1,000,000)
- ISO 8601 format for datetime strings

### Symbols
- Binance format: `BTCUSDT`, `ETHUSDT`
- Coinbase format: `BTC-USD`, `ETH-USD`
- Kraken format: `XBTUSD`, `ETHUSD`

## SDKs and Client Libraries

### Python Client Example
```python
import asyncio
import websockets
import json

async def connect_quantflow():
    uri = "ws://localhost:8000/ws"
    async with websockets.connect(uri) as websocket:
        # Subscribe to BTCUSDT
        await websocket.send(json.dumps({
            "type": "subscribe",
            "symbol": "BTCUSDT"
        }))

        # Receive updates
        while True:
            message = await websocket.recv()
            data = json.loads(message)
            print(f"Received: {data['type']}")

asyncio.run(connect_quantflow())
```

### JavaScript Client Example
```javascript
const ws = new WebSocket('ws://localhost:8000/ws');

ws.on('open', () => {
    // Subscribe to symbol
    ws.send(JSON.stringify({
        type: 'subscribe',
        symbol: 'BTCUSDT'
    }));
});

ws.on('message', (data) => {
    const message = JSON.parse(data);
    console.log(`Received ${message.type}:`, message.data);
});
```

## Changelog

### Version 0.1.0 (Current)
- Initial release
- Support for Binance, Coinbase, Kraken
- Real-time order book streaming
- Basic microstructure metrics
- Pattern detection (spoofing, layering)
- Cross-exchange arbitrage detection
- Event-driven backtesting engine