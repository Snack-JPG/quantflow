# NarrativeFlow — Crypto Narrative Rotation Tracker

**What:** A tool that detects which crypto narratives are gaining momentum BEFORE prices move, by cross-referencing social sentiment with on-chain data.

**Why it's a huge play:**
1. Portfolio piece that demonstrates data engineering + AI + real-time systems
2. Actually useful — you can trade with it
3. Natural extension of QuantFlow — same architecture, different data sources
4. Nobody has built a good open-source version of this

**The Core Insight:** Narratives follow a lifecycle:
```
CT whispers → Alpha groups → Mainstream CT → News articles → Retail FOMO → Price peak → Crash
```
The money is made in the gap between "CT whispers" and "News articles." NarrativeFlow detects that gap.

---

## How It Works

```
┌─────────────────────────────────────────────────┐
│              DATA COLLECTION LAYER               │
│                                                  │
│  ┌──────────┐ ┌──────────┐ ┌──────────────────┐ │
│  │ Social   │ │ On-Chain │ │ Market Data      │ │
│  │          │ │          │ │                  │ │
│  │ X/Twitter│ │ DeFiLlama│ │ CoinGecko API    │ │
│  │ Reddit   │ │ Dune     │ │ Binance/CEX      │ │
│  │ Telegram │ │ Nansen   │ │ DEX volumes      │ │
│  │ Discord  │ │ Arkham   │ │ Funding rates    │ │
│  │ YouTube  │ │          │ │ Open interest    │ │
│  └────┬─────┘ └────┬─────┘ └───────┬──────────┘ │
│       │            │               │             │
└───────┼────────────┼───────────────┼─────────────┘
        │            │               │
        ▼            ▼               ▼
┌─────────────────────────────────────────────────┐
│              PROCESSING LAYER                    │
│                                                  │
│  ┌──────────────────────────────────────────┐   │
│  │         Narrative Classification          │   │
│  │                                          │   │
│  │  Every token/mention gets tagged:         │   │
│  │  AI | RWA | DePIN | Memecoin | L1/L2 |   │   │
│  │  NFT | DeFi | Gaming | Privacy |         │   │
│  │  Derivatives | Social | Infrastructure   │   │
│  └──────────────────────────────────────────┘   │
│                                                  │
│  ┌──────────────────────────────────────────┐   │
│  │         Sentiment Scoring                 │   │
│  │                                          │   │
│  │  Per narrative per time window:           │   │
│  │  - Mention velocity (mentions/hour)       │   │
│  │  - Sentiment polarity (bullish/bearish)   │   │
│  │  - Influencer signal (weighted by reach)  │   │
│  │  - Novelty score (new discussion or old)  │   │
│  └──────────────────────────────────────────┘   │
│                                                  │
│  ┌──────────────────────────────────────────┐   │
│  │         On-Chain Momentum                 │   │
│  │                                          │   │
│  │  Per narrative per time window:           │   │
│  │  - TVL change (DeFiLlama)                │   │
│  │  - Active addresses change               │   │
│  │  - Volume change (DEX + CEX)             │   │
│  │  - Whale accumulation (Nansen/Arkham)    │   │
│  │  - Funding rate direction                │   │
│  └──────────────────────────────────────────┘   │
│                                                  │
│  ┌──────────────────────────────────────────┐   │
│  │         DIVERGENCE DETECTOR 🔥            │   │
│  │                                          │   │
│  │  THE KEY SIGNAL:                         │   │
│  │                                          │   │
│  │  Social buzz ↑ + On-chain activity ↑     │   │
│  │  BUT price hasn't moved yet              │   │
│  │  = EARLY ENTRY WINDOW                    │   │
│  │                                          │   │
│  │  Social buzz ↑ + Price already ↑↑↑       │   │
│  │  BUT on-chain activity flat              │   │
│  │  = LATE / EXIT SIGNAL                    │   │
│  │                                          │   │
│  │  Social buzz ↓ + On-chain activity ↑     │   │
│  │  = SMART MONEY ACCUMULATING              │   │
│  │                                          │   │
│  │  Everything ↓                            │   │
│  │  = DEAD NARRATIVE (avoid)                │   │
│  └──────────────────────────────────────────┘   │
│                                                  │
│  ┌──────────────────────────────────────────┐   │
│  │         AI Analysis Layer                 │   │
│  │                                          │   │
│  │  Claude/GPT processes raw social data:    │   │
│  │  - "What are people actually saying?"     │   │
│  │  - "Is this new alpha or recycled takes?" │   │
│  │  - "Which influencers are leading this?"  │   │
│  │  - "What catalyst is driving the buzz?"   │   │
│  │  - Daily narrative briefing generation    │   │
│  └──────────────────────────────────────────┘   │
└─────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────┐
│                   OUTPUT LAYER                    │
│                                                  │
│  ┌───────────────────────────────────────────┐  │
│  │          Dashboard (Next.js)              │  │
│  │                                           │  │
│  │  1. NARRATIVE HEATMAP                     │  │
│  │     Rows = narratives (AI, RWA, DePIN..)  │  │
│  │     Cols = time (24h, 7d, 30d)            │  │
│  │     Color = momentum score                │  │
│  │     Shows rotation in real-time           │  │
│  │                                           │  │
│  │  2. DIVERGENCE ALERTS                     │  │
│  │     "AI narrative buzz up 340% this week  │  │
│  │      but TAO price only up 12%. Early?"   │  │
│  │                                           │  │
│  │  3. NARRATIVE LIFECYCLE TRACKER           │  │
│  │     Where is each narrative in its cycle?  │  │
│  │     Whisper → Emerging → Mainstream →     │  │
│  │     Peak FOMO → Declining → Dead          │  │
│  │                                           │  │
│  │  4. TOP TOKENS PER NARRATIVE              │  │
│  │     Ranked by: sentiment × on-chain ×     │  │
│  │     inverse-price-move (undervalued)      │  │
│  │                                           │  │
│  │  5. WHALE WATCH                           │  │
│  │     Smart money flows by narrative sector │  │
│  │                                           │  │
│  │  6. DAILY AI BRIEFING                     │  │
│  │     "Today's narratives: AI agents saw    │  │
│  │      a 5x spike in CT mentions after      │  │
│  │      Coinbase launched Agentic Wallets.   │  │
│  │      On-chain: TAO TVL up 23%, NEAR       │  │
│  │      active addresses up 15%. Price flat. │  │
│  │      This looks early."                   │  │
│  └───────────────────────────────────────────┘  │
│                                                  │
│  ┌───────────────────────────────────────────┐  │
│  │          Telegram Bot Alerts              │  │
│  │                                           │  │
│  │  Push notifications:                      │  │
│  │  🔥 "RWA narrative entering FOMO phase"   │  │
│  │  🟢 "DePIN: social buzz ↑ price flat"     │  │
│  │  🔴 "Memecoins: exit signal detected"     │  │
│  │  🐋 "Whale accumulation: ONDO +$5M 24h"  │  │
│  └───────────────────────────────────────────┘  │
│                                                  │
│  ┌───────────────────────────────────────────┐  │
│  │          Historical Backtest              │  │
│  │                                           │  │
│  │  "If you'd followed divergence signals    │  │
│  │   in 2024-2025, here's what happened..."  │  │
│  │                                           │  │
│  │  Proves the thesis with real data.        │  │
│  │  This is the portfolio piece.             │  │
│  └───────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘
```

