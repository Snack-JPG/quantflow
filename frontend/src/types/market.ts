/**
 * Market data types for QuantFlow frontend
 */

export interface PriceLevel {
  price: string;
  quantity: string;
}

export interface OrderBookData {
  exchange: string;
  symbol: string;
  timestamp: number;
  sequence: number;
  bids: string[][];  // [price, quantity][]
  asks: string[][];  // [price, quantity][]
  mid_price?: string;
  spread?: string;
  spread_bps?: string;
}

export interface Trade {
  exchange: string;
  symbol: string;
  timestamp: number;
  price: string;
  quantity: string;
  side: 'buy' | 'sell';
  trade_id: string;
  value: string;
}

export interface MarketStats {
  symbol: string;
  mid_price?: string;
  spread?: string;
  spread_bps?: string;
  imbalance: number;
  bid_depth_10bps: string;
  ask_depth_10bps: string;
}

export interface AnalyticsData {
  symbol?: string;
  // VWAP
  vwap_1m?: number | null;
  vwap_5m?: number | null;
  vwap_15m?: number | null;

  // Order Book Imbalance
  obi?: number;
  weighted_obi?: number;
  obi_signal?: string;

  // Order Flow Imbalance
  ofi?: number;
  cumulative_ofi?: number;
  ofi_signal?: string;

  // Kyle's Lambda
  kyles_lambda?: number;
  price_impact?: number;
  lambda_liquidity?: string;

  // VPIN
  vpin?: number;
  vpin_toxicity?: string;

  // Liquidity Metrics
  amihud?: number;
  amihud_liquidity?: string;
  roll_spread?: number;
  roll_regime?: string;

  // Volatility
  realized_vol?: Record<number, number>;
  vol_term_structure?: string;
  garman_klass_vol?: number;
  parkinson_vol?: number;

  // Hurst
  hurst_exponent?: number;
  hurst_regime?: string;
  hurst_strategy?: string;
}

export type WebSocketMessage =
  | { type: 'connected'; client_id: string; message: string }
  | { type: 'subscribed'; symbol: string }
  | { type: 'unsubscribed'; symbol: string }
  | { type: 'orderbook'; data: OrderBookData }
  | { type: 'trade'; data: Trade }
  | { type: 'stats'; data: MarketStats }
  | { type: 'analytics'; data: AnalyticsData }
  | { type: 'pong' };
