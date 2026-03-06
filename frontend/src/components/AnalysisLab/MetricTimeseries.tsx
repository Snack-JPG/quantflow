'use client';

import React, { useState } from 'react';
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine,
  Brush
} from 'recharts';
import { motion } from 'framer-motion';

interface MetricData {
  timestamp: number;
  spread?: number;
  kyle_lambda?: number;
  vpin?: number;
  realized_volatility?: number;
  order_flow_imbalance?: number;
  depth_imbalance?: number;
  amihud_illiquidity?: number;
  roll_spread?: number;
}

interface MetricTimeseriesProps {
  data: MetricData[];
  selectedMetrics?: string[];
}

const metricConfig = {
  spread: {
    name: 'Bid-Ask Spread',
    color: '#3b82f6',
    unit: 'bps',
    format: (v: number) => `${v.toFixed(2)} bps`
  },
  kyle_lambda: {
    name: "Kyle's Lambda",
    color: '#8b5cf6',
    unit: 'λ',
    format: (v: number) => v.toFixed(4)
  },
  vpin: {
    name: 'VPIN (Toxicity)',
    color: '#ef4444',
    unit: '',
    format: (v: number) => v.toFixed(3)
  },
  realized_volatility: {
    name: 'Realized Volatility',
    color: '#f59e0b',
    unit: '%',
    format: (v: number) => `${(v * 100).toFixed(2)}%`
  },
  order_flow_imbalance: {
    name: 'Order Flow Imbalance',
    color: '#10b981',
    unit: '',
    format: (v: number) => v.toFixed(3)
  },
  depth_imbalance: {
    name: 'Depth Imbalance',
    color: '#06b6d4',
    unit: '',
    format: (v: number) => v.toFixed(3)
  },
  amihud_illiquidity: {
    name: 'Amihud Illiquidity',
    color: '#ec4899',
    unit: '',
    format: (v: number) => v.toExponential(2)
  },
  roll_spread: {
    name: 'Roll Spread',
    color: '#84cc16',
    unit: 'bps',
    format: (v: number) => `${v.toFixed(2)} bps`
  }
};

