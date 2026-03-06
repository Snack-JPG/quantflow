'use client';

import React, { useEffect, useRef } from 'react';
import { createChart, IChartApi, ColorType } from 'lightweight-charts';
import { motion } from 'framer-motion';
import { TrendingUp } from 'lucide-react';

interface EquityCurveProps {
  data: Array<{ timestamp: number; value: number }>;
  height?: number;
}

export function EquityCurve({ data, height = 400 }: EquityCurveProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);

  useEffect(() => {
    if (!chartContainerRef.current || data.length === 0) return;

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
        timeVisible: true,
        secondsVisible: false,
      },
    });

    const lineSeries = chart.addLineSeries({
      color: '#10b981',
      lineWidth: 2,
      crosshairMarkerVisible: true,
      priceScaleId: 'right',
    });

    const chartData = data.map(d => ({
      time: Math.floor(d.timestamp / 1000) as any,
      value: d.value,
    }));

    lineSeries.setData(chartData);

    // Add baseline at initial value
    const baselineSeries = chart.addLineSeries({
      color: '#71717a',
      lineWidth: 1,
      lineStyle: 2,
      crosshairMarkerVisible: false,
    });

    baselineSeries.setData([
      { time: chartData[0].time, value: data[0].value },
      { time: chartData[chartData.length - 1].time, value: data[0].value },
    ]);

    chart.timeScale().fitContent();
    chartRef.current = chart;

    const handleResize = () => {
      if (chartContainerRef.current) {
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
  }, [data, height]);

  const calculateStats = () => {
    if (data.length === 0) return null;

    const initial = data[0].value;
    const final = data[data.length - 1].value;
    const returns = ((final - initial) / initial) * 100;

    const values = data.map(d => d.value);
    const peak = Math.max(...values);

    let maxDrawdown = 0;
    let currentPeak = values[0];

    for (const value of values) {
      if (value > currentPeak) {
        currentPeak = value;
      }
      const drawdown = (currentPeak - value) / currentPeak;
      if (drawdown > maxDrawdown) {
        maxDrawdown = drawdown;
      }
    }

    return {
      totalReturn: returns,
      finalValue: final,
      maxValue: peak,
      maxDrawdown: maxDrawdown * 100,
    };
  };

  const stats = calculateStats();

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-zinc-900 rounded-lg border border-zinc-800 p-4"
    >
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <TrendingUp className="w-4 h-4 text-green-500" />
          <h3 className="text-sm font-semibold text-white">Equity Curve</h3>
        </div>
        {stats && (
          <div className="flex items-center gap-4 text-xs">
            <div>
              <span className="text-zinc-500">Return:</span>
              <span className={`ml-1 font-mono ${stats.totalReturn >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                {stats.totalReturn >= 0 ? '+' : ''}{stats.totalReturn.toFixed(2)}%
              </span>
            </div>
            <div>
              <span className="text-zinc-500">Max DD:</span>
              <span className="ml-1 font-mono text-red-400">
                -{stats.maxDrawdown.toFixed(2)}%
              </span>
            </div>
          </div>
        )}
      </div>

      <div ref={chartContainerRef} className="w-full" />

      {stats && (
        <div className="mt-4 grid grid-cols-4 gap-3">
          <div className="bg-zinc-950 rounded-lg p-2">
            <div className="text-[10px] text-zinc-500 mb-1">Initial Value</div>
            <div className="text-xs font-mono text-white">
              ${data[0].value.toLocaleString()}
            </div>
          </div>
          <div className="bg-zinc-950 rounded-lg p-2">
            <div className="text-[10px] text-zinc-500 mb-1">Final Value</div>
            <div className="text-xs font-mono text-white">
              ${stats.finalValue.toLocaleString()}
            </div>
          </div>
          <div className="bg-zinc-950 rounded-lg p-2">
            <div className="text-[10px] text-zinc-500 mb-1">Peak Value</div>
            <div className="text-xs font-mono text-white">
              ${stats.maxValue.toLocaleString()}
            </div>
          </div>
          <div className="bg-zinc-950 rounded-lg p-2">
            <div className="text-[10px] text-zinc-500 mb-1">Total Return</div>
            <div className={`text-xs font-mono ${stats.totalReturn >= 0 ? 'text-green-400' : 'text-red-400'}`}>
              {stats.totalReturn >= 0 ? '+' : ''}{stats.totalReturn.toFixed(2)}%
            </div>
          </div>
        </div>
      )}
    </motion.div>
  );
}