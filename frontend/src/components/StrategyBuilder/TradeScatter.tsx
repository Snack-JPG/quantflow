'use client';

import React, { useEffect, useRef } from 'react';
import * as d3 from 'd3';
import { motion } from 'framer-motion';
import { ScatterChart } from 'lucide-react';

interface Trade {
  entryTime: number;
  exitTime: number;
  entryPrice: number;
  exitPrice: number;
  pnl: number;
  side: 'long' | 'short';
}

interface TradeScatterProps {
  trades: Trade[];
  height?: number;
}

export function TradeScatter({ trades, height = 400 }: TradeScatterProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!svgRef.current || !containerRef.current || trades.length === 0) return;

    const width = containerRef.current.clientWidth;
    const margin = { top: 20, right: 60, bottom: 40, left: 60 };
    const innerWidth = width - margin.left - margin.right;
    const innerHeight = height - margin.top - margin.bottom;

    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();

    const g = svg.append('g')
      .attr('transform', `translate(${margin.left},${margin.top})`);

    // Calculate duration in hours
    const tradesWithDuration = trades.map(t => ({
      ...t,
      duration: (t.exitTime - t.entryTime) / (1000 * 60 * 60), // hours
    }));

    // Scales
    const xScale = d3.scaleLinear()
      .domain([0, d3.max(tradesWithDuration, d => d.duration) || 1])
      .range([0, innerWidth]);

    const yScale = d3.scaleLinear()
      .domain(d3.extent(trades, d => d.pnl) as [number, number])
      .range([innerHeight, 0]);

    const colorScale = d3.scaleOrdinal<'long' | 'short', string>()
      .domain(['long', 'short'])
      .range(['#10b981', '#ef4444']);

    const sizeScale = d3.scaleSqrt()
      .domain([0, d3.max(trades, d => Math.abs(d.pnl)) || 1])
      .range([3, 15]);

    // Add grid
    g.append('g')
      .attr('class', 'grid')
      .attr('transform', `translate(0,${innerHeight})`)
      .call(d3.axisBottom(xScale)
        .tickSize(-innerHeight)
        .tickFormat(() => '')
      )
      .style('stroke-dasharray', '3,3')
      .style('opacity', 0.3);

    g.append('g')
      .attr('class', 'grid')
      .call(d3.axisLeft(yScale)
        .tickSize(-innerWidth)
        .tickFormat(() => '')
      )
      .style('stroke-dasharray', '3,3')
      .style('opacity', 0.3);

    // Add zero line
    g.append('line')
      .attr('x1', 0)
      .attr('x2', innerWidth)
      .attr('y1', yScale(0))
      .attr('y2', yScale(0))
      .attr('stroke', '#fff')
      .attr('stroke-width', 1)
      .attr('opacity', 0.5);

    // Add scatter points
    g.selectAll('.trade')
      .data(tradesWithDuration)
      .enter()
      .append('circle')
      .attr('class', 'trade')
      .attr('cx', d => xScale(d.duration))
      .attr('cy', d => yScale(d.pnl))
      .attr('r', d => sizeScale(Math.abs(d.pnl)))
      .attr('fill', d => colorScale(d.side))
      .attr('opacity', 0.7)
      .attr('stroke', d => colorScale(d.side))
      .attr('stroke-width', 1)
      .on('mouseenter', function(event, d) {
        d3.select(this)
          .transition()
          .duration(200)
          .attr('opacity', 1)
          .attr('r', sizeScale(Math.abs(d.pnl)) * 1.5);
      })
      .on('mouseleave', function(event, d) {
        d3.select(this)
          .transition()
          .duration(200)
          .attr('opacity', 0.7)
          .attr('r', sizeScale(Math.abs(d.pnl)));
      });

    // Axes
    const xAxis = d3.axisBottom(xScale)
      .ticks(10)
      .tickFormat(d => `${d}h`);

    const yAxis = d3.axisLeft(yScale)
      .ticks(10)
      .tickFormat(d => `$${d}`);

    g.append('g')
      .attr('transform', `translate(0,${innerHeight})`)
      .call(xAxis)
      .selectAll('text')
      .attr('fill', '#9ca3af');

    g.append('g')
      .call(yAxis)
      .selectAll('text')
      .attr('fill', '#9ca3af');

    // Labels
    g.append('text')
      .attr('transform', 'rotate(-90)')
      .attr('y', 0 - margin.left + 15)
      .attr('x', 0 - innerHeight / 2)
      .attr('text-anchor', 'middle')
      .attr('fill', '#9ca3af')
      .attr('font-size', '12px')
      .text('PnL ($)');

    g.append('text')
      .attr('x', innerWidth / 2)
      .attr('y', innerHeight + margin.bottom)
      .attr('text-anchor', 'middle')
      .attr('fill', '#9ca3af')
      .attr('font-size', '12px')
      .text('Trade Duration');

    // Add quadrant labels
    const quadrants = [
      { x: innerWidth - 50, y: 20, text: 'Profitable Longs', color: '#10b981' },
      { x: innerWidth - 50, y: innerHeight - 20, text: 'Loss Longs', color: '#10b981' },
      { x: 50, y: 20, text: 'Quick Wins', color: '#fbbf24' },
      { x: 50, y: innerHeight - 20, text: 'Quick Losses', color: '#ef4444' },
    ];

    quadrants.forEach(q => {
      g.append('text')
        .attr('x', q.x)
        .attr('y', q.y)
        .attr('text-anchor', 'middle')
        .attr('fill', q.color)
        .attr('font-size', '10px')
        .attr('opacity', 0.5)
        .text(q.text);
    });

  }, [trades, height]);

  const stats = {
    totalTrades: trades.length,
    winners: trades.filter(t => t.pnl > 0).length,
    losers: trades.filter(t => t.pnl < 0).length,
    avgWin: trades.filter(t => t.pnl > 0).reduce((sum, t) => sum + t.pnl, 0) / Math.max(1, trades.filter(t => t.pnl > 0).length),
    avgLoss: trades.filter(t => t.pnl < 0).reduce((sum, t) => sum + Math.abs(t.pnl), 0) / Math.max(1, trades.filter(t => t.pnl < 0).length),
    longTrades: trades.filter(t => t.side === 'long').length,
    shortTrades: trades.filter(t => t.side === 'short').length,
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-zinc-900 rounded-lg border border-zinc-800 p-4"
    >
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <ScatterChart className="w-4 h-4 text-blue-500" />
          <h3 className="text-sm font-semibold text-white">Trade Scatter Plot</h3>
        </div>
        <div className="flex items-center gap-4 text-xs">
          <div className="flex items-center gap-1">
            <div className="w-3 h-3 bg-green-500 rounded-full" />
            <span className="text-zinc-400">Long</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-3 h-3 bg-red-500 rounded-full" />
            <span className="text-zinc-400">Short</span>
          </div>
        </div>
      </div>

      <div ref={containerRef} className="w-full">
        <svg ref={svgRef} width="100%" height={height} />
      </div>

      <div className="mt-4 grid grid-cols-4 gap-3">
        <div className="bg-zinc-950 rounded-lg p-2">
          <div className="text-[10px] text-zinc-500 mb-1">Win Rate</div>
          <div className="text-xs font-mono text-green-400">
            {((stats.winners / stats.totalTrades) * 100).toFixed(1)}%
          </div>
        </div>
        <div className="bg-zinc-950 rounded-lg p-2">
          <div className="text-[10px] text-zinc-500 mb-1">Avg Win</div>
          <div className="text-xs font-mono text-green-400">
            ${stats.avgWin.toFixed(2)}
          </div>
        </div>
        <div className="bg-zinc-950 rounded-lg p-2">
          <div className="text-[10px] text-zinc-500 mb-1">Avg Loss</div>
          <div className="text-xs font-mono text-red-400">
            -${stats.avgLoss.toFixed(2)}
          </div>
        </div>
        <div className="bg-zinc-950 rounded-lg p-2">
          <div className="text-[10px] text-zinc-500 mb-1">Profit Factor</div>
          <div className="text-xs font-mono text-white">
            {(stats.avgWin / stats.avgLoss).toFixed(2)}
          </div>
        </div>
      </div>
    </motion.div>
  );
}
