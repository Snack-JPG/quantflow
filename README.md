# QuantFlow - Order Book Intelligence Platform

Production-grade, multi-exchange order book intelligence platform with real-time market microstructure analysis.

## Features

### Phase 1 Complete ✅
- **Exchange Connectors**: Binance WebSocket with automatic reconnection and heartbeat monitoring
- **Order Book Engine**: In-memory L2 book with 10,000 snapshot ring buffer
- **WebSocket Broadcasting**: Real-time streaming to frontend clients
- **Live Order Book Display**: 100ms updates with visual depth bars
- **Depth Chart**: Market depth visualization with TradingView Lightweight Charts
- **Trade Feed**: Real-time trade stream with aggressor side classification

## Tech Stack

- **Backend**: Python 3.12, FastAPI, asyncio, WebSockets
- **Frontend**: Next.js 15, TypeScript, Tailwind CSS 4, TradingView Charts
- **Infrastructure**: Docker Compose, Redis
- **Precision**: All calculations use Decimal (not float) for accuracy

## Quick Start

### Using Docker Compose (Recommended)

```bash
# Start all services
docker-compose up

# Backend will be available at http://localhost:8000
# Frontend will be available at http://localhost:3001
```

### Manual Setup

#### Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

#### Frontend
```bash
cd frontend
npm install
npm run dev
```

## Architecture

```
┌─────────────────────────┐
│   Binance WebSocket     │
│   (Order Book + Trades) │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│   Exchange Connector    │
│   - Reconnection        │
│   - Heartbeat Monitor   │
│   - Message Parsing     │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│   Order Book Engine     │
│   - In-Memory L2 Book   │
│   - Ring Buffer (10k)   │
│   - Decimal Precision   │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│   FastAPI + WebSocket   │
│   - REST API            │
│   - WS Broadcasting     │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│   Next.js Frontend      │
│   - Live Order Book     │
│   - Depth Chart         │
│   - Trade Feed          │
└─────────────────────────┘
```

## API Endpoints

### REST
- `GET /` - Service info
- `GET /api/health` - Health check
- `GET /api/symbols` - Available symbols
- `GET /api/orderbook/{exchange}/{symbol}` - Order book snapshot
- `GET /api/stats/{symbol}` - Market statistics

### WebSocket
- `ws://localhost:8000/ws` - Real-time data stream

WebSocket messages:
```javascript
// Subscribe to symbol
{ "type": "subscribe", "symbol": "BTCUSDT" }

// Receive order book updates
{ "type": "orderbook", "data": { ... } }

// Receive trades
{ "type": "trade", "data": { ... } }

// Receive stats
{ "type": "stats", "data": { ... } }
```

## Core Metrics

- **Bid-Ask Spread**: Absolute and relative (basis points)
- **Mid Price**: (Best Bid + Best Ask) / 2
- **Order Book Imbalance**: (Bid Vol - Ask Vol) / (Bid Vol + Ask Vol)
- **Market Depth**: Cumulative volume at N basis points from mid
- **VWAP**: Volume-weighted average price for order execution

## Development

### Project Structure
```
quant-engine/
├── backend/
│   ├── app/
│   │   ├── connectors/     # Exchange connectors
│   │   ├── core/          # Order book engine
│   │   ├── models/        # Data models
│   │   ├── utils/         # WebSocket manager
│   │   └── main.py        # FastAPI app
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── app/           # Next.js pages
│   │   ├── components/    # React components
│   │   ├── lib/           # Hooks and utilities
│   │   └── types/         # TypeScript types
│   └── package.json
└── docker-compose.yml
```

### Adding New Exchanges

The connector architecture uses an abstract base class, making it trivial to add new exchanges:

```python
class NewExchangeConnector(ExchangeConnector):
    async def connect(self) -> None:
        # Implement connection logic

    async def _handle_message(self, message: dict) -> None:
        # Parse exchange-specific format
```

## Phase 2 Roadmap

- [ ] Additional exchanges (Coinbase, Kraken, Bybit, OKX)
- [ ] Advanced microstructure metrics (Kyle's Lambda, VPIN, Amihud illiquidity)
- [ ] AI pattern detection (spoofing, layering, wash trading)
- [ ] Strategy backtesting engine
- [ ] Cross-exchange arbitrage detection
- [ ] Historical data storage (TimescaleDB)

## Production Considerations

1. **Precision**: All price/quantity calculations use Decimal type
2. **Reconnection**: Exponential backoff with max delay
3. **Sequence Gaps**: Detection and recovery mechanisms
4. **Memory Management**: Ring buffer prevents unbounded growth
5. **Error Handling**: Comprehensive logging and graceful degradation

## License

MIT