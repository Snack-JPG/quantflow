'use client';

import React, { useState, useEffect } from 'react';
import { MetricTimeseries } from '@/components/AnalysisLab/MetricTimeseries';
import { FlowHeatmap } from '@/components/AnalysisLab/FlowHeatmap';
import { ToxicityGauge } from '@/components/AnalysisLab/ToxicityGauge';
import { RegimeTimeline } from '@/components/AnalysisLab/RegimeTimeline';
import { motion } from 'framer-motion';
import { BarChart3, Download, RefreshCw, Settings } from 'lucide-react';

// Generate mock data for demonstration
const generateMockMetricData = (points: number = 100) => {
  const now = Date.now();
  const interval = 5 * 60 * 1000; // 5 minutes

  return Array.from({ length: points }, (_, i) => ({
    timestamp: now - (points - i - 1) * interval,
    spread: 2 + Math.random() * 3,
    kyle_lambda: 0.001 + Math.random() * 0.002,
    vpin: 0.3 + Math.random() * 0.4,
    realized_volatility: 0.015 + Math.random() * 0.03,
    order_flow_imbalance: Math.random() * 0.6 - 0.3,
    depth_imbalance: Math.random() * 0.4 - 0.2,
    amihud_illiquidity: Math.random() * 0.00001,
    roll_spread: 1.5 + Math.random() * 2
  }));
};

const generateMockFlowData = (points: number = 500) => {
  const now = Date.now();
  const basePrice = 45000;

  return Array.from({ length: points }, (_, i) => ({
    timestamp: now - (points - i - 1) * 60000,
    priceLevel: basePrice + Math.random() * 1000 - 500,
    netFlow: Math.random() * 2 - 1,
    buyVolume: Math.random() * 100,
    sellVolume: Math.random() * 100
  }));
};

const generateMockRegimes = () => {
  const now = Date.now();
  const hour = 60 * 60 * 1000;

  return [
    {
      start: now - 24 * hour,
      end: now - 20 * hour,
      type: 'quiet' as const,
      hurstExponent: 0.45,
      volatility: 0.008,
    },
    {
      start: now - 20 * hour,
      end: now - 16 * hour,
      type: 'trending' as const,
      hurstExponent: 0.72,
      volatility: 0.025,
    },
    {
      start: now - 16 * hour,
      end: now - 12 * hour,
      type: 'volatile' as const,
      hurstExponent: 0.51,
      volatility: 0.042,
    },
    {
      start: now - 12 * hour,
      end: now - 8 * hour,
      type: 'ranging' as const,
      hurstExponent: 0.28,
      volatility: 0.015,
    },
    {
      start: now - 8 * hour,
      end: now - 4 * hour,
      type: 'trending' as const,
      hurstExponent: 0.68,
      volatility: 0.022,
    },
    {
      start: now - 4 * hour,
      end: now,
      type: 'volatile' as const,
      hurstExponent: 0.55,
      volatility: 0.038,
    },
  ];
};

