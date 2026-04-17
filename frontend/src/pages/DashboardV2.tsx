/**
 * Dashboard v2.0 — AutomAção CAD Enterprise
 *
 * Redesigned with enterprise/luxury styling:
 * - Glass hero section with gradient mesh background
 * - KPI cards with glow effects and sparklines
 * - Stagger animations for smooth entry
 * - Responsive design with bottom tab bar on mobile
 */

import React, { useCallback, useEffect, useState, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import {
  LayoutDashboard,
  Layers,
  TrendingUp,
  Zap,
  Plus,
  Flame,
  Target,
  Activity,
  Clock,
  CheckCircle2,
  ArrowUpRight,
  FileText,
  Settings,
  Bell,
  ChevronRight,
  Sparkles,
  MessageSquare,
  User,
} from "lucide-react";

// Design System
import {
  colors,
  spacing,
  radius,
  shadows,
  media,
  breakpoints,
} from "../design/tokens";
import { fontFamily, textStyles } from "../design/typography";
import {
  staggerContainer,
  staggerItem,
  fadeIn,
  fadeInScale,
  hoverLift,
  tapScale,
  slideUp,
} from "../design/animations";

// UI Components
import { Button } from "../components/ui/Button";
import Card from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { BottomTabBar, TabItem } from "../components/ui/BottomTabBar";

// Context & Services
import { useTheme } from "../context/ThemeContext";
import { useLicense } from "../context/LicenseContext";
import { ApiService, ProjectStats, ProjectRecord } from "../services/api";
import { AutoCADConnectButton } from "../components/AutoCADConnectButton";
import {
  OnboardingTour,
  DEFAULT_TOUR_STEPS,
} from "../components/OnboardingTour";

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// TYPES
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

interface KPIMetric {
  id: string;
  label: string;
  value: number | string;
  trend?: number;
  trendLabel?: string;
  icon: React.ReactNode;
  color: string;
  onClick?: () => void;
}

interface QuickAction {
  id: string;
  label: string;
  description: string;
  icon: React.ReactNode;
  color: string;
  path: string;
  badge?: number | string;
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// SUBCOMPONENTS
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

// Glass Hero Section
const HeroSection: React.FC<{
  userName: string;
  isDemo: boolean;
  onNewProject: () => void;
  onUpgrade: () => void;
}> = ({ userName, isDemo, onNewProject, onUpgrade }) => {
  const hour = new Date().getHours();
  const greeting =
    hour < 12 ? "Bom dia" : hour < 18 ? "Boa tarde" : "Boa noite";

  return (
    <motion.div
      variants={fadeInScale}
      initial="hidden"
      animate="visible"
      style={{
        position: "relative",
        padding: spacing[8],
        borderRadius: radius.xl,
        background: "rgba(255, 255, 255, 0.02)",
        backdropFilter: "blur(20px)",
        border: `1px solid ${colors.border.subtle}`,
        marginBottom: spacing[8],
        overflow: "hidden",
      }}
    >
      {/* Gradient mesh background */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          background: colors.gradient.mesh,
          opacity: 0.6,
          pointerEvents: "none",
        }}
      />

      {/* Content */}
      <div style={{ position: "relative", zIndex: 1 }}>
        {/* Greeting */}
        <motion.div variants={slideUp}>
          <p
            style={{
              margin: 0,
              ...textStyles.body.sm,
              color: colors.text.tertiary,
              textTransform: "uppercase",
              letterSpacing: "0.1em",
              marginBottom: spacing[2],
            }}
          >
            {greeting}
          </p>
          <h1
            style={{
              margin: 0,
              ...textStyles.display.md,
              color: colors.text.primary,
              marginBottom: spacing[3],
            }}
          >
            {userName}
            <span
              style={{
                background: colors.gradient.primary,
                WebkitBackgroundClip: "text",
                WebkitTextFillColor: "transparent",
                backgroundClip: "text",
              }}
            >
              .
            </span>
          </h1>
          <p
            style={{
              margin: 0,
              ...textStyles.body.lg,
              color: colors.text.secondary,
              maxWidth: "500px",
              marginBottom: spacing[6],
            }}
          >
            {isDemo
              ? "Explore a plataforma livremente. Crie sua conta para desbloquear todas as funcionalidades."
              : "Gerencie seus projetos de engenharia com automação inteligente."}
          </p>
        </motion.div>

        {/* CTA Buttons */}
        <motion.div
          variants={slideUp}
          style={{
            display: "flex",
            gap: spacing[3],
            flexWrap: "wrap",
          }}
        >
          <Button
            variant="primary"
            size="lg"
            glow
            leftIcon={<Plus size={18} />}
            onClick={onNewProject}
          >
            Novo Projeto
          </Button>
          {isDemo && (
            <Button
              variant="gold"
              size="lg"
              glow
              leftIcon={<Sparkles size={18} />}
              onClick={onUpgrade}
            >
              14 Dias Grátis
            </Button>
          )}
        </motion.div>

        {/* Quick Stats */}
        {isDemo && (
          <motion.div
            variants={slideUp}
            style={{
              display: "flex",
              gap: spacing[8],
              marginTop: spacing[8],
              paddingTop: spacing[6],
              borderTop: `1px solid ${colors.border.subtle}`,
            }}
          >
            {[
              { value: "4h", label: "Economia/projeto" },
              { value: "70%", label: "Menos retrabalho" },
              { value: "50+", label: "Normas validadas" },
            ].map((stat, i) => (
              <div key={i}>
                <div
                  style={{
                    ...textStyles.display.sm,
                    background: colors.gradient.primary,
                    WebkitBackgroundClip: "text",
                    WebkitTextFillColor: "transparent",
                    backgroundClip: "text",
                  }}
                >
                  {stat.value}
                </div>
                <div
                  style={{ ...textStyles.caption, color: colors.text.tertiary }}
                >
                  {stat.label}
                </div>
              </div>
            ))}
          </motion.div>
        )}
      </div>
    </motion.div>
  );
};

// KPI Card Component
const KPICard: React.FC<{ metric: KPIMetric; index: number }> = ({
  metric,
  index,
}) => (
  <motion.div
    variants={staggerItem}
    custom={index}
    whileHover={metric.onClick ? hoverLift : undefined}
    whileTap={metric.onClick ? tapScale : undefined}
    onClick={metric.onClick}
    style={{ cursor: metric.onClick ? "pointer" : "default" }}
  >
    <Card
      variant="glass"
      size="md"
      hover={Boolean(metric.onClick)}
      glow={Boolean(metric.onClick)}
      glowColor={metric.color.replace(")", ", 0.3)").replace("rgb", "rgba")}
      animated={false}
    >
      <div
        style={{
          display: "flex",
          alignItems: "flex-start",
          justifyContent: "space-between",
        }}
      >
        {/* Icon */}
        <div
          style={{
            width: "48px",
            height: "48px",
            borderRadius: radius.md,
            background: `${metric.color}15`,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            color: metric.color,
          }}
        >
          {metric.icon}
        </div>

        {/* Trend Badge */}
        {metric.trend !== undefined && (
          <Badge
            variant={metric.trend >= 0 ? "success" : "danger"}
            size="xs"
            icon={
              <ArrowUpRight
                size={10}
                style={{
                  transform: metric.trend < 0 ? "rotate(180deg)" : "none",
                }}
              />
            }
          >
            {metric.trend > 0 ? "+" : ""}
            {metric.trend}%
          </Badge>
        )}
      </div>

      {/* Value */}
      <div
        style={{
          marginTop: spacing[4],
          ...textStyles.display.sm,
          color: colors.text.primary,
        }}
      >
        {metric.value}
      </div>

      {/* Label */}
      <div
        style={{
          marginTop: spacing[1],
          ...textStyles.body.sm,
          color: colors.text.tertiary,
        }}
      >
        {metric.label}
      </div>

      {/* Trend Label */}
      {metric.trendLabel && (
        <div
          style={{
            marginTop: spacing[2],
            ...textStyles.caption,
            color: colors.text.tertiary,
          }}
        >
          {metric.trendLabel}
        </div>
      )}
    </Card>
  </motion.div>
);

// Quick Action Card
const QuickActionCard: React.FC<{
  action: QuickAction;
  onClick: () => void;
}> = ({ action, onClick }) => (
  <motion.div
    variants={staggerItem}
    whileHover={{ ...hoverLift, scale: 1.02 }}
    whileTap={tapScale}
    onClick={onClick}
    style={{ cursor: "pointer" }}
  >
    <Card
      variant="surface"
      size="md"
      hover
      glow
      glowColor={action.color}
      animated={false}
    >
      <div style={{ display: "flex", alignItems: "center", gap: spacing[4] }}>
        {/* Icon */}
        <div
          style={{
            width: "44px",
            height: "44px",
            borderRadius: radius.md,
            background: `${action.color}15`,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            color: action.color,
            flexShrink: 0,
          }}
        >
          {action.icon}
        </div>

        {/* Content */}
        <div style={{ flex: 1, minWidth: 0 }}>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: spacing[2],
            }}
          >
            <span
              style={{
                ...textStyles.label.lg,
                color: colors.text.primary,
              }}
            >
              {action.label}
            </span>
            {action.badge && (
              <Badge variant="primary" size="xs" glow>
                {action.badge}
              </Badge>
            )}
          </div>
          <p
            style={{
              margin: `${spacing[1]} 0 0`,
              ...textStyles.body.sm,
              color: colors.text.tertiary,
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
            }}
          >
            {action.description}
          </p>
        </div>

        {/* Arrow */}
        <ChevronRight size={18} color={colors.text.tertiary} />
      </div>
    </Card>
  </motion.div>
);

