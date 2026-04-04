import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  FaIndustry,
  FaDatabase,
  FaCogs,
  FaArrowRight,
  FaExclamationTriangle,
  FaCheckCircle,
} from "react-icons/fa";

import { useGlobal, RefineryConfig } from "../context/GlobalContext";
import { useTheme } from "../context/ThemeContext";
import { ApiService } from "../services/api";
import createStyles, { spacing, radius } from "../styles/shared";

const REFINERIES = [
  { id: "REGAP", label: "REGAP - GABRIEL PASSOS (MG)" },
  { id: "REPLAN", label: "REPLAN - PAULÍNIA (SP)" },
  { id: "RLAM", label: "RLAM - LANDULPHO ALVES (BA)" },
  { id: "RECAP", label: "RECAP - MAUÁ (SP)" },
];

const GlobalSetup: React.FC = () => {
  const navigate = useNavigate();
  const { setSelectedRefinery } = useGlobal();
  const { theme } = useTheme();
  const styles = createStyles(theme);

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
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        fontFamily: "'Inter', sans-serif",
        background: `radial-gradient(circle at center, ${theme.surface} 0%, ${theme.background} 100%)`,
        padding: spacing.lg,
      }}
    >
      <div
        style={{
          width: "100%",
          maxWidth: "900px",
          padding: spacing.xl,
          backgroundColor: theme.surface,
          border: `1px solid ${theme.border}`,
          borderRadius: radius.xl,
          boxShadow: `0 20px 60px rgba(0,0,0,0.4)`,
        }}
      >
        {/* Header */}
        <div style={{ textAlign: "center", marginBottom: spacing.xl }}>
          <div
            style={{
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              width: 64,
              height: 64,
              borderRadius: radius.lg,
              backgroundColor: `${theme.accentPrimary}15`,
              marginBottom: spacing.md,
            }}
          >
            <FaIndustry size={32} color={theme.accentPrimary} />
          </div>
          <h1
            style={{
              ...styles.pageTitle,
              justifyContent: "center",
              marginBottom: spacing.xs,
            }}
          >
            Configuração Global
          </h1>
          <p
            style={{
              ...styles.pageSubtitle,
              textTransform: "uppercase",
              letterSpacing: "0.1em",
              fontSize: "0.7rem",
            }}
          >
            Selecione a unidade de operação e parâmetros N-Norma
          </p>
        </div>

        {error && (
          <div style={styles.errorBox}>
            <FaExclamationTriangle size={16} />
            <span>{error}</span>
          </div>
        )}

        <div style={{ ...styles.grid2, marginBottom: spacing.lg }}>
          <div style={styles.inputGroup}>
            <label style={styles.inputLabel}>
              <FaDatabase size={12} /> UNIDADE / REFINARIA
            </label>
            <select
              style={{
                ...styles.input,
                cursor: "pointer",
                fontSize: "0.9rem",
              }}
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

          <div style={styles.inputGroup}>
            <label style={styles.inputLabel}>
              <FaCogs size={12} /> BANCO DE MATERIAIS
            </label>
            <div
              style={{
                ...styles.input,
                backgroundColor: theme.surfaceAlt || theme.inputBackground,
                color: theme.textSecondary,
                fontFamily: "monospace",
              }}
            >
              {materialDb}
            </div>
          </div>
        </div>

        {current && (
          <div style={{ ...styles.grid2, marginBottom: spacing.lg }}>
            <div
              style={{
                ...styles.cardCompact,
                borderLeft: `3px solid ${theme.accentPrimary}`,
              }}
            >
              <span
                style={{
                  fontSize: "0.65rem",
                  color: theme.textTertiary,
                  textTransform: "uppercase",
                  letterSpacing: "0.1em",
                  display: "block",
                  marginBottom: spacing.xs,
                }}
              >
                Classe Pressão
              </span>
              <span
                style={{
                  fontSize: "1.1rem",
                  color: theme.accentPrimary,
                  fontWeight: 600,
                }}
              >
                {current.default_pressure_class}
              </span>
            </div>
            <div
              style={{
                ...styles.cardCompact,
                borderLeft: `3px solid ${theme.success}`,
              }}
            >
              <span
                style={{
                  fontSize: "0.65rem",
                  color: theme.textTertiary,
                  textTransform: "uppercase",
                  letterSpacing: "0.1em",
                  display: "block",
                  marginBottom: spacing.xs,
                }}
              >
                Tolerância Clash
              </span>
              <span
                style={{
                  fontSize: "1.1rem",
                  color: theme.success,
                  fontWeight: 600,
                }}
              >
                {current.clash_detection_tolerance_mm} mm
              </span>
            </div>
          </div>
        )}

        <div
          style={{
            ...styles.card,
            marginBottom: spacing.xl,
            textAlign: "center",
          }}
        >
          <div
            style={{
              fontSize: "0.65rem",
              color: theme.textTertiary,
              textTransform: "uppercase",
              letterSpacing: "0.15em",
              marginBottom: spacing.md,
            }}
          >
            Normas Ativas no Núcleo
          </div>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(4, 1fr)",
              gap: spacing.sm,
            }}
          >
            {norms.map((norm) => (
              <div
                key={norm}
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: spacing.xs,
                  padding: spacing.sm,
                  backgroundColor: `${theme.success}10`,
                  borderRadius: radius.sm,
                  color: theme.success,
                  fontSize: "0.8rem",
                  fontWeight: 500,
                }}
              >
                <FaCheckCircle size={12} /> {norm}
              </div>
            ))}
          </div>
        </div>

        {loading && (
          <p
            style={{
              ...styles.loadingText,
              textAlign: "center",
              marginBottom: spacing.md,
            }}
          >
            Conectando ao backend...
          </p>
        )}

        <button
          onClick={handleSave}
          disabled={loading && !current}
          style={{
            ...styles.buttonPrimary,
            width: "100%",
            padding: spacing.md,
            fontSize: "0.9rem",
            letterSpacing: "0.1em",
            background: `linear-gradient(135deg, ${theme.accentPrimary} 0%, ${theme.accentPrimary}CC 100%)`,
            boxShadow: `0 4px 20px ${theme.accentPrimary}40`,
            opacity: loading && !current ? 0.5 : 1,
            cursor: loading && !current ? "not-allowed" : "pointer",
          }}
        >
          INICIALIZAR DASHBOARD
          <span style={{ marginLeft: spacing.sm, display: "inline-flex" }}>
            <FaArrowRight size={14} />
          </span>
        </button>
      </div>
    </div>
  );
};

export default GlobalSetup;
