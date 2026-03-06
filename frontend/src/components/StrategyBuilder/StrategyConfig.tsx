'use client';

import React from 'react';
import { motion } from 'framer-motion';
import { Settings, TrendingUp, Shield, AlertTriangle } from 'lucide-react';

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

interface StrategyConfigProps {
  strategy: Strategy;
  onChange: (strategy: Strategy) => void;
}

const availableSignals = [
  { id: 'spread', name: 'Bid-Ask Spread', category: 'microstructure' },
  { id: 'vpin', name: 'VPIN (Toxicity)', category: 'flow' },
  { id: 'kyle_lambda', name: "Kyle's Lambda", category: 'impact' },
  { id: 'order_flow_imbalance', name: 'Order Flow Imbalance', category: 'flow' },
  { id: 'depth_imbalance', name: 'Depth Imbalance', category: 'book' },
  { id: 'hurst', name: 'Hurst Exponent', category: 'regime' },
  { id: 'realized_volatility', name: 'Realized Volatility', category: 'volatility' },
  { id: 'amihud_illiquidity', name: 'Amihud Illiquidity', category: 'liquidity' },
];

export function StrategyConfig({ strategy, onChange }: StrategyConfigProps) {
  const toggleSignal = (signalId: string) => {
    const newSignals = strategy.signals.includes(signalId)
      ? strategy.signals.filter(s => s !== signalId)
      : [...strategy.signals, signalId];

    onChange({ ...strategy, signals: newSignals });
  };

  const updateEntryRule = (
    index: number,
    field: 'condition' | 'threshold',
    value: string | number
  ) => {
    const newRules = [...strategy.entryRules];
    newRules[index] = { ...newRules[index], [field]: value };
    onChange({ ...strategy, entryRules: newRules });
  };

  const updateExitRule = (
    index: number,
    field: 'condition' | 'threshold',
    value: string | number
  ) => {
    const newRules = [...strategy.exitRules];
    newRules[index] = { ...newRules[index], [field]: value };
    onChange({ ...strategy, exitRules: newRules });
  };

  const updateRiskManagement = (field: keyof typeof strategy.riskManagement, value: number) => {
    onChange({
      ...strategy,
      riskManagement: {
        ...strategy.riskManagement,
        [field]: value,
      },
    });
  };

  return (
    <div className="space-y-4">
      {/* Strategy Name */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-zinc-900 rounded-lg border border-zinc-800 p-4"
      >
        <div className="flex items-center gap-2 mb-3">
          <Settings className="w-4 h-4 text-purple-500" />
          <h3 className="text-sm font-semibold text-white">Strategy Configuration</h3>
        </div>
        <input
          type="text"
          value={strategy.name}
          onChange={(e) => onChange({ ...strategy, name: e.target.value })}
          className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-purple-500"
          placeholder="Strategy Name"
        />
      </motion.div>

      {/* Signal Selection */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="bg-zinc-900 rounded-lg border border-zinc-800 p-4"
      >
        <div className="flex items-center gap-2 mb-3">
          <TrendingUp className="w-4 h-4 text-blue-500" />
          <h3 className="text-sm font-semibold text-white">Trading Signals</h3>
        </div>
        <div className="grid grid-cols-2 gap-2">
          {availableSignals.map(signal => (
            <button
              key={signal.id}
              onClick={() => toggleSignal(signal.id)}
              className={`
                p-2 rounded-lg text-xs text-left transition-all
                ${strategy.signals.includes(signal.id)
                  ? 'bg-purple-600/20 border-2 border-purple-600 text-purple-300'
                  : 'bg-zinc-950 border-2 border-zinc-800 text-zinc-400 hover:border-zinc-700'
                }
              `}
            >
              <div className="font-medium">{signal.name}</div>
              <div className="text-[10px] opacity-70">{signal.category}</div>
            </button>
          ))}
        </div>
      </motion.div>

      {/* Entry Rules */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="bg-zinc-900 rounded-lg border border-zinc-800 p-4"
      >
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-green-500" />
            <h3 className="text-sm font-semibold text-white">Entry Rules</h3>
          </div>
          <button
            onClick={() => onChange({
              ...strategy,
              entryRules: [...strategy.entryRules, { condition: '', threshold: 0 }]
            })}
            className="text-xs text-green-400 hover:text-green-300"
          >
            + Add Rule
          </button>
        </div>
        <div className="space-y-2">
          {strategy.entryRules.map((rule, index) => (
            <div key={index} className="flex items-center gap-2">
              <select
                value={rule.condition}
                onChange={(e) => updateEntryRule(index, 'condition', e.target.value)}
                className="flex-1 bg-zinc-950 border border-zinc-800 rounded px-2 py-1 text-xs text-white"
              >
                <option value="">Select condition</option>
                <option value="spread > threshold">Spread Above</option>
                <option value="spread < threshold">Spread Below</option>
                <option value="vpin > threshold">VPIN Above</option>
                <option value="vpin < threshold">VPIN Below</option>
                <option value="imbalance > threshold">Imbalance Above</option>
                <option value="imbalance < threshold">Imbalance Below</option>
              </select>
              <input
                type="number"
                value={rule.threshold}
                onChange={(e) => updateEntryRule(index, 'threshold', parseFloat(e.target.value))}
                className="w-20 bg-zinc-950 border border-zinc-800 rounded px-2 py-1 text-xs text-white"
                placeholder="Value"
              />
              <button
                onClick={() => onChange({
                  ...strategy,
                  entryRules: strategy.entryRules.filter((_, i) => i !== index)
                })}
                className="text-red-400 hover:text-red-300 text-xs"
              >
                ×
              </button>
            </div>
          ))}
        </div>
      </motion.div>

      {/* Exit Rules */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3 }}
        className="bg-zinc-900 rounded-lg border border-zinc-800 p-4"
      >
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-red-500" />
            <h3 className="text-sm font-semibold text-white">Exit Rules</h3>
          </div>
          <button
            onClick={() => onChange({
              ...strategy,
              exitRules: [...strategy.exitRules, { condition: '', threshold: 0 }]
            })}
            className="text-xs text-red-400 hover:text-red-300"
          >
            + Add Rule
          </button>
        </div>
        <div className="space-y-2">
          {strategy.exitRules.map((rule, index) => (
            <div key={index} className="flex items-center gap-2">
              <select
                value={rule.condition}
                onChange={(e) => updateExitRule(index, 'condition', e.target.value)}
                className="flex-1 bg-zinc-950 border border-zinc-800 rounded px-2 py-1 text-xs text-white"
              >
                <option value="">Select condition</option>
                <option value="spread < threshold">Spread Below</option>
                <option value="time_limit">Time Limit (seconds)</option>
                <option value="profit_target">Profit Target</option>
                <option value="stop_loss">Stop Loss</option>
                <option value="trailing_stop">Trailing Stop</option>
              </select>
              <input
                type="number"
                value={rule.threshold}
                onChange={(e) => updateExitRule(index, 'threshold', parseFloat(e.target.value))}
                className="w-20 bg-zinc-950 border border-zinc-800 rounded px-2 py-1 text-xs text-white"
                placeholder="Value"
              />
              <button
                onClick={() => onChange({
                  ...strategy,
                  exitRules: strategy.exitRules.filter((_, i) => i !== index)
                })}
                className="text-red-400 hover:text-red-300 text-xs"
              >
                ×
              </button>
            </div>
          ))}
        </div>
      </motion.div>

      {/* Risk Management */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4 }}
        className="bg-zinc-900 rounded-lg border border-zinc-800 p-4"
      >
        <div className="flex items-center gap-2 mb-3">
          <Shield className="w-4 h-4 text-yellow-500" />
          <h3 className="text-sm font-semibold text-white">Risk Management</h3>
        </div>
        <div className="space-y-3">
          <div>
            <label className="text-xs text-zinc-400 mb-1 block">Stop Loss (%)</label>
            <input
              type="number"
              value={strategy.riskManagement.stopLoss * 100}
              onChange={(e) => updateRiskManagement('stopLoss', parseFloat(e.target.value) / 100)}
              className="w-full bg-zinc-950 border border-zinc-800 rounded px-2 py-1 text-xs text-white"
              step="0.1"
            />
          </div>
          <div>
            <label className="text-xs text-zinc-400 mb-1 block">Take Profit (%)</label>
            <input
              type="number"
              value={strategy.riskManagement.takeProfit * 100}
              onChange={(e) => updateRiskManagement('takeProfit', parseFloat(e.target.value) / 100)}
              className="w-full bg-zinc-950 border border-zinc-800 rounded px-2 py-1 text-xs text-white"
              step="0.1"
            />
          </div>
          <div>
            <label className="text-xs text-zinc-400 mb-1 block">Position Size (%)</label>
            <input
              type="number"
              value={strategy.riskManagement.positionSize * 100}
              onChange={(e) => updateRiskManagement('positionSize', parseFloat(e.target.value) / 100)}
              className="w-full bg-zinc-950 border border-zinc-800 rounded px-2 py-1 text-xs text-white"
              step="1"
            />
          </div>
        </div>
      </motion.div>
    </div>
  );
}