// System Status Bar
const SystemStatusBar: React.FC = () => {
  const systems = [
    { name: "API", status: "online", latency: 42 },
    { name: "Database", status: "online", latency: 15 },
    { name: "AutoCAD", status: "online", latency: "Cloud" },
    { name: "CNC", status: "online", latency: 8 },
  ];

  return (
    <motion.div
      variants={fadeIn}
      style={{
        display: "flex",
        alignItems: "center",
        gap: spacing[4],
        padding: `${spacing[3]} ${spacing[4]}`,
        borderRadius: radius.md,
        background: colors.dark.surface,
        border: `1px solid ${colors.border.subtle}`,
        overflowX: "auto",
      }}
    >
      <Activity size={16} color={colors.success.DEFAULT} />
      <span style={{ ...textStyles.label.sm, color: colors.text.secondary }}>
        Status:
      </span>
      {systems.map((sys, i) => (
        <div
          key={i}
          style={{
            display: "flex",
            alignItems: "center",
            gap: spacing[2],
            padding: `${spacing[1]} ${spacing[2]}`,
            borderRadius: radius.sm,
            background: colors.success.soft,
          }}
        >
          <div
            style={{
              width: "6px",
              height: "6px",
              borderRadius: "50%",
              background: colors.success.DEFAULT,
              boxShadow: `0 0 6px ${colors.success.glow}`,
            }}
          />
          <span style={{ ...textStyles.caption, color: colors.text.secondary }}>
            {sys.name}
          </span>
          <span style={{ ...textStyles.caption, color: colors.text.tertiary }}>
            {typeof sys.latency === "number" ? `${sys.latency}ms` : sys.latency}
          </span>
        </div>
      ))}
    </motion.div>
  );
};

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// MAIN COMPONENT
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  const { theme } = useTheme();
  const { license } = useLicense();
  const isDemo = license.tier === "demo";

  // State
  const [stats, setStats] = useState<ProjectStats | null>(null);
  const [projects, setProjects] = useState<ProjectRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [showTour, setShowTour] = useState(() => {
    try {
      return !localStorage.getItem("engcad_tour_done");
    } catch {
      return false;
    }
  });

  // Fetch data
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
          setProjects(projData.projects.slice(0, 6));
        }
      } catch {
        // fallback
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    load();
    return () => {
      cancelled = true;
    };
  }, []);

  // Computed values
  const total = stats?.stats?.total_projects ?? 0;
  const completed = stats?.stats?.completed_projects ?? 0;
  const companies = stats?.stats?.top_companies ?? [];

  // KPI Metrics
  const kpiMetrics: KPIMetric[] = useMemo(
    () => [
      {
        id: "total",
        label: "Total Projetos",
        value: total,
        trend: total > 0 ? 12 : undefined,
        trendLabel: "vs mês anterior",
        icon: <Layers size={22} />,
        color: colors.primary.DEFAULT,
        onClick: () => navigate("/quality"),
      },
      {
        id: "completed",
        label: "Concluídos",
        value: completed,
        trend: completed > 0 ? 8 : undefined,
        icon: <CheckCircle2 size={22} />,
        color: colors.success.DEFAULT,
      },
      {
        id: "companies",
        label: "Empresas",
        value: companies.length,
        icon: <Target size={22} />,
        color: colors.warning.DEFAULT,
      },
      {
        id: "norms",
        label: "Normas Ativas",
        value: 3,
        icon: <FileText size={22} />,
        color: colors.secondary.DEFAULT,
      },
    ],
    [total, completed, companies, navigate],
  );

  // Quick Actions
  const quickActions: QuickAction[] = useMemo(
    () => [
      {
        id: "new-project",
        label: "Novo Projeto",
        description: "Criar um novo projeto de engenharia",
        icon: <Plus size={20} />,
        color: colors.primary.DEFAULT,
        path: "/autopilot",
      },
      {
        id: "cnc",
        label: "Controle CNC",
        description: "Gerar G-code para corte plasma",
        icon: <Flame size={20} />,
        color: colors.warning.DEFAULT,
        path: "/cnc-control",
        badge: 2,
      },
      {
        id: "cad",
        label: "CAD Dashboard",
        description: "Visualizar e editar desenhos",
        icon: <Layers size={20} />,
        color: colors.success.DEFAULT,
        path: "/cad-dashboard",
      },
      {
        id: "analytics",
        label: "Analytics",
        description: "Ver métricas e relatórios",
        icon: <TrendingUp size={20} />,
        color: colors.secondary.DEFAULT,
        path: "/analytics",
      },
    ],
    [],
  );

  // Bottom Tab Bar items
  const tabItems: TabItem[] = useMemo(
    () => [
      {
        id: "dashboard",
        icon: <LayoutDashboard size={22} />,
        label: "Dashboard",
        path: "/dashboard",
      },
      {
        id: "cad",
        icon: <Layers size={22} />,
        label: "CAD",
        path: "/cad-dashboard",
      },
      {
        id: "chat",
        icon: <MessageSquare size={22} />,
        label: "Chat",
        path: "/chatcad",
      },
      {
        id: "profile",
        icon: <User size={22} />,
        label: "Perfil",
        path: "/profile",
      },
    ],
    [],
  );

  // Page styles
  const pageStyles: React.CSSProperties = {
    minHeight: "100vh",
    background: colors.dark.base,
    color: colors.text.primary,
  };

  const mainStyles: React.CSSProperties = {
    maxWidth: "1400px",
    margin: "0 auto",
    padding: spacing[6],
    paddingBottom: spacing[20], // Space for bottom tab bar
  };

  const sectionTitleStyles: React.CSSProperties = {
    display: "flex",
    alignItems: "center",
    gap: spacing[2],
    marginBottom: spacing[4],
    ...textStyles.heading.h3,
    color: colors.text.primary,
  };

  const gridStyles: React.CSSProperties = {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
    gap: spacing[4],
  };

  return (
    <div style={pageStyles}>
      <OnboardingTour
        steps={DEFAULT_TOUR_STEPS}
        active={showTour}
        onFinish={() => setShowTour(false)}
      />
      <motion.main
        style={mainStyles}
        variants={staggerContainer}
        initial="hidden"
        animate="visible"
      >
        {/* Header */}
        <motion.header
          variants={fadeIn}
          style={{
            display: "flex",
            justifyContent: "flex-end",
            alignItems: "center",
            marginBottom: spacing[6],
            gap: spacing[3],
          }}
        >
          <AutoCADConnectButton />
          <Button variant="ghost" size="sm" leftIcon={<Bell size={18} />}>
            <Badge
              variant="danger"
              dot
              style={{ position: "absolute", top: 8, right: 8 }}
            />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            leftIcon={<Settings size={18} />}
            onClick={() => navigate("/settings")}
          />
        </motion.header>

        {/* Hero Section */}
        <HeroSection
          userName="Operador"
          isDemo={isDemo}
          onNewProject={() => navigate("/autopilot")}
          onUpgrade={() => navigate("/pricing")}
        />

        {/* System Status */}
        <motion.div variants={staggerItem} style={{ marginBottom: spacing[8] }}>
          <SystemStatusBar />
        </motion.div>

        {/* KPI Metrics */}
        <motion.section
          variants={staggerItem}
          style={{ marginBottom: spacing[8] }}
        >
          <h2 style={sectionTitleStyles}>
            <TrendingUp size={20} color={colors.primary.DEFAULT} />
            Métricas
          </h2>
          <motion.div
            variants={staggerContainer}
            initial="hidden"
            animate="visible"
            style={gridStyles}
          >
            {kpiMetrics.map((metric, index) => (
              <KPICard key={metric.id} metric={metric} index={index} />
            ))}
          </motion.div>
        </motion.section>

        {/* Quick Actions */}
        <motion.section
          variants={staggerItem}
          style={{ marginBottom: spacing[8] }}
        >
          <h2 style={sectionTitleStyles}>
            <Zap size={20} color={colors.warning.DEFAULT} />
            Ações Rápidas
          </h2>
          <motion.div
            variants={staggerContainer}
            initial="hidden"
            animate="visible"
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
              gap: spacing[4],
            }}
          >
            {quickActions.map((action) => (
              <QuickActionCard
                key={action.id}
                action={action}
                onClick={() => navigate(action.path)}
              />
            ))}
          </motion.div>
        </motion.section>

        {/* Recent Projects */}
        {projects.length > 0 && (
          <motion.section variants={staggerItem}>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                marginBottom: spacing[4],
              }}
            >
              <h2 style={sectionTitleStyles}>
                <Clock size={20} color={colors.secondary.DEFAULT} />
                Projetos Recentes
              </h2>
              <Button
                variant="ghost"
                size="sm"
                rightIcon={<ChevronRight size={16} />}
                onClick={() => navigate("/quality")}
              >
                Ver todos
              </Button>
            </div>
            <motion.div
              variants={staggerContainer}
              initial="hidden"
              animate="visible"
              style={gridStyles}
            >
              {projects.slice(0, 4).map((project, index) => (
                <motion.div key={project.project_id} variants={staggerItem}>
                  <Card variant="surface" size="md" hover animated={false}>
                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: spacing[3],
                      }}
                    >
                      <div
                        style={{
                          width: "40px",
                          height: "40px",
                          borderRadius: radius.md,
                          background: colors.primary.soft,
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                        }}
                      >
                        <FileText size={18} color={colors.primary.DEFAULT} />
                      </div>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div
                          style={{
                            ...textStyles.label.md,
                            color: colors.text.primary,
                          }}
                        >
                          {project.company || "Projeto"}
                        </div>
                        <div
                          style={{
                            ...textStyles.caption,
                            color: colors.text.tertiary,
                          }}
                        >
                          {project.pipe_spec || "Sem especificação"}
                        </div>
                      </div>
                      <Badge
                        variant={
                          project.status === "completed" ? "success" : "default"
                        }
                        size="xs"
                      >
                        {project.status === "completed"
                          ? "Concluído"
                          : "Em andamento"}
                      </Badge>
                    </div>
                  </Card>
                </motion.div>
              ))}
            </motion.div>
          </motion.section>
        )}
      </motion.main>

      {/* Bottom Tab Bar (mobile only) */}
      <BottomTabBar items={tabItems} />

      {/* Global responsive styles */}
      <style>{`
        @media (max-width: ${breakpoints.md}px) {
          .dashboard-grid {
            grid-template-columns: 1fr !important;
          }
        }
      `}</style>
    </div>
  );
};

export default Dashboard;
