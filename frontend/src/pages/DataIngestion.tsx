import React, { useState, useRef } from "react";
import { useNavigate } from "react-router-dom";
import {
  FaUpload,
  FaPlay,
  FaCheckCircle,
  FaTimesCircle,
  FaSpinner,
} from "react-icons/fa";
import { ApiService } from "../services/api";
import { useTheme } from "../context/ThemeContext";

type UploadStatus = "idle" | "uploading" | "processing" | "done" | "error";

const DataIngestion = () => {
  const navigate = useNavigate();
  const { theme } = useTheme();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [status, setStatus] = useState<UploadStatus>("idle");
  const [logs, setLogs] = useState<string[]>([
    "[SISTEMA] Pronto para receber arquivo Excel (.xlsx)",
  ]);
  const [result, setResult] = useState<{
    count: number;
    files: string[];
    project_ids?: number[];
  } | null>(null);
  const [error, setError] = useState("");

  const addLog = (msg: string) => setLogs((prev) => [...prev, msg]);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const ext = file.name.split(".").pop()?.toLowerCase();
    if (ext !== "xlsx" && ext !== "xls") {
      setError("Apenas arquivos .xlsx ou .xls são aceitos.");
      return;
    }
    setSelectedFile(file);
    setError("");
    setResult(null);
    addLog(
      `[ARQUIVO] ${file.name} selecionado (${(file.size / 1024).toFixed(1)} KB)`,
    );
  };

  const handleUpload = async () => {
    if (!selectedFile) return;
    setStatus("uploading");
    setError("");
    addLog("[UPLOAD] Enviando arquivo para o servidor...");

    const formData = new FormData();
    formData.append("file", selectedFile);

    try {
      setStatus("processing");
      addLog("[MOTOR] Processando Excel via Motor de Engenharia...");
      addLog(
        "[MOTOR] Validando colunas: diâmetro, comprimento, empresa, código...",
      );

      const data = await ApiService.uploadExcel(formData);
      setResult({
        count: data.count,
        files: data.files,
        project_ids: (data as any).project_ids,
      });
      setStatus("done");
      addLog(`[SUCCESS] ${data.count} projeto(s) gerado(s) com sucesso!`);
      data.files.forEach((f: string) => {
        const name = f.split(/[/\\]/).pop() || f;
        addLog(`  → ${name}`);
      });
    } catch (err: any) {
      setStatus("error");
      const msg =
        err?.response?.data?.detail || err?.message || "Erro desconhecido";
      setError(msg);
      addLog(`[ERRO] ${msg}`);
    }
  };

  const statusColor: Record<UploadStatus, string> = {
    idle: theme.textSecondary,
    uploading: theme.accentPrimary,
    processing: theme.accentWarning,
    done: theme.accentSecondary,
    error: theme.accentDanger,
  };

  const statusText: Record<UploadStatus, string> = {
    idle: "Aguardando arquivo",
    uploading: "Enviando...",
    processing: "Processando...",
    done: "Concluído!",
    error: "Erro",
  };

  return (
    <div
      style={{
        ...ig.container,
        background: theme.gradientPage || theme.background,
        color: theme.textPrimary,
      }}
    >
      <div style={ig.grid}>
        {/* Upload & Console */}
        <div
          style={{
            ...ig.consoleCard,
            backgroundColor: theme.surface,
            border: `1px solid ${theme.border}`,
          }}
        >
          <div style={ig.cardHeader}>
            <h3 style={{ ...ig.title, color: theme.textSecondary }}>
              INGESTÃO DE DADOS — EXCEL
            </h3>
            <span
              style={{
                fontSize: 10,
                color: statusColor[status],
                display: "flex",
                alignItems: "center",
                gap: 5,
              }}
            >
              {status === "done" ? (
                <FaCheckCircle />
              ) : status === "error" ? (
                <FaTimesCircle />
              ) : status !== "idle" ? (
                <FaSpinner />
              ) : null}
              {statusText[status]}
            </span>
          </div>

          {/* Zona de upload */}
          <div
            style={ig.dropZone}
            onClick={() => fileInputRef.current?.click()}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".xlsx,.xls"
              style={{ display: "none" }}
              onChange={handleFileSelect}
            />
            <div style={{ marginBottom: 10 }}>
              <FaUpload size={32} color={theme.accentPrimary} />
            </div>
            <p style={{ color: theme.textSecondary, fontSize: 13 }}>
              {selectedFile
                ? selectedFile.name
                : "Clique ou arraste um arquivo Excel aqui"}
            </p>
            {selectedFile && (
              <p style={{ color: theme.textSecondary, fontSize: 11 }}>
                {(selectedFile.size / 1024).toFixed(1)} KB
              </p>
            )}
          </div>

          {/* Terminal de logs */}
          <div style={ig.terminal}>
            {logs.map((line, i) => (
              <p
                key={i}
                style={{
                  color: line.includes("[SUCCESS]")
                    ? theme.accentSecondary
                    : line.includes("[ERRO]")
                      ? theme.accentDanger
                      : line.includes("[MOTOR]")
                        ? theme.accentWarning
                        : line.includes("[UPLOAD]")
                          ? theme.accentPrimary
                          : theme.textSecondary,
                  margin: "2px 0",
                }}
              >
                {line}
              </p>
            ))}
          </div>

          {/* Ações */}
          <div style={ig.actionRow}>
            <button
              style={{
                ...ig.btn,
                backgroundColor:
                  selectedFile &&
                  status !== "uploading" &&
                  status !== "processing"
                    ? theme.accentPrimary
                    : theme.border,
                cursor:
                  selectedFile &&
                  status !== "uploading" &&
                  status !== "processing"
                    ? "pointer"
                    : "not-allowed",
              }}
              disabled={
                !selectedFile ||
                status === "uploading" ||
                status === "processing"
              }
              onClick={handleUpload}
            >
              <FaPlay /> PROCESSAR EXCEL
            </button>
            {result && result.project_ids && result.project_ids.length > 0 && (
              <button
                style={{
                  ...ig.btn,
                  backgroundColor: theme.accentSecondary,
                  color: theme.background,
                }}
                onClick={() =>
                  navigate(`/quality-gate?project=${result.project_ids![0]}`)
                }
              >
                <FaCheckCircle /> VER QUALIDADE
              </button>
            )}
          </div>

          {error && (
            <p
              style={{ color: theme.accentDanger, fontSize: 12, marginTop: 10 }}
            >
              {error}
            </p>
          )}
        </div>

        {/* Resultado */}
        <div
          style={{
            ...ig.resultCard,
            backgroundColor: theme.surface,
            border: `1px solid ${theme.border}`,
          }}
        >
          <h3 style={{ ...ig.title, color: theme.textSecondary }}>
            RESULTADO DO PROCESSAMENTO
          </h3>
          {!result ? (
            <div style={{ textAlign: "center", padding: 60 }}>
              <p style={{ color: theme.textSecondary, fontSize: 14 }}>
                Envie um arquivo Excel para ver os resultados aqui.
              </p>
              <p
                style={{
                  color: theme.textTertiary,
                  fontSize: 12,
                  marginTop: 10,
                }}
              >
                Colunas aceitas: diâmetro, comprimento, empresa, código, fluido,
                temperatura, pressão
              </p>
            </div>
          ) : (
            <div>
              <div style={ig.resultMetric}>
                <span
                  style={{
                    fontSize: 48,
                    color: theme.accentSecondary,
                    fontWeight: "bold",
                  }}
                >
                  {result.count}
                </span>
                <span style={{ color: theme.textSecondary, fontSize: 13 }}>
                  projetos gerados
                </span>
              </div>
              <div style={{ marginTop: 20 }}>
                <p
                  style={{
                    color: theme.textSecondary,
                    fontSize: 11,
                    marginBottom: 8,
                  }}
                >
                  ARQUIVOS GERADOS:
                </p>
                {result.files.map((f, i) => {
                  const name = f.split(/[/\\]/).pop() || f;
                  return (
                    <div key={i} style={ig.fileRow}>
                      <FaCheckCircle color={theme.accentSecondary} />
                      <span>{name}</span>
                    </div>
                  );
                })}
              </div>
              {result.project_ids && (
                <div style={{ marginTop: 20 }}>
                  <p
                    style={{
                      color: theme.textSecondary,
                      fontSize: 11,
                      marginBottom: 8,
                    }}
                  >
                    IDs DOS PROJETOS:
                  </p>
                  <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                    {result.project_ids.map((id) => (
                      <span
                        key={id}
                        style={ig.idBadge}
                        onClick={() => navigate(`/quality-gate?project=${id}`)}
                      >
                        #{id}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

const ig: { [key: string]: React.CSSProperties } = {
  container: {
    padding: "40px",
    minHeight: "100vh",
    color: "#FFF",
    fontFamily: "monospace",
    background: "radial-gradient(circle at center, #1a1a1d 0%, #050507 100%)",
  },
  grid: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: "30px" },
  consoleCard: {
    backgroundColor: "rgba(20, 20, 25, 0.8)",
    backdropFilter: "blur(15px)",
    border: "1px solid rgba(255, 255, 255, 0.05)",
    padding: "30px",
    borderRadius: "8px",
    boxShadow:
      "0 40px 100px rgba(0,0,0,0.8), inset 0 0 20px rgba(0, 255, 65, 0.05)",
  },
  cardHeader: {
    display: "flex",
    justifyContent: "space-between",
    marginBottom: "20px",
  },
  title: { fontSize: "13px", letterSpacing: "2px", color: "#888" },
  dropZone: {
    border: "2px dashed #333",
    borderRadius: "8px",
    padding: "30px",
    textAlign: "center" as const,
    cursor: "pointer",
    marginBottom: "20px",
  },
  terminal: {
    backgroundColor: "rgba(0,0,0,0.9)",
    fontFamily: "Fira Code, monospace",
    color: "#00FF41",
    padding: "15px",
    borderLeft: "3px solid #00FF41",
    boxShadow: "0 0 20px rgba(0, 255, 65, 0.1)",
    fontSize: "11px",
    lineHeight: "1.5",
    height: "200px",
    borderRadius: "4px",
    overflowY: "auto" as const,
  },
  actionRow: { display: "flex", gap: "15px", marginTop: "20px" },
  btn: {
    flex: 1,
    padding: "12px",
    color: "#FFF",
    border: "none",
    fontWeight: "bold",
    borderRadius: "6px",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    gap: "8px",
    fontSize: 13,
  },
  resultCard: {
    backgroundColor: "rgba(20, 20, 25, 0.8)",
    backdropFilter: "blur(15px)",
    border: "1px solid rgba(255, 255, 255, 0.05)",
    padding: "30px",
    borderRadius: "8px",
    boxShadow:
      "0 40px 100px rgba(0,0,0,0.8), inset 0 0 20px rgba(0, 161, 255, 0.05)",
  },
  resultMetric: {
    display: "flex",
    flexDirection: "column" as const,
    alignItems: "center",
    padding: "30px 0",
  },
  fileRow: {
    display: "flex",
    alignItems: "center",
    gap: "8px",
    padding: "6px 0",
    borderBottom: "1px solid #1a1a1a",
    fontSize: 12,
  },
  idBadge: {
    background: "rgba(0, 161, 255, 0.15)",
    color: "#00A1FF",
    padding: "4px 10px",
    borderRadius: "4px",
    fontSize: 12,
    cursor: "pointer",
    border: "1px solid rgba(0, 161, 255, 0.3)",
  },
};

export default DataIngestion;