---

## Data Sources (Mostly Free)

### Social Data
| Source | Method | Cost |
|--------|--------|------|
| **X/Twitter** | X API v2 — search recent tweets, filter by crypto KOLs | Free tier: 10K tweets/mo. Basic: $100/mo for 100K |
| **Reddit** | Reddit API — r/cryptocurrency, r/solana, r/defi etc | Free |
| **YouTube** | YouTube Data API — video titles, descriptions, comments | Free (quota-limited) |
| **Telegram** | Telethon (Python) — monitor public alpha groups | Free |
| **Discord** | Discord.py — monitor public servers | Free |

### On-Chain Data
| Source | Method | Cost |
|--------|--------|------|
| **DeFiLlama** | Public API — TVL by protocol, chain, category | Free |
| **Dune Analytics** | Public dashboards + API | Free tier available |
| **CoinGecko** | API — prices, market caps, volumes, categories | Free tier: 30 calls/min |
| **Birdeye** | Solana token data, DEX volumes | Free tier available |
| **Helius** | Solana on-chain data (you already have experience) | Free tier |

### Market Data
| Source | Method | Cost |
|--------|--------|------|
| **Binance** | WebSocket API — prices, funding rates, OI | Free |
| **CoinGecko Categories** | Market cap by narrative sector | Free |

