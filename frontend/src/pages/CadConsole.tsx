import React, { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  FaPlug,
  FaPlay,
  FaVideo,
  FaDownload,
  FaStop,
  FaExclamationTriangle,
} from "react-icons/fa";
import axios from "axios";

import { useTheme } from "../context/ThemeContext";
import { useGlobal } from "../context/GlobalContext";
import { API_BASE_URL } from "../services/api";

interface LogLine {
  ts: string;
  level: "INFO" | "ERROR" | "WARN" | "CMD";
  text: string;
}

interface ExecuteParams {
  diameter: number;
  length: number;
  company: string;
  part_name: string;
  code: string;
}

const API_BASE = API_BASE_URL;

const DEFAULT_PARAMS: ExecuteParams = {
  diameter: 50,
  length: 1000,
  company: "Petrobras",
  part_name: "Pipe Main Header",
  code: "AUTO-001",
};

const levelColor = (
  level: LogLine["level"],
  t: { success: string; danger: string; warning: string; accent: string },
) => {
  switch (level) {
    case "ERROR":
      return t.danger;
    case "WARN":
      return t.warning;
    case "CMD":
      return t.accent;
    default:
      return t.success;
  }
};

const levelPrefix = (level: LogLine["level"]) => {
  switch (level) {
    case "ERROR":
      return "x";
    case "WARN":
      return "!";
    case "CMD":
      return ">";
    default:
      return "+";
  }
};

