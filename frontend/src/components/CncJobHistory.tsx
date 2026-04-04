/**
 * ═══════════════════════════════════════════════════════════════════════════════
 * CncJobHistory - Dashboard de Histórico de Trabalhos CNC
 * ═══════════════════════════════════════════════════════════════════════════════
 *
 * Melhoria #2: Página de histórico de jobs
 * - Lista paginada de trabalhos
 * - Filtros por data, status, material
 * - Replay de simulação anterior
 * - Estatísticas de performance
 */

import React, { useState, useEffect, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  History,
  Search,
  Filter,
  Calendar,
  CheckCircle,
  XCircle,
  Clock,
  Play,
  Download,
  Eye,
  BarChart2,
  Layers,
  ChevronLeft,
  ChevronRight,
  SortAsc,
  SortDesc,
  RefreshCw,
  FileText,
  Package,
  Flame,
  TrendingUp,
} from "lucide-react";

interface Job {
  id: string;
  name: string;
  date: string;
  status: "completed" | "failed" | "cancelled" | "in_progress";
  material: string;
  thickness: number;
  pieceCount: number;
  sheetUsage: number;
  cutTime: number; // seconds
  gcodeFile?: string;
  thumbnail?: string;
  error?: string;
  operator?: string;
  machine?: string;
}

interface JobMetrics {
  totalJobs: number;
  completedJobs: number;
  failedJobs: number;
  avgSheetUsage: number;
  totalCutTime: number;
  avgCutTime: number;
}

interface CncJobHistoryProps {
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
  onReplayJob?: (job: Job) => void;
  onDownloadGcode?: (job: Job) => void;
  onViewDetails?: (job: Job) => void;
}

// Mock data - em produção viria da API
const mockJobs: Job[] = [
  {
    id: "job-001",
    name: "Flanges Industriais Lote 45",
    date: "2025-01-15T14:30:00",
    status: "completed",
    material: "Aço Carbono",
    thickness: 6,
    pieceCount: 24,
    sheetUsage: 87.3,
    cutTime: 1842,
    operator: "Carlos",
    machine: "Plasma CNC 01",
  },
  {
    id: "job-002",
    name: "Suportes Estruturais",
    date: "2025-01-15T10:15:00",
    status: "completed",
    material: "Aço Inox 304",
    thickness: 4,
    pieceCount: 48,
    sheetUsage: 92.1,
    cutTime: 2156,
    operator: "Maria",
    machine: "Plasma CNC 02",
  },
  {
    id: "job-003",
    name: "Chapas Perfuradas",
    date: "2025-01-14T16:45:00",
    status: "failed",
    material: "Alumínio",
    thickness: 3,
    pieceCount: 12,
    sheetUsage: 65.0,
    cutTime: 0,
    error: "Falha no arco plasma - bico danificado",
    operator: "João",
    machine: "Plasma CNC 01",
  },
  {
    id: "job-004",
    name: "Brackets de Fixação",
    date: "2025-01-14T09:00:00",
    status: "completed",
    material: "Aço Carbono",
    thickness: 8,
    pieceCount: 36,
    sheetUsage: 78.5,
    cutTime: 2890,
    operator: "Carlos",
    machine: "Plasma CNC 01",
  },
  {
    id: "job-005",
    name: "Tampas Circulares",
    date: "2025-01-13T11:20:00",
    status: "cancelled",
    material: "Aço Inox 316",
    thickness: 5,
    pieceCount: 20,
    sheetUsage: 0,
    cutTime: 0,
    operator: "Maria",
    machine: "Plasma CNC 02",
  },
];

const ITEMS_PER_PAGE = 10;

