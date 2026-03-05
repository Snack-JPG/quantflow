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

export type WebSocketMessage =
  | { type: 'connected'; client_id: string; message: string }
  | { type: 'subscribed'; symbol: string }
  | { type: 'unsubscribed'; symbol: string }
  | { type: 'orderbook'; data: OrderBookData }
  | { type: 'trade'; data: Trade }
  | { type: 'stats'; data: MarketStats }
  | { type: 'pong' };