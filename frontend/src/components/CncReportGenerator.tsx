/**
 * ═══════════════════════════════════════════════════════════════════════════════
 * CncReportGenerator - Geração de Relatórios PDF/Excel
 * ═══════════════════════════════════════════════════════════════════════════════
 *
 * Melhoria #8: Geração de documentos
 * - Relatórios de produção em PDF
 * - Exportação Excel com dados detalhados
 * - Templates customizáveis
 * - Scheduler de relatórios automáticos
 */

import React, { useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  FileText,
  Download,
  FileSpreadsheet,
  Calendar,
  Clock,
  Settings,
  Mail,
  RefreshCw,
  Check,
  ChevronRight,
  Eye,
  Printer,
  Share2,
  BarChart2,
  TrendingUp,
  Layers,
  Package,
  DollarSign,
  AlertTriangle,
  Filter,
  Plus,
  Trash2,
  Edit3,
  Play,
} from "lucide-react";

interface ReportTemplate {
  id: string;
  name: string;
  description: string;
  type:
    | "production"
    | "materials"
    | "efficiency"
    | "consumables"
    | "cost"
    | "custom";
  format: "pdf" | "excel" | "both";
  sections: string[];
  lastGenerated?: string;
  scheduledEnabled: boolean;
  scheduleCron?: string;
}

interface GeneratedReport {
  id: string;
  templateId: string;
  name: string;
  format: "pdf" | "excel";
  generatedAt: string;
  size: string;
  status: "ready" | "generating" | "error";
  downloadUrl?: string;
}

interface CncReportGeneratorProps {
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
  dateRange?: { start: string; end: string };
}

// Mock templates
const mockTemplates: ReportTemplate[] = [
  {
    id: "rpt-001",
    name: "Relatório de Produção Diário",
    description: "Resumo de jobs executados, peças cortadas e tempo de máquina",
    type: "production",
    format: "pdf",
    sections: ["resumo_geral", "lista_jobs", "graficos_producao", "metricas"],
    lastGenerated: "2025-01-15T08:00:00",
    scheduledEnabled: true,
    scheduleCron: "0 8 * * *",
  },
  {
    id: "rpt-002",
    name: "Análise de Eficiência Semanal",
    description: "Aproveitamento de chapas, desperdício e otimização",
    type: "efficiency",
    format: "both",
    sections: ["eficiencia_por_material", "comparativo_nesting", "tendencias"],
    lastGenerated: "2025-01-13T09:00:00",
    scheduledEnabled: true,
    scheduleCron: "0 9 * * 1",
  },
  {
    id: "rpt-003",
    name: "Consumo de Materiais",
    description: "Detalhamento de chapas consumidas por período",
    type: "materials",
    format: "excel",
    sections: ["lista_materiais", "consumo_por_tipo", "previsao"],
    scheduledEnabled: false,
  },
  {
    id: "rpt-004",
    name: "Controle de Consumíveis",
    description: "Histórico de trocas e projeção de reposição",
    type: "consumables",
    format: "pdf",
    sections: ["consumiveis_status", "historico_trocas", "custos"],
    lastGenerated: "2025-01-14T14:30:00",
    scheduledEnabled: false,
  },
  {
    id: "rpt-005",
    name: "Análise de Custos",
    description: "Custo por peça, material, energia e mão de obra",
    type: "cost",
    format: "excel",
    sections: ["custo_por_job", "custo_por_material", "margem_lucro"],
    scheduledEnabled: false,
  },
];

// Mock generated reports
const mockGenerated: GeneratedReport[] = [
  {
    id: "gen-001",
    templateId: "rpt-001",
    name: "Produção Diária - 15/01/2025",
    format: "pdf",
    generatedAt: "2025-01-15T08:00:00",
    size: "1.2 MB",
    status: "ready",
    downloadUrl: "#",
  },
  {
    id: "gen-002",
    templateId: "rpt-002",
    name: "Eficiência Semanal - Semana 2/2025",
    format: "excel",
    generatedAt: "2025-01-13T09:00:00",
    size: "856 KB",
    status: "ready",
    downloadUrl: "#",
  },
  {
    id: "gen-003",
    templateId: "rpt-004",
    name: "Consumíveis - 14/01/2025",
    format: "pdf",
    generatedAt: "2025-01-14T14:30:00",
    size: "542 KB",
    status: "ready",
    downloadUrl: "#",
  },
];

