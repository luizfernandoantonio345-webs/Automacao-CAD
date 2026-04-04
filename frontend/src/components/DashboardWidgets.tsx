/**
 * ═══════════════════════════════════════════════════════════════════════════════
 * DashboardWidgets - Componentes visuais avançados para o Dashboard
 * ═══════════════════════════════════════════════════════════════════════════════
 */

import React, { useEffect, useState, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  TrendingUp,
  TrendingDown,
  Activity,
  Clock,
  CheckCircle,
  AlertTriangle,
  XCircle,
  ArrowRight,
  Zap,
  Layers,
  Settings,
  Database,
  Cpu,
  HardDrive,
  Wifi,
  Server,
  FileText,
  Upload,
  Download,
  Play,
  Pause,
  RefreshCw,
  Eye,
  Edit3,
  Trash2,
  MoreHorizontal,
  Calendar,
  User,
  Box,
  Target,
  Award,
  Flame,
  Ruler,
} from "lucide-react";

// ═══════════════════════════════════════════════════════════════════════════════
// Types
// ═══════════════════════════════════════════════════════════════════════════════

interface Theme {
  surface: string;
  panel: string;
  border: string;
  accentPrimary: string;
  success: string;
  warning: string;
  danger: string;
  textPrimary: string;
  textSecondary: string;
  textTertiary: string;
  inputBackground: string;
  background: string;
}

interface ActivityItem {
  id: string;
  type: "project" | "export" | "cnc" | "validation" | "system";
  action: string;
  description: string;
  timestamp: Date;
  user?: string;
  status?: "success" | "warning" | "error" | "pending";
}

interface QuickAction {
  id: string;
  label: string;
  description: string;
  icon: React.ReactNode;
  color: string;
  onClick: () => void;
  badge?: number;
}

interface SystemStatus {
  name: string;
  status: "online" | "warning" | "offline";
  latency?: number;
  message?: string;
}

// ═══════════════════════════════════════════════════════════════════════════════
// WelcomeHero - Seção de boas-vindas com hora e clima
// ═══════════════════════════════════════════════════════════════════════════════

