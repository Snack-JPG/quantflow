'use client';

import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { StrategyConfig } from '@/components/StrategyBuilder/StrategyConfig';
import { BacktestResults } from '@/components/StrategyBuilder/BacktestResults';
import { EquityCurve } from '@/components/StrategyBuilder/EquityCurve';
import { TradeScatter } from '@/components/StrategyBuilder/TradeScatter';
import { PerformanceMetrics } from '@/components/StrategyBuilder/PerformanceMetrics';
import { StrategyComparison } from '@/components/StrategyBuilder/StrategyComparison';
import { Beaker, Play, Save, Upload, ChevronRight, AlertCircle } from 'lucide-react';

interface Strategy {
  id: string;
  name: string;
  signals: string[];
  entryRules: {
    condition: string;
    threshold: number;
  }[];
  exitRules: {
    condition: string;
    threshold: number;
  }[];
  riskManagement: {
    stopLoss: number;
    takeProfit: number;
    positionSize: number;
  };
}

interface BacktestResult {
  strategyId: string;
  equityCurve: Array<{ timestamp: number; value: number }>;
  trades: Array<{
    entryTime: number;
    exitTime: number;
    entryPrice: number;
    exitPrice: number;
    pnl: number;
    side: 'long' | 'short';
  }>;
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

export default function StrategyBuilderPage() {
  const [selectedStrategy, setSelectedStrategy] = useState<Strategy>({
    id: '1',
    name: 'Mean Reversion Alpha',
    signals: ['spread', 'vpin', 'order_flow_imbalance'],
    entryRules: [
      { condition: 'spread > threshold', threshold: 10 },
      { condition: 'vpin < threshold', threshold: 0.5 },
    ],
    exitRules: [
      { condition: 'spread < threshold', threshold: 5 },
      { condition: 'time_limit', threshold: 3600 },
    ],
    riskManagement: {
      stopLoss: 0.02,
      takeProfit: 0.05,
      positionSize: 0.1,
    },
  });

  const [backtestResults, setBacktestResults] = useState<BacktestResult | null>(null);
  const [isBacktesting, setIsBacktesting] = useState(false);
  const [compareStrategies, setCompareStrategies] = useState<BacktestResult[]>([]);

  const runBacktest = async () => {
    setIsBacktesting(true);

    // Simulate backtest delay
    await new Promise(resolve => setTimeout(resolve, 2000));

    // Generate mock backtest results
    const equityCurve = Array.from({ length: 100 }, (_, i) => ({
      timestamp: Date.now() - (100 - i) * 86400000,
      value: 10000 * (1 + 0.002 * i + Math.sin(i / 10) * 0.05),
    }));

    const trades = Array.from({ length: 50 }, (_, i) => {
      const entryTime = Date.now() - (100 - i * 2) * 86400000;
      const exitTime = entryTime + Math.random() * 86400000 * 3;
      const entryPrice = 45000 + Math.random() * 2000;
      const pnl = (Math.random() - 0.45) * 500;
      const exitPrice = entryPrice * (1 + pnl / entryPrice);

      return {
        entryTime,
        exitTime,
        entryPrice,
        exitPrice,
        pnl,
        side: Math.random() > 0.5 ? 'long' as const : 'short' as const,
      };
    });

    const wins = trades.filter(t => t.pnl > 0);
    const losses = trades.filter(t => t.pnl < 0);

    const result: BacktestResult = {
      strategyId: selectedStrategy.id,
      equityCurve,
      trades,
      metrics: {
        totalReturn: 0.24,
        sharpeRatio: 1.82,
        sortinoRatio: 2.15,
        maxDrawdown: 0.08,
        winRate: wins.length / trades.length,
        avgWin: wins.reduce((sum, t) => sum + t.pnl, 0) / wins.length,
        avgLoss: losses.reduce((sum, t) => sum + Math.abs(t.pnl), 0) / losses.length,
        profitFactor: 1.85,
        totalTrades: trades.length,
      },
    };

    setBacktestResults(result);
    setIsBacktesting(false);
  };

  return (
    <div className="min-h-screen bg-zinc-950 p-4">
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="max-w-[1920px] mx-auto"
      >
        {/* Header */}
        <div className="mb-6 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Beaker className="w-6 h-6 text-purple-500" />
            <h1 className="text-2xl font-bold text-white">Strategy Builder</h1>
          </div>
          <div className="flex items-center gap-3">
            <button className="flex items-center gap-2 px-4 py-2 bg-zinc-900 text-zinc-400 rounded-lg hover:text-white transition-colors border border-zinc-800">
              <Upload className="w-4 h-4" />
              Import Strategy
            </button>
            <button className="flex items-center gap-2 px-4 py-2 bg-zinc-900 text-zinc-400 rounded-lg hover:text-white transition-colors border border-zinc-800">
              <Save className="w-4 h-4" />
              Save Strategy
            </button>
            <button
              onClick={runBacktest}
              disabled={isBacktesting}
              className="flex items-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors disabled:opacity-50"
            >
              {isBacktesting ? (
                <>
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  Running Backtest...
                </>
              ) : (
                <>
                  <Play className="w-4 h-4" />
                  Run Backtest
                </>
              )}
            </button>
          </div>
        </div>

        {/* Main Grid */}
        <div className="grid grid-cols-12 gap-4">
          {/* Left Panel - Strategy Configuration */}
          <div className="col-span-12 lg:col-span-4 space-y-4">
            <StrategyConfig
              strategy={selectedStrategy}
              onChange={setSelectedStrategy}
            />
          </div>

          {/* Right Panel - Results */}
          <div className="col-span-12 lg:col-span-8 space-y-4">
            {backtestResults ? (
              <>
                {/* Performance Metrics */}
                <PerformanceMetrics metrics={backtestResults.metrics} />

                {/* Equity Curve */}
                <EquityCurve data={backtestResults.equityCurve} />

                {/* Trade Scatter */}
                <TradeScatter trades={backtestResults.trades} />

                {/* Detailed Results */}
                <BacktestResults result={backtestResults} />
              </>
            ) : (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="bg-zinc-900 rounded-lg border border-zinc-800 p-12"
              >
                <div className="text-center">
                  <Beaker className="w-16 h-16 text-zinc-700 mx-auto mb-4" />
                  <h3 className="text-lg font-semibold text-white mb-2">
                    Configure Your Strategy
                  </h3>
                  <p className="text-sm text-zinc-500 mb-6 max-w-md mx-auto">
                    Set up your trading signals, entry/exit rules, and risk parameters,
                    then run a backtest to see historical performance.
                  </p>
                  <button
                    onClick={runBacktest}
                    className="flex items-center gap-2 px-6 py-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors mx-auto"
                  >
                    <Play className="w-4 h-4" />
                    Run Your First Backtest
                  </button>
                </div>
              </motion.div>
            )}

            {/* Strategy Comparison */}
            {compareStrategies.length > 0 && (
              <StrategyComparison strategies={compareStrategies} />
            )}
          </div>
        </div>

        {/* Walk-Forward Optimization Section */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="mt-6 bg-zinc-900 rounded-lg border border-zinc-800 p-6"
        >
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-white">Walk-Forward Optimization</h3>
            <button className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">
              <ChevronRight className="w-4 h-4" />
              Run Optimization
            </button>
          </div>
          <div className="grid grid-cols-4 gap-4">
            {['In-Sample Period', 'Out-of-Sample Period', 'Walk Steps', 'Optimization Metric'].map((label, i) => (
              <div key={label} className="bg-zinc-950 rounded-lg p-3">
                <div className="text-xs text-zinc-500 mb-1">{label}</div>
                <select className="w-full bg-transparent text-sm text-white border border-zinc-800 rounded px-2 py-1">
                  {i === 0 && <option>6 months</option>}
                  {i === 1 && <option>2 months</option>}
                  {i === 2 && <option>12 steps</option>}
                  {i === 3 && <option>Sharpe Ratio</option>}
                </select>
              </div>
            ))}
          </div>
        </motion.div>
      </motion.div>
    </div>
  );
}