const CncReportGenerator: React.FC<CncReportGeneratorProps> = ({
  theme,
  dateRange,
}) => {
  const [templates, setTemplates] = useState<ReportTemplate[]>(mockTemplates);
  const [generatedReports, setGeneratedReports] =
    useState<GeneratedReport[]>(mockGenerated);
  const [selectedTemplate, setSelectedTemplate] =
    useState<ReportTemplate | null>(null);
  const [showScheduleModal, setShowScheduleModal] = useState(false);
  const [generating, setGenerating] = useState<string | null>(null);
  const [dateFilter, setDateFilter] = useState({
    start:
      dateRange?.start ||
      new Date(Date.now() - 7 * 24 * 60 * 60 * 1000)
        .toISOString()
        .split("T")[0],
    end: dateRange?.end || new Date().toISOString().split("T")[0],
  });
  const [notification, setNotification] = useState<{
    type: "success" | "error";
    message: string;
  } | null>(null);

  const getTypeConfig = (type: ReportTemplate["type"]) => {
    const configs = {
      production: {
        icon: BarChart2,
        color: theme.accentPrimary,
        label: "Produção",
      },
      materials: { icon: Package, color: theme.success, label: "Materiais" },
      efficiency: { icon: TrendingUp, color: "#9C27B0", label: "Eficiência" },
      consumables: { icon: Layers, color: theme.warning, label: "Consumíveis" },
      cost: { icon: DollarSign, color: "#FF6B35", label: "Custos" },
      custom: {
        icon: Settings,
        color: theme.textSecondary,
        label: "Personalizado",
      },
    };
    return configs[type];
  };

  const getFormatIcon = (format: "pdf" | "excel" | "both") => {
    if (format === "pdf") return FileText;
    if (format === "excel") return FileSpreadsheet;
    return FileText;
  };

  const generateReport = useCallback(
    async (template: ReportTemplate, format: "pdf" | "excel") => {
      setGenerating(`${template.id}-${format}`);

      // Simulate generation
      await new Promise((r) => setTimeout(r, 2000 + Math.random() * 2000));

      const newReport: GeneratedReport = {
        id: `gen-${Date.now()}`,
        templateId: template.id,
        name: `${template.name} - ${new Date().toLocaleDateString("pt-BR")}`,
        format,
        generatedAt: new Date().toISOString(),
        size: `${(Math.random() * 2 + 0.5).toFixed(1)} MB`,
        status: "ready",
        downloadUrl: "#",
      };

      setGeneratedReports((prev) => [newReport, ...prev]);
      setGenerating(null);
      showNotification(
        "success",
        `Relatório "${template.name}" gerado com sucesso`,
      );
    },
    [],
  );

  const showNotification = (type: "success" | "error", message: string) => {
    setNotification({ type, message });
    setTimeout(() => setNotification(null), 3000);
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleString("pt-BR", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const getScheduleLabel = (cron?: string) => {
    if (!cron) return "Não agendado";
    if (cron.includes("* * *")) return "Diário";
    if (cron.includes("* * 1")) return "Semanal (Segunda)";
    if (cron.includes("1 * *")) return "Mensal";
    return "Personalizado";
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      style={{ display: "flex", flexDirection: "column", gap: 20 }}
    >
      {/* Notification */}
      <AnimatePresence>
        {notification && (
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            style={{
              position: "fixed",
              top: 20,
              right: 20,
              padding: "12px 20px",
              borderRadius: 8,
              background:
                notification.type === "success" ? theme.success : theme.danger,
              color: "#FFF",
              display: "flex",
              alignItems: "center",
              gap: 8,
              zIndex: 1000,
              boxShadow: "0 4px 12px rgba(0,0,0,0.3)",
            }}
          >
            {notification.type === "success" ? (
              <Check size={18} />
            ) : (
              <AlertTriangle size={18} />
            )}
            {notification.message}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Header */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <FileText size={24} color={theme.accentPrimary} />
          <h2 style={{ margin: 0, color: theme.textPrimary, fontSize: 20 }}>
            Gerador de Relatórios
          </h2>
        </div>

        {/* Date Range Filter */}
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <Calendar size={16} color={theme.textSecondary} />
          <input
            type="date"
            value={dateFilter.start}
            onChange={(e) =>
              setDateFilter({ ...dateFilter, start: e.target.value })
            }
            style={{
              padding: "6px 10px",
              borderRadius: 4,
              border: `1px solid ${theme.border}`,
              background: theme.surface,
              color: theme.textPrimary,
              fontSize: 13,
            }}
          />
          <span style={{ color: theme.textSecondary }}>até</span>
          <input
            type="date"
            value={dateFilter.end}
            onChange={(e) =>
              setDateFilter({ ...dateFilter, end: e.target.value })
            }
            style={{
              padding: "6px 10px",
              borderRadius: 4,
              border: `1px solid ${theme.border}`,
              background: theme.surface,
              color: theme.textPrimary,
              fontSize: 13,
            }}
          />
        </div>
      </div>

      {/* Templates Section */}
      <div>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginBottom: 12,
          }}
        >
          <h3 style={{ margin: 0, color: theme.textPrimary, fontSize: 16 }}>
            Templates de Relatório
          </h3>
          <button
            style={{
              display: "flex",
              alignItems: "center",
              gap: 6,
              padding: "6px 12px",
              borderRadius: 6,
              border: `1px solid ${theme.border}`,
              background: "transparent",
              color: theme.textSecondary,
              cursor: "pointer",
              fontSize: 12,
            }}
          >
            <Plus size={14} />
            Novo Template
          </button>
        </div>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(340px, 1fr))",
            gap: 12,
          }}
        >
          {templates.map((template) => {
            const typeConfig = getTypeConfig(template.type);
            const TypeIcon = typeConfig.icon;
            const isGenerating = generating?.startsWith(template.id);

            return (
              <motion.div
                key={template.id}
                whileHover={{ y: -2 }}
                style={{
                  background: theme.surface,
                  border: `1px solid ${theme.border}`,
                  borderRadius: 8,
                  padding: 16,
                }}
              >
                {/* Header */}
                <div
                  style={{ display: "flex", alignItems: "flex-start", gap: 12 }}
                >
                  <div
                    style={{
                      width: 40,
                      height: 40,
                      borderRadius: 8,
                      background: `${typeConfig.color}20`,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      color: typeConfig.color,
                    }}
                  >
                    <TypeIcon size={20} />
                  </div>

                  <div style={{ flex: 1 }}>
                    <div
                      style={{
                        color: theme.textPrimary,
                        fontWeight: 600,
                        fontSize: 14,
                        marginBottom: 4,
                      }}
                    >
                      {template.name}
                    </div>
                    <div
                      style={{
                        color: theme.textSecondary,
                        fontSize: 12,
                        lineHeight: 1.4,
                      }}
                    >
                      {template.description}
                    </div>
                  </div>
                </div>

                {/* Info */}
                <div
                  style={{
                    display: "flex",
                    gap: 16,
                    marginTop: 16,
                    paddingTop: 12,
                    borderTop: `1px dashed ${theme.border}`,
                  }}
                >
                  <div style={{ flex: 1 }}>
                    <div style={{ color: theme.textSecondary, fontSize: 10 }}>
                      Formato
                    </div>
                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 4,
                        color: theme.textPrimary,
                        fontSize: 12,
                        marginTop: 2,
                      }}
                    >
                      {template.format === "both" ? (
                        <>
                          <FileText size={12} /> PDF +{" "}
                          <FileSpreadsheet size={12} /> Excel
                        </>
                      ) : template.format === "pdf" ? (
                        <>
                          <FileText size={12} /> PDF
                        </>
                      ) : (
                        <>
                          <FileSpreadsheet size={12} /> Excel
                        </>
                      )}
                    </div>
                  </div>
                  <div style={{ flex: 1 }}>
                    <div style={{ color: theme.textSecondary, fontSize: 10 }}>
                      Agendamento
                    </div>
                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 4,
                        color: template.scheduledEnabled
                          ? theme.success
                          : theme.textSecondary,
                        fontSize: 12,
                        marginTop: 2,
                      }}
                    >
                      <Clock size={12} />
                      {template.scheduledEnabled
                        ? getScheduleLabel(template.scheduleCron)
                        : "Manual"}
                    </div>
                  </div>
                </div>

                {/* Last generated */}
                {template.lastGenerated && (
                  <div
                    style={{
                      color: theme.textSecondary,
                      fontSize: 11,
                      marginTop: 8,
                    }}
                  >
                    Último: {formatDate(template.lastGenerated)}
                  </div>
                )}

                {/* Actions */}
                <div style={{ display: "flex", gap: 8, marginTop: 16 }}>
                  {template.format === "both" ? (
                    <>
                      <button
                        onClick={() => generateReport(template, "pdf")}
                        disabled={!!isGenerating}
                        style={{
                          flex: 1,
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          gap: 6,
                          padding: "8px 12px",
                          borderRadius: 6,
                          border: "none",
                          background:
                            isGenerating === `${template.id}-pdf`
                              ? theme.border
                              : "#E53935",
                          color: "#FFF",
                          cursor: isGenerating ? "not-allowed" : "pointer",
                          fontSize: 12,
                        }}
                      >
                        {isGenerating === `${template.id}-pdf` ? (
                          <RefreshCw size={14} className="spinning" />
                        ) : (
                          <FileText size={14} />
                        )}
                        Gerar PDF
                      </button>
                      <button
                        onClick={() => generateReport(template, "excel")}
                        disabled={!!isGenerating}
                        style={{
                          flex: 1,
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          gap: 6,
                          padding: "8px 12px",
                          borderRadius: 6,
                          border: "none",
                          background:
                            isGenerating === `${template.id}-excel`
                              ? theme.border
                              : "#4CAF50",
                          color: "#FFF",
                          cursor: isGenerating ? "not-allowed" : "pointer",
                          fontSize: 12,
                        }}
                      >
                        {isGenerating === `${template.id}-excel` ? (
                          <RefreshCw size={14} className="spinning" />
                        ) : (
                          <FileSpreadsheet size={14} />
                        )}
                        Gerar Excel
                      </button>
                    </>
                  ) : (
                    <button
                      onClick={() =>
                        generateReport(
                          template,
                          template.format as "pdf" | "excel",
                        )
                      }
                      disabled={!!isGenerating}
                      style={{
                        flex: 1,
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        gap: 6,
                        padding: "8px 12px",
                        borderRadius: 6,
                        border: "none",
                        background: isGenerating
                          ? theme.border
                          : template.format === "pdf"
                            ? "#E53935"
                            : "#4CAF50",
                        color: "#FFF",
                        cursor: isGenerating ? "not-allowed" : "pointer",
                        fontSize: 12,
                      }}
                    >
                      {isGenerating ? (
                        <RefreshCw size={14} className="spinning" />
                      ) : template.format === "pdf" ? (
                        <FileText size={14} />
                      ) : (
                        <FileSpreadsheet size={14} />
                      )}
                      Gerar Relatório
                    </button>
                  )}

                  <button
                    onClick={() => {
                      setSelectedTemplate(template);
                      setShowScheduleModal(true);
                    }}
                    style={{
                      padding: 8,
                      borderRadius: 6,
                      border: `1px solid ${theme.border}`,
                      background: "transparent",
                      color: theme.textSecondary,
                      cursor: "pointer",
                    }}
                    title="Configurar agendamento"
                  >
                    <Clock size={14} />
                  </button>
                </div>
              </motion.div>
            );
          })}
        </div>
      </div>

      {/* Generated Reports Section */}
      <div style={{ marginTop: 20 }}>
        <h3
          style={{ margin: "0 0 12px", color: theme.textPrimary, fontSize: 16 }}
        >
          Relatórios Gerados
        </h3>

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
                <th style={thStyle}>Relatório</th>
                <th style={thStyle}>Formato</th>
                <th style={thStyle}>Gerado em</th>
                <th style={thStyle}>Tamanho</th>
                <th style={thStyle}>Ações</th>
              </tr>
            </thead>
            <tbody>
              {generatedReports.map((report, idx) => (
                <tr
                  key={report.id}
                  style={{ borderTop: `1px solid ${theme.border}` }}
                >
                  <td style={{ padding: 12 }}>
                    <div style={{ color: theme.textPrimary, fontWeight: 500 }}>
                      {report.name}
                    </div>
                  </td>
                  <td style={{ padding: 12 }}>
                    <span
                      style={{
                        display: "inline-flex",
                        alignItems: "center",
                        gap: 4,
                        padding: "4px 8px",
                        borderRadius: 4,
                        background:
                          report.format === "pdf" ? "#E5393520" : "#4CAF5020",
                        color: report.format === "pdf" ? "#E53935" : "#4CAF50",
                        fontSize: 12,
                      }}
                    >
                      {report.format === "pdf" ? (
                        <FileText size={12} />
                      ) : (
                        <FileSpreadsheet size={12} />
                      )}
                      {report.format.toUpperCase()}
                    </span>
                  </td>
                  <td
                    style={{
                      padding: 12,
                      color: theme.textSecondary,
                      fontSize: 13,
                    }}
                  >
                    {formatDate(report.generatedAt)}
                  </td>
                  <td
                    style={{
                      padding: 12,
                      color: theme.textSecondary,
                      fontSize: 13,
                    }}
                  >
                    {report.size}
                  </td>
                  <td style={{ padding: 12 }}>
                    <div style={{ display: "flex", gap: 4 }}>
                      <button
                        style={{
                          padding: 6,
                          borderRadius: 4,
                          border: `1px solid ${theme.border}`,
                          background: "transparent",
                          color: theme.textSecondary,
                          cursor: "pointer",
                        }}
                        title="Visualizar"
                      >
                        <Eye size={14} />
                      </button>
                      <button
                        style={{
                          padding: 6,
                          borderRadius: 4,
                          border: "none",
                          background: theme.accentPrimary,
                          color: "#FFF",
                          cursor: "pointer",
                        }}
                        title="Download"
                      >
                        <Download size={14} />
                      </button>
                      <button
                        style={{
                          padding: 6,
                          borderRadius: 4,
                          border: `1px solid ${theme.border}`,
                          background: "transparent",
                          color: theme.textSecondary,
                          cursor: "pointer",
                        }}
                        title="Imprimir"
                      >
                        <Printer size={14} />
                      </button>
                      <button
                        style={{
                          padding: 6,
                          borderRadius: 4,
                          border: `1px solid ${theme.border}`,
                          background: "transparent",
                          color: theme.textSecondary,
                          cursor: "pointer",
                        }}
                        title="Compartilhar"
                      >
                        <Share2 size={14} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {generatedReports.length === 0 && (
            <div
              style={{
                padding: 40,
                textAlign: "center",
                color: theme.textSecondary,
              }}
            >
              <FileText size={40} style={{ opacity: 0.3, marginBottom: 12 }} />
              <div>Nenhum relatório gerado ainda</div>
            </div>
          )}
        </div>
      </div>

      {/* Schedule Modal */}
      <AnimatePresence>
        {showScheduleModal && selectedTemplate && (
          <ScheduleModal
            template={selectedTemplate}
            theme={theme}
            onClose={() => {
              setShowScheduleModal(false);
              setSelectedTemplate(null);
            }}
            onSave={(schedule) => {
              setTemplates((prev) =>
                prev.map((t) =>
                  t.id === selectedTemplate.id
                    ? {
                        ...t,
                        scheduledEnabled: schedule.enabled,
                        scheduleCron: schedule.cron,
                      }
                    : t,
                ),
              );
              setShowScheduleModal(false);
              setSelectedTemplate(null);
              showNotification("success", "Agendamento atualizado");
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

// Schedule Modal
const ScheduleModal: React.FC<{
  template: ReportTemplate;
  theme: CncReportGeneratorProps["theme"];
  onClose: () => void;
  onSave: (schedule: { enabled: boolean; cron: string }) => void;
}> = ({ template, theme, onClose, onSave }) => {
  const [enabled, setEnabled] = useState(template.scheduledEnabled);
  const [frequency, setFrequency] = useState<"daily" | "weekly" | "monthly">(
    "daily",
  );
  const [time, setTime] = useState("08:00");
  const [dayOfWeek, setDayOfWeek] = useState(1);
  const [dayOfMonth, setDayOfMonth] = useState(1);
  const [email, setEmail] = useState("");

  const getCron = () => {
    const [hour, minute] = time.split(":").map(Number);
    switch (frequency) {
      case "daily":
        return `${minute} ${hour} * * *`;
      case "weekly":
        return `${minute} ${hour} * * ${dayOfWeek}`;
      case "monthly":
        return `${minute} ${hour} ${dayOfMonth} * *`;
      default:
        return "";
    }
  };

  return (
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
          maxWidth: 450,
          padding: 24,
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <h3 style={{ margin: "0 0 20px", color: theme.textPrimary }}>
          Agendamento: {template.name}
        </h3>

        {/* Enable toggle */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            padding: 12,
            background: theme.surfaceAlt,
            borderRadius: 6,
            marginBottom: 20,
          }}
        >
          <span style={{ color: theme.textPrimary }}>Geração automática</span>
          <button
            onClick={() => setEnabled(!enabled)}
            style={{
              width: 48,
              height: 26,
              borderRadius: 13,
              border: "none",
              background: enabled ? theme.success : theme.border,
              cursor: "pointer",
              position: "relative",
            }}
          >
            <div
              style={{
                width: 22,
                height: 22,
                borderRadius: "50%",
                background: "#FFF",
                position: "absolute",
                top: 2,
                left: enabled ? 24 : 2,
                transition: "left 0.2s",
              }}
            />
          </button>
        </div>

        {enabled && (
          <>
            {/* Frequency */}
            <div style={{ marginBottom: 16 }}>
              <label
                style={{
                  color: theme.textSecondary,
                  fontSize: 12,
                  display: "block",
                  marginBottom: 6,
                }}
              >
                Frequência
              </label>
              <div style={{ display: "flex", gap: 8 }}>
                {[
                  { key: "daily", label: "Diário" },
                  { key: "weekly", label: "Semanal" },
                  { key: "monthly", label: "Mensal" },
                ].map(({ key, label }) => (
                  <button
                    key={key}
                    onClick={() => setFrequency(key as typeof frequency)}
                    style={{
                      flex: 1,
                      padding: "8px 12px",
                      borderRadius: 6,
                      border: `1px solid ${frequency === key ? theme.accentPrimary : theme.border}`,
                      background:
                        frequency === key
                          ? `${theme.accentPrimary}20`
                          : "transparent",
                      color:
                        frequency === key
                          ? theme.accentPrimary
                          : theme.textSecondary,
                      cursor: "pointer",
                      fontSize: 13,
                    }}
                  >
                    {label}
                  </button>
                ))}
              </div>
            </div>

            {/* Time */}
            <div style={{ marginBottom: 16 }}>
              <label
                style={{
                  color: theme.textSecondary,
                  fontSize: 12,
                  display: "block",
                  marginBottom: 6,
                }}
              >
                Horário
              </label>
              <input
                type="time"
                value={time}
                onChange={(e) => setTime(e.target.value)}
                style={{
                  width: "100%",
                  padding: 10,
                  borderRadius: 6,
                  border: `1px solid ${theme.border}`,
                  background: theme.surfaceAlt,
                  color: theme.textPrimary,
                }}
              />
            </div>

            {/* Day of week (for weekly) */}
            {frequency === "weekly" && (
              <div style={{ marginBottom: 16 }}>
                <label
                  style={{
                    color: theme.textSecondary,
                    fontSize: 12,
                    display: "block",
                    marginBottom: 6,
                  }}
                >
                  Dia da semana
                </label>
                <select
                  value={dayOfWeek}
                  onChange={(e) => setDayOfWeek(Number(e.target.value))}
                  style={{
                    width: "100%",
                    padding: 10,
                    borderRadius: 6,
                    border: `1px solid ${theme.border}`,
                    background: theme.surfaceAlt,
                    color: theme.textPrimary,
                  }}
                >
                  <option value={0}>Domingo</option>
                  <option value={1}>Segunda</option>
                  <option value={2}>Terça</option>
                  <option value={3}>Quarta</option>
                  <option value={4}>Quinta</option>
                  <option value={5}>Sexta</option>
                  <option value={6}>Sábado</option>
                </select>
              </div>
            )}

            {/* Day of month (for monthly) */}
            {frequency === "monthly" && (
              <div style={{ marginBottom: 16 }}>
                <label
                  style={{
                    color: theme.textSecondary,
                    fontSize: 12,
                    display: "block",
                    marginBottom: 6,
                  }}
                >
                  Dia do mês
                </label>
                <select
                  value={dayOfMonth}
                  onChange={(e) => setDayOfMonth(Number(e.target.value))}
                  style={{
                    width: "100%",
                    padding: 10,
                    borderRadius: 6,
                    border: `1px solid ${theme.border}`,
                    background: theme.surfaceAlt,
                    color: theme.textPrimary,
                  }}
                >
                  {Array.from({ length: 28 }, (_, i) => i + 1).map((d) => (
                    <option key={d} value={d}>
                      Dia {d}
                    </option>
                  ))}
                </select>
              </div>
            )}

            {/* Email notification */}
            <div style={{ marginBottom: 16 }}>
              <label
                style={{
                  color: theme.textSecondary,
                  fontSize: 12,
                  display: "block",
                  marginBottom: 6,
                }}
              >
                <Mail size={12} style={{ marginRight: 4 }} />
                Email para notificação (opcional)
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="email@empresa.com"
                style={{
                  width: "100%",
                  padding: 10,
                  borderRadius: 6,
                  border: `1px solid ${theme.border}`,
                  background: theme.surfaceAlt,
                  color: theme.textPrimary,
                }}
              />
            </div>
          </>
        )}

        {/* Actions */}
        <div style={{ display: "flex", gap: 12, marginTop: 24 }}>
          <button
            onClick={onClose}
            style={{
              flex: 1,
              padding: 12,
              borderRadius: 6,
              border: `1px solid ${theme.border}`,
              background: "transparent",
              color: theme.textSecondary,
              cursor: "pointer",
            }}
          >
            Cancelar
          </button>
          <button
            onClick={() => onSave({ enabled, cron: getCron() })}
            style={{
              flex: 1,
              padding: 12,
              borderRadius: 6,
              border: "none",
              background: theme.accentPrimary,
              color: "#FFF",
              cursor: "pointer",
              fontWeight: 500,
            }}
          >
            Salvar
          </button>
        </div>
      </motion.div>
    </motion.div>
  );
};

export default CncReportGenerator;
