import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  FaIndustry,
  FaDatabase,
  FaCogs,
  FaArrowRight,
  FaExclamationTriangle,
} from "react-icons/fa";

import { useGlobal, RefineryConfig } from "../context/GlobalContext";
import { ApiService } from "../services/api";

const REFINERIES = [
  { id: "REGAP", label: "REGAP - GABRIEL PASSOS (MG)" },
  { id: "REPLAN", label: "REPLAN - PAULÍNIA (SP)" },
  { id: "RLAM", label: "RLAM - LANDULPHO ALVES (BA)" },
  { id: "RECAP", label: "RECAP - MAUÁ (SP)" },
];

const GlobalSetup: React.FC = () => {
  const navigate = useNavigate();
  const { setSelectedRefinery } = useGlobal();

  const [selected, setSelected] = useState<string>("REGAP");
  const [refineryData, setRefineryData] = useState<Record<
    string,
    RefineryConfig & { name: string; location: string }
  > | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    ApiService.getRefineries()
      .then((envelope) => {
        if (!mounted) return;
        // Suportar formato padronizado {data: [...]} e legado {id: config}
        let mapped: Record<
          string,
          RefineryConfig & { name: string; location: string }
        >;
        const body = envelope as any;
        if (body?.data && Array.isArray(body.data)) {
          mapped = {};
          for (const item of body.data) {
            mapped[item.id] = item;
          }
        } else {
          mapped = body;
        }
        setRefineryData(mapped);
        setLoading(false);
      })
      .catch(() => {
        if (!mounted) return;
        setError(
          "Não foi possível conectar ao servidor. Verifique se o backend está rodando e tente novamente.",
        );
        setLoading(false);
      });
    return () => {
      mounted = false;
    };
  }, []);

  const current = refineryData?.[selected];

  const handleSave = () => {
    if (!current) return;
    setSelectedRefinery(selected, current);
    navigate("/dashboard");
  };

  const norms = current?.norms ?? ["N-58", "N-76", "N-115", "ASME B31.3"];
  const materialDb =
    current?.material_database ?? `SINCOR_${selected}_V2_OFFICIAL`;

  return (
    <div style={s.container}>
      <div style={s.card}>
        <div style={s.header}>
          <span style={s.mainIcon as React.CSSProperties}>
            <FaIndustry />
          </span>
          <h1 style={s.title}>CONFIGURAÇÃO GLOBAL</h1>
          <p style={s.subtitle}>
            SELECIONE A UNIDADE DE OPERAÇÃO E PARÂMETROS N-NORMA
          </p>
        </div>

        {error && (
          <div style={s.errorBox}>
            <FaExclamationTriangle size={14} />
            <span>{error}</span>
          </div>
        )}

        <div style={s.grid}>
          <div style={s.inputGroup}>
            <label style={s.label}>
              <FaDatabase /> UNIDADE / REFINARIA
            </label>
            <select
              style={s.select}
              value={selected}
              onChange={(e) => setSelected(e.target.value)}
            >
              {REFINERIES.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.label}
                </option>
              ))}
            </select>
          </div>

          <div style={s.inputGroup}>
            <label style={s.label}>
              <FaCogs /> BANCO DE MATERIAIS
            </label>
            <div style={s.staticValue}>{materialDb}</div>
          </div>
        </div>

        {current && (
          <div style={s.detailGrid}>
            <div style={s.detailItem}>
              <span style={s.detailLabel}>CLASSE PRESSÃO</span>
              <span style={s.detailValue}>
                {current.default_pressure_class}
              </span>
            </div>
            <div style={s.detailItem}>
              <span style={s.detailLabel}>TOLERÂNCIA CLASH</span>
              <span style={s.detailValue}>
                {current.clash_detection_tolerance_mm} mm
              </span>
            </div>
          </div>
        )}

        <div style={s.normContainer}>
          <div style={s.normTitle}>NORMAS ATIVAS NO NÚCLEO</div>
          <div style={s.normGrid}>
            {norms.map((norm) => (
              <div key={norm} style={s.normItem}>
                ✅ {norm}
              </div>
            ))}
          </div>
        </div>

        {loading && <p style={s.loadingText}>Conectando ao backend...</p>}

        <button
          onClick={handleSave}
          disabled={loading && !current}
          style={{
            ...s.button,
            opacity: loading && !current ? 0.5 : 1,
            cursor: loading && !current ? "not-allowed" : "pointer",
          }}
        >
          INICIALIZAR DASHBOARD{" "}
          <span style={{ marginLeft: "10px", display: "inline-flex" }}>
            <FaArrowRight />
          </span>
        </button>
      </div>
    </div>
  );
};

