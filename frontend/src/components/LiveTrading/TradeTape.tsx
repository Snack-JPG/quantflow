'use client';

import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ArrowUp, ArrowDown, Activity } from 'lucide-react';

interface Trade {
  id: string;
  price: number;
  quantity: number;
  timestamp: number;
  side: 'buy' | 'sell';
  exchange?: string;
  isLarge?: boolean;
  isAggressive?: boolean;
}

interface TradeTapeProps {
  trades: Trade[];
  showAggregation?: boolean;
}

export function TradeTape({ trades, showAggregation = true }: TradeTapeProps) {
  const [aggregatedTrades, setAggregatedTrades] = useState<Map<number, Trade[]>>(new Map());
  const [priceDirection, setPriceDirection] = useState<Map<number, 'up' | 'down' | 'neutral'>>(new Map());

  useEffect(() => {
    if (!showAggregation) return;

    // Aggregate trades by price level
    const aggregation = new Map<number, Trade[]>();
    const direction = new Map<number, 'up' | 'down' | 'neutral'>();

    trades.forEach((trade, index) => {
      const priceKey = Math.round(trade.price * 100) / 100;

      if (!aggregation.has(priceKey)) {
        aggregation.set(priceKey, []);
      }
      aggregation.get(priceKey)!.push(trade);

      // Determine price direction
      if (index > 0) {
        const prevTrade = trades[index - 1];
        if (trade.price > prevTrade.price) {
          direction.set(priceKey, 'up');
        } else if (trade.price < prevTrade.price) {
          direction.set(priceKey, 'down');
        } else {
          direction.set(priceKey, 'neutral');
        }
      }
    });

    setAggregatedTrades(aggregation);
    setPriceDirection(direction);
  }, [trades, showAggregation]);

  const formatPrice = (price: number) => {
    if (price >= 1000) return price.toFixed(2);
    if (price >= 1) return price.toFixed(4);
    return price.toFixed(6);
  };

  const formatQuantity = (qty: number) => {
    if (qty >= 1000) return `${(qty / 1000).toFixed(2)}K`;
    if (qty >= 1) return qty.toFixed(4);
    return qty.toFixed(6);
  };

  const formatTime = (timestamp: number) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('en-US', {
      hour12: false,
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      fractionalSecondDigits: 3
    });
  };

  return (
    <div className="bg-zinc-900 rounded-lg border border-zinc-800">
      <div className="p-4 border-b border-zinc-800">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Activity className="w-4 h-4 text-blue-500" />
            <h3 className="text-sm font-semibold text-white">Trade Tape</h3>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs text-zinc-500">Live</span>
            <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
          </div>
        </div>
      </div>

      <div className="overflow-hidden">
        <div className="grid grid-cols-5 gap-2 px-4 py-2 text-xs text-zinc-500 border-b border-zinc-800">
          <div>Time</div>
          <div className="text-right">Price</div>
          <div className="text-right">Size</div>
          <div className="text-right">Value</div>
          <div className="text-center">Side</div>
        </div>

        <div className="max-h-[600px] overflow-y-auto">
          <AnimatePresence mode="popLayout">
            {trades.slice(0, 100).map((trade, index) => (
              <motion.div
                key={`${trade.id}-${index}`}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 20 }}
                transition={{ duration: 0.2 }}
                className={`
                  grid grid-cols-5 gap-2 px-4 py-2 text-xs font-mono
                  border-b border-zinc-800/50 hover:bg-zinc-800/30 transition-colors
                  ${trade.isLarge ? 'bg-yellow-500/5' : ''}
                  ${trade.isAggressive ? 'bg-purple-500/5' : ''}
                `}
              >
                {/* Time */}
                <div className="text-zinc-400">
                  {formatTime(trade.timestamp)}
                </div>

                {/* Price with direction indicator */}
                <div className="text-right flex items-center justify-end gap-1">
                  <span className={trade.side === 'buy' ? 'text-green-400' : 'text-red-400'}>
                    {formatPrice(trade.price)}
                  </span>
                  {index === 0 && trades.length > 1 && (
                    <>
                      {trade.price > trades[1].price ? (
                        <ArrowUp className="w-3 h-3 text-green-500" />
                      ) : trade.price < trades[1].price ? (
                        <ArrowDown className="w-3 h-3 text-red-500" />
                      ) : null}
                    </>
                  )}
                </div>

                {/* Size */}
                <div className={`text-right ${trade.isLarge ? 'text-yellow-500 font-semibold' : 'text-zinc-300'}`}>
                  {formatQuantity(trade.quantity)}
                </div>

                {/* Value */}
                <div className="text-right text-zinc-400">
                  ${(trade.price * trade.quantity).toFixed(2)}
                </div>

                {/* Side indicator */}
                <div className="flex justify-center">
                  <span
                    className={`
                      px-2 py-0.5 rounded text-[10px] font-medium
                      ${trade.side === 'buy'
                        ? 'bg-green-500/20 text-green-400'
                        : 'bg-red-500/20 text-red-400'
                      }
                    `}
                  >
                    {trade.side.toUpperCase()}
                  </span>
                </div>
              </motion.div>
            ))}
          </AnimatePresence>

          {trades.length === 0 && (
            <div className="text-center py-8 text-zinc-500">
              Waiting for trades...
            </div>
          )}
        </div>
      </div>

      {/* Summary Stats */}
      {trades.length > 0 && (
        <div className="p-4 border-t border-zinc-800 bg-zinc-950/50">
          <div className="grid grid-cols-3 gap-4 text-xs">
            <div>
              <span className="text-zinc-500">Total Trades</span>
              <div className="font-mono text-white">{trades.length}</div>
            </div>
            <div>
              <span className="text-zinc-500">Buy Volume</span>
              <div className="font-mono text-green-400">
                {formatQuantity(
                  trades
                    .filter(t => t.side === 'buy')
                    .reduce((acc, t) => acc + t.quantity, 0)
                )}
              </div>
            </div>
            <div>
              <span className="text-zinc-500">Sell Volume</span>
              <div className="font-mono text-red-400">
                {formatQuantity(
                  trades
                    .filter(t => t.side === 'sell')
                    .reduce((acc, t) => acc + t.quantity, 0)
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}