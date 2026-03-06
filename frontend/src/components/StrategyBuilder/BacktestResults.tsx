'use client';

import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { FileText, Download, Eye, EyeOff } from 'lucide-react';

interface Trade {
  entryTime: number;
  exitTime: number;
  entryPrice: number;
  exitPrice: number;
  pnl: number;
  side: 'long' | 'short';
}

interface BacktestResult {
  strategyId: string;
  equityCurve: Array<{ timestamp: number; value: number }>;
  trades: Trade[];
  metrics: {
    totalReturn: number;
    sharpeRatio: number;
    sortinoRatio: number;
    maxDrawdown: number;
    winRate: number;
    avgWin: number;
    avgLoss: number;
    profitFactor: number;
    totalTrades: number;
  };
}

interface BacktestResultsProps {
  result: BacktestResult;
}

export function BacktestResults({ result }: BacktestResultsProps) {
  const [showAllTrades, setShowAllTrades] = useState(false);
  const [sortBy, setSortBy] = useState<'time' | 'pnl' | 'duration'>('time');
  const [filterSide, setFilterSide] = useState<'all' | 'long' | 'short'>('all');
  const sortOptions = ['time', 'pnl', 'duration'] as const;
  const sideOptions = ['all', 'long', 'short'] as const;

  const formatDate = (timestamp: number) => {
    return new Date(timestamp).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const formatDuration = (ms: number) => {
    const hours = Math.floor(ms / (1000 * 60 * 60));
    const days = Math.floor(hours / 24);
    if (days > 0) return `${days}d ${hours % 24}h`;
    return `${hours}h`;
  };

  // Filter and sort trades
  let filteredTrades = result.trades;
  if (filterSide !== 'all') {
    filteredTrades = filteredTrades.filter(t => t.side === filterSide);
  }

  const sortedTrades = [...filteredTrades].sort((a, b) => {
    switch (sortBy) {
      case 'pnl':
        return b.pnl - a.pnl;
      case 'duration':
        return (b.exitTime - b.entryTime) - (a.exitTime - a.entryTime);
      default:
        return b.entryTime - a.entryTime;
    }
  });

  const displayedTrades = showAllTrades ? sortedTrades : sortedTrades.slice(0, 10);

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-zinc-900 rounded-lg border border-zinc-800"
    >
      <div className="p-4 border-b border-zinc-800">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <FileText className="w-4 h-4 text-blue-500" />
            <h3 className="text-sm font-semibold text-white">Trade History</h3>
          </div>
          <div className="flex items-center gap-2">
            <select
              value={filterSide}
              onChange={(e) => {
                const nextValue = e.target.value as (typeof sideOptions)[number];
                if (sideOptions.includes(nextValue)) {
                  setFilterSide(nextValue);
                }
              }}
              className="bg-zinc-950 border border-zinc-800 rounded px-2 py-1 text-xs text-white"
            >
              <option value="all">All Trades</option>
              <option value="long">Long Only</option>
              <option value="short">Short Only</option>
            </select>
            <select
              value={sortBy}
              onChange={(e) => {
                const nextValue = e.target.value as (typeof sortOptions)[number];
                if (sortOptions.includes(nextValue)) {
                  setSortBy(nextValue);
                }
              }}
              className="bg-zinc-950 border border-zinc-800 rounded px-2 py-1 text-xs text-white"
            >
              <option value="time">Sort by Time</option>
              <option value="pnl">Sort by PnL</option>
              <option value="duration">Sort by Duration</option>
            </select>
            <button className="p-1 text-zinc-400 hover:text-white transition-colors">
              <Download className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-zinc-800">
              <th className="text-left p-3 text-zinc-500 font-medium">#</th>
              <th className="text-left p-3 text-zinc-500 font-medium">Entry Time</th>
              <th className="text-left p-3 text-zinc-500 font-medium">Exit Time</th>
              <th className="text-left p-3 text-zinc-500 font-medium">Duration</th>
              <th className="text-left p-3 text-zinc-500 font-medium">Side</th>
              <th className="text-right p-3 text-zinc-500 font-medium">Entry Price</th>
              <th className="text-right p-3 text-zinc-500 font-medium">Exit Price</th>
              <th className="text-right p-3 text-zinc-500 font-medium">PnL</th>
              <th className="text-right p-3 text-zinc-500 font-medium">Return</th>
            </tr>
          </thead>
          <tbody>
            {displayedTrades.map((trade, index) => {
              const returnPct = ((trade.exitPrice - trade.entryPrice) / trade.entryPrice) * 100;
              return (
                <motion.tr
                  key={index}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: index * 0.01 }}
                  className="border-b border-zinc-800/50 hover:bg-zinc-800/20 transition-colors"
                >
                  <td className="p-3 text-zinc-600">{index + 1}</td>
                  <td className="p-3 text-zinc-400">{formatDate(trade.entryTime)}</td>
                  <td className="p-3 text-zinc-400">{formatDate(trade.exitTime)}</td>
                  <td className="p-3 text-zinc-400">{formatDuration(trade.exitTime - trade.entryTime)}</td>
                  <td className="p-3">
                    <span className={`
                      px-2 py-0.5 rounded text-[10px] font-medium
                      ${trade.side === 'long'
                        ? 'bg-green-500/20 text-green-400'
                        : 'bg-red-500/20 text-red-400'
                      }
                    `}>
                      {trade.side.toUpperCase()}
                    </span>
                  </td>
                  <td className="p-3 text-right font-mono text-zinc-300">
                    ${trade.entryPrice.toFixed(2)}
                  </td>
                  <td className="p-3 text-right font-mono text-zinc-300">
                    ${trade.exitPrice.toFixed(2)}
                  </td>
                  <td className={`p-3 text-right font-mono font-semibold ${
                    trade.pnl >= 0 ? 'text-green-400' : 'text-red-400'
                  }`}>
                    {trade.pnl >= 0 ? '+' : ''}{trade.pnl.toFixed(2)}
                  </td>
                  <td className={`p-3 text-right font-mono ${
                    returnPct >= 0 ? 'text-green-400' : 'text-red-400'
                  }`}>
                    {returnPct >= 0 ? '+' : ''}{returnPct.toFixed(2)}%
                  </td>
                </motion.tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {sortedTrades.length > 10 && (
        <div className="p-3 border-t border-zinc-800">
          <button
            onClick={() => setShowAllTrades(!showAllTrades)}
            className="flex items-center gap-2 text-xs text-blue-400 hover:text-blue-300 transition-colors mx-auto"
          >
            {showAllTrades ? (
              <>
                <EyeOff className="w-3 h-3" />
                Show Less
              </>
            ) : (
              <>
                <Eye className="w-3 h-3" />
                Show All {sortedTrades.length} Trades
              </>
            )}
          </button>
        </div>
      )}
    </motion.div>
  );
}
