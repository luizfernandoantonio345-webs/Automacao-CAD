import React, { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import {
  FaFileSignature,
  FaDownload,
  FaAward,
  FaHistory,
  FaCheckCircle,
  FaTimesCircle,
} from "react-icons/fa";
import { ApiService, ProjectRecord, QualityCheck } from "../services/api";

const FinalReport = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const projectIdParam = searchParams.get("project");
  const [project, setProject] = useState<ProjectRecord | null>(null);
  const [checks, setChecks] = useState<QualityCheck[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!projectIdParam) {
      setLoading(false);
      return;
    }
    ApiService.getProject(parseInt(projectIdParam))
      .then((d) => {
        setProject(d.project);
        setChecks(d.quality_checks);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [projectIdParam]);

  const handleDownload = (fileType: "lsp" | "csv") => {
    if (!project) return;
    ApiService.downloadProjectFile(project.id, fileType).catch(() => {
      alert(`Arquivo ${fileType} não disponível para este projeto.`);
    });
  };

  let spec: any = {};
  try {
    spec = JSON.parse(project?.piping_spec || "{}");
  } catch {}
  let normsChecked: string[] = [];
  let normsPassed: string[] = [];
  try {
    normsChecked = JSON.parse(project?.norms_checked || "[]");
  } catch {}
  try {
    normsPassed = JSON.parse(project?.norms_passed || "[]");
  } catch {}

  const passedChecks = checks.filter((c) => c.passed);
  const allPassed = checks.length > 0 && passedChecks.length === checks.length;

  if (loading) {
    return (
      <div style={f.container}>
        <p style={{ color: "#555" }}>Carregando...</p>
      </div>
    );
  }

  if (!project) {
    return (
      <div style={f.container}>
        <div style={{ ...f.reportCard, maxWidth: 500 }}>
          <h2 style={{ color: "#FFF", letterSpacing: 4 }}>RELATÓRIO FINAL</h2>
          <p style={{ color: "#555", marginTop: 20 }}>
            Nenhum projeto selecionado. Vá ao painel de auditoria e selecione um
            projeto.
          </p>
          <button
            style={f.finalizeBtn}
            onClick={() => navigate("/quality-gate")}
          >
            IR PARA AUDITORIA
          </button>
        </div>
      </div>
    );
  }

  return (
    <div style={f.container}>
      <div style={f.reportCard}>
        {/* Selo de Qualidade */}
        <div style={f.badgeContainer}>
          <span
            style={{ ...f.goldBadge, color: allPassed ? "#FFD700" : "#FF8800" }}
          >
            <FaAward size={70} />
          </span>
        </div>

        <h1 style={f.mainTitle}>
          {allPassed ? "PROJETO CERTIFICADO" : "RELATÓRIO DO PROJETO"}
        </h1>
        <p style={f.subtitle}>
          {project.code} // {project.company} // Ø{project.diameter}mm ×{" "}
          {project.length}mm
        </p>

        {/* Métricas */}
        <div style={f.statsGrid}>
          <div style={f.statBox}>
            <span style={f.statLabel}>MATERIAL</span>
            <span style={f.statValue}>{spec.material || "N/A"}</span>
          </div>
          <div style={f.statBox}>
            <span style={f.statLabel}>SCHEDULE</span>
            <span style={f.statValue}>{spec.selected_schedule || "N/A"}</span>
          </div>
          <div style={f.statBox}>
            <span style={f.statLabel}>CLASSE PRESSÃO</span>
            <span style={f.statValue}>{spec.pressure_class || "N/A"}</span>
          </div>
          <div style={f.statBox}>
            <span style={f.statLabel}>ESPESSURA</span>
            <span style={f.statValue}>
              {spec.wall_thickness_mm ? `${spec.wall_thickness_mm}mm` : "N/A"}
            </span>
          </div>
          <div style={f.statBox}>
            <span style={f.statLabel}>HIDROTESTE</span>
            <span style={f.statValue}>
              {spec.hydrotest_pressure_bar
                ? `${spec.hydrotest_pressure_bar} bar`
                : "N/A"}
            </span>
          </div>
          <div style={f.statBox}>
            <span style={f.statLabel}>VERIFICAÇÕES</span>
            <span
              style={{
                ...f.statValue,
                color: allPassed ? "#32CD32" : "#FFD700",
              }}
            >
              {passedChecks.length}/{checks.length}
            </span>
          </div>
        </div>

        {/* Normas */}
        {normsChecked.length > 0 && (
          <div style={{ textAlign: "left", marginBottom: 25 }}>
            <h3 style={f.docTitle}>NORMAS VERIFICADAS</h3>
            {normsChecked.map((n, i) => (
              <div
                key={i}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  padding: "5px 0",
                  fontSize: 13,
                }}
              >
                {normsPassed.includes(n) ? (
                  <FaCheckCircle color="#32CD32" />
                ) : (
                  <FaTimesCircle color="#FF4B4B" />
                )}
                <span style={{ color: "#DDD" }}>{n}</span>
              </div>
            ))}
          </div>
        )}

        {/* Arquivos para download */}
        <div style={f.docSection}>
          <h3 style={f.docTitle}>ARQUIVOS GERADOS</h3>
          {project.lsp_path && (
            <div style={f.fileItem}>
              <span>
                <FaFileSignature color="#00A1FF" />{" "}
                {project.lsp_path.split(/[/\\]/).pop()}
              </span>
              <button
                style={f.downloadBtn}
                onClick={() => handleDownload("lsp")}
              >
                <FaDownload />
              </button>
            </div>
          )}
          {project.csv_path && (
            <div style={f.fileItem}>
              <span>
                <FaFileSignature color="#00FF88" />{" "}
                {project.csv_path.split(/[/\\]/).pop()}
              </span>
              <button
                style={f.downloadBtn}
                onClick={() => handleDownload("csv")}
              >
                <FaDownload />
              </button>
            </div>
          )}
          {!project.lsp_path && !project.csv_path && (
            <p style={{ color: "#555", fontSize: 12 }}>
              Nenhum arquivo gerado ainda.
            </p>
          )}
        </div>

        <div style={f.footerButtons}>
          <button
            style={f.historyBtn}
            onClick={() => navigate("/quality-gate?project=" + project.id)}
          >
            <FaHistory /> VOLTAR À AUDITORIA
          </button>
          <button style={f.finalizeBtn} onClick={() => navigate("/dashboard")}>
            NOVO PROJETO
          </button>
        </div>
      </div>
    </div>
  );
};

