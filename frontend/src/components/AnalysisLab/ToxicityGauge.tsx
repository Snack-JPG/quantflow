'use client';

import React, { useEffect, useRef } from 'react';
import * as d3 from 'd3';
import { motion } from 'framer-motion';
import { AlertTriangle, TrendingUp, TrendingDown } from 'lucide-react';

interface ToxicityGaugeProps {
  vpin: number; // 0-1 scale
  historicalVpin?: number[];
  width?: number;
  height?: number;
}

export function ToxicityGauge({ vpin, historicalVpin = [], width = 300, height = 200 }: ToxicityGaugeProps) {
  const svgRef = useRef<SVGSVGElement>(null);

  const getToxicityLevel = (value: number) => {
    if (value < 0.3) return { level: 'Low', color: '#10b981', description: 'Normal market conditions' };
    if (value < 0.5) return { level: 'Moderate', color: '#eab308', description: 'Elevated information asymmetry' };
    if (value < 0.7) return { level: 'High', color: '#f97316', description: 'Significant toxic flow detected' };
    return { level: 'Critical', color: '#ef4444', description: 'Extreme market toxicity' };
  };

  const toxicityInfo = getToxicityLevel(vpin);

  useEffect(() => {
    if (!svgRef.current) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();

    const margin = { top: 20, right: 20, bottom: 40, left: 20 };
    const innerWidth = width - margin.left - margin.right;
    const innerHeight = height - margin.top - margin.bottom;

    const g = svg.append('g')
      .attr('transform', `translate(${margin.left + innerWidth / 2},${margin.top + innerHeight})`);

    type ArcDatum = { endAngle: number };

    // Create arc generator
    const arc = d3.arc<ArcDatum>()
      .innerRadius(innerHeight * 0.6)
      .outerRadius(innerHeight * 0.8)
      .startAngle(-Math.PI / 2)
      .cornerRadius(3);

    // Background arc
    g.append('path')
      .datum({ endAngle: Math.PI / 2 })
      .attr('d', d => arc(d) ?? '')
      .attr('fill', '#27272a');

    // Create gradient
    const gradientId = 'toxicity-gradient';
    const gradient = svg.append('defs')
      .append('linearGradient')
      .attr('id', gradientId)
      .attr('x1', '0%')
      .attr('x2', '100%');

    gradient.append('stop')
      .attr('offset', '0%')
      .attr('stop-color', '#10b981');

    gradient.append('stop')
      .attr('offset', '33%')
      .attr('stop-color', '#eab308');

    gradient.append('stop')
      .attr('offset', '66%')
      .attr('stop-color', '#f97316');

    gradient.append('stop')
      .attr('offset', '100%')
      .attr('stop-color', '#ef4444');

    // Value arc with animation
    const valueArc = g.append('path')
      .datum({ endAngle: -Math.PI / 2 })
      .attr('d', d => arc(d) ?? '')
      .attr('fill', toxicityInfo.color);

    valueArc.transition()
      .duration(1000)
      .ease(d3.easeElasticOut)
      .attrTween('d', function(d: ArcDatum) {
        const interpolate = d3.interpolate(d.endAngle, -Math.PI / 2 + Math.PI * vpin);
        return function(t: number) {
          d.endAngle = interpolate(t);
          return arc(d) ?? '';
        };
      });

    // Add tick marks
    const tickData = [0, 0.25, 0.5, 0.75, 1];
    const ticks = g.selectAll('.tick')
      .data(tickData)
      .enter()
      .append('g')
      .attr('class', 'tick')
      .attr('transform', d => `rotate(${d * 180 - 90})`);

    ticks.append('line')
      .attr('x1', innerHeight * 0.82)
      .attr('x2', innerHeight * 0.88)
      .attr('stroke', '#71717a')
      .attr('stroke-width', 1);

    ticks.append('text')
      .attr('x', innerHeight * 0.95)
      .attr('text-anchor', 'middle')
      .attr('dominant-baseline', 'central')
      .attr('fill', '#9ca3af')
      .attr('font-size', '10px')
      .attr('transform', d => `rotate(${-d * 180 + 90})`)
      .text(d => d.toFixed(1));

    // Needle
    const needleLength = innerHeight * 0.75;
    const needleAngle = -Math.PI / 2 + Math.PI * vpin;

    const needle = g.append('g')
      .attr('class', 'needle');

    needle.append('line')
      .attr('x1', 0)
      .attr('y1', 0)
      .attr('x2', 0)
      .attr('y2', -needleLength)
      .attr('stroke', 'white')
      .attr('stroke-width', 2)
      .attr('transform', `rotate(${-90})`)
      .transition()
      .duration(1000)
      .ease(d3.easeElasticOut)
      .attr('transform', `rotate(${needleAngle * 180 / Math.PI})`);

    needle.append('circle')
      .attr('r', 5)
      .attr('fill', 'white');

    // Value text
    g.append('text')
      .attr('x', 0)
      .attr('y', -innerHeight * 0.3)
      .attr('text-anchor', 'middle')
      .attr('fill', 'white')
      .attr('font-size', '24px')
      .attr('font-weight', 'bold')
      .text(vpin.toFixed(3));

    g.append('text')
      .attr('x', 0)
      .attr('y', -innerHeight * 0.1)
      .attr('text-anchor', 'middle')
      .attr('fill', '#9ca3af')
      .attr('font-size', '12px')
      .text('VPIN Score');

  }, [vpin, width, height, toxicityInfo.color]);

  // Calculate trend
  const trend = historicalVpin.length >= 2
    ? historicalVpin[historicalVpin.length - 1] - historicalVpin[historicalVpin.length - 2]
    : 0;

  return (
    <div className="bg-zinc-900 rounded-lg border border-zinc-800 p-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-white">Flow Toxicity (VPIN)</h3>
        <div className="flex items-center gap-2">
          {trend > 0.05 ? (
            <TrendingUp className="w-4 h-4 text-red-500" />
          ) : trend < -0.05 ? (
            <TrendingDown className="w-4 h-4 text-green-500" />
          ) : null}
          <span className={`
            px-2 py-1 rounded text-xs font-medium
            ${toxicityInfo.level === 'Low' ? 'bg-green-500/20 text-green-400' :
              toxicityInfo.level === 'Moderate' ? 'bg-yellow-500/20 text-yellow-400' :
              toxicityInfo.level === 'High' ? 'bg-orange-500/20 text-orange-400' :
              'bg-red-500/20 text-red-400'}
          `}>
            {toxicityInfo.level}
          </span>
        </div>
      </div>

      <svg ref={svgRef} width={width} height={height} />

      <div className="mt-4 p-3 bg-zinc-950 rounded-lg">
        <div className="flex items-start gap-2 mb-2">
          <AlertTriangle className={`w-4 h-4 mt-0.5`} style={{ color: toxicityInfo.color }} />
          <div className="flex-1">
            <p className="text-xs text-zinc-400">{toxicityInfo.description}</p>
          </div>
        </div>

        {/* Historical mini chart */}
        {historicalVpin.length > 0 && (
          <div className="mt-3">
            <div className="text-xs text-zinc-500 mb-1">Last 24h Trend</div>
            <div className="h-8 flex items-end gap-0.5">
              {historicalVpin.slice(-24).map((value, i) => {
                const barHeight = value * 100;
                const color = getToxicityLevel(value).color;
                return (
                  <motion.div
                    key={i}
                    initial={{ height: 0 }}
                    animate={{ height: `${barHeight}%` }}
                    transition={{ delay: i * 0.02 }}
                    className="flex-1 min-w-[2px]"
                    style={{ backgroundColor: color, opacity: 0.7 }}
                  />
                );
              })}
            </div>
          </div>
        )}

        {/* Metrics */}
        <div className="grid grid-cols-3 gap-2 mt-3 text-xs">
          <div>
            <div className="text-zinc-600">24h Avg</div>
            <div className="font-mono text-zinc-300">
              {historicalVpin.length > 0
                ? (historicalVpin.reduce((a, b) => a + b, 0) / historicalVpin.length).toFixed(3)
                : vpin.toFixed(3)}
            </div>
          </div>
          <div>
            <div className="text-zinc-600">24h Max</div>
            <div className="font-mono text-zinc-300">
              {historicalVpin.length > 0
                ? Math.max(...historicalVpin).toFixed(3)
                : vpin.toFixed(3)}
            </div>
          </div>
          <div>
            <div className="text-zinc-600">Percentile</div>
            <div className="font-mono text-zinc-300">
              {(vpin * 100).toFixed(0)}th
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
