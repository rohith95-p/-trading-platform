'use client';

import { useState, useEffect, useRef, useCallback } from 'react';

export interface WebSocketState<T> {
  data: T | null;
  isConnected: boolean;
  error: string | null;
}

/**
 * useWebSocket Hook
 * Manages a WebSocket connection with auto-reconnect and JSON message handling.
 *
 * @param url - WebSocket URL to connect to
 * @returns { data, isConnected, error }
 */
export function useWebSocket<T = unknown>(url: string): WebSocketState<T> {
  const [data, setData] = useState<T | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isMountedRef = useRef(true);
  const reconnectDelayRef = useRef(1000);

  const connect = useCallback(() => {
    if (!isMountedRef.current) return;

    try {
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        if (!isMountedRef.current) return;
        setIsConnected(true);
        setError(null);
        reconnectDelayRef.current = 1000; // reset backoff
      };

      ws.onmessage = (event: MessageEvent) => {
        if (!isMountedRef.current) return;
        try {
          const parsed = JSON.parse(event.data as string) as T;
          setData(parsed);
        } catch {
          // non-JSON message, ignore
        }
      };

      ws.onerror = () => {
        if (!isMountedRef.current) return;
        setError('WebSocket error');
      };

      ws.onclose = () => {
        if (!isMountedRef.current) return;
        setIsConnected(false);
        wsRef.current = null;

        // Auto-reconnect with exponential backoff (max 30s)
        const delay = Math.min(reconnectDelayRef.current, 30000);
        reconnectDelayRef.current = delay * 2;
        reconnectTimeoutRef.current = setTimeout(connect, delay);
      };
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to connect');
    }
  }, [url]);

  useEffect(() => {
    isMountedRef.current = true;
    connect();

    return () => {
      isMountedRef.current = false;
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.onclose = null; // prevent reconnect on intentional close
        wsRef.current.close();
      }
    };
  }, [connect]);

  return { data, isConnected, error };
}