### Smart Money (Premium — Add Later)
| Source | Method | Cost |
|--------|--------|------|
| **Nansen** | Whale wallet tracking, smart money labels | $100+/mo |
| **Arkham Intelligence** | Entity tracking, fund flows | Free tier + paid |

---

## Architecture (Reuses QuantFlow)

This is the key insight — NarrativeFlow and QuantFlow share 60-70% of infrastructure:

| Component | QuantFlow | NarrativeFlow |
|-----------|-----------|---------------|
| Data ingestion | Exchange WebSocket | Social APIs + DeFiLlama |
| Processing engine | Microstructure metrics | Sentiment scoring + narrative classification |
| AI layer | Pattern detection | Narrative analysis + briefing generation |
| Time-series storage | TimescaleDB | TimescaleDB (same) |
| Event bus | Redis Pub/Sub | Redis Pub/Sub (same) |
| Frontend | Next.js dashboard | Next.js dashboard (same framework) |
| Alerting | Dashboard alerts | Telegram bot alerts |
| Backtesting | Strategy backtester | Narrative signal backtester |

**Build QuantFlow first → Fork/extend into NarrativeFlow.** The core infrastructure (data pipeline, storage, frontend, alerting) carries over directly.

---

## Tech Stack

| Layer | Tech |
|-------|------|
| Backend | Python 3.12, FastAPI |
| Social Scraping | Tweepy (X), PRAW (Reddit), Telethon (Telegram), aiohttp |
| NLP/Sentiment | Claude API for classification + sentiment. VADER/TextBlob for fast pre-filtering |
| On-Chain | DeFiLlama API, Dune API, CoinGecko API, Helius |
| Storage | TimescaleDB (time-series), Redis (cache + pub/sub) |
| Frontend | Next.js 15, TradingView charts, D3.js heatmaps |
| Alerts | grammY (Telegram bot — you already have experience from NFT tracker) |
| Deploy | Docker Compose → Railway/Fly.io |

---

## Build Phases

### Phase 1: Data Collection (Days 1-3)
- [ ] Social data ingestion: X API (search by crypto keywords, filter KOLs)
- [ ] Reddit scraper: r/cryptocurrency, r/solana, r/defi, r/altcoin
- [ ] CoinGecko categories API: market cap + volume by sector
- [ ] DeFiLlama API: TVL by protocol and chain
- [ ] Binance API: funding rates, OI, prices for top 50 tokens
- [ ] Store everything in TimescaleDB with narrative tags

### Phase 2: Narrative Classification + Sentiment (Days 3-5)
- [ ] Build narrative taxonomy (AI, RWA, DePIN, Memecoin, L1/L2, NFT, DeFi, Gaming, etc.)
- [ ] Auto-classify every social mention into narrative bucket(s)
- [ ] Sentiment scoring per mention (bullish/bearish/neutral + confidence)
- [ ] Mention velocity calculation (mentions/hour rolling windows)
- [ ] Influencer weighting (verified accounts, follower count, engagement ratio)
- [ ] Novelty scoring (is this new alpha or recycled takes?)

