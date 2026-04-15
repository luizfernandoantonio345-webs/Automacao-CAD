import { useCallback, useEffect, useRef, useState } from "react";
import { API_BASE_URL } from "../services/api";

export interface AutoCADStatus {
  connected: boolean;
  driver_status: string;
  cad_running: boolean;
  process_id: number | null;
  cad_type: string | null;
  cad_version: string | null;
  machine: string | null;
  commands_pending: number;
  commands_executed: number;
  last_heartbeat: string | null;
  seconds_since_heartbeat: number | null;
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

/**
 * Hook para gerenciar conexão com o Agente AutoCAD via Backend Bridge.
 * 
 * O sincronizador PowerShell envia heartbeats para /api/bridge/connection.
 * Este hook consulta /api/bridge/health para verificar o status.
 */
export const useAutoCADConnection = (): UseAutoCADConnectionReturn => {
  const [status, setStatus] = useState<ConnectionStatus>("disconnected");
  const [cadStatus, setCadStatus] = useState<AutoCADStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const BACKEND_URL = API_BASE_URL;

  /**
   * Consulta o status do agente via backend (não mais localhost:8100)
   */
  const fetchBridgeHealth = useCallback(
    async (signal?: AbortSignal): Promise<AutoCADStatus | null> => {
      try {
        const response = await fetch(`${BACKEND_URL}/api/bridge/health`, { 
          signal,
          headers: { "Accept": "application/json" },
        });
        if (!response.ok) {
          throw new Error(`Bridge health HTTP ${response.status}`);
        }
        const data = await response.json();
        
        // Mapear resposta do backend para AutoCADStatus
        return {
          connected: data.connected ?? false,
          driver_status: data.status ?? "unknown",
          cad_running: data.connected && data.cad_type != null,
          process_id: null, // Não disponível via bridge
          cad_type: data.cad_type ?? null,
          cad_version: data.cad_version ?? null,
          machine: data.machine ?? null,
          commands_pending: data.commands_pending ?? 0,
          commands_executed: data.commands_executed ?? 0,
          last_heartbeat: data.last_heartbeat ?? null,
          seconds_since_heartbeat: data.seconds_since_heartbeat ?? null,
          reconnect_attempts: 0,
        };
      } catch (err) {
        if (signal?.aborted) return null;
        console.error("Bridge health error:", err);
        return null;
      }
    },
    [BACKEND_URL],
  );

  /**
   * Configura o backend para modo bridge (opcional, já é o default)
   */
  const configureBridgeMode = useCallback(async (): Promise<void> => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/autocad/config/bridge`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path: "C:/AutoCAD_Drop/" }),
      });
      if (!response.ok) {
        console.warn(`Backend config returned ${response.status}, continuing anyway`);
      }
    } catch (err) {
      console.warn("Backend config error (non-blocking):", err);
      // Não bloquear - o sincronizador pode funcionar mesmo sem esta config
    }
  }, [BACKEND_URL]);

  /**
   * Inicia conexão - configura backend e aguarda heartbeat do sincronizador
   */
  const connect = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    setStatus("connecting");
    abortControllerRef.current = new AbortController();

    try {
      // 1. Configurar backend para modo bridge
      await configureBridgeMode();

      // 2. Aguardar heartbeat do sincronizador (poll /api/bridge/health)
      const signal = abortControllerRef.current.signal;
      const startTime = Date.now();
      const TIMEOUT_MS = 60000; // 60s timeout (sincronizador pode demorar para abrir CAD)
      
      while (Date.now() - startTime < TIMEOUT_MS) {
        const bridgeStatus = await fetchBridgeHealth(signal);
        if (bridgeStatus?.connected) {
          setStatus("connected");
          setCadStatus(bridgeStatus);
          setError(null);
          return;
        }
        // Mostrar feedback ao usuário
        const elapsed = Math.floor((Date.now() - startTime) / 1000);
        setError(`Aguardando sincronizador... (${elapsed}s)`);
        await new Promise((r) => setTimeout(r, 2000));
      }
      throw new Error("Sincronizador não conectou. Execute o instalador no PC do AutoCAD.");
    } catch (err: any) {
      if (!abortControllerRef.current?.signal.aborted) {
        setError(err.message || "Falha na conexão");
        setStatus("error");
      }
    } finally {
      setIsLoading(false);
      abortControllerRef.current = null;
    }
  }, [fetchBridgeHealth, configureBridgeMode]);

  /**
   * Desconecta - apenas para polling do frontend
   */
  const disconnect = useCallback(async () => {
    setIsLoading(true);
    try {
      // Cancelar conexão em andamento
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
      // Parar polling
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
      setStatus("disconnected");
      setCadStatus(null);
      setError(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  /**
   * Polling contínuo do status do bridge
   */
  useEffect(() => {
    const pollBridgeHealth = async () => {
      const bridgeStatus = await fetchBridgeHealth();
      if (bridgeStatus) {
        setCadStatus(bridgeStatus);
        if (bridgeStatus.connected) {
          setStatus("connected");
          setError(null);
        } else {
          // Só marcar desconectado se já estava conectado antes
          if (status === "connected") {
            setStatus("disconnected");
            setError("Sincronizador desconectou. Verifique se está rodando.");
          }
        }
      } else {
        // Falha no fetch - backend pode estar offline
        if (status === "connected") {
          setStatus("error");
          setError("Falha ao consultar status do bridge");
        }
      }
    };

    // Poll inicial
    pollBridgeHealth();
    
    // Poll a cada 5s (alinhado com heartbeat do sincronizador)
    intervalRef.current = setInterval(pollBridgeHealth, 5000);

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
      if (abortControllerRef.current) abortControllerRef.current.abort();
    };
  }, [fetchBridgeHealth, status]);

  return {
    status,
    cadStatus,
    error,
    connect,
    disconnect,
    isLoading,
  };
};
