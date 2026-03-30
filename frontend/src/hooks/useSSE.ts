import { useEffect, useRef, useCallback } from "react";
import { SSE_BASE_URL } from "../services/api";

interface UseSSEOptions {
  /** SSE endpoint path, e.g. "/sse/notifications" */
  path: string;
  /** Map of event names to handlers */
  listeners?: Record<string, (data: any) => void>;
  /** Handler for generic messages (onmessage) */
  onMessage?: (data: any) => void;
  /** Called when connection state changes */
  onConnectionChange?: (connected: boolean) => void;
  /** Max reconnect attempts before giving up (default: 10) */
  maxRetries?: number;
  /** Max seconds without a ping before forcing reconnect (default: 45) */
  pingTimeout?: number;
  /** Whether the hook is active (default: true) */
  enabled?: boolean;
}

/**
 * SSE hook with exponential backoff reconnection & ping-based dead-connection detection.
 * Automatically reconnects when the connection drops or no ping is received within the timeout.
 */
export function useSSE(options: UseSSEOptions) {
  const {
    path,
    listeners,
    onMessage,
    onConnectionChange,
    maxRetries = 10,
    pingTimeout = 45,
    enabled = true,
  } = options;

  const sourceRef = useRef<EventSource | null>(null);
  const retryRef = useRef(0);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const pingTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const destroyedRef = useRef(false);

  const resetPingTimer = useCallback(() => {
    if (pingTimerRef.current) clearTimeout(pingTimerRef.current);
    pingTimerRef.current = setTimeout(() => {
      // No ping received — force reconnect
      sourceRef.current?.close();
      sourceRef.current = null;
      scheduleReconnect();
    }, pingTimeout * 1000);
  }, [pingTimeout]); // eslint-disable-line

  const scheduleReconnect = useCallback(() => {
    if (destroyedRef.current || retryRef.current >= maxRetries) return;
    const delay = Math.min(1000 * Math.pow(2, retryRef.current), 30000);
    retryRef.current++;
    timerRef.current = setTimeout(() => connect(), delay);
  }, [maxRetries]); // eslint-disable-line

  const connect = useCallback(() => {
    if (destroyedRef.current) return;
    try {
      const url = `${SSE_BASE_URL}${path}`;
      const es = new EventSource(url);
      sourceRef.current = es;

      es.onopen = () => {
        retryRef.current = 0;
        onConnectionChange?.(true);
        resetPingTimer();
      };

      // Listen for ping/heartbeat to detect alive connection
      es.addEventListener("ping", () => resetPingTimer());
      es.addEventListener("heartbeat", () => resetPingTimer());

      // Register custom event listeners
      if (listeners) {
        for (const [event, handler] of Object.entries(listeners)) {
          es.addEventListener(event, (ev: MessageEvent) => {
            resetPingTimer();
            try {
              handler(JSON.parse(ev.data));
            } catch {
              handler(ev.data);
            }
          });
        }
      }

      if (onMessage) {
        es.onmessage = (ev: MessageEvent) => {
          resetPingTimer();
          try {
            onMessage(JSON.parse(ev.data));
          } catch {
            onMessage(ev.data);
          }
        };
      }

      es.onerror = () => {
        es.close();
        sourceRef.current = null;
        onConnectionChange?.(false);
        scheduleReconnect();
      };
    } catch {
      scheduleReconnect();
    }
  }, [
    path,
    listeners,
    onMessage,
    onConnectionChange,
    resetPingTimer,
    scheduleReconnect,
  ]);

  useEffect(() => {
    destroyedRef.current = false;
    if (enabled) {
      connect();
    }
    return () => {
      destroyedRef.current = true;
      if (timerRef.current) clearTimeout(timerRef.current);
      if (pingTimerRef.current) clearTimeout(pingTimerRef.current);
      sourceRef.current?.close();
      sourceRef.current = null;
    };
  }, [enabled, path]); // eslint-disable-line

  return sourceRef;
}
