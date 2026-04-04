/**
 * ═══════════════════════════════════════════════════════════════════════════════
 * CncMachineIntegration - Interface de Integração com CNCs
 * ═══════════════════════════════════════════════════════════════════════════════
 *
 * Melhoria #6: Comunicação com máquinas CNC
 * - Cadastro de múltiplas máquinas
 * - Status em tempo real via polling/WebSocket
 * - Envio direto de G-Code
 * - Queue de jobs por máquina
 */

import React, { useState, useEffect, useCallback, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Server,
  Wifi,
  WifiOff,
  Play,
  Pause,
  Square,
  Send,
  RefreshCw,
  Settings,
  Plus,
  Edit3,
  Trash2,
  AlertTriangle,
  CheckCircle,
  Clock,
  FileCode,
  List,
  Cpu,
  Thermometer,
  Activity,
  Upload,
  Download,
  XCircle,
  Monitor,
  Power,
  ChevronDown,
  ChevronRight,
} from "lucide-react";

type ConnectionStatus = "online" | "offline" | "connecting" | "error";
type MachineState =
  | "idle"
  | "running"
  | "paused"
  | "error"
  | "homing"
  | "stopped";

interface CncMachine {
  id: string;
  name: string;
  model: string;
  manufacturer: string;
  ip: string;
  port: number;
  protocol: "modbus" | "opc-ua" | "http" | "serial" | "linuxcnc";
  connection: ConnectionStatus;
  state: MachineState;
  currentJob?: string;
  progress: number;
  position: { x: number; y: number; z: number };
  feedRate: number;
  spindleSpeed: number;
  arcVoltage?: number;
  pierceCount?: number;
  uptime?: number;
  lastSeen?: string;
}

interface QueuedJob {
  id: string;
  machineId: string;
  name: string;
  gcodeFile: string;
  status: "queued" | "running" | "completed" | "failed" | "cancelled";
  progress: number;
  addedAt: string;
  startedAt?: string;
  completedAt?: string;
  priority: number;
}

interface CncMachineIntegrationProps {
  theme: {
    surface: string;
    surfaceAlt: string;
    border: string;
    accentPrimary: string;
    success: string;
    warning: string;
    danger: string;
    textPrimary: string;
    textSecondary: string;
  };
  onSendGcode?: (machineId: string, gcode: string) => Promise<boolean>;
}

// Mock data
const mockMachines: CncMachine[] = [
  {
    id: "cnc-001",
    name: "Plasma CNC 01",
    model: "HPR260XD",
    manufacturer: "Hypertherm",
    ip: "192.168.1.100",
    port: 502,
    protocol: "modbus",
    connection: "online",
    state: "running",
    currentJob: "Flanges Lote 45",
    progress: 67,
    position: { x: 1250.5, y: 890.3, z: 15.0 },
    feedRate: 2800,
    spindleSpeed: 0,
    arcVoltage: 142,
    pierceCount: 48,
    uptime: 14520,
    lastSeen: "2025-01-15T14:30:00",
  },
  {
    id: "cnc-002",
    name: "Plasma CNC 02",
    model: "XPR300",
    manufacturer: "Hypertherm",
    ip: "192.168.1.101",
    port: 502,
    protocol: "modbus",
    connection: "online",
    state: "idle",
    progress: 0,
    position: { x: 0, y: 0, z: 50 },
    feedRate: 0,
    spindleSpeed: 0,
    arcVoltage: 0,
    pierceCount: 0,
    uptime: 8640,
    lastSeen: "2025-01-15T14:30:00",
  },
  {
    id: "cnc-003",
    name: "Laser CNC 01",
    model: "F3015",
    manufacturer: "Fiber Laser",
    ip: "192.168.1.102",
    port: 4840,
    protocol: "opc-ua",
    connection: "offline",
    state: "stopped",
    progress: 0,
    position: { x: 0, y: 0, z: 0 },
    feedRate: 0,
    spindleSpeed: 0,
  },
];

