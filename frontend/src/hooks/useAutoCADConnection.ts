import { useCallback, useEffect, useRef, useState } from "react";

export interface AutoCADStatus {
  connected: boolean;
  driver_status: string;
  cad_running: boolean;
  process_id: number | null;
  cad_type: string | null;
  reconnect_attempts: number;
}

export type ConnectionStatus =
  | "disconnected"
  | "connecting"
  | "connected"
  | "error";

interface UseAutoCADConnectionReturn {
  status: ConnectionStatus;
  cadStatus: AutoCADStatus | null;
  error: string | null;
  connect: () => Promise<void>;
  disconnect: () => Promise<void>;
  isLoading: boolean;
}

export const useAutoCADConnection = (): UseAutoCADConnectionReturn => {
  const [status, setStatus] = useState<ConnectionStatus>("disconnected");
  const [cadStatus, setCadStatus] = useState<AutoCADStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const AGENT_URL = "http://localhost:8100";
  const BACKEND_URL = "http://localhost:8000";

  const fetchAgentHealth = useCallback(
    async (signal?: AbortSignal): Promise<AutoCADStatus | null> => {
      try {
        const response = await fetch(`${AGENT_URL}/health`, { signal });
        if (!response.ok) {
          throw new Error(`Agent HTTP ${response.status}`);
        }
        const data = await response.json();
        return data.cad_manager || data.autocad_driver || null;
      } catch (err) {
        if (signal?.aborted) return null;
        return null;
      }
    },
    [],
  );

  const connectToBackend = useCallback(async (): Promise<void> => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/autocad/config/bridge`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path: "C:/AutoCAD_Drop/" }),
      });
      if (!response.ok) throw new Error("Backend config failed");
    } catch (err) {
      console.error("Backend connect error:", err);
    }
  }, []);

  const connect = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    setStatus("connecting");
    abortControllerRef.current = new AbortController();

    try {
      // 1. Connect backend
      await connectToBackend();

      // 2. Poll agent until connected
      const signal = abortControllerRef.current.signal;
      const startTime = Date.now();
      while (Date.now() - startTime < 30000) {
        // 30s timeout
        const agentStatus = await fetchAgentHealth(signal);
        if (agentStatus?.connected && agentStatus.cad_running) {
          setStatus("connected");
          setCadStatus(agentStatus);
          return;
        }
        await new Promise((r) => setTimeout(r, 2000));
      }
      throw new Error("Timeout waiting for agent");
    } catch (err: any) {
      setError(err.message || "Connection failed");
      setStatus("error");
    } finally {
      setIsLoading(false);
      abortControllerRef.current = null;
    }
  }, [fetchAgentHealth, connectToBackend]);

  const disconnect = useCallback(async () => {
    setIsLoading(true);
    try {
      // Stop polling
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
      setStatus("disconnected");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    const pollAgent = async () => {
      const agentStatus = await fetchAgentHealth();
      if (agentStatus) {
        setCadStatus(agentStatus);
        setStatus(
          agentStatus.connected && agentStatus.cad_running
            ? "connected"
            : "disconnected",
        );
        setError(null);
      } else {
        setStatus("disconnected");
        setError("Agent not running");
      }
    };

    pollAgent(); // Initial poll
    intervalRef.current = setInterval(pollAgent, 3000); // Poll every 3s

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
      if (abortControllerRef.current) abortControllerRef.current.abort();
    };
  }, [fetchAgentHealth]);

  return {
    status,
    cadStatus,
    error,
    connect,
    disconnect,
    isLoading,
  };
};
