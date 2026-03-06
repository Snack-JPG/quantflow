/**
 * Live Order Book Display Component
 */

'use client';

import React, { useMemo } from 'react';
import { OrderBookData } from '@/types/market';

interface OrderBookProps {
  data: OrderBookData | null;
  depth?: number;
}

export function OrderBook({ data, depth = 20 }: OrderBookProps) {
  // Format price with appropriate decimal places
  const formatPrice = (price: string) => {
    const num = parseFloat(price);
    if (num >= 1000) return num.toFixed(2);
    if (num >= 1) return num.toFixed(4);
    return num.toFixed(6);
  };

  // Format quantity
  const formatQuantity = (qty: string) => {
    const num = parseFloat(qty);
    if (num >= 1000) return num.toFixed(2);
    if (num >= 1) return num.toFixed(4);
    return num.toFixed(6);
  };

  // Calculate max quantities for visual bars
  const { maxBidQty, maxAskQty } = useMemo(() => {
    if (!data) return { maxBidQty: 0, maxAskQty: 0 };

    const maxBid = Math.max(
      ...data.bids.slice(0, depth).map(([, qty]) => parseFloat(qty))
    );
    const maxAsk = Math.max(
      ...data.asks.slice(0, depth).map(([, qty]) => parseFloat(qty))
    );

    return { maxBidQty: maxBid || 1, maxAskQty: maxAsk || 1 };
  }, [data, depth]);

  if (!data) {
    return (
      <div className="bg-card rounded-lg border border-border p-4">
        <h2 className="text-lg font-semibold mb-4">Order Book</h2>
        <div className="text-muted-foreground text-center py-8">
          Waiting for data...
        </div>
      </div>
    );
  }

  return (
    <div className="bg-card rounded-lg border border-border">
      <div className="p-4 border-b border-border">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">Order Book</h2>
          <div className="flex items-center gap-4 text-sm">
            <span className="text-muted-foreground">{data.symbol}</span>
            {data.spread_bps && (
              <span className="text-muted-foreground">
                Spread: {parseFloat(data.spread_bps).toFixed(2)} bps
              </span>
            )}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 divide-x divide-border">
        {/* Bids */}
        <div>
          <div className="order-book-header text-muted-foreground">
            <div>Price</div>
            <div className="text-right">Quantity</div>
            <div className="text-right">Total</div>
          </div>
          <div className="divide-y divide-border/50">
            {data.bids.slice(0, depth).map(([price, qty], i) => {
              const priceFmt = formatPrice(price);
              const qtyFmt = formatQuantity(qty);
              const total = (parseFloat(price) * parseFloat(qty)).toFixed(2);
              const barWidth = (parseFloat(qty) / maxBidQty) * 100;

              return (
                <div
                  key={`bid-${i}`}
                  className="order-book-row relative hover:bg-secondary/20 transition-colors"
                >
                  <div
                    className="absolute inset-y-0 left-0 bg-buy/10"
                    style={{ width: `${barWidth}%` }}
                  />
                  <div className="relative text-buy">{priceFmt}</div>
                  <div className="relative text-right">{qtyFmt}</div>
                  <div className="relative text-right text-muted-foreground text-xs">
                    ${total}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Asks */}
        <div>
          <div className="order-book-header text-muted-foreground">
            <div>Price</div>
            <div className="text-right">Quantity</div>
            <div className="text-right">Total</div>
          </div>
          <div className="divide-y divide-border/50">
            {data.asks.slice(0, depth).map(([price, qty], i) => {
              const priceFmt = formatPrice(price);
              const qtyFmt = formatQuantity(qty);
              const total = (parseFloat(price) * parseFloat(qty)).toFixed(2);
              const barWidth = (parseFloat(qty) / maxAskQty) * 100;

              return (
                <div
                  key={`ask-${i}`}
                  className="order-book-row relative hover:bg-secondary/20 transition-colors"
                >
                  <div
                    className="absolute inset-y-0 right-0 bg-sell/10"
                    style={{ width: `${barWidth}%` }}
                  />
                  <div className="relative text-sell">{priceFmt}</div>
                  <div className="relative text-right">{qtyFmt}</div>
                  <div className="relative text-right text-muted-foreground text-xs">
                    ${total}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Mid Price Display */}
      {data.mid_price && (
        <div className="p-3 border-t border-border bg-secondary/10">
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Mid Price</span>
            <span className="font-mono font-semibold">
              {formatPrice(data.mid_price)}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