const f: { [key: string]: React.CSSProperties } = {
  container: {
    minHeight: "100vh",
    backgroundColor: "#050507",
    display: "flex",
    justifyContent: "center",
    alignItems: "center",
    position: "relative" as const,
    overflow: "hidden",
    padding: "40px 20px",
  },
  reportCard: {
    width: "700px",
    maxWidth: "100%",
    padding: "40px",
    backgroundColor: "rgba(20, 20, 25, 0.9)",
    backdropFilter: "blur(20px)",
    border: "1px solid rgba(255,255,255,0.05)",
    borderRadius: "16px",
    textAlign: "center" as const,
    zIndex: 10,
    boxShadow: "0 50px 100px rgba(0,0,0,0.8)",
  },
  badgeContainer: { marginBottom: "15px" },
  goldBadge: {
    color: "#FFD700",
    filter: "drop-shadow(0 0 20px rgba(255,215,0,0.5))",
    display: "inline-block",
  },
  mainTitle: {
    color: "#FFF",
    fontSize: "24px",
    letterSpacing: "5px",
    margin: "10px 0",
    fontWeight: 900,
  },
  subtitle: {
    color: "#555",
    fontSize: "10px",
    letterSpacing: "2px",
    marginBottom: "30px",
  },
  statsGrid: {
    display: "grid",
    gridTemplateColumns: "1fr 1fr 1fr",
    gap: "12px",
    marginBottom: "30px",
  },
  statBox: {
    backgroundColor: "#000",
    padding: "12px",
    borderRadius: "8px",
    border: "1px solid #222",
  },
  statLabel: {
    display: "block",
    color: "#666",
    fontSize: "9px",
    marginBottom: "4px",
  },
  statValue: { color: "#32CD32", fontSize: "13px", fontWeight: "bold" },
  docSection: { textAlign: "left" as const, marginBottom: "30px" },
  docTitle: {
    color: "#888",
    fontSize: "11px",
    marginBottom: "12px",
    letterSpacing: "1px",
  },
  fileItem: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    backgroundColor: "rgba(255,255,255,0.02)",
    padding: "10px 12px",
    borderRadius: "4px",
    marginBottom: "8px",
    fontSize: "12px",
    color: "#EEE",
  },
  downloadBtn: {
    background: "none",
    border: "none",
    color: "#00A1FF",
    cursor: "pointer",
    fontSize: "16px",
  },
  footerButtons: { display: "flex", gap: "15px" },
  historyBtn: {
    flex: 1,
    padding: "14px",
    backgroundColor: "transparent",
    border: "1px solid #333",
    color: "#AAA",
    borderRadius: "4px",
    cursor: "pointer",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    gap: "8px",
    fontSize: 13,
  },
  finalizeBtn: {
    flex: 2,
    padding: "14px",
    backgroundColor: "#00A1FF",
    border: "none",
    color: "#FFF",
    fontWeight: "bold",
    borderRadius: "4px",
    cursor: "pointer",
    fontSize: 13,
  },
};

export default FinalReport;