const CncJobHistory: React.FC<CncJobHistoryProps> = ({
  theme,
  onReplayJob,
  onDownloadGcode,
  onViewDetails,
}) => {
  const [jobs, setJobs] = useState<Job[]>(mockJobs);
  const [loading, setLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [materialFilter, setMaterialFilter] = useState<string>("all");
  const [dateRange, setDateRange] = useState<{ start: string; end: string }>({
    start: "",
    end: "",
  });
  const [sortField, setSortField] = useState<keyof Job>("date");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");
  const [currentPage, setCurrentPage] = useState(1);

  // Unique materials for filter
  const materials = useMemo(() => {
    const unique = [...new Set(jobs.map((j) => j.material))];
    return unique;
  }, [jobs]);

  // Filtered and sorted jobs
  const filteredJobs = useMemo(() => {
    let result = [...jobs];

    // Search
    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      result = result.filter(
        (j) =>
          j.name.toLowerCase().includes(term) ||
          j.id.toLowerCase().includes(term) ||
          j.operator?.toLowerCase().includes(term),
      );
    }

    // Status filter
    if (statusFilter !== "all") {
      result = result.filter((j) => j.status === statusFilter);
    }

    // Material filter
    if (materialFilter !== "all") {
      result = result.filter((j) => j.material === materialFilter);
    }

    // Date range
    if (dateRange.start) {
      result = result.filter(
        (j) => new Date(j.date) >= new Date(dateRange.start),
      );
    }
    if (dateRange.end) {
      result = result.filter(
        (j) => new Date(j.date) <= new Date(dateRange.end),
      );
    }

    // Sort
    result.sort((a, b) => {
      let aVal = a[sortField];
      let bVal = b[sortField];

      if (sortField === "date") {
        aVal = new Date(aVal as string).getTime();
        bVal = new Date(bVal as string).getTime();
      }

      if (aVal < bVal) return sortDir === "asc" ? -1 : 1;
      if (aVal > bVal) return sortDir === "asc" ? 1 : -1;
      return 0;
    });

    return result;
  }, [
    jobs,
    searchTerm,
    statusFilter,
    materialFilter,
    dateRange,
    sortField,
    sortDir,
  ]);

  // Pagination
  const totalPages = Math.ceil(filteredJobs.length / ITEMS_PER_PAGE);
  const paginatedJobs = filteredJobs.slice(
    (currentPage - 1) * ITEMS_PER_PAGE,
    currentPage * ITEMS_PER_PAGE,
  );

  // Metrics
  const metrics: JobMetrics = useMemo(() => {
    const completed = jobs.filter((j) => j.status === "completed");
    return {
      totalJobs: jobs.length,
      completedJobs: completed.length,
      failedJobs: jobs.filter((j) => j.status === "failed").length,
      avgSheetUsage:
        completed.length > 0
          ? completed.reduce((sum, j) => sum + j.sheetUsage, 0) /
            completed.length
          : 0,
      totalCutTime: completed.reduce((sum, j) => sum + j.cutTime, 0),
      avgCutTime:
        completed.length > 0
          ? completed.reduce((sum, j) => sum + j.cutTime, 0) / completed.length
          : 0,
    };
  }, [jobs]);

  const formatTime = (seconds: number) => {
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = seconds % 60;
    if (h > 0) return `${h}h ${m}m`;
    if (m > 0) return `${m}m ${s}s`;
    return `${s}s`;
  };

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString("pt-BR", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const toggleSort = (field: keyof Job) => {
    if (sortField === field) {
      setSortDir(sortDir === "asc" ? "desc" : "asc");
    } else {
      setSortField(field);
      setSortDir("desc");
    }
  };

  const getStatusConfig = (status: Job["status"]) => {
    switch (status) {
      case "completed":
        return { color: theme.success, icon: CheckCircle, label: "Concluído" };
      case "failed":
        return { color: theme.danger, icon: XCircle, label: "Falhou" };
      case "cancelled":
        return { color: theme.warning, icon: XCircle, label: "Cancelado" };
      case "in_progress":
        return {
          color: theme.accentPrimary,
          icon: Clock,
          label: "Em Progresso",
        };
      default:
        return { color: theme.textSecondary, icon: Clock, label: status };
    }
  };

  const refreshData = async () => {
    setLoading(true);
    // Simular fetch
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
          <History size={24} color={theme.accentPrimary} />
          <h2 style={{ margin: 0, color: theme.textPrimary, fontSize: 20 }}>
            Histórico de Trabalhos
          </h2>
        </div>
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
          }}
        >
          <RefreshCw size={16} className={loading ? "spinning" : ""} />
          Atualizar
        </button>
      </div>

      {/* Metrics Cards */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(5, 1fr)",
          gap: 12,
        }}
      >
        <MetricCard
          icon={<FileText size={18} />}
          label="Total Jobs"
          value={metrics.totalJobs.toString()}
          theme={theme}
        />
        <MetricCard
          icon={<CheckCircle size={18} />}
          label="Concluídos"
          value={metrics.completedJobs.toString()}
          color={theme.success}
          theme={theme}
        />
        <MetricCard
          icon={<XCircle size={18} />}
          label="Falhas"
          value={metrics.failedJobs.toString()}
          color={theme.danger}
          theme={theme}
        />
        <MetricCard
          icon={<Layers size={18} />}
          label="Aproveitamento Médio"
          value={`${metrics.avgSheetUsage.toFixed(1)}%`}
          color={theme.accentPrimary}
          theme={theme}
        />
        <MetricCard
          icon={<Clock size={18} />}
          label="Tempo Total Corte"
          value={formatTime(metrics.totalCutTime)}
          theme={theme}
        />
      </div>

      {/* Filters */}
      <div
        style={{
          display: "flex",
          gap: 12,
          padding: 16,
          background: theme.surface,
          border: `1px solid ${theme.border}`,
          borderRadius: 8,
          flexWrap: "wrap",
        }}
      >
        {/* Search */}
        <div style={{ flex: 1, minWidth: 200, position: "relative" }}>
          <Search
            size={16}
            style={{
              position: "absolute",
              left: 12,
              top: "50%",
              transform: "translateY(-50%)",
              color: theme.textSecondary,
            }}
          />
          <input
            type="text"
            placeholder="Buscar por nome, ID ou operador..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            style={{
              width: "100%",
              padding: "8px 12px 8px 36px",
              borderRadius: 6,
              border: `1px solid ${theme.border}`,
              background: theme.surfaceAlt,
              color: theme.textPrimary,
              fontSize: 14,
            }}
          />
        </div>

        {/* Status filter */}
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          style={{
            padding: "8px 12px",
            borderRadius: 6,
            border: `1px solid ${theme.border}`,
            background: theme.surfaceAlt,
            color: theme.textPrimary,
            fontSize: 14,
          }}
        >
          <option value="all">Todos Status</option>
          <option value="completed">Concluídos</option>
          <option value="failed">Falhou</option>
          <option value="cancelled">Cancelados</option>
          <option value="in_progress">Em Progresso</option>
        </select>

        {/* Material filter */}
        <select
          value={materialFilter}
          onChange={(e) => setMaterialFilter(e.target.value)}
          style={{
            padding: "8px 12px",
            borderRadius: 6,
            border: `1px solid ${theme.border}`,
            background: theme.surfaceAlt,
            color: theme.textPrimary,
            fontSize: 14,
          }}
        >
          <option value="all">Todos Materiais</option>
          {materials.map((m) => (
            <option key={m} value={m}>
              {m}
            </option>
          ))}
        </select>

        {/* Date range */}
        <input
          type="date"
          value={dateRange.start}
          onChange={(e) =>
            setDateRange({ ...dateRange, start: e.target.value })
          }
          style={{
            padding: "8px 12px",
            borderRadius: 6,
            border: `1px solid ${theme.border}`,
            background: theme.surfaceAlt,
            color: theme.textPrimary,
            fontSize: 14,
          }}
        />
        <span style={{ color: theme.textSecondary, alignSelf: "center" }}>
          até
        </span>
        <input
          type="date"
          value={dateRange.end}
          onChange={(e) => setDateRange({ ...dateRange, end: e.target.value })}
          style={{
            padding: "8px 12px",
            borderRadius: 6,
            border: `1px solid ${theme.border}`,
            background: theme.surfaceAlt,
            color: theme.textPrimary,
            fontSize: 14,
          }}
        />
      </div>

      {/* Table */}
      <div
        style={{
          background: theme.surface,
          border: `1px solid ${theme.border}`,
          borderRadius: 8,
          overflow: "hidden",
        }}
      >
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ background: theme.surfaceAlt }}>
              <Th
                onClick={() => toggleSort("name")}
                active={sortField === "name"}
                dir={sortDir}
                theme={theme}
              >
                Nome do Trabalho
              </Th>
              <Th
                onClick={() => toggleSort("date")}
                active={sortField === "date"}
                dir={sortDir}
                theme={theme}
              >
                Data
              </Th>
              <Th
                onClick={() => toggleSort("status")}
                active={sortField === "status"}
                dir={sortDir}
                theme={theme}
              >
                Status
              </Th>
              <Th
                onClick={() => toggleSort("material")}
                active={sortField === "material"}
                dir={sortDir}
                theme={theme}
              >
                Material
              </Th>
              <Th
                onClick={() => toggleSort("pieceCount")}
                active={sortField === "pieceCount"}
                dir={sortDir}
                theme={theme}
              >
                Peças
              </Th>
              <Th
                onClick={() => toggleSort("sheetUsage")}
                active={sortField === "sheetUsage"}
                dir={sortDir}
                theme={theme}
              >
                Aproveitamento
              </Th>
              <Th
                onClick={() => toggleSort("cutTime")}
                active={sortField === "cutTime"}
                dir={sortDir}
                theme={theme}
              >
                Tempo
              </Th>
              <th
                style={{
                  padding: 12,
                  textAlign: "center",
                  color: theme.textSecondary,
                  fontWeight: 500,
                  fontSize: 13,
                }}
              >
                Ações
              </th>
            </tr>
          </thead>
          <tbody>
            <AnimatePresence>
              {paginatedJobs.map((job) => {
                const statusConfig = getStatusConfig(job.status);
                const StatusIcon = statusConfig.icon;

                return (
                  <motion.tr
                    key={job.id}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    style={{
                      borderTop: `1px solid ${theme.border}`,
                    }}
                  >
                    <td style={{ padding: 12 }}>
                      <div>
                        <div
                          style={{ color: theme.textPrimary, fontWeight: 500 }}
                        >
                          {job.name}
                        </div>
                        <div
                          style={{ color: theme.textSecondary, fontSize: 11 }}
                        >
                          {job.id}
                        </div>
                      </div>
                    </td>
                    <td
                      style={{
                        padding: 12,
                        color: theme.textSecondary,
                        fontSize: 13,
                      }}
                    >
                      {formatDate(job.date)}
                    </td>
                    <td style={{ padding: 12 }}>
                      <span
                        style={{
                          display: "inline-flex",
                          alignItems: "center",
                          gap: 6,
                          padding: "4px 8px",
                          borderRadius: 4,
                          background: `${statusConfig.color}20`,
                          color: statusConfig.color,
                          fontSize: 12,
                          fontWeight: 500,
                        }}
                      >
                        <StatusIcon size={12} />
                        {statusConfig.label}
                      </span>
                    </td>
                    <td
                      style={{
                        padding: 12,
                        color: theme.textPrimary,
                        fontSize: 13,
                      }}
                    >
                      {job.material} ({job.thickness}mm)
                    </td>
                    <td
                      style={{
                        padding: 12,
                        color: theme.textPrimary,
                        fontSize: 13,
                        textAlign: "center",
                      }}
                    >
                      {job.pieceCount}
                    </td>
                    <td style={{ padding: 12 }}>
                      {job.sheetUsage > 0 ? (
                        <div
                          style={{
                            display: "flex",
                            alignItems: "center",
                            gap: 8,
                          }}
                        >
                          <div
                            style={{
                              width: 60,
                              height: 6,
                              background: theme.border,
                              borderRadius: 3,
                              overflow: "hidden",
                            }}
                          >
                            <div
                              style={{
                                width: `${job.sheetUsage}%`,
                                height: "100%",
                                background:
                                  job.sheetUsage >= 85
                                    ? theme.success
                                    : job.sheetUsage >= 70
                                      ? theme.warning
                                      : theme.danger,
                              }}
                            />
                          </div>
                          <span
                            style={{ color: theme.textPrimary, fontSize: 12 }}
                          >
                            {job.sheetUsage.toFixed(1)}%
                          </span>
                        </div>
                      ) : (
                        <span
                          style={{ color: theme.textSecondary, fontSize: 12 }}
                        >
                          -
                        </span>
                      )}
                    </td>
                    <td
                      style={{
                        padding: 12,
                        color: theme.textSecondary,
                        fontSize: 13,
                      }}
                    >
                      {job.cutTime > 0 ? formatTime(job.cutTime) : "-"}
                    </td>
                    <td style={{ padding: 12 }}>
                      <div
                        style={{
                          display: "flex",
                          gap: 6,
                          justifyContent: "center",
                        }}
                      >
                        <ActionButton
                          icon={<Eye size={14} />}
                          title="Ver detalhes"
                          onClick={() => onViewDetails?.(job)}
                          theme={theme}
                        />
                        {job.status === "completed" && (
                          <>
                            <ActionButton
                              icon={<Play size={14} />}
                              title="Replay simulação"
                              onClick={() => onReplayJob?.(job)}
                              theme={theme}
                            />
                            <ActionButton
                              icon={<Download size={14} />}
                              title="Download G-Code"
                              onClick={() => onDownloadGcode?.(job)}
                              theme={theme}
                            />
                          </>
                        )}
                      </div>
                    </td>
                  </motion.tr>
                );
              })}
            </AnimatePresence>
          </tbody>
        </table>

        {/* Pagination */}
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            padding: 16,
            borderTop: `1px solid ${theme.border}`,
          }}
        >
          <span style={{ color: theme.textSecondary, fontSize: 13 }}>
            Mostrando {(currentPage - 1) * ITEMS_PER_PAGE + 1} -{" "}
            {Math.min(currentPage * ITEMS_PER_PAGE, filteredJobs.length)} de{" "}
            {filteredJobs.length} trabalhos
          </span>
          <div style={{ display: "flex", gap: 8 }}>
            <button
              onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
              disabled={currentPage === 1}
              style={{
                padding: 8,
                borderRadius: 4,
                border: `1px solid ${theme.border}`,
                background: "transparent",
                color:
                  currentPage === 1 ? theme.textSecondary : theme.textPrimary,
                cursor: currentPage === 1 ? "not-allowed" : "pointer",
                opacity: currentPage === 1 ? 0.5 : 1,
              }}
            >
              <ChevronLeft size={16} />
            </button>
            {Array.from({ length: totalPages }, (_, i) => i + 1).map((page) => (
              <button
                key={page}
                onClick={() => setCurrentPage(page)}
                style={{
                  padding: "8px 12px",
                  borderRadius: 4,
                  border: `1px solid ${page === currentPage ? theme.accentPrimary : theme.border}`,
                  background:
                    page === currentPage ? theme.accentPrimary : "transparent",
                  color: page === currentPage ? "#FFF" : theme.textSecondary,
                  cursor: "pointer",
                  fontSize: 13,
                }}
              >
                {page}
              </button>
            ))}
            <button
              onClick={() =>
                setCurrentPage(Math.min(totalPages, currentPage + 1))
              }
              disabled={currentPage === totalPages}
              style={{
                padding: 8,
                borderRadius: 4,
                border: `1px solid ${theme.border}`,
                background: "transparent",
                color:
                  currentPage === totalPages
                    ? theme.textSecondary
                    : theme.textPrimary,
                cursor: currentPage === totalPages ? "not-allowed" : "pointer",
                opacity: currentPage === totalPages ? 0.5 : 1,
              }}
            >
              <ChevronRight size={16} />
            </button>
          </div>
        </div>
      </div>
    </motion.div>
  );
};