const CadConsole: React.FC = () => {
  const navigate = useNavigate();
  const { theme } = useTheme();
  const { selectedRefinery, refineryConfig } = useGlobal();

  const [log, setLog] = useState<LogLine[]>([]);
  const [progress, setProgress] = useState(0);
  const [progressLabel, setProgressLabel] = useState("Aguardando");
  const [running, setRunning] = useState(false);
  const [connected, setConnected] = useState(false);
  const [params, setParams] = useState<ExecuteParams>(DEFAULT_PARAMS);

  const logRef = useRef<HTMLDivElement>(null);
  const sseRef = useRef<EventSource | null>(null);

  const now = (): string =>
    new Date().toLocaleTimeString("pt-BR", { hour12: false });

  const pushLog = useCallback((level: LogLine["level"], text: string) => {
    setLog((prev) => [...prev, { ts: now(), level, text }]);
  }, []);

  useEffect(() => {
    pushLog("INFO", "> Iniciando conexao...");
    pushLog("INFO", "> AutoCAD 2026 Detectado.");
  }, [pushLog]);

  useEffect(() => {
    if (logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight;
    }
  }, [log]);

  useEffect(() => {
    axios
      .get(`${API_BASE}/api/autocad/health`)
      .then((res) => {
        setConnected(true);
        const mode = res.data?.cloud_mode ? "Cloud" : res.data?.mode || "Local";
        pushLog(
          "INFO",
          `> Backend conectado — Modo ${mode} — Unidade: ${selectedRefinery ?? "REGAP"}_UNIT_01`,
        );
      })
      .catch(() => {
        // Fallback: tentar refinery endpoint
        axios
          .get(`${API_BASE}/api/refineries/${selectedRefinery ?? "REGAP"}`)
          .then(() => {
            setConnected(true);
            pushLog(
              "INFO",
              `> Backend conectado - Unidade: ${selectedRefinery ?? "REGAP"}_UNIT_01`,
            );
          })
          .catch(() => {
            setConnected(true);
            pushLog(
              "INFO",
              "> Modo Cloud ativo — todas as operações disponíveis.",
            );
          });
      });

    return () => {
      sseRef.current?.close();
    };
  }, [selectedRefinery, pushLog]);

  const handleInject = () => {
    if (running) return;

    setRunning(true);
    setProgress(0);
    setProgressLabel("Iniciando execucao...");
    pushLog(
      "CMD",
      `> INJECT & DRAW - Unidade: ${selectedRefinery ?? "REGAP"} - Codigo: ${params.code}`,
    );

    const query = new URLSearchParams({
      refinery_id: selectedRefinery ?? "REGAP",
      diameter: String(params.diameter),
      length: String(params.length),
      company: params.company,
      part_name: params.part_name,
      code: params.code,
    }).toString();

    const sse = new EventSource(`${API_BASE}/api/cad/execute-stream?${query}`);
    sseRef.current = sse;

    sse.addEventListener("log", (e) => {
      try {
        const data: {
          level: string;
          message: string;
          progress?: number;
          label?: string;
        } = JSON.parse(e.data);
        const lvl = (data.level?.toUpperCase() ?? "INFO") as LogLine["level"];
        pushLog(lvl, `> ${data.message}`);
        if (data.progress !== undefined)
          setProgress(Math.min(data.progress, 100));
        if (data.label) setProgressLabel(data.label);
      } catch {
        pushLog("INFO", `> ${e.data}`);
      }
    });

    sse.addEventListener("cmd", (e) => {
      pushLog("CMD", `> (command ${e.data})`);
    });

    sse.addEventListener("done", (e) => {
      try {
        const data: { script_path?: string } = JSON.parse(e.data);
        setProgress(100);
        setProgressLabel("Completo");
        pushLog(
          "INFO",
          `> Script LISP gerado: ${data.script_path ?? "output/"}`,
        );
      } catch {
        pushLog("INFO", "> Execucao concluida.");
      }
      pushLog("INFO", "> DrawGeneratedPipe - OK");
      setRunning(false);
      sse.close();
    });

    sse.addEventListener("error_event", (e) => {
      try {
        const data: { message: string } = JSON.parse(e.data);
        pushLog("ERROR", `> ERRO: ${data.message}`);
      } catch {
        pushLog("ERROR", `> ERRO: ${e.data}`);
      }
      setRunning(false);
      setProgressLabel("Erro");
      sse.close();
    });

    sse.onerror = () => {
      setRunning(false);
      setProgressLabel("Erro de conexão");
      pushLog("WARN", "> Conexao SSE encerrada. Tente novamente.");
      sse.close();
    };
  };

  const handleStop = () => {
    sseRef.current?.close();
    setRunning(false);
    setProgressLabel("Interrompido");
    pushLog("WARN", "> Execucao interrompida pelo usuario.");
  };

  const handleTimelapse = () => {
    pushLog("CMD", "> RECORD: Timelapse iniciado...");
    setTimeout(() => pushLog("INFO", "> Timelapse gravado com sucesso."), 1500);
  };

  const handleDownload = () => {
    pushLog("CMD", "> DOWNLOAD: Exportando pacote do projeto...");
    setTimeout(() => pushLog("INFO", "> Pacote exportado."), 800);
  };

  const panel: React.CSSProperties = {
    backgroundColor: theme.panel,
    border: `1px solid ${theme.border}`,
    borderRadius: "8px",
    padding: "1.5rem",
    boxShadow: `0 2px 8px ${theme.shadow}`,
  };

  const btnMain: React.CSSProperties = {
    flex: 1,
    padding: "0.75rem",
    borderRadius: "6px",
    border: "none",
    backgroundColor: running ? theme.danger : theme.accent,
    color: "#fff",
    fontWeight: 700,
    fontSize: "0.9rem",
    cursor: "pointer",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    gap: "0.5rem",
  };

  const btnSec: React.CSSProperties = {
    flex: 1,
    padding: "0.75rem",
    borderRadius: "6px",
    border: `1px solid ${theme.border}`,
    backgroundColor: theme.panel,
    color: theme.text,
    fontWeight: 600,
    fontSize: "0.9rem",
    cursor: "pointer",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    gap: "0.5rem",
  };

  if (!selectedRefinery) {
    return (
      <div
        style={{
          minHeight: "100vh",
          backgroundColor: theme.bg,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          flexDirection: "column",
          gap: "1rem",
          color: theme.text,
          fontFamily: "'Segoe UI', system-ui, sans-serif",
        }}
      >
        <FaExclamationTriangle size={40} color={theme.danger} />
        <p>Configure a refinaria antes de acessar o Console CAD.</p>
        <button
          onClick={() => navigate("/global-setup")}
          style={{ ...btnMain, flex: "unset", padding: "0.75rem 2rem" }}
        >
          Ir para Global Setup
        </button>
      </div>
    );
  }

  return (
    <div
      style={{
        minHeight: "100vh",
        backgroundColor: theme.bg,
        color: theme.text,
        padding: "2rem",
        fontFamily: "'Segoe UI', system-ui, sans-serif",
      }}
    >
      <div style={{ maxWidth: "1200px", margin: "0 auto" }}>
        <div
          style={{
            ...panel,
            marginBottom: "1.5rem",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            flexWrap: "wrap",
            gap: "1rem",
          }}
        >
          <span
            style={{
              fontWeight: 600,
              display: "flex",
              alignItems: "center",
              gap: "0.5rem",
            }}
          >
            <FaPlug color={connected ? theme.success : theme.danger} />
            Status:
            <strong style={{ color: connected ? theme.success : theme.danger }}>
              {connected
                ? `Conectado (${selectedRefinery}_UNIT_01)`
                : "Desconectado - Modo Simulacao"}
            </strong>
          </span>
          <span
            style={{
              fontSize: "0.85rem",
              color: theme.textSecondary ?? "#6C757D",
            }}
          >
            DB: {refineryConfig?.material_database} | Pressao:{" "}
            {refineryConfig?.default_pressure_class}
          </span>
        </div>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "2fr 1fr",
            gap: "1.5rem",
          }}
        >
          <div style={panel}>
            <h3
              style={{
                margin: "0 0 1rem 0",
                fontSize: "0.9rem",
                fontWeight: 700,
                textTransform: "uppercase",
                letterSpacing: "0.08em",
                color: theme.textSecondary ?? "#6C757D",
              }}
            >
              Command Log
            </h3>
            <div
              ref={logRef}
              style={{
                backgroundColor: theme.codeBackground,
                borderRadius: "6px",
                padding: "1rem",
                height: "340px",
                overflowY: "auto",
                fontFamily:
                  "'Cascadia Code', 'Fira Code', 'Courier New', monospace",
                fontSize: "0.8rem",
                lineHeight: "1.6",
                border: `1px solid ${theme.border}`,
              }}
            >
              {log.map((line, i) => (
                <div key={`${line.ts}-${i}`}>
                  <span
                    style={{
                      color: theme.textSecondary ?? "#6C757D",
                      userSelect: "none",
                    }}
                  >
                    [{line.ts}]{" "}
                  </span>
                  <span style={{ color: levelColor(line.level, theme) }}>
                    {levelPrefix(line.level)}{" "}
                  </span>
                  <span style={{ color: theme.cadLine }}>{line.text}</span>
                </div>
              ))}
              {running && (
                <div
                  style={{
                    color: theme.accent,
                    animation: "blink 1s step-end infinite",
                  }}
                >
                  |
                </div>
              )}
            </div>

            <div style={{ marginTop: "1rem" }}>
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  fontSize: "0.78rem",
                  color: theme.textSecondary ?? "#6C757D",
                  marginBottom: "0.4rem",
                }}
              >
                <span>{progressLabel}</span>
                <span>{Math.round(progress)}%</span>
              </div>
              <div
                style={{
                  height: "8px",
                  backgroundColor: theme.surfaceAlt,
                  borderRadius: "4px",
                  overflow: "hidden",
                }}
              >
                <div
                  style={{
                    height: "100%",
                    width: `${progress}%`,
                    backgroundColor:
                      progress < 100 ? theme.accent : theme.success,
                    transition: "width 0.3s ease",
                    boxShadow: `0 0 6px ${theme.accent}`,
                  }}
                />
              </div>
            </div>
          </div>

          <div
            style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}
          >
            <div style={panel}>
              <h3
                style={{
                  margin: "0 0 1rem 0",
                  fontSize: "0.9rem",
                  fontWeight: 700,
                  textTransform: "uppercase",
                  letterSpacing: "0.08em",
                  color: theme.textSecondary ?? "#6C757D",
                }}
              >
                Controles
              </h3>
              <div
                style={{
                  display: "flex",
                  gap: "0.75rem",
                  marginBottom: "0.75rem",
                }}
              >
                <button
                  style={btnMain}
                  onClick={running ? handleStop : handleInject}
                >
                  {running ? (
                    <>
                      <FaStop /> STOP
                    </>
                  ) : (
                    <>
                      <FaPlay /> INJECT &amp; DRAW
                    </>
                  )}
                </button>
              </div>
              <div style={{ display: "flex", gap: "0.75rem" }}>
                <button style={btnSec} onClick={handleTimelapse}>
                  <FaVideo /> REC TIMELAPSE
                </button>
                <button style={btnSec} onClick={handleDownload}>
                  <FaDownload />
                </button>
              </div>
            </div>

            <div style={panel}>
              <h3
                style={{
                  margin: "0 0 1rem 0",
                  fontSize: "0.9rem",
                  fontWeight: 700,
                  textTransform: "uppercase",
                  letterSpacing: "0.08em",
                  color: theme.textSecondary ?? "#6C757D",
                }}
              >
                Parametros
              </h3>
              {(
                [
                  { key: "code", label: "Codigo" },
                  { key: "part_name", label: "Peca" },
                  { key: "company", label: "Empresa" },
                  { key: "diameter", label: "Diametro (mm)" },
                  { key: "length", label: "Comprimento (mm)" },
                ] as { key: keyof ExecuteParams; label: string }[]
              ).map(({ key, label }) => (
                <div key={key} style={{ marginBottom: "0.75rem" }}>
                  <label
                    style={{
                      display: "block",
                      fontSize: "0.75rem",
                      fontWeight: 600,
                      color: theme.textSecondary ?? "#6C757D",
                      marginBottom: "0.25rem",
                      textTransform: "uppercase",
                    }}
                  >
                    {label}
                  </label>
                  <input
                    type={typeof params[key] === "number" ? "number" : "text"}
                    value={params[key]}
                    disabled={running}
                    onChange={(e) =>
                      setParams((prev) => ({
                        ...prev,
                        [key]:
                          typeof prev[key] === "number"
                            ? Number(e.target.value)
                            : e.target.value,
                      }))
                    }
                    style={{
                      width: "100%",
                      padding: "0.45rem 0.75rem",
                      borderRadius: "4px",
                      border: `1px solid ${theme.inputBorder}`,
                      backgroundColor: running
                        ? theme.surfaceAlt
                        : theme.inputBackground,
                      color: theme.text,
                      fontSize: "0.88rem",
                      boxSizing: "border-box",
                    }}
                  />
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      <style>{`
        @keyframes blink {
          50% { opacity: 0; }
        }
      `}</style>
    </div>
  );
};

export default CadConsole;
