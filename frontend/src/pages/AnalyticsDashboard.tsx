import React, { useEffect, useState, useCallback } from "react";
import {
  FaChartLine,
  FaChartBar,
  FaChartPie,
  FaUsers,
  FaRobot,
  FaServer,
  FaShieldAlt,
  FaClock,
  FaCheckCircle,
  FaExclamationTriangle,
  FaSync,
  FaDownload,
  FaCalendarAlt,
  FaTachometerAlt,
  FaDatabase,
  FaMemory,
} from "react-icons/fa";
import { useTheme } from "../context/ThemeContext";
import { useLicense } from "../context/LicenseContext";
import { API_BASE_URL } from "../services/api";
import createStyles, { spacing, radius } from "../styles/shared";

// ── Tipos ──
interface KPI {
  name: string;
  current_value: number;
  target_value: number;
  unit: string;
  trend: "up" | "down" | "stable";
  change_percent: number;
  status: "on_track" | "at_risk" | "critical";
}

interface SystemComponent {
  status: "healthy" | "degraded" | "down";
  latency_ms?: number;
  uptime?: number;
  [key: string]: unknown;
}

interface AIEngine {
  name: string;
  accuracy: number;
  calls: number;
  avg_time_ms: number;
}

interface TopFeature {
  name: string;
  usage: number;
  change: number;
}

interface UserActivity {
  active_users_today: number;
  active_users_week: number;
  active_users_month: number;
  new_users_today: number;
  retention_rate: number;
  avg_session_duration: string;
  by_hour: number[];
}

interface AnalyticsDashboardData {
  kpis: Record<string, KPI>;
  system_health: {
    overall: string;
    components: Record<string, SystemComponent>;
    alerts: Array<{ level: string; message: string; time: string }>;
  };
  ai_performance: {
    overall_accuracy: number;
    engines: AIEngine[];
  };
  user_activity: UserActivity;
  top_features: TopFeature[];
  time_series: {
    labels: string[];
    datasets: Record<string, number[]>;
  };
}

// ── Componentes ──
const KPICard: React.FC<{
  kpi: KPI;
  theme: ReturnType<typeof useTheme>["theme"];
}> = ({ kpi, theme }) => {
  const statusColors = {
    on_track: "#00FF94",
    at_risk: "#FFD93D",
    critical: "#FF6B6B",
  };

  const trendIcons = {
    up: "↑",
    down: "↓",
    stable: "→",
  };

  return (
    <div
      style={{
        background: theme.panel,
        borderRadius: radius.lg,
        border: `1px solid ${theme.border}`,
        padding: spacing.md,
        position: "relative",
        overflow: "hidden",
      }}
    >
      <div
        style={{
          position: "absolute",
          top: 0,
          right: 0,
          width: 4,
          height: "100%",
          background: statusColors[kpi.status],
        }}
      />
      <div style={{ marginBottom: spacing.sm }}>
        <span style={{ color: theme.textSecondary, fontSize: 12 }}>
          {kpi.name}
        </span>
      </div>
      <div style={{ display: "flex", alignItems: "baseline", gap: spacing.xs }}>
        <span
          style={{ color: theme.textPrimary, fontSize: 28, fontWeight: 700 }}
        >
          {typeof kpi.current_value === "number"
            ? kpi.current_value.toLocaleString("pt-BR")
            : kpi.current_value}
        </span>
        <span style={{ color: theme.textSecondary, fontSize: 14 }}>
          {kpi.unit}
        </span>
      </div>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: spacing.xs,
          marginTop: spacing.xs,
        }}
      >
        <span
          style={{
            color:
              kpi.trend === "up"
                ? "#00FF94"
                : kpi.trend === "down"
                  ? "#FF6B6B"
                  : theme.textSecondary,
            fontSize: 12,
          }}
        >
          {trendIcons[kpi.trend]} {kpi.change_percent > 0 ? "+" : ""}
          {kpi.change_percent}%
        </span>
        <span style={{ color: theme.textSecondary, fontSize: 10 }}>
          Meta: {kpi.target_value.toLocaleString("pt-BR")} {kpi.unit}
        </span>
      </div>
    </div>
  );
};