export default function AnalysisLabPage() {
  const [metricData, setMetricData] = useState(() => generateMockMetricData());
  const [flowData, setFlowData] = useState(() => generateMockFlowData());
  const [vpin, setVpin] = useState(0.45);
  const [historicalVpin, setHistoricalVpin] = useState(() =>
    Array.from({ length: 24 }, () => 0.3 + Math.random() * 0.4)
  );
  const [regimes, setRegimes] = useState(() => generateMockRegimes());
  const [selectedExchange, setSelectedExchange] = useState('All Exchanges');
  const [autoRefresh, setAutoRefresh] = useState(true);

  // Simulate real-time updates
  useEffect(() => {
    if (!autoRefresh) return;

    const interval = setInterval(() => {
      // Update metrics
      setMetricData(prev => {
        const newPoint = {
          timestamp: Date.now(),
          spread: 2 + Math.random() * 3,
          kyle_lambda: 0.001 + Math.random() * 0.002,
          vpin: 0.3 + Math.random() * 0.4,
          realized_volatility: 0.015 + Math.random() * 0.03,
          order_flow_imbalance: Math.random() * 0.6 - 0.3,
          depth_imbalance: Math.random() * 0.4 - 0.2,
          amihud_illiquidity: Math.random() * 0.00001,
          roll_spread: 1.5 + Math.random() * 2
        };
        return [...prev.slice(1), newPoint];
      });

      // Update VPIN
      const newVpin = 0.3 + Math.random() * 0.4;
      setVpin(newVpin);
      setHistoricalVpin(prev => [...prev.slice(1), newVpin]);

      // Update flow data
      setFlowData(prev => {
        const newPoints = Array.from({ length: 5 }, () => ({
          timestamp: Date.now(),
          priceLevel: 45000 + Math.random() * 1000 - 500,
          netFlow: Math.random() * 2 - 1,
          buyVolume: Math.random() * 100,
          sellVolume: Math.random() * 100
        }));
        return [...prev.slice(5), ...newPoints];
      });
    }, 5000);

    return () => clearInterval(interval);
  }, [autoRefresh]);

  return (
    <div className="p-4 bg-zinc-950 min-h-screen">
      {/* Header */}
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <BarChart3 className="w-5 h-5 text-blue-500" />
            <h1 className="text-xl font-bold text-white">Analysis Lab</h1>
          </div>

          <select
            value={selectedExchange}
            onChange={(e) => setSelectedExchange(e.target.value)}
            className="bg-zinc-900 border border-zinc-800 rounded-lg px-4 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
          >
            <option value="All Exchanges">All Exchanges</option>
            <option value="Binance">Binance</option>
            <option value="Coinbase">Coinbase</option>
            <option value="Kraken">Kraken</option>
          </select>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => setAutoRefresh(!autoRefresh)}
            className={`
              flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors
              ${autoRefresh
                ? 'bg-green-600/20 text-green-400 border border-green-600'
                : 'bg-zinc-900 text-zinc-400 border border-zinc-800 hover:border-zinc-700'
              }
            `}
          >
            <RefreshCw className={`w-4 h-4 ${autoRefresh ? 'animate-spin' : ''}`} />
            {autoRefresh ? 'Auto-Refresh On' : 'Auto-Refresh Off'}
          </button>

          <button className="flex items-center gap-2 px-3 py-2 bg-zinc-900 text-zinc-400 rounded-lg text-sm hover:text-white transition-colors border border-zinc-800">
            <Download className="w-4 h-4" />
            Export Data
          </button>

          <button className="p-2 text-zinc-400 hover:text-white transition-colors">
            <Settings className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* Main Grid */}
      <div className="grid grid-cols-12 gap-4">
        {/* Left Column - Metrics & Toxicity */}
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          className="col-span-12 lg:col-span-8 space-y-4"
        >
          {/* Metric Timeseries */}
          <MetricTimeseries
            data={metricData}
            selectedMetrics={['spread', 'vpin', 'order_flow_imbalance']}
          />

          {/* Flow Heatmap */}
          <div className="bg-zinc-900 rounded-lg border border-zinc-800 p-4">
            <h3 className="text-sm font-semibold text-white mb-3">Order Flow Heatmap</h3>
            <FlowHeatmap data={flowData} height={400} />
          </div>
        </motion.div>

        {/* Right Column - Toxicity & Regime */}
        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.1 }}
          className="col-span-12 lg:col-span-4 space-y-4"
        >
          {/* Toxicity Gauge */}
          <ToxicityGauge
            vpin={vpin}
            historicalVpin={historicalVpin}
            width={350}
            height={200}
          />

          {/* Regime Timeline */}
          <RegimeTimeline
            periods={regimes}
            currentRegime={regimes[regimes.length - 1]}
          />

          {/* Cross-Exchange Correlation */}
          <div className="bg-zinc-900 rounded-lg border border-zinc-800 p-4">
            <h3 className="text-sm font-semibold text-white mb-3">Cross-Exchange Correlation</h3>

            <div className="space-y-3">
              {[
                { pair: 'Binance-Coinbase', correlation: 0.982, lag: '12ms' },
                { pair: 'Binance-Kraken', correlation: 0.965, lag: '45ms' },
                { pair: 'Coinbase-Kraken', correlation: 0.958, lag: '32ms' },
                { pair: 'Binance-Bybit', correlation: 0.978, lag: '18ms' },
              ].map((item, index) => (
                <motion.div
                  key={item.pair}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.05 }}
                  className="flex items-center justify-between"
                >
                  <span className="text-xs text-zinc-400">{item.pair}</span>
                  <div className="flex items-center gap-3">
                    <div className="flex items-center gap-1">
                      <span className="text-xs text-zinc-600">ρ:</span>
                      <span className={`text-xs font-mono ${
                        item.correlation > 0.97 ? 'text-green-400' : 'text-yellow-400'
                      }`}>
                        {item.correlation.toFixed(3)}
                      </span>
                    </div>
                    <div className="flex items-center gap-1">
                      <span className="text-xs text-zinc-600">lag:</span>
                      <span className="text-xs font-mono text-zinc-300">{item.lag}</span>
                    </div>
                  </div>
                </motion.div>
              ))}
            </div>

            <div className="mt-3 pt-3 border-t border-zinc-800">
              <p className="text-xs text-zinc-500">
                Binance leads price discovery with lowest latency
              </p>
            </div>
          </div>

          {/* Volume Profile */}
          <div className="bg-zinc-900 rounded-lg border border-zinc-800 p-4">
            <h3 className="text-sm font-semibold text-white mb-3">Volume Profile</h3>

            <div className="space-y-2">
              {[
                { price: 45800, volume: 1250, poc: true },
                { price: 45700, volume: 890, poc: false },
                { price: 45600, volume: 2100, poc: false },
                { price: 45500, volume: 3200, poc: false },
                { price: 45400, volume: 1800, poc: false },
                { price: 45300, volume: 950, poc: false },
              ].map((level, index) => (
                <div key={level.price} className="flex items-center gap-2">
                  <span className={`text-xs font-mono w-16 ${
                    level.poc ? 'text-yellow-400' : 'text-zinc-400'
                  }`}>
                    ${level.price}
                  </span>
                  <div className="flex-1 h-4 bg-zinc-950 rounded overflow-hidden">
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${(level.volume / 3200) * 100}%` }}
                      transition={{ delay: index * 0.05 }}
                      className={`h-full ${
                        level.poc ? 'bg-yellow-500' : 'bg-blue-500'
                      }`}
                      style={{ opacity: 0.7 }}
                    />
                  </div>
                  <span className="text-xs text-zinc-600 w-12 text-right">
                    {(level.volume / 1000).toFixed(1)}K
                  </span>
                </div>
              ))}
            </div>

            <div className="mt-3 pt-3 border-t border-zinc-800 flex justify-between text-xs">
              <span className="text-zinc-500">Point of Control</span>
              <span className="text-yellow-400 font-mono">$45,800</span>
            </div>
          </div>
        </motion.div>
      </div>
    </div>
  );
}