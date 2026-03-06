'use client';

import React, { useEffect, useRef, useState } from 'react';
import * as d3 from 'd3';

interface FlowData {
  timestamp: number;
  priceLevel: number;
  netFlow: number;
  buyVolume: number;
  sellVolume: number;
}

interface FlowHeatmapProps {
  data: FlowData[];
  width?: number;
  height?: number;
}

export function FlowHeatmap({ data, width: propWidth, height = 400 }: FlowHeatmapProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ width: propWidth || 0, height });

  useEffect(() => {
    const updateDimensions = () => {
      if (containerRef.current && !propWidth) {
        setDimensions({
          width: containerRef.current.clientWidth,
          height
        });
      }
    };

    updateDimensions();
    window.addEventListener('resize', updateDimensions);
    return () => window.removeEventListener('resize', updateDimensions);
  }, [height, propWidth]);

  useEffect(() => {
    if (!svgRef.current || dimensions.width === 0 || data.length === 0) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();

    const margin = { top: 40, right: 80, bottom: 60, left: 80 };
    const width = dimensions.width - margin.left - margin.right;
    const height = dimensions.height - margin.top - margin.bottom;

    // Create time bins (e.g., 1-minute intervals)
    const timeExtent = d3.extent(data, d => d.timestamp) as [number, number];
    const priceExtent = d3.extent(data, d => d.priceLevel) as [number, number];

    const timeBins = 50;
    const priceBins = 30;

    const timeStep = (timeExtent[1] - timeExtent[0]) / timeBins;
    const priceStep = (priceExtent[1] - priceExtent[0]) / priceBins;

    // Create 2D matrix for heatmap
    const matrix: number[][] = Array(priceBins)
      .fill(0)
      .map(() => Array(timeBins).fill(0));

    // Aggregate data into bins
    data.forEach(d => {
      const timeIndex = Math.min(
        Math.floor((d.timestamp - timeExtent[0]) / timeStep),
        timeBins - 1
      );
      const priceIndex = Math.min(
        Math.floor((d.priceLevel - priceExtent[0]) / priceStep),
        priceBins - 1
      );
      matrix[priceIndex][timeIndex] += d.netFlow;
    });

    // Flatten for D3
    const flatData: any[] = [];
    matrix.forEach((row, i) => {
      row.forEach((value, j) => {
        flatData.push({
          priceIndex: i,
          timeIndex: j,
          value: value,
          price: priceExtent[0] + i * priceStep,
          time: timeExtent[0] + j * timeStep
        });
      });
    });

    const g = svg.append('g')
      .attr('transform', `translate(${margin.left},${margin.top})`);

    // Scales
    const xScale = d3.scaleLinear()
      .domain([0, timeBins])
      .range([0, width]);

    const yScale = d3.scaleLinear()
      .domain([0, priceBins])
      .range([height, 0]);

    // Color scale - diverging for net flow
    const maxFlow = d3.max(flatData, d => Math.abs(d.value)) || 1;
    const colorScale = d3.scaleDiverging()
      .domain([-maxFlow, 0, maxFlow])
      .interpolator(d3.interpolateRdBu);

    // Draw cells
    g.selectAll('.cell')
      .data(flatData)
      .enter()
      .append('rect')
      .attr('class', 'cell')
      .attr('x', d => xScale(d.timeIndex))
      .attr('y', d => yScale(d.priceIndex + 1))
      .attr('width', width / timeBins)
      .attr('height', height / priceBins)
      .attr('fill', d => colorScale(d.value))
      .attr('stroke', 'none')
      .on('mouseover', function(event, d) {
        // Tooltip
        const tooltip = d3.select('body').append('div')
          .attr('class', 'tooltip')
          .style('opacity', 0)
          .style('position', 'absolute')
          .style('background', 'rgba(0,0,0,0.9)')
          .style('color', 'white')
          .style('padding', '8px')
          .style('border-radius', '4px')
          .style('font-size', '12px')
          .style('pointer-events', 'none');

        tooltip.transition()
          .duration(200)
          .style('opacity', .9);

        tooltip.html(`
          Price: $${d.price.toFixed(2)}<br/>
          Time: ${new Date(d.time).toLocaleTimeString()}<br/>
          Net Flow: ${d.value.toFixed(4)}<br/>
          ${d.value > 0 ? 'Buy Pressure' : 'Sell Pressure'}
        `)
          .style('left', (event.pageX + 10) + 'px')
          .style('top', (event.pageY - 28) + 'px');
      })
      .on('mouseout', function() {
        d3.selectAll('.tooltip').remove();
      });

    // X-axis (time)
    const xAxis = d3.axisBottom(xScale)
      .ticks(10)
      .tickFormat(d => {
        const time = timeExtent[0] + d * timeStep;
        return new Date(time).toLocaleTimeString('en-US', {
          hour: '2-digit',
          minute: '2-digit'
        });
      });

    g.append('g')
      .attr('transform', `translate(0,${height})`)
      .attr('class', 'x-axis')
      .call(xAxis)
      .selectAll('text')
      .attr('fill', '#9ca3af')
      .style('text-anchor', 'end')
      .attr('dx', '-.8em')
      .attr('dy', '.15em')
      .attr('transform', 'rotate(-45)');

    // Y-axis (price)
    const yAxis = d3.axisLeft(yScale)
      .ticks(10)
      .tickFormat(d => {
        const price = priceExtent[0] + d * priceStep;
        return `$${price.toFixed(0)}`;
      });

    g.append('g')
      .attr('class', 'y-axis')
      .call(yAxis)
      .selectAll('text')
      .attr('fill', '#9ca3af');

    // Title
    g.append('text')
      .attr('x', width / 2)
      .attr('y', -20)
      .attr('text-anchor', 'middle')
      .attr('fill', 'white')
      .attr('font-size', '14px')
      .attr('font-weight', 'bold')
      .text('Order Flow Heatmap');

    // Color legend
    const legendWidth = 200;
    const legendHeight = 10;

    const legendScale = d3.scaleLinear()
      .domain([-maxFlow, maxFlow])
      .range([0, legendWidth]);

    const legendAxis = d3.axisBottom(legendScale)
      .ticks(5)
      .tickFormat(d3.format('.2f'));

    const legend = g.append('g')
      .attr('transform', `translate(${width - legendWidth}, -30)`);

    // Create gradient
    const gradientId = 'flow-gradient';
    const gradient = svg.append('defs')
      .append('linearGradient')
      .attr('id', gradientId)
      .attr('x1', '0%')
      .attr('x2', '100%');

    const nStops = 10;
    for (let i = 0; i <= nStops; i++) {
      const value = -maxFlow + (i / nStops) * 2 * maxFlow;
      gradient.append('stop')
        .attr('offset', `${(i / nStops) * 100}%`)
        .attr('stop-color', colorScale(value));
    }

    legend.append('rect')
      .attr('width', legendWidth)
      .attr('height', legendHeight)
      .style('fill', `url(#${gradientId})`);

    legend.append('g')
      .attr('transform', `translate(0,${legendHeight})`)
      .call(legendAxis)
      .selectAll('text')
      .attr('fill', '#9ca3af')
      .style('font-size', '10px');

    legend.append('text')
      .attr('x', legendWidth / 2)
      .attr('y', -5)
      .attr('text-anchor', 'middle')
      .attr('fill', '#9ca3af')
      .style('font-size', '10px')
      .text('Net Flow (Sell ← → Buy)');

  }, [data, dimensions]);

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