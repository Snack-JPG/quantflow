/**
 * WebSocket hook for real-time market data
 */

import { useEffect, useRef, useState, useCallback } from 'react';
import { WebSocketMessage, OrderBookData, Trade, MarketStats } from '@/types/market';

interface UseWebSocketOptions {
  url?: string;
  symbol?: string;
  onOrderBook?: (data: OrderBookData) => void;
  onTrade?: (trade: Trade) => void;
  onStats?: (stats: MarketStats) => void;
  onAnalytics?: (analytics: any) => void;
  reconnectDelay?: number;
}

export function useWebSocket({
  url = 'ws://localhost:8000/ws',
  symbol,
  onOrderBook,
  onTrade,
  onStats,
  onAnalytics,
  reconnectDelay = 5000,
}: UseWebSocketOptions) {
  const [isConnected, setIsConnected] = useState(false);
  const [clientId, setClientId] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const pingIntervalRef = useRef<NodeJS.Timeout | null>(null);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    try {
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('WebSocket connected');
        setIsConnected(true);

        // Start ping interval
        pingIntervalRef.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'ping' }));
          }
        }, 30000);
      };

      ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);

          switch (message.type) {
            case 'connected':
              setClientId(message.client_id);
              console.log('Connected with client ID:', message.client_id);

              // Auto-subscribe to symbol if provided
              if (symbol && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({ type: 'subscribe', symbol }));
              }
              break;

            case 'orderbook':
              onOrderBook?.(message.data);
              break;

            case 'trade':
              onTrade?.(message.data);
              break;

            case 'stats':
              onStats?.(message.data);
              break;

            case 'analytics':
              onAnalytics?.(message.data);
              break;

            case 'subscribed':
              console.log('Subscribed to:', message.symbol);
              break;

            case 'unsubscribed':
              console.log('Unsubscribed from:', message.symbol);
              break;

            case 'pong':
              // Heartbeat response
              break;
          }
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
      };

      ws.onclose = () => {
        console.log('WebSocket disconnected');
        setIsConnected(false);
        setClientId(null);

        // Clear ping interval
        if (pingIntervalRef.current) {
          clearInterval(pingIntervalRef.current);
          pingIntervalRef.current = null;
        }

        // Attempt to reconnect
        reconnectTimeoutRef.current = setTimeout(() => {
          console.log('Attempting to reconnect...');
          connect();
        }, reconnectDelay);
      };
    } catch (error) {
      console.error('Failed to create WebSocket connection:', error);
      setIsConnected(false);
    }
  }, [url, symbol, onOrderBook, onTrade, onStats, onAnalytics, reconnectDelay]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    if (pingIntervalRef.current) {
      clearInterval(pingIntervalRef.current);
      pingIntervalRef.current = null;
    }

    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    setIsConnected(false);
    setClientId(null);
  }, []);

  const subscribe = useCallback((newSymbol: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'subscribe', symbol: newSymbol }));
    }
  }, []);

  const unsubscribe = useCallback((oldSymbol: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'unsubscribe', symbol: oldSymbol }));
    }
  }, []);

  useEffect(() => {
    connect();

    return () => {
      disconnect();
    };
  }, [connect, disconnect]);

  // Handle symbol changes
  useEffect(() => {
    if (symbol && isConnected && wsRef.current?.readyState === WebSocket.OPEN) {
      subscribe(symbol);
    }
  }, [symbol, isConnected, subscribe]);

  return {
    isConnected,
    clientId,
    subscribe,
    unsubscribe,
  };
}