export const WelcomeHero: React.FC<{
  userName?: string;
  theme: Theme;
}> = ({ userName = "Operador", theme }) => {
  const [time, setTime] = useState(new Date());

  useEffect(() => {
    const timer = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  const getGreeting = () => {
    const hour = time.getHours();
    if (hour < 12) return "Bom dia";
    if (hour < 18) return "Boa tarde";
    return "Boa noite";
  };

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString("pt-BR", {
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const formatDate = (date: Date) => {
    return date.toLocaleDateString("pt-BR", {
      weekday: "long",
      day: "numeric",
      month: "long",
    });
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      style={{
        padding: "24px 32px",
        background: `linear-gradient(135deg, ${theme.accentPrimary}15, ${theme.panel})`,
        borderRadius: 16,
        border: `1px solid ${theme.accentPrimary}30`,
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        marginBottom: 24,
      }}
    >
      <div>
        <motion.h1
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.1 }}
          style={{
            fontSize: 28,
            fontWeight: 700,
            color: theme.textPrimary,
            margin: 0,
            marginBottom: 8,
          }}
        >
          {getGreeting()},{" "}
          <span style={{ color: theme.accentPrimary }}>{userName}</span>! 👋
        </motion.h1>
        <p style={{ fontSize: 14, color: theme.textSecondary, margin: 0 }}>
          {formatDate(time)} • Sistema pronto para operação
        </p>
      </div>

      <div style={{ textAlign: "right" }}>
        <div
          style={{
            fontSize: 36,
            fontWeight: 700,
            color: theme.accentPrimary,
            fontFamily: "monospace",
            letterSpacing: 2,
          }}
        >
          {formatTime(time)}
        </div>
        <div style={{ fontSize: 12, color: theme.textTertiary }}>
          Horário de Brasília
        </div>
      </div>
    </motion.div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// ProgressRing - Gráfico circular de progresso
// ═══════════════════════════════════════════════════════════════════════════════

export const ProgressRing: React.FC<{
  value: number;
  max: number;
  size?: number;
  strokeWidth?: number;
  color: string;
  label: string;
  theme: Theme;
}> = ({ value, max, size = 120, strokeWidth = 10, color, label, theme }) => {
  const radius = (size - strokeWidth) / 2;
  const circumference = radius * 2 * Math.PI;
  const percent = max > 0 ? (value / max) * 100 : 0;
  const offset = circumference - (percent / 100) * circumference;

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: 8,
      }}
    >
      <div style={{ position: "relative", width: size, height: size }}>
        <svg width={size} height={size}>
          {/* Background circle */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke={theme.border}
            strokeWidth={strokeWidth}
          />
          {/* Progress circle */}
          <motion.circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke={color}
            strokeWidth={strokeWidth}
            strokeLinecap="round"
            strokeDasharray={circumference}
            initial={{ strokeDashoffset: circumference }}
            animate={{ strokeDashoffset: offset }}
            transition={{ duration: 1, ease: "easeOut" }}
            style={{
              transform: "rotate(-90deg)",
              transformOrigin: "50% 50%",
            }}
          />
        </svg>
        <div
          style={{
            position: "absolute",
            top: "50%",
            left: "50%",
            transform: "translate(-50%, -50%)",
            textAlign: "center",
          }}
        >
          <div style={{ fontSize: 24, fontWeight: 700, color }}>
            {Math.round(percent)}%
          </div>
          <div style={{ fontSize: 10, color: theme.textTertiary }}>
            {value}/{max}
          </div>
        </div>
      </div>
      <div
        style={{ fontSize: 12, fontWeight: 600, color: theme.textSecondary }}
      >
        {label}
      </div>
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// MetricCardAdvanced - Card de métrica com tendência
// ═══════════════════════════════════════════════════════════════════════════════

export const MetricCardAdvanced: React.FC<{
  icon: React.ReactNode;
  label: string;
  value: number | string;
  trend?: number;
  trendLabel?: string;
  color: string;
  theme: Theme;
  onClick?: () => void;
}> = ({ icon, label, value, trend, trendLabel, color, theme, onClick }) => {
  const isPositive = trend && trend > 0;
  const isNegative = trend && trend < 0;

  return (
    <motion.div
      whileHover={{ scale: 1.02, y: -4 }}
      whileTap={{ scale: 0.98 }}
      onClick={onClick}
      style={{
        backgroundColor: theme.surface,
        border: `1px solid ${theme.border}`,
        borderRadius: 16,
        padding: 20,
        cursor: onClick ? "pointer" : "default",
        position: "relative",
        overflow: "hidden",
      }}
    >
      {/* Accent bar */}
      <div
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          width: "100%",
          height: 3,
          background: `linear-gradient(90deg, ${color}, ${color}80)`,
        }}
      />

      <div
        style={{
          display: "flex",
          alignItems: "flex-start",
          justifyContent: "space-between",
        }}
      >
        <div
          style={{
            width: 44,
            height: 44,
            borderRadius: 12,
            backgroundColor: `${color}15`,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            color: color,
          }}
        >
          {icon}
        </div>

        {trend !== undefined && (
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 4,
              padding: "4px 8px",
              borderRadius: 8,
              backgroundColor: isPositive
                ? `${theme.success}15`
                : isNegative
                  ? `${theme.danger}15`
                  : `${theme.border}`,
              color: isPositive
                ? theme.success
                : isNegative
                  ? theme.danger
                  : theme.textSecondary,
              fontSize: 11,
              fontWeight: 600,
            }}
          >
            {isPositive ? (
              <TrendingUp size={12} />
            ) : isNegative ? (
              <TrendingDown size={12} />
            ) : null}
            {Math.abs(trend)}%
          </div>
        )}
      </div>

      <div style={{ marginTop: 16 }}>
        <div
          style={{
            fontSize: 28,
            fontWeight: 700,
            color: theme.textPrimary,
            lineHeight: 1,
          }}
        >
          {value}
        </div>
        <div
          style={{
            fontSize: 13,
            color: theme.textSecondary,
            marginTop: 4,
          }}
        >
          {label}
        </div>
        {trendLabel && (
          <div
            style={{ fontSize: 11, color: theme.textTertiary, marginTop: 2 }}
          >
            {trendLabel}
          </div>
        )}
      </div>
    </motion.div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// QuickActionCard - Card de ação rápida
// ═══════════════════════════════════════════════════════════════════════════════

export const QuickActionCard: React.FC<{
  action: QuickAction;
  theme: Theme;
}> = ({ action, theme }) => (
  <motion.button
    whileHover={{ scale: 1.02, backgroundColor: `${action.color}10` }}
    whileTap={{ scale: 0.98 }}
    onClick={action.onClick}
    style={{
      backgroundColor: theme.surface,
      border: `1px solid ${theme.border}`,
      borderRadius: 12,
      padding: "16px 20px",
      cursor: "pointer",
      display: "flex",
      alignItems: "center",
      gap: 16,
      width: "100%",
      textAlign: "left",
      position: "relative",
    }}
  >
    <div
      style={{
        width: 48,
        height: 48,
        borderRadius: 12,
        backgroundColor: `${action.color}15`,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        color: action.color,
        flexShrink: 0,
      }}
    >
      {action.icon}
    </div>

    <div style={{ flex: 1 }}>
      <div
        style={{
          fontSize: 14,
          fontWeight: 600,
          color: theme.textPrimary,
          marginBottom: 2,
        }}
      >
        {action.label}
      </div>
      <div style={{ fontSize: 12, color: theme.textSecondary }}>
        {action.description}
      </div>
    </div>

    {action.badge !== undefined && action.badge > 0 && (
      <div
        style={{
          minWidth: 24,
          height: 24,
          borderRadius: 12,
          backgroundColor: theme.danger,
          color: "#fff",
          fontSize: 11,
          fontWeight: 700,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          padding: "0 8px",
        }}
      >
        {action.badge}
      </div>
    )}

    <ArrowRight size={18} color={theme.textTertiary} />
  </motion.button>
);

// ═══════════════════════════════════════════════════════════════════════════════
// ActivityTimeline - Timeline de atividades recentes
// ═══════════════════════════════════════════════════════════════════════════════

export const ActivityTimeline: React.FC<{
  activities: ActivityItem[];
  maxItems?: number;
  theme: Theme;
}> = ({ activities, maxItems = 5, theme }) => {
  const getIcon = (type: ActivityItem["type"]) => {
    switch (type) {
      case "project":
        return <FileText size={14} />;
      case "export":
        return <Download size={14} />;
      case "cnc":
        return <Flame size={14} />;
      case "validation":
        return <CheckCircle size={14} />;
      case "system":
        return <Settings size={14} />;
      default:
        return <Activity size={14} />;
    }
  };

  const getStatusColor = (status?: string) => {
    switch (status) {
      case "success":
        return theme.success;
      case "warning":
        return theme.warning;
      case "error":
        return theme.danger;
      default:
        return theme.accentPrimary;
    }
  };

  const formatTime = (date: Date) => {
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);

    if (minutes < 1) return "Agora";
    if (minutes < 60) return `${minutes}min atrás`;
    if (hours < 24) return `${hours}h atrás`;
    return date.toLocaleDateString("pt-BR");
  };

  return (
    <div
      style={{
        backgroundColor: theme.surface,
        border: `1px solid ${theme.border}`,
        borderRadius: 16,
        padding: 20,
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
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
          <Activity size={18} color={theme.accentPrimary} />
          Atividade Recente
        </h3>
        <span style={{ fontSize: 11, color: theme.textTertiary }}>
          Últimas {maxItems} ações
        </span>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
        {activities.slice(0, maxItems).map((activity, idx) => (
          <motion.div
            key={activity.id}
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: idx * 0.05 }}
            style={{
              display: "flex",
              alignItems: "flex-start",
              gap: 12,
              padding: "12px 0",
              borderBottom:
                idx < activities.length - 1
                  ? `1px solid ${theme.border}`
                  : "none",
            }}
          >
            <div
              style={{
                width: 28,
                height: 28,
                borderRadius: 8,
                backgroundColor: `${getStatusColor(activity.status)}15`,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: getStatusColor(activity.status),
                flexShrink: 0,
              }}
            >
              {getIcon(activity.type)}
            </div>

            <div style={{ flex: 1, minWidth: 0 }}>
              <div
                style={{
                  fontSize: 13,
                  fontWeight: 500,
                  color: theme.textPrimary,
                  marginBottom: 2,
                }}
              >
                {activity.action}
              </div>
              <div
                style={{
                  fontSize: 12,
                  color: theme.textSecondary,
                  whiteSpace: "nowrap",
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                }}
              >
                {activity.description}
              </div>
            </div>

            <div
              style={{
                fontSize: 11,
                color: theme.textTertiary,
                whiteSpace: "nowrap",
              }}
            >
              {formatTime(activity.timestamp)}
            </div>
          </motion.div>
        ))}

        {activities.length === 0 && (
          <div
            style={{
              padding: 24,
              textAlign: "center",
              color: theme.textTertiary,
              fontSize: 13,
            }}
          >
            Nenhuma atividade recente
          </div>
        )}
      </div>
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// SystemHealthBar - Barra de status do sistema
// ═══════════════════════════════════════════════════════════════════════════════

export const SystemHealthBar: React.FC<{
  systems: SystemStatus[];
  theme: Theme;
}> = ({ systems, theme }) => {
  const getStatusIcon = (status: SystemStatus["status"]) => {
    switch (status) {
      case "online":
        return <CheckCircle size={14} />;
      case "warning":
        return <AlertTriangle size={14} />;
      case "offline":
        return <XCircle size={14} />;
    }
  };

  const getStatusColor = (status: SystemStatus["status"]) => {
    switch (status) {
      case "online":
        return theme.success;
      case "warning":
        return theme.warning;
      case "offline":
        return theme.danger;
    }
  };

  return (
    <div
      style={{
        display: "flex",
        gap: 12,
        padding: "12px 16px",
        backgroundColor: theme.surface,
        border: `1px solid ${theme.border}`,
        borderRadius: 12,
        overflowX: "auto",
      }}
    >
      {systems.map((system, idx) => (
        <motion.div
          key={system.name}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: idx * 0.1 }}
          style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
            padding: "8px 12px",
            backgroundColor: `${getStatusColor(system.status)}10`,
            borderRadius: 8,
            whiteSpace: "nowrap",
          }}
        >
          <div style={{ color: getStatusColor(system.status) }}>
            {getStatusIcon(system.status)}
          </div>
          <div>
            <div
              style={{
                fontSize: 12,
                fontWeight: 600,
                color: theme.textPrimary,
              }}
            >
              {system.name}
            </div>
            {system.latency !== undefined && (
              <div style={{ fontSize: 10, color: theme.textTertiary }}>
                {system.latency}ms
              </div>
            )}
          </div>
        </motion.div>
      ))}
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// MiniChart - Gráfico de barras simples
// ═══════════════════════════════════════════════════════════════════════════════

export const MiniBarChart: React.FC<{
  data: number[];
  labels?: string[];
  color: string;
  height?: number;
  theme: Theme;
}> = ({ data, labels, color, height = 80, theme }) => {
  const max = Math.max(...data, 1);

  return (
    <div style={{ display: "flex", alignItems: "flex-end", gap: 4, height }}>
      {data.map((value, idx) => (
        <div
          key={idx}
          style={{
            flex: 1,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: 4,
          }}
        >
          <motion.div
            initial={{ height: 0 }}
            animate={{ height: `${(value / max) * 100}%` }}
            transition={{ delay: idx * 0.05, duration: 0.5 }}
            style={{
              width: "100%",
              backgroundColor: color,
              borderRadius: 4,
              minHeight: 4,
            }}
          />
          {labels && labels[idx] && (
            <span style={{ fontSize: 9, color: theme.textTertiary }}>
              {labels[idx]}
            </span>
          )}
        </div>
      ))}
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// ProjectCard - Card de projeto individual
// ═══════════════════════════════════════════════════════════════════════════════

export const ProjectCard: React.FC<{
  project: {
    id: number | string;
    code: string;
    company: string;
    diameter: number;
    length: number;
    status: string;
    progress?: number;
    updatedAt?: Date;
  };
  onClick?: () => void;
  theme: Theme;
}> = ({ project, onClick, theme }) => {
  const statusColors: Record<string, string> = {
    completed: theme.success,
    processing: theme.accentPrimary,
    pending: theme.warning,
    error: theme.danger,
  };

  const statusLabels: Record<string, string> = {
    completed: "Concluído",
    processing: "Processando",
    pending: "Pendente",
    error: "Erro",
  };

  const color = statusColors[project.status] || theme.textTertiary;

  return (
    <motion.div
      whileHover={{ scale: 1.01, backgroundColor: `${theme.accentPrimary}08` }}
      onClick={onClick}
      style={{
        padding: 16,
        backgroundColor: theme.surface,
        border: `1px solid ${theme.border}`,
        borderRadius: 12,
        cursor: onClick ? "pointer" : "default",
        display: "flex",
        alignItems: "center",
        gap: 16,
      }}
    >
      <div
        style={{
          width: 40,
          height: 40,
          borderRadius: 10,
          backgroundColor: `${color}15`,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          color: color,
        }}
      >
        <Box size={18} />
      </div>

      <div style={{ flex: 1, minWidth: 0 }}>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
            marginBottom: 4,
          }}
        >
          <span
            style={{
              fontSize: 14,
              fontWeight: 600,
              color: theme.textPrimary,
            }}
          >
            {project.code}
          </span>
          <span
            style={{
              fontSize: 11,
              padding: "2px 8px",
              borderRadius: 6,
              backgroundColor: `${color}15`,
              color: color,
              fontWeight: 600,
            }}
          >
            {statusLabels[project.status] || project.status}
          </span>
        </div>
        <div style={{ fontSize: 12, color: theme.textSecondary }}>
          {project.company} • Ø{project.diameter}mm × {project.length}mm
        </div>
      </div>

      {project.progress !== undefined && (
        <div style={{ width: 60 }}>
          <div
            style={{
              height: 4,
              backgroundColor: theme.border,
              borderRadius: 2,
              overflow: "hidden",
            }}
          >
            <div
              style={{
                width: `${project.progress}%`,
                height: "100%",
                backgroundColor: color,
                borderRadius: 2,
              }}
            />
          </div>
          <div
            style={{
              fontSize: 10,
              color: theme.textTertiary,
              textAlign: "center",
              marginTop: 4,
            }}
          >
            {project.progress}%
          </div>
        </div>
      )}

      <ArrowRight size={16} color={theme.textTertiary} />
    </motion.div>
  );
};

export default {
  WelcomeHero,
  ProgressRing,
  MetricCardAdvanced,
  QuickActionCard,
  ActivityTimeline,
  SystemHealthBar,
  MiniBarChart,
  ProjectCard,
};
