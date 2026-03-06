# QuantFlow — Comprehensive Research Document

> A complete technical reference for building a real-time order book intelligence platform.
> Generated: 2026-03-05

---

## Table of Contents

1. [Market Microstructure Metrics — Exact Formulas + Python Pseudocode](#1-market-microstructure-metrics)
2. [Binance WebSocket API — Complete Technical Reference](#2-binance-websocket-api)
3. [Order Book Manipulation Patterns — Detection Algorithms](#3-order-book-manipulation-patterns)
4. [Existing Open-Source Projects — Landscape Analysis](#4-existing-open-source-projects)
5. [Academic Papers — Key References](#5-academic-papers)
6. [Implementation Notes](#6-implementation-notes)

---

## 1. Market Microstructure Metrics

### 1.1 Bid-Ask Spread

**Source:** Market microstructure fundamentals; formalized in Demsetz (1968), "The Cost of Transacting."

**Definition:** The bid-ask spread measures the cost of immediate execution — the premium a liquidity taker pays to transact immediately rather than waiting for a counterparty.

#### Absolute Spread

**Formula:**

```
S_abs = P_ask - P_bid
```

Where `P_ask` is the best (lowest) ask price and `P_bid` is the best (highest) bid price.

#### Relative Spread (in basis points)

**Formula:**

```
S_rel_bps = ((P_ask - P_bid) / M) × 10000

where M = (P_ask + P_bid) / 2    (midpoint price)
```

#### Effective Spread

The effective spread measures actual execution cost, accounting for trades that execute at or inside the quoted spread.

**Formula:**

```
S_eff = 2 × |P_trade - M|

where M = (P_ask + P_bid) / 2  at the time of the trade
```

The factor of 2 normalizes to a round-trip cost. Multiply by the trade direction sign (+1 for buy, -1 for sell) if you want the signed effective spread.

**Python Implementation:**

```python
from decimal import Decimal

def bid_ask_spread(best_bid: Decimal, best_ask: Decimal) -> dict:
    """Calculate all spread variants."""
    midpoint = (best_bid + best_ask) / 2
    absolute = best_ask - best_bid
    relative_bps = (absolute / midpoint) * Decimal('10000')
    return {
        'absolute': absolute,
        'midpoint': midpoint,
        'relative_bps': relative_bps,
    }

def effective_spread(trade_price: Decimal, best_bid: Decimal, best_ask: Decimal) -> Decimal:
    """Effective spread for a single trade."""
    midpoint = (best_bid + best_ask) / 2
    return 2 * abs(trade_price - midpoint)
```

**What it tells you:** Narrow spreads indicate high liquidity and competitive market-making. Widening spreads signal uncertainty, low liquidity, or anticipated volatility. In crypto, spreads widen dramatically during exchange outages, delistings, or flash crashes.

---

### 1.2 VWAP (Volume Weighted Average Price)

**Source:** Standard institutional execution benchmark. Formalized in Berkowitz, Logue & Noser (1988).

**Definition:** The average price of an asset weighted by volume over a time window. Used as a benchmark for execution quality — executing at or better than VWAP means you didn't move the market against yourself.

**Formula:**

```
VWAP = Σ(P_i × V_i) / Σ(V_i)

where:
  P_i = price of trade i
  V_i = volume (quantity) of trade i
  sum is over all trades in the window
```

**Python Implementation (Rolling Window):**

```python
from collections import deque
from decimal import Decimal
import time

class RollingVWAP:
    """Rolling VWAP over a fixed time window."""
    
    def __init__(self, window_seconds: int = 300):
        self.window_seconds = window_seconds
        self.trades = deque()  # (timestamp, price, quantity)
        self.sum_pv = Decimal('0')   # Σ(price × volume)
        self.sum_v = Decimal('0')    # Σ(volume)
    
    def add_trade(self, timestamp_ms: int, price: Decimal, quantity: Decimal):
        pv = price * quantity
        self.trades.append((timestamp_ms, pv, quantity))
        self.sum_pv += pv
        self.sum_v += quantity
        self._evict(timestamp_ms)
    
    def _evict(self, current_ts: int):
        cutoff = current_ts - (self.window_seconds * 1000)
        while self.trades and self.trades[0][0] < cutoff:
            _, old_pv, old_v = self.trades.popleft()
            self.sum_pv -= old_pv
            self.sum_v -= old_v
    
    def value(self) -> Decimal | None:
        if self.sum_v == 0:
            return None
        return self.sum_pv / self.sum_v
```

**What it tells you:** VWAP is the fair average price. If the current price is above VWAP, buyers have been more aggressive. If below, sellers dominate. Traders use it to assess whether their execution was good (bought below VWAP = good fill). In QuantFlow, comparing real-time price to rolling VWAP signals short-term directional pressure.

---

### 1.3 Order Book Imbalance (OBI)

**Source:** Widely used in market microstructure; formalized in Cao, Chen & Griffin (2005), "Informational Content of Option Volume Prior to Takeovers."

**Definition:** Measures the relative balance between bid-side and ask-side liquidity in the order book. A strong predictor of short-term price direction.

**Formula:**

```
OBI = (V_bid - V_ask) / (V_bid + V_ask)

where:
  V_bid = total volume on bid side (top N levels)
  V_ask = total volume on ask side (top N levels)
  
OBI ∈ [-1, 1]
  OBI → +1: heavy bid pressure (bullish)
  OBI → -1: heavy ask pressure (bearish)
  OBI ≈  0: balanced book
```

**Python Implementation:**

```python
from decimal import Decimal

def order_book_imbalance(
    bids: list[tuple[Decimal, Decimal]],  # [(price, qty), ...] sorted desc
    asks: list[tuple[Decimal, Decimal]],  # [(price, qty), ...] sorted asc
    levels: int = 10
) -> Decimal:
    """
    Calculate OBI over the top N levels.
    Returns value in [-1, 1].
    """
    bid_vol = sum(qty for _, qty in bids[:levels])
    ask_vol = sum(qty for _, qty in asks[:levels])
    
    total = bid_vol + ask_vol
    if total == 0:
        return Decimal('0')
    
    return (bid_vol - ask_vol) / total


def weighted_obi(
    bids: list[tuple[Decimal, Decimal]],
    asks: list[tuple[Decimal, Decimal]],
    levels: int = 10,
    decay: float = 0.85
) -> float:
    """
    Distance-weighted OBI: levels closer to the midpoint 
    get higher weight (exponential decay).
    """
    bid_weighted = sum(
        float(qty) * (decay ** i) for i, (_, qty) in enumerate(bids[:levels])
    )
    ask_weighted = sum(
        float(qty) * (decay ** i) for i, (_, qty) in enumerate(asks[:levels])
    )
    total = bid_weighted + ask_weighted
    if total == 0:
        return 0.0
    return (bid_weighted - ask_weighted) / total
```

**What it tells you:** OBI is the single most predictive short-term signal available from the order book. Academic research (Cont, Kukanov & Stoikov 2014) shows it's linearly correlated with subsequent price changes at short horizons. A sustained OBI > 0.3 typically precedes upward price movement. However, OBI is susceptible to manipulation (spoofing creates false imbalance).

---

### 1.4 Order Flow Imbalance (OFI)

**Source:** Cont, Kukanov & Stoikov (2014), "The Price Impact of Order Book Events," *Quantitative Finance*.

**Definition:** OFI captures the *change* in order book state between snapshots — not just the static imbalance, but the dynamics of how liquidity is being added and removed. It's a more robust predictor of price changes than static OBI because it captures aggressive order flow.

**Formula:**

At each snapshot t, define:

```
e_t^b = I(P_bid(t) ≥ P_bid(t-1)) × Q_bid(t) - I(P_bid(t) ≤ P_bid(t-1)) × Q_bid(t-1)
e_t^a = I(P_ask(t) ≤ P_ask(t-1)) × Q_ask(t) - I(P_ask(t) ≥ P_ask(t-1)) × Q_ask(t-1)

OFI_t = e_t^b - e_t^a
```

Where `I(condition)` is the indicator function, `P_bid(t)`, `Q_bid(t)` are best bid price and quantity at snapshot t, and similarly for ask.

**More intuitively, the full logic is:**

```
If bid price increases:       e_b = +Q_bid(t)        (new aggressive bid)
If bid price unchanged:       e_b = Q_bid(t) - Q_bid(t-1)  (quantity change at same level)
If bid price decreases:       e_b = -Q_bid(t-1)      (bid pulled / consumed)

If ask price decreases:       e_a = +Q_ask(t)        (new aggressive ask)
If ask price unchanged:       e_a = Q_ask(t) - Q_ask(t-1)  (quantity change at same level)
If ask price increases:       e_a = -Q_ask(t-1)      (ask pulled / consumed)

OFI = e_b - e_a
```

**Python Implementation:**

```python
from decimal import Decimal
from dataclasses import dataclass

@dataclass
class BookTop:
    bid_price: Decimal
    bid_qty: Decimal
    ask_price: Decimal
    ask_qty: Decimal

class OFICalculator:
    """Order Flow Imbalance per Cont, Kukanov & Stoikov (2014)."""
    
    def __init__(self):
        self.prev: BookTop | None = None
    
    def update(self, current: BookTop) -> Decimal | None:
        if self.prev is None:
            self.prev = current
            return None
        
        # Bid-side event
        if current.bid_price > self.prev.bid_price:
            e_b = current.bid_qty
        elif current.bid_price == self.prev.bid_price:
            e_b = current.bid_qty - self.prev.bid_qty
        else:
            e_b = -self.prev.bid_qty
        
        # Ask-side event
        if current.ask_price < self.prev.ask_price:
            e_a = current.ask_qty
        elif current.ask_price == self.prev.ask_price:
            e_a = current.ask_qty - self.prev.ask_qty
        else:
            e_a = -self.prev.ask_qty
        
        ofi = e_b - e_a
        self.prev = current
        return ofi


class CumulativeOFI:
    """Cumulative OFI over a rolling window of N snapshots."""
    
    def __init__(self, window: int = 50):
        self.ofi_calc = OFICalculator()
        self.window = window
        self.buffer = deque(maxlen=window)
    
    def update(self, book_top: BookTop) -> Decimal:
        ofi = self.ofi_calc.update(book_top)
        if ofi is not None:
            self.buffer.append(ofi)
        return sum(self.buffer)
```

**What it tells you:** OFI is the change-based version of imbalance. Positive OFI means bids are being added (or asks consumed) faster than the reverse. Cont et al. showed that the regression `ΔP = α + β × OFI + ε` has a remarkably high R² at short horizons (1-second). OFI predicts price direction better than OBI because it captures *flow* rather than *state*.

---

### 1.5 Kyle's Lambda (λ)

**Source:** Kyle (1985), "Continuous Auctions and Insider Trading," *Econometrica*, 53(6), 1315-1335.

**Definition:** Kyle's Lambda measures the permanent price impact of order flow — how much the price moves per unit of signed volume. It is the slope coefficient from regressing price changes on signed order flow. Higher λ means lower liquidity (each unit of volume moves the price more).

**Formula:**

```
ΔP_t = α + λ × S_t + ε_t

where:
  ΔP_t = P_t - P_{t-1}    (price change over interval)
  S_t = Σ(sign_i × V_i)   (signed order flow: sum of volume × trade direction)
  sign_i = +1 if buyer-initiated, -1 if seller-initiated
  λ = Cov(ΔP, S) / Var(S)  (OLS slope coefficient)
```

Trade direction classification (Lee-Ready algorithm):
```
If P_trade > M (midpoint):  buyer-initiated (+1)
If P_trade < M (midpoint):  seller-initiated (-1)
If P_trade = M:             use tick test (compare to previous trade price)
```

**Python Implementation:**

```python
import numpy as np
from decimal import Decimal

def classify_trade_direction(
    trade_price: float, 
    bid: float, 
    ask: float, 
    prev_price: float | None = None
) -> int:
    """Lee-Ready trade classification algorithm."""
    mid = (bid + ask) / 2
    if trade_price > mid:
        return 1   # buyer-initiated
    elif trade_price < mid:
        return -1  # seller-initiated
    else:
        # Tick test fallback
        if prev_price is not None:
            if trade_price > prev_price:
                return 1
            elif trade_price < prev_price:
                return -1
        return 0  # indeterminate


def kyles_lambda(
    price_changes: np.ndarray,     # ΔP for each interval
    signed_volumes: np.ndarray     # Signed order flow for each interval
) -> dict:
    """
    Estimate Kyle's Lambda via OLS regression.
    ΔP = α + λ × SignedVolume + ε
    """
    n = len(price_changes)
    assert n == len(signed_volumes) and n > 2
    
    # OLS: ΔP = α + λ × S
    X = np.column_stack([np.ones(n), signed_volumes])
    beta = np.linalg.lstsq(X, price_changes, rcond=None)[0]
    
    alpha = beta[0]
    lambda_coeff = beta[1]
    
    # R-squared
    y_hat = X @ beta
    ss_res = np.sum((price_changes - y_hat) ** 2)
    ss_tot = np.sum((price_changes - np.mean(price_changes)) ** 2)
    r_squared = 1 - ss_res / ss_tot if ss_tot > 0 else 0
    
    return {
        'alpha': alpha,
        'lambda': lambda_coeff,
        'r_squared': r_squared,
        'n_observations': n,
    }
```

**What it tells you:** Kyle's Lambda is the gold standard measure of market depth / price impact. Low λ = deep market, large orders can execute without moving the price much. High λ = shallow/illiquid market. In crypto, λ varies wildly between exchanges and time of day. Tracking λ over time reveals liquidity regime changes. A sudden increase in λ often precedes volatility events.

---

### 1.6 VPIN (Volume-Synchronized Probability of Informed Trading)

**Source:** Easley, López de Prado & O'Hara (2012), "Flow Toxicity and Liquidity in a High-Frequency World," *Review of Financial Studies*, 25(5), 1457-1493.

**Definition:** VPIN estimates the probability that informed traders are active in the market. Unlike time-based metrics, VPIN is synchronized on volume — it uses fixed-volume buckets rather than fixed-time intervals, which better captures information arrival in fast markets.

**Algorithm:**

1. **Bulk Volume Classification (BVC):** Instead of Lee-Ready (which requires quote data for every trade), BVC classifies trade volume probabilistically using the price change within a bar:

```
V_buy = V × Φ((P_close - P_open) / σ_ΔP)
V_sell = V - V_buy

where:
  V = total volume in the bar
  Φ = standard normal CDF
  σ_ΔP = standard deviation of price changes
```

2. **Volume Bucketing:** Aggregate trades into fixed-volume buckets of size V_bucket. Each bucket contains exactly V_bucket units of volume.

3. **VPIN Calculation:** Over a rolling window of n buckets:

```
VPIN = (1/n) × Σ |V_buy_i - V_sell_i| / V_bucket

VPIN ∈ [0, 1]
  VPIN → 0: uninformed flow dominates (balanced buy/sell)
  VPIN → 1: informed flow dominates (one-sided pressure)
```

**Python Implementation:**

```python
import numpy as np
from scipy.stats import norm
from collections import deque

class VPINCalculator:
    """
    VPIN per Easley, López de Prado & O'Hara (2012).
    """
    
    def __init__(self, bucket_size: float, n_buckets: int = 50):
        self.bucket_size = bucket_size
        self.n_buckets = n_buckets
        self.buckets = deque(maxlen=n_buckets)  # (v_buy, v_sell) per bucket
        
        # Current partial bucket
        self.current_buy = 0.0
        self.current_sell = 0.0
        self.current_volume = 0.0
        
        # For sigma estimation
        self.price_changes = deque(maxlen=200)
        self.last_price = None
    
    def _sigma(self) -> float:
        if len(self.price_changes) < 10:
            return 1e-8  # avoid division by zero
        return float(np.std(self.price_changes)) or 1e-8
    
    def add_bar(self, open_price: float, close_price: float, volume: float):
        """Process a time bar (e.g., 1-second bar)."""
        # Track price changes for sigma
        dp = close_price - open_price
        self.price_changes.append(dp)
        
        # Bulk Volume Classification
        sigma = self._sigma()
        z = dp / sigma
        buy_fraction = norm.cdf(z)
        
        v_buy = volume * buy_fraction
        v_sell = volume * (1 - buy_fraction)
        
        # Fill buckets
        self.current_buy += v_buy
        self.current_sell += v_sell
        self.current_volume += volume
        
        while self.current_volume >= self.bucket_size:
            # Scale to bucket size
            scale = self.bucket_size / self.current_volume
            bucket_buy = self.current_buy * scale
            bucket_sell = self.current_sell * scale
            
            self.buckets.append((bucket_buy, bucket_sell))
            
            # Remainder carries over
            self.current_buy -= bucket_buy
            self.current_sell -= bucket_sell
            self.current_volume -= self.bucket_size
    
    def value(self) -> float | None:
        """Current VPIN estimate."""
        if len(self.buckets) < self.n_buckets:
            return None
        
        total_imbalance = sum(
            abs(v_buy - v_sell) for v_buy, v_sell in self.buckets
        )
        return total_imbalance / (self.n_buckets * self.bucket_size)
```

**What it tells you:** VPIN is an early-warning system for toxicity. When VPIN rises sharply, informed traders are active and market makers are likely to widen spreads or withdraw liquidity. Easley et al. showed VPIN spiked before the 2010 Flash Crash. In crypto, VPIN spikes often precede large moves (insider knowledge of exchange listings, hack disclosures, regulatory actions).

**Calibration notes:** The bucket size V_bucket should be approximately the average daily volume divided by 50. The window n_buckets is typically 50. These parameters need tuning per asset.

---

### 1.7 Amihud Illiquidity Ratio

**Source:** Amihud (2002), "Illiquidity and Stock Returns: Cross-Section and Time-Series Effects," *Journal of Financial Markets*, 5(1), 31-56.

**Definition:** The Amihud ratio measures price impact per unit of dollar volume. It's the daily ratio of absolute return to dollar volume, averaged over a period. Simple to compute, widely used in academic literature as a liquidity proxy.

**Formula:**

```
ILLIQ_t = |r_t| / DollarVolume_t

where:
  r_t = ln(P_t / P_{t-1})   or  (P_t - P_{t-1}) / P_{t-1}
  DollarVolume_t = P_t × V_t

Average over T days:
  ILLIQ = (1/T) × Σ(|r_t| / DollarVolume_t)
```

**Python Implementation:**

```python
from decimal import Decimal
from collections import deque

class AmihudIlliquidity:
    """
    Rolling Amihud illiquidity ratio.
    Higher values = less liquid (price moves more per dollar of volume).
    """
    
    def __init__(self, window: int = 20):
        self.window = window
        self.ratios = deque(maxlen=window)
        self.prev_price = None
    
    def update(self, price: float, volume: float) -> float | None:
        if self.prev_price is None or self.prev_price == 0:
            self.prev_price = price
            return None
        
        ret = abs((price - self.prev_price) / self.prev_price)
        dollar_volume = price * volume
        
        if dollar_volume > 0:
            ratio = ret / dollar_volume
            self.ratios.append(ratio)
        
        self.prev_price = price
        
        if len(self.ratios) < 2:
            return None
        
        return sum(self.ratios) / len(self.ratios)
```

**What it tells you:** Amihud is a coarse but effective liquidity measure. It's best for comparing liquidity across assets or tracking liquidity changes over time. In crypto, useful for comparing liquidity across trading pairs or detecting liquidity withdrawals (Amihud spikes = market makers pulling out).

---

### 1.8 Roll Spread Estimator

**Source:** Roll (1984), "A Simple Implicit Measure of the Effective Bid-Ask Spread in an Efficient Market," *Journal of Finance*, 39(4), 1127-1139.

**Definition:** Roll's model infers the effective spread from the autocovariance of consecutive price changes. The intuition: if a market bounces between bid and ask, consecutive returns will be negatively autocorrelated. The magnitude of this negative autocovariance reveals the spread.

**Formula:**

```
Cov(ΔP_t, ΔP_{t-1}) = -c² / 4

where c = effective spread

Therefore:
  Roll_Spread = 2 × √(-Cov(ΔP_t, ΔP_{t-1}))
  
If the autocovariance is positive (which happens in trending markets), 
the Roll estimator is undefined. Convention: set to 0 or NaN.
```

**Python Implementation:**

```python
import numpy as np
from collections import deque

class RollSpread:
    """
    Roll (1984) implied spread estimator.
    """
    
    def __init__(self, window: int = 100):
        self.window = window
        self.prices = deque(maxlen=window + 2)
    
    def update(self, price: float) -> float | None:
        self.prices.append(price)
        
        if len(self.prices) < 4:
            return None
        
        prices = np.array(self.prices)
        returns = np.diff(prices)  # ΔP series
        
        # Autocovariance of returns at lag 1
        n = len(returns)
        r1 = returns[1:]
        r0 = returns[:-1]
        cov = np.mean(r1 * r0) - np.mean(r1) * np.mean(r0)
        
        if cov >= 0:
            return 0.0  # undefined in trending regime
        
        return 2.0 * np.sqrt(-cov)
```

**What it tells you:** Roll spread is useful when you don't have direct quote data. In crypto (where we do have quote data), it serves as a cross-check: if the Roll spread diverges significantly from the quoted spread, something interesting is happening — possibly hidden liquidity, iceberg orders, or manipulation.

---

### 1.9 Realized Volatility

**Source:** Andersen & Bollerslev (1998), "Answering the Skeptics: Yes, Standard Volatility Models Do Provide Accurate Forecasts," *International Economic Review*.

**Definition:** Realized volatility (RV) is the sum of squared returns computed from high-frequency data. It's a model-free estimate of true volatility over a given window.

**Formula:**

```
RV = √(Σ r_i²)

where r_i = ln(P_i / P_{i-1})  for each trade or fixed-interval return

Annualized:
  RV_annual = RV_daily × √365  (crypto trades 365 days)
```

**Python Implementation:**

```python
import numpy as np
from collections import deque
import math

class RealizedVolatility:
    """
    Realized volatility from trade returns.
    Supports multiple window sizes simultaneously.
    """
    
    def __init__(self, windows: list[int] = [60, 300, 3600]):
        """windows: list of lookback periods in seconds."""
        self.windows = windows
        self.log_returns = deque()  # (timestamp_ms, log_return)
        self.last_price = None
    
    def add_trade(self, timestamp_ms: int, price: float):
        if self.last_price is not None and self.last_price > 0:
            lr = math.log(price / self.last_price)
            self.log_returns.append((timestamp_ms, lr))
        self.last_price = price
        
        # Evict oldest (keep max window + buffer)
        max_window_ms = max(self.windows) * 1000 + 60000
        cutoff = timestamp_ms - max_window_ms
        while self.log_returns and self.log_returns[0][0] < cutoff:
            self.log_returns.popleft()
    
    def compute(self, current_ts_ms: int) -> dict[int, float]:
        """Returns RV for each window size."""
        result = {}
        for w in self.windows:
            cutoff = current_ts_ms - (w * 1000)
            returns = [lr for ts, lr in self.log_returns if ts >= cutoff]
            if len(returns) < 2:
                result[w] = 0.0
            else:
                result[w] = math.sqrt(sum(r * r for r in returns))
        return result
```

**What it tells you:** RV at multiple time horizons reveals volatility term structure. If short-term RV >> long-term RV, the market is in a spike. If short-term RV << long-term RV, volatility is compressing (often precedes a breakout). Use for dynamic position sizing and risk management.

---

### 1.10 Garman-Klass Volatility

**Source:** Garman & Klass (1980), "On the Estimation of Security Price Volatilities from Historical Data," *Journal of Business*, 53(1), 67-78.

**Definition:** An OHLC-based volatility estimator that is 7.4x more efficient than the close-to-close estimator. Uses the full price range information within each bar.

**Formula:**

```
σ²_GK = 0.5 × [ln(H/L)]² - (2ln2 - 1) × [ln(C/O)]²

where:
  H = high price
  L = low price
  O = open price
  C = close price

For multiple periods:
  σ²_GK_avg = (1/N) × Σ σ²_GK_i
  σ_GK = √(σ²_GK_avg)
```

**Python Implementation:**

```python
import math
from collections import deque

class GarmanKlassVolatility:
    """Garman-Klass (1980) OHLC volatility estimator."""
    
    def __init__(self, window: int = 20):
        self.window = window
        self.estimates = deque(maxlen=window)
    
    def add_bar(self, open_: float, high: float, low: float, close: float):
        if low <= 0 or open_ <= 0:
            return
        
        log_hl = math.log(high / low)
        log_co = math.log(close / open_)
        
        sigma2 = 0.5 * log_hl ** 2 - (2 * math.log(2) - 1) * log_co ** 2
        self.estimates.append(sigma2)
    
    def value(self) -> float | None:
        if len(self.estimates) < 2:
            return None
        avg_var = sum(self.estimates) / len(self.estimates)
        if avg_var < 0:
            avg_var = 0  # Can happen with noisy data
        return math.sqrt(avg_var)
```

**What it tells you:** GK volatility uses more information than simple close-to-close and converges faster. Ideal for OHLC data from kline/candlestick streams. Compare with Parkinson and realized volatility for a more complete picture.

---

### 1.11 Parkinson Volatility

**Source:** Parkinson (1980), "The Extreme Value Method for Estimating the Variance of the Rate of Return," *Journal of Business*, 53(1), 61-65.

**Definition:** Uses only high-low range to estimate volatility. 5.2x more efficient than close-to-close. Particularly useful when you only have high/low data.

**Formula:**

```
σ²_P = (1 / (4 × N × ln2)) × Σ [ln(H_i / L_i)]²

σ_P = √(σ²_P)
```

**Python Implementation:**

```python
import math
from collections import deque

class ParkinsonVolatility:
    """Parkinson (1980) high-low range volatility estimator."""
    
    def __init__(self, window: int = 20):
        self.window = window
        self.log_ranges_sq = deque(maxlen=window)
    
    def add_bar(self, high: float, low: float):
        if low <= 0:
            return
        log_range = math.log(high / low)
        self.log_ranges_sq.append(log_range ** 2)
    
    def value(self) -> float | None:
        n = len(self.log_ranges_sq)
        if n < 2:
            return None
        
        sum_sq = sum(self.log_ranges_sq)
        variance = sum_sq / (4 * n * math.log(2))
        return math.sqrt(variance)
```

**What it tells you:** Parkinson volatility is a clean, efficient estimator that's resistant to close-price noise. Compare Parkinson to realized volatility: if Parkinson >> RV, there are intrabar extremes that aren't captured by trade-to-trade returns (possible wicks, liquidation cascades). If Parkinson << RV, microstructure noise dominates.

---

### 1.12 Hurst Exponent

**Source:** Mandelbrot (1971), "When Can Price Be Arbitraged Efficiently?"; formalized via R/S analysis by Hurst (1951) for Nile River flood analysis, applied to financial markets extensively.

**Definition:** The Hurst Exponent H measures the long-term memory of a time series:
- H = 0.5: random walk (no memory, efficient market)
- H > 0.5: trending / persistent (momentum)
- H < 0.5: mean-reverting (anti-persistent)

**Formula (R/S Analysis):**

```
For a time series of prices, compute log returns X_1, ..., X_n

For each sub-period of length n:
  1. Mean-adjusted series: Y_i = X_i - X̄
  2. Cumulative deviation: Z_i = Σ(j=1 to i) Y_j
  3. Range: R(n) = max(Z) - min(Z)
  4. Standard deviation: S(n) = std(X)
  5. Rescaled range: R(n) / S(n)

The Hurst exponent H satisfies:
  E[R(n)/S(n)] = C × n^H

Estimate H as the slope of log(R/S) vs log(n)
```

**Python Implementation:**

```python
import numpy as np

def hurst_exponent(prices: np.ndarray, min_window: int = 10) -> float:
    """
    Estimate Hurst exponent via R/S analysis.
    
    Returns:
        H ~ 0.5: random walk
        H > 0.5: trending (momentum strategy works)
        H < 0.5: mean-reverting (reversion strategy works)
    """
    log_returns = np.diff(np.log(prices))
    n = len(log_returns)
    
    if n < min_window * 4:
        return 0.5  # insufficient data
    
    # Generate window sizes (logarithmically spaced)
    max_window = n // 2
    window_sizes = []
    w = min_window
    while w <= max_window:
        window_sizes.append(w)
        w = int(w * 1.5)
    
    log_rs = []
    log_n = []
    
    for w in window_sizes:
        rs_values = []
        num_segments = n // w
        
        for i in range(num_segments):
            segment = log_returns[i * w : (i + 1) * w]
            mean = np.mean(segment)
            deviations = segment - mean
            cumulative = np.cumsum(deviations)
            
            R = np.max(cumulative) - np.min(cumulative)
            S = np.std(segment, ddof=1)
            
            if S > 0:
                rs_values.append(R / S)
        
        if rs_values:
            log_rs.append(np.log(np.mean(rs_values)))
            log_n.append(np.log(w))
    
    if len(log_rs) < 3:
        return 0.5
    
    # Linear regression: log(R/S) = H × log(n) + c
    coeffs = np.polyfit(log_n, log_rs, 1)
    H = coeffs[0]
    
    return float(np.clip(H, 0.0, 1.0))
```

**What it tells you:** The Hurst exponent tells you whether to use momentum or mean-reversion strategies. If H > 0.5, trends persist and you should trade breakouts. If H < 0.5, the price reverts and you should fade moves. Most liquid crypto pairs exhibit H slightly above 0.5 in trending markets and below 0.5 during consolidation. Tracking H over rolling windows reveals regime transitions.

---

## 2. Binance WebSocket API

### 2.1 Connection URLs

| Environment | Base URL | Notes |
|---|---|---|
| Spot | `wss://stream.binance.com:9443` | Primary |
| Spot (alt) | `wss://stream.binance.com:443` | Same, different port |
| Spot (data only) | `wss://data-stream.binance.vision` | Market data only, no user data |
| USD-M Futures | `wss://fstream.binance.com` | USDT/USDC-margined |
| COIN-M Futures | `wss://dstream.binance.com` | Coin-margined |

**Stream access patterns:**
- Raw single stream: `wss://stream.binance.com:9443/ws/<streamName>`
- Combined streams: `wss://stream.binance.com:9443/stream?streams=<stream1>/<stream2>/<stream3>`

Combined stream events are wrapped:
```json
{"stream": "<streamName>", "data": <rawPayload>}
```

**All symbols must be lowercase** in stream names (e.g., `btcusdt`, not `BTCUSDT`).

### 2.2 Order Book Depth Streams

#### Partial Book Depth Streams (Snapshot)

Stream names: `<symbol>@depth<levels>` or `<symbol>@depth<levels>@100ms`

Valid levels: **5, 10, or 20**

Update speed: 1000ms (default) or 100ms

These provide a full snapshot of the top N levels on each update.

```json
{
    "lastUpdateId": 160,
    "bids": [
        ["0.0024", "10"],
        ["0.0023", "15"]
    ],
    "asks": [
        ["0.0026", "100"],
        ["0.0027", "50"]
    ]
}
```

Each entry is `[price_string, quantity_string]`. A quantity of `"0"` means that price level should be removed.

#### Diff Depth Stream (Incremental Updates)

Stream name: `<symbol>@depth` or `<symbol>@depth@100ms`

Update speed: 1000ms (default) or 100ms

```json
{
    "e": "depthUpdate",
    "E": 1672515782136,
    "s": "BNBBTC",
    "U": 157,
    "u": 160,
    "b": [
        ["0.0024", "10"]
    ],
    "a": [
        ["0.0026", "100"]
    ]
}
```

Fields:
- `e` — Event type: `"depthUpdate"`
- `E` — Event time (ms)
- `s` — Symbol
- `U` — First update ID in this event
- `u` — Final update ID in this event
- `b` — Bids to update: `[[price, qty], ...]`
- `a` — Asks to update: `[[price, qty], ...]`

**Futures diff depth** adds:
- `T` — Transaction time
- `pu` — Previous final update ID (for sequencing verification)

#### Key Difference: `@depth` vs `@depth20`

| Feature | `@depth` (diff) | `@depth20` (snapshot) |
|---|---|---|
| Data type | Incremental deltas only | Full top-20 snapshot |
| Requires snapshot init? | **Yes** (must GET /api/v3/depth first) | **No** (self-contained) |
| Data volume | Lower (only changes) | Higher (full 20 levels each update) |
| Correctness guarantee | Must sequence correctly | Always correct on receipt |
| Best for | Full depth maintenance | Quick top-of-book monitoring |

### 2.3 Trade Streams

#### Individual Trade Stream

Stream name: `<symbol>@trade`

```json
{
    "e": "trade",
    "E": 1672515782136,
    "s": "BNBBTC",
    "t": 12345,
    "p": "0.001",
    "q": "100",
    "T": 1672515782136,
    "m": true,
    "M": true
}
```

- `t` — Trade ID (unique per trade)
- `p` — Price (string)
- `q` — Quantity (string)
- `T` — Trade time (ms)
- `m` — **Is the buyer the market maker?** If `true`, the trade was a sell (maker was on bid side, taker hit the bid). If `false`, the trade was a buy (taker lifted the ask).

**Important:** The `m` field is the inverse of what you might expect. `m: true` means buyer was maker = trade was seller-initiated. Use `not m` to determine if a trade is buyer-initiated.

#### Aggregate Trade Stream

Stream name: `<symbol>@aggTrade`

```json
{
    "e": "aggTrade",
    "E": 1672515782136,
    "s": "BNBBTC",
    "a": 12345,
    "p": "0.001",
    "q": "100",
    "f": 100,
    "l": 105,
    "T": 1672515782136,
    "m": true,
    "M": true
}
```

Aggregates multiple fills from a single taker order into one event. Fields `f` and `l` give the range of individual trade IDs aggregated. Use `@aggTrade` for most analytics — it's cleaner and lower volume than `@trade`.

### 2.4 Maintaining a Local Order Book

This is the critical procedure for keeping a synchronized local order book using diff depth updates:

**Step-by-step algorithm:**

1. Open WebSocket to `wss://stream.binance.com:9443/ws/btcusdt@depth@100ms`
2. **Buffer** all incoming events (don't process yet). Note the `U` (first update ID) of the first received event.
3. GET snapshot from REST API: `https://api.binance.com/api/v3/depth?symbol=BTCUSDT&limit=5000`
4. If snapshot's `lastUpdateId` < first buffered event's `U`, discard snapshot and get a new one.
5. Discard buffered events where `u` (final update ID) ≤ snapshot's `lastUpdateId`.
6. The first remaining buffered event should have `U ≤ lastUpdateId+1 ≤ u`. If not, restart from step 1.
7. Initialize local book with snapshot data.
8. Apply buffered events in sequence, then process new events as they arrive.

**Update rules:**
- For each `[price, quantity]` in bids/asks:
  - If `quantity == "0"`: **remove** that price level
  - If `quantity != "0"`: **set** that price level to the new quantity (insert or update)

**Sequencing verification (spot):**
- Each new event's `U` should equal previous event's `u + 1`
- If there's a gap, reconnect and rebuild

**Sequencing verification (futures):**
- Each new event's `pu` should equal the previous event's `u`
- If `pu != previous_u`, there's a gap — reconnect

```python
import asyncio
import aiohttp
from decimal import Decimal
from sortedcontainers import SortedDict

class LocalOrderBook:
    """Maintains a local order book from Binance diff depth stream."""
    
    def __init__(self, symbol: str):
        self.symbol = symbol
        self.bids = SortedDict()  # price -> qty (reverse sorted for bids)
        self.asks = SortedDict()  # price -> qty (sorted ascending)
        self.last_update_id = 0
        self.initialized = False
        self.buffer = []
    
    async def initialize(self, session: aiohttp.ClientSession):
        """Fetch REST snapshot and initialize book."""
        url = f"https://api.binance.com/api/v3/depth?symbol={self.symbol.upper()}&limit=5000"
        async with session.get(url) as resp:
            data = await resp.json()
        
        self.bids.clear()
        self.asks.clear()
        
        for price, qty in data['bids']:
            self.bids[Decimal(price)] = Decimal(qty)
        for price, qty in data['asks']:
            self.asks[Decimal(price)] = Decimal(qty)
        
        self.last_update_id = data['lastUpdateId']
        
        # Process buffered events
        for event in self.buffer:
            if event['u'] <= self.last_update_id:
                continue
            self._apply_update(event)
        
        self.buffer.clear()
        self.initialized = True
    
    def process_event(self, event: dict):
        """Process a depth update event."""
        if not self.initialized:
            self.buffer.append(event)
            return
        
        # Verify sequencing
        if event['u'] <= self.last_update_id:
            return  # stale event
        
        self._apply_update(event)
    
    def _apply_update(self, event: dict):
        for price_str, qty_str in event.get('b', []):
            price, qty = Decimal(price_str), Decimal(qty_str)
            if qty == 0:
                self.bids.pop(price, None)
            else:
                self.bids[price] = qty
        
        for price_str, qty_str in event.get('a', []):
            price, qty = Decimal(price_str), Decimal(qty_str)
            if qty == 0:
                self.asks.pop(price, None)
            else:
                self.asks[price] = qty
        
        self.last_update_id = event['u']
    
    @property
    def best_bid(self) -> tuple[Decimal, Decimal] | None:
        if self.bids:
            price = self.bids.keys()[-1]  # highest bid
            return (price, self.bids[price])
        return None
    
    @property
    def best_ask(self) -> tuple[Decimal, Decimal] | None:
        if self.asks:
            price = self.asks.keys()[0]  # lowest ask
            return (price, self.asks[price])
        return None
```

### 2.5 Rate Limits & Connection Limits

| Limit | Spot | Futures |
|---|---|---|
| Incoming messages/sec | 5 | 10 |
| Max streams per connection | 1024 | 1024 |
| Max connections per 5 min (per IP) | 300 | — |
| Connection lifetime | 24 hours | 24 hours |
| Ping interval (server sends) | Every 20 seconds | Every 3 minutes |
| Pong deadline | 1 minute | 10 minutes |

### 2.6 Reconnection Best Practices

```python
import asyncio
import websockets
import json

async def resilient_ws_connect(url: str, handler, max_retries: int = 100):
    """WebSocket connection with exponential backoff reconnection."""
    retry_count = 0
    base_delay = 0.5  # seconds
    max_delay = 30.0
    
    while retry_count < max_retries:
        try:
            async with websockets.connect(
                url,
                ping_interval=20,
                ping_timeout=30,
                close_timeout=5,
                max_size=10 * 1024 * 1024,  # 10MB
            ) as ws:
                retry_count = 0  # reset on successful connect
                async for message in ws:
                    data = json.loads(message)
                    await handler(data)
                    
        except (websockets.ConnectionClosed, 
                ConnectionRefusedError,
                asyncio.TimeoutError,
                OSError) as e:
            retry_count += 1
            delay = min(base_delay * (2 ** retry_count), max_delay)
            # Add jitter
            delay += random.uniform(0, delay * 0.1)
            await asyncio.sleep(delay)
        
        except Exception as e:
            # Unexpected error — log and continue
            retry_count += 1
            await asyncio.sleep(5)
```

**Key reconnection rules:**
1. Always use exponential backoff with jitter
2. After reconnecting the depth stream, re-fetch the REST snapshot and rebuild the book
3. Keep a heartbeat timer — if no message received in 60s, force reconnect
4. Before the 24-hour mark, proactively disconnect and reconnect
5. Log all reconnection events for debugging

### 2.7 Multi-Stream Subscription

Two approaches:

**URL-based (on connect):**
```
wss://stream.binance.com:9443/stream?streams=btcusdt@depth@100ms/btcusdt@aggTrade/ethusdt@depth@100ms/ethusdt@aggTrade
```

**Dynamic subscription (post-connect):**
```json
{
    "method": "SUBSCRIBE",
    "params": [
        "btcusdt@depth@100ms",
        "btcusdt@aggTrade",
        "ethusdt@depth@100ms",
        "ethusdt@aggTrade"
    ],
    "id": 1
}
```

Combined stream events are wrapped:
```json
{
    "stream": "btcusdt@aggTrade",
    "data": { /* raw event payload */ }
}
```

Use dynamic subscription for flexibility (can add/remove streams without reconnecting). Rate limit: 5 messages/sec inbound on spot, so batch subscription requests.

### 2.8 Coinbase WebSocket (Brief Comparison)

**URL:** `wss://ws-feed.exchange.coinbase.com`

**Subscribe:**
```json
{
    "type": "subscribe",
    "product_ids": ["BTC-USD"],
    "channels": ["level2", "matches"]
}
```

**Level 2 (order book) initial snapshot:**
```json
{
    "type": "snapshot",
    "product_id": "BTC-USD",
    "bids": [["10101.10", "0.45054140"]],
    "asks": [["10102.55", "0.57753524"]]
}
```

**Level 2 updates:**
```json
{
    "type": "l2update",
    "product_id": "BTC-USD",
    "time": "2024-08-14T20:42:27.265Z",
    "changes": [
        ["buy", "10101.80", "0.162567"]
    ]
}
```

**Key differences from Binance:**
- Coinbase sends the snapshot automatically on subscribe (no separate REST call needed)
- Updates use `["side", "price", "size"]` format vs Binance's `[price, size]`
- Requires authentication for some channels
- ISO timestamp strings vs Unix ms

### 2.9 Kraken WebSocket v2 (Brief Comparison)

**URL:** `wss://ws.kraken.com/v2`

**Subscribe:**
```json
{
    "method": "subscribe",
    "params": {
        "channel": "book",
        "symbol": ["BTC/USD"],
        "depth": 25
    }
}
```

**Book snapshot:**
```json
{
    "channel": "book",
    "type": "snapshot",
    "data": [{
        "symbol": "BTC/USD",
        "bids": [{"price": 45000.0, "qty": 1.5}],
        "asks": [{"price": 45001.0, "qty": 0.8}],
        "checksum": 1234567890
    }]
}
```

**Key differences:**
- Kraken v2 uses structured objects (`{price, qty}`) instead of arrays
- Built-in **checksum verification** — each update includes a CRC32 checksum of the book state to verify sync
- Supports L3 (individual order) data stream
- Uses ISO 4217 currency pair format (`XBT/USD` not `BTCUSD`)
- Depth options: 10, 25, 100, 500, 1000

---

## 3. Order Book Manipulation Patterns

### 3.1 Spoofing

**Definition:** Placing large orders with the intent to cancel before execution. The goal is to create a false impression of supply/demand, inducing other traders (and algorithms) to trade in the desired direction.

**Mechanics:**
1. Spoofer wants to buy cheaply
2. Places massive sell orders above the market → creates impression of heavy resistance
3. Other traders/algos see sell pressure, push price down
4. Spoofer buys at lower price
5. Cancels the large sell orders
6. Price recovers → spoofer profits

**Detection Algorithm:**

```python
from dataclasses import dataclass
from collections import defaultdict
from decimal import Decimal

@dataclass
class OrderEvent:
    timestamp_ms: int
    price: Decimal
    quantity: Decimal
    side: str  # 'bid' or 'ask'
    event_type: str  # 'place', 'cancel', 'fill'

class SpoofingDetector:
    """
    Detect spoofing: large orders placed and rapidly cancelled.
    
    Signals:
    - Large order relative to typical size at that level
    - Short lifespan (placed and cancelled within threshold)
    - Repeated pattern by same participant (if identifiable)
    - Price moved in favorable direction during order's lifespan
    """
    
    def __init__(
        self,
        cancel_window_ms: int = 5000,      # Max time before cancel for suspicion
        size_multiple: float = 5.0,          # Size vs average to flag
        min_pattern_count: int = 3,          # Minimum occurrences to flag
        lookback_minutes: int = 30
    ):
        self.cancel_window_ms = cancel_window_ms
        self.size_multiple = size_multiple
        self.min_pattern_count = min_pattern_count
        self.lookback_ms = lookback_minutes * 60 * 1000
        
        self.active_orders = {}          # price_level -> (timestamp, qty, side)
        self.avg_level_size = {}         # price_level -> running average size
        self.spoof_candidates = []       # potential spoofing events
    
    def on_order_placed(self, event: OrderEvent):
        key = (event.price, event.side)
        self.active_orders[key] = (event.timestamp_ms, event.quantity)
        
        # Update average size at this level
        if key not in self.avg_level_size:
            self.avg_level_size[key] = float(event.quantity)
        else:
            alpha = 0.05
            self.avg_level_size[key] = (
                alpha * float(event.quantity) + 
                (1 - alpha) * self.avg_level_size[key]
            )
    
    def on_order_cancelled(self, event: OrderEvent, price_moved_favorably: bool):
        key = (event.price, event.side)
        
        if key not in self.active_orders:
            return
        
        place_ts, place_qty = self.active_orders.pop(key)
        lifespan_ms = event.timestamp_ms - place_ts
        
        avg_size = self.avg_level_size.get(key, float(place_qty))
        size_ratio = float(place_qty) / avg_size if avg_size > 0 else 1.0
        
        # Spoofing criteria
        is_suspicious = (
            lifespan_ms < self.cancel_window_ms and
            size_ratio > self.size_multiple and
            price_moved_favorably
        )
        
        if is_suspicious:
            self.spoof_candidates.append({
                'timestamp': event.timestamp_ms,
                'price': event.price,
                'quantity': place_qty,
                'side': event.side,
                'lifespan_ms': lifespan_ms,
                'size_ratio': size_ratio,
            })
    
    def get_spoof_score(self) -> float:
        """0-1 score of current spoofing likelihood."""
        recent = [
            c for c in self.spoof_candidates
            if c['timestamp'] > (self.spoof_candidates[-1]['timestamp'] - self.lookback_ms)
        ] if self.spoof_candidates else []
        
        if len(recent) < self.min_pattern_count:
            return 0.0
        
        # Score based on frequency and size
        return min(1.0, len(recent) / (self.min_pattern_count * 3))
```

**Real-world cases:**
- **Navinder Singh Sarao (2015):** Used spoofing on E-mini S&P 500 futures, contributing to the 2010 Flash Crash. Placed ~$200M in fake sell orders. Convicted and sentenced to 1 year home detention.
- **Michael Coscia (2015):** First person convicted under Dodd-Frank anti-spoofing provisions. Used custom algorithms to spoof CME and ICE futures. Sentenced to 3 years.
- **JP Morgan (2020):** $920M settlement for spoofing in precious metals and Treasury futures over 8 years. Traders placed thousands of fake orders.

**False positive considerations:**
- Legitimate cancellations due to market moving away from order
- Iceberg/peg orders that automatically adjust
- Market makers rebalancing inventory (they legitimately cancel and replace frequently)
- Use cancel rate alone as insufficient — need the conjunction of size, speed, and favorable price movement

---

### 3.2 Layering

**Definition:** A sophisticated variant of spoofing where multiple orders are placed at different price levels on one side of the book, creating a "wall" of liquidity that is entirely fictitious. All orders are cancelled together once the price has moved.

**Mechanics:**
1. Layerer wants to sell high
2. Places multiple buy orders at 5-10 different price levels below market
3. This creates an illusion of strong support — other traders gain confidence, push price up
4. Layerer sells into the rising market
5. Cancels all layered buy orders simultaneously

**Detection Algorithm:**

```python
class LayeringDetector:
    """
    Detect layering: coordinated placement and cancellation of 
    multiple orders at different price levels.
    """
    
    def __init__(self, min_layers: int = 3, sync_window_ms: int = 500):
        self.min_layers = min_layers
        self.sync_window_ms = sync_window_ms
        self.order_groups = []  # groups of orders placed close together
        self.current_group = []
        self.last_event_ts = 0
    
    def on_order_placed(self, timestamp_ms: int, price: Decimal, 
                         qty: Decimal, side: str):
        # Group orders placed within sync window
        if timestamp_ms - self.last_event_ts > self.sync_window_ms:
            if len(self.current_group) >= self.min_layers:
                self.order_groups.append(list(self.current_group))
            self.current_group = []
        
        self.current_group.append({
            'ts': timestamp_ms, 'price': price,
            'qty': qty, 'side': side, 'cancelled': False
        })
        self.last_event_ts = timestamp_ms
    
    def on_orders_cancelled(self, timestamp_ms: int, 
                             cancelled_prices: set[Decimal], side: str):
        """Check if cancelled orders match a placed group."""
        for group in self.order_groups:
            group_prices = {o['price'] for o in group if o['side'] == side}
            overlap = group_prices & cancelled_prices
            
            if len(overlap) >= self.min_layers:
                # Check they're all on same side and at different prices
                prices = sorted(overlap)
                if len(prices) >= self.min_layers:
                    return {
                        'detected': True,
                        'side': side,
                        'num_layers': len(prices),
                        'price_range': (min(prices), max(prices)),
                        'timestamp': timestamp_ms,
                    }
        return {'detected': False}
```

**False positive considerations:**
- Algorithmic market makers using grid strategies (they legitimately place orders at multiple levels)
- Trailing stop ladders being hit simultaneously
- Look for the asymmetry: layered orders should be on the opposite side from the eventual trade

---

### 3.3 Iceberg Orders

**Definition:** Large orders that are split into smaller visible portions. When one portion fills, the next appears at the same price. Not manipulative per se (it's a legitimate execution strategy), but detecting them reveals hidden liquidity.

**Detection Algorithm:**

```python
class IcebergDetector:
    """
    Detect iceberg orders: repeated fills at the same price 
    with consistent replenishment.
    """
    
    def __init__(self, min_repeats: int = 3, price_tolerance: Decimal = Decimal('0')):
        self.min_repeats = min_repeats
        self.price_tolerance = price_tolerance
        self.fill_history = defaultdict(list)  # price -> [(ts, qty), ...]
    
    def on_trade(self, timestamp_ms: int, price: Decimal, quantity: Decimal):
        self.fill_history[price].append((timestamp_ms, quantity))
        
        # Check for iceberg pattern at this price
        fills = self.fill_history[price]
        
        # Only look at recent fills (last 60 seconds)
        recent = [(ts, qty) for ts, qty in fills if timestamp_ms - ts < 60000]
        
        if len(recent) < self.min_repeats:
            return None
        
        # Check for consistent size (within 20% tolerance)
        quantities = [float(qty) for _, qty in recent]
        avg_qty = sum(quantities) / len(quantities)
        
        consistent = all(
            abs(q - avg_qty) / avg_qty < 0.2 for q in quantities
        )
        
        if consistent and len(recent) >= self.min_repeats:
            return {
                'detected': True,
                'price': price,
                'visible_size': avg_qty,
                'estimated_total': avg_qty * len(recent),  # lower bound
                'num_refills': len(recent),
                'still_active': True,
            }
        return None
```

**What it reveals:** Iceberg detection is valuable because it reveals the true liquidity landscape. A "thin" order book at a price level might actually have massive hidden liquidity behind it. Detecting icebergs helps you avoid fighting a whale.

---

### 3.4 Momentum Ignition

**Definition:** A burst of aggressive orders designed to trigger other algorithms' stop-losses, breakout signals, or momentum strategies — creating a self-reinforcing cascade that the igniter then fades.

**Detection Algorithm:**

```python
class MomentumIgnitionDetector:
    """
    Detect momentum ignition: sudden burst of aggressive orders 
    followed by reversal.
    """
    
    def __init__(
        self,
        burst_window_ms: int = 2000,
        min_burst_trades: int = 10,
        reversal_window_ms: int = 30000,
        reversal_threshold: float = 0.8
    ):
        self.burst_window_ms = burst_window_ms
        self.min_burst_trades = min_burst_trades
        self.reversal_window_ms = reversal_window_ms
        self.reversal_threshold = reversal_threshold
        self.trades = deque()
        self.bursts = []
    
    def on_trade(self, timestamp_ms: int, price: float, 
                  qty: float, is_buy: bool):
        self.trades.append((timestamp_ms, price, qty, is_buy))
        
        # Detect burst: sudden one-sided volume
        cutoff = timestamp_ms - self.burst_window_ms
        recent = [(ts, p, q, b) for ts, p, q, b in self.trades if ts >= cutoff]
        
        if len(recent) < self.min_burst_trades:
            return None
        
        buy_vol = sum(q for _, _, q, b in recent if b)
        sell_vol = sum(q for _, _, q, b in recent if not b)
        total = buy_vol + sell_vol
        
        if total == 0:
            return None
        
        imbalance = abs(buy_vol - sell_vol) / total
        
        if imbalance > 0.85:  # >85% one-sided
            direction = 'buy' if buy_vol > sell_vol else 'sell'
            burst_start_price = recent[0][1]
            burst_end_price = recent[-1][1]
            
            self.bursts.append({
                'timestamp': timestamp_ms,
                'direction': direction,
                'start_price': burst_start_price,
                'end_price': burst_end_price,
                'volume': total,
                'imbalance': imbalance,
            })
            
            # Check for reversal of previous burst
            return self._check_reversal(timestamp_ms, price)
        
        return None
    
    def _check_reversal(self, current_ts: int, current_price: float):
        for burst in self.bursts:
            elapsed = current_ts - burst['timestamp']
            if elapsed > self.burst_window_ms and elapsed < self.reversal_window_ms:
                move = burst['end_price'] - burst['start_price']
                reversal = current_price - burst['end_price']
                
                if move != 0 and abs(reversal) / abs(move) > self.reversal_threshold:
                    if (move > 0 and reversal < 0) or (move < 0 and reversal > 0):
                        return {
                            'detected': True,
                            'type': 'momentum_ignition',
                            'original_direction': burst['direction'],
                            'burst_move': move,
                            'reversal': reversal,
                            'reversal_ratio': abs(reversal / move),
                        }
        return None
```

---

### 3.5 Wash Trading

**Definition:** Trading with yourself (or colluding parties) to artificially inflate volume, creating the appearance of market activity and liquidity.

**Detection Algorithm:**

```python
class WashTradingDetector:
    """
    Detect wash trading patterns:
    - Self-trades (same participant on both sides)
    - Synchronized trading between colluding accounts
    - Volume that doesn't result in net position change
    """
    
    def __init__(self, window_seconds: int = 300):
        self.window_seconds = window_seconds
        self.trades = deque()
    
    def on_trade(self, timestamp_ms: int, price: float, 
                  qty: float, is_buy: bool):
        self.trades.append((timestamp_ms, price, qty, is_buy))
        
        # Evict old trades
        cutoff = timestamp_ms - self.window_seconds * 1000
        while self.trades and self.trades[0][0] < cutoff:
            self.trades.popleft()
    
    def analyze(self) -> dict:
        """
        Heuristic indicators of wash trading.
        Without account-level data, we look for statistical anomalies.
        """
        if len(self.trades) < 20:
            return {'wash_score': 0.0}
        
        scores = []
        
        # 1. Buy-sell volume symmetry at exact same prices
        price_buys = defaultdict(float)
        price_sells = defaultdict(float)
        for ts, p, q, is_buy in self.trades:
            p_rounded = round(p, 2)
            if is_buy:
                price_buys[p_rounded] += q
            else:
                price_sells[p_rounded] += q
        
        # If buys and sells match closely at many price levels → suspicious
        matched_volume = 0
        total_volume = 0
        for price in set(price_buys) & set(price_sells):
            matched = min(price_buys[price], price_sells[price])
            matched_volume += matched
            total_volume += price_buys[price] + price_sells[price]
        
        if total_volume > 0:
            symmetry_score = matched_volume / total_volume
            scores.append(symmetry_score)
        
        # 2. Unusually regular inter-trade intervals
        timestamps = [t for t, _, _, _ in self.trades]
        if len(timestamps) > 10:
            intervals = np.diff(timestamps)
            cv = np.std(intervals) / np.mean(intervals) if np.mean(intervals) > 0 else 1
            # Low coefficient of variation = suspiciously regular
            regularity_score = max(0, 1 - cv)
            scores.append(regularity_score)
        
        # 3. Volume anomaly: high volume with no price impact
        prices = [p for _, p, _, _ in self.trades]
        volumes = [q for _, _, q, _ in self.trades]
        price_range = max(prices) - min(prices) if prices else 0
        total_vol = sum(volumes)
        
        if total_vol > 0 and max(prices) > 0:
            impact_ratio = price_range / (max(prices) * total_vol)
            # Very low impact per unit volume = suspicious
            no_impact_score = max(0, 1 - impact_ratio * 1e6)
            scores.append(no_impact_score)
        
        return {
            'wash_score': sum(scores) / len(scores) if scores else 0.0,
            'symmetry': scores[0] if len(scores) > 0 else 0,
            'regularity': scores[1] if len(scores) > 1 else 0,
            'no_impact': scores[2] if len(scores) > 2 else 0,
        }
```

**Real-world cases:**
- **Bitfinex/Tether (2019):** NY Attorney General investigation found wash trading used to manipulate BTC prices.
- **Numerous crypto exchanges:** Blockchain Transparency Institute estimated 80%+ of reported volume on many exchanges was wash traded (pre-2020).

---

### 3.6 Tape Painting

**Definition:** Executing small trades at progressively higher (or lower) prices to create the visual appearance of a trend. The trades are typically small and just above the last trade price, "painting the tape" in a desired direction.

**Detection Algorithm:**

```python
class TapePaintingDetector:
    """
    Detect tape painting: sequential small trades at 
    monotonically increasing/decreasing prices.
    """
    
    def __init__(self, min_streak: int = 8, max_trade_size_pct: float = 0.01):
        self.min_streak = min_streak
        self.max_trade_size_pct = max_trade_size_pct
        self.trades = deque(maxlen=200)
        self.avg_trade_size = None
    
    def on_trade(self, timestamp_ms: int, price: float, qty: float):
        self.trades.append((timestamp_ms, price, qty))
        
        # Update average trade size (exponential)
        if self.avg_trade_size is None:
            self.avg_trade_size = qty
        else:
            self.avg_trade_size = 0.01 * qty + 0.99 * self.avg_trade_size
    
    def detect(self) -> dict | None:
        if len(self.trades) < self.min_streak:
            return None
        
        recent = list(self.trades)[-self.min_streak * 2:]
        
        # Find monotonic sequences of small trades
        up_streak = 0
        down_streak = 0
        max_up = 0
        max_down = 0
        
        for i in range(1, len(recent)):
            ts, price, qty = recent[i]
            _, prev_price, _ = recent[i - 1]
            
            is_small = qty < self.avg_trade_size * self.max_trade_size_pct * 100
            
            if price > prev_price and is_small:
                up_streak += 1
                down_streak = 0
                max_up = max(max_up, up_streak)
            elif price < prev_price and is_small:
                down_streak += 1
                up_streak = 0
                max_down = max(max_down, down_streak)
            else:
                up_streak = 0
                down_streak = 0
        
        if max_up >= self.min_streak:
            return {'detected': True, 'direction': 'up', 'streak': max_up}
        if max_down >= self.min_streak:
            return {'detected': True, 'direction': 'down', 'streak': max_down}
        
        return None
```

---

### 3.7 Front-Running

**Definition:** Detecting a large incoming order and trading ahead of it to profit from the anticipated price impact.

**In crypto context:** Front-running often manifests as MEV (Maximal Extractable Value) in DeFi, or HFTs detecting large orders on one exchange and racing to other exchanges.

**Detection (from order book perspective):**

```python
class FrontRunningDetector:
    """
    Detect potential front-running: small trades appearing 
    just before large trades in the same direction.
    """
    
    def __init__(self, leader_window_ms: int = 100, 
                  size_ratio: float = 10.0):
        self.leader_window_ms = leader_window_ms
        self.size_ratio = size_ratio
        self.recent_trades = deque(maxlen=1000)
    
    def on_trade(self, timestamp_ms: int, price: float, 
                  qty: float, is_buy: bool):
        self.recent_trades.append((timestamp_ms, price, qty, is_buy))
        
        # Check if this is a "large" trade that was front-run
        if self.avg_size and qty > self.avg_size * self.size_ratio:
            # Look for small trades in same direction just before
            leaders = [
                (ts, p, q) for ts, p, q, b in self.recent_trades
                if b == is_buy 
                and timestamp_ms - ts < self.leader_window_ms
                and timestamp_ms - ts > 0
                and q < self.avg_size
            ]
            
            if leaders:
                return {
                    'detected': True,
                    'large_trade_size': qty,
                    'leader_count': len(leaders),
                    'leader_total_size': sum(q for _, _, q in leaders),
                    'lead_time_ms': timestamp_ms - leaders[0][0],
                }
        
        return None
```

---

### 3.8 Quote Stuffing

**Definition:** Flooding the order book with a massive number of orders and cancellations to slow down competing trading systems and create confusion.

**Detection Algorithm:**

```python
class QuoteStuffingDetector:
    """
    Detect quote stuffing: abnormally high message rate with 
    rapid cancellations and minimal fills.
    """
    
    def __init__(self, 
                  window_ms: int = 1000,
                  msg_threshold: int = 100,
                  cancel_ratio_threshold: float = 0.95):
        self.window_ms = window_ms
        self.msg_threshold = msg_threshold
        self.cancel_ratio_threshold = cancel_ratio_threshold
        self.events = deque()
    
    def on_event(self, timestamp_ms: int, event_type: str):
        """event_type: 'place', 'cancel', 'fill'"""
        self.events.append((timestamp_ms, event_type))
        
        # Evict old events
        cutoff = timestamp_ms - self.window_ms
        while self.events and self.events[0][0] < cutoff:
            self.events.popleft()
    
    def detect(self) -> dict:
        if not self.events:
            return {'detected': False}
        
        total = len(self.events)
        cancels = sum(1 for _, t in self.events if t == 'cancel')
        fills = sum(1 for _, t in self.events if t == 'fill')
        
        cancel_ratio = cancels / total if total > 0 else 0
        
        is_stuffing = (
            total > self.msg_threshold and
            cancel_ratio > self.cancel_ratio_threshold
        )
        
        return {
            'detected': is_stuffing,
            'message_rate': total,
            'cancel_ratio': cancel_ratio,
            'fill_ratio': fills / total if total > 0 else 0,
        }
```

**Real-world cases:** High-frequency traders like Citadel and Virtu have faced scrutiny for quote-to-trade ratios exceeding 99:1. In crypto, quote stuffing is less regulated but still prevalent on exchanges with low fees.

---

## 4. Existing Open-Source Projects

### 4.1 Hummingbot

- **URL:** https://github.com/hummingbot/hummingbot
- **Stars:** ~14,000+
- **Language:** Python
- **What it does well:** Full market-making and arbitrage bot framework with 50+ exchange connectors. Excellent connector abstraction layer. Active community and governance via HBOT token.
- **What it's missing:** Not focused on analytics or visualization. Order book intelligence is minimal — it's an execution engine, not a research tool. No manipulation detection.
- **What we learn:** Connector architecture is excellent. Their exchange adapter pattern (normalizing different APIs) is worth studying.

### 4.2 CCXT

- **URL:** https://github.com/ccxt/ccxt
- **Stars:** ~33,000+
- **Language:** JavaScript/TypeScript, Python, PHP, C#, Go
- **What it does well:** Unified API across 100+ exchanges. The definitive library for exchange connectivity. Handles REST and WebSocket. Excellent documentation.
- **What it's missing:** CCXT is a connectivity layer, not an analytics layer. No order book analysis, no manipulation detection, no microstructure metrics. WebSocket support (CCXT Pro) is paid.
- **What we learn:** API normalization patterns. Their symbol/market/currency normalization is essential to study.

### 4.3 Bookmap (Commercial, no OSS)

- **Note:** Bookmap is the gold standard for order book visualization (heatmap, liquidity maps, historical playback) but it's commercial, closed-source, and Java-based.
- **What we learn:** The visualization concepts — heatmap of limit order density over time, aggressor detection, and liquidity withdrawal visualization — should be replicated in QuantFlow's eventual frontend.

### 4.4 Backtrader

- **URL:** https://github.com/mementum/backtrader
- **Stars:** ~14,000+
- **Language:** Python
- **What it does well:** Event-driven backtesting with a clean, Pythonic API. Good broker emulation. Live trading support with Interactive Brokers.
- **What it's missing:** No order book simulation in backtesting (only OHLCV). No real-time order book analysis. Somewhat abandoned (infrequent updates).
- **What we learn:** Event-driven architecture and strategy abstraction patterns.

### 4.5 Zipline / Zipline-Reloaded

- **URL:** https://github.com/stefan-jansen/zipline-reloaded
- **Stars:** ~1,200+ (reloaded); original Zipline ~17,000+
- **Language:** Python
- **What it does well:** Pipeline API for factor analysis. Data bundle management. Calendar-aware backtesting.
- **What it's missing:** Not designed for crypto. No real-time capability. No order-book-level simulation.
- **What we learn:** The Pipeline abstraction for composable factor computation is elegant and could inspire QuantFlow's metric pipeline.

### 4.6 VectorBT

- **URL:** https://github.com/polakowo/vectorbt
- **Stars:** ~4,500+ (free); Pro version is commercial
- **Language:** Python (NumPy/pandas-based)
- **What it does well:** Extremely fast vectorized backtesting. Beautiful visualizations. Portfolio optimization.
- **What it's missing:** OHLCV-only backtesting. No tick-level or order-book-level simulation. Pro features are paid.
- **What we learn:** Vectorized computation patterns for performance. Their use of NumPy broadcasting for bulk strategy evaluation.

### 4.7 QSTrader

- **URL:** https://github.com/mhallsmoore/qstrader
- **Stars:** ~3,000+
- **Language:** Python
- **What it does well:** Institutional-quality backtesting with proper fee/slippage modeling. Clean architecture.
- **What it's missing:** Small community. No real-time capabilities. Traditional equities focused.
- **What we learn:** Fee and slippage modeling for realistic execution simulation.

### 4.8 NautilusTrader

- **URL:** https://github.com/nautechsystems/nautilus_trader
- **Stars:** ~2,500+
- **Language:** Python/Rust (Cython core)
- **What it does well:** High-performance event-driven architecture. Supports L2/L3 order book data. Live trading with multiple exchanges. The most architecturally sophisticated open-source trading framework.
- **What it's missing:** Complex to learn. Smaller community. No built-in manipulation detection.
- **What we learn:** Their order book data model and L2/L3 simulation is the closest to what QuantFlow needs. Study their architecture carefully.

### What Makes QuantFlow Different?

None of the above projects combine:
1. **Real-time order book analytics** (microstructure metrics computed live)
2. **Manipulation detection** (algorithmic spoofing/layering/wash detection)
3. **Multi-exchange normalization** (unified book across venues)
4. **Academic rigor** (exact implementations of Kyle's λ, VPIN, OFI — not approximations)
5. **Intelligence-first** — not an execution engine, not a backtester, but an *intelligence platform* for understanding what the order book is telling you

QuantFlow sits in a gap: traders use Bookmap for visualization, CCXT for connectivity, and custom scripts for analytics. QuantFlow unifies the analytics layer with real-time feeds and manipulation detection into a single, open-source platform.

---

## 5. Academic Papers — Key References

### Market Microstructure — Foundational

1. **Kyle (1985)** — "Continuous Auctions and Insider Trading." *Econometrica*, 53(6), 1315-1335.
   - Seminal model of strategic informed trading. Defines Kyle's Lambda (λ) as the price impact coefficient. Shows how insiders trade optimally to hide information over time.

2. **Glosten & Milgrom (1985)** — "Bid, Ask and Transaction Prices in a Specialist Market with Heterogeneously Informed Traders." *Journal of Financial Economics*, 14(1), 71-100.
   - Asymmetric information model where the bid-ask spread compensates market makers for adverse selection risk. Foundation for understanding why spreads exist.

3. **Easley & O'Hara (1992)** — "Time and the Process of Security Price Adjustment." *Journal of Finance*, 47(2), 577-605.
   - Establishes that time between trades carries information. Long intervals = low information; short intervals = high information. Motivates time-weighted vs. volume-weighted analysis.

4. **Easley, Kiefer, O'Hara & Paperman (1996)** — "Liquidity, Information, and Infrequently Traded Stocks." *Journal of Finance*, 51(4), 1405-1436.
   - Introduces the PIN (Probability of Informed Trading) model. Direct ancestor of VPIN.

### Order Flow & Microstructure Metrics

5. **Easley, López de Prado & O'Hara (2012)** — "Flow Toxicity and Liquidity in a High-Frequency World." *Review of Financial Studies*, 25(5), 1457-1493.
   - Introduces VPIN — volume-synchronized estimate of informed trading probability. Shows it predicted the Flash Crash. The modern workhorse for flow toxicity measurement.

6. **Cont, Kukanov & Stoikov (2014)** — "The Price Impact of Order Book Events." *Quantitative Finance*, 14(1), 135-153.
   - Defines Order Flow Imbalance (OFI) and shows its linear relationship to contemporaneous price changes. R² of ~65% at 10-second frequency. Essential reading.

7. **Cont (2001)** — "Empirical Properties of Asset Returns: Stylized Facts and Statistical Issues." *Quantitative Finance*, 1(2), 223-236.
   - Comprehensive catalog of statistical properties of financial returns (fat tails, volatility clustering, leverage effects). Required background knowledge.

### Liquidity Measurement

8. **Amihud (2002)** — "Illiquidity and Stock Returns: Cross-Section and Time-Series Effects." *Journal of Financial Markets*, 5(1), 31-56.
   - The Amihud illiquidity ratio: |return| / dollar volume. Simple, widely used, works cross-sectionally.

9. **Roll (1984)** — "A Simple Implicit Measure of the Effective Bid-Ask Spread in an Efficient Market." *Journal of Finance*, 39(4), 1127-1139.
   - Derives the implied spread from return autocovariance. Elegant but assumes market efficiency.

10. **Lee & Ready (1991)** — "Inferring Trade Direction from Intraday Data." *Journal of Finance*, 46(2), 733-746.
    - The standard algorithm for classifying trades as buyer- or seller-initiated. Essential for computing signed order flow.

### Volatility Estimation

11. **Garman & Klass (1980)** — "On the Estimation of Security Price Volatilities from Historical Data." *Journal of Business*, 53(1), 67-78.
    - OHLC-based volatility estimator that's 7.4x more efficient than close-to-close.

12. **Parkinson (1980)** — "The Extreme Value Method for Estimating the Variance of the Rate of Return." *Journal of Business*, 53(1), 61-65.
    - High-low range volatility estimator. 5.2x efficiency gain.

13. **Andersen & Bollerslev (1998)** — "Answering the Skeptics: Yes, Standard Volatility Models Do Provide Accurate Forecasts." *International Economic Review*, 39(4), 885-905.
    - Establishes realized volatility from high-frequency data as the benchmark for volatility measurement.

### Market Manipulation

14. **Aitken, Harris & Ji (2009)** — "Trade-Based Manipulation and Market Efficiency: A Cross-Market Comparison." *22nd Australasian Finance and Banking Conference*.
    - Empirical analysis of trade-based manipulation detection across markets.

15. **Cao, Chen & Griffin (2005)** — "Informational Content of Option Volume Prior to Takeovers." *Journal of Business*, 78(3), 1073-1109.
    - Order book imbalance as predictor of informed trading activity.

### Long Memory & Persistence

16. **Mandelbrot (1971)** — "When Can Price Be Arbitraged Efficiently? A Limit to the Validity of the Random Walk and Martingale Models." *Review of Economics and Statistics*, 53(3), 225-236.
    - Foundational work on long-range dependence in financial time series. Motivates Hurst exponent analysis.

17. **Lo (1991)** — "Long-Term Memory in Stock Market Prices." *Econometrica*, 59(5), 1279-1313.
    - Critical analysis of R/S methodology with modified R/S test to account for short-range dependence.

### High-Frequency & Modern

18. **Bouchaud, Farmer & Lillo (2009)** — "How Markets Slowly Digest Changes in Supply and Demand." *Handbook of Financial Markets: Dynamics and Evolution*, 57-160.
    - Comprehensive review of price impact, order flow, and market microstructure at the tick level.

19. **Cartea, Jaimungal & Penalva (2015)** — *Algorithmic and High-Frequency Trading*. Cambridge University Press.
    - The textbook for HFT microstructure. Covers optimal market-making, execution, and the mathematics of order flow.

---

## 6. Implementation Notes

### 6.1 High-Throughput Python Async

**Use uvloop for 2-4x event loop performance:**
```python
import uvloop
import asyncio

# Set as default event loop policy
asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
```

**Message batching pattern:**
```python
class MessageBatcher:
    """
    Batch incoming WebSocket messages and process in bulk
    to reduce per-message overhead.
    """
    
    def __init__(self, batch_size: int = 50, flush_interval_ms: int = 10):
        self.batch_size = batch_size
        self.flush_interval_ms = flush_interval_ms
        self.buffer = []
        self.processor = None  # async callable
    
    async def add(self, message: dict):
        self.buffer.append(message)
        if len(self.buffer) >= self.batch_size:
            await self.flush()
    
    async def flush(self):
        if not self.buffer:
            return
        batch = self.buffer
        self.buffer = []
        await self.processor(batch)
    
    async def run_flush_timer(self):
        """Background task to flush on timer."""
        while True:
            await asyncio.sleep(self.flush_interval_ms / 1000)
            await self.flush()
```

**Key async patterns:**
- Use `asyncio.TaskGroup` (Python 3.11+) for managing concurrent WebSocket connections
- Use `asyncio.Queue` for producer-consumer between WebSocket readers and processors
- Never block the event loop — offload CPU-heavy computations (Hurst, Kyle's λ regression) to a `ProcessPoolExecutor`
- Use `orjson` instead of `json` for 3-5x faster JSON parsing

```python
import orjson

# 3-5x faster than json.loads
data = orjson.loads(raw_message)
```

### 6.2 Order Book Data Structures

**Option 1: SortedDict (recommended for Python)**

```python
from sortedcontainers import SortedDict

class OrderBook:
    def __init__(self):
        self.bids = SortedDict()   # price -> qty, naturally sorted ascending
        self.asks = SortedDict()   # price -> qty, naturally sorted ascending
    
    @property
    def best_bid(self):
        return self.bids.peekitem(-1) if self.bids else None  # highest bid = last item
    
    @property
    def best_ask(self):
        return self.asks.peekitem(0) if self.asks else None   # lowest ask = first item
    
    def update_bid(self, price, qty):
        if qty == 0:
            self.bids.pop(price, None)
        else:
            self.bids[price] = qty
    
    def update_ask(self, price, qty):
        if qty == 0:
            self.asks.pop(price, None)
        else:
            self.asks[price] = qty
```

Performance characteristics of SortedDict (backed by sorted list of lists):
- Insert/delete: O(log n)
- Lookup: O(log n)
- Iteration: O(n) — contiguous memory, cache-friendly
- Best bid/ask: O(1) via `peekitem()`

**Option 2: Price-level HashMap (fastest updates, unordered)**

```python
class FastOrderBook:
    """
    HashMap for O(1) updates, track best bid/ask separately.
    Best when update frequency >> query frequency.
    """
    def __init__(self):
        self.bids = {}  # price -> qty
        self.asks = {}
        self._best_bid = None
        self._best_ask = None
    
    def update_bid(self, price, qty):
        if qty == 0:
            self.bids.pop(price, None)
            if price == self._best_bid:
                self._best_bid = max(self.bids) if self.bids else None
        else:
            self.bids[price] = qty
            if self._best_bid is None or price > self._best_bid:
                self._best_bid = price
```

**Option 3: For maximum performance — C extension or Rust via PyO3**

For production systems processing thousands of messages per second across many symbols, consider a compiled order book:
- `rust-orderbook` via PyO3 bindings
- Custom C extension with a skip list or red-black tree

### 6.3 Ring Buffer for Time-Series Lookback

```python
import numpy as np

class RingBuffer:
    """
    Fixed-size circular buffer backed by a NumPy array.
    O(1) append, O(1) read by index, contiguous memory for vectorized ops.
    """
    
    def __init__(self, capacity: int, dtype=np.float64):
        self.capacity = capacity
        self.data = np.zeros(capacity, dtype=dtype)
        self.timestamps = np.zeros(capacity, dtype=np.int64)
        self.head = 0     # next write position
        self.count = 0    # number of elements stored
    
    def append(self, timestamp_ms: int, value: float):
        self.data[self.head] = value
        self.timestamps[self.head] = timestamp_ms
        self.head = (self.head + 1) % self.capacity
        self.count = min(self.count + 1, self.capacity)
    
    def get_array(self) -> np.ndarray:
        """Return data in chronological order."""
        if self.count < self.capacity:
            return self.data[:self.count].copy()
        else:
            return np.concatenate([
                self.data[self.head:],
                self.data[:self.head]
            ])
    
    def get_last_n(self, n: int) -> np.ndarray:
        """Return the most recent n values."""
        n = min(n, self.count)
        if n == 0:
            return np.array([])
        
        start = (self.head - n) % self.capacity
        if start < self.head:
            return self.data[start:self.head].copy()
        else:
            return np.concatenate([
                self.data[start:],
                self.data[:self.head]
            ])
    
    def get_window(self, current_ts: int, window_ms: int) -> np.ndarray:
        """Return values within a time window."""
        arr = self.get_array()
        ts = (np.concatenate([
            self.timestamps[self.head:self.head + self.count] 
            if self.count < self.capacity 
            else np.concatenate([self.timestamps[self.head:], self.timestamps[:self.head]])
        ]) if self.count > 0 else np.array([]))
        
        # Simpler approach for the common case
        cutoff = current_ts - window_ms
        mask = ts >= cutoff
        return arr[mask]
```

**Why ring buffers matter:** QuantFlow needs rolling windows for every metric (VWAP, RV, OBI, OFI, etc.). A ring buffer with NumPy backing means:
- Fixed memory allocation (no GC pressure)
- Vectorized computation over the window (numpy operations on contiguous memory)
- O(1) append
- Time-based windowing with binary search on the timestamp array

### 6.4 WebSocket Reconnection Patterns

```python
import asyncio
import random
import logging

logger = logging.getLogger(__name__)

class ResilientWebSocket:
    """
    Production WebSocket manager with:
    - Exponential backoff with jitter
    - Health monitoring (missing message detection)
    - Graceful 24h rotation
    - Order book rebuild on reconnect
    """
    
    def __init__(self, url: str, on_message, on_reconnect):
        self.url = url
        self.on_message = on_message
        self.on_reconnect = on_reconnect  # async callback to rebuild state
        self.connected_at = None
        self.last_message_at = None
        self.message_count = 0
    
    async def run(self):
        retry = 0
        while True:
            try:
                async with websockets.connect(self.url) as ws:
                    self.connected_at = asyncio.get_event_loop().time()
                    self.last_message_at = self.connected_at
                    retry = 0
                    
                    logger.info(f"Connected to {self.url}")
                    await self.on_reconnect()
                    
                    # Start health check task
                    health_task = asyncio.create_task(self._health_check(ws))
                    
                    try:
                        async for msg in ws:
                            self.last_message_at = asyncio.get_event_loop().time()
                            self.message_count += 1
                            data = orjson.loads(msg)
                            await self.on_message(data)
                    finally:
                        health_task.cancel()
                        
            except Exception as e:
                retry += 1
                delay = min(0.5 * (2 ** retry), 30) + random.uniform(0, 1)
                logger.warning(f"WS disconnected ({e}), retry {retry} in {delay:.1f}s")
                await asyncio.sleep(delay)
    
    async def _health_check(self, ws):
        """Monitor connection health."""
        while True:
            await asyncio.sleep(30)
            now = asyncio.get_event_loop().time()
            
            # No message in 60s → something is wrong
            if now - self.last_message_at > 60:
                logger.warning("No messages in 60s, forcing reconnect")
                await ws.close()
                return
            
            # Approaching 24h limit → graceful rotation
            if now - self.connected_at > 23.5 * 3600:
                logger.info("Approaching 24h limit, rotating connection")
                await ws.close()
                return
```

### 6.5 Decimal Precision

**The golden rule: NEVER use float for financial calculations.**

```python
from decimal import Decimal, getcontext, ROUND_HALF_UP

# Set global precision
getcontext().prec = 28
getcontext().rounding = ROUND_HALF_UP

# All prices and quantities from the exchange come as strings — parse directly to Decimal
price = Decimal("0.00123456")  # ✅ Correct
price = Decimal(0.00123456)    # ❌ WRONG — float precision already lost

# For performance-critical paths where Decimal is too slow,
# use integer arithmetic with a fixed scale factor:
class FixedPoint:
    """Integer-based fixed-point arithmetic. Scale = 10^8 (satoshi precision)."""
    SCALE = 10 ** 8
    
    @classmethod
    def from_str(cls, s: str) -> int:
        d = Decimal(s)
        return int(d * cls.SCALE)
    
    @classmethod
    def to_float(cls, v: int) -> float:
        return v / cls.SCALE
    
    @classmethod
    def multiply(cls, a: int, b: int) -> int:
        """a × b, result in same scale."""
        return (a * b) // cls.SCALE

# Example:
btc_price = FixedPoint.from_str("67432.50")     # 6743250000000
btc_qty = FixedPoint.from_str("0.00150000")      # 150000
notional = FixedPoint.multiply(btc_price, btc_qty)  # 101148750 = $101.14875
```

**When to use what:**
- `Decimal`: order book state, position tracking, P&L — anywhere correctness matters
- `float64`/`numpy`: analytics computations (VWAP, volatility, Hurst) where speed matters and minor floating-point drift is acceptable
- `int` (fixed-point): ultra-high-frequency paths, matching engine internals

### 6.6 Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│                    QuantFlow                         │
│                                                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐           │
│  │ Binance  │  │ Coinbase │  │  Kraken  │  Connectors│
│  │   WS     │  │   WS     │  │   WS     │           │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘           │
│       │              │              │                 │
│       ▼              ▼              ▼                 │
│  ┌──────────────────────────────────────┐            │
│  │       Normalizer / Event Bus         │            │
│  │   (unified OrderBookEvent, Trade)    │            │
│  └───────────────┬──────────────────────┘            │
│                   │                                   │
│       ┌───────────┼───────────┐                      │
│       ▼           ▼           ▼                      │
│  ┌─────────┐ ┌─────────┐ ┌──────────┐               │
│  │  Order  │ │  Trade  │ │  Metric  │               │
│  │  Book   │ │  Store  │ │  Engine  │               │
│  │  Engine │ │ (Ring   │ │ (VWAP,   │               │
│  │ (local  │ │  Buf)   │ │  OBI,    │               │
│  │  books) │ │         │ │  VPIN,   │               │
│  └────┬────┘ └────┬────┘ │  OFI...) │               │
│       │           │      └─────┬────┘               │
│       │           │            │                     │
│       ▼           ▼            ▼                     │
│  ┌──────────────────────────────────────┐            │
│  │        Detection Engine              │            │
│  │  (Spoofing, Layering, Wash, etc.)    │            │
│  └───────────────┬──────────────────────┘            │
│                   │                                   │
│                   ▼                                   │
│  ┌──────────────────────────────────────┐            │
│  │          Output / API                │            │
│  │  (WebSocket server, REST, alerts)    │            │
│  └──────────────────────────────────────┘            │
└─────────────────────────────────────────────────────┘
```

### 6.7 Performance Targets

For a single-symbol feed (e.g., BTCUSDT):
- **Message ingestion:** >10,000 msg/sec
- **Order book update latency:** <100μs per update
- **Metric computation:** <1ms for all metrics combined
- **Detection engine:** <5ms per evaluation cycle
- **Memory per symbol:** <50MB (full book + 1-hour history)

For multi-symbol (100 pairs):
- **Total throughput:** >100,000 msg/sec
- **Total memory:** <5GB
- **CPU:** Should run on 4 cores comfortably

These targets are achievable with Python + uvloop + NumPy + SortedContainers. For higher performance, the order book engine and ring buffer can be reimplemented in Rust with PyO3 bindings.

---

*End of RESEARCH.md — QuantFlow Reference Document*
*Total coverage: 12 metrics with formulas + pseudocode, 3 exchange APIs, 8 manipulation patterns with detection algorithms, 8 OSS projects analyzed, 19 academic papers, and complete implementation guidance.*
