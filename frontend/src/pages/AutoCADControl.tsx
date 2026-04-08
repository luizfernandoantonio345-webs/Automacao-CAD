import React, { useCallback, useEffect, useRef, useState } from "react";
import axios from "axios";
import { API_BASE_URL } from "../services/api";
import { useToast } from "../context/ToastContext";
import { useSSE } from "../hooks/useSSE";
import { useTheme } from "../context/ThemeContext";

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
    const id = setInterval(fetchStatus, 8000);
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

  const { theme } = useTheme();
  const st = buildUIStyles(theme);

  return (
    <div style={st.page}>
      <div style={st.container}>
        {/* ── Header ── */}
        <header style={st.header}>
          <div>
            <h1 style={st.pageTitle}>
              ENGENHARIA <span style={{ color: theme.accentPrimary }}>CAD</span>
              <span style={st.badge}>Controle AutoCAD</span>
              {driverStatus?.engine && driverStatus.engine !== "Unknown" && (
                <span style={{
                  ...st.badge,
                  backgroundColor: driverStatus.engine === "GstarCAD" ? (theme.accentSecondary + "18") : (theme.accentPrimary + "18"),
                  color: driverStatus.engine === "GstarCAD" ? theme.accentSecondary : theme.accentPrimary,
                  border: `1px solid ${driverStatus.engine === "GstarCAD" ? theme.accentSecondary : theme.accentPrimary}30`,
                }}>
                  ⚙ {driverStatus.engine}
                </span>
              )}
            </h1>
            <p style={st.pageSubtitle}>Driver híbrido COM + Ponte de Rede • Norma N-58 Petrobras</p>
          </div>
          <label style={st.toggleLabel}>
            <input type="checkbox" checked={polling} onChange={(e) => setPolling(e.target.checked)} style={{ accentColor: theme.accentPrimary }} />
            <span>Auto-refresh (3s)</span>
          </label>
        </header>

        {/* ═══ PAINEL 1: Status ═══ */}
        <Section title="Status do Driver" theme={theme} st={st}>
          {driverStatus ? (
            <div style={st.statusGrid}>
              <MetricCard label="Modo" value={driverStatus.mode.toUpperCase()} color={statusColor(driverStatus.status)} theme={theme} st={st} />
              <MetricCard label="Engine" value={driverStatus.engine || "—"} color={driverStatus.engine === "GstarCAD" ? theme.accentSecondary : theme.accentPrimary} theme={theme} st={st} />
              <MetricCard label="Status" value={driverStatus.status} color={statusColor(driverStatus.status)} theme={theme} st={st} />
              <MetricCard label="Buffer" value={`${driverStatus.buffer_size} cmds`} color={theme.accentWarning} theme={theme} st={st} />
              <MetricCard label="Operações" value={`${driverStatus.operations_success}/${driverStatus.operations_total}`} color={theme.accentSecondary} theme={theme} st={st} />
              <MetricCard label="Falhas" value={String(driverStatus.operations_failed)} color={driverStatus.operations_failed > 0 ? theme.accentDanger : theme.accentSecondary} theme={theme} st={st} />
              <MetricCard label="Commits" value={String(driverStatus.bridge_commits)} color={theme.accentPrimary} theme={theme} st={st} />
              <MetricCard label="Enviados" value={String(driverStatus.bridge_commands_sent)} color={theme.accentPrimary} theme={theme} st={st} />
            </div>
          ) : (
            <div style={{ padding: "16px", color: theme.accentDanger, fontSize: "0.85rem", border: `1px solid ${theme.accentDanger}30`, borderRadius: 8, backgroundColor: theme.accentDanger + "08" }}>
              Driver offline ou inacessível — verifique se o servidor está rodando em {API}
            </div>
          )}
          {driverStatus?.last_error && (
            <div style={{ marginTop: 12, padding: "10px 14px", backgroundColor: theme.accentDanger + "0A", border: `1px solid ${theme.accentDanger}30`, borderRadius: 8, fontSize: "0.8rem", color: theme.accentDanger }}>
              Último erro: {driverStatus.last_error}
            </div>
          )}
          <div style={st.btnRow}>
            <ActionBtn onClick={handleConnect} label="Conectar" theme={theme} />
            <ActionBtn onClick={handleDisconnect} label="Desconectar" theme={theme} variant="ghost" />
            <ActionBtn onClick={handleSetModeBridge} label="Modo PONTE" theme={theme} variant={driverStatus?.mode === "bridge" ? "active" : "ghost"} />
            <ActionBtn onClick={handleSetModeCOM} label="Modo COM" theme={theme} variant={driverStatus?.mode === "com" ? "active" : "ghost"} />
          </div>
        </Section>

        {/* ═══ PAINEL 2: Bridge Path ═══ */}
        <Section title="Configurar Ponte (Bridge Path)" theme={theme} st={st}>
          <div style={st.inlineGroup}>
            <input
              type="text" value={bridgePath} onChange={(e) => setBridgePath(e.target.value)}
              placeholder={driverStatus?.bridge_path || "Ex: Z:/AutoCAD_Drop/"}
              style={st.input}
            />
            <ActionBtn onClick={handleSetBridgePath} label="Salvar" theme={theme} />
          </div>
          {driverStatus?.bridge_path && (
            <p style={st.hint}>Caminho atual: <span style={{ color: theme.accentPrimary }}>{driverStatus.bridge_path}</span></p>
          )}
        </Section>

        {/* ═══ PAINEL 3: Comandos N-58 ═══ */}
        <Section title="Comandos N-58 Petrobras" theme={theme} st={st}>
          <div style={st.grid2}>
            {/* ── Traçar Tubo ── */}
            <div style={st.card}>
              <h3 style={st.cardTitle}>Traçar Tubo</h3>
              <div style={st.grid2Inner}>
                <FieldGroup label="Ponto A (X, Y, Z)" theme={theme} st={st}>
                  <div style={st.coordRow}>
                    <input style={st.coordInput} value={pipeAx} onChange={(e) => setPipeAx(e.target.value)} placeholder="X" />
                    <input style={st.coordInput} value={pipeAy} onChange={(e) => setPipeAy(e.target.value)} placeholder="Y" />
                    <input style={st.coordInput} value={pipeAz} onChange={(e) => setPipeAz(e.target.value)} placeholder="Z" />
                  </div>
                </FieldGroup>
                <FieldGroup label="Ponto B (X, Y, Z)" theme={theme} st={st}>
                  <div style={st.coordRow}>
                    <input style={st.coordInput} value={pipeBx} onChange={(e) => setPipeBx(e.target.value)} placeholder="X" />
                    <input style={st.coordInput} value={pipeBy} onChange={(e) => setPipeBy(e.target.value)} placeholder="Y" />
                    <input style={st.coordInput} value={pipeBz} onChange={(e) => setPipeBz(e.target.value)} placeholder="Z" />
                  </div>
                </FieldGroup>
              </div>
              <FieldGroup label="Diâmetro" theme={theme} st={st}>
                <select style={st.select} value={pipeDiameter} onChange={(e) => setPipeDiameter(Number(e.target.value))}>
                  {DIAMETERS.map((d) => (<option key={d.value} value={d.value}>{d.label}</option>))}
                </select>
              </FieldGroup>
              <ActionBtn onClick={handleDrawPipe} label="Traçar Tubo" theme={theme} style={{ width: "100%", marginTop: 12 }} />
            </div>

            {/* ── Inserir Válvula ── */}
            <div style={st.card}>
              <h3 style={st.cardTitle}>Inserir Válvula / Componente</h3>
              <FieldGroup label="Bloco" theme={theme} st={st}>
                <select style={st.select} value={valveBlock} onChange={(e) => setValveBlock(e.target.value)}>
                  {VALVE_BLOCKS.map((b) => (<option key={b} value={b}>{b}</option>))}
                </select>
              </FieldGroup>
              <FieldGroup label="Ponto de Inserção (X, Y, Z)" theme={theme} st={st}>
                <div style={st.coordRow}>
                  <input style={st.coordInput} value={valveX} onChange={(e) => setValveX(e.target.value)} placeholder="X" />
                  <input style={st.coordInput} value={valveY} onChange={(e) => setValveY(e.target.value)} placeholder="Y" />
                  <input style={st.coordInput} value={valveZ} onChange={(e) => setValveZ(e.target.value)} placeholder="Z" />
                </div>
              </FieldGroup>
              <div style={st.grid2Inner}>
                <FieldGroup label="Rotação (°)" theme={theme} st={st}>
                  <input style={st.input} value={valveRotation} onChange={(e) => setValveRotation(e.target.value)} placeholder="0" />
                </FieldGroup>
                <FieldGroup label="Escala" theme={theme} st={st}>
                  <input style={st.input} value={valveScale} onChange={(e) => setValveScale(e.target.value)} placeholder="1" />
                </FieldGroup>
              </div>
              <ActionBtn onClick={handleInsertValve} label="Inserir Componente" theme={theme} style={{ width: "100%", marginTop: 12 }} />
            </div>
          </div>

          {/* Ações rápidas */}
          <div style={{ ...st.btnRow, marginTop: 16 }}>
            <ActionBtn onClick={handleCreateLayers} label="Criar Layers N-58" theme={theme} variant="ghost" />
            <ActionBtn onClick={handleFinalize} label="Finalizar Visualização" theme={theme} />
            <ActionBtn onClick={handleCommit} label="Commit → .lsp" theme={theme} variant="active" />
            <ActionBtn onClick={handleSave} label="Salvar Documento" theme={theme} variant="ghost" />
            <ActionBtn onClick={handleGetBuffer} label="Ver Buffer" theme={theme} variant="ghost" />
            <ActionBtn onClick={handleGetHealth} label="Health Check" theme={theme} variant="ghost" />
          </div>
        </Section>

        {/* ═══ PAINEL 4: Operações Adicionais ═══ */}
        <Section title="Operações Adicionais" theme={theme} st={st}>
          <div style={st.grid3}>
            {/* Texto */}
            <div style={st.card}>
              <h3 style={st.cardTitle}>Anotação de Texto</h3>
              <FieldGroup label="Texto" theme={theme} st={st}>
                <input style={st.input} value={textContent} onChange={(e) => setTextContent(e.target.value)} placeholder="Ex: TAG-001" />
              </FieldGroup>
              <FieldGroup label="Posição (X, Y, Z)" theme={theme} st={st}>
                <div style={st.coordRow}>
                  <input style={st.coordInput} value={textX} onChange={(e) => setTextX(e.target.value)} placeholder="X" />
                  <input style={st.coordInput} value={textY} onChange={(e) => setTextY(e.target.value)} placeholder="Y" />
                  <input style={st.coordInput} value={textZ} onChange={(e) => setTextZ(e.target.value)} placeholder="Z" />
                </div>
              </FieldGroup>
              <FieldGroup label="Altura" theme={theme} st={st}>
                <input style={st.input} value={textHeight} onChange={(e) => setTextHeight(e.target.value)} placeholder="2.5" />
              </FieldGroup>
              <ActionBtn onClick={handleAddText} label="Inserir Texto" theme={theme} style={{ width: "100%", marginTop: 8 }} />
            </div>

            {/* Linha */}
            <div style={st.card}>
              <h3 style={st.cardTitle}>Desenhar Linha</h3>
              <FieldGroup label="Início (X, Y)" theme={theme} st={st}>
                <div style={st.coordRow}>
                  <input style={st.coordInput} value={lineStartX} onChange={(e) => setLineStartX(e.target.value)} placeholder="X" />
                  <input style={st.coordInput} value={lineStartY} onChange={(e) => setLineStartY(e.target.value)} placeholder="Y" />
                </div>
              </FieldGroup>
              <FieldGroup label="Fim (X, Y)" theme={theme} st={st}>
                <div style={st.coordRow}>
                  <input style={st.coordInput} value={lineEndX} onChange={(e) => setLineEndX(e.target.value)} placeholder="X" />
                  <input style={st.coordInput} value={lineEndY} onChange={(e) => setLineEndY(e.target.value)} placeholder="Y" />
                </div>
              </FieldGroup>
              <ActionBtn onClick={handleDrawLine} label="Desenhar Linha" theme={theme} style={{ width: "100%", marginTop: 8 }} />
            </div>

            {/* Comando Direto */}
            <div style={st.card}>
              <h3 style={st.cardTitle}>Comando Direto (LISP)</h3>
              <FieldGroup label="Comando" theme={theme} st={st}>
                <textarea
                  style={{ ...st.input, minHeight: 80, fontFamily: "'Cascadia Code', 'Fira Code', monospace", resize: "vertical" as const }}
                  value={rawCommand} onChange={(e) => setRawCommand(e.target.value)}
                  placeholder='Ex: (command "_CIRCLE" "0,0" 100)'
                />
              </FieldGroup>
              <ActionBtn onClick={handleSendCommand} label="Enviar Comando" theme={theme} variant="active" style={{ width: "100%", marginTop: 8 }} />
            </div>
          </div>
        </Section>

        {/* ═══ PAINEL 5: Batch Draw ═══ */}
        <Section title="Batch Draw — Desenho em Lote" theme={theme} st={st}>
          <p style={st.hint}>Envie JSON com múltiplas tubulações + componentes. Execução sequencial com auto-commit em modo PONTE.</p>
          <textarea
            style={{ ...st.input, minHeight: 180, fontFamily: "'Cascadia Code', 'Fira Code', monospace", fontSize: "0.8rem", resize: "vertical" as const }}
            value={batchJson} onChange={(e) => setBatchJson(e.target.value)}
          />
          <ActionBtn onClick={handleBatchDraw} label={batchRunning ? "Executando..." : "Executar Batch Draw"} theme={theme} variant="active" style={{ marginTop: 12 }} />
        </Section>

        {/* ═══ PAINEL 6: Health ═══ */}
        {healthData && (
          <Section title="Diagnóstico (Health)" theme={theme} st={st}>
            <pre style={st.pre}>{JSON.stringify(healthData, null, 2)}</pre>
          </Section>
        )}

        {/* ═══ PAINEL 7: Console ═══ */}
        <Section title="Console de Retorno" theme={theme} st={st} action={<ActionBtn onClick={handleClearLog} label="Limpar" theme={theme} variant="ghost" />}>
          <div ref={logRef} style={st.console}>
            {logs.length === 0 && <div style={{ color: theme.textTertiary }}>Aguardando comandos...</div>}
            {logs.map((entry, i) => (
              <div key={i} style={{ marginBottom: 2 }}>
                <span style={{ color: theme.textTertiary }}>[{entry.ts}]</span>{" "}
                <span style={{ color: logColor(entry.level), fontWeight: 700 }}>[{entry.level}]</span>{" "}
                <span>{entry.text}</span>
                {entry.json && (
                  <pre style={{ margin: "2px 0 6px 24px", color: theme.textSecondary, fontSize: "0.75rem", whiteSpace: "pre-wrap", wordBreak: "break-all" as const }}>{JSON.stringify(entry.json, null, 2)}</pre>
                )}
              </div>
            ))}
          </div>
        </Section>
      </div>
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════
// COMPONENTES AUXILIARES (Design System Premium)
// ═══════════════════════════════════════════════════════════════════════

const Section: React.FC<{
  title: string;
  theme: any;
  st: ReturnType<typeof buildUIStyles>;
  children: React.ReactNode;
  action?: React.ReactNode;
}> = ({ title, theme, st, children, action }) => (
  <section style={st.section}>
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
      <h2 style={st.sectionTitle}>{title}</h2>
      {action}
    </div>
    {children}
  </section>
);

const FieldGroup: React.FC<{
  label: string;
  theme: any;
  st: ReturnType<typeof buildUIStyles>;
  children: React.ReactNode;
}> = ({ label, st, children }) => (
  <div style={{ marginBottom: 12 }}>
    <label style={st.label}>{label}</label>
    {children}
  </div>
);

const MetricCard: React.FC<{
  label: string;
  value: string;
  color: string;
  theme: any;
  st: ReturnType<typeof buildUIStyles>;
}> = ({ label, value, color, theme, st }) => (
  <div style={st.metricCard}>
    <div style={st.metricLabel}>{label}</div>
    <div style={{ ...st.metricValue, color }}>{value}</div>
  </div>
);

const ActionBtn: React.FC<{
  onClick: () => void;
  label: string;
  theme: any;
  variant?: "primary" | "ghost" | "active";
  style?: React.CSSProperties;
}> = ({ onClick, label, theme, variant = "primary", style }) => {
  const base: React.CSSProperties = {
    padding: "8px 18px",
    borderRadius: 8,
    fontSize: "0.82rem",
    fontWeight: 600,
    cursor: "pointer",
    transition: "all 0.15s ease",
    border: "1px solid transparent",
    fontFamily: "'Inter', -apple-system, sans-serif",
    ...style,
  };

  if (variant === "active") {
    return (
      <button onClick={onClick} style={{ ...base, backgroundColor: theme.accentPrimary, color: "#fff", border: `1px solid ${theme.accentPrimary}` }}>
        {label}
      </button>
    );
  }
  if (variant === "ghost") {
    return (
      <button onClick={onClick} style={{ ...base, backgroundColor: "transparent", color: theme.textSecondary, border: `1px solid ${theme.border}` }}>
        {label}
      </button>
    );
  }
  // primary
  return (
    <button onClick={onClick} style={{ ...base, backgroundColor: theme.accentSecondary + "18", color: theme.accentSecondary, border: `1px solid ${theme.accentSecondary}30` }}>
      {label}
    </button>
  );
};

// ── Design System Styles ──

function buildUIStyles(theme: any) {
  return {
    page: {
      minHeight: "100vh",
      backgroundColor: theme.background,
      color: theme.textPrimary,
      padding: "24px",
      fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
    } as React.CSSProperties,
    container: {
      maxWidth: 1400,
      margin: "0 auto",
    } as React.CSSProperties,

    // Header
    header: {
      display: "flex",
      alignItems: "flex-start",
      justifyContent: "space-between",
      marginBottom: 24,
      paddingBottom: 20,
      borderBottom: `1px solid ${theme.border}`,
    } as React.CSSProperties,
    pageTitle: {
      margin: 0,
      fontSize: "1.4rem",
      fontWeight: 700,
      letterSpacing: "0.06em",
      display: "flex",
      alignItems: "center",
      gap: 10,
      flexWrap: "wrap" as const,
    } as React.CSSProperties,
    pageSubtitle: {
      margin: "4px 0 0",
      fontSize: "0.78rem",
      color: theme.textTertiary,
      letterSpacing: "0.02em",
    } as React.CSSProperties,
    badge: {
      fontSize: "0.68rem",
      fontWeight: 600,
      padding: "3px 10px",
      borderRadius: 6,
      backgroundColor: theme.accentPrimary + "12",
      color: theme.accentPrimary,
      border: `1px solid ${theme.accentPrimary}25`,
      letterSpacing: "0.03em",
    } as React.CSSProperties,
    toggleLabel: {
      display: "flex",
      alignItems: "center",
      gap: 6,
      fontSize: "0.8rem",
      color: theme.textSecondary,
      cursor: "pointer",
    } as React.CSSProperties,

    // Section
    section: {
      backgroundColor: theme.surface,
      border: `1px solid ${theme.border}`,
      borderRadius: 12,
      padding: 24,
      marginBottom: 16,
      boxShadow: "0 2px 8px rgba(0,0,0,0.08)",
    } as React.CSSProperties,
    sectionTitle: {
      margin: 0,
      fontSize: "0.82rem",
      fontWeight: 700,
      textTransform: "uppercase" as const,
      letterSpacing: "0.08em",
      color: theme.textSecondary,
    } as React.CSSProperties,

    // Cards
    card: {
      backgroundColor: theme.surfaceAlt || theme.background,
      border: `1px solid ${theme.border}`,
      borderRadius: 10,
      padding: 20,
    } as React.CSSProperties,
    cardTitle: {
      margin: "0 0 16px",
      fontSize: "0.9rem",
      fontWeight: 600,
      color: theme.accentPrimary,
    } as React.CSSProperties,

    // Status grid
    statusGrid: {
      display: "grid",
      gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))",
      gap: 12,
    } as React.CSSProperties,
    metricCard: {
      backgroundColor: theme.surfaceAlt || theme.background,
      border: `1px solid ${theme.border}`,
      borderRadius: 8,
      padding: "12px 16px",
    } as React.CSSProperties,
    metricLabel: {
      fontSize: "0.68rem",
      color: theme.textTertiary,
      textTransform: "uppercase" as const,
      letterSpacing: "0.06em",
      marginBottom: 4,
    } as React.CSSProperties,
    metricValue: {
      fontSize: "1.15rem",
      fontWeight: 700,
    } as React.CSSProperties,

    // Grids
    grid2: {
      display: "grid",
      gridTemplateColumns: "1fr 1fr",
      gap: 16,
    } as React.CSSProperties,
    grid2Inner: {
      display: "grid",
      gridTemplateColumns: "1fr 1fr",
      gap: 12,
    } as React.CSSProperties,
    grid3: {
      display: "grid",
      gridTemplateColumns: "1fr 1fr 1fr",
      gap: 16,
    } as React.CSSProperties,

    // Inputs
    input: {
      width: "100%",
      padding: "10px 14px",
      borderRadius: 8,
      border: `1px solid ${theme.inputBorder || theme.border}`,
      backgroundColor: theme.inputBackground || theme.background,
      color: theme.textPrimary,
      fontSize: "0.85rem",
      fontFamily: "'Inter', sans-serif",
      outline: "none",
      transition: "border-color 0.15s, box-shadow 0.15s",
      boxSizing: "border-box" as const,
    } as React.CSSProperties,
    coordInput: {
      flex: 1,
      padding: "8px 10px",
      borderRadius: 8,
      border: `1px solid ${theme.inputBorder || theme.border}`,
      backgroundColor: theme.inputBackground || theme.background,
      color: theme.textPrimary,
      fontSize: "0.85rem",
      textAlign: "center" as const,
      outline: "none",
      transition: "border-color 0.15s",
    } as React.CSSProperties,
    coordRow: {
      display: "flex",
      gap: 6,
    } as React.CSSProperties,
    select: {
      width: "100%",
      padding: "10px 14px",
      borderRadius: 8,
      border: `1px solid ${theme.inputBorder || theme.border}`,
      backgroundColor: theme.inputBackground || theme.background,
      color: theme.textPrimary,
      fontSize: "0.85rem",
      outline: "none",
    } as React.CSSProperties,
    label: {
      display: "block",
      fontSize: "0.7rem",
      fontWeight: 600,
      color: theme.textTertiary,
      marginBottom: 6,
      textTransform: "uppercase" as const,
      letterSpacing: "0.06em",
    } as React.CSSProperties,

    // Misc
    inlineGroup: {
      display: "flex",
      gap: 10,
      alignItems: "center",
    } as React.CSSProperties,
    btnRow: {
      display: "flex",
      gap: 8,
      marginTop: 12,
      flexWrap: "wrap" as const,
    } as React.CSSProperties,
    hint: {
      fontSize: "0.78rem",
      color: theme.textTertiary,
      margin: "8px 0 0",
    } as React.CSSProperties,
    pre: {
      backgroundColor: theme.codeBackground || theme.background,
      border: `1px solid ${theme.border}`,
      borderRadius: 8,
      padding: 16,
      color: theme.textSecondary,
      fontSize: "0.75rem",
      whiteSpace: "pre-wrap" as const,
      wordBreak: "break-all" as const,
      maxHeight: 200,
      overflowY: "auto" as const,
    } as React.CSSProperties,
    console: {
      backgroundColor: theme.codeBackground || "#0D1117",
      border: `1px solid ${theme.border}`,
      borderRadius: 8,
      padding: 16,
      height: 320,
      overflowY: "auto" as const,
      fontFamily: "'Cascadia Code', 'Fira Code', 'Consolas', monospace",
      fontSize: "0.8rem",
      lineHeight: 1.6,
    } as React.CSSProperties,
  };
}

export default AutoCADControl;
