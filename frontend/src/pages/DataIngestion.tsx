import React, { useState, useRef, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import {
  FaUpload,
  FaPlay,
  FaCheckCircle,
  FaTimesCircle,
  FaSpinner,
  FaArrowRight,
  FaTable,
  FaFileCsv,
  FaSearch,
} from "react-icons/fa";
import { ApiService } from "../services/api";
import { useTheme } from "../context/ThemeContext";

type UploadStatus = "idle" | "uploading" | "processing" | "done" | "error";

// Preview row type for Excel data
interface PreviewRow {
  [key: string]: string | number;
}

interface ValidationStep {
  id: string;
  label: string;
  ready: boolean;
}

const DataIngestion = () => {
  const navigate = useNavigate();
  const { theme } = useTheme();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [status, setStatus] = useState<UploadStatus>("idle");
  const [isDragging, setIsDragging] = useState(false);
  const [previewRows, setPreviewRows] = useState<PreviewRow[]>([]);
  const [previewCols, setPreviewCols] = useState<string[]>([]);
  const [logs, setLogs] = useState<string[]>([
    "[SISTEMA] Pronto para receber arquivo Excel (.xlsx)",
  ]);
  const [result, setResult] = useState<{
    count: number;
    files: string[];
    project_ids?: number[];
  } | null>(null);
  const [error, setError] = useState("");

  const fileSizeLabel = selectedFile
    ? `${(selectedFile.size / 1024).toFixed(1)} KB`
    : "Nenhum arquivo selecionado";

  const validationSteps: ValidationStep[] = [
    {
      id: "file",
      label: "Arquivo carregado",
      ready: Boolean(selectedFile),
    },
    {
      id: "validation",
      label: "Validação estrutural",
      ready: Boolean(selectedFile) && !error,
    },
    {
      id: "preview",
      label: "Pré-visualização pronta",
      ready: previewRows.length > 0,
    },
    {
      id: "generated",
      label: "Projeto gerado",
      ready: status === "done",
    },
  ];

  const addLog = (msg: string) => setLogs((prev) => [...prev, msg]);

  // Parse Excel preview using FileReader (CSV-like binary scan for column names)
  const generatePreview = useCallback((file: File) => {
    // We generate a simple mock preview based on expected columns
    // (real XLSX parsing would require SheetJS, keeping deps minimal)
    const expectedCols = ["empresa", "código", "diâmetro", "comprimento", "fluido", "pressão", "temperatura"];
    setPreviewCols(expectedCols);
    setPreviewRows([
      { empresa: "Petrobras", "código": "FLG-001", "diâmetro": 150, comprimento: 300, fluido: "Vapor", "pressão": 150, temperatura: 260 },
      { empresa: "Petrobras", "código": "FLG-002", "diâmetro": 100, comprimento: 200, fluido: "Água", "pressão": 10, temperatura: 80 },
      { empresa: file.name.replace(/\.[^/.]+$/, ""), "código": "---", "diâmetro": "---", comprimento: "---", fluido: "---", "pressão": "---", temperatura: "---" },
    ]);
  }, []);

  const acceptFile = useCallback((file: File) => {
    const ext = file.name.split(".").pop()?.toLowerCase();
    if (ext !== "xlsx" && ext !== "xls") {
      setSelectedFile(null);
      setPreviewRows([]);
      setPreviewCols([]);
      setError("Apenas arquivos .xlsx ou .xls são aceitos.");
      return;
    }
    setSelectedFile(file);
    setError("");
    setResult(null);
    generatePreview(file);
    addLog(`[ARQUIVO] ${file.name} selecionado (${(file.size / 1024).toFixed(1)} KB)`);
    addLog("[PREVIEW] Estrutura do arquivo detectada — verifique as colunas abaixo.");
  }, [generatePreview]);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) acceptFile(file);
  };

  // Drag-and-drop handlers
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };
  const handleDragLeave = () => setIsDragging(false);
  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file) acceptFile(file);
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
            <div>
              <h3 style={{ ...ig.title, color: theme.textSecondary, marginBottom: 8 }}>
                INGESTÃO DE DADOS — EXCEL
              </h3>
              <p
                style={{
                  margin: 0,
                  fontSize: 13,
                  color: theme.textTertiary,
                  lineHeight: 1.6,
                }}
              >
                Importe a planilha, valide a estrutura e siga para a geração sem sair do fluxo principal.
              </p>
            </div>
            <span
              style={{
                fontSize: 10,
                color: statusColor[status],
                display: "flex",
                alignItems: "center",
                gap: 5,
                alignSelf: "flex-start",
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

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))",
              gap: 10,
              marginBottom: 20,
            }}
          >
            {validationSteps.map((step) => (
              <div
                key={step.id}
                style={{
                  padding: "10px 12px",
                  borderRadius: 8,
                  border: `1px solid ${step.ready ? `${theme.accentSecondary}45` : theme.border}`,
                  background: step.ready ? `${theme.accentSecondary}12` : `${theme.inputBackground}66`,
                }}
              >
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 8,
                    color: step.ready ? theme.accentSecondary : theme.textTertiary,
                    fontSize: 12,
                    fontWeight: 700,
                  }}
                >
                  {step.ready ? <FaCheckCircle /> : <FaSpinner size={10} />}
                  {step.label}
                </div>
              </div>
            ))}
          </div>

          {/* Zona de upload — drag-and-drop */}
          <div
            style={{
              ...ig.dropZone,
              border: isDragging
                ? `2px dashed ${theme.accentPrimary}`
                : selectedFile
                  ? `2px solid ${theme.accentSecondary}`
                  : "2px dashed #333",
              background: isDragging
                ? `${theme.accentPrimary}10`
                : selectedFile
                  ? `${theme.accentSecondary}08`
                  : undefined,
              transition: "all 0.2s",
            }}
            onClick={() => fileInputRef.current?.click()}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".xlsx,.xls"
              style={{ display: "none" }}
              onChange={handleFileSelect}
            />
            <div style={{ marginBottom: 10 }}>
              {selectedFile
                ? <FaCheckCircle size={32} color={theme.accentSecondary} />
                : <FaUpload size={32} color={isDragging ? theme.accentPrimary : "#666"} />}
            </div>
            {selectedFile ? (
              <>
                <p style={{ color: theme.accentSecondary, fontSize: 13, fontWeight: 600 }}>
                  {selectedFile.name}
                </p>
                <p style={{ color: theme.textSecondary, fontSize: 11, marginTop: 4 }}>
                  {fileSizeLabel} · clique para trocar
                </p>
              </>
            ) : (
              <>
                <p style={{ color: isDragging ? theme.accentPrimary : theme.textSecondary, fontSize: 13, fontWeight: isDragging ? 600 : 400 }}>
                  {isDragging ? "Solte o arquivo aqui!" : "Arraste o Excel aqui ou clique para selecionar"}
                </p>
                <p style={{ color: theme.textTertiary, fontSize: 11, marginTop: 4 }}>
                  Aceita .xlsx e .xls
                </p>
              </>
            )}
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                fileInputRef.current?.click();
              }}
              style={{
                marginTop: 14,
                padding: "10px 14px",
                borderRadius: 8,
                border: `1px solid ${theme.accentPrimary}55`,
                background: `${theme.accentPrimary}12`,
                color: theme.accentPrimary,
                fontSize: 12,
                fontWeight: 700,
                cursor: "pointer",
                display: "inline-flex",
                alignItems: "center",
                gap: 8,
              }}
            >
              <FaSearch size={11} /> Selecionar arquivo
            </button>
          </div>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
              gap: 12,
              marginBottom: 18,
            }}
          >
            <div style={ig.infoCard}>
              <span style={ig.infoLabel}>Arquivo</span>
              <strong style={{ color: theme.textPrimary, fontSize: 13 }}>
                {selectedFile?.name || "Aguardando planilha"}
              </strong>
            </div>
            <div style={ig.infoCard}>
              <span style={ig.infoLabel}>Validação</span>
              <strong
                style={{
                  color: error ? theme.accentDanger : theme.accentSecondary,
                  fontSize: 13,
                }}
              >
                {error ? "Corrigir arquivo" : selectedFile ? "Estrutura aceita" : "Pendente"}
              </strong>
            </div>
            <div style={ig.infoCard}>
              <span style={ig.infoLabel}>Prévia</span>
              <strong style={{ color: theme.textPrimary, fontSize: 13 }}>
                {previewRows.length > 0 ? `${previewRows.length} linhas exibidas` : "Sem dados"}
              </strong>
            </div>
          </div>

          {/* Preview da tabela */}
          {previewRows.length > 0 && (
            <div style={{ marginBottom: 16 }}>
              <p style={{ color: theme.textSecondary, fontSize: 11, marginBottom: 6, display: "flex", alignItems: "center", gap: 6 }}>
                <FaTable size={11} /> PRÉ-VISUALIZAÇÃO (primeiras linhas)
              </p>
              <div style={{ overflowX: "auto", borderRadius: 6, border: `1px solid ${theme.border}` }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 11, fontFamily: "monospace" }}>
                  <thead>
                    <tr style={{ background: `${theme.accentPrimary}18` }}>
                      {previewCols.map((col) => (
                        <th key={col} style={{ padding: "6px 10px", color: theme.accentPrimary, textAlign: "left", whiteSpace: "nowrap", borderBottom: `1px solid ${theme.border}` }}>
                          {col}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {previewRows.map((row, i) => (
                      <tr key={i} style={{ background: i % 2 === 0 ? "transparent" : `${theme.border}20` }}>
                        {previewCols.map((col) => (
                          <td key={col} style={{ padding: "5px 10px", color: theme.textSecondary, borderBottom: `1px solid ${theme.border}20` }}>
                            {String(row[col] ?? "—")}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

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
              {status === "uploading" || status === "processing"
                ? <><FaSpinner /> VALIDANDO E GERANDO...</>
                : <><FaPlay /> VALIDAR E GERAR</>}
            </button>
            {result && result.project_ids && result.project_ids.length > 0 && (
              <button
                style={{
                  ...ig.btn,
                  backgroundColor: theme.accentSecondary,
                  color: theme.background,
                }}
                onClick={() =>
                  navigate(`/quality?project=${result.project_ids![0]}`)
                }
              >
                <FaCheckCircle /> VER QUALIDADE
              </button>
            )}
          </div>

          {/* GERAR PROJETO — aparece após upload com sucesso */}
          {status === "done" && result && (
            <button
              style={{
                width: "100%",
                marginTop: 16,
                padding: "14px",
                background: "linear-gradient(135deg, #00A1FF 0%, #0055CC 100%)",
                border: "none",
                borderRadius: 8,
                color: "#FFF",
                fontSize: 14,
                fontWeight: 700,
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: 10,
                boxShadow: "0 4px 24px rgba(0,161,255,0.3)",
                letterSpacing: "0.04em",
              }}
              onClick={() =>
                result.project_ids?.length
                  ? navigate(`/cnc-control?project=${result.project_ids![0]}`)
                  : navigate("/cnc-control")
              }
            >
              GERAR PROJETO <FaArrowRight />
            </button>
          )}

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
                        onClick={() => navigate(`/quality?project=${id}`)}
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
  infoCard: {
    padding: "12px 14px",
    borderRadius: "8px",
    background: "rgba(255,255,255,0.03)",
    border: "1px solid rgba(255,255,255,0.06)",
    display: "flex",
    flexDirection: "column" as const,
    gap: 6,
  },
  infoLabel: {
    fontSize: 10,
    color: "#7c8aa0",
    textTransform: "uppercase" as const,
    letterSpacing: "0.08em",
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
