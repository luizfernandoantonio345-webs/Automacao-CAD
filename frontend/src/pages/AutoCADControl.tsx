import React, { useCallback, useEffect, useRef, useState } from "react";
import axios from "axios";
import { API_BASE_URL } from "../services/api";
import { useToast } from "../context/ToastContext";
import { useSSE } from "../hooks/useSSE";

// ═══════════════════════════════════════════════════════════════════════
// Engenharia CAD — Interface de Controle do AutoCAD Driver (Nível 4)
// Consome TODOS os endpoints REST de /api/autocad/* para operar o Driver
// híbrido (COM direto + Ponte de Rede).
// Inclui: watchdog validation, batch-draw UI, SSE, toast integration.
// ═══════════════════════════════════════════════════════════════════════

const API = API_BASE_URL;

interface DriverStatus {
  status: string;
  engine: string;
  mode: string;
  bridge_path: string;
  buffer_size: number;
  operations_total: number;
  operations_success: number;
  operations_failed: number;
  bridge_commits: number;
  bridge_commands_sent: number;
  last_error: string | null;
}

interface LogEntry {
  ts: string;
  level: "OK" | "ERR" | "INFO" | "CMD";
  text: string;
  json?: unknown;
}

// Blocos padrão N-58 Petrobras para válvulas
const VALVE_BLOCKS = [
  "VALVE-GATE",
  "VALVE-GLOBE",
  "VALVE-CHECK",
  "VALVE-BALL",
  "VALVE-BUTTERFLY",
  "VALVE-PLUG",
  "VALVE-NEEDLE",
  "VALVE-RELIEF",
  "VALVE-CONTROL",
  "FLANGE-WN",
  "FLANGE-SO",
  "FLANGE-BL",
  "REDUCER-CON",
  "REDUCER-ECC",
  "TEE-EQUAL",
  "TEE-REDUCING",
  "ELBOW-90",
  "ELBOW-45",
];

const DIAMETERS = [
  { label: '2" (DN50)', value: 2 },
  { label: '3" (DN80)', value: 3 },
  { label: '4" (DN100)', value: 4 },
  { label: '6" (DN150)', value: 6 },
  { label: '8" (DN200)', value: 8 },
  { label: '10" (DN250)', value: 10 },
  { label: '12" (DN300)', value: 12 },
  { label: '14" (DN350)', value: 14 },
  { label: '16" (DN400)', value: 16 },
  { label: '20" (DN500)', value: 20 },
  { label: '24" (DN600)', value: 24 },
];

const BATCH_EXAMPLE = JSON.stringify(
  {
    pipes: [
      {
        points: [
          [0, 0, 0],
          [1000, 0, 0],
        ],
        diameter: 6,
        layer: "PIPE-PROCESS",
      },
      {
        points: [
          [1000, 0, 0],
          [1000, 500, 0],
        ],
        diameter: 4,
        layer: "PIPE-UTILITY",
      },
    ],
    components: [
      {
        block_name: "VALVE-GATE",
        coordinate: [500, 0, 0],
        rotation: 0,
        scale: 1,
        layer: "VALVE",
      },
    ],
    finalize: true,
  },
  null,
  2,
);

const now = (): string =>
  new Date().toLocaleTimeString("pt-BR", { hour12: false });

