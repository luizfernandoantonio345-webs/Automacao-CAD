import React from "react";
import { useAutoCADConnection } from "../hooks/useAutoCADConnection";
import { Loader2, AlertCircle, CheckCircle2 } from "lucide-react";

const STATUS_CONFIG = {
  disconnected: {
    text: "Conectar ao AutoCAD",
    icon: AlertCircle,
    color: "bg-red-100 text-red-800 border-red-200",
  },
  connecting: {
    text: "Conectando...",
    icon: Loader2,
    color: "bg-yellow-100 text-yellow-800 border-yellow-200",
  },
  connected: {
    text: "AutoCAD Conectado",
    icon: CheckCircle2,
    color: "bg-green-100 text-green-800 border-green-200",
  },
  error: {
    text: "Erro de Conexão",
    icon: AlertCircle,
    color: "bg-red-100 text-red-800 border-red-200",
  },
} as const;

interface AutoCADConnectButtonProps {}

export const AutoCADConnectButton: React.FC<AutoCADConnectButtonProps> = () => {
  const { status, cadStatus, error, connect, disconnect, isLoading } =
    useAutoCADConnection();

  const config = STATUS_CONFIG[status];

  const handleClick = () => {
    if (status === "connected") {
      disconnect();
    } else {
      connect();
    }
  };

  // Abre o instalador do agente local (PowerShell ou BAT)
  const handleInstallAgent = () => {
    // Caminho relativo ao workspace do script de instalação
    // O navegador não pode abrir arquivos locais, mas Electron/desktop pode. Aqui, instrução para o usuário.
    window.open("/AutoCAD_Cliente/SINCRONIZADOR_INTELIGENTE.ps1", "_blank");
  };

  const renderStatusInfo = () => {
    if (status === "connected" && cadStatus) {
      return (
        <div className="text-xs space-y-1 mt-1">
          <div>CAD: {cadStatus.cad_running ? "Aberto" : "Fechado"}</div>
          <div>Driver: {cadStatus.driver_status}</div>
          {cadStatus.process_id && <div>PID: {cadStatus.process_id}</div>}
        </div>
      );
    }
    if (status === "error" || status === "disconnected") {
      return (
        <div className="text-xs mt-1 text-muted-foreground">
          {error || "Agente não encontrado. Inicie o serviço local."}
          <div className="mt-2">
            <button
              className="px-3 py-1 rounded bg-blue-100 text-blue-800 border border-blue-200 hover:bg-blue-200 transition-colors text-xs font-medium"
              onClick={handleInstallAgent}
              type="button"
            >
              Instalar/Executar Agente
            </button>
            <div className="mt-1 text-[10px] text-gray-500">
              Execute o <b>SINCRONIZADOR_INTELIGENTE.ps1</b> ou{" "}
              <b>AutoSetup_License_Connect.bat</b> na pasta{" "}
              <b>AutoCAD_Cliente</b>.<br />
              (Necessário para detectar e conectar ao AutoCAD automaticamente)
            </div>
          </div>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="w-full max-w-sm">
      <button
        onClick={handleClick}
        disabled={isLoading}
        className={`w-full rounded-md border px-4 py-2 text-sm font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-60 ${config.color}`}
      >
        {isLoading ? (
          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
        ) : (
          React.createElement(config.icon, { className: "mr-2 h-4 w-4" })
        )}
        {config.text}
      </button>
      {renderStatusInfo()}
    </div>
  );
};
