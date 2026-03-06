# QuantFlow — Week Build Spec (MVP)

**What:** Real-time order book analyzer with AI pattern detection for crypto markets.
**Why:** Portfolio proof that you can build low-latency financial systems with AI — without a finance degree.
**Timeline:** 5-7 days with Claude Code

---

## What It Does

Connect to live crypto exchange WebSocket feeds, ingest and process order book data in real-time, detect patterns using statistical + AI methods, and display everything on a live dashboard.

A recruiter opens it, sees a live order book updating in real-time with AI annotations flagging suspicious patterns. That's the "wow."

---

## Architecture

```
Binance/Coinbase WebSocket
        │
        ▼
┌──────────────────┐
│  Ingestion Layer  │  Python (FastAPI + websockets)
│  - Connect to WS  │  - Normalize order book snapshots
│  - Buffer + store  │  - Publish to internal event bus
└────────┬─────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌────────┐ ┌──────────┐
│ Stats  │ │ AI Layer │
│ Engine │ │          │
│        │ │ Pattern  │
│ VWAP   │ │ Detector │
│ Spread │ │          │
│ Depth  │ │ Spoofing │
│ Flow   │ │ Walls    │
│ Imbal. │ │ Icebergs │
└───┬────┘ └────┬─────┘
    │           │
    ▼           ▼
┌──────────────────┐
│   WebSocket API   │  Streams to frontend
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│   Next.js Dashboard  │
│                      │
│  Live Order Book     │
│  Depth Chart         │
│  Trade Tape          │
│  AI Alert Feed       │
│  Stats Panel         │
└──────────────────┘
```

---

## Tech Stack

| Layer | Tech | Why |
|-------|------|-----|
| Backend | Python 3.12, FastAPI, uvicorn | Industry standard for quant, async WebSocket handling |
| Data Feed | Binance WebSocket API (free, no auth needed for public data) | Best free real-time order book data |
| Processing | NumPy, pandas | Fast numerical computation |
| AI Detection | Rule-based + Claude API for complex patterns | Hybrid: fast rules + smart AI |
| Storage | SQLite + in-memory ring buffer | Zero config, fast enough for MVP |
| Frontend | Next.js 15, TypeScript, Tailwind | Your bread and butter |
| Charts | Lightweight Charts (TradingView) + D3.js | Professional financial charts |
| Real-time | WebSocket (server→client) | Sub-second updates |
| Deploy | Vercel (frontend) + Railway (backend) | Free tier, instant |

---

## Day-by-Day Build Plan

### Day 1: Data Ingestion
- [ ] Project scaffold (FastAPI + Next.js monorepo)
- [ ] Binance WebSocket connection (order book depth stream)
- [ ] Order book data normalization (bids/asks, timestamps, quantities)
- [ ] In-memory ring buffer for last N snapshots
- [ ] Basic health check / status endpoint

### Day 2: Statistical Engine
- [ ] Real-time metrics computation:
  - **Spread** (bid-ask spread, % spread)
  - **VWAP** (Volume Weighted Average Price)
  - **Order book imbalance** (bid volume vs ask volume ratio)
  - **Depth at levels** (cumulative volume at 0.1%, 0.5%, 1% from mid)
  - **Trade flow** (buy vs sell aggressor)
- [ ] Rolling window calculations (1m, 5m, 15m)
- [ ] WebSocket broadcast to frontend clients

### Day 3: AI Pattern Detection
- [ ] Rule-based detectors (fast, no API cost):
  - **Spoofing** — large orders placed and cancelled within seconds
  - **Walls** — unusually large orders at a single price level (>3σ from mean)
  - **Iceberg detection** — repeated fills at same price suggesting hidden liquidity
  - **Momentum ignition** — rapid series of aggressive orders in one direction
- [ ] Claude API integration for complex pattern analysis:
  - Feed 30-second order book snapshots
  - Ask for anomaly classification + confidence score
  - Rate-limited (1 call per 10 seconds to manage costs)
- [ ] Alert event system (pattern type, confidence, timestamp, context)

### Day 4: Frontend — Live Dashboard
- [ ] WebSocket client connecting to backend
- [ ] **Order Book Visualization** — heatmap or stacked depth chart, live updating
- [ ] **Depth Chart** — TradingView Lightweight Charts for price/depth
- [ ] **Trade Tape** — scrolling list of recent trades with buy/sell coloring
- [ ] **AI Alert Feed** — live alerts with severity badges (info/warning/critical)
- [ ] **Stats Panel** — spread, VWAP, imbalance, volume metrics

### Day 5: Polish + Deploy
- [ ] Dark theme (financial dashboards are always dark)
- [ ] Responsive layout (but optimized for desktop — this is a pro tool)
- [ ] Loading states, error handling, reconnection logic
- [ ] README with architecture diagram, screenshots, "how to run"
- [ ] Deploy: Vercel (frontend) + Railway (backend)
- [ ] Record 30-second demo GIF for GitHub README

---

## Data Sources (Free, No Auth)

```python
# Binance WebSocket — no API key needed for public data
wss://stream.binance.com:9443/ws/btcusdt@depth20@100ms  # Order book (top 20 levels, 100ms)
wss://stream.binance.com:9443/ws/btcusdt@trade           # Individual trades
wss://stream.binance.com:9443/ws/btcusdt@kline_1m        # Candlesticks
```

Can also add Coinbase (`wss://ws-feed.exchange.coinbase.com`) for multi-exchange comparison.

---

## What Makes This Impressive

1. **Real-time systems** — not a Jupyter notebook, not a backtest. Live data, live processing, live UI.
2. **AI + finance** — hybrid detection (rules for speed, LLM for nuance) shows architectural thinking.
3. **Full stack** — data pipeline → processing → AI → WebSocket → dashboard. Every layer built.
4. **Domain knowledge** — understanding order book mechanics, market microstructure concepts.
5. **Production quality** — error handling, reconnection, proper architecture. Not a toy.

---

## Scope Boundaries (MVP)

**In scope:**
- Single trading pair (BTC/USDT)
- Real-time order book + trades
- Statistical metrics
- AI pattern detection (4-5 patterns)
- Live dashboard

**Out of scope (see full spec):**
- Multiple exchanges / pairs
- Historical data storage + replay
- Backtesting engine
- Actual trading / order execution
- User accounts / auth
- Mobile responsive