const AutoCADControl: React.FC = () => {
  const { addToast, handleApiError } = useToast();

  // ── Status do Driver ──
  const [driverStatus, setDriverStatus] = useState<DriverStatus | null>(null);
  const [healthData, setHealthData] = useState<Record<string, unknown> | null>(
    null,
  );
  const [polling, setPolling] = useState(true);

  // ── Configuração de caminho ──
  const [bridgePath, setBridgePath] = useState("");

  // ── Traçar Tubo ──
  const [pipeAx, setPipeAx] = useState("0");
  const [pipeAy, setPipeAy] = useState("0");
  const [pipeAz, setPipeAz] = useState("0");
  const [pipeBx, setPipeBx] = useState("1000");
  const [pipeBy, setPipeBy] = useState("0");
  const [pipeBz, setPipeBz] = useState("0");
  const [pipeDiameter, setPipeDiameter] = useState(6);

  // ── Inserir Componente ──
  const [valveBlock, setValveBlock] = useState(VALVE_BLOCKS[0]);
  const [valveX, setValveX] = useState("500");
  const [valveY, setValveY] = useState("500");
  const [valveZ, setValveZ] = useState("0");
  const [valveRotation, setValveRotation] = useState("0");
  const [valveScale, setValveScale] = useState("1");

  // ── Adicionar Texto ──
  const [textContent, setTextContent] = useState("");
  const [textX, setTextX] = useState("0");
  const [textY, setTextY] = useState("0");
  const [textZ, setTextZ] = useState("0");
  const [textHeight, setTextHeight] = useState("2.5");

  // ── Linha Simples ──
  const [lineStartX, setLineStartX] = useState("0");
  const [lineStartY, setLineStartY] = useState("0");
  const [lineEndX, setLineEndX] = useState("1000");
  const [lineEndY, setLineEndY] = useState("1000");

  // ── Comando Direto ──
  const [rawCommand, setRawCommand] = useState("");

  // ── Batch Draw ──
  const [batchJson, setBatchJson] = useState(BATCH_EXAMPLE);
  const [batchRunning, setBatchRunning] = useState(false);

  // ── Console de Retorno ──
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const logRef = useRef<HTMLDivElement>(null);

  const pushLog = useCallback(
    (level: LogEntry["level"], text: string, json?: unknown) => {
      setLogs((prev) => {
        const next = [...prev, { ts: now(), level, text, json }];
        return next.length > 500 ? next.slice(-500) : next;
      });
    },
    [],
  );

  // Auto-scroll do console
  useEffect(() => {
    if (logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight;
    }
  }, [logs]);

  // ── Polling de status + health ──
  useEffect(() => {
    if (!polling) return;
    let cancelled = false;

    const fetchStatus = async () => {
      try {
        const [statusRes, healthRes] = await Promise.all([
          axios.get<DriverStatus>(`${API}/api/autocad/status`),
          axios.get(`${API}/api/autocad/health`),
        ]);
        if (!cancelled) {
          setDriverStatus(statusRes.data);
          setHealthData(healthRes.data);
        }
      } catch {
        if (!cancelled) {
          setDriverStatus(null);
          setHealthData(null);
        }
      }
    };

    fetchStatus();
    const id = setInterval(fetchStatus, 3000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [polling]);

  // ── SSE: Escuta notificações de circuit breaker (com auto-reconnect) ──
  useSSE({
    path: "/sse/notifications",
    onMessage: useCallback(
      (data: any) => {
        if (data?.type === "circuit_breaker" || data?.circuit_breaker) {
          addToast(
            "error",
            "Sistema em Recuperação",
            data.message ||
              "Modo Offline Ativado — aguarde recuperação automática.",
          );
        }
        pushLog("INFO", `[SSE] ${data?.message || JSON.stringify(data)}`);
      },
      [addToast, pushLog],
    ),
  });

  // ── Watchdog Validation ──
  const validateDiameter = (d: number): string | null => {
    if (d <= 0 || d > 120) return "Diâmetro deve ser entre 0.1 e 120 polegadas";
    return null;
  };

  const validateCoords = (coords: number[], label: string): string | null => {
    if (coords.some(isNaN))
      return `${label}: coordenadas devem ser números válidos`;
    if (coords.some((c) => Math.abs(c) > 1_000_000))
      return `${label}: coordenada fora do limite razoável (±1.000.000)`;
    return null;
  };

  // ── Helpers de API (com toast para circuit breaker) ──
  const apiCall = async (
    method: "get" | "post",
    path: string,
    body?: unknown,
    label?: string,
  ) => {
    const tag = label ?? path;
    pushLog("CMD", `${method.toUpperCase()} ${path}`);
    try {
      const res =
        method === "get"
          ? await axios.get(`${API}${path}`)
          : await axios.post(`${API}${path}`, body);
      pushLog("OK", `${tag} — Sucesso`, res.data);
      return res.data;
    } catch (err: any) {
      handleApiError(err);
      const detail =
        err?.response?.data?.detail ??
        err?.response?.data ??
        err?.message ??
        "Erro desconhecido";
      pushLog(
        "ERR",
        `${tag} — Falha: ${typeof detail === "string" ? detail : JSON.stringify(detail)}`,
        detail,
      );
      return null;
    }
  };

  // ── Ações (todos os 15 endpoints) ──
  const handleConnect = () =>
    apiCall("post", "/api/autocad/connect", {}, "Conectar");
  const handleDisconnect = () =>
    apiCall("post", "/api/autocad/disconnect", {}, "Desconectar");

  const handleSetBridgePath = () => {
    if (!bridgePath.trim()) {
      pushLog("ERR", "Caminho não pode ser vazio");
      return;
    }
    apiCall(
      "post",
      "/api/autocad/config/bridge",
      { path: bridgePath },
      "Config Bridge",
    );
  };

  const handleSetModeBridge = () =>
    apiCall(
      "post",
      "/api/autocad/config/mode",
      { use_bridge: true },
      "Modo → PONTE",
    );
  const handleSetModeCOM = () =>
    apiCall(
      "post",
      "/api/autocad/config/mode",
      { use_bridge: false },
      "Modo → COM",
    );

  const handleDrawPipe = () => {
    const pointA = [parseFloat(pipeAx), parseFloat(pipeAy), parseFloat(pipeAz)];
    const pointB = [parseFloat(pipeBx), parseFloat(pipeBy), parseFloat(pipeBz)];
    const errCoordA = validateCoords(pointA, "Ponto A");
    const errCoordB = validateCoords(pointB, "Ponto B");
    const errDiam = validateDiameter(pipeDiameter);
    if (errCoordA) {
      pushLog("ERR", errCoordA);
      addToast("warning", "Validação", errCoordA);
      return;
    }
    if (errCoordB) {
      pushLog("ERR", errCoordB);
      addToast("warning", "Validação", errCoordB);
      return;
    }
    if (errDiam) {
      pushLog("ERR", errDiam);
      addToast("warning", "Validação", errDiam);
      return;
    }
    apiCall(
      "post",
      "/api/autocad/draw-pipe",
      {
        points: [pointA, pointB],
        diameter: pipeDiameter,
        layer: "PIPE-PROCESS",
      },
      `Traçar Tubo Ø${pipeDiameter}"`,
    );
  };

  const handleDrawLine = () => {
    const start = [parseFloat(lineStartX), parseFloat(lineStartY), 0];
    const end = [parseFloat(lineEndX), parseFloat(lineEndY), 0];
    const err1 = validateCoords(start, "Início");
    const err2 = validateCoords(end, "Fim");
    if (err1) {
      pushLog("ERR", err1);
      return;
    }
    if (err2) {
      pushLog("ERR", err2);
      return;
    }
    apiCall(
      "post",
      "/api/autocad/draw-line",
      { start, end, layer: "PIPE-UTILITY" },
      "Desenhar Linha",
    );
  };

  const handleInsertValve = () => {
    const coord = [parseFloat(valveX), parseFloat(valveY), parseFloat(valveZ)];
    const rot = parseFloat(valveRotation);
    const scl = parseFloat(valveScale);
    const errCoord = validateCoords(coord, "Inserção");
    if (errCoord) {
      pushLog("ERR", errCoord);
      addToast("warning", "Validação", errCoord);
      return;
    }
    if (isNaN(rot) || rot < 0 || rot >= 360) {
      pushLog("ERR", "Rotação deve ser 0–359°");
      return;
    }
    if (isNaN(scl) || scl <= 0 || scl > 100) {
      pushLog("ERR", "Escala deve ser 0.01–100");
      return;
    }
    apiCall(
      "post",
      "/api/autocad/insert-component",
      {
        block_name: valveBlock,
        coordinate: coord,
        rotation: rot,
        scale: scl,
        layer: "VALVE",
      },
      `Inserir ${valveBlock}`,
    );
  };

  const handleAddText = () => {
    if (!textContent.trim()) {
      pushLog("ERR", "Texto não pode ser vazio");
      return;
    }
    const pos = [parseFloat(textX), parseFloat(textY), parseFloat(textZ)];
    const h = parseFloat(textHeight);
    const errPos = validateCoords(pos, "Posição do texto");
    if (errPos) {
      pushLog("ERR", errPos);
      return;
    }
    if (isNaN(h) || h <= 0 || h > 100) {
      pushLog("ERR", "Altura deve ser 0.1–100");
      return;
    }
    apiCall(
      "post",
      "/api/autocad/add-text",
      { text: textContent, position: pos, height: h, layer: "ANNOTATION" },
      "Adicionar Texto",
    );
  };

  const handleSendCommand = () => {
    if (!rawCommand.trim()) {
      pushLog("ERR", "Comando vazio");
      return;
    }
    apiCall(
      "post",
      "/api/autocad/send-command",
      { command: rawCommand },
      `CMD: ${rawCommand.slice(0, 40)}`,
    );
    setRawCommand("");
  };

  const handleFinalize = () =>
    apiCall("post", "/api/autocad/finalize", {}, "Finalizar Visualização");
  const handleCommit = () =>
    apiCall("post", "/api/autocad/commit", {}, "Commit Buffer → .lsp");
  const handleCreateLayers = () =>
    apiCall("post", "/api/autocad/create-layers", {}, "Criar Layers N-58");
  const handleSave = () =>
    apiCall("post", "/api/autocad/save", {}, "Salvar Documento");
  const handleGetBuffer = () =>
    apiCall("get", "/api/autocad/buffer", undefined, "Status do Buffer");
  const handleGetHealth = () =>
    apiCall("get", "/api/autocad/health", undefined, "Health Check Detalhado");

  // ── Batch Draw ──
  const handleBatchDraw = async () => {
    let payload: unknown;
    try {
      payload = JSON.parse(batchJson);
    } catch {
      pushLog("ERR", "JSON de batch inválido — verifique a sintaxe");
      addToast(
        "warning",
        "JSON Inválido",
        "O JSON do batch-draw contém erros de sintaxe.",
      );
      return;
    }
    setBatchRunning(true);
    await apiCall(
      "post",
      "/api/autocad/batch-draw",
      payload,
      "Batch Draw (Lote)",
    );
    setBatchRunning(false);
  };

  const handleClearLog = () => setLogs([]);

  // ── Render helpers ──
  const statusColor = (s: string | undefined) => {
    switch (s) {
      case "Bridge":
        return "#00BFFF";
      case "Connected":
        return "#00FF87";
      case "Simulation":
        return "#FFD700";
      case "Recovering":
        return "#FFA500";
      default:
        return "#FF4444";
    }
  };

  const logColor = (level: LogEntry["level"]) => {
    switch (level) {
      case "OK":
        return "#00FF87";
      case "ERR":
        return "#FF4444";
      case "CMD":
        return "#00BFFF";
      default:
        return "#888";
    }
  };

  // ═══════════════════════════════════════════════════════════════════════
  // RENDER
  // ═══════════════════════════════════════════════════════════════════════

  return (
    <div
      style={{
        minHeight: "100vh",
        backgroundColor: "#0A0A0B",
        color: "#E0E0E0",
        padding: "1.5rem",
        fontFamily: "'Segoe UI', system-ui, monospace",
      }}
    >
      <div style={{ maxWidth: "1400px", margin: "0 auto" }}>
        {/* ── Header ── */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            marginBottom: "1.5rem",
            flexWrap: "wrap",
            gap: "0.5rem",
          }}
        >
          <h1 style={{ margin: 0, fontSize: "1.4rem", letterSpacing: "0.1em" }}>
            ENGENHARIA <span style={{ color: "#00A1FF" }}>CAD</span> — Controle
            AutoCAD
            {driverStatus?.engine && driverStatus.engine !== "Unknown" && (
              <span
                style={{
                  marginLeft: "0.75rem",
                  fontSize: "0.75rem",
                  fontWeight: 600,
                  padding: "0.2rem 0.6rem",
                  borderRadius: "4px",
                  backgroundColor:
                    driverStatus.engine === "GstarCAD" ? "#1a3a1e" : "#1e2a3f",
                  border: `1px solid ${driverStatus.engine === "GstarCAD" ? "#00FF87" : "#00A1FF"}`,
                  color:
                    driverStatus.engine === "GstarCAD" ? "#00FF87" : "#00A1FF",
                  verticalAlign: "middle",
                }}
              >
                ⚙ Engine: {driverStatus.engine}
              </span>
            )}
          </h1>
          <label
            style={{
              display: "flex",
              alignItems: "center",
              gap: "0.5rem",
              fontSize: "0.8rem",
              color: "#888",
            }}
          >
            <input
              type="checkbox"
              checked={polling}
              onChange={(e) => setPolling(e.target.checked)}
            />
            Auto-refresh status (3s)
          </label>
        </div>

        {/* ═══ PAINEL 1: Status Real-time ═══ */}
        <section style={sectionStyle}>
          <h2 style={sectionTitle}>1. Status Real-time do Driver</h2>
          {driverStatus ? (
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
                gap: "0.75rem",
              }}
            >
              <StatusCard
                label="Modo"
                value={driverStatus.mode.toUpperCase()}
                color={statusColor(driverStatus.status)}
              />
              <StatusCard
                label="Engine"
                value={driverStatus.engine || "Unknown"}
                color={
                  driverStatus.engine === "GstarCAD"
                    ? "#00FF87"
                    : driverStatus.engine === "AutoCAD"
                      ? "#00BFFF"
                      : "#888"
                }
              />
              <StatusCard
                label="Status"
                value={driverStatus.status}
                color={statusColor(driverStatus.status)}
              />
              <StatusCard
                label="Buffer"
                value={`${driverStatus.buffer_size} cmds`}
                color="#FFD700"
              />
              <StatusCard
                label="Operações"
                value={`${driverStatus.operations_success}/${driverStatus.operations_total}`}
                color="#00FF87"
              />
              <StatusCard
                label="Falhas"
                value={String(driverStatus.operations_failed)}
                color={
                  driverStatus.operations_failed > 0 ? "#FF4444" : "#00FF87"
                }
              />
              <StatusCard
                label="Commits"
                value={String(driverStatus.bridge_commits)}
                color="#00BFFF"
              />
              <StatusCard
                label="Cmds Enviados"
                value={String(driverStatus.bridge_commands_sent)}
                color="#00BFFF"
              />
              {driverStatus.last_error && (
                <div
                  style={{
                    gridColumn: "1 / -1",
                    padding: "0.5rem",
                    backgroundColor: "#2a0000",
                    border: "1px solid #FF4444",
                    borderRadius: "4px",
                    fontSize: "0.8rem",
                    color: "#FF4444",
                  }}
                >
                  Último erro: {driverStatus.last_error}
                </div>
              )}
            </div>
          ) : (
            <div style={{ color: "#FF4444" }}>
              Driver offline ou inacessível — verifique se o servidor está
              rodando em {API}
            </div>
          )}
          <div
            style={{
              display: "flex",
              gap: "0.5rem",
              marginTop: "0.75rem",
              flexWrap: "wrap",
            }}
          >
            <Btn onClick={handleConnect} label="Conectar" />
            <Btn
              onClick={handleDisconnect}
              label="Desconectar"
              variant="secondary"
            />
            <Btn
              onClick={handleSetModeBridge}
              label="Modo PONTE"
              variant={driverStatus?.mode === "bridge" ? "active" : "default"}
            />
            <Btn
              onClick={handleSetModeCOM}
              label="Modo COM"
              variant={driverStatus?.mode === "com" ? "active" : "default"}
            />
          </div>
        </section>

        {/* ═══ PAINEL 2: Configurador de Caminho ═══ */}
        <section style={sectionStyle}>
          <h2 style={sectionTitle}>
            2. Configurar Caminho da Ponte (Bridge Path)
          </h2>
          <div
            style={{
              display: "flex",
              gap: "0.5rem",
              alignItems: "center",
              flexWrap: "wrap",
            }}
          >
            <input
              type="text"
              value={bridgePath}
              onChange={(e) => setBridgePath(e.target.value)}
              placeholder={
                driverStatus?.bridge_path ||
                "Ex: Z:/AutoCAD_Drop/ ou C:/EngenhariaCAD/bridge/"
              }
              style={inputStyle}
            />
            <Btn onClick={handleSetBridgePath} label="Salvar Caminho" />
          </div>
          {driverStatus?.bridge_path && (
            <div
              style={{ marginTop: "0.5rem", fontSize: "0.8rem", color: "#888" }}
            >
              Caminho atual:{" "}
              <span style={{ color: "#00BFFF" }}>
                {driverStatus.bridge_path}
              </span>
            </div>
          )}
        </section>

        {/* ═══ PAINEL 3: Comandos Rápidos N-58 ═══ */}
        <section style={sectionStyle}>
          <h2 style={sectionTitle}>3. Comandos Rápidos N-58</h2>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: "1rem",
            }}
          >
            {/* ── Traçar Tubo ── */}
            <div style={cardStyle}>
              <h3 style={cardTitle}>Traçar Tubo</h3>
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "1fr 1fr",
                  gap: "0.5rem",
                }}
              >
                <div>
                  <label style={labelStyle}>Ponto A (x, y, z)</label>
                  <div style={{ display: "flex", gap: "0.25rem" }}>
                    <input
                      style={coordInput}
                      value={pipeAx}
                      onChange={(e) => setPipeAx(e.target.value)}
                      placeholder="X"
                    />
                    <input
                      style={coordInput}
                      value={pipeAy}
                      onChange={(e) => setPipeAy(e.target.value)}
                      placeholder="Y"
                    />
                    <input
                      style={coordInput}
                      value={pipeAz}
                      onChange={(e) => setPipeAz(e.target.value)}
                      placeholder="Z"
                    />
                  </div>
                </div>
                <div>
                  <label style={labelStyle}>Ponto B (x, y, z)</label>
                  <div style={{ display: "flex", gap: "0.25rem" }}>
                    <input
                      style={coordInput}
                      value={pipeBx}
                      onChange={(e) => setPipeBx(e.target.value)}
                      placeholder="X"
                    />
                    <input
                      style={coordInput}
                      value={pipeBy}
                      onChange={(e) => setPipeBy(e.target.value)}
                      placeholder="Y"
                    />
                    <input
                      style={coordInput}
                      value={pipeBz}
                      onChange={(e) => setPipeBz(e.target.value)}
                      placeholder="Z"
                    />
                  </div>
                </div>
              </div>
              <div style={{ marginTop: "0.5rem" }}>
                <label style={labelStyle}>Diâmetro</label>
                <select
                  style={selectStyle}
                  value={pipeDiameter}
                  onChange={(e) => setPipeDiameter(Number(e.target.value))}
                >
                  {DIAMETERS.map((d) => (
                    <option key={d.value} value={d.value}>
                      {d.label}
                    </option>
                  ))}
                </select>
              </div>
              <Btn
                onClick={handleDrawPipe}
                label="Traçar Tubo"
                style={{ marginTop: "0.75rem", width: "100%" }}
              />
            </div>

            {/* ── Inserir Válvula / Componente ── */}
            <div style={cardStyle}>
              <h3 style={cardTitle}>Inserir Válvula / Componente</h3>
              <label style={labelStyle}>Bloco</label>
              <select
                style={selectStyle}
                value={valveBlock}
                onChange={(e) => setValveBlock(e.target.value)}
              >
                {VALVE_BLOCKS.map((b) => (
                  <option key={b} value={b}>
                    {b}
                  </option>
                ))}
              </select>
              <label style={{ ...labelStyle, marginTop: "0.5rem" }}>
                Ponto de Inserção (x, y, z)
              </label>
              <div style={{ display: "flex", gap: "0.25rem" }}>
                <input
                  style={coordInput}
                  value={valveX}
                  onChange={(e) => setValveX(e.target.value)}
                  placeholder="X"
                />
                <input
                  style={coordInput}
                  value={valveY}
                  onChange={(e) => setValveY(e.target.value)}
                  placeholder="Y"
                />
                <input
                  style={coordInput}
                  value={valveZ}
                  onChange={(e) => setValveZ(e.target.value)}
                  placeholder="Z"
                />
              </div>
              <div
                style={{ display: "flex", gap: "0.5rem", marginTop: "0.5rem" }}
              >
                <div style={{ flex: 1 }}>
                  <label style={labelStyle}>Rotação (°)</label>
                  <input
                    style={coordInput}
                    value={valveRotation}
                    onChange={(e) => setValveRotation(e.target.value)}
                    placeholder="0"
                  />
                </div>
                <div style={{ flex: 1 }}>
                  <label style={labelStyle}>Escala</label>
                  <input
                    style={coordInput}
                    value={valveScale}
                    onChange={(e) => setValveScale(e.target.value)}
                    placeholder="1"
                  />
                </div>
              </div>
              <Btn
                onClick={handleInsertValve}
                label="Inserir Componente"
                style={{ marginTop: "0.75rem", width: "100%" }}
              />
            </div>
          </div>

          {/* ── Ações de Finalização ── */}
          <div
            style={{
              display: "flex",
              gap: "0.5rem",
              marginTop: "1rem",
              flexWrap: "wrap",
            }}
          >
            <Btn
              onClick={handleCreateLayers}
              label="Criar Layers N-58"
              variant="secondary"
            />
            <Btn onClick={handleFinalize} label="Finalizar Visualização" />
            <Btn
              onClick={handleCommit}
              label="Commit Buffer → .lsp"
              variant="active"
            />
            <Btn
              onClick={handleSave}
              label="Salvar Documento"
              variant="secondary"
            />
            <Btn
              onClick={handleGetBuffer}
              label="Ver Buffer"
              variant="secondary"
            />
            <Btn
              onClick={handleGetHealth}
              label="Health Check"
              variant="secondary"
            />
          </div>
        </section>

        {/* ═══ PAINEL 4: Operações Adicionais — Texto, Linha, Comando ═══ */}
        <section style={sectionStyle}>
          <h2 style={sectionTitle}>4. Operações Adicionais</h2>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr 1fr",
              gap: "1rem",
            }}
          >
            {/* ── Adicionar Texto ── */}
            <div style={cardStyle}>
              <h3 style={cardTitle}>Adicionar Texto (Anotação)</h3>
              <label style={labelStyle}>Texto</label>
              <input
                style={{ ...inputStyle, width: "100%", minWidth: 0 }}
                value={textContent}
                onChange={(e) => setTextContent(e.target.value)}
                placeholder="Ex: TAG-001"
              />
              <label style={{ ...labelStyle, marginTop: "0.5rem" }}>
                Posição (x, y, z)
              </label>
              <div style={{ display: "flex", gap: "0.25rem" }}>
                <input
                  style={coordInput}
                  value={textX}
                  onChange={(e) => setTextX(e.target.value)}
                  placeholder="X"
                />
                <input
                  style={coordInput}
                  value={textY}
                  onChange={(e) => setTextY(e.target.value)}
                  placeholder="Y"
                />
                <input
                  style={coordInput}
                  value={textZ}
                  onChange={(e) => setTextZ(e.target.value)}
                  placeholder="Z"
                />
              </div>
              <label style={{ ...labelStyle, marginTop: "0.5rem" }}>
                Altura
              </label>
              <input
                style={coordInput}
                value={textHeight}
                onChange={(e) => setTextHeight(e.target.value)}
                placeholder="2.5"
              />
              <Btn
                onClick={handleAddText}
                label="Inserir Texto"
                style={{ marginTop: "0.75rem", width: "100%" }}
              />
            </div>

            {/* ── Desenhar Linha ── */}
            <div style={cardStyle}>
              <h3 style={cardTitle}>Desenhar Linha Simples</h3>
              <label style={labelStyle}>Início (x, y)</label>
              <div style={{ display: "flex", gap: "0.25rem" }}>
                <input
                  style={coordInput}
                  value={lineStartX}
                  onChange={(e) => setLineStartX(e.target.value)}
                  placeholder="X"
                />
                <input
                  style={coordInput}
                  value={lineStartY}
                  onChange={(e) => setLineStartY(e.target.value)}
                  placeholder="Y"
                />
              </div>
              <label style={{ ...labelStyle, marginTop: "0.5rem" }}>
                Fim (x, y)
              </label>
              <div style={{ display: "flex", gap: "0.25rem" }}>
                <input
                  style={coordInput}
                  value={lineEndX}
                  onChange={(e) => setLineEndX(e.target.value)}
                  placeholder="X"
                />
                <input
                  style={coordInput}
                  value={lineEndY}
                  onChange={(e) => setLineEndY(e.target.value)}
                  placeholder="Y"
                />
              </div>
              <Btn
                onClick={handleDrawLine}
                label="Desenhar Linha"
                style={{ marginTop: "0.75rem", width: "100%" }}
              />
            </div>

            {/* ── Comando Direto ── */}
            <div style={cardStyle}>
              <h3 style={cardTitle}>Comando Direto (LISP / Nativo)</h3>
              <label style={labelStyle}>Comando</label>
              <textarea
                style={{
                  ...inputStyle,
                  width: "100%",
                  minWidth: 0,
                  minHeight: "80px",
                  fontFamily: "monospace",
                  resize: "vertical",
                }}
                value={rawCommand}
                onChange={(e) => setRawCommand(e.target.value)}
                placeholder='Ex: (command "_CIRCLE" "0,0" 100)'
              />
              <Btn
                onClick={handleSendCommand}
                label="Enviar Comando"
                style={{ marginTop: "0.75rem", width: "100%" }}
                variant="active"
              />
            </div>
          </div>
        </section>

        {/* ═══ PAINEL 5: Batch Draw (Desenho em Lote) ═══ */}
        <section style={sectionStyle}>
          <h2 style={sectionTitle}>
            5. Batch Draw — Desenho em Lote (AI Orchestrator)
          </h2>
          <p
            style={{
              fontSize: "0.8rem",
              color: "#666",
              margin: "0 0 0.75rem 0",
            }}
          >
            Envie um JSON com múltiplas tubulações + componentes. O sistema
            executa tudo em sequência e faz auto-commit em modo PONTE.
          </p>
          <textarea
            style={{
              width: "100%",
              minHeight: "180px",
              padding: "0.75rem",
              borderRadius: "4px",
              border: "1px solid #333",
              backgroundColor: "#0A0A0B",
              color: "#E0E0E0",
              fontFamily: "'Cascadia Code', 'Fira Code', monospace",
              fontSize: "0.8rem",
              resize: "vertical",
            }}
            value={batchJson}
            onChange={(e) => setBatchJson(e.target.value)}
          />
          <Btn
            onClick={handleBatchDraw}
            label={batchRunning ? "Executando..." : "Executar Batch Draw"}
            variant="active"
            style={{ marginTop: "0.75rem" }}
          />
        </section>

        {/* ═══ PAINEL 6: Health / Diagnóstico ═══ */}
        {healthData && (
          <section style={sectionStyle}>
            <h2 style={sectionTitle}>6. Diagnóstico Detalhado (Health)</h2>
            <pre
              style={{
                backgroundColor: "#000",
                border: "1px solid #222",
                borderRadius: "4px",
                padding: "0.75rem",
                color: "#aaa",
                fontSize: "0.75rem",
                whiteSpace: "pre-wrap",
                wordBreak: "break-all",
                maxHeight: "200px",
                overflowY: "auto",
              }}
            >
              {JSON.stringify(healthData, null, 2)}
            </pre>
          </section>
        )}

        {/* ═══ PAINEL 7: Console de Retorno ═══ */}
        <section style={sectionStyle}>
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
            }}
          >
            <h2 style={sectionTitle}>7. Console de Retorno</h2>
            <Btn onClick={handleClearLog} label="Limpar" variant="secondary" />
          </div>
          <div
            ref={logRef}
            style={{
              backgroundColor: "#000",
              border: "1px solid #222",
              borderRadius: "4px",
              padding: "0.75rem",
              height: "320px",
              overflowY: "auto",
              fontFamily: "'Cascadia Code', 'Fira Code', 'Consolas', monospace",
              fontSize: "0.8rem",
              lineHeight: "1.6",
            }}
          >
            {logs.length === 0 && (
              <div style={{ color: "#444" }}>Aguardando comandos...</div>
            )}
            {logs.map((entry, i) => (
              <div key={i}>
                <span style={{ color: "#555" }}>[{entry.ts}]</span>{" "}
                <span style={{ color: logColor(entry.level), fontWeight: 700 }}>
                  [{entry.level}]
                </span>{" "}
                <span>{entry.text}</span>
                {entry.json && (
                  <pre
                    style={{
                      margin: "0.2rem 0 0.5rem 2rem",
                      color: "#aaa",
                      fontSize: "0.75rem",
                      whiteSpace: "pre-wrap",
                      wordBreak: "break-all",
                    }}
                  >
                    {JSON.stringify(entry.json, null, 2)}
                  </pre>
                )}
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════
// COMPONENTES AUXILIARES (Funcionalidade pura, CSS mínimo)
// ═══════════════════════════════════════════════════════════════════════

const StatusCard: React.FC<{ label: string; value: string; color: string }> = ({
  label,
  value,
  color,
}) => (
  <div
    style={{
      backgroundColor: "#111",
      border: "1px solid #222",
      borderRadius: "4px",
      padding: "0.6rem 0.8rem",
    }}
  >
    <div
      style={{
        fontSize: "0.7rem",
        color: "#666",
        textTransform: "uppercase",
        letterSpacing: "0.05em",
      }}
    >
      {label}
    </div>
    <div
      style={{
        fontSize: "1.1rem",
        fontWeight: 700,
        color,
        marginTop: "0.2rem",
      }}
    >
      {value}
    </div>
  </div>
);

const Btn: React.FC<{
  onClick: () => void;
  label: string;
  variant?: "default" | "secondary" | "active";
  style?: React.CSSProperties;
}> = ({ onClick, label, variant = "default", style }) => {
  const bg =
    variant === "active"
      ? "#00A1FF"
      : variant === "secondary"
        ? "#1a1a1e"
        : "#1e3a2f";
  const border =
    variant === "active"
      ? "#00A1FF"
      : variant === "secondary"
        ? "#333"
        : "#00FF87";
  const color =
    variant === "active"
      ? "#fff"
      : variant === "secondary"
        ? "#aaa"
        : "#00FF87";

  return (
    <button
      onClick={onClick}
      style={{
        padding: "0.5rem 1rem",
        borderRadius: "4px",
        border: `1px solid ${border}`,
        backgroundColor: bg,
        color,
        fontWeight: 600,
        fontSize: "0.8rem",
        cursor: "pointer",
        ...style,
      }}
    >
      {label}
    </button>
  );
};

// ── Estilos inline (funcionalidade primeiro, CSS refinado depois) ──

const sectionStyle: React.CSSProperties = {
  backgroundColor: "#0D0D0F",
  border: "1px solid #1a1c22",
  borderRadius: "6px",
  padding: "1.25rem",
  marginBottom: "1rem",
};

const sectionTitle: React.CSSProperties = {
  margin: "0 0 0.75rem 0",
  fontSize: "0.9rem",
  fontWeight: 700,
  textTransform: "uppercase",
  letterSpacing: "0.08em",
  color: "#888",
};

const cardStyle: React.CSSProperties = {
  backgroundColor: "#111",
  border: "1px solid #222",
  borderRadius: "4px",
  padding: "1rem",
};

const cardTitle: React.CSSProperties = {
  margin: "0 0 0.75rem 0",
  fontSize: "0.85rem",
  fontWeight: 700,
  color: "#00A1FF",
};

const labelStyle: React.CSSProperties = {
  display: "block",
  fontSize: "0.75rem",
  color: "#666",
  marginBottom: "0.25rem",
  textTransform: "uppercase",
  letterSpacing: "0.04em",
};

const inputStyle: React.CSSProperties = {
  flex: 1,
  padding: "0.5rem 0.75rem",
  borderRadius: "4px",
  border: "1px solid #333",
  backgroundColor: "#111",
  color: "#E0E0E0",
  fontSize: "0.85rem",
  minWidth: "200px",
};

const coordInput: React.CSSProperties = {
  flex: 1,
  padding: "0.4rem 0.5rem",
  borderRadius: "4px",
  border: "1px solid #333",
  backgroundColor: "#0A0A0B",
  color: "#E0E0E0",
  fontSize: "0.85rem",
  textAlign: "center",
};

const selectStyle: React.CSSProperties = {
  width: "100%",
  padding: "0.5rem",
  borderRadius: "4px",
  border: "1px solid #333",
  backgroundColor: "#0A0A0B",
  color: "#E0E0E0",
  fontSize: "0.85rem",
};

export default AutoCADControl;
