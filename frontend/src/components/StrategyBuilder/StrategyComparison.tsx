'use client';

import React from 'react';
import { motion } from 'framer-motion';
import { GitCompare } from 'lucide-react';

interface BacktestResult {
  strategyId: string;
  strategyName?: string;
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

interface StrategyComparisonProps {
  strategies: BacktestResult[];
}

export function StrategyComparison({ strategies }: StrategyComparisonProps) {
  if (strategies.length === 0) return null;

  const metrics = [
    { key: 'totalReturn', label: 'Total Return', format: (v: number) => `${(v * 100).toFixed(2)}%`, higher: true },
    { key: 'sharpeRatio', label: 'Sharpe Ratio', format: (v: number) => v.toFixed(2), higher: true },
    { key: 'sortinoRatio', label: 'Sortino Ratio', format: (v: number) => v.toFixed(2), higher: true },
    { key: 'maxDrawdown', label: 'Max Drawdown', format: (v: number) => `-${(v * 100).toFixed(2)}%`, higher: false },
    { key: 'winRate', label: 'Win Rate', format: (v: number) => `${(v * 100).toFixed(1)}%`, higher: true },
    { key: 'profitFactor', label: 'Profit Factor', format: (v: number) => v.toFixed(2), higher: true },
    { key: 'totalTrades', label: 'Total Trades', format: (v: number) => v.toString(), higher: false },
  ];

  const getBestValue = (key: string, higher: boolean) => {
    const values = strategies.map(s => s.metrics[key as keyof typeof s.metrics] as number);
    return higher ? Math.max(...values) : Math.min(...values);
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-zinc-900 rounded-lg border border-zinc-800 p-4"
    >
      <div className="flex items-center gap-2 mb-4">
        <GitCompare className="w-4 h-4 text-purple-500" />
        <h3 className="text-sm font-semibold text-white">Strategy Comparison</h3>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-zinc-800">
              <th className="text-left p-3 text-zinc-500 font-medium">Metric</th>
              {strategies.map((strategy, i) => (
                <th key={i} className="text-right p-3 text-zinc-500 font-medium">
                  {strategy.strategyName || `Strategy ${i + 1}`}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {metrics.map(metric => {
              const bestValue = getBestValue(metric.key, metric.higher);
              return (
                <tr key={metric.key} className="border-b border-zinc-800/50">
                  <td className="p-3 text-zinc-400">{metric.label}</td>
                  {strategies.map((strategy, i) => {
                    const value = strategy.metrics[metric.key as keyof typeof strategy.metrics] as number;
                    const isBest = value === bestValue;
                    return (
                      <td
                        key={i}
                        className={`p-3 text-right font-mono ${
                          isBest ? 'text-green-400 font-semibold' : 'text-zinc-300'
                        }`}
                      >
                        {metric.format(value)}
                        {isBest && (
                          <span className="ml-1 text-green-500 text-[10px]">★</span>
                        )}
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div className="mt-4 p-3 bg-zinc-950 rounded-lg">
        <div className="text-xs text-zinc-500 mb-2">Best Overall Strategy</div>
        <div className="flex items-center justify-between">
          <div className="text-sm font-semibold text-white">
            {(() => {
              const scores = strategies.map((s, i) => ({
                index: i,
                name: s.strategyName || `Strategy ${i + 1}`,
                score: s.metrics.sharpeRatio * 2 + s.metrics.winRate - s.metrics.maxDrawdown * 3,
              }));
              const best = scores.reduce((a, b) => a.score > b.score ? a : b);
              return best.name;
            })()}
          </div>
          <div className="text-xs text-zinc-400">
            Based on risk-adjusted performance
          </div>
        </div>
      </div>
    </motion.div>
  );
}