'use client';

import React from 'react';
import { motion } from 'framer-motion';
import { TrendingUp, TrendingDown, Activity, Award } from 'lucide-react';

interface Metrics {
  totalReturn: number;
  sharpeRatio: number;
  sortinoRatio: number;
  maxDrawdown: number;
  winRate: number;
  avgWin: number;
  avgLoss: number;
  profitFactor: number;
  totalTrades: number;
}

interface PerformanceMetricsProps {
  metrics: Metrics;
}

export function PerformanceMetrics({ metrics }: PerformanceMetricsProps) {
  const getMetricColor = (metric: string, value: number) => {
    switch (metric) {
      case 'return':
        return value >= 0 ? 'text-green-400' : 'text-red-400';
      case 'sharpe':
        return value >= 1.5 ? 'text-green-400' : value >= 1 ? 'text-yellow-400' : 'text-red-400';
      case 'drawdown':
        return value <= 0.1 ? 'text-green-400' : value <= 0.2 ? 'text-yellow-400' : 'text-red-400';
      case 'winrate':
        return value >= 0.6 ? 'text-green-400' : value >= 0.4 ? 'text-yellow-400' : 'text-red-400';
      default:
        return 'text-white';
    }
  };

  const metricCards = [
    {
      label: 'Total Return',
      value: `${metrics.totalReturn >= 0 ? '+' : ''}${(metrics.totalReturn * 100).toFixed(2)}%`,
      icon: metrics.totalReturn >= 0 ? TrendingUp : TrendingDown,
      color: getMetricColor('return', metrics.totalReturn),
      description: 'Overall strategy performance',
    },
    {
      label: 'Sharpe Ratio',
      value: metrics.sharpeRatio.toFixed(2),
      icon: Award,
      color: getMetricColor('sharpe', metrics.sharpeRatio),
      description: 'Risk-adjusted returns',
    },
    {
      label: 'Max Drawdown',
      value: `-${(metrics.maxDrawdown * 100).toFixed(2)}%`,
      icon: TrendingDown,
      color: getMetricColor('drawdown', metrics.maxDrawdown),
      description: 'Largest peak-to-trough decline',
    },
    {
      label: 'Win Rate',
      value: `${(metrics.winRate * 100).toFixed(1)}%`,
      icon: Activity,
      color: getMetricColor('winrate', metrics.winRate),
      description: 'Percentage of winning trades',
    },
  ];

  const detailedMetrics = [
    { label: 'Sortino Ratio', value: metrics.sortinoRatio.toFixed(2), description: 'Downside risk-adjusted return' },
    { label: 'Profit Factor', value: metrics.profitFactor.toFixed(2), description: 'Gross profit / Gross loss' },
    { label: 'Total Trades', value: metrics.totalTrades.toString(), description: 'Number of completed trades' },
    { label: 'Avg Win', value: `$${metrics.avgWin.toFixed(2)}`, description: 'Average winning trade' },
    { label: 'Avg Loss', value: `-$${metrics.avgLoss.toFixed(2)}`, description: 'Average losing trade' },
    { label: 'Win/Loss Ratio', value: (metrics.avgWin / metrics.avgLoss).toFixed(2), description: 'Avg win / Avg loss' },
  ];

  return (
    <div className="space-y-4">
      {/* Primary Metrics Cards */}
      <div className="grid grid-cols-4 gap-4">
        {metricCards.map((metric, index) => {
          const Icon = metric.icon;
          return (
            <motion.div
              key={metric.label}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.1 }}
              className="bg-zinc-900 rounded-lg border border-zinc-800 p-4"
            >
              <div className="flex items-start justify-between mb-2">
                <Icon className={`w-5 h-5 ${metric.color}`} />
                <span className={`text-lg font-mono font-bold ${metric.color}`}>
                  {metric.value}
                </span>
              </div>
              <h4 className="text-xs font-medium text-zinc-400 mb-1">{metric.label}</h4>
              <p className="text-[10px] text-zinc-600">{metric.description}</p>
            </motion.div>
          );
        })}
      </div>

      {/* Detailed Metrics Table */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4 }}
        className="bg-zinc-900 rounded-lg border border-zinc-800 p-4"
      >
        <h3 className="text-sm font-semibold text-white mb-3">Detailed Performance Metrics</h3>
        <div className="grid grid-cols-3 gap-3">
          {detailedMetrics.map((metric, index) => (
            <div
              key={metric.label}
              className="bg-zinc-950 rounded-lg p-3"
            >
              <div className="text-[10px] text-zinc-500 mb-1">{metric.label}</div>
              <div className="text-sm font-mono text-white mb-1">{metric.value}</div>
              <div className="text-[9px] text-zinc-600">{metric.description}</div>
            </div>
          ))}
        </div>
      </motion.div>

      {/* Performance Grade */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.5 }}
        className="bg-gradient-to-r from-purple-900/20 to-blue-900/20 rounded-lg border border-purple-800/30 p-4"
      >
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-sm font-semibold text-white mb-1">Strategy Grade</h3>
            <p className="text-xs text-zinc-400">
              Based on risk-adjusted performance metrics
            </p>
          </div>
          <div className="text-center">
            <div className="text-3xl font-bold text-purple-400">
              {metrics.sharpeRatio >= 2 ? 'A+' :
               metrics.sharpeRatio >= 1.5 ? 'A' :
               metrics.sharpeRatio >= 1 ? 'B' :
               metrics.sharpeRatio >= 0.5 ? 'C' : 'D'}
            </div>
            <div className="text-[10px] text-zinc-500 mt-1">
              {metrics.sharpeRatio >= 2 ? 'Excellent' :
               metrics.sharpeRatio >= 1.5 ? 'Very Good' :
               metrics.sharpeRatio >= 1 ? 'Good' :
               metrics.sharpeRatio >= 0.5 ? 'Average' : 'Poor'}
            </div>
          </div>
        </div>
      </motion.div>
    </div>
  );
}