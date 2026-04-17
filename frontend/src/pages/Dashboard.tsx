import React, { useEffect, useState, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import {
  FaChartLine,
  FaBox,
  FaDraftingCompass,
  FaShieldAlt,
  FaPlus,
} from "react-icons/fa";
import {
  Flame,
  Layers,
  Activity,
  Settings,
  Upload,
  FileText,
  Ruler,
  Target,
  Zap,
  TrendingUp,
  Clock,
  CheckCircle,
  Download,
} from "lucide-react";
import { ApiService, ProjectStats, ProjectRecord } from "../services/api";
import { useTheme } from "../context/ThemeContext";
import { useLicense } from "../context/LicenseContext";
import createStyles, { spacing, radius } from "../styles/shared";
import {
  WelcomeHero,
  ProgressRing,
  MetricCardAdvanced,
  QuickActionCard,
  ActivityTimeline,
  SystemHealthBar,
  MiniBarChart,
  ProjectCard,
} from "../components/DashboardWidgets";
import { AutoCADConnectButton } from "../components/AutoCADConnectButton";
import OnboardingWalkthrough from "../components/OnboardingWalkthrough";

const Dashboard = () => {
  const navigate = useNavigate();
  const { theme } = useTheme();
  const { license } = useLicense();
  const styles = createStyles(theme);
  const isDemo = license.tier === "demo";
  const queriesUsed = license.aiQueriesUsed;
  const queriesLimit = license.aiQueriesLimit;
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

  // Theme for widgets
  const widgetTheme = useMemo(
    () => ({
      surface: theme.surface ?? theme.panel,
      panel: theme.panel,
      border: theme.border,
      accentPrimary: theme.accentPrimary,
      success: theme.success,
      warning: theme.warning,
      danger: theme.danger,
      textPrimary: theme.textPrimary,
      textSecondary: theme.textSecondary,
      textTertiary: theme.textTertiary,
      inputBackground: theme.inputBackground,
      background: theme.background,
    }),
    [theme],
  );

  // Quick actions
  const quickActions = useMemo(
    () => [
      {
        id: "new-project",
        label: "Novo Projeto",
        description: "Criar um novo projeto de engenharia",
        icon: <FaPlus size={20} />,
        color: theme.accentPrimary,
        onClick: () => navigate("/global-setup"),
      },
      {
        id: "cnc",
        label: "Controle CNC",
        description: "Gerar G-code para corte plasma",
        icon: <Flame size={20} />,
        color: theme.warning,
        onClick: () => navigate("/cnc-control"),
        badge: 2,
      },
      {
        id: "cad",
        label: "CAD Dashboard",
        description: "Visualizar e editar desenhos",
        icon: <Layers size={20} />,
        color: theme.success,
        onClick: () => navigate("/cad-dashboard"),
      },
      {
        id: "analytics",
        label: "Analytics",
        description: "Ver métricas e relatórios",
        icon: <TrendingUp size={20} />,
        color: "#AA66FF",
        onClick: () => navigate("/analytics"),
      },
    ],
    [navigate, theme],
  );

  // System status
  const systemStatus = useMemo(
    () => [
      { name: "API Server", status: "online" as const, latency: 42 },
      { name: "Database", status: "online" as const, latency: 15 },
      {
        name: "AutoCAD Link",
        status: "online" as const,
        message: "Cloud Mode",
      },
      { name: "CNC Queue", status: "online" as const, latency: 8 },
    ],
    [],
  );

  // Recent activities (mock - in production would come from API)
  const activities = useMemo(
    () => [
      {
        id: "1",
        type: "project" as const,
        action: "Projeto criado",
        description: "Flange DN-150 para Petrobras",
        timestamp: new Date(Date.now() - 5 * 60000),
        status: "success" as const,
      },
      {
        id: "2",
        type: "cnc" as const,
        action: "G-code gerado",
        description: "3 peças exportadas para corte",
        timestamp: new Date(Date.now() - 25 * 60000),
        status: "success" as const,
      },
      {
        id: "3",
        type: "validation" as const,
        action: "Validação concluída",
        description: "ASME B16.5 verificada",
        timestamp: new Date(Date.now() - 60 * 60000),
        status: "success" as const,
      },
      {
        id: "4",
        type: "export" as const,
        action: "DXF exportado",
        description: "Desenho técnico enviado ao AutoCAD",
        timestamp: new Date(Date.now() - 120 * 60000),
        status: "success" as const,
      },
      {
        id: "5",
        type: "system" as const,
        action: "Backup automático",
        description: "Database backup completed",
        timestamp: new Date(Date.now() - 180 * 60000),
        status: "success" as const,
      },
    ],
    [],
  );

  // Weekly activity data for chart
  const weeklyData = useMemo(() => [5, 12, 8, 15, 10, 7, 3], []);
  const weekLabels = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"];

  return (
    <div
      style={{
        ...styles.pageContainer,
        padding: 0,
        overflow: "hidden",
        background: theme.gradientPage || theme.background,
      }}
    >
      <main
        style={{
          flex: 1,
          padding: spacing.lg,
          overflowY: "auto",
          overflowX: "hidden",
          maxWidth: "100%",
          boxSizing: "border-box",
        }}
      >
        {/* Header com AutoCAD Status */}
        <div
          style={{
            display: "flex",
            justifyContent: "flex-end",
            marginBottom: 24,
          }}
        >
          <AutoCADConnectButton />
        </div>
        {/* Welcome Hero */}
        <WelcomeHero userName="Operador" theme={widgetTheme} />

        {/* Guided Walkthrough — first 7 days */}
        <OnboardingWalkthrough onNavigate={(path) => navigate(path)} />

        {/* Onboarding CTA — shown when no projects or demo mode */}
        {!loading && (total === 0 || isDemo) && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            style={{
              marginBottom: 24,
              padding: 28,
              borderRadius: 16,
              background: `linear-gradient(135deg, ${theme.accentPrimary}12, ${theme.accentPrimary}04)`,
              border: `1px solid ${theme.accentPrimary}30`,
              display: "flex",
              flexDirection: "column",
              gap: 16,
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <Target size={24} color={theme.accentPrimary} />
              <h3
                style={{
                  margin: 0,
                  fontSize: 17,
                  fontWeight: 700,
                  color: theme.textPrimary,
                }}
              >
                {isDemo ? "Bem-vindo à demonstração!" : "Primeiros Passos"}
              </h3>
            </div>
            <p
              style={{
                margin: 0,
                fontSize: 14,
                color: theme.textSecondary,
                lineHeight: 1.7,
              }}
            >
              {isDemo
                ? "Explore a plataforma livremente. Para liberar todas as funcionalidades, crie sua conta gratuita com 14 dias de teste."
                : "Crie seu primeiro projeto para ver a plataforma em ação. Configure um projeto de piping, valide normas e gere desenhos automaticamente."}
            </p>
            <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
              {isDemo && (
                <button
                  onClick={() => navigate("/pricing")}
                  style={{
                    padding: "12px 24px",
                    background:
                      "linear-gradient(135deg, #00A1FF 0%, #0077CC 100%)",
                    border: "none",
                    borderRadius: 10,
                    color: "#FFF",
                    fontSize: 13,
                    fontWeight: 700,
                    cursor: "pointer",
                    display: "flex",
                    alignItems: "center",
                    gap: 8,
                    boxShadow: "0 4px 20px rgba(0,161,255,0.3)",
                  }}
                >
                  <Zap size={16} />
                  Criar Conta Grátis (14 dias)
                </button>
              )}
              <button
                onClick={() => navigate("/global-setup")}
                style={{
                  padding: "12px 24px",
                  background: isDemo
                    ? "transparent"
                    : "linear-gradient(135deg, #00A1FF 0%, #0077CC 100%)",
                  border: isDemo ? `1px solid ${theme.border}` : "none",
                  borderRadius: 10,
                  color: isDemo ? theme.textSecondary : "#FFF",
                  fontSize: 13,
                  fontWeight: 600,
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  boxShadow: isDemo ? "none" : "0 4px 20px rgba(0,161,255,0.3)",
                }}
              >
                <FaPlus size={14} />
                {total === 0 ? "Criar Primeiro Projeto" : "Novo Projeto"}
              </button>
            </div>

            {/* Quick value metrics */}
            {isDemo && (
              <div
                style={{
                  display: "flex",
                  gap: 24,
                  marginTop: 8,
                  paddingTop: 16,
                  borderTop: `1px solid ${theme.border}`,
                }}
              >
                {[
                  { label: "Tempo médio economizado", value: "4h/projeto" },
                  { label: "Redução de retrabalho", value: "70%" },
                  { label: "Normas validadas", value: "50+" },
                ].map((stat, i) => (
                  <div key={i} style={{ textAlign: "center", flex: 1 }}>
                    <div
                      style={{
                        fontSize: 18,
                        fontWeight: 800,
                        color: theme.accentPrimary,
                      }}
                    >
                      {stat.value}
                    </div>
                    <div
                      style={{
                        fontSize: 11,
                        color: theme.textTertiary,
                        marginTop: 4,
                      }}
                    >
                      {stat.label}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </motion.div>
        )}
        {/* System Status Bar */}
        <div style={{ marginBottom: 24 }}>
          <SystemHealthBar systems={systemStatus} theme={widgetTheme} />
        </div>

        {/* Quota warning banner */}
        {queriesLimit > 0 && queriesUsed >= queriesLimit * 0.8 && (
          <div
            style={{
              marginBottom: 24,
              padding: "14px 20px",
              borderRadius: 12,
              background:
                queriesUsed >= queriesLimit
                  ? `${theme.danger}15`
                  : `${theme.warning}15`,
              border: `1px solid ${
                queriesUsed >= queriesLimit ? theme.danger : theme.warning
              }40`,
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              flexWrap: "wrap",
              gap: 12,
            }}
          >
            <span
              style={{
                fontSize: 13,
                color:
                  queriesUsed >= queriesLimit ? theme.danger : theme.warning,
                fontWeight: 600,
              }}
            >
              {queriesUsed >= queriesLimit
                ? `⛔ Limite de consultas IA atingido (${queriesUsed}/${queriesLimit})`
                : `⚠️ ${queriesLimit - queriesUsed} consultas IA restantes (${queriesUsed}/${queriesLimit})`}
            </span>
            <button
              onClick={() => navigate("/pricing")}
              style={{
                padding: "8px 18px",
                background: "linear-gradient(135deg, #00A1FF, #0077CC)",
                border: "none",
                borderRadius: 8,
                color: "#FFF",
                fontSize: 12,
                fontWeight: 700,
                cursor: "pointer",
              }}
            >
              Fazer Upgrade
            </button>
          </div>
        )}
        {/* Quick Actions */}
        <div style={{ marginBottom: 24 }}>
          <h2
            style={{
              fontSize: 16,
              fontWeight: 600,
              color: theme.textPrimary,
              marginBottom: 16,
              display: "flex",
              alignItems: "center",
              gap: 8,
            }}
          >
            <Zap size={18} color={theme.accentPrimary} />
            Ações Rápidas
          </h2>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
              gap: 16,
              maxWidth: "100%",
            }}
          >
            {quickActions.map((action) => (
              <QuickActionCard
                key={action.id}
                action={action}
                theme={widgetTheme}
              />
            ))}
          </div>
        </div>
        {/* Metrics Row */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
            gap: 16,
            marginBottom: 24,
          }}
        >
          <MetricCardAdvanced
            icon={<FaBox size={20} />}
            label="Total Projetos"
            value={total}
            trend={total > 0 ? 12 : undefined}
            trendLabel="vs mês anterior"
            color={theme.accentPrimary}
            theme={widgetTheme}
            onClick={() => navigate("/quality")}
          />
          <MetricCardAdvanced
            icon={<FaDraftingCompass size={20} />}
            label="Concluídos"
            value={completed}
            trend={completed > 0 ? 8 : undefined}
            color={theme.success}
            theme={widgetTheme}
          />
          <MetricCardAdvanced
            icon={<FaChartLine size={20} />}
            label="Empresas"
            value={companies.length}
            color={theme.warning}
            theme={widgetTheme}
          />
          <MetricCardAdvanced
            icon={<FaShieldAlt size={20} />}
            label="Normas Ativas"
            value={3}
            color={theme.accentInfo || theme.accentPrimary}
            theme={widgetTheme}
          />
        </div>
        {/* Main Grid */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))",
            gap: 24,
            maxWidth: "100%",
          }}
        >
          {/* Recent Projects */}
          <div
            style={{
              background: theme.gradientPanel || theme.surface,
              border: `1px solid ${theme.borderStrong || theme.border}`,
              borderRadius: 16,
              padding: 20,
              minWidth: 0,
              overflow: "hidden",
            }}
          >
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                marginBottom: 16,
              }}
            >
              <h3
                style={{
                  fontSize: 14,
                  fontWeight: 600,
                  color: theme.textPrimary,
                  margin: 0,
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                }}
              >
                <FileText size={18} color={theme.accentPrimary} />
                Últimos Projetos
              </h3>
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={() => navigate("/global-setup")}
                style={{
                  padding: "8px 16px",
                  border: "none",
                  borderRadius: 8,
                  background: `linear-gradient(135deg, ${theme.accentPrimary}, ${theme.accentPrimary}CC)`,
                  color: "#fff",
                  fontSize: 12,
                  fontWeight: 600,
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  gap: 6,
                }}
              >
                <FaPlus size={10} /> Novo
              </motion.button>
            </div>

            {loading ? (
              <div
                style={{
                  padding: 40,
                  textAlign: "center",
                  color: theme.textTertiary,
                }}
              >
                <motion.div
                  animate={{ rotate: 360 }}
                  transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                >
                  <Activity size={24} />
                </motion.div>
                <p style={{ marginTop: 12, fontSize: 13 }}>Carregando...</p>
              </div>
            ) : projects.length === 0 ? (
              <div
                style={{
                  padding: 40,
                  textAlign: "center",
                  color: theme.textTertiary,
                }}
              >
                <FileText
                  size={32}
                  style={{ marginBottom: 12, opacity: 0.5 }}
                />
                <p style={{ fontSize: 13, marginBottom: 16 }}>
                  Nenhum projeto ainda
                </p>
                <motion.button
                  whileHover={{ scale: 1.02 }}
                  onClick={() => navigate("/global-setup")}
                  style={{
                    padding: "10px 20px",
                    border: `1px solid ${theme.accentPrimary}`,
                    borderRadius: 8,
                    backgroundColor: "transparent",
                    color: theme.accentPrimary,
                    fontSize: 12,
                    fontWeight: 600,
                    cursor: "pointer",
                  }}
                >
                  Criar Primeiro Projeto
                </motion.button>
              </div>
            ) : (
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  gap: 8,
                  maxHeight: 400,
                  overflowY: "auto",
                }}
              >
                {projects.map((p) => (
                  <ProjectCard
                    key={p.id}
                    project={{
                      id: p.id,
                      code: p.code,
                      company: p.company,
                      diameter: p.diameter,
                      length: p.length,
                      status: p.status,
                      progress: p.status === "completed" ? 100 : 65,
                    }}
                    onClick={() => navigate(`/quality?project=${p.id}`)}
                    theme={widgetTheme}
                  />
                ))}
              </div>
            )}
          </div>
          {/* Progress & Charts Column */}
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            {/* Completion Rate */}
            <div
              style={{
                background: theme.gradientPanel || theme.surface,
                border: `1px solid ${theme.borderStrong || theme.border}`,
                borderRadius: 16,
                padding: 20,
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
              }}
            >
              <h3
                style={{
                  fontSize: 14,
                  fontWeight: 600,
                  color: theme.textPrimary,
                  marginBottom: 16,
                  alignSelf: "flex-start",
                }}
              >
                Taxa de Conclusão
              </h3>
              <ProgressRing
                value={completed}
                max={total || 1}
                size={140}
                strokeWidth={12}
                color={theme.success}
                label="Projetos Concluídos"
                theme={widgetTheme}
              />
            </div>
            {/* Weekly Activity */}
            <div
              style={{
                background: theme.gradientPanel || theme.surface,
                border: `1px solid ${theme.borderStrong || theme.border}`,
                borderRadius: 16,
                padding: 20,
              }}
            >
              <h3
                style={{
                  fontSize: 14,
                  fontWeight: 600,
                  color: theme.textPrimary,
                  marginBottom: 16,
                }}
              >
                Atividade Semanal
              </h3>
              <MiniBarChart
                data={weeklyData}
                labels={weekLabels}
                color={theme.accentPrimary}
                height={100}
                theme={widgetTheme}
              />
            </div>
          </div>
          {/* Activity Timeline */}
          <ActivityTimeline
            activities={activities}
            maxItems={5}
            theme={widgetTheme}
          />
        </div>
        {/* Rankings Row */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
            gap: 24,
            marginTop: 24,
            maxWidth: "100%",
          }}
        >
          {/* Top Companies */}
          <div
            style={{
              background: theme.gradientPanel || theme.surface,
              border: `1px solid ${theme.borderStrong || theme.border}`,
              borderRadius: 16,
              padding: 20,
              minWidth: 0,
              overflow: "hidden",
            }}
          >
            <h3
              style={{
                fontSize: 14,
                fontWeight: 600,
                color: theme.textPrimary,
                marginBottom: 16,
                display: "flex",
                alignItems: "center",
                gap: 8,
              }}
            >
              <Target size={18} color={theme.warning} />
              Top Empresas
            </h3>
            {companies.length > 0 ? (
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {companies.slice(0, 5).map(([name, count], i) => (
                  <div
                    key={i}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 12,
                      padding: "10px 12px",
                      backgroundColor:
                        i === 0 ? `${theme.warning}10` : "transparent",
                      borderRadius: 8,
                    }}
                  >
                    <div
                      style={{
                        width: 28,
                        height: 28,
                        borderRadius: 8,
                        backgroundColor: i === 0 ? theme.warning : theme.border,
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        color: i === 0 ? "#fff" : theme.textSecondary,
                        fontSize: 12,
                        fontWeight: 700,
                      }}
                    >
                      {i + 1}
                    </div>
                    <span
                      style={{
                        flex: 1,
                        fontSize: 13,
                        color: theme.textPrimary,
                      }}
                    >
                      {name || "Sem nome"}
                    </span>
                    <span
                      style={{
                        fontSize: 14,
                        fontWeight: 600,
                        color: theme.accentPrimary,
                      }}
                    >
                      {count} projetos
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <p style={{ color: theme.textTertiary, fontSize: 13 }}>
                Gere projetos para ver rankings
              </p>
            )}
          </div>
          {/* Top Parts */}
          <div
            style={{
              background: theme.gradientPanel || theme.surface,
              border: `1px solid ${theme.borderStrong || theme.border}`,
              borderRadius: 16,
              padding: 20,
            }}
          >
            <h3
              style={{
                fontSize: 14,
                fontWeight: 600,
                color: theme.textPrimary,
                marginBottom: 16,
                display: "flex",
                alignItems: "center",
                gap: 8,
              }}
            >
              <Ruler size={18} color={theme.success} />
              Top Peças
            </h3>
            {parts.length > 0 ? (
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {parts.slice(0, 5).map(([name, count], i) => (
                  <div
                    key={i}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 12,
                      padding: "10px 12px",
                      backgroundColor:
                        i === 0 ? `${theme.success}10` : "transparent",
                      borderRadius: 8,
                    }}
                  >
                    <div
                      style={{
                        width: 28,
                        height: 28,
                        borderRadius: 8,
                        backgroundColor: i === 0 ? theme.success : theme.border,
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        color: i === 0 ? "#fff" : theme.textSecondary,
                        fontSize: 12,
                        fontWeight: 700,
                      }}
                    >
                      {i + 1}
                    </div>
                    <span
                      style={{
                        flex: 1,
                        fontSize: 13,
                        color: theme.textPrimary,
                      }}
                    >
                      {name || "Sem nome"}
                    </span>
                    <span
                      style={{
                        fontSize: 14,
                        fontWeight: 600,
                        color: theme.success,
                      }}
                    >
                      {count} usos
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <p style={{ color: theme.textTertiary, fontSize: 13 }}>
                Gere projetos para ver rankings
              </p>
            )}
          </div>
        </div>
      </main>
    </div>
  );
};

export default Dashboard;
