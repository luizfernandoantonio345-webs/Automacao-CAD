import React, { useState, useEffect, useCallback, useRef } from "react";
import { useTheme } from "../context/ThemeContext";
import { ApiService } from "../services/api";
import type { AutoCADHealthResponse, DriverResult } from "../services/api";
import { motion, AnimatePresence } from "framer-motion";
import {
  Activity,
  Wifi,
  WifiOff,
  Network,
  Monitor,
  Pipette,
  CircleDot,
  Hexagon,
  FolderSync,
  Send,
  CheckCircle2,
  XCircle,
  Loader2,
  RefreshCw,
  Layers,
  Save,
  ZoomIn,
  Type,
  Minus,
  Settings2,
  AlertTriangle,
  Download,
  ExternalLink,
  Copy,
  Info,
} from "lucide-react";

// ═══════════════════════════════════════════════════════════════════════════
// Types
// ═══════════════════════════════════════════════════════════════════════════

type DriverMode = "com" | "bridge";

interface BufferStatus {
  mode: string;
  bridge_path: string;
  buffer_size: number;
  bridge_accessible: boolean;
}

interface CommandLog {
  id: string;
  timestamp: string;
  operation: string;
  status: "success" | "error" | "pending";
  message: string;
}

// ═══════════════════════════════════════════════════════════════════════════
// CadDashboard — Painel de Controle AutoCAD N-58
// ═══════════════════════════════════════════════════════════════════════════

