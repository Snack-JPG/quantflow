/**
 * Depth Chart Component using TradingView Lightweight Charts
 */

'use client';

import React, { useEffect, useRef, useMemo } from 'react';
import { OrderBookData } from '@/types/market';
import type { AreaData, IChartApi, ISeriesApi, UTCTimestamp } from 'lightweight-charts';

interface DepthChartProps {
  data: OrderBookData | null;
  height?: number;
}

interface DepthLevel {
  price: number;
  quantity: number;
  cumulative: number;
}

interface DepthSeriesRefs {
  bidSeries: ISeriesApi<'Area'>;
  askSeries: ISeriesApi<'Area'>;
}

export function DepthChart({ data, height = 400 }: DepthChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<DepthSeriesRefs | null>(null);

  // Calculate cumulative depth data
  const depthData = useMemo(() => {
    if (!data || !data.bids.length || !data.asks.length) return null;

    // Process bids (cumulative from best to worst)
    const bidDepth: DepthLevel[] = [];
    let bidCumulative = 0;

    for (let i = 0; i < Math.min(data.bids.length, 50); i++) {
      const [price, qty] = data.bids[i];
      bidCumulative += parseFloat(qty);
      bidDepth.push({
        price: parseFloat(price),
        quantity: parseFloat(qty),
        cumulative: bidCumulative,
      });
    }

    // Process asks (cumulative from best to worst)
    const askDepth: DepthLevel[] = [];
    let askCumulative = 0;

    for (let i = 0; i < Math.min(data.asks.length, 50); i++) {
      const [price, qty] = data.asks[i];
      askCumulative += parseFloat(qty);
      askDepth.push({
        price: parseFloat(price),
        quantity: parseFloat(qty),
        cumulative: askCumulative,
      });
    }

    return { bidDepth, askDepth };
  }, [data]);

  // Initialize chart
  useEffect(() => {
    let mounted = true;
    let handleResize: (() => void) | null = null;

    const initChart = async () => {
      if (!containerRef.current) return;

      const { createChart } = await import('lightweight-charts');
      if (!mounted || !containerRef.current) return;

      const chart = createChart(containerRef.current, {
        width: containerRef.current.clientWidth,
        height,
        layout: {
          background: { color: '#0a0a0a' },
          textColor: '#9ca3af',
        },
        grid: {
          vertLines: { color: '#262626' },
          horzLines: { color: '#262626' },
        },
        rightPriceScale: {
          borderColor: '#262626',
        },
        timeScale: {
          borderColor: '#262626',
          timeVisible: false,
        },
      });

      const bidSeries = chart.addAreaSeries({
        lineColor: '#22c55e',
        topColor: '#22c55e',
        bottomColor: 'rgba(34, 197, 94, 0.1)',
        lineWidth: 2,
        priceScaleId: 'right',
      });

      const askSeries = chart.addAreaSeries({
        lineColor: '#ef4444',
        topColor: '#ef4444',
        bottomColor: 'rgba(239, 68, 68, 0.1)',
        lineWidth: 2,
        priceScaleId: 'right',
      });

      chartRef.current = chart;
      seriesRef.current = { bidSeries, askSeries };

      handleResize = () => {
        if (containerRef.current && chartRef.current) {
          chartRef.current.applyOptions({
            width: containerRef.current.clientWidth,
          });
        }
      };

      window.addEventListener('resize', handleResize);
    };

    void initChart();

    return () => {
      mounted = false;
      if (handleResize) {
        window.removeEventListener('resize', handleResize);
      }
      if (chartRef.current) {
        chartRef.current.remove();
        chartRef.current = null;
      }
      seriesRef.current = null;
    };
  }, [height]);

  // Update chart data
  useEffect(() => {
    if (!seriesRef.current || !depthData) return;

    const { bidSeries, askSeries } = seriesRef.current;
    const { bidDepth, askDepth } = depthData;

    // Format bid data for chart
    const bidData: AreaData<UTCTimestamp>[] = bidDepth.map((level, index) => ({
      time: (Math.floor(level.price * 10) + index) as UTCTimestamp,
      value: level.cumulative,
    }));

    // Format ask data for chart
    const askData: AreaData<UTCTimestamp>[] = askDepth.map((level, index) => ({
      time: (Math.floor(level.price * 10) + index + 1_000_000) as UTCTimestamp,
      value: level.cumulative,
    }));

    // Update series
    bidSeries.setData(bidData);
    askSeries.setData(askData);

    // Auto-scale to fit
    if (chartRef.current) {
      chartRef.current.timeScale().fitContent();
    }
  }, [depthData]);

  return (
    <div className="bg-card rounded-lg border border-border">
      <div className="p-4 border-b border-border">
        <h2 className="text-lg font-semibold">Market Depth</h2>
      </div>
      <div ref={containerRef} className="w-full" style={{ height: `${height}px` }} />
    </div>
  );
}
