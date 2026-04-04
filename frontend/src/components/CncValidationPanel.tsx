/**
 * ═══════════════════════════════════════════════════════════════════════════════
 * CncValidationPanel - Painel de Validações em Tempo Real
 * ═══════════════════════════════════════════════════════════════════════════════
 *
 * Mostra em tempo real os problemas de geometria:
 * - Erros críticos (bloqueiam o corte)
 * - Avisos importantes (podem causar problemas)
 * - Sugestões de otimização
 */

import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  AlertTriangle,
  AlertCircle,
  CheckCircle,
  Info,
  ChevronDown,
  ChevronRight,
  RefreshCw,
  Target,
  Maximize,
  MinusCircle,
  CircleDot,
  Layers,
  CornerDownRight,
  Eye,
  EyeOff,
} from "lucide-react";

type IssueSeverity = "error" | "warning" | "info" | "success";
type IssueCategory =
  | "geometry"
  | "nesting"
  | "toolpath"
  | "material"
  | "machine";

interface ValidationIssue {
  id: string;
  severity: IssueSeverity;
  category: IssueCategory;
  code: string;
  message: string;
  description?: string;
  pieceId?: string;
  pieceName?: string;
  location?: { x: number; y: number };
  autoFixAvailable?: boolean;
}

interface CncValidationPanelProps {
  issues: ValidationIssue[];
  isValidating?: boolean;
  onRefresh?: () => void;
  onAutoFix?: (issueId: string) => void;
  onHighlightIssue?: (issue: ValidationIssue) => void;
  onDismissIssue?: (issueId: string) => void;
  theme: {
    surface: string;
    border: string;
    accentPrimary: string;
    success: string;
    warning: string;
    danger: string;
    textPrimary: string;
    textSecondary: string;
    inputBackground: string;
  };
}

