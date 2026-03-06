'use client';

import React, { useMemo } from 'react';
import { motion } from 'framer-motion';
import { TrendingUp, TrendingDown, Activity, AlertTriangle, Zap, BarChart } from 'lucide-react';

interface Metric {
  name: string;
  value: number | string;
  change?: number;
  unit?: string;
  status?: 'normal' | 'warning' | 'critical';
  description?: string;
}

interface MetricsPanelProps {
  metrics?: {
    spread?: number;
    vwap?: number;
    imbalance?: number;
    kyle_lambda?: number;
    vpin?: number;
    hurst?: number;
    regime?: string;
    microPrice?: number;
    effectiveSpread?: number;
    realizeSpreadvol?: number;
    orderFlowToxicity?: number;
    priceImpact?: number;
  };
}

export function MetricsPanel({ metrics }: MetricsPanelProps) {
  const formattedMetrics = useMemo(() => {
    if (!metrics) return [];

    const metricsArray: Metric[] = [];

    // Core Market Metrics
    if (metrics.spread !== undefined) {
      metricsArray.push({
        name: 'Spread',
        value: metrics.spread.toFixed(2),
        unit: 'bps',
        status: metrics.spread > 10 ? 'warning' : 'normal',
        description: 'Bid-ask spread in basis points',
      });
    }

    if (metrics.vwap !== undefined) {
      metricsArray.push({
        name: 'VWAP',
        value: metrics.vwap.toFixed(2),
        unit: '$',
        description: 'Volume-weighted average price',
      });
    }

    if (metrics.imbalance !== undefined) {
      const imbalanceValue = metrics.imbalance * 100;
      metricsArray.push({
        name: 'Order Imbalance',
        value: imbalanceValue.toFixed(1),
        unit: '%',
        status: Math.abs(imbalanceValue) > 30 ? 'warning' : 'normal',
        description: 'Order book imbalance ratio',
      });
    }

    // Advanced Microstructure Metrics
    if (metrics.kyle_lambda !== undefined) {
      metricsArray.push({
        name: "Kyle's Lambda",
        value: metrics.kyle_lambda.toFixed(4),
        status: metrics.kyle_lambda > 0.01 ? 'warning' : 'normal',
        description: 'Price impact coefficient',
      });
    }

    if (metrics.vpin !== undefined) {
      metricsArray.push({
        name: 'VPIN',
        value: metrics.vpin.toFixed(3),
        status: metrics.vpin > 0.7 ? 'critical' : metrics.vpin > 0.5 ? 'warning' : 'normal',
        description: 'Volume-synchronized probability of informed trading',
      });
    }

    if (metrics.hurst !== undefined) {
      metricsArray.push({
        name: 'Hurst Exponent',
        value: metrics.hurst.toFixed(3),
        status: metrics.hurst > 0.6 ? 'warning' : metrics.hurst < 0.4 ? 'warning' : 'normal',
        description: 'Market regime indicator (0.5 = random walk)',
      });
    }

    if (metrics.regime) {
      metricsArray.push({
        name: 'Market Regime',
        value: metrics.regime,
        status: metrics.regime === 'volatile' ? 'warning' : 'normal',
        description: 'Current market state classification',
      });
    }

    if (metrics.orderFlowToxicity !== undefined) {
      metricsArray.push({
        name: 'Flow Toxicity',
        value: (metrics.orderFlowToxicity * 100).toFixed(1),
        unit: '%',
        status: metrics.orderFlowToxicity > 0.6 ? 'critical' : metrics.orderFlowToxicity > 0.4 ? 'warning' : 'normal',
        description: 'Probability of adverse selection',
      });
    }

    return metricsArray;
  }, [metrics]);

  const getStatusColor = (status?: string) => {
    switch (status) {
      case 'critical':
        return 'text-red-500 bg-red-500/10 border-red-500/20';
      case 'warning':
        return 'text-yellow-500 bg-yellow-500/10 border-yellow-500/20';
      default:
        return 'text-green-500 bg-green-500/10 border-green-500/20';
    }
  };

  const getStatusIcon = (status?: string) => {
    switch (status) {
      case 'critical':
        return <AlertTriangle className="w-4 h-4" />;
      case 'warning':
        return <Zap className="w-4 h-4" />;
      default:
        return <Activity className="w-4 h-4" />;
    }
  };

  return (
    <div className="bg-zinc-900 rounded-lg border border-zinc-800">
      <div className="p-4 border-b border-zinc-800">
        <div className="flex items-center gap-2">
          <BarChart className="w-4 h-4 text-blue-500" />
          <h3 className="text-sm font-semibold text-white">Real-Time Metrics</h3>
        </div>
      </div>

      <div className="p-4 space-y-3">
        {formattedMetrics.length > 0 ? (
          formattedMetrics.map((metric, index) => (
            <motion.div
              key={metric.name}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.05 }}
              className={`
                p-3 rounded-lg border transition-all duration-300
                ${getStatusColor(metric.status)}
              `}
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    {getStatusIcon(metric.status)}
                    <span className="text-xs font-medium text-zinc-300">
                      {metric.name}
                    </span>
                  </div>
                  <div className="mt-1 flex items-baseline gap-1">
                    <span className="text-lg font-mono font-semibold text-white">
                      {metric.value}
                    </span>
                    {metric.unit && (
                      <span className="text-xs text-zinc-500">{metric.unit}</span>
                    )}
                  </div>
                  {metric.description && (
                    <p className="mt-1 text-[10px] text-zinc-500">
                      {metric.description}
                    </p>
                  )}
                </div>
                {metric.change !== undefined && (
                  <div className="flex items-center gap-1">
                    {metric.change > 0 ? (
                      <TrendingUp className="w-3 h-3 text-green-500" />
                    ) : (
                      <TrendingDown className="w-3 h-3 text-red-500" />
                    )}
                    <span className={`text-xs ${metric.change > 0 ? 'text-green-500' : 'text-red-500'}`}>
                      {Math.abs(metric.change).toFixed(1)}%
                    </span>
                  </div>
                )}
              </div>
            </motion.div>
          ))
        ) : (
          <div className="text-center py-8 text-zinc-500">
            <Activity className="w-8 h-8 mx-auto mb-2 opacity-50" />
            <p className="text-sm">Waiting for metrics data...</p>
          </div>
        )}
      </div>

      {/* Legend */}
      <div className="px-4 pb-4">
        <div className="flex items-center gap-4 text-[10px] text-zinc-500">
          <div className="flex items-center gap-1">
            <div className="w-2 h-2 bg-green-500 rounded-full" />
            <span>Normal</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-2 h-2 bg-yellow-500 rounded-full" />
            <span>Warning</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-2 h-2 bg-red-500 rounded-full" />
            <span>Critical</span>
          </div>
        </div>
      </div>
    </div>
  );
}