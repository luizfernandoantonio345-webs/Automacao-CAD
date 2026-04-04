/**
 * ═══════════════════════════════════════════════════════════════════════════════
 * CncStatisticsPanel - Painel de Estatísticas para Corte CNC
 * ═══════════════════════════════════════════════════════════════════════════════
 *
 * Mostra em tempo real:
 * - Tempo estimado de corte
 * - Custo total
 * - Peso do material
 * - Perímetro de corte
 * - Número de peças
 * - Aproveitamento da chapa
 */

import React from "react";
import { motion } from "framer-motion";
import {
  Clock,
  DollarSign,
  Ruler,
  Scale,
  Layers,
  Percent,
  Flame,
  Zap,
  Target,
  Box,
  TrendingUp,
  AlertTriangle,
} from "lucide-react";

interface CuttingConfig {
  material: string;
  thickness: number;
  amperage: number;
  cuttingSpeed: number;
}

interface ToolpathStats {
  totalCuts: number;
  cuttingLength: number;
  rapidLength: number;
  estimatedTime: number;
  internalContours: number;
  externalContours: number;
}

interface CostEstimate {
  materialCost: number;
  cuttingTimeCost: number;
  totalCost: number;
  scrapPercentage: number;
}

interface NestingResult {
  efficiency: number;
  totalPieces: number;
  unplacedPieces: number;
  usedArea: number;
  wasteArea: number;
}

