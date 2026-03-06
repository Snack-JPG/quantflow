'use client';

import React, { useEffect, useRef, useState } from 'react';
import * as d3 from 'd3';

interface PriceLevel {
  price: number;
  quantity: number;
  total: number;
}

interface OrderBookHeatmapProps {
  bids: PriceLevel[];
  asks: PriceLevel[];
  trades?: Array<{
    price: number;
    quantity: number;
    timestamp: number;
    side: 'buy' | 'sell';
  }>;
  height?: number;
}

export function OrderBookHeatmap({ bids, asks, trades = [], height = 600 }: OrderBookHeatmapProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ width: 0, height });

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
    if (!svgRef.current || dimensions.width === 0) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();

    const margin = { top: 20, right: 60, bottom: 40, left: 80 };
    const width = dimensions.width - margin.left - margin.right;
    const height = dimensions.height - margin.top - margin.bottom;

    const g = svg.append('g')
      .attr('transform', `translate(${margin.left},${margin.top})`);

    // Combine and prepare data
    const allLevels = [
      ...asks.map(d => ({ ...d, side: 'ask' as const })),
      ...bids.map(d => ({ ...d, side: 'bid' as const }))
    ];

    if (allLevels.length === 0) return;

    const priceExtent = d3.extent(allLevels, d => d.price) as [number, number];
    const maxQuantity = d3.max(allLevels, d => d.quantity) || 1;

    // Scales
    const xScale = d3.scaleLinear()
      .domain([0, maxQuantity * 1.1])
      .range([0, width]);

    const yScale = d3.scaleLinear()
      .domain(priceExtent)
      .range([height, 0]);

    // Color scales
    const bidColorScale = d3.scaleSequential()
      .domain([0, maxQuantity])
      .interpolator(d3.interpolateGreens);

    const askColorScale = d3.scaleSequential()
      .domain([0, maxQuantity])
      .interpolator(d3.interpolateReds);

    // Draw heatmap bars
    const barHeight = Math.max(1, height / allLevels.length);

    // Bids
    g.selectAll('.bid-bar')
      .data(bids)
      .enter()
      .append('rect')
      .attr('class', 'bid-bar')
      .attr('x', d => width / 2 - xScale(d.quantity))
      .attr('y', d => yScale(d.price) - barHeight / 2)
      .attr('width', d => xScale(d.quantity))
      .attr('height', barHeight)
      .attr('fill', d => bidColorScale(d.quantity))
      .attr('opacity', 0.8);

    // Asks
    g.selectAll('.ask-bar')
      .data(asks)
      .enter()
      .append('rect')
      .attr('class', 'ask-bar')
      .attr('x', width / 2)
      .attr('y', d => yScale(d.price) - barHeight / 2)
      .attr('width', d => xScale(d.quantity))
      .attr('height', barHeight)
      .attr('fill', d => askColorScale(d.quantity))
      .attr('opacity', 0.8);

    // Mid price line
    const midPrice = (priceExtent[0] + priceExtent[1]) / 2;
    g.append('line')
      .attr('class', 'mid-price')
      .attr('x1', 0)
      .attr('x2', width)
      .attr('y1', yScale(midPrice))
      .attr('y2', yScale(midPrice))
      .attr('stroke', '#fff')
      .attr('stroke-width', 1)
      .attr('stroke-dasharray', '3,3')
      .attr('opacity', 0.5);

    // Trade markers
    const recentTrades = trades.slice(0, 100);
    g.selectAll('.trade-marker')
      .data(recentTrades)
      .enter()
      .append('circle')
      .attr('class', 'trade-marker')
      .attr('cx', width / 2)
      .attr('cy', d => yScale(d.price))
      .attr('r', d => Math.sqrt(d.quantity) * 2)
      .attr('fill', d => d.side === 'buy' ? '#10b981' : '#ef4444')
      .attr('opacity', 0.6)
      .transition()
      .duration(1000)
      .attr('r', d => Math.sqrt(d.quantity) * 4)
      .attr('opacity', 0)
      .remove();

    // Axes
    const xAxisBid = d3.axisBottom(xScale.copy().domain([maxQuantity * 1.1, 0]))
      .ticks(5)
      .tickFormat(d3.format('.2s'));

    const xAxisAsk = d3.axisTop(xScale)
      .ticks(5)
      .tickFormat(d3.format('.2s'));

    const yAxis = d3.axisLeft(yScale)
      .ticks(10)
      .tickFormat(d3.format(',.0f'));

    g.append('g')
      .attr('transform', `translate(0,${height})`)
      .attr('class', 'x-axis')
      .call(xAxisBid)
      .selectAll('text')
      .attr('fill', '#9ca3af');

    g.append('g')
      .attr('transform', `translate(${width / 2},${height})`)
      .attr('class', 'x-axis')
      .call(d3.axisBottom(xScale).ticks(5).tickFormat(d3.format('.2s')))
      .selectAll('text')
      .attr('fill', '#9ca3af');

    g.append('g')
      .attr('class', 'y-axis')
      .call(yAxis)
      .selectAll('text')
      .attr('fill', '#9ca3af');

    // Labels
    g.append('text')
      .attr('x', width / 4)
      .attr('y', -5)
      .attr('text-anchor', 'middle')
      .attr('fill', '#10b981')
      .attr('font-size', '12px')
      .text('BIDS');

    g.append('text')
      .attr('x', 3 * width / 4)
      .attr('y', -5)
      .attr('text-anchor', 'middle')
      .attr('fill', '#ef4444')
      .attr('font-size', '12px')
      .text('ASKS');

  }, [bids, asks, trades, dimensions]);

  return (
    <div ref={containerRef} className="w-full">
      <svg
        ref={svgRef}
        width={dimensions.width}
        height={dimensions.height}
        className="bg-zinc-900 rounded-lg"
      />
    </div>
  );
}