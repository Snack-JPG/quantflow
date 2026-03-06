'use client';

import React from 'react';
import { motion } from 'framer-motion';
import { TrendingUp, TrendingDown, Activity, Zap } from 'lucide-react';

interface RegimePeriod {
  start: number;
  end: number;
  type: 'trending' | 'ranging' | 'volatile' | 'quiet';
  hurstExponent: number;
  volatility: number;
  description?: string;
}

interface RegimeTimelineProps {
  periods: RegimePeriod[];
  currentRegime: RegimePeriod;
  width?: number;
}

export function RegimeTimeline({ periods, currentRegime }: RegimeTimelineProps) {
  const getRegimeConfig = (type: RegimePeriod['type']) => {
    switch (type) {
      case 'trending':
        return {
          color: 'bg-blue-500',
          borderColor: 'border-blue-500',
          textColor: 'text-blue-400',
          bgColor: 'bg-blue-500/20',
          icon: TrendingUp,
          label: 'Trending',
          description: 'Strong directional movement (H > 0.6)'
        };
      case 'ranging':
        return {
          color: 'bg-purple-500',
          borderColor: 'border-purple-500',
          textColor: 'text-purple-400',
          bgColor: 'bg-purple-500/20',
          icon: Activity,
          label: 'Ranging',
          description: 'Mean-reverting behavior (H < 0.4)'
        };
      case 'volatile':
        return {
          color: 'bg-red-500',
          borderColor: 'border-red-500',
          textColor: 'text-red-400',
          bgColor: 'bg-red-500/20',
          icon: Zap,
          label: 'Volatile',
          description: 'High volatility regime (σ > 0.03)'
        };
      case 'quiet':
        return {
          color: 'bg-green-500',
          borderColor: 'border-green-500',
          textColor: 'text-green-400',
          bgColor: 'bg-green-500/20',
          icon: TrendingDown,
          label: 'Quiet',
          description: 'Low volatility consolidation (σ < 0.01)'
        };
    }
  };

  const formatDuration = (start: number, end: number) => {
    const duration = end - start;
    const hours = Math.floor(duration / (1000 * 60 * 60));
    const minutes = Math.floor((duration % (1000 * 60 * 60)) / (1000 * 60));

    if (hours > 0) {
      return `${hours}h ${minutes}m`;
    }
    return `${minutes}m`;
  };

  const formatTime = (timestamp: number) => {
    return new Date(timestamp).toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      hour12: false
    });
  };

  const currentConfig = getRegimeConfig(currentRegime.type);
  const CurrentIcon = currentConfig.icon;

  // Calculate timeline scale
  const now = Date.now();
  const timeRange = 24 * 60 * 60 * 1000; // 24 hours
  const startTime = now - timeRange;

  return (
    <div className="bg-zinc-900 rounded-lg border border-zinc-800 p-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-white">Market Regime Timeline</h3>
        <div className="flex items-center gap-2">
          <CurrentIcon className={`w-4 h-4 ${currentConfig.textColor}`} />
          <span className={`px-2 py-1 rounded text-xs font-medium ${currentConfig.bgColor} ${currentConfig.textColor}`}>
            Current: {currentConfig.label}
          </span>
        </div>
      </div>

      {/* Current Regime Details */}
      <div className={`mb-4 p-3 rounded-lg border ${currentConfig.borderColor} ${currentConfig.bgColor}/10`}>
        <div className="flex items-start justify-between">
          <div>
            <div className="text-xs text-zinc-500 mb-1">Active Since</div>
            <div className="text-sm font-mono text-white">
              {formatTime(currentRegime.start)}
            </div>
          </div>
          <div className="text-right">
            <div className="text-xs text-zinc-500 mb-1">Duration</div>
            <div className="text-sm font-mono text-white">
              {formatDuration(currentRegime.start, now)}
            </div>
          </div>
        </div>
        <div className="mt-2 grid grid-cols-2 gap-2">
          <div>
            <div className="text-xs text-zinc-600">Hurst Exponent</div>
            <div className="font-mono text-sm text-zinc-300">{currentRegime.hurstExponent.toFixed(3)}</div>
          </div>
          <div>
            <div className="text-xs text-zinc-600">Volatility</div>
            <div className="font-mono text-sm text-zinc-300">{(currentRegime.volatility * 100).toFixed(2)}%</div>
          </div>
        </div>
        <p className="text-xs text-zinc-400 mt-2">{currentConfig.description}</p>
      </div>

      {/* Timeline */}
      <div className="relative">
        {/* Time axis */}
        <div className="flex justify-between text-xs text-zinc-500 mb-2">
          <span>24h ago</span>
          <span>18h</span>
          <span>12h</span>
          <span>6h</span>
          <span>Now</span>
        </div>

        {/* Timeline bar */}
        <div className="relative h-12 bg-zinc-950 rounded-lg overflow-hidden">
          {periods.map((period, index) => {
            const config = getRegimeConfig(period.type);
            const startPercent = Math.max(0, ((period.start - startTime) / timeRange) * 100);
            const endPercent = Math.min(100, ((period.end - startTime) / timeRange) * 100);
            const width = endPercent - startPercent;

            if (width <= 0) return null;

            return (
              <motion.div
                key={index}
                initial={{ scaleX: 0 }}
                animate={{ scaleX: 1 }}
                transition={{ delay: index * 0.1 }}
                className={`absolute h-full ${config.color}`}
                style={{
                  left: `${startPercent}%`,
                  width: `${width}%`,
                  opacity: 0.8,
                  transformOrigin: 'left'
                }}
                title={`${config.label}: ${formatTime(period.start)} - ${formatTime(period.end)}`}
              />
            );
          })}

          {/* Current position indicator */}
          <div
            className="absolute top-0 bottom-0 w-0.5 bg-white animate-pulse"
            style={{ right: '0%' }}
          />
        </div>

        {/* Legend */}
        <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-2">
          {(['trending', 'ranging', 'volatile', 'quiet'] as const).map(type => {
            const config = getRegimeConfig(type);
            const Icon = config.icon;
            const count = periods.filter(p => p.type === type).length;

            return (
              <div key={type} className="flex items-center gap-2 text-xs">
                <div className={`w-3 h-3 rounded ${config.color}`} />
                <Icon className="w-3 h-3 text-zinc-500" />
                <span className="text-zinc-400">{config.label}</span>
                <span className="text-zinc-600">({count})</span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Statistics */}
      <div className="mt-4 pt-4 border-t border-zinc-800 grid grid-cols-3 gap-4 text-xs">
        <div>
          <div className="text-zinc-600">Regime Changes</div>
          <div className="font-mono text-white">{periods.length}</div>
        </div>
        <div>
          <div className="text-zinc-600">Avg Duration</div>
          <div className="font-mono text-white">
            {formatDuration(
              0,
              periods.reduce((acc, p) => acc + (p.end - p.start), 0) / periods.length
            )}
          </div>
        </div>
        <div>
          <div className="text-zinc-600">Dominant Regime</div>
          <div className="font-mono text-white">
            {(() => {
              const counts = periods.reduce((acc, p) => {
                const duration = p.end - p.start;
                acc[p.type] = (acc[p.type] || 0) + duration;
                return acc;
              }, {} as Record<string, number>);

              const dominant = Object.entries(counts).sort((a, b) => b[1] - a[1])[0];
              return getRegimeConfig(dominant[0] as RegimePeriod['type']).label;
            })()}
          </div>
        </div>
      </div>
    </div>
  );
}