const mockQueue: QueuedJob[] = [
  {
    id: "job-q1",
    machineId: "cnc-001",
    name: "Flanges Lote 45",
    gcodeFile: "flanges_lote45.nc",
    status: "running",
    progress: 67,
    addedAt: "2025-01-15T13:00:00",
    startedAt: "2025-01-15T13:15:00",
    priority: 1,
  },
  {
    id: "job-q2",
    machineId: "cnc-001",
    name: "Suportes Estruturais",
    gcodeFile: "suportes_est.nc",
    status: "queued",
    progress: 0,
    addedAt: "2025-01-15T13:30:00",
    priority: 2,
  },
];

const CncMachineIntegration: React.FC<CncMachineIntegrationProps> = ({
  theme,
  onSendGcode,
}) => {
  const [machines, setMachines] = useState<CncMachine[]>(mockMachines);
  const [queue, setQueue] = useState<QueuedJob[]>(mockQueue);
  const [selectedMachine, setSelectedMachine] = useState<CncMachine | null>(
    null,
  );
  const [expandedMachine, setExpandedMachine] = useState<string | null>(null);
  const [showAddModal, setShowAddModal] = useState(false);
  const [showQueuePanel, setShowQueuePanel] = useState(false);
  const pollingRef = useRef<NodeJS.Timeout | null>(null);

  // Simulate real-time updates
  useEffect(() => {
    pollingRef.current = setInterval(() => {
      setMachines((prev) =>
        prev.map((m) => {
          if (m.state === "running") {
            const newProgress = Math.min(100, m.progress + Math.random() * 2);
            return {
              ...m,
              progress: newProgress,
              position: {
                x: m.position.x + (Math.random() - 0.5) * 10,
                y: m.position.y + (Math.random() - 0.5) * 10,
                z: m.position.z,
              },
              state: newProgress >= 100 ? "idle" : "running",
            };
          }
          return m;
        }),
      );
    }, 2000);

    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current);
    };
  }, []);

  const getConnectionColor = (status: ConnectionStatus) => {
    switch (status) {
      case "online":
        return theme.success;
      case "connecting":
        return theme.warning;
      case "offline":
      case "error":
        return theme.danger;
      default:
        return theme.textSecondary;
    }
  };

  const getStateConfig = (state: MachineState) => {
    switch (state) {
      case "idle":
        return { color: theme.textSecondary, label: "Ocioso", icon: Clock };
      case "running":
        return { color: theme.success, label: "Executando", icon: Play };
      case "paused":
        return { color: theme.warning, label: "Pausado", icon: Pause };
      case "error":
        return { color: theme.danger, label: "Erro", icon: AlertTriangle };
      case "homing":
        return { color: theme.accentPrimary, label: "Homing", icon: RefreshCw };
      case "stopped":
        return { color: theme.danger, label: "Parado", icon: Square };
      default:
        return { color: theme.textSecondary, label: state, icon: Clock };
    }
  };

  const formatUptime = (seconds?: number) => {
    if (!seconds) return "-";
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    return `${h}h ${m}m`;
  };

  const connectMachine = async (id: string) => {
    setMachines((prev) =>
      prev.map((m) => (m.id === id ? { ...m, connection: "connecting" } : m)),
    );
    await new Promise((r) => setTimeout(r, 1500));
    setMachines((prev) =>
      prev.map((m) =>
        m.id === id
          ? { ...m, connection: "online", lastSeen: new Date().toISOString() }
          : m,
      ),
    );
  };

  const disconnectMachine = async (id: string) => {
    setMachines((prev) =>
      prev.map((m) => (m.id === id ? { ...m, connection: "offline" } : m)),
    );
  };

  const sendCommand = async (
    machineId: string,
    command: "start" | "pause" | "stop" | "home",
  ) => {
    const stateMap: Record<string, MachineState> = {
      start: "running",
      pause: "paused",
      stop: "idle",
      home: "homing",
    };

    setMachines((prev) =>
      prev.map((m) =>
        m.id === machineId ? { ...m, state: stateMap[command] || m.state } : m,
      ),
    );

    // Simulate homing completion
    if (command === "home") {
      setTimeout(() => {
        setMachines((prev) =>
          prev.map((m) =>
            m.id === machineId && m.state === "homing"
              ? { ...m, state: "idle", position: { x: 0, y: 0, z: 0 } }
              : m,
          ),
        );
      }, 3000);
    }
  };

  const queueForMachine = (machineId: string) =>
    queue.filter((j) => j.machineId === machineId);

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      style={{ display: "flex", flexDirection: "column", gap: 20 }}
    >
      {/* Header */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <Server size={24} color={theme.accentPrimary} />
          <h2 style={{ margin: 0, color: theme.textPrimary, fontSize: 20 }}>
            Integração CNC
          </h2>
          <span
            style={{
              padding: "4px 8px",
              borderRadius: 4,
              background: `${theme.success}20`,
              color: theme.success,
              fontSize: 12,
            }}
          >
            {machines.filter((m) => m.connection === "online").length}/
            {machines.length} Online
          </span>
        </div>

        <div style={{ display: "flex", gap: 8 }}>
          <button
            onClick={() => setShowQueuePanel(!showQueuePanel)}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              padding: "8px 16px",
              borderRadius: 6,
              border: `1px solid ${showQueuePanel ? theme.accentPrimary : theme.border}`,
              background: showQueuePanel
                ? `${theme.accentPrimary}20`
                : "transparent",
              color: showQueuePanel ? theme.accentPrimary : theme.textSecondary,
              cursor: "pointer",
              fontSize: 13,
            }}
          >
            <List size={16} />
            Fila ({queue.length})
          </button>

          <button
            onClick={() => setShowAddModal(true)}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              padding: "8px 16px",
              borderRadius: 6,
              border: "none",
              background: theme.accentPrimary,
              color: "#FFF",
              cursor: "pointer",
              fontSize: 13,
              fontWeight: 500,
            }}
          >
            <Plus size={16} />
            Adicionar Máquina
          </button>
        </div>
      </div>

      {/* Machine Cards */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(350px, 1fr))",
          gap: 16,
        }}
      >
        {machines.map((machine) => {
          const stateConfig = getStateConfig(machine.state);
          const StateIcon = stateConfig.icon;
          const isExpanded = expandedMachine === machine.id;
          const machineQueue = queueForMachine(machine.id);

          return (
            <motion.div
              key={machine.id}
              layout
              style={{
                background: theme.surface,
                border: `1px solid ${theme.border}`,
                borderRadius: 8,
                overflow: "hidden",
              }}
            >
              {/* Card Header */}
              <div
                style={{
                  padding: 16,
                  borderBottom: `1px solid ${theme.border}`,
                  display: "flex",
                  alignItems: "center",
                  gap: 12,
                }}
              >
                {/* Connection indicator */}
                <div
                  style={{
                    width: 10,
                    height: 10,
                    borderRadius: "50%",
                    background: getConnectionColor(machine.connection),
                    boxShadow:
                      machine.connection === "online"
                        ? `0 0 8px ${theme.success}`
                        : "none",
                  }}
                />

                <div style={{ flex: 1 }}>
                  <div style={{ color: theme.textPrimary, fontWeight: 600 }}>
                    {machine.name}
                  </div>
                  <div style={{ color: theme.textSecondary, fontSize: 11 }}>
                    {machine.manufacturer} {machine.model}
                  </div>
                </div>

                {/* State badge */}
                <span
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: 4,
                    padding: "4px 8px",
                    borderRadius: 4,
                    background: `${stateConfig.color}20`,
                    color: stateConfig.color,
                    fontSize: 11,
                    fontWeight: 500,
                  }}
                >
                  <StateIcon size={12} />
                  {stateConfig.label}
                </span>

                <button
                  onClick={() =>
                    setExpandedMachine(isExpanded ? null : machine.id)
                  }
                  style={{
                    width: 28,
                    height: 28,
                    borderRadius: 4,
                    border: "none",
                    background: "transparent",
                    color: theme.textSecondary,
                    cursor: "pointer",
                  }}
                >
                  {isExpanded ? (
                    <ChevronDown size={18} />
                  ) : (
                    <ChevronRight size={18} />
                  )}
                </button>
              </div>

              {/* Progress bar (if running) */}
              {machine.state === "running" && (
                <div style={{ height: 4, background: theme.border }}>
                  <motion.div
                    animate={{ width: `${machine.progress}%` }}
                    style={{
                      height: "100%",
                      background: `linear-gradient(90deg, ${theme.accentPrimary}, ${theme.success})`,
                    }}
                  />
                </div>
              )}

              {/* Main Info */}
              <div style={{ padding: 16 }}>
                {/* Current job */}
                {machine.currentJob && (
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 8,
                      marginBottom: 12,
                      padding: 10,
                      background: theme.surfaceAlt,
                      borderRadius: 6,
                    }}
                  >
                    <FileCode size={16} color={theme.accentPrimary} />
                    <div style={{ flex: 1 }}>
                      <div style={{ color: theme.textPrimary, fontSize: 13 }}>
                        {machine.currentJob}
                      </div>
                      <div style={{ color: theme.textSecondary, fontSize: 11 }}>
                        {machine.progress.toFixed(1)}% concluído
                      </div>
                    </div>
                  </div>
                )}

                {/* Live stats */}
                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(3, 1fr)",
                    gap: 8,
                  }}
                >
                  <StatBox
                    label="Posição X"
                    value={`${machine.position.x.toFixed(1)}`}
                    unit="mm"
                    theme={theme}
                  />
                  <StatBox
                    label="Posição Y"
                    value={`${machine.position.y.toFixed(1)}`}
                    unit="mm"
                    theme={theme}
                  />
                  <StatBox
                    label="Feed Rate"
                    value={`${machine.feedRate}`}
                    unit="mm/min"
                    theme={theme}
                  />
                  {machine.arcVoltage !== undefined && (
                    <StatBox
                      label="Arco"
                      value={`${machine.arcVoltage}`}
                      unit="V"
                      theme={theme}
                    />
                  )}
                  {machine.pierceCount !== undefined && (
                    <StatBox
                      label="Perfurações"
                      value={`${machine.pierceCount}`}
                      theme={theme}
                    />
                  )}
                  <StatBox
                    label="Uptime"
                    value={formatUptime(machine.uptime)}
                    theme={theme}
                  />
                </div>

                {/* Control buttons */}
                <div
                  style={{
                    display: "flex",
                    gap: 8,
                    marginTop: 16,
                    paddingTop: 16,
                    borderTop: `1px dashed ${theme.border}`,
                  }}
                >
                  {machine.connection === "online" ? (
                    <>
                      {machine.state === "running" ? (
                        <ControlButton
                          icon={<Pause size={14} />}
                          label="Pausar"
                          onClick={() => sendCommand(machine.id, "pause")}
                          theme={theme}
                        />
                      ) : (
                        <ControlButton
                          icon={<Play size={14} />}
                          label="Iniciar"
                          onClick={() => sendCommand(machine.id, "start")}
                          color={theme.success}
                          theme={theme}
                        />
                      )}
                      <ControlButton
                        icon={<Square size={14} />}
                        label="Parar"
                        onClick={() => sendCommand(machine.id, "stop")}
                        color={theme.danger}
                        theme={theme}
                      />
                      <ControlButton
                        icon={<RefreshCw size={14} />}
                        label="Home"
                        onClick={() => sendCommand(machine.id, "home")}
                        theme={theme}
                      />
                      <div style={{ flex: 1 }} />
                      <ControlButton
                        icon={<WifiOff size={14} />}
                        label="Desconectar"
                        onClick={() => disconnectMachine(machine.id)}
                        color={theme.warning}
                        theme={theme}
                      />
                    </>
                  ) : (
                    <ControlButton
                      icon={<Wifi size={14} />}
                      label="Conectar"
                      onClick={() => connectMachine(machine.id)}
                      color={theme.accentPrimary}
                      fullWidth
                      theme={theme}
                    />
                  )}
                </div>
              </div>

              {/* Expanded Details */}
              <AnimatePresence>
                {isExpanded && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: "auto", opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    style={{ overflow: "hidden" }}
                  >
                    <div
                      style={{
                        padding: 16,
                        borderTop: `1px solid ${theme.border}`,
                        background: theme.surfaceAlt,
                      }}
                    >
                      <h4
                        style={{
                          margin: "0 0 12px",
                          color: theme.textPrimary,
                          fontSize: 13,
                        }}
                      >
                        Configuração de Rede
                      </h4>
                      <div
                        style={{
                          display: "grid",
                          gridTemplateColumns: "1fr 1fr",
                          gap: 8,
                        }}
                      >
                        <InfoItem label="IP" value={machine.ip} theme={theme} />
                        <InfoItem
                          label="Porta"
                          value={machine.port.toString()}
                          theme={theme}
                        />
                        <InfoItem
                          label="Protocolo"
                          value={machine.protocol.toUpperCase()}
                          theme={theme}
                        />
                        <InfoItem
                          label="Última comunicação"
                          value={
                            machine.lastSeen
                              ? new Date(machine.lastSeen).toLocaleTimeString(
                                  "pt-BR",
                                )
                              : "-"
                          }
                          theme={theme}
                        />
                      </div>

                      {/* Queue for this machine */}
                      {machineQueue.length > 0 && (
                        <>
                          <h4
                            style={{
                              margin: "16px 0 12px",
                              color: theme.textPrimary,
                              fontSize: 13,
                            }}
                          >
                            Fila de Jobs ({machineQueue.length})
                          </h4>
                          <div
                            style={{
                              display: "flex",
                              flexDirection: "column",
                              gap: 8,
                            }}
                          >
                            {machineQueue.map((job, idx) => (
                              <div
                                key={job.id}
                                style={{
                                  display: "flex",
                                  alignItems: "center",
                                  gap: 8,
                                  padding: 8,
                                  background: theme.surface,
                                  borderRadius: 4,
                                }}
                              >
                                <span
                                  style={{
                                    width: 20,
                                    height: 20,
                                    borderRadius: "50%",
                                    background: theme.border,
                                    display: "flex",
                                    alignItems: "center",
                                    justifyContent: "center",
                                    fontSize: 10,
                                    fontWeight: 600,
                                    color: theme.textSecondary,
                                  }}
                                >
                                  {idx + 1}
                                </span>
                                <div style={{ flex: 1 }}>
                                  <div
                                    style={{
                                      color: theme.textPrimary,
                                      fontSize: 12,
                                    }}
                                  >
                                    {job.name}
                                  </div>
                                  <div
                                    style={{
                                      color: theme.textSecondary,
                                      fontSize: 10,
                                    }}
                                  >
                                    {job.status === "running"
                                      ? `${job.progress}% concluído`
                                      : job.status}
                                  </div>
                                </div>
                              </div>
                            ))}
                          </div>
                        </>
                      )}

                      {/* Actions */}
                      <div style={{ display: "flex", gap: 8, marginTop: 16 }}>
                        <button
                          onClick={() => setSelectedMachine(machine)}
                          style={{
                            flex: 1,
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                            gap: 6,
                            padding: 10,
                            borderRadius: 6,
                            border: `1px solid ${theme.border}`,
                            background: "transparent",
                            color: theme.textSecondary,
                            cursor: "pointer",
                            fontSize: 12,
                          }}
                        >
                          <Settings size={14} />
                          Configurar
                        </button>
                        <button
                          style={{
                            flex: 1,
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                            gap: 6,
                            padding: 10,
                            borderRadius: 6,
                            border: "none",
                            background: theme.accentPrimary,
                            color: "#FFF",
                            cursor: "pointer",
                            fontSize: 12,
                            fontWeight: 500,
                          }}
                        >
                          <Send size={14} />
                          Enviar G-Code
                        </button>
                      </div>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </motion.div>
          );
        })}
      </div>

      {/* Queue Panel (Slide in) */}
      <AnimatePresence>
        {showQueuePanel && (
          <motion.div
            initial={{ opacity: 0, x: 300 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 300 }}
            style={{
              position: "fixed",
              top: 0,
              right: 0,
              bottom: 0,
              width: 400,
              background: theme.surface,
              borderLeft: `1px solid ${theme.border}`,
              boxShadow: "-4px 0 20px rgba(0,0,0,0.3)",
              zIndex: 100,
              display: "flex",
              flexDirection: "column",
            }}
          >
            <div
              style={{
                padding: 20,
                borderBottom: `1px solid ${theme.border}`,
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
              }}
            >
              <h3 style={{ margin: 0, color: theme.textPrimary }}>
                Fila de Jobs
              </h3>
              <button
                onClick={() => setShowQueuePanel(false)}
                style={{
                  width: 32,
                  height: 32,
                  borderRadius: 6,
                  border: "none",
                  background: "transparent",
                  color: theme.textSecondary,
                  cursor: "pointer",
                }}
              >
                <XCircle size={20} />
              </button>
            </div>

            <div style={{ flex: 1, overflow: "auto", padding: 16 }}>
              {queue.length === 0 ? (
                <div
                  style={{
                    textAlign: "center",
                    color: theme.textSecondary,
                    padding: 40,
                  }}
                >
                  <List size={40} style={{ opacity: 0.3, marginBottom: 12 }} />
                  <div>Fila vazia</div>
                </div>
              ) : (
                queue.map((job, idx) => (
                  <div
                    key={job.id}
                    style={{
                      padding: 16,
                      background: theme.surfaceAlt,
                      borderRadius: 8,
                      marginBottom: 12,
                    }}
                  >
                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 8,
                        marginBottom: 8,
                      }}
                    >
                      <span
                        style={{
                          padding: "2px 6px",
                          borderRadius: 4,
                          background:
                            job.status === "running"
                              ? `${theme.success}20`
                              : job.status === "queued"
                                ? `${theme.warning}20`
                                : theme.border,
                          color:
                            job.status === "running"
                              ? theme.success
                              : job.status === "queued"
                                ? theme.warning
                                : theme.textSecondary,
                          fontSize: 10,
                          fontWeight: 500,
                        }}
                      >
                        {job.status.toUpperCase()}
                      </span>
                      <span
                        style={{ color: theme.textSecondary, fontSize: 11 }}
                      >
                        Prioridade: {job.priority}
                      </span>
                    </div>
                    <div
                      style={{
                        color: theme.textPrimary,
                        fontWeight: 500,
                        marginBottom: 4,
                      }}
                    >
                      {job.name}
                    </div>
                    <div style={{ color: theme.textSecondary, fontSize: 12 }}>
                      Máquina:{" "}
                      {machines.find((m) => m.id === job.machineId)?.name}
                    </div>
                    {job.status === "running" && (
                      <div style={{ marginTop: 8 }}>
                        <div
                          style={{
                            height: 4,
                            background: theme.border,
                            borderRadius: 2,
                            overflow: "hidden",
                          }}
                        >
                          <div
                            style={{
                              width: `${job.progress}%`,
                              height: "100%",
                              background: theme.success,
                            }}
                          />
                        </div>
                        <div
                          style={{
                            color: theme.textSecondary,
                            fontSize: 10,
                            marginTop: 4,
                          }}
                        >
                          {job.progress}% concluído
                        </div>
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Add Machine Modal */}
      <AnimatePresence>
        {showAddModal && (
          <AddMachineModal
            theme={theme}
            onClose={() => setShowAddModal(false)}
            onSave={(machine) => {
              setMachines((prev) => [
                ...prev,
                { ...machine, id: `cnc-${Date.now()}` },
              ]);
              setShowAddModal(false);
            }}
          />
        )}
      </AnimatePresence>
    </motion.div>
  );
};

// Sub-components

const StatBox: React.FC<{
  label: string;
  value: string;
  unit?: string;
  theme: CncMachineIntegrationProps["theme"];
}> = ({ label, value, unit, theme }) => (
  <div
    style={{
      padding: 8,
      background: theme.surfaceAlt,
      borderRadius: 4,
      textAlign: "center",
    }}
  >
    <div style={{ color: theme.textSecondary, fontSize: 10 }}>{label}</div>
    <div style={{ color: theme.textPrimary, fontWeight: 600, fontSize: 13 }}>
      {value}
      {unit && (
        <span style={{ fontSize: 10, fontWeight: 400, marginLeft: 2 }}>
          {unit}
        </span>
      )}
    </div>
  </div>
);

const ControlButton: React.FC<{
  icon: React.ReactNode;
  label: string;
  onClick: () => void;
  color?: string;
  fullWidth?: boolean;
  theme: CncMachineIntegrationProps["theme"];
}> = ({ icon, label, onClick, color, fullWidth, theme }) => (
  <button
    onClick={onClick}
    style={{
      flex: fullWidth ? 1 : undefined,
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      gap: 6,
      padding: "8px 12px",
      borderRadius: 6,
      border: `1px solid ${color || theme.border}`,
      background: "transparent",
      color: color || theme.textSecondary,
      cursor: "pointer",
      fontSize: 11,
    }}
  >
    {icon}
    {label}
  </button>
);

const InfoItem: React.FC<{
  label: string;
  value: string;
  theme: CncMachineIntegrationProps["theme"];
}> = ({ label, value, theme }) => (
  <div>
    <div style={{ color: theme.textSecondary, fontSize: 10 }}>{label}</div>
    <div style={{ color: theme.textPrimary, fontWeight: 500, fontSize: 12 }}>
      {value}
    </div>
  </div>
);

const AddMachineModal: React.FC<{
  theme: CncMachineIntegrationProps["theme"];
  onClose: () => void;
  onSave: (machine: Omit<CncMachine, "id">) => void;
}> = ({ theme, onClose, onSave }) => {
  const [form, setForm] = useState({
    name: "",
    model: "",
    manufacturer: "",
    ip: "",
    port: 502,
    protocol: "modbus" as CncMachine["protocol"],
  });

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.7)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 1000,
      }}
      onClick={onClose}
    >
      <motion.div
        initial={{ scale: 0.9, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.9, opacity: 0 }}
        style={{
          background: theme.surface,
          borderRadius: 12,
          width: "90%",
          maxWidth: 500,
          padding: 24,
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <h3 style={{ margin: "0 0 20px", color: theme.textPrimary }}>
          Adicionar Nova Máquina
        </h3>

        <div style={{ display: "grid", gap: 16 }}>
          <div>
            <label style={{ color: theme.textSecondary, fontSize: 12 }}>
              Nome
            </label>
            <input
              type="text"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              style={{
                width: "100%",
                padding: 10,
                borderRadius: 6,
                border: `1px solid ${theme.border}`,
                background: theme.surfaceAlt,
                color: theme.textPrimary,
                marginTop: 4,
              }}
              placeholder="Ex: Plasma CNC 03"
            />
          </div>

          <div
            style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}
          >
            <div>
              <label style={{ color: theme.textSecondary, fontSize: 12 }}>
                Fabricante
              </label>
              <input
                type="text"
                value={form.manufacturer}
                onChange={(e) =>
                  setForm({ ...form, manufacturer: e.target.value })
                }
                style={{
                  width: "100%",
                  padding: 10,
                  borderRadius: 6,
                  border: `1px solid ${theme.border}`,
                  background: theme.surfaceAlt,
                  color: theme.textPrimary,
                  marginTop: 4,
                }}
              />
            </div>
            <div>
              <label style={{ color: theme.textSecondary, fontSize: 12 }}>
                Modelo
              </label>
              <input
                type="text"
                value={form.model}
                onChange={(e) => setForm({ ...form, model: e.target.value })}
                style={{
                  width: "100%",
                  padding: 10,
                  borderRadius: 6,
                  border: `1px solid ${theme.border}`,
                  background: theme.surfaceAlt,
                  color: theme.textPrimary,
                  marginTop: 4,
                }}
              />
            </div>
          </div>

          <div
            style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: 12 }}
          >
            <div>
              <label style={{ color: theme.textSecondary, fontSize: 12 }}>
                Endereço IP
              </label>
              <input
                type="text"
                value={form.ip}
                onChange={(e) => setForm({ ...form, ip: e.target.value })}
                style={{
                  width: "100%",
                  padding: 10,
                  borderRadius: 6,
                  border: `1px solid ${theme.border}`,
                  background: theme.surfaceAlt,
                  color: theme.textPrimary,
                  marginTop: 4,
                }}
                placeholder="192.168.1.xxx"
              />
            </div>
            <div>
              <label style={{ color: theme.textSecondary, fontSize: 12 }}>
                Porta
              </label>
              <input
                type="number"
                value={form.port}
                onChange={(e) =>
                  setForm({ ...form, port: Number(e.target.value) })
                }
                style={{
                  width: "100%",
                  padding: 10,
                  borderRadius: 6,
                  border: `1px solid ${theme.border}`,
                  background: theme.surfaceAlt,
                  color: theme.textPrimary,
                  marginTop: 4,
                }}
              />
            </div>
          </div>

          <div>
            <label style={{ color: theme.textSecondary, fontSize: 12 }}>
              Protocolo
            </label>
            <select
              value={form.protocol}
              onChange={(e) =>
                setForm({
                  ...form,
                  protocol: e.target.value as CncMachine["protocol"],
                })
              }
              style={{
                width: "100%",
                padding: 10,
                borderRadius: 6,
                border: `1px solid ${theme.border}`,
                background: theme.surfaceAlt,
                color: theme.textPrimary,
                marginTop: 4,
              }}
            >
              <option value="modbus">Modbus TCP</option>
              <option value="opc-ua">OPC-UA</option>
              <option value="http">HTTP/REST</option>
              <option value="serial">Serial/RS485</option>
              <option value="linuxcnc">LinuxCNC</option>
            </select>
          </div>
        </div>

        <div style={{ display: "flex", gap: 12, marginTop: 24 }}>
          <button
            onClick={onClose}
            style={{
              flex: 1,
              padding: 12,
              borderRadius: 6,
              border: `1px solid ${theme.border}`,
              background: "transparent",
              color: theme.textSecondary,
              cursor: "pointer",
            }}
          >
            Cancelar
          </button>
          <button
            onClick={() =>
              onSave({
                ...form,
                connection: "offline",
                state: "stopped",
                progress: 0,
                position: { x: 0, y: 0, z: 0 },
                feedRate: 0,
                spindleSpeed: 0,
              })
            }
            style={{
              flex: 1,
              padding: 12,
              borderRadius: 6,
              border: "none",
              background: theme.accentPrimary,
              color: "#FFF",
              cursor: "pointer",
              fontWeight: 500,
            }}
          >
            Adicionar
          </button>
        </div>
      </motion.div>
    </motion.div>
  );
};

export default CncMachineIntegration;
