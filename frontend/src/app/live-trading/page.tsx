'use client';

import React, { useState, useEffect } from 'react';
import { OrderBookHeatmap } from '@/components/LiveTrading/OrderBookHeatmap';
import { MultiExchangeStrip } from '@/components/LiveTrading/MultiExchangeStrip';
import { TradeTape } from '@/components/LiveTrading/TradeTape';
import { OrderBook } from '@/components/OrderBook';
import { DepthChart } from '@/components/DepthChart';
import { MetricsPanel } from '@/components/MetricsPanel';
import AlertFeed from '@/components/AlertFeed';
import { motion } from 'framer-motion';

// Mock data generator for demonstration
const generateMockOrderBook = () => {
  const midPrice = 45000 + Math.random() * 1000;
  const bids = Array.from({ length: 20 }, (_, i) => ({
    price: midPrice - (i + 1) * 10,
    quantity: Math.random() * 5,
    total: 0
  }));
  const asks = Array.from({ length: 20 }, (_, i) => ({
    price: midPrice + (i + 1) * 10,
    quantity: Math.random() * 5,
    total: 0
  }));

  // Calculate cumulative totals
  let bidTotal = 0;
  let askTotal = 0;
  bids.forEach(bid => {
    bidTotal += bid.quantity;
    bid.total = bidTotal;
  });
  asks.forEach(ask => {
    askTotal += ask.quantity;
    ask.total = askTotal;
  });

  return { bids, asks, midPrice };
};

const generateMockTrades = (count: number = 50) => {
  return Array.from({ length: count }, (_, i) => ({
    id: `trade-${Date.now()}-${i}`,
    price: 45000 + Math.random() * 1000,
    quantity: Math.random() * 2,
    timestamp: Date.now() - i * 1000,
    side: Math.random() > 0.5 ? 'buy' as const : 'sell' as const,
    isLarge: Math.random() > 0.9,
    isAggressive: Math.random() > 0.8
  }));
};

const generateMockExchangeData = () => {
  const basePrice = 45000 + Math.random() * 100;
  return [
    {
      exchange: 'Binance',
      price: basePrice + Math.random() * 50 - 25,
      volume24h: 1250000000,
      spread: 2.5 + Math.random() * 2,
      change24h: Math.random() * 10 - 5,
      lastUpdate: Date.now(),
      isLeading: true,
      hasArbitrage: false
    },
    {
      exchange: 'Coinbase',
      price: basePrice + Math.random() * 50 - 25,
      volume24h: 850000000,
      spread: 3.2 + Math.random() * 2,
      change24h: Math.random() * 10 - 5,
      lastUpdate: Date.now(),
      hasArbitrage: Math.random() > 0.7
    },
    {
      exchange: 'Kraken',
      price: basePrice + Math.random() * 50 - 25,
      volume24h: 450000000,
      spread: 4.1 + Math.random() * 2,
      change24h: Math.random() * 10 - 5,
      lastUpdate: Date.now(),
      hasArbitrage: false
    },
    {
      exchange: 'Bybit',
      price: basePrice + Math.random() * 50 - 25,
      volume24h: 750000000,
      spread: 2.8 + Math.random() * 2,
      change24h: Math.random() * 10 - 5,
      lastUpdate: Date.now(),
      hasArbitrage: Math.random() > 0.8
    },
    {
      exchange: 'OKX',
      price: basePrice + Math.random() * 50 - 25,
      volume24h: 650000000,
      spread: 3.5 + Math.random() * 2,
      change24h: Math.random() * 10 - 5,
      lastUpdate: Date.now(),
      hasArbitrage: false
    }
  ];
};

