/**
 * ═══════════════════════════════════════════════════════════════════════════════
 * CncConsumablesMonitor - Monitor de Consumíveis em Tempo Real
 * ═══════════════════════════════════════════════════════════════════════════════
 *
 * Melhoria #4: Monitoramento visual de consumíveis plasma
 * - Status de bico, eletrodo, protetor
 * - Vida útil estimada vs real
 * - Alertas de troca
 * - Histórico de consumo
 */

import React, { useState, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Zap,
  Circle,
  Shield,
  AlertTriangle,
  CheckCircle,
  Clock,
  TrendingDown,
  TrendingUp,
  RefreshCw,
  Settings,
  History,
  Bell,
  BellOff,
  ChevronRight,
  Package,
  DollarSign,
  BarChart2,
  Flame,
} from "lucide-react";

interface Consumable {
  id: string;
  type: "electrode" | "nozzle" | "shield" | "swirl_ring" | "retaining_cap";
  name: string;
  brand?: string;
  partNumber?: string;
  installedAt: string;
  expectedLifeHours: number;
  usedHours: number;
  pierceCount: number;
  maxPierces: number;
  status: "good" | "warning" | "critical" | "replace";
  currentAmperage: number;
  maxAmperage: number;
  cost: number;
}

interface ConsumptionHistory {
  date: string;
  consumableType: string;
  usedHours: number;
  pierceCount: number;
  reason: string;
}

interface CncConsumablesMonitorProps {
  machineId: string;
  theme: {
    surface: string;
    surfaceAlt: string;
    border: string;
    accentPrimary: string;
    success: string;
    warning: string;
    danger: string;
    textPrimary: string;
    textSecondary: string;
  };
  onReplaceConsumable?: (consumable: Consumable) => void;
}

// Mock data
const mockConsumables: Consumable[] = [
  {
    id: "cons-001",
    type: "electrode",
    name: "Eletrodo HFC",
    brand: "Hypertherm",
    partNumber: "220842",
    installedAt: "2025-01-10T08:00:00",
    expectedLifeHours: 4,
    usedHours: 3.2,
    pierceCount: 1850,
    maxPierces: 2000,
    status: "warning",
    currentAmperage: 105,
    maxAmperage: 130,
    cost: 45.0,
  },
  {
    id: "cons-002",
    type: "nozzle",
    name: "Bico 105A",
    brand: "Hypertherm",
    partNumber: "220819",
    installedAt: "2025-01-12T14:30:00",
    expectedLifeHours: 3,
    usedHours: 1.5,
    pierceCount: 920,
    maxPierces: 1500,
    status: "good",
    currentAmperage: 105,
    maxAmperage: 105,
    cost: 35.0,
  },
  {
    id: "cons-003",
    type: "shield",
    name: "Protetor de Respingos",
    brand: "Hypertherm",
    partNumber: "220817",
    installedAt: "2025-01-08T10:00:00",
    expectedLifeHours: 8,
    usedHours: 6.8,
    pierceCount: 3500,
    maxPierces: 4000,
    status: "warning",
    currentAmperage: 105,
    maxAmperage: 130,
    cost: 25.0,
  },
  {
    id: "cons-004",
    type: "swirl_ring",
    name: "Anel Difusor",
    brand: "Hypertherm",
    partNumber: "220857",
    installedAt: "2025-01-01T08:00:00",
    expectedLifeHours: 40,
    usedHours: 18.5,
    pierceCount: 12000,
    maxPierces: 20000,
    status: "good",
    currentAmperage: 105,
    maxAmperage: 130,
    cost: 55.0,
  },
  {
    id: "cons-005",
    type: "retaining_cap",
    name: "Tampa de Retenção",
    brand: "Hypertherm",
    partNumber: "220854",
    installedAt: "2024-12-15T08:00:00",
    expectedLifeHours: 100,
    usedHours: 45.2,
    pierceCount: 28000,
    maxPierces: 50000,
    status: "good",
    currentAmperage: 105,
    maxAmperage: 130,
    cost: 85.0,
  },
];