interface CncStatisticsPanelProps {
  config: CuttingConfig;
  stats?: ToolpathStats;
  costEstimate?: CostEstimate;
  nestingResult?: NestingResult;
  sheetWidth?: number;
  sheetHeight?: number;
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

// Materiais e densidades
const MATERIAL_INFO: Record<
  string,
  { name: string; density: number; color: string }
> = {
  mild_steel: { name: "Aço Carbono", density: 7.85, color: "#6B7280" },
  stainless: { name: "Aço Inox", density: 8.0, color: "#9CA3AF" },
  aluminum: { name: "Alumínio", density: 2.7, color: "#D1D5DB" },
  copper: { name: "Cobre", density: 8.96, color: "#F59E0B" },
  brass: { name: "Latão", density: 8.5, color: "#EAB308" },
  galvanized: { name: "Galvanizado", density: 7.85, color: "#71717A" },
};

const CncStatisticsPanel: React.FC<CncStatisticsPanelProps> = ({
  config,
  stats,
  costEstimate,
  nestingResult,
  sheetWidth = 3000,
  sheetHeight = 1500,
  theme,
}) => {
  // Calcular peso estimado da chapa
  const sheetArea = (sheetWidth / 1000) * (sheetHeight / 1000); // m²
  const materialInfo =
    MATERIAL_INFO[config.material] || MATERIAL_INFO.mild_steel;
  const sheetWeight =
    sheetArea * (config.thickness / 1000) * materialInfo.density * 1000; // kg

  // Formatar tempo
  const formatTime = (seconds: number): string => {
    if (seconds < 60) return `${Math.round(seconds)}s`;
    const minutes = Math.floor(seconds / 60);
    const secs = Math.round(seconds % 60);
    if (minutes < 60) return `${minutes}min ${secs}s`;
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return `${hours}h ${mins}min`;
  };

  // Formatar número
  const formatNumber = (num: number, decimals: number = 1): string => {
    return num.toLocaleString("pt-BR", {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    });
  };

  // Card style
  const cardStyle: React.CSSProperties = {
    backgroundColor: theme.surface,
    border: `1px solid ${theme.border}`,
    borderRadius: 10,
    padding: "12px 16px",
    display: "flex",
    flexDirection: "column",
    gap: 4,
  };

  const iconBoxStyle = (color: string): React.CSSProperties => ({
    width: 36,
    height: 36,
    borderRadius: 8,
    backgroundColor: `${color}20`,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    flexShrink: 0,
  });

  const labelStyle: React.CSSProperties = {
    fontSize: 11,
    color: theme.textSecondary,
    textTransform: "uppercase",
    letterSpacing: 0.5,
    fontWeight: 600,
  };

  const valueStyle: React.CSSProperties = {
    fontSize: 20,
    fontWeight: 700,
    color: theme.textPrimary,
    fontFamily: "monospace",
  };

  const unitStyle: React.CSSProperties = {
    fontSize: 12,
    color: theme.textSecondary,
    marginLeft: 4,
  };

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 12,
        width: 280,
        maxHeight: "calc(100vh - 200px)",
        overflowY: "auto",
      }}
    >
      {/* Header */}
      <div
        style={{
          padding: "12px 16px",
          backgroundColor: theme.accentPrimary,
          borderRadius: 10,
          color: "#fff",
        }}
      >
        <div style={{ fontSize: 14, fontWeight: 700, marginBottom: 4 }}>
          📊 Estatísticas do Corte
        </div>
        <div style={{ fontSize: 11, opacity: 0.8 }}>
          Material: {materialInfo.name} {config.thickness}mm
        </div>
      </div>

      {/* Tempo Estimado */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        style={cardStyle}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div style={iconBoxStyle(theme.accentPrimary)}>
            <Clock size={18} color={theme.accentPrimary} />
          </div>
          <div>
            <div style={labelStyle}>Tempo Estimado</div>
            <div style={valueStyle}>
              {stats ? formatTime(stats.estimatedTime) : "--"}
            </div>
          </div>
        </div>
        {stats && (
          <div
            style={{ fontSize: 11, color: theme.textSecondary, marginTop: 4 }}
          >
            Corte:{" "}
            {formatTime((stats.cuttingLength / config.cuttingSpeed) * 60)} |
            Rapids: {formatTime((stats.rapidLength / 10000) * 60)}
          </div>
        )}
      </motion.div>

      {/* Custo Total */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.05 }}
        style={cardStyle}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div style={iconBoxStyle(theme.success)}>
            <DollarSign size={18} color={theme.success} />
          </div>
          <div>
            <div style={labelStyle}>Custo Total</div>
            <div style={valueStyle}>
              R$ {costEstimate ? formatNumber(costEstimate.totalCost, 2) : "--"}
            </div>
          </div>
        </div>
        {costEstimate && (
          <div
            style={{ fontSize: 11, color: theme.textSecondary, marginTop: 4 }}
          >
            Material: R$ {formatNumber(costEstimate.materialCost, 2)} | Hora
            máq.: R$ {formatNumber(costEstimate.cuttingTimeCost, 2)}
          </div>
        )}
      </motion.div>

      {/* Perímetro de Corte */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        style={cardStyle}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div style={iconBoxStyle(theme.warning)}>
            <Ruler size={18} color={theme.warning} />
          </div>
          <div>
            <div style={labelStyle}>Perímetro de Corte</div>
            <div style={valueStyle}>
              {stats ? formatNumber(stats.cuttingLength / 1000, 2) : "--"}
              <span style={unitStyle}>m</span>
            </div>
          </div>
        </div>
        {stats && (
          <div
            style={{ fontSize: 11, color: theme.textSecondary, marginTop: 4 }}
          >
            {stats.totalCuts} cortes | {stats.internalContours} internos,{" "}
            {stats.externalContours} externos
          </div>
        )}
      </motion.div>

      {/* Deslocamento Rápido */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.15 }}
        style={cardStyle}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div style={iconBoxStyle(theme.danger)}>
            <Zap size={18} color={theme.danger} />
          </div>
          <div>
            <div style={labelStyle}>Deslocamento Rápido</div>
            <div style={valueStyle}>
              {stats ? formatNumber(stats.rapidLength / 1000, 2) : "--"}
              <span style={unitStyle}>m</span>
            </div>
          </div>
        </div>
      </motion.div>

      {/* Peso Estimado */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        style={cardStyle}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div style={iconBoxStyle("#8B5CF6")}>
            <Scale size={18} color="#8B5CF6" />
          </div>
          <div>
            <div style={labelStyle}>Peso da Chapa</div>
            <div style={valueStyle}>
              {formatNumber(sheetWeight, 1)}
              <span style={unitStyle}>kg</span>
            </div>
          </div>
        </div>
        <div style={{ fontSize: 11, color: theme.textSecondary, marginTop: 4 }}>
          Chapa: {sheetWidth}x{sheetHeight}mm | Densidade:{" "}
          {materialInfo.density} g/cm³
        </div>
      </motion.div>

      {/* Nesting Results */}
      {nestingResult && (
        <>
          <div
            style={{
              height: 1,
              backgroundColor: theme.border,
              margin: "4px 0",
            }}
          />

          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.25 }}
            style={{
              ...cardStyle,
              border: `1px solid ${nestingResult.efficiency >= 70 ? theme.success : theme.warning}40`,
              backgroundColor: `${nestingResult.efficiency >= 70 ? theme.success : theme.warning}08`,
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <div
                style={iconBoxStyle(
                  nestingResult.efficiency >= 70
                    ? theme.success
                    : theme.warning,
                )}
              >
                <Percent
                  size={18}
                  color={
                    nestingResult.efficiency >= 70
                      ? theme.success
                      : theme.warning
                  }
                />
              </div>
              <div>
                <div style={labelStyle}>Aproveitamento</div>
                <div
                  style={{
                    ...valueStyle,
                    color:
                      nestingResult.efficiency >= 70
                        ? theme.success
                        : theme.warning,
                  }}
                >
                  {formatNumber(nestingResult.efficiency, 1)}%
                </div>
              </div>
            </div>

            {/* Barra de progresso */}
            <div
              style={{
                height: 6,
                backgroundColor: theme.border,
                borderRadius: 3,
                overflow: "hidden",
                marginTop: 8,
              }}
            >
              <div
                style={{
                  height: "100%",
                  width: `${nestingResult.efficiency}%`,
                  backgroundColor:
                    nestingResult.efficiency >= 70
                      ? theme.success
                      : theme.warning,
                  borderRadius: 3,
                }}
              />
            </div>

            <div
              style={{ fontSize: 11, color: theme.textSecondary, marginTop: 4 }}
            >
              Usado: {formatNumber(nestingResult.usedArea / 1000000, 2)}m² |
              Sobra: {formatNumber(nestingResult.wasteArea / 1000000, 2)}m²
            </div>
          </motion.div>

          {/* Peças */}
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            style={cardStyle}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <div style={iconBoxStyle(theme.accentPrimary)}>
                <Layers size={18} color={theme.accentPrimary} />
              </div>
              <div>
                <div style={labelStyle}>Peças Posicionadas</div>
                <div style={valueStyle}>
                  {nestingResult.totalPieces}
                  {nestingResult.unplacedPieces > 0 && (
                    <span
                      style={{
                        fontSize: 14,
                        color: theme.danger,
                        marginLeft: 8,
                      }}
                    >
                      (+{nestingResult.unplacedPieces} sem espaço)
                    </span>
                  )}
                </div>
              </div>
            </div>
          </motion.div>
        </>
      )}

      {/* Warnings */}
      {costEstimate && costEstimate.scrapPercentage > 15 && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          style={{
            ...cardStyle,
            backgroundColor: `${theme.warning}15`,
            border: `1px solid ${theme.warning}40`,
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <AlertTriangle size={16} color={theme.warning} />
            <span
              style={{ fontSize: 12, color: theme.warning, fontWeight: 600 }}
            >
              Alto percentual de perda (
              {formatNumber(costEstimate.scrapPercentage)}%)
            </span>
          </div>
          <div
            style={{ fontSize: 11, color: theme.textSecondary, marginTop: 4 }}
          >
            Considere otimizar o nesting ou adicionar peças menores.
          </div>
        </motion.div>
      )}

      {/* Parâmetros atuais */}
      <div
        style={{
          ...cardStyle,
          backgroundColor: theme.inputBackground,
          marginTop: 8,
        }}
      >
        <div style={{ ...labelStyle, marginBottom: 8 }}>Parâmetros Ativos</div>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: 8,
            fontSize: 12,
          }}
        >
          <div>
            <span style={{ color: theme.textSecondary }}>Amperagem:</span>
            <span
              style={{
                color: theme.textPrimary,
                marginLeft: 4,
                fontWeight: 600,
              }}
            >
              {config.amperage}A
            </span>
          </div>
          <div>
            <span style={{ color: theme.textSecondary }}>Velocidade:</span>
            <span
              style={{
                color: theme.textPrimary,
                marginLeft: 4,
                fontWeight: 600,
              }}
            >
              {config.cuttingSpeed} mm/min
            </span>
          </div>
          <div>
            <span style={{ color: theme.textSecondary }}>Espessura:</span>
            <span
              style={{
                color: theme.textPrimary,
                marginLeft: 4,
                fontWeight: 600,
              }}
            >
              {config.thickness}mm
            </span>
          </div>
          <div>
            <span style={{ color: theme.textSecondary }}>Material:</span>
            <span
              style={{
                color: theme.textPrimary,
                marginLeft: 4,
                fontWeight: 600,
              }}
            >
              {materialInfo.name}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CncStatisticsPanel;