const s: Record<string, React.CSSProperties> = {
  container: {
    height: "100vh",
    display: "flex",
    justifyContent: "center",
    alignItems: "center",
    fontFamily: "Inter, sans-serif",
    background: "radial-gradient(circle at center, #1a1a1d 0%, #050507 100%)",
  },
  card: {
    width: "850px",
    padding: "40px",
    backgroundColor: "rgba(20, 20, 25, 0.8)",
    backdropFilter: "blur(15px)",
    border: "1px solid rgba(255, 255, 255, 0.05)",
    borderRadius: "12px",
    boxShadow:
      "0 40px 100px rgba(0,0,0,0.8), inset 0 0 20px rgba(0, 161, 255, 0.05)",
  },
  header: { textAlign: "center" as const, marginBottom: "30px" },
  mainIcon: { fontSize: "40px", color: "#00A1FF", marginBottom: "10px" },
  title: { color: "#FFF", letterSpacing: "4px", fontSize: "22px", margin: 0 },
  subtitle: { color: "#444", fontSize: "10px", marginTop: "5px" },
  errorBox: {
    display: "flex",
    alignItems: "center",
    gap: "10px",
    padding: "12px",
    backgroundColor: "#1a0505",
    border: "1px solid #FF4B4B",
    borderRadius: "4px",
    marginBottom: "20px",
    color: "#FF4B4B",
    fontSize: "11px",
  },
  grid: {
    display: "grid",
    gridTemplateColumns: "1fr 1fr",
    gap: "20px",
    marginBottom: "20px",
  },
  inputGroup: { display: "flex", flexDirection: "column" as const },
  label: {
    color: "#005596",
    fontSize: "11px",
    fontWeight: "bold",
    marginBottom: "10px",
    display: "flex",
    alignItems: "center",
    gap: "8px",
  },
  select: {
    padding: "12px",
    backgroundColor: "#050507",
    border: "1px solid #333",
    color: "#00FF41",
    outline: "none",
    cursor: "pointer",
    fontFamily: "monospace",
    fontSize: "13px",
  },
  staticValue: {
    padding: "12px",
    backgroundColor: "#161618",
    border: "1px solid #222",
    color: "#AAA",
    fontSize: "13px",
    fontFamily: "monospace",
  },
  detailGrid: {
    display: "grid",
    gridTemplateColumns: "1fr 1fr",
    gap: "15px",
    marginBottom: "20px",
  },
  detailItem: {
    padding: "10px",
    backgroundColor: "#050507",
    border: "1px solid #1a1c22",
    borderRadius: "4px",
  },
  detailLabel: {
    display: "block",
    fontSize: "9px",
    color: "#555",
    marginBottom: "4px",
    letterSpacing: "1px",
  },
  detailValue: { fontSize: "13px", color: "#00A1FF", fontWeight: "bold" },
  normContainer: {
    padding: "20px",
    backgroundColor: "#050507",
    borderRadius: "4px",
    border: "1px solid #1a1c22",
    marginBottom: "30px",
  },
  normTitle: {
    color: "#555",
    fontSize: "10px",
    marginBottom: "15px",
    textAlign: "center" as const,
    letterSpacing: "2px",
  },
  normGrid: {
    display: "grid",
    gridTemplateColumns: "1fr 1fr 1fr 1fr",
    gap: "10px",
  },
  normItem: {
    fontSize: "11px",
    color: "#32CD32",
    textAlign: "center" as const,
  },
  loadingText: {
    fontSize: "11px",
    color: "#555",
    textAlign: "center" as const,
    marginBottom: "15px",
  },
  button: {
    width: "100%",
    padding: "16px",
    background:
      "linear-gradient(90deg, rgba(0, 161, 255, 0.15) 0%, transparent 100%)",
    color: "#FFF",
    border: "1px solid #00A1FF",
    borderRadius: "8px",
    fontWeight: "bold",
    cursor: "pointer",
    letterSpacing: "2px",
    fontFamily: "Inter, sans-serif",
    fontSize: "13px",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    boxShadow: "0 0 15px rgba(0, 161, 255, 0.3)",
  },
};

export default GlobalSetup;
