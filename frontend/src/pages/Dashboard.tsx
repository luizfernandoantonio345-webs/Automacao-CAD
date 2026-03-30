import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  FaChartLine,
  FaBox,
  FaDraftingCompass,
  FaShieldAlt,
} from "react-icons/fa";
import { ApiService, ProjectStats, ProjectRecord } from "../services/api";

const Dashboard = () => {
  const navigate = useNavigate();
  const [stats, setStats] = useState<ProjectStats | null>(null);
  const [projects, setProjects] = useState<ProjectRecord[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const [statsData, projData] = await Promise.all([
          ApiService.getProjectStats(),
          ApiService.getProjects(),
        ]);
        if (!cancelled) {
          setStats(statsData);
          setProjects(projData.projects.slice(0, 8));
        }
      } catch {
        // fallback — sem dados ainda
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    load();
    return () => {
      cancelled = true;
    };
  }, []);

  const total = stats?.stats?.total_projects ?? 0;
  const completed = stats?.stats?.completed_projects ?? 0;
  const companies = stats?.stats?.top_companies ?? [];
  const parts = stats?.stats?.top_parts ?? [];

  return (
    <div style={db.container}>
      <main style={db.main}>
        <header style={db.topNav}>
          <span>
            Engenharia CAD Dashboard | {new Date().toLocaleDateString("pt-BR")}
          </span>
          <button
            style={db.projectBtn}
            onClick={() => navigate("/global-setup")}
          >
            NOVO PROJETO
          </button>
        </header>

        {/* Métricas Principais */}
        <div style={db.metricsRow}>
          <MetricCard
            icon={<FaBox />}
            label="Total Projetos"
            value={total}
            color="#00A1FF"
          />
          <MetricCard
            icon={<FaDraftingCompass />}
            label="Concluídos"
            value={completed}
            color="#00FF88"
          />
          <MetricCard
            icon={<FaChartLine />}
            label="Empresas"
            value={companies.length}
            color="#FF8800"
          />
          <MetricCard
            icon={<FaShieldAlt />}
            label="Normas Ativas"
            value={3}
            color="#AA66FF"
          />
        </div>

        <div style={db.grid}>
          {/* Últimos Projetos */}
          <div style={db.card}>
            <h3 style={db.label}>ÚLTIMOS PROJETOS</h3>
            {loading ? (
              <p style={{ color: "#555", fontSize: 13 }}>Carregando...</p>
            ) : projects.length === 0 ? (
              <p style={{ color: "#555", fontSize: 13 }}>
                Nenhum projeto gerado ainda. Clique em "Novo Projeto" para
                começar.
              </p>
            ) : (
              <div style={{ maxHeight: 360, overflowY: "auto" }}>
                {projects.map((p) => (
                  <div
                    key={p.id}
                    style={db.projectRow}
                    onClick={() => navigate(`/quality-gate?project=${p.id}`)}
                  >
                    <div>
                      <span style={{ color: "#00A1FF", fontWeight: "bold" }}>
                        #{p.id}
                      </span>{" "}
                      <span>{p.code}</span>
                    </div>
                    <div style={{ fontSize: 11, color: "#888" }}>
                      {p.company} — Ø{p.diameter}mm × {p.length}mm
                    </div>
                    <div
                      style={{
                        fontSize: 11,
                        color: p.status === "completed" ? "#0F0" : "#FA0",
                      }}
                    >
                      {p.status === "completed"
                        ? "✓ Completo"
                        : "⏳ " + p.status}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Ranking */}
          <div style={db.card}>
            <h3 style={db.label}>TOP EMPRESAS / PEÇAS</h3>
            {companies.length > 0 && (
              <>
                <p style={{ color: "#888", fontSize: 11, marginBottom: 8 }}>
                  Empresas
                </p>
                {companies.map(([name, count], i) => (
                  <div key={i} style={db.rankRow}>
                    <span>{name || "Sem nome"}</span>
                    <span style={{ color: "#00A1FF" }}>{count}</span>
                  </div>
                ))}
              </>
            )}
            {parts.length > 0 && (
              <>
                <p
                  style={{
                    color: "#888",
                    fontSize: 11,
                    marginBottom: 8,
                    marginTop: 16,
                  }}
                >
                  Peças
                </p>
                {parts.map(([name, count], i) => (
                  <div key={i} style={db.rankRow}>
                    <span>{name || "Sem nome"}</span>
                    <span style={{ color: "#00FF88" }}>{count}</span>
                  </div>
                ))}
              </>
            )}
            {companies.length === 0 && parts.length === 0 && (
              <p style={{ color: "#555", fontSize: 13 }}>
                Gere projetos para ver rankings.
              </p>
            )}
          </div>
        </div>
      </main>
    </div>
  );
};

const MetricCard = ({
  icon,
  label,
  value,
  color,
}: {
  icon: React.ReactNode;
  label: string;
  value: number;
  color: string;
}) => (
  <div style={{ ...db.metricCard, borderColor: color }}>
    <div style={{ fontSize: 24, color }}>{icon}</div>
    <div style={{ fontSize: 28, fontWeight: "bold", color }}>{value}</div>
    <div style={{ fontSize: 11, color: "#888" }}>{label}</div>
  </div>
);

const db: { [key: string]: React.CSSProperties } = {
  container: {
    display: "flex",
    flexDirection: "column",
    height: "100%",
    backgroundColor: "#0A0A0B",
    color: "#FFF",
  },
  main: { flex: 1, padding: "30px", overflowY: "auto" as const },
  topNav: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: "30px",
    fontSize: "13px",
  },
  projectBtn: {
    background:
      "linear-gradient(90deg, rgba(0, 161, 255, 0.15) 0%, transparent 100%)",
    color: "#FFF",
    border: "1px solid #00A1FF",
    padding: "10px 25px",
    borderRadius: "8px",
    fontWeight: "bold",
    cursor: "pointer",
    boxShadow: "0 0 15px rgba(0, 161, 255, 0.3)",
  },
  metricsRow: {
    display: "grid",
    gridTemplateColumns: "repeat(4, 1fr)",
    gap: "15px",
    marginBottom: "25px",
  },
  metricCard: {
    backgroundColor: "rgba(20, 20, 25, 0.8)",
    border: "1px solid #333",
    padding: "20px",
    borderRadius: "8px",
    textAlign: "center" as const,
    display: "flex",
    flexDirection: "column" as const,
    alignItems: "center",
    gap: "6px",
  },
  grid: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: "25px" },
  card: {
    backgroundColor: "rgba(20, 20, 25, 0.8)",
    backdropFilter: "blur(15px)",
    border: "1px solid rgba(255, 255, 255, 0.05)",
    padding: "25px",
    borderRadius: "8px",
    boxShadow:
      "0 40px 100px rgba(0,0,0,0.8), inset 0 0 20px rgba(0, 161, 255, 0.05)",
  },
  label: {
    fontSize: "11px",
    color: "#555",
    marginBottom: "15px",
    letterSpacing: "1px",
  },
  projectRow: {
    padding: "10px 12px",
    borderBottom: "1px solid #1a1a1a",
    cursor: "pointer",
    display: "flex",
    flexDirection: "column" as const,
    gap: "2px",
  },
  rankRow: {
    display: "flex",
    justifyContent: "space-between",
    padding: "6px 0",
    borderBottom: "1px solid #1a1a1a",
    fontSize: 13,
  },
};

export default Dashboard;
