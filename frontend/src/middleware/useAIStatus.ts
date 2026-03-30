// ═══════════════════════════════════════════════════════════════════════════
// Engenharia CAD — Hook React para monitorar status de operações CAD
// Permite que componentes exibam progresso sem saber que a IA existe.
// ═══════════════════════════════════════════════════════════════════════════

import { useState, useEffect } from "react";
import { orchestrator } from "./AIOrchestrator";

export interface AIStatusInfo {
  phase: string;
  progress: number;
  message: string;
}

/**
 * Hook que subscreve ao canal de status do orquestrador.
 * Componentes podem mostrar barras de progresso sem acoplamento direto.
 */
export function useAIStatus(): AIStatusInfo {
  const [status, setStatus] = useState<AIStatusInfo>({
    phase: "idle",
    progress: 0,
    message: "",
  });

  useEffect(() => {
    const unsubscribe = orchestrator.onStatusChange(setStatus);
    return unsubscribe;
  }, []);

  return status;
}
