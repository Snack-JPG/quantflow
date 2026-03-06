'use client';

import React from 'react';
import { motion } from 'framer-motion';
import { TrendingUp, TrendingDown, Minus, AlertTriangle } from 'lucide-react';

interface ExchangeData {
  exchange: string;
  price: number;
  volume24h: number;
  spread: number;
  change24h: number;
  lastUpdate: number;
  isLeading?: boolean;
  hasArbitrage?: boolean;
}

interface MultiExchangeStripProps {
  data: ExchangeData[];
  symbol: string;
}

export function MultiExchangeStrip({ data, symbol }: MultiExchangeStripProps) {
  const avgPrice = data.reduce((acc, d) => acc + d.price, 0) / data.length;
  const maxDeviation = Math.max(...data.map(d => Math.abs(d.price - avgPrice) / avgPrice * 100));

  const formatPrice = (price: number) => {
    if (price >= 1000) return price.toFixed(2);
    if (price >= 1) return price.toFixed(4);
    return price.toFixed(6);
  };

  const formatVolume = (volume: number) => {
    if (volume >= 1e9) return `${(volume / 1e9).toFixed(2)}B`;
    if (volume >= 1e6) return `${(volume / 1e6).toFixed(2)}M`;
    if (volume >= 1e3) return `${(volume / 1e3).toFixed(2)}K`;
    return volume.toFixed(2);
  };

  return (
    <div className="bg-zinc-900 rounded-lg border border-zinc-800 p-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-zinc-400">Cross-Exchange Prices</h3>
        <div className="flex items-center gap-4 text-xs">
          <div className="flex items-center gap-1">
            <span className="text-zinc-500">Symbol:</span>
            <span className="text-white font-mono">{symbol}</span>
          </div>
          <div className="flex items-center gap-1">
            <span className="text-zinc-500">Max Deviation:</span>
            <span className={`font-mono ${maxDeviation > 0.5 ? 'text-yellow-500' : 'text-green-500'}`}>
              {maxDeviation.toFixed(3)}%
            </span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-3">
        {data.map((exchange, index) => {
          const priceDeviation = ((exchange.price - avgPrice) / avgPrice) * 100;
          const isHighest = exchange.price === Math.max(...data.map(d => d.price));
          const isLowest = exchange.price === Math.min(...data.map(d => d.price));

          return (
            <motion.div
              key={exchange.exchange}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.05 }}
              className={`
                bg-zinc-950 rounded-lg p-3 border transition-all duration-200
                ${exchange.isLeading ? 'border-blue-500/50' : 'border-zinc-800'}
                ${exchange.hasArbitrage ? 'ring-2 ring-yellow-500/30' : ''}
                hover:border-zinc-700
              `}
            >
              {/* Exchange Header */}
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-medium text-zinc-400">
                  {exchange.exchange}
                </span>
                <div className="flex items-center gap-1">
                  {exchange.isLeading && (
                    <span className="text-[10px] px-1.5 py-0.5 bg-blue-500/20 text-blue-400 rounded">
                      LEAD
                    </span>
                  )}
                  {exchange.hasArbitrage && (
                    <AlertTriangle className="w-3 h-3 text-yellow-500" />
                  )}
                </div>
              </div>

              {/* Price */}
              <div className="flex items-center justify-between mb-1">
                <span className={`
                  text-lg font-mono font-semibold
                  ${isHighest ? 'text-red-400' : isLowest ? 'text-green-400' : 'text-white'}
                `}>
                  ${formatPrice(exchange.price)}
                </span>
                <div className={`
                  flex items-center gap-0.5
                  ${exchange.change24h > 0 ? 'text-green-500' : exchange.change24h < 0 ? 'text-red-500' : 'text-zinc-500'}
                `}>
                  {exchange.change24h > 0 ? (
                    <TrendingUp className="w-3 h-3" />
                  ) : exchange.change24h < 0 ? (
                    <TrendingDown className="w-3 h-3" />
                  ) : (
                    <Minus className="w-3 h-3" />
                  )}
                  <span className="text-xs font-medium">
                    {Math.abs(exchange.change24h).toFixed(2)}%
                  </span>
                </div>
              </div>

              {/* Metrics */}
              <div className="grid grid-cols-2 gap-2 text-[10px]">
                <div>
                  <span className="text-zinc-600">Volume</span>
                  <div className="font-mono text-zinc-400">
                    ${formatVolume(exchange.volume24h)}
                  </div>
                </div>
                <div>
                  <span className="text-zinc-600">Spread</span>
                  <div className="font-mono text-zinc-400">
                    {exchange.spread.toFixed(2)} bps
                  </div>
                </div>
              </div>

              {/* Price Deviation Bar */}
              <div className="mt-2 h-1 bg-zinc-800 rounded-full overflow-hidden">
                <motion.div
                  className={`h-full ${priceDeviation > 0 ? 'bg-red-500' : 'bg-green-500'}`}
                  initial={{ width: 0 }}
                  animate={{ width: `${Math.min(Math.abs(priceDeviation) * 20, 100)}%` }}
                  transition={{ duration: 0.5 }}
                />
              </div>
            </motion.div>
          );
        })}
      </div>

      {/* Arbitrage Alert */}
      {maxDeviation > 0.5 && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          className="mt-4 p-3 bg-yellow-500/10 border border-yellow-500/30 rounded-lg"
        >
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-yellow-500" />
            <span className="text-xs text-yellow-500">
              Potential arbitrage opportunity detected: {maxDeviation.toFixed(3)}% price deviation
            </span>
          </div>
        </motion.div>
      )}
    </div>
  );
}