const SystemHealthCard: React.FC<{
  health: AnalyticsDashboardData["system_health"];
  theme: ReturnType<typeof useTheme>["theme"];
}> = ({ health, theme }) => {
  const statusColors = {
    healthy: "#00FF94",
    degraded: "#FFD93D",
    down: "#FF6B6B",
  };

  return (
    <div
      style={{
        background: theme.panel,
        borderRadius: radius.lg,
        border: `1px solid ${theme.border}`,
        padding: spacing.md,
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: spacing.sm,
          marginBottom: spacing.md,
        }}
      >
        <span
          style={{
            color:
              statusColors[health.overall as keyof typeof statusColors] ||
              "#00FF94",
          }}
        >
          <FaServer />
        </span>
        <span style={{ color: theme.textPrimary, fontWeight: 600 }}>
          Sistema
        </span>
        <span
          style={{
            marginLeft: "auto",
            padding: "4px 12px",
            borderRadius: radius.sm,
            background: `${statusColors[health.overall as keyof typeof statusColors]}20`,
            color: statusColors[health.overall as keyof typeof statusColors],
            fontSize: 12,
            fontWeight: 600,
          }}
        >
          {health.overall?.toUpperCase()}
        </span>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
          gap: spacing.sm,
          maxWidth: "100%",
        }}
      >
        {Object.entries(health.components || {}).map(([name, comp]) => {
          const component = comp as SystemComponent;
          return (
            <div
              key={name}
              style={{
                padding: spacing.sm,
                borderRadius: radius.md,
                background: theme.bg,
                display: "flex",
                alignItems: "center",
                gap: spacing.xs,
              }}
            >
              <div
                style={{
                  width: 8,
                  height: 8,
                  borderRadius: "50%",
                  background: statusColors[component.status] || "#00FF94",
                }}
              />
              <span style={{ color: theme.textPrimary, fontSize: 12, flex: 1 }}>
                {name.replace(/_/g, " ")}
              </span>
              {component.latency_ms && (
                <span style={{ color: theme.textSecondary, fontSize: 10 }}>
                  {component.latency_ms}ms
                </span>
              )}
            </div>
          );
        })}
      </div>

      {health.alerts && health.alerts.length > 0 && (
        <div style={{ marginTop: spacing.md }}>
          <span
            style={{
              color: theme.textSecondary,
              fontSize: 11,
              marginBottom: spacing.xs,
              display: "block",
            }}
          >
            ALERTAS RECENTES
          </span>
          {health.alerts.slice(0, 3).map((alert, idx) => (
            <div
              key={idx}
              style={{
                padding: spacing.xs,
                borderRadius: radius.sm,
                background:
                  alert.level === "warning" ? "#FFD93D20" : "#00D4FF20",
                marginBottom: spacing.xs,
                display: "flex",
                alignItems: "center",
                gap: spacing.xs,
              }}
            >
              <span
                style={{
                  color: alert.level === "warning" ? "#FFD93D" : "#00D4FF",
                  fontSize: 10,
                }}
              >
                <FaExclamationTriangle />
              </span>
              <span style={{ color: theme.textPrimary, fontSize: 11, flex: 1 }}>
                {alert.message}
              </span>
              <span style={{ color: theme.textSecondary, fontSize: 10 }}>
                {alert.time}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

const AIPerformanceCard: React.FC<{
  performance: AnalyticsDashboardData["ai_performance"];
  theme: ReturnType<typeof useTheme>["theme"];
}> = ({ performance, theme }) => {
  return (
    <div
      style={{
        background: theme.panel,
        borderRadius: radius.lg,
        border: `1px solid ${theme.border}`,
        padding: spacing.md,
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: spacing.sm,
          marginBottom: spacing.md,
        }}
      >
        <span style={{ color: "#00D4FF" }}>
          <FaRobot />
        </span>
        <span style={{ color: theme.textPrimary, fontWeight: 600 }}>
          Performance das IAs
        </span>
        <span
          style={{
            marginLeft: "auto",
            color: "#00FF94",
            fontSize: 20,
            fontWeight: 700,
          }}
        >
          {performance.overall_accuracy}%
        </span>
      </div>

      <div
        style={{ display: "flex", flexDirection: "column", gap: spacing.xs }}
      >
        {(performance.engines || []).map((engine) => (
          <div
            key={engine.name}
            style={{
              padding: spacing.sm,
              borderRadius: radius.md,
              background: theme.bg,
            }}
          >
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                marginBottom: 4,
              }}
            >
              <span
                style={{
                  color: theme.textPrimary,
                  fontSize: 12,
                  fontWeight: 500,
                }}
              >
                {engine.name}
              </span>
              <span style={{ color: "#00FF94", fontSize: 12 }}>
                {engine.accuracy}%
              </span>
            </div>
            <div
              style={{
                height: 4,
                background: theme.border,
                borderRadius: 2,
                overflow: "hidden",
              }}
            >
              <div
                style={{
                  height: "100%",
                  width: `${engine.accuracy}%`,
                  background: `linear-gradient(90deg, #00D4FF, #00FF94)`,
                  borderRadius: 2,
                }}
              />
            </div>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                marginTop: 4,
              }}
            >
              <span style={{ color: theme.textSecondary, fontSize: 10 }}>
                {engine.calls.toLocaleString()} chamadas
              </span>
              <span style={{ color: theme.textSecondary, fontSize: 10 }}>
                {engine.avg_time_ms}ms médio
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

const UserActivityCard: React.FC<{
  activity: UserActivity;
  theme: ReturnType<typeof useTheme>["theme"];
}> = ({ activity, theme }) => {
  const maxHour = Math.max(...(activity.by_hour || [1]));

  return (
    <div
      style={{
        background: theme.panel,
        borderRadius: radius.lg,
        border: `1px solid ${theme.border}`,
        padding: spacing.md,
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: spacing.sm,
          marginBottom: spacing.md,
        }}
      >
        <span style={{ color: "#9B59B6" }}>
          <FaUsers />
        </span>
        <span style={{ color: theme.textPrimary, fontWeight: 600 }}>
          Atividade
        </span>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(100px, 1fr))",
          gap: spacing.sm,
          marginBottom: spacing.md,
          maxWidth: "100%",
        }}
      >
        <div style={{ textAlign: "center" }}>
          <div
            style={{ color: theme.textPrimary, fontSize: 24, fontWeight: 700 }}
          >
            {activity.active_users_today}
          </div>
          <div style={{ color: theme.textSecondary, fontSize: 10 }}>HOJE</div>
        </div>
        <div style={{ textAlign: "center" }}>
          <div
            style={{ color: theme.textPrimary, fontSize: 24, fontWeight: 700 }}
          >
            {activity.active_users_week}
          </div>
          <div style={{ color: theme.textSecondary, fontSize: 10 }}>SEMANA</div>
        </div>
        <div style={{ textAlign: "center" }}>
          <div
            style={{ color: theme.textPrimary, fontSize: 24, fontWeight: 700 }}
          >
            {activity.active_users_month}
          </div>
          <div style={{ color: theme.textSecondary, fontSize: 10 }}>MÊS</div>
        </div>
      </div>

      {/* Mini chart */}
      <div
        style={{ display: "flex", alignItems: "flex-end", height: 60, gap: 2 }}
      >
        {(activity.by_hour || []).map((value, idx) => (
          <div
            key={idx}
            style={{
              flex: 1,
              height: `${(value / maxHour) * 100}%`,
              background: `linear-gradient(180deg, #9B59B6, #9B59B640)`,
              borderRadius: "2px 2px 0 0",
              minHeight: 2,
            }}
          />
        ))}
      </div>

      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          marginTop: spacing.sm,
        }}
      >
        <span
          style={{
            color: theme.textSecondary,
            fontSize: 10,
            display: "flex",
            alignItems: "center",
            gap: 4,
          }}
        >
          <FaClock />
          Sessão média: {activity.avg_session_duration}
        </span>
        <span style={{ color: "#00FF94", fontSize: 10 }}>
          {activity.retention_rate}% retenção
        </span>
      </div>
    </div>
  );
};

const TopFeaturesCard: React.FC<{
  features: TopFeature[];
  theme: ReturnType<typeof useTheme>["theme"];
}> = ({ features, theme }) => {
  const maxUsage = Math.max(...features.map((f) => f.usage), 1);

  return (
    <div
      style={{
        background: theme.panel,
        borderRadius: radius.lg,
        border: `1px solid ${theme.border}`,
        padding: spacing.md,
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: spacing.sm,
          marginBottom: spacing.md,
        }}
      >
        <span style={{ color: "#FF8C00" }}>
          <FaChartBar />
        </span>
        <span style={{ color: theme.textPrimary, fontWeight: 600 }}>
          Features Mais Usadas
        </span>
      </div>

      <div
        style={{ display: "flex", flexDirection: "column", gap: spacing.xs }}
      >
        {features.slice(0, 6).map((feature, idx) => (
          <div key={idx}>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                marginBottom: 2,
              }}
            >
              <span style={{ color: theme.textPrimary, fontSize: 12 }}>
                {feature.name}
              </span>
              <span style={{ color: theme.textSecondary, fontSize: 11 }}>
                {feature.usage.toLocaleString()}
                <span
                  style={{
                    marginLeft: 4,
                    color: feature.change > 0 ? "#00FF94" : "#FF6B6B",
                  }}
                >
                  {feature.change > 0 ? "+" : ""}
                  {feature.change}%
                </span>
              </span>
            </div>
            <div
              style={{
                height: 4,
                background: theme.border,
                borderRadius: 2,
                overflow: "hidden",
              }}
            >
              <div
                style={{
                  height: "100%",
                  width: `${(feature.usage / maxUsage) * 100}%`,
                  background: `hsl(${idx * 40 + 200}, 70%, 50%)`,
                  borderRadius: 2,
                }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

// ── Página Principal ──
const AnalyticsDashboard: React.FC = () => {
  const { theme } = useTheme();
  const styles = createStyles(theme);
  const { canUse, triggerUpgrade } = useLicense();
  const [data, setData] = useState<AnalyticsDashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [period, setPeriod] = useState<"24h" | "7d" | "30d">("24h");
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());

  const loadData = useCallback(async () => {
    try {
      const token = localStorage.getItem("token");
      const headers: Record<string, string> = {};
      if (token) headers["Authorization"] = `Bearer ${token}`;
      const res = await fetch(`${API_BASE_URL}/api/analytics/dashboard`, { headers });
      if (res.ok) {
        const dashboardData = await res.json();
        setData(dashboardData);
        setLastUpdate(new Date());
      }
    } catch (err) {
      console.error("Erro ao carregar analytics:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 30000); // Atualiza a cada 30s
    return () => clearInterval(interval);
  }, [loadData]);

  if (loading) {
    return (
      <div
        style={{
          ...styles.pageContainer,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <span style={{ color: theme.accentPrimary }}>
          <FaSync size={40} />
        </span>
      </div>
    );
  }

  const kpis = data?.kpis || {};
  const systemHealth = data?.system_health || {
    overall: "unknown",
    components: {},
    alerts: [],
  };
  const aiPerformance = data?.ai_performance || {
    overall_accuracy: 0,
    engines: [],
  };
  const userActivity = data?.user_activity || {
    active_users_today: 0,
    active_users_week: 0,
    active_users_month: 0,
    new_users_today: 0,
    retention_rate: 0,
    avg_session_duration: "0 min",
    by_hour: [],
  };
  const topFeatures = data?.top_features || [];

  // ── Feature gate: Analytics requires paid plan ──
  if (!canUse("analytics")) {
    return (
      <div
        style={{
          minHeight: "100vh",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          background: theme.background || "#050507",
          gap: "24px",
          padding: "32px",
          textAlign: "center",
        }}
      >
        <div style={{ fontSize: "64px" }}>📊</div>
        <h2
          style={{
            color: theme.textPrimary || "#fff",
            fontSize: "24px",
            fontWeight: 700,
            margin: 0,
          }}
        >
          Analytics Avançado
        </h2>
        <p
          style={{
            color: "#8899aa",
            fontSize: "15px",
            maxWidth: "480px",
            lineHeight: 1.6,
            margin: 0,
          }}
        >
          Acesse KPIs em tempo real, saúde do sistema, performance de IA e
          atividade de usuários com os planos
          <strong style={{ color: "#00A1FF" }}> Professional</strong> ou{" "}
          <strong style={{ color: "#A855F7" }}>Enterprise</strong>.
        </p>
        <div
          style={{
            display: "flex",
            gap: "12px",
            flexWrap: "wrap",
            justifyContent: "center",
          }}
        >
          <button
            onClick={() =>
              triggerUpgrade(
                "Analytics Avançado está disponível no plano Professional ou Enterprise.",
              )
            }
            style={{
              padding: "14px 32px",
              background: "linear-gradient(135deg, #00A1FF, #0077BB)",
              color: "#fff",
              border: "none",
              borderRadius: "10px",
              fontSize: "15px",
              fontWeight: 700,
              cursor: "pointer",
            }}
          >
            🚀 Ver Planos
          </button>
          <button
            onClick={() => {
              const t = encodeURIComponent(
                "Olá! Quero saber mais sobre o Analytics do Engenharia CAD.",
              );
              window.open(`https://wa.me/5531992681231?text=${t}`, "_blank");
            }}
            style={{
              padding: "14px 32px",
              background: "#25D366",
              color: "#fff",
              border: "none",
              borderRadius: "10px",
              fontSize: "15px",
              fontWeight: 700,
              cursor: "pointer",
            }}
          >
            💬 Falar com Consultor
          </button>
        </div>
        <div
          style={{
            display: "flex",
            gap: "12px",
            flexWrap: "wrap",
            justifyContent: "center",
            marginTop: "8px",
          }}
        >
          {[
            "KPIs em tempo real",
            "Saúde do sistema",
            "Performance IA",
            "Atividade de usuários",
          ].map((f) => (
            <div
              key={f}
              style={{
                background: "#111827",
                border: "1px solid #1e3050",
                borderRadius: "8px",
                padding: "8px 16px",
                color: "#a0b0c0",
                fontSize: "13px",
                opacity: 0.6,
              }}
            >
              🔒 {f}
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div style={{ ...styles.pageContainer, padding: 0 }}>
      <main style={{ flex: 1, padding: spacing.lg, overflowY: "auto" }}>
        {/* Header */}
        <header style={styles.pageHeader}>
          <div>
            <h1 style={styles.pageTitle}>
              <span style={{ color: "#FF8C00", display: "flex" }}>
                <FaTachometerAlt />
              </span>
              Analytics Dashboard
            </h1>
            <p style={styles.pageSubtitle}>
              Última atualização: {lastUpdate.toLocaleTimeString("pt-BR")}
            </p>
          </div>
          <div style={{ display: "flex", gap: spacing.sm }}>
            {(["24h", "7d", "30d"] as const).map((p) => (
              <button
                key={p}
                onClick={() => setPeriod(p)}
                style={{
                  padding: `${spacing.xs} ${spacing.md}`,
                  borderRadius: radius.md,
                  border: `1px solid ${period === p ? theme.accentPrimary : theme.border}`,
                  background:
                    period === p ? `${theme.accentPrimary}20` : "transparent",
                  color:
                    period === p ? theme.accentPrimary : theme.textSecondary,
                  cursor: "pointer",
                  fontSize: 12,
                }}
              >
                {p}
              </button>
            ))}
            <button
              onClick={loadData}
              style={{
                ...styles.buttonPrimary,
                background: `linear-gradient(135deg, #FF8C00 0%, #FF8C00CC 100%)`,
              }}
            >
              <FaSync size={12} /> ATUALIZAR
            </button>
            <button
              style={{
                padding: `${spacing.xs} ${spacing.md}`,
                borderRadius: radius.md,
                border: `1px solid ${theme.border}`,
                background: "transparent",
                color: theme.textSecondary,
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                gap: spacing.xs,
              }}
            >
              <FaDownload size={12} /> EXPORTAR
            </button>
          </div>
        </header>

        {/* KPIs Grid */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
            gap: spacing.md,
            marginBottom: spacing.lg,
            maxWidth: "100%",
          }}
        >
          {Object.entries(kpis)
            .slice(0, 8)
            .map(([key, kpi]) => (
              <KPICard key={key} kpi={kpi} theme={theme} />
            ))}
        </div>

        {/* Main Grid */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))",
            gap: spacing.lg,
          }}
        >
          {/* Coluna 1: System Health */}
          <SystemHealthCard health={systemHealth} theme={theme} />

          {/* Coluna 2: AI Performance */}
          <AIPerformanceCard performance={aiPerformance} theme={theme} />

          {/* Coluna 3: User Activity */}
          <UserActivityCard activity={userActivity} theme={theme} />
        </div>

        {/* Bottom Grid */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "2fr 1fr",
            gap: spacing.lg,
            marginTop: spacing.lg,
          }}
        >
          {/* Time Series Chart Placeholder */}
          <div
            style={{
              background: theme.panel,
              borderRadius: radius.lg,
              border: `1px solid ${theme.border}`,
              padding: spacing.md,
            }}
          >
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: spacing.sm,
                marginBottom: spacing.md,
              }}
            >
              <span style={{ color: "#00D4FF" }}>
                <FaChartLine />
              </span>
              <span style={{ color: theme.textPrimary, fontWeight: 600 }}>
                Requisições por Hora
              </span>
            </div>
            <div
              style={{
                height: 200,
                display: "flex",
                alignItems: "flex-end",
                gap: 4,
                padding: spacing.sm,
              }}
            >
              {(data?.time_series?.datasets?.requests || []).map(
                (value, idx) => {
                  const max = Math.max(
                    ...(data?.time_series?.datasets?.requests || [1]),
                  );
                  return (
                    <div
                      key={idx}
                      style={{
                        flex: 1,
                        height: `${(value / max) * 100}%`,
                        background: `linear-gradient(180deg, #00D4FF, #00D4FF40)`,
                        borderRadius: "4px 4px 0 0",
                        minHeight: 4,
                      }}
                    />
                  );
                },
              )}
            </div>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                marginTop: spacing.xs,
              }}
            >
              <span style={{ color: theme.textSecondary, fontSize: 10 }}>
                00:00
              </span>
              <span style={{ color: theme.textSecondary, fontSize: 10 }}>
                12:00
              </span>
              <span style={{ color: theme.textSecondary, fontSize: 10 }}>
                23:00
              </span>
            </div>
          </div>

          {/* Top Features */}
          <TopFeaturesCard features={topFeatures} theme={theme} />
        </div>
      </main>
    </div>
  );
};

export default AnalyticsDashboard;
