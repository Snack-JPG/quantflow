/**
 * Depth Chart Component using TradingView Lightweight Charts
 */

'use client';

import React, { useEffect, useRef, useMemo } from 'react';
import { OrderBookData } from '@/types/market';

interface DepthChartProps {
  data: OrderBookData | null;
  height?: number;
}

export function DepthChart({ data, height = 400 }: DepthChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<any>(null);
  const seriesRef = useRef<any>(null);

  // Calculate cumulative depth data
  const depthData = useMemo(() => {
    if (!data || !data.bids.length || !data.asks.length) return null;

    // Process bids (cumulative from best to worst)
    const bidDepth: Array<{ price: number; quantity: number; cumulative: number }> = [];
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
    const askDepth: Array<{ price: number; quantity: number; cumulative: number }> = [];
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
    const initChart = async () => {
      if (!containerRef.current) return;

      // Dynamically import lightweight-charts
      const { createChart } = await import('lightweight-charts');

      // Create chart
      const chart = createChart(containerRef.current, {
        width: containerRef.current.clientWidth,
        height: height,
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

      // Create area series for bids
      const bidSeries = chart.addAreaSeries({
        lineColor: '#22c55e',
        topColor: '#22c55e',
        bottomColor: 'rgba(34, 197, 94, 0.1)',
        lineWidth: 2,
        priceScaleId: 'right',
      });

      // Create area series for asks
      const askSeries = chart.addAreaSeries({
        lineColor: '#ef4444',
        topColor: '#ef4444',
        bottomColor: 'rgba(239, 68, 68, 0.1)',
        lineWidth: 2,
        priceScaleId: 'right',
      });

      chartRef.current = chart;
      seriesRef.current = { bidSeries, askSeries };

      // Handle resize
      const handleResize = () => {
        if (containerRef.current && chart) {
          chart.applyOptions({
            width: containerRef.current.clientWidth,
          });
        }
      };

      window.addEventListener('resize', handleResize);

      return () => {
        window.removeEventListener('resize', handleResize);
        chart.remove();
      };
    };

    initChart();
  }, [height]);

  // Update chart data
  useEffect(() => {
    if (!seriesRef.current || !depthData) return;

    const { bidSeries, askSeries } = seriesRef.current;
    const { bidDepth, askDepth } = depthData;

    // Format bid data for chart
    const bidData = bidDepth.map((level) => ({
      time: level.price as any, // Using price as x-axis
      value: level.cumulative,
    }));

    // Format ask data for chart
    const askData = askDepth.map((level) => ({
      time: level.price as any, // Using price as x-axis
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