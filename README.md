# QuantFlow — Production-Grade Multi-Exchange Order Book Intelligence Platform

**Real-time market microstructure analysis, AI-powered pattern detection, and institutional-grade backtesting**

[![CI/CD Pipeline](https://github.com/Snack-JPG/quantflow/actions/workflows/ci.yml/badge.svg)](https://github.com/Snack-JPG/quantflow/actions)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://python.org)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0-blue.svg)](https://typescriptlang.org)
[![Docker](https://img.shields.io/badge/Docker-ready-green.svg)](https://docker.com)

## 🎯 Why This Exists

QuantFlow isn't another crypto dashboard showing candles. It's a market microstructure analysis platform — the kind of tool quant researchers use internally at trading firms. It ingests raw order book data from multiple exchanges simultaneously, computes institutional-grade analytics that you won't find in retail tools, detects manipulation patterns using hybrid rule/AI systems, and lets you backtest strategies against actual order flow, not just price ticks.

**The difference:** This system understands *why* prices move (order flow dynamics, liquidity imbalances, toxic flow), not just *that* they moved.

## 📊 Key Features

### Market Microstructure Analytics
- **Kyle's Lambda (λ)** — Price impact per unit of order flow
- **VPIN** — Volume-Synchronized Probability of Informed Trading
- **Amihud Illiquidity** — |return| / dollar volume measure
- **Roll Spread Estimator** — Implied spread from return autocovariance
- **Order Flow Imbalance** — Directional pressure metrics
- **Realized/Effective Spreads** — True trading costs beyond quoted spreads
- **Hurst Exponent** — Market regime detection (trending vs mean-reverting)

### AI-Powered Pattern Detection
- **Hybrid System** — Fast rule engine (<1ms) + Claude API for nuanced analysis
- **Detectable Patterns:**
  - Spoofing (large orders placed → cancelled)
  - Layering (coordinated multi-level manipulation)
  - Momentum ignition (aggressive directional bursts)
  - Iceberg orders (hidden size detection)
  - Wash trading (self-dealing detection)
  - Front-running (order anticipation patterns)

### Event-Driven Backtesting
Built from scratch (no external libraries) to demonstrate architecture understanding:
- **Sub-millisecond order book replay**
- **Realistic slippage modeling** (order book-based, not fixed)
- **Walk-forward optimization**
- **Risk metrics** — Sharpe, Sortino, Calmar, max drawdown
- **Position sizing** — Kelly criterion, risk parity

### Cross-Exchange Intelligence
- **Real-time arbitrage detection** across 5 exchanges
- **Lead-lag analysis** — Which exchange leads price discovery?
- **Triangular arbitrage** — BTC/USDT × ETH/USDT × ETH/BTC
- **Latency-adjusted spreads** — Account for feed delays

## 🏗️ Architecture

```
┌─────────────────────────────────────────┐
│           Exchange Connectors            │
│  Binance  Coinbase  Kraken  Bybit  OKX  │
│    WS        WS       WS     WS    WS   │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│         Ingestion Gateway               │
│  - Normalize across exchanges           │
│  - Unified order book format            │
│  - Sequence validation                  │
│  - Gap detection + recovery             │
└────────────────┬────────────────────────┘
                 │
     ┌───────────┼───────────┐
     ▼           ▼           ▼
┌─────────┐ ┌─────────┐ ┌─────────┐
│ In-Mem  │ │TimescDB │ │ Redis   │
│ Engine  │ │Storage  │ │ Pub/Sub │
│         │ │         │ │         │
│ 10k snap│ │7-day raw│ │Real-time│
│ buffer  │ │30-day ag│ │ events  │
└────┬────┘ └────┬────┘ └────┬────┘
     │          │           │
     └──────────┼───────────┘
                ▼
┌──────────────────────────────────────────────────────────┐
│                    Analytics Layer                        │
│                                                          │
│  ┌────────────┐  ┌────────────┐  ┌─────────────────┐    │
│  │ Micro-     │  │ AI Pattern │  │ Strategy        │    │
│  │ structure  │  │ Detection  │  │ Engine          │    │
│  │            │  │            │  │                 │    │
│  │ Kyle λ     │  │ Spoofing   │  │ Event-driven    │    │
│  │ VPIN       │  │ Layering   │  │ Backtesting     │    │
│  │ Amihud     │  │ Momentum   │  │ Walk-forward    │    │
│  │ Roll       │  │ Icebergs   │  │ Risk metrics    │    │
│  └────────────┘  └────────────┘  └─────────────────┘    │
│                                                          │
│  ┌────────────────────────────────────────────────────┐  │
│  │              Cross-Exchange Arbitrage               │  │
│  │  Price discrepancy • Lead-lag • Triangular arb     │  │
│  └────────────────────────────────────────────────────┘  │
└──────────────────────────┬───────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────┐
│                      API Layer                           │
│  FastAPI • WebSocket • REST • Real-time streaming        │
└──────────────────────────┬───────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────┐
│                   Next.js Frontend                       │
│  Live Trading • Analysis Lab • Strategy Builder • Research│
└──────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- 8GB RAM minimum
- 20GB disk space

### Run with Docker

```bash
# Clone repository
git clone https://github.com/Snack-JPG/quantflow.git
cd quantflow

# Start all services
docker-compose up -d

# Services will be available at:
# - Frontend: http://localhost:3000
# - API: http://localhost:8000
# - API Docs: http://localhost:8000/docs
```

### Run Locally (Development)

```bash
# Backend setup
cd backend
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend setup (new terminal)
cd frontend
npm install
npm run dev
```

## 📈 Performance Benchmarks

Measured on commodity hardware (Intel i7, 16GB RAM):

| Component | Metric | Performance |
|-----------|--------|------------|
| **Order Book Updates** | Throughput | >50,000 updates/sec |
| **Snapshot Generation** | Latency | <1ms (20 levels) |
| **VWAP Calculation** | Latency | <0.5ms |
| **WebSocket Processing** | Throughput | >50,000 msg/sec |
| **Microstructure Metrics** | All metrics (10k trades) | <500ms |
| **Backtesting Engine** | Events/sec | >100,000 |
| **End-to-End Latency** | Exchange → Analytics → API | <5ms |
| **Memory Usage** | Per order book (1000 levels) | <5MB |

## 🧪 Testing

Comprehensive test coverage ensures production reliability:

```bash
# Run all tests
pytest backend/tests/ -v

# Unit tests only
pytest backend/tests/unit/

# Integration tests
pytest backend/tests/integration/

# Performance benchmarks
pytest backend/tests/benchmarks/ --benchmark-only

# Coverage report
pytest --cov=app --cov-report=html
```

## 📚 API Documentation

Full API documentation is auto-generated and available at:
- **Local:** http://localhost:8000/docs
- **Swagger UI:** http://localhost:8000/redoc

### Key Endpoints

```python
GET  /api/v1/orderbook/{exchange}/{symbol}  # Real-time order book
GET  /api/v1/metrics/{metric}/{symbol}      # Microstructure metrics
POST /api/v1/backtest/run                   # Run backtest
GET  /api/v1/alerts/live                    # Pattern detection alerts
WS   /ws/orderbook/{symbol}                 # WebSocket stream
```

## 🏛️ Academic Foundation

This implementation is based on peer-reviewed research:

- **Kyle (1985)** — "Continuous Auctions and Insider Trading"
- **Easley & O'Hara (1992)** — "Time and the Process of Security Price Adjustment"
- **Amihud (2002)** — "Illiquidity and Stock Returns"
- **Roll (1984)** — "A Simple Implicit Measure of the Effective Bid-Ask Spread"
- **Hasbrouck (1995)** — "One Security, Many Markets"
- **Ané & Geman (2000)** — "Order Flow, Transaction Clock, and Normality of Asset Returns"

## 🤝 Contributing

Contributions are welcome! Please read our [Contributing Guide](CONTRIBUTING.md) first.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## ⚠️ Disclaimer

This software is for educational and research purposes only. It is not intended to be used for actual trading without thorough testing and validation. The authors are not responsible for any financial losses incurred through the use of this software.

## 📜 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Exchange data providers (Binance, Coinbase, Kraken)
- TimescaleDB team for the excellent time-series database
- FastAPI for the modern Python web framework
- The quantitative finance research community

