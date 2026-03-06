'use client';

import React, { useEffect, useRef, useState } from 'react';
import * as d3 from 'd3';
import { motion } from 'framer-motion';
import { BarChart3 } from 'lucide-react';

interface VolumeLevel {
  price: number;
  buyVolume: number;
  sellVolume: number;
  totalVolume: number;
  poc?: boolean; // Point of Control
  vah?: boolean; // Value Area High
  val?: boolean; // Value Area Low
}

interface VolumeProfileProps {
  data: VolumeLevel[];
  currentPrice?: number;
  height?: number;
  showValueArea?: boolean;
}

export function VolumeProfile({
  data,
  currentPrice = 45000,
  height = 600,
  showValueArea = true
}: VolumeProfileProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ width: 0, height });
  const [hoveredLevel, setHoveredLevel] = useState<VolumeLevel | null>(null);

  useEffect(() => {
    const updateDimensions = () => {
      if (containerRef.current) {
        setDimensions({
          width: containerRef.current.clientWidth,
          height
        });
      }
    };

    updateDimensions();
    window.addEventListener('resize', updateDimensions);
    return () => window.removeEventListener('resize', updateDimensions);
  }, [height]);

  useEffect(() => {
    if (!svgRef.current || dimensions.width === 0 || data.length === 0) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();

    const margin = { top: 20, right: 60, bottom: 40, left: 80 };
    const width = dimensions.width - margin.left - margin.right;
    const chartHeight = dimensions.height - margin.top - margin.bottom;

    const g = svg.append('g')
      .attr('transform', `translate(${margin.left},${margin.top})`);

    // Find POC (Point of Control - highest volume price)
    const poc = data.reduce((prev, current) =>
      prev.totalVolume > current.totalVolume ? prev : current
    );

    // Calculate Value Area (70% of total volume around POC)
    const totalVolume = data.reduce((sum, d) => sum + d.totalVolume, 0);
    const targetVolume = totalVolume * 0.7;

    const valueAreaData = [poc];
    let accumulatedVolume = poc.totalVolume;
    const pocIndex = data.findIndex(d => d.price === poc.price);
    let upperIndex = pocIndex + 1;
    let lowerIndex = pocIndex - 1;

    while (accumulatedVolume < targetVolume && (upperIndex < data.length || lowerIndex >= 0)) {
      const upperVol = upperIndex < data.length ? data[upperIndex].totalVolume : 0;
      const lowerVol = lowerIndex >= 0 ? data[lowerIndex].totalVolume : 0;

      if (upperVol > lowerVol && upperIndex < data.length) {
        valueAreaData.push(data[upperIndex]);
        accumulatedVolume += upperVol;
        upperIndex++;
      } else if (lowerIndex >= 0) {
        valueAreaData.unshift(data[lowerIndex]);
        accumulatedVolume += lowerVol;
        lowerIndex--;
      } else if (upperIndex < data.length) {
        valueAreaData.push(data[upperIndex]);
        accumulatedVolume += upperVol;
        upperIndex++;
      } else {
        break;
      }
    }

    const vah = Math.max(...valueAreaData.map(d => d.price));
    const val = Math.min(...valueAreaData.map(d => d.price));

    // Scales
    const priceScale = d3.scaleLinear()
      .domain(d3.extent(data, d => d.price) as [number, number])
      .range([chartHeight, 0]);

    const maxVolume = d3.max(data, d => d.totalVolume) || 1;
    const volumeScale = d3.scaleLinear()
      .domain([0, maxVolume])
      .range([0, width * 0.8]);

    // Background gradient
    const gradient = svg.append('defs')
      .append('linearGradient')
      .attr('id', 'volume-gradient')
      .attr('x1', '0%')
      .attr('x2', '100%');

    gradient.append('stop')
      .attr('offset', '0%')
      .attr('stop-color', '#10b981')
      .attr('stop-opacity', 0.2);

    gradient.append('stop')
      .attr('offset', '50%')
      .attr('stop-color', '#3b82f6')
      .attr('stop-opacity', 0.2);

    gradient.append('stop')
      .attr('offset', '100%')
      .attr('stop-color', '#ef4444')
      .attr('stop-opacity', 0.2);

    // Value Area background
    if (showValueArea) {
      g.append('rect')
        .attr('x', 0)
        .attr('y', priceScale(vah))
        .attr('width', width)
        .attr('height', priceScale(val) - priceScale(vah))
        .attr('fill', '#3b82f6')
        .attr('opacity', 0.05);

      // VAH line
      g.append('line')
        .attr('x1', 0)
        .attr('x2', width)
        .attr('y1', priceScale(vah))
        .attr('y2', priceScale(vah))
        .attr('stroke', '#3b82f6')
        .attr('stroke-width', 1)
        .attr('stroke-dasharray', '5,5')
        .attr('opacity', 0.5);

      // VAL line
      g.append('line')
        .attr('x1', 0)
        .attr('x2', width)
        .attr('y1', priceScale(val))
        .attr('y2', priceScale(val))
        .attr('stroke', '#3b82f6')
        .attr('stroke-width', 1)
        .attr('stroke-dasharray', '5,5')
        .attr('opacity', 0.5);
    }

    // Volume bars
    const bars = g.selectAll('.volume-bar')
      .data(data)
      .enter()
      .append('g')
      .attr('class', 'volume-bar');

    // Buy volume (green)
    bars.append('rect')
      .attr('x', 0)
      .attr('y', d => priceScale(d.price) - 2)
      .attr('width', d => volumeScale(d.buyVolume))
      .attr('height', 4)
      .attr('fill', '#10b981')
      .attr('opacity', 0.7)
      .on('mouseenter', (event, d) => setHoveredLevel(d))
      .on('mouseleave', () => setHoveredLevel(null));

    // Sell volume (red)
    bars.append('rect')
      .attr('x', d => volumeScale(d.buyVolume))
      .attr('y', d => priceScale(d.price) - 2)
      .attr('width', d => volumeScale(d.sellVolume))
      .attr('height', 4)
      .attr('fill', '#ef4444')
      .attr('opacity', 0.7)
      .on('mouseenter', (event, d) => setHoveredLevel(d))
      .on('mouseleave', () => setHoveredLevel(null));

    // POC marker
    g.append('rect')
      .attr('x', 0)
      .attr('y', priceScale(poc.price) - 3)
      .attr('width', volumeScale(poc.totalVolume))
      .attr('height', 6)
      .attr('fill', '#fbbf24')
      .attr('opacity', 0.8);

    g.append('text')
      .attr('x', volumeScale(poc.totalVolume) + 5)
      .attr('y', priceScale(poc.price) + 3)
      .attr('fill', '#fbbf24')
      .attr('font-size', '10px')
      .attr('font-weight', 'bold')
      .text('POC');

    // Current price line
    if (currentPrice) {
      g.append('line')
        .attr('x1', 0)
        .attr('x2', width)
        .attr('y1', priceScale(currentPrice))
        .attr('y2', priceScale(currentPrice))
        .attr('stroke', '#fff')
        .attr('stroke-width', 2)
        .attr('stroke-dasharray', '10,5');

      g.append('text')
        .attr('x', width - 40)
        .attr('y', priceScale(currentPrice) - 5)
        .attr('fill', '#fff')
        .attr('font-size', '11px')
        .attr('font-weight', 'bold')
        .text('Current');
    }

    // Axes
    const yAxis = d3.axisLeft(priceScale)
      .ticks(15)
      .tickFormat(d3.format(',.0f'));

    const xAxis = d3.axisBottom(volumeScale)
      .ticks(5)
      .tickFormat(d3.format('.2s'));

    g.append('g')
      .attr('class', 'y-axis')
      .call(yAxis)
      .selectAll('text')
      .attr('fill', '#9ca3af');

    g.append('g')
      .attr('class', 'x-axis')
      .attr('transform', `translate(0,${chartHeight})`)
      .call(xAxis)
      .selectAll('text')
      .attr('fill', '#9ca3af');

    // Labels
    g.append('text')
      .attr('transform', 'rotate(-90)')
      .attr('y', 0 - margin.left + 20)
      .attr('x', 0 - chartHeight / 2)
      .attr('text-anchor', 'middle')
      .attr('fill', '#9ca3af')
      .attr('font-size', '12px')
      .text('Price');

    g.append('text')
      .attr('x', width / 2)
      .attr('y', chartHeight + margin.bottom)
      .attr('text-anchor', 'middle')
      .attr('fill', '#9ca3af')
      .attr('font-size', '12px')
      .text('Volume');

  }, [data, dimensions, currentPrice, showValueArea]);

  return (
    <div className="bg-zinc-900 rounded-lg border border-zinc-800 p-4">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <BarChart3 className="w-4 h-4 text-blue-500" />
          <h3 className="text-sm font-semibold text-white">Volume Profile</h3>
        </div>
        <div className="flex items-center gap-4 text-xs">
          <div className="flex items-center gap-1">
            <div className="w-3 h-3 bg-green-500 rounded-sm" />
            <span className="text-zinc-400">Buy Volume</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-3 h-3 bg-red-500 rounded-sm" />
            <span className="text-zinc-400">Sell Volume</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-3 h-3 bg-yellow-500 rounded-sm" />
            <span className="text-zinc-400">POC</span>
          </div>
        </div>
      </div>

      <div ref={containerRef} className="w-full relative">
        <svg
          ref={svgRef}
          width={dimensions.width}
          height={dimensions.height}
          className="bg-zinc-950 rounded"
        />

        {/* Hover tooltip */}
        {hoveredLevel && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="absolute top-4 right-4 bg-zinc-950 border border-zinc-800 rounded-lg p-3 z-10"
          >
            <div className="text-xs space-y-1">
              <div className="flex justify-between gap-4">
                <span className="text-zinc-500">Price:</span>
                <span className="font-mono text-white">${hoveredLevel.price.toFixed(2)}</span>
              </div>
              <div className="flex justify-between gap-4">
                <span className="text-zinc-500">Buy Vol:</span>
                <span className="font-mono text-green-400">
                  {hoveredLevel.buyVolume.toFixed(2)}
                </span>
              </div>
              <div className="flex justify-between gap-4">
                <span className="text-zinc-500">Sell Vol:</span>
                <span className="font-mono text-red-400">
                  {hoveredLevel.sellVolume.toFixed(2)}
                </span>
              </div>
              <div className="flex justify-between gap-4 pt-1 border-t border-zinc-800">
                <span className="text-zinc-500">Total:</span>
                <span className="font-mono text-white">
                  {hoveredLevel.totalVolume.toFixed(2)}
                </span>
              </div>
            </div>
          </motion.div>
        )}
      </div>

      {/* Legend */}
      <div className="mt-4 grid grid-cols-3 gap-4 text-xs">
        <div className="bg-zinc-950 rounded-lg p-2">
          <div className="text-zinc-500 mb-1">Value Area High</div>
          <div className="font-mono text-blue-400">VAH</div>
        </div>
        <div className="bg-zinc-950 rounded-lg p-2">
          <div className="text-zinc-500 mb-1">Point of Control</div>
          <div className="font-mono text-yellow-400">POC</div>
        </div>
        <div className="bg-zinc-950 rounded-lg p-2">
          <div className="text-zinc-500 mb-1">Value Area Low</div>
          <div className="font-mono text-blue-400">VAL</div>
        </div>
      </div>
    </div>
  );
}
