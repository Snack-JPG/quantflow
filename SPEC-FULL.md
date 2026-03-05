# QuantFlow — Full System Spec

**What:** Production-grade, multi-exchange order book intelligence platform with AI-powered market microstructure analysis, backtesting, and strategy simulation.
**Why:** The kind of system that makes quant firms ask "wait, you built this yourself?"
**Timeline:** 2-4 weeks with Claude Code (Austin's right — these estimates compress)

---

## Vision

QuantFlow isn't a dashboard that shows candles. It's a market microstructure analysis platform — the kind of tool quant researchers actually use internally. It ingests raw order book data from multiple exchanges simultaneously, computes institutional-grade analytics, detects manipulation patterns using AI, and lets you backtest strategies against historical order flow.

The difference between this and every other "crypto dashboard" on GitHub: this one understands *why* prices move, not just *that* they moved.

---

## Architecture

```
                    ┌─────────────────────────────────────────┐
                    │           Exchange Connectors            │
                    │                                         │
                    │  Binance  Coinbase  Kraken  Bybit  OKX  │
                    │    WS        WS       WS     WS    WS   │
                    └────────────────┬────────────────────────┘
                                     │
                                     ▼
                    ┌─────────────────────────────────────────┐
                    │         Ingestion Gateway               │
                    │                                         │
                    │  - Normalize across exchanges           │
                    │  - Unified order book format            │
                    │  - Sequence numbering                   │
                    │  - Gap detection + recovery             │
                    │  - Heartbeat monitoring                 │
                    └────────────────┬────────────────────────┘
                                     │
                         ┌───────────┼───────────┐
                         ▼           ▼           ▼
                    ┌─────────┐ ┌─────────┐ ┌─────────┐
                    │ In-Mem  │ │ TimeSer │ │ Event   │
                    │ Engine  │ │ Storage │ │ Bus     │
                    │         │ │         │ │         │
                    │ Ring    │ │ QuestDB │ │ Redis   │
                    │ Buffers │ │ or      │ │ Pub/Sub │
                    │ L3 Book │ │ TimescDB│ │         │
                    └────┬────┘ └────┬────┘ └────┬────┘
                         │          │           │
              ┌──────────┼──────────┼───────────┘
              │          │          │
              ▼          ▼          ▼
┌──────────────────────────────────────────────────────────┐
│                    Analytics Layer                        │
│                                                          │
│  ┌────────────┐  ┌────────────┐  ┌─────────────────┐    │
│  │ Micro-     │  │ AI Pattern │  │ Strategy        │    │
│  │ structure  │  │ Detection  │  │ Engine          │    │
│  │            │  │            │  │                 │    │
│  │ Spread     │  │ Spoofing   │  │ Signal Gen      │    │
│  │ VWAP       │  │ Layering   │  │ Backtesting     │    │
│  │ Kyle λ     │  │ Wash Trade │  │ Walk-Forward    │    │
│  │ PIN        │  │ Icebergs   │  │ PnL Tracking    │    │
│  │ Toxicity   │  │ Momentum   │  │ Risk Metrics    │    │
│  │ Amihud     │  │ Ignition   │  │ Sharpe/Sortino  │    │
│  │ Roll       │  │ Front-Run  │  │ Max Drawdown    │    │
│  │ Realized   │  │ Painting   │  │ Position Sizing │    │
│  │ Vol        │  │            │  │                 │    │
│  └────────────┘  └────────────┘  └─────────────────┘    │
│                                                          │
│  ┌────────────────────────────────────────────────────┐  │
│  │              Cross-Exchange Arbitrage               │  │
│  │  - Price discrepancy detection                     │  │
│  │  - Latency-adjusted spread                         │  │
│  │  - Triangular arb scanner                          │  │
│  └────────────────────────────────────────────────────┘  │
└──────────────────────────┬───────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────┐
│                      API Layer                           │
│                                                          │
│  REST (FastAPI)          WebSocket (real-time)            │
│  - Historical queries    - Live order book               │
│  - Backtest runs         - Live analytics                │
│  - Strategy CRUD         - Alert stream                  │
│  - Export/download       - Cross-exchange feed           │
└──────────────────────────┬───────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────┐
│                   Next.js Frontend                       │
│                                                          │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────┐  │
│  │ Live     │ │ Analysis │ │ Strategy │ │ Research  │  │
│  │ Trading  │ │ Lab      │ │ Builder  │ │ Console   │  │
│  │ View     │ │          │ │          │ │           │  │
│  │          │ │ Heatmaps │ │ Visual   │ │ NL Query  │  │
│  │ Book     │ │ Flow     │ │ Strategy │ │ "Show me  │  │
│  │ Depth    │ │ Toxicity │ │ Editor   │ │  spoofing │  │
│  │ Tape     │ │ Regimes  │ │ Backtest │ │  events   │  │
│  │ Alerts   │ │ Cross-Ex │ │ Results  │ │  last 24h"│  │
│  │ Stats    │ │ Compare  │ │ PnL Crv  │ │           │  │
│  └──────────┘ └──────────┘ └──────────┘ └───────────┘  │
└──────────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer | Tech | Why |
|-------|------|-----|
| **Backend** | Python 3.12, FastAPI, uvicorn | Quant industry standard |
| **Async Runtime** | asyncio + uvloop | High-throughput event processing |
| **Exchange Connectors** | aiohttp + websockets | Async multi-exchange connections |
| **In-Memory** | NumPy arrays + custom ring buffers | Sub-millisecond order book ops |
| **Time-Series DB** | TimescaleDB (PostgreSQL extension) | Production-grade, SQL-compatible, free |
| **Message Bus** | Redis Pub/Sub | Decouple ingestion from analytics |
| **AI Detection** | Rule engine + Claude API | Fast rules + deep analysis |
| **Strategy Engine** | Custom event-driven backtester | No dependency on external libs |
| **Frontend** | Next.js 15, TypeScript, Tailwind | Full-stack consistency |
| **Charts** | TradingView Lightweight Charts + D3.js + Three.js (3D vol surface) | Pro-grade financial viz |
| **Real-Time** | WebSocket (server→client) | Live streaming |
| **Deploy** | Docker Compose → Railway/Fly.io | One-command deploy |
| **CI/CD** | GitHub Actions | Auto-test, auto-deploy |

---

## Module Breakdown

### Module 1: Exchange Connectors (Day 1-2)

Unified interface for multiple exchanges. Each connector normalizes to a common format.

```python
@dataclass
class OrderBookSnapshot:
    exchange: str
    symbol: str
    timestamp_us: int          # Microsecond precision
    sequence: int              # Exchange sequence number
    bids: list[PriceLevel]     # [(price, quantity), ...] sorted desc
    asks: list[PriceLevel]     # [(price, quantity), ...] sorted asc
    
@dataclass
class Trade:
    exchange: str
    symbol: str
    timestamp_us: int
    price: Decimal
    quantity: Decimal
    side: Literal["buy", "sell"]  # Aggressor side
    trade_id: str

@dataclass
class PriceLevel:
    price: Decimal
    quantity: Decimal
    order_count: int | None    # Some exchanges provide this
```

**Exchanges:**
- **Binance** — deepest liquidity, best free data
- **Coinbase** — L3 order book (individual orders, not just levels)
- **Kraken** — good for cross-exchange comparison
- **Bybit** — derivatives/perps data
- **OKX** — additional depth

Each connector handles:
- Connection management (reconnect, backoff)
- Heartbeat monitoring
- Sequence gap detection + snapshot recovery
- Rate limit compliance

### Module 2: Order Book Engine (Day 2-3)

The core data structure — maintains a live, consistent order book in memory.

```python
class OrderBook:
    """Maintains L2 order book with full history ring buffer."""
    
    def apply_delta(self, delta: OrderBookDelta) -> None: ...
    def get_snapshot(self, depth: int = 20) -> OrderBookSnapshot: ...
    def get_mid_price(self) -> Decimal: ...
    def get_spread(self) -> Decimal: ...
    def get_depth_at_bps(self, bps: int) -> tuple[Decimal, Decimal]: ...
    def get_imbalance(self, levels: int = 5) -> float: ...
    def get_vwap(self, side: str, quantity: Decimal) -> Decimal: ...
```

Ring buffer stores last 10,000 snapshots (~17 minutes at 100ms intervals) for pattern detection lookback.

### Module 3: Microstructure Analytics (Day 3-5)

Research-grade market microstructure metrics. These are what separate a toy project from something a quant would actually respect.

**Liquidity Metrics:**
- **Bid-Ask Spread** — absolute and relative (bps)
- **Effective Spread** — actual cost of trading (using trade data)
- **Quoted Depth** — volume available at best bid/ask and N levels deep
- **VWAP** — volume-weighted average price over rolling windows
- **Amihud Illiquidity** — |return| / dollar volume (daily measure)
- **Kyle's Lambda (λ)** — price impact per unit of order flow (regression-based)

**Order Flow Metrics:**
- **Order Book Imbalance (OBI)** — (bid_vol - ask_vol) / (bid_vol + ask_vol)
- **Order Flow Imbalance (OFI)** — change in bid/ask quantities between snapshots
- **Trade Flow Toxicity (VPIN)** — Volume-Synchronized Probability of Informed Trading
- **Buy/Sell Pressure** — aggressor-side volume ratio

**Volatility Metrics:**
- **Realized Volatility** — from trade returns (1m, 5m, 15m, 1h windows)
- **Garman-Klass Volatility** — uses OHLC for better estimation
- **Parkinson Volatility** — high-low range estimator
- **Roll Spread Estimator** — implied spread from return autocovariance

**Market Regime Detection:**
- **Hurst Exponent** — trending (H>0.5) vs mean-reverting (H<0.5)
- **Regime Classification** — trending / ranging / volatile / quiet (HMM-based)

### Module 4: AI Pattern Detection (Day 5-7)

Two-tier detection system: fast rule-based engine for obvious patterns, Claude API for nuanced analysis.

**Rule-Based Detectors (< 1ms):**

| Pattern | Detection Method | Confidence |
|---------|-----------------|------------|
| **Spoofing** | Large order placed → cancelled within 2s, repeated 3+ times in 5 min | Size relative to avg + cancel speed |
| **Layering** | Multiple large orders at sequential price levels, all cancelled together | Order correlation + timing |
| **Walls** | Single price level with >3σ quantity vs mean level size, persists >30s | Statistical outlier test |
| **Iceberg Orders** | Repeated fills at same price, quantity replenishes consistently | Fill pattern + quantity consistency |
| **Momentum Ignition** | Burst of aggressive orders (>5 in 2s), one direction, >2σ volume | Volume spike + directional bias |
| **Wash Trading** | Buy and sell at same price within 1s, similar quantities | Price + quantity + timing match |
| **Tape Painting** | Cluster of small trades at progressively higher/lower prices | Trade size + price direction pattern |
| **Front-Running** | Large order appears → small orders execute ahead of it → large order moves price | Sequence + timing analysis |

**AI-Powered Analysis (Claude API, rate-limited):**
- Feed 60-second order book + trade snapshots as structured data
- Classify market regime (accumulation, distribution, markup, markdown — Wyckoff)
- Detect complex multi-step manipulation that rules can't catch
- Generate natural language explanations of detected patterns
- Confidence scoring with reasoning chain

**Alert System:**
```python
@dataclass
class Alert:
    id: str
    timestamp: datetime
    pattern: str              # "spoofing", "iceberg", etc.
    severity: Literal["info", "warning", "critical"]
    confidence: float         # 0.0 - 1.0
    exchange: str
    symbol: str
    context: dict             # Supporting data
    explanation: str          # Human-readable description
    ai_generated: bool        # Rule-based or AI
```

### Module 5: Strategy Engine + Backtester (Day 7-10)

Event-driven backtesting framework. No external libraries — built from scratch to show you understand the architecture.

**Core Components:**

```python
class Strategy(ABC):
    """Base class for all strategies."""
    
    @abstractmethod
    def on_book_update(self, book: OrderBookSnapshot) -> list[Signal]: ...
    
    @abstractmethod
    def on_trade(self, trade: Trade) -> list[Signal]: ...
    
    @abstractmethod
    def on_alert(self, alert: Alert) -> list[Signal]: ...

class Signal:
    direction: Literal["long", "short", "close"]
    strength: float           # -1.0 to 1.0
    reason: str
    metadata: dict

class BacktestEngine:
    """Event-driven backtester with realistic execution simulation."""
    
    def run(self, strategy: Strategy, data: DataFeed, config: BacktestConfig) -> BacktestResult: ...
    
class BacktestConfig:
    initial_capital: Decimal
    commission_bps: float     # Trading fees
    slippage_model: str       # "fixed", "proportional", "order_book"
    position_sizing: str      # "fixed", "kelly", "risk_parity"
    max_position_pct: float   # Max % of capital per position
    
class BacktestResult:
    trades: list[TradeRecord]
    equity_curve: pd.Series
    metrics: PerformanceMetrics

class PerformanceMetrics:
    total_return: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    max_drawdown_duration: timedelta
    win_rate: float
    profit_factor: float
    avg_trade_pnl: Decimal
    avg_holding_period: timedelta
    calmar_ratio: float
    trades_per_day: float
```

**Built-In Strategies (examples):**

1. **Order Book Imbalance Mean Reversion**
   - Signal: OBI > threshold → expect price reversion
   - Entry: OBI crosses ±0.7, exit on mean reversion or timeout
   
2. **VPIN Toxicity Fade**
   - Signal: High VPIN → informed trading → follow the flow
   - Entry: VPIN spike > 0.8, trade in direction of flow
   
3. **Spoofing Detection Alpha**
   - Signal: Detected spoofing → trade opposite to the fake orders
   - Entry: Spoofing alert with confidence > 0.8, trade against spoof direction

4. **Cross-Exchange Arbitrage**
   - Signal: Price discrepancy between exchanges > threshold + fees
   - Entry: Buy cheap exchange, sell expensive (simulated)

### Module 6: Cross-Exchange Intelligence (Day 10-12)

**Price Discrepancy Monitor:**
- Track same pair across all connected exchanges
- Compute latency-adjusted spreads (account for different feed speeds)
- Alert on arbitrage opportunities above fee threshold

**Triangular Arbitrage Scanner:**
- Monitor BTC/USDT, ETH/USDT, ETH/BTC simultaneously
- Detect circular arbitrage opportunities
- Account for order book depth (can you actually fill at those prices?)

**Lead-Lag Analysis:**
- Which exchange leads price discovery?
- Cross-correlation with lag optimization
- Granger causality tests between exchange prices

### Module 7: Frontend (Day 12-16)

Four main views, all real-time:

**1. Live Trading View**
- Order book heatmap (price × time, color = quantity) — like Bookmap
- Depth chart with cumulative volume
- Trade tape with aggressor coloring
- Real-time metrics panel (spread, VWAP, imbalance, regime)
- AI alert feed with severity badges
- Multi-exchange price comparison strip

**2. Analysis Lab**
- Microstructure metric timeseries (select any metric, any timeframe)
- Order flow heatmap (time × price, color = net flow)
- Toxicity gauge (VPIN visualization)
- Regime timeline (colored bands showing market state over time)
- Cross-exchange correlation matrix
- Volume profile (horizontal histogram at price levels)

**3. Strategy Builder**
- Visual strategy configuration (select signals, thresholds, entry/exit rules)
- One-click backtest with progress bar
- Results dashboard: equity curve, drawdown chart, trade scatter plot
- Performance metrics table (Sharpe, Sortino, max DD, win rate, etc.)
- Walk-forward optimization results
- Strategy comparison (overlay multiple strategies)

**4. Research Console**
- Natural language query interface: "Show me all spoofing events in the last 24 hours"
- AI-powered market commentary: "What happened at 14:32 when BTC dropped 2%?"
- Data export (CSV, JSON) for any metric or time range
- Anomaly timeline with drill-down

**Visualization Tech:**
- TradingView Lightweight Charts — candlesticks, depth, overlays
- D3.js — heatmaps, flow diagrams, custom charts
- Three.js — 3D order book visualization (optional but impressive)
- Framer Motion — smooth transitions and loading states

### Module 8: Infrastructure (Day 16-18)

**Docker Compose Setup:**
```yaml
services:
  gateway:       # FastAPI backend
  timescaledb:   # Time-series storage
  redis:         # Pub/Sub + caching
  frontend:      # Next.js
  connector-*:   # One per exchange (scalable)
```

**Monitoring:**
- Health check endpoints for each connector
- Message throughput metrics
- Latency tracking (exchange → processing → frontend)
- Error rate dashboards

**Data Management:**
- Automatic retention policies (raw ticks: 7 days, 1-min aggregates: 90 days, daily: forever)
- Export/import for backtest datasets
- Snapshot + replay capability

**CI/CD:**
- GitHub Actions: lint, type-check, test, build, deploy
- Docker image build + push
- Automated deployment to Railway/Fly.io

### Module 9: Testing + Documentation (Throughout)

**Tests (important — quant hiring managers check for this):**
- Unit tests for order book operations
- Unit tests for every microstructure metric (validated against known values)
- Integration tests for exchange connectors (mock WebSocket)
- Backtest validation (known strategy on known data → known result)
- Load testing (how many messages/sec can it handle?)

**Documentation:**
- README with architecture diagram, screenshots, "why this exists"
- API documentation (auto-generated from FastAPI)
- Strategy development guide
- Metric glossary with academic references
- Performance benchmarks

---

## Data Sources

**Free, No Auth Required:**
```
Binance:  wss://stream.binance.com:9443/ws/btcusdt@depth20@100ms
Coinbase: wss://ws-feed.exchange.coinbase.com (subscribe to "level2")
Kraken:   wss://ws.kraken.com (subscribe to "book")
```

**Free with API Key:**
```
Bybit:    wss://stream.bybit.com/v5/public/spot
OKX:      wss://ws.okx.com:8443/ws/v5/public
```

**Historical Data (for backtesting):**
- Binance public data: https://data.binance.vision/ (free, massive archive)
- Kaggle crypto datasets
- CryptoDataDownload.com

---

## What Makes This "Quant-Grade"

1. **Market microstructure** — Kyle's Lambda, VPIN, Amihud, Roll estimator. These aren't in tutorials. They're in academic papers and prop trading desks.

2. **Multi-exchange** — real quant systems aggregate across venues. Single-exchange dashboards are toys.

3. **Event-driven backtester** — built from scratch, not Backtrader. Shows you understand the architecture, not just the API.

4. **AI integration that makes sense** — not "I put GPT on a chart." Genuine pattern detection with hybrid rule/LLM approach and proper confidence scoring.

5. **Production infrastructure** — Docker, CI/CD, monitoring, data retention. Not a Jupyter notebook.

6. **Tests** — the r/quant consensus: "the existence of tests in the repo will definitely convince me that the candidate is a worthwhile hire."

7. **Academic references** — citing the actual papers (Kyle 1985, Easley & O'Hara 1992, Ané & Geman 2000) shows intellectual curiosity beyond Stack Overflow.

---

## Build Order (Suggested)

| Phase | Days | What |
|-------|------|------|
| 1 | 1-2 | Exchange connectors + order book engine |
| 2 | 3-5 | Microstructure analytics (all metrics) |
| 3 | 5-7 | AI pattern detection (rules + Claude) |
| 4 | 7-10 | Strategy engine + backtester |
| 5 | 10-12 | Cross-exchange intelligence |
| 6 | 12-16 | Frontend (all 4 views) |
| 7 | 16-18 | Infrastructure (Docker, CI/CD, deploy) |
| 8 | 18-20 | Tests, docs, polish, demo recording |

**Realistic with Claude Code: 10-14 days** if you're shipping fast.

---

## Name Ideas

- **QuantFlow** — clean, professional
- **Orderflow.ai** — descriptive
- **Microstructure** — bold, academic
- **DeepBook** — plays on deep learning + order book
- **FlowState** — order flow + "being in the zone"