export default function LiveTradingPage() {
  const [selectedSymbol, setSelectedSymbol] = useState('BTC/USDT');
  const [orderBookData, setOrderBookData] = useState(() => generateMockOrderBook());
  const [trades, setTrades] = useState(() => generateMockTrades());
  const [exchangeData, setExchangeData] = useState(() => generateMockExchangeData());
  const [metrics, setMetrics] = useState({
    spread: 2.5,
    depth_imbalance: 0.15,
    vpin: 0.45,
    kyle_lambda: 0.0012,
    realized_volatility: 0.025,
    order_flow_imbalance: -0.08
  });

  const formattedSymbol = selectedSymbol.replace('/', '');
  const orderBookSnapshot = {
    exchange: 'simulated',
    symbol: formattedSymbol,
    timestamp: Date.now() * 1000,
    sequence: Date.now(),
    bids: orderBookData.bids.map((b) => [`${b.price}`, `${b.quantity}`]),
    asks: orderBookData.asks.map((a) => [`${a.price}`, `${a.quantity}`]),
  };

  // Simulate real-time updates
  useEffect(() => {
    const interval = setInterval(() => {
      setOrderBookData(generateMockOrderBook());
      setExchangeData(generateMockExchangeData());

      // Add new trade
      const newTrade = generateMockTrades(1)[0];
      setTrades(prev => [newTrade, ...prev.slice(0, 99)]);

      // Update metrics
      setMetrics({
        spread: 2.5 + Math.random() * 2,
        depth_imbalance: Math.random() * 0.4 - 0.2,
        vpin: Math.random() * 0.3 + 0.3,
        kyle_lambda: 0.001 + Math.random() * 0.001,
        realized_volatility: 0.02 + Math.random() * 0.02,
        order_flow_imbalance: Math.random() * 0.4 - 0.2
      });
    }, 1000);

    return () => clearInterval(interval);
  }, []);

  return (
    <div className="p-4 bg-zinc-950 min-h-screen">
      {/* Header Bar */}
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <select
            value={selectedSymbol}
            onChange={(e) => setSelectedSymbol(e.target.value)}
            className="bg-zinc-900 border border-zinc-800 rounded-lg px-4 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
          >
            <option value="BTC/USDT">BTC/USDT</option>
            <option value="ETH/USDT">ETH/USDT</option>
            <option value="SOL/USDT">SOL/USDT</option>
          </select>

          <div className="flex items-center gap-2 px-3 py-1.5 bg-zinc-900 rounded-lg">
            <span className="text-xs text-zinc-500">Mid Price:</span>
            <span className="text-sm font-mono text-white">
              ${orderBookData.midPrice.toFixed(2)}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <button className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 transition-colors">
            Connect Exchange
          </button>
        </div>
      </div>

      {/* Multi-Exchange Strip */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-4"
      >
        <MultiExchangeStrip data={exchangeData} symbol={selectedSymbol} />
      </motion.div>

      {/* Main Grid */}
      <div className="grid grid-cols-12 gap-4">
        {/* Left Column - Order Book */}
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.1 }}
          className="col-span-3"
        >
          <OrderBook
            data={orderBookSnapshot}
            depth={20}
          />
        </motion.div>

        {/* Center - Heatmap & Depth Chart */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="col-span-6 space-y-4"
        >
          <div className="bg-zinc-900 rounded-lg border border-zinc-800 p-4">
            <h3 className="text-sm font-semibold text-zinc-400 mb-3">Order Book Heatmap</h3>
            <OrderBookHeatmap
              bids={orderBookData.bids}
              asks={orderBookData.asks}
              trades={trades}
              height={400}
            />
          </div>

          <div className="bg-zinc-900 rounded-lg border border-zinc-800 p-4">
            <h3 className="text-sm font-semibold text-zinc-400 mb-3">Market Depth</h3>
            <DepthChart
              data={orderBookSnapshot}
              height={300}
            />
          </div>
        </motion.div>

        {/* Right Column - Trade Tape & Metrics */}
        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.3 }}
          className="col-span-3 space-y-4"
        >
          <TradeTape trades={trades} />
          <MetricsPanel metrics={metrics} />
        </motion.div>
      </div>

      {/* Bottom Section - Alert Feed */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4 }}
        className="mt-4"
      >
        <AlertFeed maxAlerts={10} />
      </motion.div>
    </div>
  );
}
