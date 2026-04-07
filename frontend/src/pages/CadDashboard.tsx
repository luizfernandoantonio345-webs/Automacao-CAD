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
  Zap,
  Box,
  PenTool,
  Move3D,
  RotateCw,
  Maximize2,
  Grid3X3,
  Cpu,
  Server,
  CloudLightning,
  Terminal,
  Code,
} from "lucide-react";

// ═══════════════════════════════════════════════════════════════════════════
// Types
// ═══════════════════════════════════════════════════════════════════════════

type ConnectionMode = "auto" | "simulation" | "local";

interface CommandLog {
  id: string;
  timestamp: string;
  operation: string;
  status: "success" | "error" | "pending" | "simulated";
  message: string;
}

// ═══════════════════════════════════════════════════════════════════════════
// CadDashboard — Painel de Controle CAD Avançado
// ═══════════════════════════════════════════════════════════════════════════

const CadDashboard: React.FC = () => {
  const { theme } = useTheme();

  // ── Connection State ──
  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [connectionMode, setConnectionMode] = useState<ConnectionMode>("auto");
  const [cadInfo, setCadInfo] = useState<{
    type: string;
    version: string;
    document?: string;
  } | null>(null);

  // ── Operation State ──
  const [logs, setLogs] = useState<CommandLog[]>([]);
  const [loading, setLoading] = useState<string | null>(null);
  const [stats, setStats] = useState({ operations: 0, success: 0, errors: 0 });

  // ── Draw Pipe Form ──
  const [pipeStartX, setPipeStartX] = useState("0");
  const [pipeStartY, setPipeStartY] = useState("0");
  const [pipeEndX, setPipeEndX] = useState("1000");
  const [pipeEndY, setPipeEndY] = useState("0");
  const [pipeDiameter, setPipeDiameter] = useState("6");
  const [pipeLayer, setPipeLayer] = useState("PIPE-PROCESS");

  // ── Component Form ──
  const [compType, setCompType] = useState("VALVE-GATE");
  const [compX, setCompX] = useState("500");
  const [compY, setCompY] = useState("0");
  const [compScale, setCompScale] = useState("1");

  // ── Text Form ──
  const [textContent, setTextContent] = useState("");
  const [textX, setTextX] = useState("0");
  const [textY, setTextY] = useState("0");
  const [textHeight, setTextHeight] = useState("2.5");

  const logEndRef = useRef<HTMLDivElement>(null);
  const wsRef = useRef<WebSocket | null>(null);

  // ═══════════════════════════════════════════════════════════════════════
  // HELPERS
  // ═══════════════════════════════════════════════════════════════════════

  const addLog = useCallback(
    (
      operation: string,
      status: "success" | "error" | "pending" | "simulated",
      message: string
    ) => {
      const entry: CommandLog = {
        id: `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
        timestamp: new Date().toLocaleTimeString("pt-BR"),
        operation,
        status,
        message,
      };
      setLogs((prev) => [...prev.slice(-99), entry]);
      
      if (status === "success" || status === "simulated") {
        setStats(s => ({ ...s, operations: s.operations + 1, success: s.success + 1 }));
      } else if (status === "error") {
        setStats(s => ({ ...s, operations: s.operations + 1, errors: s.errors + 1 }));
      }
    },
    []
  );

  // ═══════════════════════════════════════════════════════════════════════
  // AUTO-CONNECT (WebSocket + API Hybrid)
  // ═══════════════════════════════════════════════════════════════════════

  const doConnect = useCallback(async () => {
    if (isConnecting || isConnected) return;
    
    setIsConnecting(true);
    addLog("Conexão", "pending", "Conectando ao sistema CAD...");

    try {
      // Tentar conectar via API primeiro
      const health = await ApiService.autocadHealth();
      
      if (health?.driver_status === "Connected" || health?.com_available) {
        // CAD real detectado
        setIsConnected(true);
        setCadInfo({
          type: health.engine || "AutoCAD",
          version: "2024",
          document: health.document?.name,
        });
        setConnectionMode("local");
        addLog("Conexão", "success", `✓ Conectado ao ${health.engine || "AutoCAD"}`);
      } else {
        // Sem CAD disponível - modo simulação automático
        setIsConnected(true);
        setCadInfo({
          type: "Simulador CAD",
          version: "1.0",
          document: "Documento Virtual",
        });
        setConnectionMode("simulation");
        addLog("Conexão", "simulated", "✓ Conectado em modo Simulação (sem AutoCAD detectado)");
      }
    } catch (error) {
      // Fallback para modo simulação
      setIsConnected(true);
      setCadInfo({
        type: "Simulador CAD",
        version: "1.0",
        document: "Documento Virtual",
      });
      setConnectionMode("simulation");
      addLog("Conexão", "simulated", "✓ Modo Simulação ativo (backend offline)");
    } finally {
      setIsConnecting(false);
    }
  }, [isConnecting, isConnected, addLog]);

  const doDisconnect = useCallback(() => {
    setIsConnected(false);
    setCadInfo(null);
    setConnectionMode("auto");
    addLog("Desconexão", "success", "Desconectado do sistema CAD");
  }, [addLog]);

  // Auto-conectar ao montar
  useEffect(() => {
    const timer = setTimeout(() => {
      doConnect();
    }, 500);
    return () => clearTimeout(timer);
  }, []);

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  // ═══════════════════════════════════════════════════════════════════════
  // CAD OPERATIONS
  // ═══════════════════════════════════════════════════════════════════════

  const executeCommand = useCallback(
    async (
      name: string,
      apiCall: () => Promise<DriverResult>,
      simulatedResult?: string
    ) => {
      if (!isConnected) {
        addLog(name, "error", "Não conectado");
        return;
      }

      setLoading(name);
      addLog(name, "pending", "Executando...");

      try {
        if (connectionMode === "simulation") {
          // Simular delay realista
          await new Promise((r) => setTimeout(r, 300 + Math.random() * 500));
          addLog(name, "simulated", simulatedResult || "✓ Simulado com sucesso");
        } else {
          const result = await apiCall();
          if (result.success) {
            addLog(name, "success", result.message || "✓ OK");
          } else {
            addLog(name, "error", result.message || "Falhou");
          }
        }
      } catch (error: any) {
        addLog(name, "error", error?.message || "Erro de execução");
      } finally {
        setLoading(null);
      }
    },
    [isConnected, connectionMode, addLog]
  );

  const doCreateLayers = () =>
    executeCommand("Criar Layers N-58", () => ApiService.autocadCreateLayers(), "12 layers Petrobras N-58 criados");

  const doDrawPipe = () =>
    executeCommand(
      "Desenhar Tubo",
      () =>
        ApiService.autocadDrawPipe({
          points: [
            [parseFloat(pipeStartX), parseFloat(pipeStartY), 0],
            [parseFloat(pipeEndX), parseFloat(pipeEndY), 0],
          ],
          diameter: parseFloat(pipeDiameter),
          layer: pipeLayer,
        }),
      `Tubo Ø${pipeDiameter}" desenhado (${pipeStartX},${pipeStartY}) → (${pipeEndX},${pipeEndY})`
    );

  const doInsertComponent = () =>
    executeCommand(
      `Inserir ${compType}`,
      () =>
        ApiService.autocadInsertComponent({
          block_name: compType,
          coordinate: [parseFloat(compX), parseFloat(compY), 0],
          rotation: 0,
          scale: parseFloat(compScale),
          layer: "VALVE",
        }),
      `${compType} inserido em (${compX}, ${compY})`
    );

  const doAddText = () => {
    if (!textContent.trim()) return;
    executeCommand(
      "Adicionar Texto",
      () =>
        ApiService.autocadAddText({
          text: textContent.trim(),
          position: [parseFloat(textX), parseFloat(textY), 0],
          height: parseFloat(textHeight),
          layer: "ANNOTATION",
        }),
      `Texto "${textContent}" adicionado`
    );
  };

  const doSave = () =>
    executeCommand("Salvar", () => ApiService.autocadSave(), "Documento salvo");

  const doFinalize = () =>
    executeCommand("Finalizar Vista", () => ApiService.autocadFinalize(), "Vista zoom extents aplicada");

  // ═══════════════════════════════════════════════════════════════════════
  // STYLES
  // ═══════════════════════════════════════════════════════════════════════

  const colors = {
    primary: "#00A1FF",
    success: "#10B981",
    warning: "#F59E0B",
    danger: "#EF4444",
    purple: "#8B5CF6",
    gradient: "linear-gradient(135deg, #00A1FF 0%, #0077CC 100%)",
  };

  const card = (extra?: React.CSSProperties): React.CSSProperties => ({
    background: `linear-gradient(180deg, ${theme.surface}ee 0%, ${theme.surface}dd 100%)`,
    backdropFilter: "blur(20px)",
    border: `1px solid ${theme.border}`,
    borderRadius: "16px",
    padding: "24px",
    boxShadow: "0 4px 24px rgba(0,0,0,0.15)",
    ...extra,
  });

  const glowCard = (color: string): React.CSSProperties => ({
    ...card(),
    border: `1px solid ${color}40`,
    boxShadow: `0 0 40px ${color}15, 0 4px 24px rgba(0,0,0,0.15)`,
  });

  const inputStyle: React.CSSProperties = {
    backgroundColor: `${theme.inputBackground}cc`,
    border: `1px solid ${theme.inputBorder}`,
    borderRadius: "10px",
    padding: "12px 16px",
    color: theme.textPrimary,
    fontSize: "0.9rem",
    width: "100%",
    outline: "none",
    transition: "all 0.2s ease",
  };

  const labelStyle: React.CSSProperties = {
    fontSize: "0.7rem",
    color: theme.textSecondary,
    fontWeight: 700,
    textTransform: "uppercase",
    letterSpacing: "1.2px",
    marginBottom: "8px",
    display: "block",
  };

  const btnPrimary = (isLoading?: boolean): React.CSSProperties => ({
    background: isLoading ? theme.textTertiary : colors.gradient,
    color: "#FFFFFF",
    border: "none",
    borderRadius: "12px",
    padding: "14px 24px",
    fontWeight: 700,
    cursor: isLoading ? "not-allowed" : "pointer",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    gap: "10px",
    fontSize: "0.9rem",
    transition: "all 0.3s ease",
    opacity: isLoading ? 0.7 : 1,
    boxShadow: isLoading ? "none" : `0 4px 20px ${colors.primary}40`,
  });

  const btnSecondary: React.CSSProperties = {
    backgroundColor: "transparent",
    color: theme.textPrimary,
    border: `2px solid ${theme.border}`,
    borderRadius: "12px",
    padding: "12px 20px",
    fontWeight: 600,
    cursor: "pointer",
    display: "flex",
    alignItems: "center",
    gap: "8px",
    fontSize: "0.85rem",
    transition: "all 0.3s ease",
  };

  const btnDanger: React.CSSProperties = {
    background: `linear-gradient(135deg, ${colors.danger} 0%, #DC2626 100%)`,
    color: "#FFFFFF",
    border: "none",
    borderRadius: "12px",
    padding: "12px 20px",
    fontWeight: 600,
    cursor: "pointer",
    display: "flex",
    alignItems: "center",
    gap: "8px",
    fontSize: "0.85rem",
    boxShadow: `0 4px 20px ${colors.danger}30`,
  };

  const quickActionBtn = (
    color: string,
    active?: boolean
  ): React.CSSProperties => ({
    background: active
      ? `linear-gradient(135deg, ${color}30 0%, ${color}15 100%)`
      : `${theme.surface}80`,
    border: `2px solid ${active ? color : theme.border}`,
    borderRadius: "16px",
    padding: "20px",
    cursor: "pointer",
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    gap: "12px",
    color: theme.textPrimary,
    transition: "all 0.3s ease",
    minWidth: "140px",
    boxShadow: active ? `0 0 30px ${color}20` : "none",
  });

  const statusBadge = (
    status: "connected" | "simulated" | "disconnected"
  ): React.CSSProperties => {
    const statusColors = {
      connected: colors.success,
      simulated: colors.warning,
      disconnected: colors.danger,
    };
    const color = statusColors[status];
    return {
      display: "inline-flex",
      alignItems: "center",
      gap: "8px",
      padding: "8px 16px",
      borderRadius: "20px",
      fontSize: "0.8rem",
      fontWeight: 700,
      backgroundColor: `${color}15`,
      border: `1px solid ${color}40`,
      color: color,
    };
  };

  // ═══════════════════════════════════════════════════════════════════════
  // RENDER
  // ═══════════════════════════════════════════════════════════════════════

  const connectionStatus = isConnected
    ? connectionMode === "simulation"
      ? "simulated"
      : "connected"
    : "disconnected";

  return (
    <div
      style={{
        padding: "32px",
        background: `linear-gradient(180deg, ${theme.background} 0%, ${theme.background}ee 100%)`,
        minHeight: "100vh",
        color: theme.textPrimary,
      }}
    >
      {/* ═══════════════════════════════════════════════════════════════════
          HEADER
      ═══════════════════════════════════════════════════════════════════ */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          marginBottom: "32px",
        }}
      >
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "16px", marginBottom: "8px" }}>
            <div
              style={{
                width: "48px",
                height: "48px",
                borderRadius: "14px",
                background: colors.gradient,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                boxShadow: `0 4px 20px ${colors.primary}40`,
              }}
            >
              <Layers size={26} color="#FFF" />
            </div>
            <div>
              <h1
                style={{
                  margin: 0,
                  fontSize: "2rem",
                  fontWeight: 800,
                  letterSpacing: "-0.5px",
                  background: `linear-gradient(90deg, ${theme.textPrimary} 0%, ${colors.primary} 100%)`,
                  WebkitBackgroundClip: "text",
                  WebkitTextFillColor: "transparent",
                }}
              >
                PAINEL CAD
              </h1>
              <p
                style={{
                  margin: 0,
                  fontSize: "0.85rem",
                  color: theme.textSecondary,
                  letterSpacing: "2px",
                  textTransform: "uppercase",
                }}
              >
                Automação Industrial N-58
              </p>
            </div>
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
          <div style={statusBadge(connectionStatus)}>
            <div
              style={{
                width: "8px",
                height: "8px",
                borderRadius: "50%",
                backgroundColor: "currentColor",
                boxShadow: `0 0 10px currentColor`,
                animation: isConnected ? "pulse 2s infinite" : "none",
              }}
            />
            {connectionStatus === "connected"
              ? "CAD Conectado"
              : connectionStatus === "simulated"
              ? "Modo Simulação"
              : "Desconectado"}
          </div>

          {isConnected ? (
            <button onClick={doDisconnect} style={btnDanger}>
              <WifiOff size={18} /> Desconectar
            </button>
          ) : (
            <button
              onClick={doConnect}
              disabled={isConnecting}
              style={btnPrimary(isConnecting)}
            >
              {isConnecting ? (
                <Loader2 size={18} className="animate-spin" />
              ) : (
                <Zap size={18} />
              )}
              Conectar
            </button>
          )}
        </div>
      </motion.div>

      {/* ═══════════════════════════════════════════════════════════════════
          STATUS CARDS ROW
      ═══════════════════════════════════════════════════════════════════ */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
          gap: "20px",
          marginBottom: "28px",
          maxWidth: "100%",
        }}
      >
        {/* Status Card */}
        <motion.div
          style={glowCard(isConnected ? colors.success : colors.danger)}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "12px", marginBottom: "16px" }}>
            <Server size={20} color={isConnected ? colors.success : colors.danger} />
            <span style={{ ...labelStyle, marginBottom: 0 }}>STATUS</span>
          </div>
          <div style={{ fontSize: "1.5rem", fontWeight: 800, marginBottom: "4px" }}>
            {isConnected ? cadInfo?.type : "Offline"}
          </div>
          <div style={{ fontSize: "0.8rem", color: theme.textSecondary }}>
            {cadInfo?.document || "Nenhum documento"}
          </div>
        </motion.div>

        {/* Operations Card */}
        <motion.div
          style={glowCard(colors.primary)}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.15 }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "12px", marginBottom: "16px" }}>
            <Activity size={20} color={colors.primary} />
            <span style={{ ...labelStyle, marginBottom: 0 }}>OPERAÇÕES</span>
          </div>
          <div style={{ fontSize: "2.5rem", fontWeight: 800, color: colors.primary }}>
            {stats.operations}
          </div>
          <div style={{ fontSize: "0.8rem", color: theme.textSecondary }}>
            Total executadas
          </div>
        </motion.div>

        {/* Success Card */}
        <motion.div
          style={glowCard(colors.success)}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "12px", marginBottom: "16px" }}>
            <CheckCircle2 size={20} color={colors.success} />
            <span style={{ ...labelStyle, marginBottom: 0 }}>SUCESSO</span>
          </div>
          <div style={{ fontSize: "2.5rem", fontWeight: 800, color: colors.success }}>
            {stats.success}
          </div>
          <div style={{ fontSize: "0.8rem", color: theme.textSecondary }}>
            Comandos OK
          </div>
        </motion.div>

        {/* Mode Card */}
        <motion.div
          style={glowCard(colors.purple)}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.25 }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "12px", marginBottom: "16px" }}>
            <Cpu size={20} color={colors.purple} />
            <span style={{ ...labelStyle, marginBottom: 0 }}>MODO</span>
          </div>
          <div style={{ fontSize: "1.3rem", fontWeight: 800 }}>
            {connectionMode === "simulation" ? "Simulação" : connectionMode === "local" ? "Local" : "Auto"}
          </div>
          <div style={{ fontSize: "0.8rem", color: theme.textSecondary }}>
            {connectionMode === "simulation" ? "Virtual" : "Direto"}
          </div>
        </motion.div>
      </div>

      {/* ═══════════════════════════════════════════════════════════════════
          QUICK ACTIONS
      ═══════════════════════════════════════════════════════════════════ */}
      <motion.div
        style={{ ...card({ marginBottom: "28px" }) }}
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3 }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "12px", marginBottom: "24px" }}>
          <CloudLightning size={22} color={colors.primary} />
          <span style={{ fontSize: "1rem", fontWeight: 700 }}>AÇÕES RÁPIDAS</span>
          <span
            style={{
              marginLeft: "auto",
              fontSize: "0.7rem",
              padding: "4px 12px",
              borderRadius: "20px",
              backgroundColor: `${colors.primary}15`,
              color: colors.primary,
              fontWeight: 600,
            }}
          >
            NORMA N-58 PETROBRAS
          </span>
        </div>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(100px, 1fr))",
            gap: "16px",
            maxWidth: "100%",
          }}
        >
          <button
            onClick={doCreateLayers}
            disabled={!isConnected || !!loading}
            style={quickActionBtn(colors.primary, loading === "Criar Layers N-58")}
          >
            {loading === "Criar Layers N-58" ? (
              <Loader2 size={28} className="animate-spin" color={colors.primary} />
            ) : (
              <Layers size={28} color={colors.primary} />
            )}
            <span style={{ fontSize: "0.8rem", fontWeight: 600 }}>Layers N-58</span>
          </button>

          <button
            onClick={doDrawPipe}
            disabled={!isConnected || !!loading}
            style={quickActionBtn(colors.success, loading === "Desenhar Tubo")}
          >
            {loading === "Desenhar Tubo" ? (
              <Loader2 size={28} className="animate-spin" color={colors.success} />
            ) : (
              <Pipette size={28} color={colors.success} />
            )}
            <span style={{ fontSize: "0.8rem", fontWeight: 600 }}>Tubo</span>
          </button>

          <button
            onClick={doInsertComponent}
            disabled={!isConnected || !!loading}
            style={quickActionBtn(colors.warning, loading?.includes("Inserir"))}
          >
            {loading?.includes("Inserir") ? (
              <Loader2 size={28} className="animate-spin" color={colors.warning} />
            ) : (
              <Hexagon size={28} color={colors.warning} />
            )}
            <span style={{ fontSize: "0.8rem", fontWeight: 600 }}>Componente</span>
          </button>

          <button
            onClick={doAddText}
            disabled={!isConnected || !!loading || !textContent.trim()}
            style={quickActionBtn(colors.purple, loading === "Adicionar Texto")}
          >
            {loading === "Adicionar Texto" ? (
              <Loader2 size={28} className="animate-spin" color={colors.purple} />
            ) : (
              <Type size={28} color={colors.purple} />
            )}
            <span style={{ fontSize: "0.8rem", fontWeight: 600 }}>Texto</span>
          </button>

          <button
            onClick={doFinalize}
            disabled={!isConnected || !!loading}
            style={quickActionBtn("#06B6D4", loading === "Finalizar Vista")}
          >
            {loading === "Finalizar Vista" ? (
              <Loader2 size={28} className="animate-spin" color="#06B6D4" />
            ) : (
              <Maximize2 size={28} color="#06B6D4" />
            )}
            <span style={{ fontSize: "0.8rem", fontWeight: 600 }}>Finalizar</span>
          </button>

          <button
            onClick={doSave}
            disabled={!isConnected || !!loading}
            style={quickActionBtn(colors.danger, loading === "Salvar")}
          >
            {loading === "Salvar" ? (
              <Loader2 size={28} className="animate-spin" color={colors.danger} />
            ) : (
              <Save size={28} color={colors.danger} />
            )}
            <span style={{ fontSize: "0.8rem", fontWeight: 600 }}>Salvar</span>
          </button>
        </div>
      </motion.div>

      {/* ═══════════════════════════════════════════════════════════════════
          FORMS ROW
      ═══════════════════════════════════════════════════════════════════ */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr 1fr",
          gap: "20px",
          marginBottom: "28px",
        }}
      >
        {/* Pipe Form */}
        <motion.div
          style={card()}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.35 }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "12px", marginBottom: "20px" }}>
            <Pipette size={20} color={colors.success} />
            <span style={{ fontSize: "1rem", fontWeight: 700 }}>Desenhar Tubo</span>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
            <div>
              <label style={labelStyle}>Início X</label>
              <input
                type="number"
                value={pipeStartX}
                onChange={(e) => setPipeStartX(e.target.value)}
                style={inputStyle}
              />
            </div>
            <div>
              <label style={labelStyle}>Início Y</label>
              <input
                type="number"
                value={pipeStartY}
                onChange={(e) => setPipeStartY(e.target.value)}
                style={inputStyle}
              />
            </div>
            <div>
              <label style={labelStyle}>Fim X</label>
              <input
                type="number"
                value={pipeEndX}
                onChange={(e) => setPipeEndX(e.target.value)}
                style={inputStyle}
              />
            </div>
            <div>
              <label style={labelStyle}>Fim Y</label>
              <input
                type="number"
                value={pipeEndY}
                onChange={(e) => setPipeEndY(e.target.value)}
                style={inputStyle}
              />
            </div>
            <div>
              <label style={labelStyle}>Diâmetro</label>
              <select
                value={pipeDiameter}
                onChange={(e) => setPipeDiameter(e.target.value)}
                style={inputStyle}
              >
                {["1", "2", "3", "4", "6", "8", "10", "12", "14", "16", "18", "20", "24"].map((d) => (
                  <option key={d} value={d}>
                    {d}"
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label style={labelStyle}>Layer</label>
              <select
                value={pipeLayer}
                onChange={(e) => setPipeLayer(e.target.value)}
                style={inputStyle}
              >
                {["PIPE-PROCESS", "PIPE-UTILITY", "PIPE-INSTRUMENT"].map((l) => (
                  <option key={l} value={l}>
                    {l}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </motion.div>

        {/* Component Form */}
        <motion.div
          style={card()}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "12px", marginBottom: "20px" }}>
            <Hexagon size={20} color={colors.warning} />
            <span style={{ fontSize: "1rem", fontWeight: 700 }}>Inserir Componente</span>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
            <div style={{ gridColumn: "1 / -1" }}>
              <label style={labelStyle}>Tipo</label>
              <select
                value={compType}
                onChange={(e) => setCompType(e.target.value)}
                style={inputStyle}
              >
                {[
                  "VALVE-GATE",
                  "VALVE-GLOBE",
                  "VALVE-CHECK",
                  "VALVE-BALL",
                  "VALVE-BUTTERFLY",
                  "ELBOW-90",
                  "ELBOW-45",
                  "TEE",
                  "REDUCER",
                  "FLANGE",
                  "BLIND",
                ].map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label style={labelStyle}>Posição X</label>
              <input
                type="number"
                value={compX}
                onChange={(e) => setCompX(e.target.value)}
                style={inputStyle}
              />
            </div>
            <div>
              <label style={labelStyle}>Posição Y</label>
              <input
                type="number"
                value={compY}
                onChange={(e) => setCompY(e.target.value)}
                style={inputStyle}
              />
            </div>
            <div style={{ gridColumn: "1 / -1" }}>
              <label style={labelStyle}>Escala</label>
              <input
                type="number"
                value={compScale}
                onChange={(e) => setCompScale(e.target.value)}
                style={inputStyle}
                step="0.1"
              />
            </div>
          </div>
        </motion.div>

        {/* Text Form */}
        <motion.div
          style={card()}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.45 }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "12px", marginBottom: "20px" }}>
            <Type size={20} color={colors.purple} />
            <span style={{ fontSize: "1rem", fontWeight: 700 }}>Adicionar Texto</span>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
            <div style={{ gridColumn: "1 / -1" }}>
              <label style={labelStyle}>Conteúdo</label>
              <input
                type="text"
                value={textContent}
                onChange={(e) => setTextContent(e.target.value)}
                placeholder="Digite o texto..."
                style={inputStyle}
              />
            </div>
            <div>
              <label style={labelStyle}>Posição X</label>
              <input
                type="number"
                value={textX}
                onChange={(e) => setTextX(e.target.value)}
                style={inputStyle}
              />
            </div>
            <div>
              <label style={labelStyle}>Posição Y</label>
              <input
                type="number"
                value={textY}
                onChange={(e) => setTextY(e.target.value)}
                style={inputStyle}
              />
            </div>
            <div style={{ gridColumn: "1 / -1" }}>
              <label style={labelStyle}>Altura</label>
              <input
                type="number"
                value={textHeight}
                onChange={(e) => setTextHeight(e.target.value)}
                style={inputStyle}
                step="0.5"
              />
            </div>
          </div>
        </motion.div>
      </div>

      {/* ═══════════════════════════════════════════════════════════════════
          LOGS
      ═══════════════════════════════════════════════════════════════════ */}
      <motion.div
        style={card()}
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.5 }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "12px", marginBottom: "20px" }}>
          <Terminal size={20} color={colors.primary} />
          <span style={{ fontSize: "1rem", fontWeight: 700 }}>Console de Operações</span>
          <span
            style={{
              marginLeft: "auto",
              fontSize: "0.7rem",
              padding: "4px 12px",
              borderRadius: "20px",
              backgroundColor: `${theme.textSecondary}15`,
              color: theme.textSecondary,
            }}
          >
            {logs.length} logs
          </span>
        </div>

        <div
          style={{
            backgroundColor: "#0D0D0D",
            borderRadius: "12px",
            padding: "16px",
            maxHeight: "300px",
            overflowY: "auto",
            fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
            fontSize: "0.8rem",
          }}
        >
          <AnimatePresence>
            {logs.length === 0 ? (
              <div style={{ color: "#666", textAlign: "center", padding: "20px" }}>
                <Code size={32} style={{ marginBottom: "8px", opacity: 0.5 }} />
                <div>Nenhuma operação executada ainda</div>
                <div style={{ fontSize: "0.7rem", marginTop: "4px" }}>
                  Clique em "Conectar" para começar
                </div>
              </div>
            ) : (
              logs.map((log) => (
                <motion.div
                  key={log.id}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0 }}
                  style={{
                    display: "flex",
                    alignItems: "flex-start",
                    gap: "12px",
                    padding: "8px 0",
                    borderBottom: "1px solid #1a1a1a",
                  }}
                >
                  <span style={{ color: "#666", minWidth: "70px" }}>{log.timestamp}</span>
                  <span
                    style={{
                      color:
                        log.status === "success"
                          ? colors.success
                          : log.status === "simulated"
                          ? colors.warning
                          : log.status === "error"
                          ? colors.danger
                          : colors.primary,
                      minWidth: "20px",
                    }}
                  >
                    {log.status === "success"
                      ? "✓"
                      : log.status === "simulated"
                      ? "◉"
                      : log.status === "error"
                      ? "✗"
                      : "○"}
                  </span>
                  <span style={{ color: "#AAA", fontWeight: 600 }}>[{log.operation}]</span>
                  <span style={{ color: "#DDD" }}>{log.message}</span>
                </motion.div>
              ))
            )}
          </AnimatePresence>
          <div ref={logEndRef} />
        </div>
      </motion.div>

      {/* CSS Animations */}
      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.5; }
        }
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        .animate-spin {
          animation: spin 1s linear infinite;
        }
      `}</style>
    </div>
  );
};

export default CadDashboard;