const CncValidationPanel: React.FC<CncValidationPanelProps> = ({
  issues,
  isValidating = false,
  onRefresh,
  onAutoFix,
  onHighlightIssue,
  onDismissIssue,
  theme,
}) => {
  const [expandedCategory, setExpandedCategory] =
    useState<IssueCategory | null>(null);
  const [hiddenIssueIds, setHiddenIssueIds] = useState<Set<string>>(new Set());
  const [showAllIssues, setShowAllIssues] = useState(true);

  // Filtrar issues visíveis
  const visibleIssues = showAllIssues
    ? issues
    : issues.filter((i) => !hiddenIssueIds.has(i.id));

  // Agrupar por categoria
  const groupedIssues = visibleIssues.reduce(
    (acc, issue) => {
      if (!acc[issue.category]) acc[issue.category] = [];
      acc[issue.category].push(issue);
      return acc;
    },
    {} as Record<IssueCategory, ValidationIssue[]>,
  );

  // Contadores
  const errorCount = visibleIssues.filter((i) => i.severity === "error").length;
  const warningCount = visibleIssues.filter(
    (i) => i.severity === "warning",
  ).length;
  const infoCount = visibleIssues.filter((i) => i.severity === "info").length;
  const hasIssues = errorCount > 0 || warningCount > 0;

  // Cores e ícones por severidade
  const severityConfig: Record<
    IssueSeverity,
    { color: string; icon: React.FC<any>; label: string }
  > = {
    error: { color: theme.danger, icon: AlertCircle, label: "Erro" },
    warning: { color: theme.warning, icon: AlertTriangle, label: "Aviso" },
    info: { color: theme.accentPrimary, icon: Info, label: "Info" },
    success: { color: theme.success, icon: CheckCircle, label: "OK" },
  };

  // Configuração de categorias
  const categoryConfig: Record<
    IssueCategory,
    { icon: React.FC<any>; label: string }
  > = {
    geometry: { icon: CircleDot, label: "Geometria" },
    nesting: { icon: Layers, label: "Nesting" },
    toolpath: { icon: CornerDownRight, label: "Toolpath" },
    material: { icon: Maximize, label: "Material" },
    machine: { icon: Target, label: "Máquina" },
  };

  const handleToggleHidden = (issueId: string) => {
    const newHidden = new Set(hiddenIssueIds);
    if (newHidden.has(issueId)) {
      newHidden.delete(issueId);
    } else {
      newHidden.add(issueId);
    }
    setHiddenIssueIds(newHidden);
  };

  // Renderizar issue individual
  const renderIssue = (issue: ValidationIssue) => {
    const config = severityConfig[issue.severity];
    const Icon = config.icon;
    const isHidden = hiddenIssueIds.has(issue.id);

    return (
      <motion.div
        key={issue.id}
        initial={{ opacity: 0, x: -10 }}
        animate={{ opacity: isHidden ? 0.5 : 1, x: 0 }}
        exit={{ opacity: 0, height: 0 }}
        style={{
          display: "flex",
          gap: 10,
          padding: "10px 12px",
          backgroundColor: `${config.color}08`,
          borderLeft: `3px solid ${config.color}`,
          borderRadius: "0 8px 8px 0",
          marginBottom: 6,
          cursor: "pointer",
          transition: "all 0.2s",
        }}
        onClick={() => onHighlightIssue?.(issue)}
        whileHover={{ backgroundColor: `${config.color}15` }}
      >
        <Icon
          size={16}
          color={config.color}
          style={{ flexShrink: 0, marginTop: 2 }}
        />

        <div style={{ flex: 1, minWidth: 0 }}>
          <div
            style={{
              fontSize: 12,
              fontWeight: 600,
              color: theme.textPrimary,
              marginBottom: 2,
            }}
          >
            {issue.message}
          </div>

          {issue.description && (
            <div
              style={{
                fontSize: 11,
                color: theme.textSecondary,
                lineHeight: 1.4,
              }}
            >
              {issue.description}
            </div>
          )}

          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              marginTop: 6,
            }}
          >
            {issue.pieceName && (
              <span
                style={{
                  fontSize: 10,
                  padding: "2px 6px",
                  backgroundColor: theme.surface,
                  borderRadius: 4,
                  color: theme.textSecondary,
                }}
              >
                📐 {issue.pieceName}
              </span>
            )}

            {issue.location && (
              <span
                style={{
                  fontSize: 10,
                  padding: "2px 6px",
                  backgroundColor: theme.surface,
                  borderRadius: 4,
                  color: theme.textSecondary,
                  fontFamily: "monospace",
                }}
              >
                X:{issue.location.x.toFixed(1)} Y:{issue.location.y.toFixed(1)}
              </span>
            )}

            <span
              style={{
                fontSize: 10,
                padding: "2px 6px",
                backgroundColor: `${config.color}15`,
                color: config.color,
                borderRadius: 4,
                fontWeight: 600,
              }}
            >
              {issue.code}
            </span>
          </div>
        </div>

        {/* Ações */}
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: 4,
          }}
        >
          {issue.autoFixAvailable && (
            <motion.button
              whileHover={{ scale: 1.1 }}
              whileTap={{ scale: 0.9 }}
              onClick={(e) => {
                e.stopPropagation();
                onAutoFix?.(issue.id);
              }}
              style={{
                width: 24,
                height: 24,
                border: "none",
                borderRadius: 4,
                backgroundColor: theme.success,
                color: "#fff",
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
              title="Auto-corrigir"
            >
              <RefreshCw size={12} />
            </motion.button>
          )}

          <motion.button
            whileHover={{ scale: 1.1 }}
            whileTap={{ scale: 0.9 }}
            onClick={(e) => {
              e.stopPropagation();
              handleToggleHidden(issue.id);
            }}
            style={{
              width: 24,
              height: 24,
              border: "none",
              borderRadius: 4,
              backgroundColor: theme.inputBackground,
              color: theme.textSecondary,
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
            title={isHidden ? "Mostrar" : "Ignorar"}
          >
            {isHidden ? <Eye size={12} /> : <EyeOff size={12} />}
          </motion.button>
        </div>
      </motion.div>
    );
  };

  return (
    <div
      style={{
        width: 320,
        maxHeight: "calc(100vh - 200px)",
        display: "flex",
        flexDirection: "column",
        backgroundColor: theme.surface,
        border: `1px solid ${theme.border}`,
        borderRadius: 12,
        overflow: "hidden",
      }}
    >
      {/* Header */}
      <div
        style={{
          padding: "12px 16px",
          borderBottom: `1px solid ${theme.border}`,
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          {hasIssues ? (
            <AlertTriangle
              size={18}
              color={errorCount > 0 ? theme.danger : theme.warning}
            />
          ) : (
            <CheckCircle size={18} color={theme.success} />
          )}
          <span
            style={{
              fontSize: 14,
              fontWeight: 700,
              color: theme.textPrimary,
            }}
          >
            Validações
          </span>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          {/* Contadores */}
          {errorCount > 0 && (
            <span
              style={{
                fontSize: 11,
                padding: "2px 8px",
                backgroundColor: `${theme.danger}20`,
                color: theme.danger,
                borderRadius: 10,
                fontWeight: 600,
              }}
            >
              {errorCount} erros
            </span>
          )}
          {warningCount > 0 && (
            <span
              style={{
                fontSize: 11,
                padding: "2px 8px",
                backgroundColor: `${theme.warning}20`,
                color: theme.warning,
                borderRadius: 10,
                fontWeight: 600,
              }}
            >
              {warningCount} avisos
            </span>
          )}

          {/* Refresh */}
          <motion.button
            whileHover={{ scale: 1.1 }}
            whileTap={{ scale: 0.9 }}
            onClick={onRefresh}
            disabled={isValidating}
            style={{
              width: 28,
              height: 28,
              border: "none",
              borderRadius: 6,
              backgroundColor: theme.inputBackground,
              color: theme.textSecondary,
              cursor: isValidating ? "wait" : "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <RefreshCw
              size={14}
              className={isValidating ? "spin" : ""}
              style={{
                animation: isValidating ? "spin 1s linear infinite" : "none",
              }}
            />
          </motion.button>
        </div>
      </div>

      {/* Status bar */}
      {!hasIssues && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          style={{
            padding: "16px",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: 8,
            color: theme.success,
          }}
        >
          <CheckCircle size={32} />
          <span style={{ fontSize: 13, fontWeight: 600 }}>Tudo validado!</span>
          <span
            style={{
              fontSize: 11,
              color: theme.textSecondary,
              textAlign: "center",
            }}
          >
            A geometria está pronta para gerar o G-code.
          </span>
        </motion.div>
      )}

      {/* Issues por categoria */}
      <div
        style={{
          flex: 1,
          overflowY: "auto",
          padding: hasIssues ? "12px" : 0,
        }}
      >
        {Object.entries(groupedIssues).map(([category, categoryIssues]) => {
          const catConfig = categoryConfig[category as IssueCategory];
          const CatIcon = catConfig.icon;
          const isExpanded =
            expandedCategory === category || expandedCategory === null;
          const issuesArray = categoryIssues as ValidationIssue[];
          const categoryErrorCount = issuesArray.filter(
            (i) => i.severity === "error",
          ).length;
          const categoryWarningCount = issuesArray.filter(
            (i) => i.severity === "warning",
          ).length;

          return (
            <div key={category} style={{ marginBottom: 12 }}>
              {/* Cabeçalho da categoria */}
              <motion.div
                whileHover={{ backgroundColor: theme.inputBackground }}
                onClick={() =>
                  setExpandedCategory(
                    expandedCategory === category
                      ? null
                      : (category as IssueCategory),
                  )
                }
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  padding: "8px 10px",
                  borderRadius: 8,
                  cursor: "pointer",
                  marginBottom: 8,
                }}
              >
                {isExpanded ? (
                  <ChevronDown size={14} color={theme.textSecondary} />
                ) : (
                  <ChevronRight size={14} color={theme.textSecondary} />
                )}
                <CatIcon size={14} color={theme.accentPrimary} />
                <span
                  style={{
                    flex: 1,
                    fontSize: 12,
                    fontWeight: 600,
                    color: theme.textPrimary,
                  }}
                >
                  {catConfig.label}
                </span>

                {/* Badges */}
                <div style={{ display: "flex", gap: 4 }}>
                  {categoryErrorCount > 0 && (
                    <span
                      style={{
                        width: 18,
                        height: 18,
                        borderRadius: 9,
                        backgroundColor: theme.danger,
                        color: "#fff",
                        fontSize: 10,
                        fontWeight: 700,
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                      }}
                    >
                      {categoryErrorCount}
                    </span>
                  )}
                  {categoryWarningCount > 0 && (
                    <span
                      style={{
                        width: 18,
                        height: 18,
                        borderRadius: 9,
                        backgroundColor: theme.warning,
                        color: "#fff",
                        fontSize: 10,
                        fontWeight: 700,
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                      }}
                    >
                      {categoryWarningCount}
                    </span>
                  )}
                </div>
              </motion.div>

              {/* Issues da categoria */}
              <AnimatePresence>
                {isExpanded && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: "auto" }}
                    exit={{ opacity: 0, height: 0 }}
                    style={{ paddingLeft: 8 }}
                  >
                    {issuesArray
                      .sort((a, b) => {
                        const order: IssueSeverity[] = [
                          "error",
                          "warning",
                          "info",
                          "success",
                        ];
                        return (
                          order.indexOf(a.severity) - order.indexOf(b.severity)
                        );
                      })
                      .map(renderIssue)}
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          );
        })}
      </div>

      {/* Footer com ações */}
      {hasIssues && (
        <div
          style={{
            padding: "12px 16px",
            borderTop: `1px solid ${theme.border}`,
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={() => setShowAllIssues(!showAllIssues)}
            style={{
              padding: "6px 12px",
              border: `1px solid ${theme.border}`,
              borderRadius: 6,
              backgroundColor: theme.inputBackground,
              color: theme.textSecondary,
              fontSize: 11,
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: 6,
            }}
          >
            {showAllIssues ? <EyeOff size={12} /> : <Eye size={12} />}
            {showAllIssues ? "Esconder ignorados" : "Mostrar todos"}
          </motion.button>

          {issues.some((i) => i.autoFixAvailable) && (
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => {
                issues
                  .filter((i) => i.autoFixAvailable)
                  .forEach((i) => onAutoFix?.(i.id));
              }}
              style={{
                padding: "6px 12px",
                border: "none",
                borderRadius: 6,
                backgroundColor: theme.success,
                color: "#fff",
                fontSize: 11,
                fontWeight: 600,
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                gap: 6,
              }}
            >
              <RefreshCw size={12} />
              Auto-corrigir tudo
            </motion.button>
          )}
        </div>
      )}

      <style>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
};

export default CncValidationPanel;