### Phase 3: Divergence Detection Engine (Days 5-7)
- [ ] Compute narrative momentum scores: social_buzz × on_chain_activity
- [ ] Compute price momentum per narrative basket
- [ ] DIVERGENCE SIGNAL: high narrative momentum + low price momentum = early entry
- [ ] LATE SIGNAL: high price momentum + declining narrative momentum = exit
- [ ] ACCUMULATION SIGNAL: low social + high on-chain = smart money
- [ ] Assign lifecycle stage: Whisper → Emerging → Mainstream → Peak → Declining → Dead
- [ ] Backtest divergence signals against 2024-2025 data

### Phase 4: AI Analysis Layer (Days 7-9)
- [ ] Claude API integration for daily narrative briefing
- [ ] Feed: top 50 social mentions + on-chain changes + price data per narrative
- [ ] Output: natural language market briefing with actionable signals
- [ ] "What's new today vs yesterday?" change detection
- [ ] Catalyst identification: "Coinbase launched X, driving AI narrative"

### Phase 5: Frontend Dashboard (Days 9-13)
- [ ] Narrative heatmap (rows=narratives, cols=time, color=momentum)
- [ ] Divergence alert feed (real-time)
- [ ] Narrative lifecycle tracker (visual cycle position)
- [ ] Top tokens per narrative (ranked by undervaluation signal)
- [ ] Daily AI briefing panel
- [ ] Historical narrative rotation chart (show how capital rotated through 2024-2025)

### Phase 6: Telegram Bot + Alerts (Days 13-15)
- [ ] grammY Telegram bot
- [ ] Push alerts on: divergence signals, lifecycle transitions, whale moves
- [ ] Daily morning briefing message
- [ ] Commands: /narrative AI, /divergence, /briefing, /top

### Phase 7: Backtest + Polish (Days 15-18)
- [ ] Historical backtest: "if you followed divergence signals in 2024-2025..."
- [ ] Performance metrics: win rate, avg return, time-to-peak
- [ ] README with architecture diagram, screenshots, methodology
- [ ] Deploy
- [ ] Demo video/GIF

---

## Monetisation Potential

This isn't just a portfolio piece — it's a product:

| Model | Price | TAM |
|-------|-------|-----|
| **Free tier** | Dashboard with delayed data (1hr) | Lead gen |
| **Pro** | Real-time + Telegram alerts + daily AI briefing | $29/mo |
| **Whale** | API access + custom narrative tracking + whale alerts | $99/mo |
| **Data API** | Sell narrative sentiment data to funds/traders | Enterprise |

Crypto traders will pay for edge. A tool that says "AI narrative is heating up but price hasn't moved" is worth a lot more than $29/mo to someone trading with real money.

---

## Why This Is a Monster Portfolio Piece

1. **Full-stack data engineering** — social APIs, on-chain APIs, market data, all normalised into one system
2. **NLP + AI** — real sentiment analysis, not toy examples
3. **Real-time systems** — streaming data, live dashboard, push alerts
4. **Backtesting** — proves the thesis with historical data
5. **Domain expertise** — demonstrates deep understanding of crypto markets
6. **Actually useful** — not a demo, a real tool you use to make money
7. **Extends QuantFlow** — shows you can build a platform, not just projects

Combined portfolio story:
- QuantFlow: "I built the order book analysis engine"
- NarrativeFlow: "I built the market intelligence layer on top"
- "Together they give me real-time market microstructure + narrative rotation signals. I use them to trade."

That's not a junior developer. That's someone building institutional-grade tooling for fun.

---

## Relationship to QuantFlow

```
QuantFlow (order book intelligence)
    │
    ├── Market microstructure data
    ├── Pattern detection  
    ├── Real-time price/volume feeds
    │
    └──── feeds into ────┐
                         │
                    NarrativeFlow (narrative intelligence)
                         │
                         ├── Social sentiment data
                         ├── On-chain activity data
                         ├── Narrative classification
                         ├── Divergence detection
                         │
                         └── Combined signal:
                              "AI narrative heating up"
                              + "Order book shows accumulation"
                              + "Price hasn't moved"
                              = HIGH CONVICTION ENTRY
```

The two tools together create a signal that neither can produce alone. That's the real alpha.
