'use client';

import React, { useEffect, useRef } from 'react';
import { createChart, IChartApi, ISeriesApi, ColorType } from 'lightweight-charts';
import { motion } from 'framer-motion';

interface DepthChartProps {
  bids: Array<{ price: number; quantity: number; total: number }>;
  asks: Array<{ price: number; quantity: number; total: number }>;
  height?: number;
}

export function DepthChart({ bids, asks, height = 400 }: DepthChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const bidSeriesRef = useRef<ISeriesApi<'Area'> | null>(null);
  const askSeriesRef = useRef<ISeriesApi<'Area'> | null>(null);

  useEffect(() => {
    if (!chartContainerRef.current) return;

    // Create chart
    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: '#18181b' },
        textColor: '#9ca3af',
      },
      grid: {
        vertLines: { color: '#27272a' },
        horzLines: { color: '#27272a' },
      },
      width: chartContainerRef.current.clientWidth,
      height: height,
      rightPriceScale: {
        borderColor: '#27272a',
      },
      timeScale: {
        borderColor: '#27272a',
        timeVisible: false,
        secondsVisible: false,
      },
      crosshair: {
        horzLine: {
          visible: true,
          labelVisible: true,
        },
        vertLine: {
          visible: true,
          labelVisible: true,
        },
      },
    });

    // Create bid area series (green)
    const bidSeries = chart.addAreaSeries({
      topColor: 'rgba(16, 185, 129, 0.4)',
      bottomColor: 'rgba(16, 185, 129, 0.05)',
      lineColor: '#10b981',
      lineWidth: 2,
      crosshairMarkerVisible: true,
      priceScaleId: 'left',
    });

    // Create ask area series (red)
    const askSeries = chart.addAreaSeries({
      topColor: 'rgba(239, 68, 68, 0.4)',
      bottomColor: 'rgba(239, 68, 68, 0.05)',
      lineColor: '#ef4444',
      lineWidth: 2,
      crosshairMarkerVisible: true,
    });

    chart.priceScale('left').applyOptions({
      borderColor: '#27272a',
    });

    chartRef.current = chart;
    bidSeriesRef.current = bidSeries;
    askSeriesRef.current = askSeries;

    // Handle resize
    const handleResize = () => {
      if (chartContainerRef.current && chart) {
        chart.applyOptions({
          width: chartContainerRef.current.clientWidth,
        });
      }
    };

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      chart.remove();
    };
  }, [height]);

  useEffect(() => {
    if (!bidSeriesRef.current || !askSeriesRef.current) return;

    // Prepare bid data (sorted descending by price)
    const bidData = [...bids]
      .sort((a, b) => b.price - a.price)
      .map(level => ({
        time: level.price,
        value: level.total,
      }));

    // Prepare ask data (sorted ascending by price)
    const askData = [...asks]
      .sort((a, b) => a.price - b.price)
      .map(level => ({
        time: level.price,
        value: level.total,
      }));

    // Update series
    if (bidData.length > 0) {
      bidSeriesRef.current.setData(bidData);
    }
    if (askData.length > 0) {
      askSeriesRef.current.setData(askData);
    }

    // Fit content
    if (chartRef.current) {
      chartRef.current.timeScale().fitContent();
    }
  }, [bids, asks]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="bg-zinc-900 rounded-lg border border-zinc-800 p-4"
    >
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-zinc-100">Market Depth</h3>
        <div className="flex items-center gap-4 text-xs">
          <div className="flex items-center gap-1">
            <div className="w-3 h-3 bg-green-500 rounded-sm" />
            <span className="text-zinc-400">Bids</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-3 h-3 bg-red-500 rounded-sm" />
            <span className="text-zinc-400">Asks</span>
          </div>
        </div>
      </div>
      <div ref={chartContainerRef} className="w-full" />
    </motion.div>
  );
}