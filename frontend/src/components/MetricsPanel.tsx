/**
 * MetricsPanel - Display all microstructure analytics metrics
 */

import React from 'react';
import { AnalyticsData } from '@/types/market';

interface MetricsPanelProps {
  metrics: AnalyticsData | null;
}

export function MetricsPanel({ metrics }: MetricsPanelProps) {
  const formatNumber = (value: number | undefined | null, decimals: number = 4): string => {
    if (value === undefined || value === null) return '-';
    return value.toFixed(decimals);
  };

  const formatPercent = (value: number | undefined | null): string => {
    if (value === undefined || value === null) return '-';
    return `${(value * 100).toFixed(2)}%`;
  };

  const getSignalColor = (signal: string | undefined): string => {
    if (!signal) return 'text-muted-foreground';
    if (signal.includes('bullish') || signal.includes('buy')) return 'text-buy';
    if (signal.includes('bearish') || signal.includes('sell')) return 'text-sell';
    return 'text-yellow-500';
  };

  const getToxicityColor = (toxicity: string | undefined): string => {
    if (!toxicity) return 'text-muted-foreground';
    if (toxicity === 'low') return 'text-green-500';
    if (toxicity === 'moderate') return 'text-yellow-500';
    if (toxicity === 'high') return 'text-orange-500';
    if (toxicity === 'extreme') return 'text-red-500';
    return 'text-muted-foreground';
  };

  if (!metrics) {
    return (
      <div className="bg-card rounded-lg border border-border p-4">
        <h2 className="text-lg font-semibold mb-4">Microstructure Analytics</h2>
        <div className="text-center py-8 text-muted-foreground">
          Waiting for analytics data...
        </div>
      </div>
    );
  }

  return (
    <div className="bg-card rounded-lg border border-border p-4">
      <h2 className="text-lg font-semibold mb-4">Microstructure Analytics</h2>

      <div className="space-y-6">
        {/* VWAP Section */}
        <div>
          <h3 className="text-sm font-semibold text-muted-foreground mb-2">VWAP</h3>
          <div className="grid grid-cols-3 gap-2 text-sm">
            <div>
              <div className="text-xs text-muted-foreground">1m</div>
              <div className="font-mono">{formatNumber(metrics.vwap_1m, 2)}</div>
            </div>
            <div>
              <div className="text-xs text-muted-foreground">5m</div>
              <div className="font-mono">{formatNumber(metrics.vwap_5m, 2)}</div>
            </div>
            <div>
              <div className="text-xs text-muted-foreground">15m</div>
              <div className="font-mono">{formatNumber(metrics.vwap_15m, 2)}</div>
            </div>
          </div>
        </div>

        {/* Order Book Metrics */}
        <div>
          <h3 className="text-sm font-semibold text-muted-foreground mb-2">Order Book</h3>
          <div className="grid grid-cols-2 gap-2 text-sm">
            <div>
              <div className="text-xs text-muted-foreground">OBI</div>
              <div className="font-mono">{formatPercent(metrics.obi)}</div>
            </div>
            <div>
              <div className="text-xs text-muted-foreground">Weighted OBI</div>
              <div className="font-mono">{formatPercent(metrics.weighted_obi)}</div>
            </div>
            <div>
              <div className="text-xs text-muted-foreground">OFI</div>
              <div className="font-mono">{formatNumber(metrics.ofi, 2)}</div>
            </div>
            <div>
              <div className="text-xs text-muted-foreground">Signal</div>
              <div className={`font-semibold ${getSignalColor(metrics.obi_signal)}`}>
                {metrics.obi_signal || '-'}
              </div>
            </div>
          </div>
        </div>

        {/* Flow Toxicity */}
        <div>
          <h3 className="text-sm font-semibold text-muted-foreground mb-2">Flow Toxicity</h3>
          <div className="grid grid-cols-2 gap-2 text-sm">
            <div>
              <div className="text-xs text-muted-foreground">VPIN</div>
              <div className="font-mono">{formatPercent(metrics.vpin)}</div>
            </div>
            <div>
              <div className="text-xs text-muted-foreground">Toxicity</div>
              <div className={`font-semibold ${getToxicityColor(metrics.vpin_toxicity)}`}>
                {metrics.vpin_toxicity || '-'}
              </div>
            </div>
          </div>
        </div>

        {/* Price Impact */}
        <div>
          <h3 className="text-sm font-semibold text-muted-foreground mb-2">Price Impact</h3>
          <div className="grid grid-cols-2 gap-2 text-sm">
            <div>
              <div className="text-xs text-muted-foreground">Kyle&apos;s λ</div>
              <div className="font-mono">{formatNumber(metrics.kyles_lambda, 6)}</div>
            </div>
            <div>
              <div className="text-xs text-muted-foreground">Liquidity</div>
              <div className="font-semibold">{metrics.lambda_liquidity || '-'}</div>
            </div>
          </div>
        </div>

        {/* Liquidity Metrics */}
        <div>
          <h3 className="text-sm font-semibold text-muted-foreground mb-2">Liquidity</h3>
          <div className="grid grid-cols-2 gap-2 text-sm">
            <div>
              <div className="text-xs text-muted-foreground">Amihud</div>
              <div className="font-mono">{formatNumber(metrics.amihud, 8)}</div>
            </div>
            <div>
              <div className="text-xs text-muted-foreground">Roll Spread</div>
              <div className="font-mono">{formatNumber(metrics.roll_spread, 4)}</div>
            </div>
          </div>
        </div>

        {/* Volatility */}
        <div>
          <h3 className="text-sm font-semibold text-muted-foreground mb-2">Volatility</h3>
          <div className="grid grid-cols-2 gap-2 text-sm">
            <div>
              <div className="text-xs text-muted-foreground">Garman-Klass</div>
              <div className="font-mono">{formatNumber(metrics.garman_klass_vol, 4)}</div>
            </div>
            <div>
              <div className="text-xs text-muted-foreground">Parkinson</div>
              <div className="font-mono">{formatNumber(metrics.parkinson_vol, 4)}</div>
            </div>
            <div>
              <div className="text-xs text-muted-foreground">Term Structure</div>
              <div className="font-semibold">{metrics.vol_term_structure || '-'}</div>
            </div>
          </div>
        </div>

        {/* Market Regime */}
        <div>
          <h3 className="text-sm font-semibold text-muted-foreground mb-2">Market Regime</h3>
          <div className="grid grid-cols-2 gap-2 text-sm">
            <div>
              <div className="text-xs text-muted-foreground">Hurst H</div>
              <div className="font-mono">{formatNumber(metrics.hurst_exponent, 3)}</div>
            </div>
            <div>
              <div className="text-xs text-muted-foreground">Regime</div>
              <div className="font-semibold">{metrics.hurst_regime || '-'}</div>
            </div>
            <div className="col-span-2">
              <div className="text-xs text-muted-foreground">Strategy</div>
              <div className="font-semibold text-accent">{metrics.hurst_strategy || '-'}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
