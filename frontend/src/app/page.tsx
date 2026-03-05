/**
 * QuantFlow - Main Trading View Page
 */

'use client';

import React, { useState, useCallback } from 'react';
import { useWebSocket } from '@/lib/useWebSocket';
import { OrderBook } from '@/components/OrderBook';
import { DepthChart } from '@/components/DepthChart';
import { OrderBookData, Trade, MarketStats } from '@/types/market';

export default function HomePage() {
  const [selectedSymbol, setSelectedSymbol] = useState('BTCUSDT');
  const [orderBookData, setOrderBookData] = useState<OrderBookData | null>(null);
  const [recentTrades, setRecentTrades] = useState<Trade[]>([]);
  const [marketStats, setMarketStats] = useState<MarketStats | null>(null);

  // WebSocket handlers
  const handleOrderBook = useCallback((data: OrderBookData) => {
    setOrderBookData(data);
  }, []);

  const handleTrade = useCallback((trade: Trade) => {
    setRecentTrades((prev) => [trade, ...prev.slice(0, 49)]); // Keep last 50 trades
  }, []);

  const handleStats = useCallback((stats: MarketStats) => {
    setMarketStats(stats);
  }, []);

  // Connect to WebSocket
  const { isConnected } = useWebSocket({
    symbol: selectedSymbol,
    onOrderBook: handleOrderBook,
    onTrade: handleTrade,
    onStats: handleStats,
  });

  // Format numbers
  const formatPrice = (price?: string) => {
    if (!price) return '-';
    const num = parseFloat(price);
    if (num >= 1000) return num.toFixed(2);
    if (num >= 1) return num.toFixed(4);
    return num.toFixed(6);
  };

  const formatQuantity = (qty?: string) => {
    if (!qty) return '-';
    const num = parseFloat(qty);
    if (num >= 1000) return num.toFixed(2);
    if (num >= 1) return num.toFixed(4);
    return num.toFixed(6);
  };

  const formatTime = (timestamp: number) => {
    const date = new Date(timestamp / 1000); // Convert from microseconds
    return date.toLocaleTimeString();
  };

  return (
    <div className="min-h-screen bg-background p-4">
      {/* Header */}
      <header className="mb-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <h1 className="text-2xl font-bold">QuantFlow</h1>
            <div className="flex items-center gap-2">
              <div
                className={`w-2 h-2 rounded-full ${
                  isConnected ? 'bg-green-500' : 'bg-red-500'
                }`}
              />
              <span className="text-sm text-muted-foreground">
                {isConnected ? 'Connected' : 'Disconnected'}
              </span>
            </div>
          </div>

          {/* Symbol Selector */}
          <div className="flex items-center gap-4">
            <select
              value={selectedSymbol}
              onChange={(e) => setSelectedSymbol(e.target.value)}
              className="bg-card border border-border rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
            >
              <option value="BTCUSDT">BTC/USDT</option>
              <option value="ETHUSDT">ETH/USDT</option>
            </select>
          </div>
        </div>
      </header>

      {/* Market Stats Bar */}
      {marketStats && (
        <div className="mb-6 bg-card rounded-lg border border-border p-4">
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
            <div>
              <div className="text-xs text-muted-foreground mb-1">Mid Price</div>
              <div className="font-mono font-semibold">
                {formatPrice(marketStats.mid_price)}
              </div>
            </div>
            <div>
              <div className="text-xs text-muted-foreground mb-1">Spread</div>
              <div className="font-mono font-semibold">
                {marketStats.spread_bps
                  ? `${parseFloat(marketStats.spread_bps).toFixed(2)} bps`
                  : '-'}
              </div>
            </div>
            <div>
              <div className="text-xs text-muted-foreground mb-1">Imbalance</div>
              <div className="font-mono font-semibold">
                {marketStats.imbalance
                  ? `${(marketStats.imbalance * 100).toFixed(1)}%`
                  : '-'}
              </div>
            </div>
            <div>
              <div className="text-xs text-muted-foreground mb-1">Bid Depth (10bps)</div>
              <div className="font-mono font-semibold">
                {formatQuantity(marketStats.bid_depth_10bps)}
              </div>
            </div>
            <div>
              <div className="text-xs text-muted-foreground mb-1">Ask Depth (10bps)</div>
              <div className="font-mono font-semibold">
                {formatQuantity(marketStats.ask_depth_10bps)}
              </div>
            </div>
            <div>
              <div className="text-xs text-muted-foreground mb-1">Exchange</div>
              <div className="font-semibold">Binance</div>
            </div>
          </div>
        </div>
      )}

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Order Book */}
        <div className="lg:col-span-1">
          <OrderBook data={orderBookData} depth={20} />
        </div>

        {/* Center Column */}
        <div className="lg:col-span-1 space-y-6">
          {/* Depth Chart */}
          <DepthChart data={orderBookData} height={400} />

          {/* Recent Trades */}
          <div className="bg-card rounded-lg border border-border">
            <div className="p-4 border-b border-border">
              <h2 className="text-lg font-semibold">Recent Trades</h2>
            </div>
            <div className="max-h-96 overflow-y-auto">
              <div className="divide-y divide-border/50">
                {recentTrades.map((trade, i) => (
                  <div
                    key={`${trade.trade_id}-${i}`}
                    className="grid grid-cols-4 gap-2 px-4 py-2 text-xs font-mono hover:bg-secondary/20 transition-colors"
                  >
                    <div className={trade.side === 'buy' ? 'text-buy' : 'text-sell'}>
                      {formatPrice(trade.price)}
                    </div>
                    <div className="text-right">{formatQuantity(trade.quantity)}</div>
                    <div className="text-right text-muted-foreground">
                      ${parseFloat(trade.value).toFixed(2)}
                    </div>
                    <div className="text-right text-muted-foreground">
                      {formatTime(trade.timestamp)}
                    </div>
                  </div>
                ))}
                {recentTrades.length === 0 && (
                  <div className="text-center py-8 text-muted-foreground">
                    Waiting for trades...
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Right Column - Additional Stats */}
        <div className="lg:col-span-1 space-y-6">
          {/* Connection Info */}
          <div className="bg-card rounded-lg border border-border p-4">
            <h2 className="text-lg font-semibold mb-4">System Status</h2>
            <div className="space-y-3">
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">WebSocket</span>
                <span className={isConnected ? 'text-green-500' : 'text-red-500'}>
                  {isConnected ? 'Connected' : 'Disconnected'}
                </span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Symbol</span>
                <span>{selectedSymbol}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Exchange</span>
                <span>Binance</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Update Rate</span>
                <span>100ms</span>
              </div>
            </div>
          </div>

          {/* Info Panel */}
          <div className="bg-card rounded-lg border border-border p-4">
            <h2 className="text-lg font-semibold mb-4">About QuantFlow</h2>
            <div className="space-y-3 text-sm text-muted-foreground">
              <p>
                Production-grade order book intelligence platform with real-time market
                microstructure analysis.
              </p>
              <div className="space-y-2">
                <div className="flex items-start gap-2">
                  <span className="text-green-500">•</span>
                  <span>Live order book with 100ms updates</span>
                </div>
                <div className="flex items-start gap-2">
                  <span className="text-green-500">•</span>
                  <span>Market depth visualization</span>
                </div>
                <div className="flex items-start gap-2">
                  <span className="text-green-500">•</span>
                  <span>Real-time trade feed</span>
                </div>
                <div className="flex items-start gap-2">
                  <span className="text-green-500">•</span>
                  <span>Microstructure analytics</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}