const mockHistory: ConsumptionHistory[] = [
  {
    date: "2025-01-14",
    consumableType: "electrode",
    usedHours: 3.8,
    pierceCount: 2100,
    reason: "Desgaste normal",
  },
  {
    date: "2025-01-14",
    consumableType: "nozzle",
    usedHours: 2.9,
    pierceCount: 1480,
    reason: "Desgaste normal",
  },
  {
    date: "2025-01-12",
    consumableType: "electrode",
    usedHours: 4.1,
    pierceCount: 2250,
    reason: "Desgaste normal",
  },
  {
    date: "2025-01-10",
    consumableType: "shield",
    usedHours: 7.5,
    pierceCount: 3800,
    reason: "Respingos excessivos",
  },
];

const CncConsumablesMonitor: React.FC<CncConsumablesMonitorProps> = ({
  machineId,
  theme,
  onReplaceConsumable,
}) => {
  const [consumables, setConsumables] = useState<Consumable[]>(mockConsumables);
  const [history, setHistory] = useState<ConsumptionHistory[]>(mockHistory);
  const [selectedConsumable, setSelectedConsumable] =
    useState<Consumable | null>(null);
  const [alertsEnabled, setAlertsEnabled] = useState(true);
  const [showHistory, setShowHistory] = useState(false);
  const [loading, setLoading] = useState(false);

  // Simulated real-time updates
  useEffect(() => {
    const interval = setInterval(() => {
      setConsumables((prev) =>
        prev.map((c) => ({
          ...c,
          usedHours: c.usedHours + 0.001,
          pierceCount: c.pierceCount + Math.floor(Math.random() * 2),
          status: getStatus(
            c.usedHours + 0.001,
            c.expectedLifeHours,
            c.pierceCount + 1,
            c.maxPierces,
          ),
        })),
      );
    }, 5000);

    return () => clearInterval(interval);
  }, []);

  const getStatus = (
    usedHours: number,
    expectedHours: number,
    pierceCount: number,
    maxPierces: number,
  ): Consumable["status"] => {
    const lifePercent = Math.max(
      (usedHours / expectedHours) * 100,
      (pierceCount / maxPierces) * 100,
    );
    if (lifePercent >= 95) return "replace";
    if (lifePercent >= 80) return "critical";
    if (lifePercent >= 60) return "warning";
    return "good";
  };

  const getStatusConfig = (status: Consumable["status"]) => {
    switch (status) {
      case "good":
        return { color: theme.success, label: "Bom", icon: CheckCircle };
      case "warning":
        return { color: theme.warning, label: "Atenção", icon: AlertTriangle };
      case "critical":
        return { color: "#FF6B35", label: "Crítico", icon: AlertTriangle };
      case "replace":
        return {
          color: theme.danger,
          label: "Substituir",
          icon: AlertTriangle,
        };
      default:
        return { color: theme.textSecondary, label: status, icon: Circle };
    }
  };

  const getTypeIcon = (type: Consumable["type"]) => {
    switch (type) {
      case "electrode":
        return Zap;
      case "nozzle":
        return Flame;
      case "shield":
        return Shield;
      case "swirl_ring":
        return Circle;
      case "retaining_cap":
        return Package;
      default:
        return Circle;
    }
  };

  const getTypeLabel = (type: Consumable["type"]) => {
    switch (type) {
      case "electrode":
        return "Eletrodo";
      case "nozzle":
        return "Bico";
      case "shield":
        return "Protetor";
      case "swirl_ring":
        return "Difusor";
      case "retaining_cap":
        return "Tampa";
      default:
        return type;
    }
  };

  const getLifePercentage = (c: Consumable) => {
    const hourPercent = (c.usedHours / c.expectedLifeHours) * 100;
    const piercePercent = (c.pierceCount / c.maxPierces) * 100;
    return Math.min(100, Math.max(hourPercent, piercePercent));
  };

  const getRemainingLife = (c: Consumable) => {
    const hourRemaining = c.expectedLifeHours - c.usedHours;
    const pierceRemaining = c.maxPierces - c.pierceCount;
    return {
      hours: Math.max(0, hourRemaining).toFixed(1),
      pierces: Math.max(0, pierceRemaining),
    };
  };

  const totalCost = consumables.reduce((sum, c) => sum + c.cost, 0);
  const criticalCount = consumables.filter(
    (c) => c.status === "critical" || c.status === "replace",
  ).length;
  const warningCount = consumables.filter((c) => c.status === "warning").length;

  const refreshData = async () => {
    setLoading(true);
    await new Promise((r) => setTimeout(r, 500));
    setLoading(false);
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      style={{ display: "flex", flexDirection: "column", gap: 20 }}
    >
      {/* Header */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <Package size={24} color={theme.accentPrimary} />
          <h2 style={{ margin: 0, color: theme.textPrimary, fontSize: 20 }}>
            Monitor de Consumíveis
          </h2>
          <span
            style={{
              padding: "4px 8px",
              borderRadius: 4,
              background: theme.surfaceAlt,
              color: theme.textSecondary,
              fontSize: 12,
            }}
          >
            Máquina: {machineId}
          </span>
        </div>

        <div style={{ display: "flex", gap: 8 }}>
          <button
            onClick={() => setShowHistory(!showHistory)}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              padding: "8px 16px",
              borderRadius: 6,
              border: `1px solid ${showHistory ? theme.accentPrimary : theme.border}`,
              background: showHistory
                ? `${theme.accentPrimary}20`
                : "transparent",
              color: showHistory ? theme.accentPrimary : theme.textSecondary,
              cursor: "pointer",
              fontSize: 13,
            }}
          >
            <History size={16} />
            Histórico
          </button>

          <button
            onClick={() => setAlertsEnabled(!alertsEnabled)}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              padding: "8px 16px",
              borderRadius: 6,
              border: `1px solid ${theme.border}`,
              background: "transparent",
              color: alertsEnabled ? theme.warning : theme.textSecondary,
              cursor: "pointer",
              fontSize: 13,
            }}
          >
            {alertsEnabled ? <Bell size={16} /> : <BellOff size={16} />}
            Alertas
          </button>

          <button
            onClick={refreshData}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              padding: "8px 16px",
              borderRadius: 6,
              border: `1px solid ${theme.border}`,
              background: "transparent",
              color: theme.textSecondary,
              cursor: "pointer",
              fontSize: 13,
            }}
          >
            <RefreshCw size={16} className={loading ? "spinning" : ""} />
            Atualizar
          </button>
        </div>
      </div>

      {/* Summary Cards */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(4, 1fr)",
          gap: 12,
        }}
      >
        <SummaryCard
          icon={<Package size={18} />}
          label="Total Consumíveis"
          value={consumables.length.toString()}
          theme={theme}
        />
        <SummaryCard
          icon={<AlertTriangle size={18} />}
          label="Críticos"
          value={criticalCount.toString()}
          color={criticalCount > 0 ? theme.danger : theme.success}
          theme={theme}
        />
        <SummaryCard
          icon={<Clock size={18} />}
          label="Atenção"
          value={warningCount.toString()}
          color={warningCount > 0 ? theme.warning : theme.success}
          theme={theme}
        />
        <SummaryCard
          icon={<DollarSign size={18} />}
          label="Custo Instalado"
          value={`R$ ${totalCost.toFixed(2)}`}
          theme={theme}
        />
      </div>

      {/* Alerts Banner */}
      {alertsEnabled && (criticalCount > 0 || warningCount > 0) && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          style={{
            padding: 16,
            background:
              criticalCount > 0 ? `${theme.danger}15` : `${theme.warning}15`,
            border: `1px solid ${criticalCount > 0 ? theme.danger : theme.warning}`,
            borderRadius: 8,
            display: "flex",
            alignItems: "center",
            gap: 12,
          }}
        >
          <AlertTriangle
            size={20}
            color={criticalCount > 0 ? theme.danger : theme.warning}
          />
          <span style={{ color: theme.textPrimary, flex: 1 }}>
            {criticalCount > 0 ? (
              <>
                <strong>
                  {criticalCount} consumível(is) precisa(m) de substituição
                  imediata!
                </strong>
              </>
            ) : (
              <>
                <strong>
                  {warningCount} consumível(is) com vida útil acima de 60%.
                </strong>{" "}
                Providencie reposição.
              </>
            )}
          </span>
          <button
            onClick={() => setAlertsEnabled(false)}
            style={{
              padding: "6px 12px",
              borderRadius: 4,
              border: "none",
              background: "rgba(255,255,255,0.2)",
              color: theme.textPrimary,
              cursor: "pointer",
              fontSize: 12,
            }}
          >
            Dispensar
          </button>
        </motion.div>
      )}

      {/* Consumables Grid */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))",
          gap: 12,
        }}
      >
        {consumables.map((consumable) => {
          const statusConfig = getStatusConfig(consumable.status);
          const StatusIcon = statusConfig.icon;
          const TypeIcon = getTypeIcon(consumable.type);
          const lifePercent = getLifePercentage(consumable);
          const remaining = getRemainingLife(consumable);

          return (
            <motion.div
              key={consumable.id}
              whileHover={{ scale: 1.02 }}
              onClick={() => setSelectedConsumable(consumable)}
              style={{
                padding: 16,
                background: theme.surface,
                border: `1px solid ${consumable.status !== "good" ? statusConfig.color : theme.border}`,
                borderRadius: 8,
                cursor: "pointer",
                position: "relative",
                overflow: "hidden",
              }}
            >
              {/* Status indicator */}
              <div
                style={{
                  position: "absolute",
                  top: 0,
                  left: 0,
                  right: 0,
                  height: 3,
                  background: statusConfig.color,
                }}
              />

              {/* Header */}
              <div
                style={{
                  display: "flex",
                  alignItems: "flex-start",
                  gap: 12,
                  marginTop: 8,
                }}
              >
                <div
                  style={{
                    width: 40,
                    height: 40,
                    borderRadius: 8,
                    background: `${statusConfig.color}20`,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    color: statusConfig.color,
                  }}
                >
                  <TypeIcon size={20} />
                </div>

                <div style={{ flex: 1 }}>
                  <div
                    style={{ display: "flex", alignItems: "center", gap: 6 }}
                  >
                    <span
                      style={{
                        color: theme.textPrimary,
                        fontWeight: 600,
                        fontSize: 14,
                      }}
                    >
                      {consumable.name}
                    </span>
                    <StatusIcon size={14} color={statusConfig.color} />
                  </div>
                  <div style={{ color: theme.textSecondary, fontSize: 11 }}>
                    {consumable.brand} - {consumable.partNumber}
                  </div>
                </div>
              </div>

              {/* Life Progress */}
              <div style={{ marginTop: 16 }}>
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    marginBottom: 4,
                  }}
                >
                  <span style={{ color: theme.textSecondary, fontSize: 11 }}>
                    Vida Útil
                  </span>
                  <span
                    style={{
                      color: statusConfig.color,
                      fontSize: 11,
                      fontWeight: 600,
                    }}
                  >
                    {lifePercent.toFixed(0)}%
                  </span>
                </div>
                <div
                  style={{
                    height: 8,
                    background: theme.border,
                    borderRadius: 4,
                    overflow: "hidden",
                  }}
                >
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${lifePercent}%` }}
                    style={{
                      height: "100%",
                      background:
                        lifePercent >= 80
                          ? `linear-gradient(90deg, ${theme.warning}, ${theme.danger})`
                          : lifePercent >= 60
                            ? `linear-gradient(90deg, ${theme.success}, ${theme.warning})`
                            : theme.success,
                      borderRadius: 4,
                    }}
                  />
                </div>
              </div>

              {/* Stats */}
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "1fr 1fr",
                  gap: 12,
                  marginTop: 16,
                  paddingTop: 12,
                  borderTop: `1px dashed ${theme.border}`,
                }}
              >
                <div>
                  <div style={{ color: theme.textSecondary, fontSize: 10 }}>
                    Horas restantes
                  </div>
                  <div style={{ color: theme.textPrimary, fontWeight: 600 }}>
                    {remaining.hours}h
                  </div>
                </div>
                <div>
                  <div style={{ color: theme.textSecondary, fontSize: 10 }}>
                    Perfurações
                  </div>
                  <div style={{ color: theme.textPrimary, fontWeight: 600 }}>
                    {remaining.pierces} restantes
                  </div>
                </div>
              </div>

              {/* Replace button */}
              {(consumable.status === "critical" ||
                consumable.status === "replace") && (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onReplaceConsumable?.(consumable);
                  }}
                  style={{
                    width: "100%",
                    marginTop: 12,
                    padding: "8px 16px",
                    borderRadius: 6,
                    border: "none",
                    background: theme.danger,
                    color: "#FFF",
                    cursor: "pointer",
                    fontSize: 12,
                    fontWeight: 500,
                  }}
                >
                  Registrar Substituição
                </button>
              )}
            </motion.div>
          );
        })}
      </div>

      {/* History Panel */}
      <AnimatePresence>
        {showHistory && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            style={{
              background: theme.surface,
              border: `1px solid ${theme.border}`,
              borderRadius: 8,
              overflow: "hidden",
            }}
          >
            <div
              style={{
                padding: 16,
                borderBottom: `1px solid ${theme.border}`,
                display: "flex",
                alignItems: "center",
                gap: 8,
              }}
            >
              <History size={18} color={theme.accentPrimary} />
              <span style={{ color: theme.textPrimary, fontWeight: 600 }}>
                Histórico de Substituições
              </span>
            </div>

            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr style={{ background: theme.surfaceAlt }}>
                  <th style={thStyle}>Data</th>
                  <th style={thStyle}>Consumível</th>
                  <th style={thStyle}>Horas Usadas</th>
                  <th style={thStyle}>Perfurações</th>
                  <th style={thStyle}>Motivo</th>
                </tr>
              </thead>
              <tbody>
                {history.map((h, idx) => (
                  <tr
                    key={idx}
                    style={{ borderTop: `1px solid ${theme.border}` }}
                  >
                    <td style={{ ...tdStyle, color: theme.textSecondary }}>
                      {new Date(h.date).toLocaleDateString("pt-BR")}
                    </td>
                    <td
                      style={{
                        ...tdStyle,
                        color: theme.textPrimary,
                        fontWeight: 500,
                      }}
                    >
                      {getTypeLabel(h.consumableType as Consumable["type"])}
                    </td>
                    <td style={{ ...tdStyle, color: theme.textSecondary }}>
                      {h.usedHours.toFixed(1)}h
                    </td>
                    <td style={{ ...tdStyle, color: theme.textSecondary }}>
                      {h.pierceCount.toLocaleString()}
                    </td>
                    <td style={{ ...tdStyle, color: theme.textSecondary }}>
                      {h.reason}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Detail Modal */}
      <AnimatePresence>
        {selectedConsumable && (
          <ConsumableDetailModal
            consumable={selectedConsumable}
            theme={theme}
            onClose={() => setSelectedConsumable(null)}
            onReplace={() => {
              onReplaceConsumable?.(selectedConsumable);
              setSelectedConsumable(null);
            }}
          />
        )}
      </AnimatePresence>
    </motion.div>
  );
};

// Styles
const thStyle: React.CSSProperties = {
  padding: 12,
  textAlign: "left",
  fontSize: 12,
  fontWeight: 500,
  color: "#999",
};

const tdStyle: React.CSSProperties = {
  padding: 12,
  fontSize: 13,
};

// Sub-components
const SummaryCard: React.FC<{
  icon: React.ReactNode;
  label: string;
  value: string;
  color?: string;
  theme: CncConsumablesMonitorProps["theme"];
}> = ({ icon, label, value, color, theme }) => (
  <div
    style={{
      padding: 16,
      background: theme.surface,
      border: `1px solid ${theme.border}`,
      borderRadius: 8,
      display: "flex",
      alignItems: "center",
      gap: 12,
    }}
  >
    <div
      style={{
        width: 40,
        height: 40,
        borderRadius: 8,
        background: `${color || theme.accentPrimary}20`,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        color: color || theme.accentPrimary,
      }}
    >
      {icon}
    </div>
    <div>
      <div style={{ color: theme.textSecondary, fontSize: 12 }}>{label}</div>
      <div style={{ color: theme.textPrimary, fontSize: 18, fontWeight: 600 }}>
        {value}
      </div>
    </div>
  </div>
);

const ConsumableDetailModal: React.FC<{
  consumable: Consumable;
  theme: CncConsumablesMonitorProps["theme"];
  onClose: () => void;
  onReplace: () => void;
}> = ({ consumable, theme, onClose, onReplace }) => (
  <motion.div
    initial={{ opacity: 0 }}
    animate={{ opacity: 1 }}
    exit={{ opacity: 0 }}
    style={{
      position: "fixed",
      inset: 0,
      background: "rgba(0,0,0,0.7)",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      zIndex: 1000,
    }}
    onClick={onClose}
  >
    <motion.div
      initial={{ scale: 0.9, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      exit={{ scale: 0.9, opacity: 0 }}
      style={{
        background: theme.surface,
        borderRadius: 12,
        width: "90%",
        maxWidth: 500,
        padding: 24,
      }}
      onClick={(e) => e.stopPropagation()}
    >
      <h3 style={{ margin: "0 0 20px", color: theme.textPrimary }}>
        {consumable.name}
      </h3>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        <InfoRow label="Marca" value={consumable.brand || "-"} theme={theme} />
        <InfoRow
          label="Part Number"
          value={consumable.partNumber || "-"}
          theme={theme}
        />
        <InfoRow
          label="Instalado em"
          value={new Date(consumable.installedAt).toLocaleDateString("pt-BR")}
          theme={theme}
        />
        <InfoRow
          label="Amperagem Atual"
          value={`${consumable.currentAmperage}A`}
          theme={theme}
        />
        <InfoRow
          label="Horas Usadas"
          value={`${consumable.usedHours.toFixed(2)}h / ${consumable.expectedLifeHours}h`}
          theme={theme}
        />
        <InfoRow
          label="Perfurações"
          value={`${consumable.pierceCount.toLocaleString()} / ${consumable.maxPierces.toLocaleString()}`}
          theme={theme}
        />
        <InfoRow
          label="Custo"
          value={`R$ ${consumable.cost.toFixed(2)}`}
          theme={theme}
        />
      </div>

      <div style={{ display: "flex", gap: 12, marginTop: 24 }}>
        <button
          onClick={onClose}
          style={{
            flex: 1,
            padding: "12px",
            borderRadius: 6,
            border: `1px solid ${theme.border}`,
            background: "transparent",
            color: theme.textSecondary,
            cursor: "pointer",
          }}
        >
          Fechar
        </button>
        <button
          onClick={onReplace}
          style={{
            flex: 1,
            padding: "12px",
            borderRadius: 6,
            border: "none",
            background: theme.accentPrimary,
            color: "#FFF",
            cursor: "pointer",
            fontWeight: 500,
          }}
        >
          Registrar Substituição
        </button>
      </div>
    </motion.div>
  </motion.div>
);

const InfoRow: React.FC<{
  label: string;
  value: string;
  theme: CncConsumablesMonitorProps["theme"];
}> = ({ label, value, theme }) => (
  <div>
    <div style={{ color: theme.textSecondary, fontSize: 12, marginBottom: 4 }}>
      {label}
    </div>
    <div style={{ color: theme.textPrimary, fontWeight: 500 }}>{value}</div>
  </div>
);

export default CncConsumablesMonitor;