const CadDashboard: React.FC = () => {
  const { theme } = useTheme();

  // ── State ──
  const [health, setHealth] = useState<AutoCADHealthResponse | null>(null);
  const [bufferStatus, setBufferStatus] = useState<BufferStatus | null>(null);
  const [bridgeClient, setBridgeClient] = useState<{
    connected: boolean;
    cad_type?: string;
    cad_version?: string;
    machine?: string;
    commands_executed?: number;
    last_seen?: string;
  } | null>(null);
  const [driverMode, setDriverMode] = useState<DriverMode>("com");
  const [bridgePath, setBridgePath] = useState("");
  const [loading, setLoading] = useState<string | null>(null);
  const [logs, setLogs] = useState<CommandLog[]>([]);

  // Draw Pipe form
  const [pipeStartX, setPipeStartX] = useState("0");
  const [pipeStartY, setPipeStartY] = useState("0");
  const [pipeStartZ, setPipeStartZ] = useState("0");
  const [pipeEndX, setPipeEndX] = useState("1000");
  const [pipeEndY, setPipeEndY] = useState("0");
  const [pipeEndZ, setPipeEndZ] = useState("0");
  const [pipeDiameter, setPipeDiameter] = useState("6");
  const [pipeLayer, setPipeLayer] = useState("PIPE-PROCESS");

  // Insert Component form
  const [compType, setCompType] = useState("VALVE-GATE");
  const [compX, setCompX] = useState("500");
  const [compY, setCompY] = useState("0");
  const [compZ, setCompZ] = useState("0");
  const [compRotation, setCompRotation] = useState("0");
  const [compScale, setCompScale] = useState("1");
  const [compLayer, setCompLayer] = useState("VALVE");

  // Add Text form
  const [textContent, setTextContent] = useState("");
  const [textX, setTextX] = useState("0");
  const [textY, setTextY] = useState("0");
  const [textZ, setTextZ] = useState("0");
  const [textHeight, setTextHeight] = useState("2.5");

  const logEndRef = useRef<HTMLDivElement>(null);

  // ── Helpers ──
  const addLog = useCallback(
    (
      operation: string,
      status: "success" | "error" | "pending",
      message: string,
    ) => {
      const entry: CommandLog = {
        id: `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
        timestamp: new Date().toLocaleTimeString("pt-BR"),
        operation,
        status,
        message,
      };
      setLogs((prev) => [...prev.slice(-49), entry]);
    },
    [],
  );

  const handleResult = useCallback(
    (operation: string, result: DriverResult) => {
      if (result.success) {
        addLog(operation, "success", result.message || "OK");
      } else {
        addLog(operation, "error", result.message || "Falha");
      }
    },
    [addLog],
  );

  // ── Polling health ──
  const refreshHealth = useCallback(async () => {
    try {
      const [h, b] = await Promise.all([
        ApiService.autocadHealth(),
        ApiService.autocadBufferStatus(),
      ]);
      setHealth(h);
      setBufferStatus(b);
      setDriverMode(b.mode === "bridge" ? "bridge" : "com");
      if (b.bridge_path) setBridgePath(b.bridge_path);

      // Buscar status do cliente bridge
      if (b.mode === "bridge") {
        try {
          const bridgeStatus = await fetch(
            `${process.env.REACT_APP_API_BASE_URL || "https://automacao-cad-backend.vercel.app"}/api/bridge/status`,
          ).then((r) => r.json());
          if (bridgeStatus.client) {
            setBridgeClient(bridgeStatus.client);
          }
        } catch {
          // Ignorar erros de bridge status
        }
      }
    } catch {
      setHealth(null);
      setBufferStatus(null);
    }
  }, []);

  useEffect(() => {
    refreshHealth();
    const timer = setInterval(refreshHealth, 5000);
    return () => clearInterval(timer);
  }, [refreshHealth]);

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  // ── Actions ──
  const doConnect = async () => {
    setLoading("connect");
    try {
      const r = await ApiService.autocadConnect();
      handleResult("Conectar AutoCAD", r);
      await refreshHealth();
    } catch (e: any) {
      addLog("Conectar AutoCAD", "error", e?.message ?? "Erro de conexão");
    }
    setLoading(null);
  };

  const doDisconnect = async () => {
    setLoading("disconnect");
    try {
      const r = await ApiService.autocadDisconnect();
      handleResult("Desconectar", r);
      await refreshHealth();
    } catch (e: any) {
      addLog("Desconectar", "error", e?.message ?? "Erro");
    }
    setLoading(null);
  };

  const doSetMode = async (useBridge: boolean) => {
    setLoading("mode");
    try {
      const r = await ApiService.autocadSetMode(useBridge);
      handleResult(`Modo → ${useBridge ? "Ponte" : "COM"}`, r);
      setDriverMode(useBridge ? "bridge" : "com");
      await refreshHealth();
    } catch (e: any) {
      addLog("Alterar Modo", "error", e?.message ?? "Erro");
    }
    setLoading(null);
  };

  const doSetBridgePath = async () => {
    if (!bridgePath.trim()) return;
    setLoading("bridge");
    try {
      const r = await ApiService.autocadSetBridgePath(bridgePath.trim());
      handleResult("Configurar Bridge Path", r);
      await refreshHealth();
    } catch (e: any) {
      addLog("Bridge Path", "error", e?.message ?? "Erro");
    }
    setLoading(null);
  };

  const doCreateLayers = async () => {
    setLoading("layers");
    try {
      const r = await ApiService.autocadCreateLayers();
      handleResult("Criar Layers N-58", r);
    } catch (e: any) {
      addLog("Criar Layers", "error", e?.message ?? "Erro");
    }
    setLoading(null);
  };

  const doDrawPipe = async () => {
    setLoading("pipe");
    addLog("Desenhar Tubo", "pending", "Enviando...");
    try {
      const r = await ApiService.autocadDrawPipe({
        points: [
          [
            parseFloat(pipeStartX),
            parseFloat(pipeStartY),
            parseFloat(pipeStartZ),
          ],
          [parseFloat(pipeEndX), parseFloat(pipeEndY), parseFloat(pipeEndZ)],
        ],
        diameter: parseFloat(pipeDiameter),
        layer: pipeLayer,
      });
      handleResult("Desenhar Tubo", r);
    } catch (e: any) {
      addLog("Desenhar Tubo", "error", e?.message ?? "Erro ao desenhar");
    }
    setLoading(null);
  };

  const doInsertComponent = async () => {
    setLoading("component");
    addLog(`Inserir ${compType}`, "pending", "Enviando...");
    try {
      const r = await ApiService.autocadInsertComponent({
        block_name: compType,
        coordinate: [parseFloat(compX), parseFloat(compY), parseFloat(compZ)],
        rotation: parseFloat(compRotation),
        scale: parseFloat(compScale),
        layer: compLayer,
      });
      handleResult(`Inserir ${compType}`, r);
    } catch (e: any) {
      addLog(`Inserir ${compType}`, "error", e?.message ?? "Erro");
    }
    setLoading(null);
  };

  const doAddText = async () => {
    if (!textContent.trim()) return;
    setLoading("text");
    addLog("Adicionar Texto", "pending", "Enviando...");
    try {
      const r = await ApiService.autocadAddText({
        text: textContent.trim(),
        position: [parseFloat(textX), parseFloat(textY), parseFloat(textZ)],
        height: parseFloat(textHeight),
        layer: "ANNOTATION",
      });
      handleResult("Adicionar Texto", r);
    } catch (e: any) {
      addLog("Adicionar Texto", "error", e?.message ?? "Erro");
    }
    setLoading(null);
  };

  const doFinalize = async () => {
    setLoading("finalize");
    try {
      const r = await ApiService.autocadFinalize();
      handleResult("Finalizar Vista", r);
    } catch (e: any) {
      addLog("Finalizar Vista", "error", e?.message ?? "Erro");
    }
    setLoading(null);
  };

  const doSave = async () => {
    setLoading("save");
    try {
      const r = await ApiService.autocadSave();
      handleResult("Salvar Documento", r);
    } catch (e: any) {
      addLog("Salvar Documento", "error", e?.message ?? "Erro");
    }
    setLoading(null);
  };

  const doCommit = async () => {
    setLoading("commit");
    try {
      const r = await ApiService.autocadCommit();
      handleResult("Commit Bridge", r);
      await refreshHealth();
    } catch (e: any) {
      addLog("Commit Bridge", "error", e?.message ?? "Erro");
    }
    setLoading(null);
  };

  // ── Derived state ──
  const clientConnected = bridgeClient?.connected === true;
  const isConnected =
    health?.driver_status === "Connected" ||
    health?.driver_status === "Simulation" ||
    health?.driver_status === "Bridge" ||
    clientConnected;
  const statusColor = clientConnected
    ? theme.success
    : isConnected
      ? theme.warning
      : theme.danger;
  const statusLabel = clientConnected
    ? `🟢 Sincronizador Conectado (${bridgeClient?.cad_type || "CAD"})`
    : health?.driver_status === "Bridge"
      ? "🟡 Aguardando Sincronizador..."
      : (health?.driver_status ?? "Desconhecido");
  const isBridge = driverMode === "bridge";

  // ── Style helpers ──
  const card = (extra?: React.CSSProperties): React.CSSProperties => ({
    backgroundColor: theme.surface,
    border: `1px solid ${theme.border}`,
    borderRadius: "12px",
    padding: "20px",
    ...extra,
  });

  const inputStyle: React.CSSProperties = {
    backgroundColor: theme.inputBackground,
    border: `1px solid ${theme.inputBorder}`,
    borderRadius: "6px",
    padding: "8px 12px",
    color: theme.textPrimary,
    fontSize: "0.875rem",
    width: "100%",
    outline: "none",
  };

  const labelStyle: React.CSSProperties = {
    fontSize: "0.75rem",
    color: theme.textSecondary,
    fontWeight: 600,
    textTransform: "uppercase",
    letterSpacing: "0.5px",
    marginBottom: "4px",
    display: "block",
  };

  const btnPrimary = (isLoading?: boolean): React.CSSProperties => ({
    backgroundColor: isLoading ? theme.textTertiary : theme.accentPrimary,
    color: "#FFFFFF",
    border: "none",
    borderRadius: "8px",
    padding: "10px 20px",
    fontWeight: 600,
    cursor: isLoading ? "not-allowed" : "pointer",
    display: "flex",
    alignItems: "center",
    gap: "8px",
    fontSize: "0.875rem",
    transition: "all 0.2s ease",
    opacity: isLoading ? 0.7 : 1,
  });

  const btnSecondary: React.CSSProperties = {
    backgroundColor: "transparent",
    color: theme.textPrimary,
    border: `1px solid ${theme.border}`,
    borderRadius: "8px",
    padding: "8px 16px",
    fontWeight: 500,
    cursor: "pointer",
    display: "flex",
    alignItems: "center",
    gap: "6px",
    fontSize: "0.8rem",
    transition: "all 0.2s ease",
  };

  const btnDanger: React.CSSProperties = {
    backgroundColor: theme.danger,
    color: "#FFFFFF",
    border: "none",
    borderRadius: "8px",
    padding: "8px 16px",
    fontWeight: 600,
    cursor: "pointer",
    display: "flex",
    alignItems: "center",
    gap: "6px",
    fontSize: "0.8rem",
  };

  const quickBtn = (color: string): React.CSSProperties => ({
    background: `linear-gradient(135deg, ${color}22 0%, ${color}11 100%)`,
    border: `1px solid ${color}44`,
    borderRadius: "10px",
    padding: "16px",
    cursor: "pointer",
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    gap: "8px",
    color: theme.textPrimary,
    transition: "all 0.2s ease",
    minWidth: "120px",
  });

  // ═══════════════════════════════════════════════════════════════════════
  // RENDER
  // ═══════════════════════════════════════════════════════════════════════

  return (
    <div
      style={{
        padding: "24px",
        backgroundColor: theme.background,
        minHeight: "100vh",
        color: theme.textPrimary,
      }}
    >
      {/* ── Header ── */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "24px",
        }}
      >
        <div>
          <h1 style={{ margin: 0, fontSize: "1.75rem", fontWeight: 700 }}>
            Painel de Controle CAD
          </h1>
          <p
            style={{
              margin: "4px 0 0 0",
              fontSize: "0.85rem",
              color: theme.textSecondary,
            }}
          >
            Engenharia CAD — Dashboard Norma N-58 Petrobras
          </p>
        </div>
        <button
          onClick={refreshHealth}
          style={btnSecondary}
          title="Atualizar status"
        >
          <RefreshCw size={16} /> Atualizar
        </button>
      </div>

      {/* ═══════════ ROW 1: Status + Mode + Bridge Config ═══════════ */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr 1fr",
          gap: "16px",
          marginBottom: "20px",
        }}
      >
        {/* ── Status Card ── */}
        <motion.div
          style={card()}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
        >
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "10px",
              marginBottom: "16px",
            }}
          >
            <Activity size={18} color={theme.accentPrimary} />
            <span style={{ ...labelStyle, marginBottom: 0 }}>STATUS CAD</span>
            {health?.engine && health.engine !== "Unknown" && (
              <span
                style={{
                  marginLeft: "auto",
                  fontSize: "0.65rem",
                  fontWeight: 700,
                  padding: "2px 8px",
                  borderRadius: "4px",
                  backgroundColor:
                    health.engine === "GstarCAD"
                      ? `${theme.success}18`
                      : `${theme.accentPrimary}18`,
                  border: `1px solid ${health.engine === "GstarCAD" ? theme.success : theme.accentPrimary}`,
                  color:
                    health.engine === "GstarCAD"
                      ? theme.success
                      : theme.accentPrimary,
                  letterSpacing: "0.04em",
                }}
              >
                ⚙ {health.engine}
              </span>
            )}
          </div>

          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "12px",
              marginBottom: "16px",
            }}
          >
            <div
              style={{
                width: "12px",
                height: "12px",
                borderRadius: "50%",
                backgroundColor: statusColor,
                boxShadow: `0 0 8px ${statusColor}`,
              }}
            />
            <span style={{ fontSize: "1.1rem", fontWeight: 600 }}>
              {statusLabel}
            </span>
          </div>

          {/* Info do cliente bridge conectado */}
          {bridgeClient?.connected && (
            <div
              style={{
                backgroundColor: `${theme.success}15`,
                border: `1px solid ${theme.success}40`,
                borderRadius: "8px",
                padding: "12px",
                marginBottom: "12px",
              }}
            >
              <div
                style={{
                  fontSize: "0.75rem",
                  fontWeight: 600,
                  color: theme.success,
                  marginBottom: "8px",
                }}
              >
                ✓ SINCRONIZADOR ATIVO
              </div>
              <div
                style={{
                  fontSize: "0.8rem",
                  color: theme.textSecondary,
                  display: "grid",
                  gap: "4px",
                }}
              >
                <span>📍 Máquina: {bridgeClient.machine || "Local"}</span>
                <span>
                  🖥️ CAD: {bridgeClient.cad_type} {bridgeClient.cad_version}
                </span>
                <span>
                  📊 Comandos executados: {bridgeClient.commands_executed || 0}
                </span>
              </div>
            </div>
          )}

          {/* Info quando aguardando sincronizador */}
          {isBridge && !bridgeClient?.connected && (
            <div
              style={{
                backgroundColor: `${theme.warning}15`,
                border: `1px solid ${theme.warning}40`,
                borderRadius: "8px",
                padding: "12px",
                marginBottom: "12px",
              }}
            >
              <div
                style={{
                  fontSize: "0.75rem",
                  fontWeight: 600,
                  color: theme.warning,
                  marginBottom: "8px",
                }}
              >
                ⏳ AGUARDANDO SINCRONIZADOR
              </div>
              <div
                style={{
                  fontSize: "0.8rem",
                  color: theme.textSecondary,
                  marginBottom: "10px",
                }}
              >
                Baixe e execute o sincronizador no PC do AutoCAD
              </div>
              <a
                href="https://automacao-cad-backend.vercel.app/api/download/sincronizador"
                target="_blank"
                rel="noopener noreferrer"
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "6px",
                  padding: "8px 14px",
                  backgroundColor: theme.accentPrimary,
                  color: "#FFFFFF",
                  borderRadius: "6px",
                  textDecoration: "none",
                  fontSize: "0.8rem",
                  fontWeight: 600,
                }}
              >
                <Download size={14} /> Baixar Sincronizador
              </a>
            </div>
          )}

          {health && (
            <div
              style={{
                fontSize: "0.8rem",
                color: theme.textSecondary,
                display: "grid",
                gap: "4px",
              }}
            >
              <span>Engine: {health.engine || "Não detectado"}</span>
              <span>
                COM Disponível: {health.com_available ? "✓ Sim" : "✗ Não"}
              </span>
              {health.document && (
                <span>Documento: {health.document.name}</span>
              )}
              {health.stats && (
                <>
                  <span>
                    Operações: {health.stats.operations_success}/
                    {health.stats.operations_total}
                  </span>
                  <span>Reconexões: {health.stats.reconnections}</span>
                </>
              )}
            </div>
          )}

          <div style={{ display: "flex", gap: "8px", marginTop: "16px" }}>
            <button
              onClick={doConnect}
              disabled={!!loading}
              style={btnPrimary(loading === "connect")}
            >
              {loading === "connect" ? (
                <Loader2 size={16} className="animate-spin" />
              ) : (
                <Wifi size={16} />
              )}
              Conectar
            </button>
            <button
              onClick={doDisconnect}
              disabled={!!loading}
              style={btnDanger}
            >
              <WifiOff size={16} /> Desconectar
            </button>
          </div>
        </motion.div>

        {/* ── Mode Card ── */}
        <motion.div
          style={card()}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: 0.05 }}
        >
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "10px",
              marginBottom: "16px",
            }}
          >
            <Settings2 size={18} color={theme.accentPrimary} />
            <span style={{ ...labelStyle, marginBottom: 0 }}>
              MODO DE OPERAÇÃO
            </span>
          </div>

          <div style={{ display: "flex", gap: "8px", marginBottom: "16px" }}>
            <button
              onClick={() => doSetMode(false)}
              disabled={!!loading}
              style={{
                flex: 1,
                padding: "12px",
                borderRadius: "8px",
                border: `2px solid ${!isBridge ? theme.accentPrimary : theme.border}`,
                backgroundColor: !isBridge
                  ? `${theme.accentPrimary}15`
                  : "transparent",
                color: theme.textPrimary,
                cursor: "pointer",
                fontWeight: !isBridge ? 700 : 400,
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                gap: "6px",
                transition: "all 0.2s ease",
              }}
            >
              <Monitor
                size={22}
                color={!isBridge ? theme.accentPrimary : theme.textSecondary}
              />
              <span style={{ fontSize: "0.85rem" }}>COM Direto</span>
              <span style={{ fontSize: "0.65rem", color: theme.textTertiary }}>
                PC Local
              </span>
            </button>
            <button
              onClick={() => doSetMode(true)}
              disabled={!!loading}
              style={{
                flex: 1,
                padding: "12px",
                borderRadius: "8px",
                border: `2px solid ${isBridge ? theme.accentPrimary : theme.border}`,
                backgroundColor: isBridge
                  ? `${theme.accentPrimary}15`
                  : "transparent",
                color: theme.textPrimary,
                cursor: "pointer",
                fontWeight: isBridge ? 700 : 400,
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                gap: "6px",
                transition: "all 0.2s ease",
              }}
            >
              <Network
                size={22}
                color={isBridge ? theme.accentPrimary : theme.textSecondary}
              />
              <span style={{ fontSize: "0.85rem" }}>Modo Ponte</span>
              <span style={{ fontSize: "0.65rem", color: theme.textTertiary }}>
                Rede / Vigilante
              </span>
            </button>
          </div>

          {bufferStatus && isBridge && (
            <div style={{ fontSize: "0.8rem", color: theme.textSecondary }}>
              <span>Buffer: {bufferStatus.buffer_size} comandos</span>
              {bufferStatus.buffer_size > 0 && (
                <button
                  onClick={doCommit}
                  disabled={!!loading}
                  style={{
                    ...btnPrimary(loading === "commit"),
                    marginTop: "8px",
                    width: "100%",
                    justifyContent: "center",
                  }}
                >
                  {loading === "commit" ? (
                    <Loader2 size={14} className="animate-spin" />
                  ) : (
                    <Send size={14} />
                  )}
                  Commit → Vigilante
                </button>
              )}
            </div>
          )}
        </motion.div>

        {/* ── Bridge Path Config ── */}
        <motion.div
          style={card()}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: 0.1 }}
        >
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "10px",
              marginBottom: "16px",
            }}
          >
            <FolderSync size={18} color={theme.accentPrimary} />
            <span style={{ ...labelStyle, marginBottom: 0 }}>
              BRIDGE PATH (PASTA DE REDE)
            </span>
          </div>

          <div style={{ marginBottom: "12px" }}>
            <input
              type="text"
              value={bridgePath}
              onChange={(e) => setBridgePath(e.target.value)}
              placeholder="Ex: Z:/AutoCAD_Drop/ ou C:/AutoCAD_Drop/"
              style={inputStyle}
            />
          </div>

          <button
            onClick={doSetBridgePath}
            disabled={!!loading || !bridgePath.trim()}
            style={btnPrimary(loading === "bridge")}
          >
            {loading === "bridge" ? (
              <Loader2 size={14} className="animate-spin" />
            ) : (
              <FolderSync size={14} />
            )}
            Salvar Caminho
          </button>

          {bufferStatus && (
            <div
              style={{
                marginTop: "12px",
                padding: "8px 12px",
                borderRadius: "6px",
                backgroundColor: bufferStatus.bridge_accessible
                  ? `${theme.success}15`
                  : `${theme.warning}15`,
                border: `1px solid ${bufferStatus.bridge_accessible ? theme.success : theme.warning}44`,
                fontSize: "0.75rem",
                display: "flex",
                alignItems: "center",
                gap: "6px",
              }}
            >
              {bufferStatus.bridge_accessible ? (
                <>
                  <CheckCircle2 size={14} color={theme.success} />
                  <span style={{ color: theme.success }}>Pasta acessível</span>
                </>
              ) : (
                <>
                  <AlertTriangle size={14} color={theme.warning} />
                  <span style={{ color: theme.warning }}>
                    Pasta não encontrada
                  </span>
                </>
              )}
            </div>
          )}
        </motion.div>
      </div>

      {/* ═══════════ ROW 2: Quick Actions N-58 ═══════════ */}
      <motion.div
        style={{ ...card({ marginBottom: "20px" }) }}
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, delay: 0.15 }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "10px",
            marginBottom: "16px",
          }}
        >
          <Layers size={18} color={theme.accentPrimary} />
          <span style={{ ...labelStyle, marginBottom: 0 }}>
            AÇÕES RÁPIDAS — NORMA N-58
          </span>
        </div>

        <div style={{ display: "flex", gap: "12px", flexWrap: "wrap" }}>
          <button
            onClick={doCreateLayers}
            disabled={!!loading}
            style={quickBtn(theme.accentPrimary)}
            onMouseEnter={(e) => {
              e.currentTarget.style.transform = "translateY(-2px)";
              e.currentTarget.style.boxShadow = `0 4px 12px ${theme.accentPrimary}33`;
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.transform = "translateY(0)";
              e.currentTarget.style.boxShadow = "none";
            }}
          >
            <Layers size={24} color={theme.accentPrimary} />
            <span style={{ fontWeight: 600, fontSize: "0.85rem" }}>
              Criar Layers
            </span>
            <span style={{ fontSize: "0.7rem", color: theme.textTertiary }}>
              Sistema N-58
            </span>
          </button>

          <button
            onClick={() =>
              document
                .getElementById("pipe-form")
                ?.scrollIntoView({ behavior: "smooth" })
            }
            style={quickBtn(theme.success)}
            onMouseEnter={(e) => {
              e.currentTarget.style.transform = "translateY(-2px)";
              e.currentTarget.style.boxShadow = `0 4px 12px ${theme.success}33`;
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.transform = "translateY(0)";
              e.currentTarget.style.boxShadow = "none";
            }}
          >
            <Pipette size={24} color={theme.success} />
            <span style={{ fontWeight: 600, fontSize: "0.85rem" }}>
              Desenhar Tubo
            </span>
            <span style={{ fontSize: "0.7rem", color: theme.textTertiary }}>
              Tubulação 3D
            </span>
          </button>

          <button
            onClick={() => {
              setCompType("VALVE-GATE");
              setCompLayer("VALVE");
              document
                .getElementById("comp-form")
                ?.scrollIntoView({ behavior: "smooth" });
            }}
            style={quickBtn(theme.warning)}
            onMouseEnter={(e) => {
              e.currentTarget.style.transform = "translateY(-2px)";
              e.currentTarget.style.boxShadow = `0 4px 12px ${theme.warning}33`;
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.transform = "translateY(0)";
              e.currentTarget.style.boxShadow = "none";
            }}
          >
            <CircleDot size={24} color={theme.warning} />
            <span style={{ fontWeight: 600, fontSize: "0.85rem" }}>
              Inserir Válvula
            </span>
            <span style={{ fontSize: "0.7rem", color: theme.textTertiary }}>
              VALVE-GATE
            </span>
          </button>

          <button
            onClick={() => {
              setCompType("FLANGE-WN");
              setCompLayer("FLANGE");
              document
                .getElementById("comp-form")
                ?.scrollIntoView({ behavior: "smooth" });
            }}
            style={quickBtn(theme.danger)}
            onMouseEnter={(e) => {
              e.currentTarget.style.transform = "translateY(-2px)";
              e.currentTarget.style.boxShadow = `0 4px 12px ${theme.danger}33`;
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.transform = "translateY(0)";
              e.currentTarget.style.boxShadow = "none";
            }}
          >
            <Hexagon size={24} color={theme.danger} />
            <span style={{ fontWeight: 600, fontSize: "0.85rem" }}>
              Inserir Flange
            </span>
            <span style={{ fontSize: "0.7rem", color: theme.textTertiary }}>
              FLANGE-WN
            </span>
          </button>

          <button
            onClick={() =>
              document
                .getElementById("text-form")
                ?.scrollIntoView({ behavior: "smooth" })
            }
            style={quickBtn(theme.accentSecondary)}
            onMouseEnter={(e) => {
              e.currentTarget.style.transform = "translateY(-2px)";
              e.currentTarget.style.boxShadow = `0 4px 12px ${theme.accentSecondary}33`;
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.transform = "translateY(0)";
              e.currentTarget.style.boxShadow = "none";
            }}
          >
            <Type size={24} color={theme.accentSecondary} />
            <span style={{ fontWeight: 600, fontSize: "0.85rem" }}>
              Adicionar Texto
            </span>
            <span style={{ fontSize: "0.7rem", color: theme.textTertiary }}>
              Anotação
            </span>
          </button>

          <button
            onClick={doFinalize}
            disabled={!!loading}
            style={quickBtn(theme.accentPrimary)}
            onMouseEnter={(e) => {
              e.currentTarget.style.transform = "translateY(-2px)";
              e.currentTarget.style.boxShadow = `0 4px 12px ${theme.accentPrimary}33`;
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.transform = "translateY(0)";
              e.currentTarget.style.boxShadow = "none";
            }}
          >
            <ZoomIn size={24} color={theme.accentPrimary} />
            <span style={{ fontWeight: 600, fontSize: "0.85rem" }}>
              Finalizar Vista
            </span>
            <span style={{ fontSize: "0.7rem", color: theme.textTertiary }}>
              Zoom + Regen
            </span>
          </button>

          <button
            onClick={doSave}
            disabled={!!loading}
            style={quickBtn(theme.accentSecondary)}
            onMouseEnter={(e) => {
              e.currentTarget.style.transform = "translateY(-2px)";
              e.currentTarget.style.boxShadow = `0 4px 12px ${theme.accentSecondary}33`;
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.transform = "translateY(0)";
              e.currentTarget.style.boxShadow = "none";
            }}
          >
            <Save size={24} color={theme.accentSecondary} />
            <span style={{ fontWeight: 600, fontSize: "0.85rem" }}>Salvar</span>
            <span style={{ fontSize: "0.7rem", color: theme.textTertiary }}>
              Documento
            </span>
          </button>
        </div>
      </motion.div>

      {/* ═══════════ ROW 3: Forms (Pipe + Component) ═══════════ */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: "16px",
          marginBottom: "20px",
        }}
      >
        {/* ── Draw Pipe Form ── */}
        <motion.div
          id="pipe-form"
          style={card()}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: 0.2 }}
        >
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "10px",
              marginBottom: "20px",
            }}
          >
            <Pipette size={18} color={theme.success} />
            <span style={{ fontSize: "1rem", fontWeight: 600 }}>
              Desenhar Tubulação
            </span>
          </div>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: "12px",
            }}
          >
            {/* Start Point */}
            <div style={{ gridColumn: "span 2" }}>
              <span style={labelStyle}>Ponto Inicial (X, Y, Z)</span>
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "1fr 1fr 1fr",
                  gap: "6px",
                }}
              >
                <input
                  type="number"
                  value={pipeStartX}
                  onChange={(e) => setPipeStartX(e.target.value)}
                  placeholder="X"
                  style={inputStyle}
                />
                <input
                  type="number"
                  value={pipeStartY}
                  onChange={(e) => setPipeStartY(e.target.value)}
                  placeholder="Y"
                  style={inputStyle}
                />
                <input
                  type="number"
                  value={pipeStartZ}
                  onChange={(e) => setPipeStartZ(e.target.value)}
                  placeholder="Z"
                  style={inputStyle}
                />
              </div>
            </div>

            {/* End Point */}
            <div style={{ gridColumn: "span 2" }}>
              <span style={labelStyle}>Ponto Final (X, Y, Z)</span>
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "1fr 1fr 1fr",
                  gap: "6px",
                }}
              >
                <input
                  type="number"
                  value={pipeEndX}
                  onChange={(e) => setPipeEndX(e.target.value)}
                  placeholder="X"
                  style={inputStyle}
                />
                <input
                  type="number"
                  value={pipeEndY}
                  onChange={(e) => setPipeEndY(e.target.value)}
                  placeholder="Y"
                  style={inputStyle}
                />
                <input
                  type="number"
                  value={pipeEndZ}
                  onChange={(e) => setPipeEndZ(e.target.value)}
                  placeholder="Z"
                  style={inputStyle}
                />
              </div>
            </div>

            {/* Diameter */}
            <div>
              <span style={labelStyle}>Diâmetro (pol)</span>
              <select
                value={pipeDiameter}
                onChange={(e) => setPipeDiameter(e.target.value)}
                style={inputStyle}
              >
                <option value="2">2" (DN50)</option>
                <option value="3">3" (DN80)</option>
                <option value="4">4" (DN100)</option>
                <option value="6">6" (DN150)</option>
                <option value="8">8" (DN200)</option>
                <option value="10">10" (DN250)</option>
                <option value="12">12" (DN300)</option>
                <option value="16">16" (DN400)</option>
                <option value="20">20" (DN500)</option>
                <option value="24">24" (DN600)</option>
              </select>
            </div>

            {/* Layer */}
            <div>
              <span style={labelStyle}>Layer</span>
              <select
                value={pipeLayer}
                onChange={(e) => setPipeLayer(e.target.value)}
                style={inputStyle}
              >
                <option value="PIPE-PROCESS">PIPE-PROCESS</option>
                <option value="PIPE-UTILITY">PIPE-UTILITY</option>
                <option value="PIPE-DRAIN">PIPE-DRAIN</option>
                <option value="PIPE-VENT">PIPE-VENT</option>
                <option value="PIPE-STEAM">PIPE-STEAM</option>
              </select>
            </div>
          </div>

          <button
            onClick={doDrawPipe}
            disabled={!!loading}
            style={{
              ...btnPrimary(loading === "pipe"),
              marginTop: "16px",
              width: "100%",
              justifyContent: "center",
            }}
          >
            {loading === "pipe" ? (
              <Loader2 size={16} className="animate-spin" />
            ) : (
              <Minus size={16} />
            )}
            Desenhar Tubo
          </button>
        </motion.div>

        {/* ── Insert Component Form ── */}
        <motion.div
          id="comp-form"
          style={card()}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: 0.25 }}
        >
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "10px",
              marginBottom: "20px",
            }}
          >
            <CircleDot size={18} color={theme.warning} />
            <span style={{ fontSize: "1rem", fontWeight: 600 }}>
              Inserir Componente
            </span>
          </div>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: "12px",
            }}
          >
            {/* Component Type */}
            <div style={{ gridColumn: "span 2" }}>
              <span style={labelStyle}>Tipo de Componente</span>
              <select
                value={compType}
                onChange={(e) => setCompType(e.target.value)}
                style={inputStyle}
              >
                <optgroup label="Válvulas">
                  <option value="VALVE-GATE">Válvula Gaveta (Gate)</option>
                  <option value="VALVE-GLOBE">Válvula Globo (Globe)</option>
                  <option value="VALVE-BALL">Válvula Esfera (Ball)</option>
                  <option value="VALVE-CHECK">Válvula Retenção (Check)</option>
                  <option value="VALVE-BUTTERFLY">
                    Válvula Borboleta (Butterfly)
                  </option>
                </optgroup>
                <optgroup label="Flanges">
                  <option value="FLANGE-WN">Flange Pescoço (Weld Neck)</option>
                  <option value="FLANGE-SO">Flange Sobreposto (Slip-On)</option>
                  <option value="FLANGE-BL">Flange Cego (Blind)</option>
                </optgroup>
                <optgroup label="Conexões">
                  <option value="ELBOW-90">Cotovelo 90°</option>
                  <option value="ELBOW-45">Cotovelo 45°</option>
                  <option value="TEE">Tê</option>
                  <option value="REDUCER">Redução</option>
                </optgroup>
              </select>
            </div>

            {/* Coordinate */}
            <div style={{ gridColumn: "span 2" }}>
              <span style={labelStyle}>Coordenada (X, Y, Z)</span>
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "1fr 1fr 1fr",
                  gap: "6px",
                }}
              >
                <input
                  type="number"
                  value={compX}
                  onChange={(e) => setCompX(e.target.value)}
                  placeholder="X"
                  style={inputStyle}
                />
                <input
                  type="number"
                  value={compY}
                  onChange={(e) => setCompY(e.target.value)}
                  placeholder="Y"
                  style={inputStyle}
                />
                <input
                  type="number"
                  value={compZ}
                  onChange={(e) => setCompZ(e.target.value)}
                  placeholder="Z"
                  style={inputStyle}
                />
              </div>
            </div>

            {/* Rotation */}
            <div>
              <span style={labelStyle}>Rotação (°)</span>
              <input
                type="number"
                value={compRotation}
                onChange={(e) => setCompRotation(e.target.value)}
                min="0"
                max="359"
                style={inputStyle}
              />
            </div>

            {/* Scale */}
            <div>
              <span style={labelStyle}>Escala</span>
              <input
                type="number"
                value={compScale}
                onChange={(e) => setCompScale(e.target.value)}
                min="0.1"
                max="100"
                step="0.1"
                style={inputStyle}
              />
            </div>

            {/* Layer */}
            <div style={{ gridColumn: "span 2" }}>
              <span style={labelStyle}>Layer</span>
              <select
                value={compLayer}
                onChange={(e) => setCompLayer(e.target.value)}
                style={inputStyle}
              >
                <option value="VALVE">VALVE</option>
                <option value="FLANGE">FLANGE</option>
                <option value="FITTING">FITTING</option>
                <option value="INSTRUMENT">INSTRUMENT</option>
                <option value="SUPPORT">SUPPORT</option>
              </select>
            </div>
          </div>

          <button
            onClick={doInsertComponent}
            disabled={!!loading}
            style={{
              ...btnPrimary(loading === "component"),
              marginTop: "16px",
              width: "100%",
              justifyContent: "center",
            }}
          >
            {loading === "component" ? (
              <Loader2 size={16} className="animate-spin" />
            ) : (
              <CircleDot size={16} />
            )}
            Inserir {compType.split("-")[0]}
          </button>
        </motion.div>
      </div>

      {/* ═══════════ ROW 4: Text Form + Command Log ═══════════ */}
      <div
        style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}
      >
        {/* ── Add Text Form ── */}
        <motion.div
          id="text-form"
          style={card()}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: 0.3 }}
        >
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "10px",
              marginBottom: "20px",
            }}
          >
            <Type size={18} color={theme.accentSecondary} />
            <span style={{ fontSize: "1rem", fontWeight: 600 }}>
              Adicionar Texto / Anotação
            </span>
          </div>

          <div style={{ display: "grid", gap: "12px" }}>
            <div>
              <span style={labelStyle}>Texto</span>
              <input
                type="text"
                value={textContent}
                onChange={(e) => setTextContent(e.target.value)}
                placeholder='Ex: "L-350-002-HC-6" ou "TAG-V-001"'
                style={inputStyle}
              />
            </div>

            <div>
              <span style={labelStyle}>Posição (X, Y, Z)</span>
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "1fr 1fr 1fr",
                  gap: "6px",
                }}
              >
                <input
                  type="number"
                  value={textX}
                  onChange={(e) => setTextX(e.target.value)}
                  placeholder="X"
                  style={inputStyle}
                />
                <input
                  type="number"
                  value={textY}
                  onChange={(e) => setTextY(e.target.value)}
                  placeholder="Y"
                  style={inputStyle}
                />
                <input
                  type="number"
                  value={textZ}
                  onChange={(e) => setTextZ(e.target.value)}
                  placeholder="Z"
                  style={inputStyle}
                />
              </div>
            </div>

            <div>
              <span style={labelStyle}>Altura do Texto</span>
              <input
                type="number"
                value={textHeight}
                onChange={(e) => setTextHeight(e.target.value)}
                min="0.1"
                max="100"
                step="0.5"
                style={inputStyle}
              />
            </div>
          </div>

          <button
            onClick={doAddText}
            disabled={!!loading || !textContent.trim()}
            style={{
              ...btnPrimary(loading === "text"),
              marginTop: "16px",
              width: "100%",
              justifyContent: "center",
            }}
          >
            {loading === "text" ? (
              <Loader2 size={16} className="animate-spin" />
            ) : (
              <Type size={16} />
            )}
            Adicionar Texto
          </button>
        </motion.div>

        {/* ── Command Log ── */}
        <motion.div
          style={card({
            maxHeight: "380px",
            display: "flex",
            flexDirection: "column",
          })}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: 0.35 }}
        >
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              marginBottom: "12px",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
              <Activity size={18} color={theme.accentPrimary} />
              <span style={{ fontSize: "1rem", fontWeight: 600 }}>
                Log de Comandos
              </span>
            </div>
            <button
              onClick={() => setLogs([])}
              style={{
                ...btnSecondary,
                padding: "4px 10px",
                fontSize: "0.7rem",
              }}
            >
              Limpar
            </button>
          </div>

          <div
            style={{
              flex: 1,
              overflowY: "auto",
              backgroundColor: theme.codeBackground,
              borderRadius: "8px",
              padding: "12px",
              fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
              fontSize: "0.75rem",
            }}
          >
            {logs.length === 0 ? (
              <div
                style={{
                  color: theme.textTertiary,
                  textAlign: "center",
                  paddingTop: "40px",
                }}
              >
                Nenhum comando executado ainda.
              </div>
            ) : (
              <AnimatePresence>
                {logs.map((log) => (
                  <motion.div
                    key={log.id}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    style={{
                      display: "flex",
                      alignItems: "flex-start",
                      gap: "8px",
                      marginBottom: "6px",
                      paddingBottom: "6px",
                      borderBottom: `1px solid ${theme.border}33`,
                    }}
                  >
                    {log.status === "success" && (
                      <CheckCircle2
                        size={14}
                        color={theme.success}
                        style={{ marginTop: "2px", flexShrink: 0 }}
                      />
                    )}
                    {log.status === "error" && (
                      <XCircle
                        size={14}
                        color={theme.danger}
                        style={{ marginTop: "2px", flexShrink: 0 }}
                      />
                    )}
                    {log.status === "pending" && (
                      <Loader2
                        size={14}
                        color={theme.warning}
                        style={{ marginTop: "2px", flexShrink: 0 }}
                      />
                    )}
                    <span style={{ color: theme.textTertiary, flexShrink: 0 }}>
                      {log.timestamp}
                    </span>
                    <span style={{ fontWeight: 600, color: theme.textPrimary }}>
                      {log.operation}
                    </span>
                    <span
                      style={{
                        color:
                          log.status === "error"
                            ? theme.danger
                            : theme.textSecondary,
                      }}
                    >
                      {log.message}
                    </span>
                  </motion.div>
                ))}
              </AnimatePresence>
            )}
            <div ref={logEndRef} />
          </div>
        </motion.div>
      </div>
    </div>
  );
};

export default CadDashboard;