export function MetricTimeseries({ data, selectedMetrics = ['spread', 'vpin'] }: MetricTimeseriesProps) {
  const [activeMetrics, setActiveMetrics] = useState<string[]>(selectedMetrics);
  const [timeRange, setTimeRange] = useState<'1H' | '4H' | '12H' | '24H'>('4H');

  const toggleMetric = (metric: string) => {
    setActiveMetrics(prev =>
      prev.includes(metric)
        ? prev.filter(m => m !== metric)
        : [...prev, metric]
    );
  };

  const filterDataByTimeRange = (data: MetricData[]) => {
    const now = Date.now();
    const ranges = {
      '1H': 60 * 60 * 1000,
      '4H': 4 * 60 * 60 * 1000,
      '12H': 12 * 60 * 60 * 1000,
      '24H': 24 * 60 * 60 * 1000
    };
    const cutoff = now - ranges[timeRange];
    return data.filter(d => d.timestamp > cutoff);
  };

  const filteredData = filterDataByTimeRange(data);

  const formatTime = (timestamp: number) => {
    return new Date(timestamp).toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      hour12: false
    });
  };

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (!active || !payload) return null;

    return (
      <div className="bg-zinc-950 border border-zinc-800 rounded-lg p-3">
        <p className="text-xs text-zinc-400 mb-2">{formatTime(label)}</p>
        {payload.map((entry: any, index: number) => {
          const config = metricConfig[entry.dataKey as keyof typeof metricConfig];
          return (
            <div key={index} className="flex items-center gap-2 text-xs">
              <div
                className="w-2 h-2 rounded-full"
                style={{ backgroundColor: entry.color }}
              />
              <span className="text-zinc-400">{config.name}:</span>
              <span className="font-mono text-white">
                {config.format(entry.value)}
              </span>
            </div>
          );
        })}
      </div>
    );
  };

  return (
    <div className="bg-zinc-900 rounded-lg border border-zinc-800 p-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-white">Microstructure Metrics</h3>

        {/* Time Range Selector */}
        <div className="flex items-center gap-1 bg-zinc-950 rounded-lg p-1">
          {(['1H', '4H', '12H', '24H'] as const).map(range => (
            <button
              key={range}
              onClick={() => setTimeRange(range)}
              className={`
                px-3 py-1 rounded text-xs font-medium transition-colors
                ${timeRange === range
                  ? 'bg-blue-600 text-white'
                  : 'text-zinc-400 hover:text-white'
                }
              `}
            >
              {range}
            </button>
          ))}
        </div>
      </div>

      {/* Metric Toggles */}
      <div className="grid grid-cols-4 gap-2 mb-4">
        {Object.entries(metricConfig).map(([key, config]) => (
          <motion.button
            key={key}
            whileTap={{ scale: 0.95 }}
            onClick={() => toggleMetric(key)}
            className={`
              px-3 py-2 rounded-lg text-xs font-medium transition-all
              ${activeMetrics.includes(key)
                ? 'bg-zinc-800 text-white border-2'
                : 'bg-zinc-950 text-zinc-500 border-2 border-zinc-900 hover:border-zinc-700'
              }
            `}
            style={{
              borderColor: activeMetrics.includes(key) ? config.color : undefined
            }}
          >
            <div className="flex items-center gap-2">
              <div
                className="w-2 h-2 rounded-full"
                style={{ backgroundColor: config.color }}
              />
              <span>{config.name}</span>
            </div>
          </motion.button>
        ))}
      </div>

      {/* Chart */}
      <div className="h-[400px]">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={filteredData} margin={{ top: 5, right: 5, left: 5, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
            <XAxis
              dataKey="timestamp"
              tickFormatter={formatTime}
              stroke="#71717a"
              style={{ fontSize: '10px' }}
            />
            <YAxis
              stroke="#71717a"
              style={{ fontSize: '10px' }}
              domain={['auto', 'auto']}
            />
            <Tooltip content={<CustomTooltip />} />
            <Brush
              dataKey="timestamp"
              height={30}
              stroke="#3b82f6"
              fill="#1f2937"
              tickFormatter={formatTime}
            />

            {activeMetrics.map(metric => {
              const config = metricConfig[metric as keyof typeof metricConfig];
              return (
                <Line
                  key={metric}
                  type="monotone"
                  dataKey={metric}
                  stroke={config.color}
                  strokeWidth={2}
                  dot={false}
                  activeDot={{ r: 4 }}
                  name={config.name}
                />
              );
            })}

            {/* Reference lines for significant levels */}
            {activeMetrics.includes('vpin') && (
              <>
                <ReferenceLine y={0.7} stroke="#ef4444" strokeDasharray="5 5" />
                <ReferenceLine y={0.3} stroke="#10b981" strokeDasharray="5 5" />
              </>
            )}
            {activeMetrics.includes('order_flow_imbalance') && (
              <ReferenceLine y={0} stroke="#71717a" strokeDasharray="5 5" />
            )}
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Statistics */}
      <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-4">
        {activeMetrics.map(metric => {
          const config = metricConfig[metric as keyof typeof metricConfig];
          const values = filteredData
            .map(d => d[metric as keyof MetricData])
            .filter(v => v !== undefined) as number[];

          if (values.length === 0) return null;

          const current = values[values.length - 1];
          const avg = values.reduce((a, b) => a + b, 0) / values.length;
          const max = Math.max(...values);
          const min = Math.min(...values);

          return (
            <div key={metric} className="bg-zinc-950 rounded-lg p-3">
              <div className="text-xs text-zinc-500 mb-1">{config.name}</div>
              <div className="font-mono text-sm text-white mb-2">
                {config.format(current)}
              </div>
              <div className="grid grid-cols-3 gap-1 text-[10px]">
                <div>
                  <span className="text-zinc-600">Avg</span>
                  <div className="text-zinc-400">{config.format(avg)}</div>
                </div>
                <div>
                  <span className="text-zinc-600">Min</span>
                  <div className="text-zinc-400">{config.format(min)}</div>
                </div>
                <div>
                  <span className="text-zinc-600">Max</span>
                  <div className="text-zinc-400">{config.format(max)}</div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}