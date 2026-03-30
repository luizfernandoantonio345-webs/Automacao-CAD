import React, { useState, useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import {
  FaShieldAlt,
  FaCheckCircle,
  FaTimesCircle,
  FaExclamationTriangle,
  FaSpinner,
} from "react-icons/fa";
import { ApiService, ProjectRecord, QualityCheckResult } from "../services/api";

const QualityGate = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const projectIdParam = searchParams.get("project");
  const [projects, setProjects] = useState<ProjectRecord[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(
    projectIdParam ? parseInt(projectIdParam) : null,
  );
  const [project, setProject] = useState<ProjectRecord | null>(null);
  const [qcResult, setQcResult] = useState<QualityCheckResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [running, setRunning] = useState(false);

  useEffect(() => {
    ApiService.getProjects()
      .then((d) => setProjects(d.projects))
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (!selectedId) return;
    setLoading(true);
    ApiService.getProject(selectedId)
      .then((d) => {
        setProject(d.project);
        // Se já tem checks, montar resultado
        if (d.quality_checks.length > 0) {
          const checks = d.quality_checks.map((c: any) => ({
            name: c.check_name,
            passed: !!c.passed,
            detail: c.details,
          }));
          const passed = checks.filter((c: any) => c.passed).length;
          setQcResult({
            project_id: selectedId,
            checks,
            passed,
            total: checks.length,
            all_passed: passed === checks.length,
            verdict:
              passed === checks.length
                ? "APROVADO"
                : passed > checks.length / 2
                  ? "PARCIAL"
                  : "REPROVADO",
          });
        }
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [selectedId]);

  const handleRunCheck = async () => {
    if (!selectedId) return;
    setRunning(true);
    try {
      const result = await ApiService.runQualityCheck(selectedId);
      setQcResult(result);
    } catch {
      // error
    } finally {
      setRunning(false);
    }
  };

  const verdictColor = {
    APROVADO: "#32CD32",
    PARCIAL: "#FFD700",
    REPROVADO: "#FF4B4B",
  };

  return (
    <div style={qg.container}>
      <h2 style={{ letterSpacing: "4px", marginBottom: "30px" }}>
        <FaShieldAlt /> PAINEL DE AUDITORIA
      </h2>

      <div style={qg.grid}>
        {/* Seleção de Projeto */}
        <div style={qg.card}>
          <h3 style={qg.title}>SELECIONAR PROJETO</h3>
          <select
            style={qg.select}
            value={selectedId ?? ""}
            onChange={(e) => {
              setSelectedId(parseInt(e.target.value) || null);
              setQcResult(null);
            }}
          >
            <option value="">-- Selecione --</option>
            {projects.map((p) => (
              <option key={p.id} value={p.id}>
                #{p.id} — {p.code} ({p.company})
              </option>
            ))}
          </select>

          {project && (
            <div style={{ marginTop: 20 }}>
              <InfoRow label="Código" value={project.code} />
              <InfoRow label="Empresa" value={project.company} />
              <InfoRow label="Peça" value={project.part_name} />
              <InfoRow label="Diâmetro" value={`${project.diameter}mm`} />
              <InfoRow label="Comprimento" value={`${project.length}mm`} />
              <InfoRow label="Status" value={project.status} />
            </div>
          )}

          <button
            style={{
              ...qg.runBtn,
              opacity: selectedId && !running ? 1 : 0.4,
              cursor: selectedId && !running ? "pointer" : "not-allowed",
            }}
            disabled={!selectedId || running}
            onClick={handleRunCheck}
          >
            {running ? (
              <>
                <FaSpinner /> Verificando...
              </>
            ) : (
              <>
                <FaShieldAlt /> EXECUTAR VERIFICAÇÃO
              </>
            )}
          </button>
        </div>

        {/* Resultado */}
        <div style={qg.card}>
          <h3 style={qg.title}>RESULTADO DA AUDITORIA</h3>
          {loading ? (
            <p style={{ color: "#555" }}>Carregando...</p>
          ) : !qcResult ? (
            <p style={{ color: "#555", fontSize: 13 }}>
              Selecione um projeto e clique em "Executar Verificação".
            </p>
          ) : (
            <>
              {/* Veredito */}
              <div
                style={{
                  backgroundColor: verdictColor[qcResult.verdict],
                  padding: "20px",
                  borderRadius: "8px",
                  textAlign: "center",
                  marginBottom: "20px",
                }}
              >
                <div style={{ fontSize: 12, color: "#000" }}>VEREDITO</div>
                <div
                  style={{ fontSize: 28, fontWeight: "bold", color: "#000" }}
                >
                  {qcResult.verdict}
                </div>
                <div style={{ fontSize: 13, color: "#000" }}>
                  {qcResult.passed}/{qcResult.total} verificações aprovadas
                </div>
              </div>

              {/* Lista de checks */}
              {qcResult.checks.map((c, i) => (
                <div key={i} style={qg.checkRow}>
                  <span>
                    {c.passed ? (
                      <FaCheckCircle color="#32CD32" />
                    ) : (
                      <FaTimesCircle color="#FF4B4B" />
                    )}
                  </span>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontWeight: "bold", fontSize: 13 }}>
                      {c.name}
                    </div>
                    <div style={{ fontSize: 11, color: "#888" }}>
                      {c.detail}
                    </div>
                  </div>
                </div>
              ))}

              <button
                style={qg.nextBtn}
                onClick={() => navigate(`/final-report?project=${selectedId}`)}
              >
                PROSSEGUIR → RELATÓRIO FINAL
              </button>
            </>
          )}
        </div>

        {/* Especificação Técnica */}
        <div style={qg.card}>
          <h3 style={qg.title}>ESPECIFICAÇÃO TÉCNICA</h3>
          {project ? (
            (() => {
              let spec: any = {};
              try {
                spec = JSON.parse(project.piping_spec || "{}");
              } catch {}
              return Object.keys(spec).length > 0 ? (
                <div>
                  <InfoRow
                    label="Classe"
                    value={spec.pressure_class || "N/A"}
                  />
                  <InfoRow label="Material" value={spec.material || "N/A"} />
                  <InfoRow
                    label="Face Flange"
                    value={spec.flange_face || "N/A"}
                  />
                  <InfoRow
                    label="Schedule"
                    value={spec.selected_schedule || "N/A"}
                  />
                  <InfoRow
                    label="Espessura"
                    value={`${spec.wall_thickness_mm || 0}mm`}
                  />
                  <InfoRow
                    label="Hidroteste"
                    value={`${spec.hydrotest_pressure_bar || 0} bar`}
                  />
                  <InfoRow
                    label="Corrosão"
                    value={`${spec.corrosion_allowance_mm || 0}mm`}
                  />
                </div>
              ) : (
                <p style={{ color: "#555", fontSize: 13 }}>
                  Execute a verificação para gerar especificação.
                </p>
              );
            })()
          ) : (
            <p style={{ color: "#555", fontSize: 13 }}>Selecione um projeto.</p>
          )}
        </div>
      </div>
    </div>
  );
};

const InfoRow = ({ label, value }: { label: string; value: string }) => (
  <div
    style={{
      display: "flex",
      justifyContent: "space-between",
      padding: "6px 0",
      borderBottom: "1px solid #1a1a1a",
      fontSize: 12,
    }}
  >
    <span style={{ color: "#888" }}>{label}</span>
    <span style={{ color: "#FFF" }}>{value}</span>
  </div>
);

const qg: { [key: string]: React.CSSProperties } = {
  container: {
    padding: "40px",
    minHeight: "100vh",
    color: "#FFF",
    background: "radial-gradient(circle at center, #1a1a1d 0%, #050507 100%)",
  },
  grid: {
    display: "grid",
    gridTemplateColumns: "1fr 1fr 1fr",
    gap: "20px",
  },
  card: {
    backgroundColor: "rgba(20, 20, 25, 0.8)",
    backdropFilter: "blur(15px)",
    border: "1px solid rgba(255, 255, 255, 0.05)",
    padding: "25px",
    borderRadius: "8px",
    boxShadow:
      "0 40px 100px rgba(0,0,0,0.8), inset 0 0 20px rgba(0, 161, 255, 0.05)",
  },
  title: {
    fontSize: "12px",
    letterSpacing: "2px",
    marginBottom: "15px",
    color: "#888",
  },
  select: {
    width: "100%",
    padding: "10px",
    backgroundColor: "#000",
    border: "1px solid #333",
    color: "#FFF",
    borderRadius: "4px",
    fontSize: 13,
  },
  runBtn: {
    width: "100%",
    padding: "14px",
    background:
      "linear-gradient(90deg, rgba(0, 161, 255, 0.15) 0%, transparent 100%)",
    color: "#FFF",
    border: "1px solid #00A1FF",
    borderRadius: "8px",
    fontWeight: "bold",
    marginTop: "20px",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    gap: "8px",
    fontSize: 13,
    boxShadow: "0 0 15px rgba(0, 161, 255, 0.3)",
  },
  checkRow: {
    display: "flex",
    alignItems: "center",
    gap: "12px",
    padding: "10px 0",
    borderBottom: "1px solid #1a1a1a",
  },
  nextBtn: {
    width: "100%",
    padding: "12px",
    backgroundColor: "#32CD32",
    color: "#000",
    border: "none",
    borderRadius: "8px",
    fontWeight: "bold",
    marginTop: "20px",
    cursor: "pointer",
    fontSize: 13,
  },
};

export default QualityGate;