// Sub-components

const MetricCard: React.FC<{
  icon: React.ReactNode;
  label: string;
  value: string;
  color?: string;
  theme: CncJobHistoryProps["theme"];
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

const Th: React.FC<{
  children: React.ReactNode;
  onClick: () => void;
  active: boolean;
  dir: "asc" | "desc";
  theme: CncJobHistoryProps["theme"];
}> = ({ children, onClick, active, dir, theme }) => (
  <th
    onClick={onClick}
    style={{
      padding: 12,
      textAlign: "left",
      color: active ? theme.accentPrimary : theme.textSecondary,
      fontWeight: 500,
      fontSize: 13,
      cursor: "pointer",
      userSelect: "none",
    }}
  >
    <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
      {children}
      {active &&
        (dir === "asc" ? <SortAsc size={12} /> : <SortDesc size={12} />)}
    </div>
  </th>
);

const ActionButton: React.FC<{
  icon: React.ReactNode;
  title: string;
  onClick: () => void;
  theme: CncJobHistoryProps["theme"];
}> = ({ icon, title, onClick, theme }) => (
  <button
    onClick={onClick}
    title={title}
    style={{
      width: 28,
      height: 28,
      borderRadius: 4,
      border: `1px solid ${theme.border}`,
      background: "transparent",
      color: theme.textSecondary,
      cursor: "pointer",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
    }}
  >
    {icon}
  </button>
);

export default CncJobHistory;
