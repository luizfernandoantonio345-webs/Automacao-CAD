// ═══════════════════════════════════════════════════════════════════════════
// ENGENHARIA CAD — Estilos Compartilhados v2.0
// Padronização visual de headers, cards, tipografia e espaçamentos
// ═══════════════════════════════════════════════════════════════════════════

import React from "react";
import type { Theme } from "./theme";

// ─────────────────────────────────────────────────────────────────────────────
// TIPOGRAFIA
// ─────────────────────────────────────────────────────────────────────────────

export const typography = {
  fontFamily:
    "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",

  // Tamanhos de título padronizados
  h1: {
    fontSize: "1.75rem", // 28px - Título principal de página
    fontWeight: 700,
    letterSpacing: "0.02em",
    lineHeight: 1.2,
  },
  h2: {
    fontSize: "1.25rem", // 20px - Título de seção/card
    fontWeight: 600,
    letterSpacing: "0.015em",
    lineHeight: 1.3,
  },
  h3: {
    fontSize: "0.875rem", // 14px - Subtítulo/label
    fontWeight: 600,
    letterSpacing: "0.04em",
    lineHeight: 1.4,
    textTransform: "uppercase" as const,
  },
  body: {
    fontSize: "0.875rem", // 14px
    fontWeight: 400,
    lineHeight: 1.5,
  },
  small: {
    fontSize: "0.75rem", // 12px
    fontWeight: 400,
    lineHeight: 1.4,
  },
  caption: {
    fontSize: "0.625rem", // 10px
    fontWeight: 500,
    letterSpacing: "0.06em",
    lineHeight: 1.3,
    textTransform: "uppercase" as const,
  },
};

// ─────────────────────────────────────────────────────────────────────────────
// ESPAÇAMENTOS
// ─────────────────────────────────────────────────────────────────────────────

export const spacing = {
  xs: "4px",
  sm: "8px",
  md: "16px",
  lg: "24px",
  xl: "32px",
  xxl: "48px",

  // Padding de cards
  cardPadding: "24px",
  cardPaddingSm: "16px",

  // Gap entre elementos
  gap: "16px",
  gapSm: "8px",
  gapLg: "24px",
};

// ─────────────────────────────────────────────────────────────────────────────
// BORDER RADIUS
// ─────────────────────────────────────────────────────────────────────────────

export const radius = {
  sm: "4px",
  md: "8px",
  lg: "12px",
  xl: "16px",
  round: "50%",
};

// ─────────────────────────────────────────────────────────────────────────────
// SOMBRAS
// ─────────────────────────────────────────────────────────────────────────────

export const shadows = {
  card: "0 4px 20px rgba(0, 0, 0, 0.3)",
  cardHover: "0 8px 30px rgba(0, 0, 0, 0.4)",
  glow: (color: string) => `0 0 20px ${color}33`,
  inset: "inset 0 1px 3px rgba(0, 0, 0, 0.2)",
};

// ─────────────────────────────────────────────────────────────────────────────
// COMPONENTES - Funções que retornam estilos baseados no tema
// ─────────────────────────────────────────────────────────────────────────────

export const createStyles = (theme: Theme) => ({
  // Container de página
  pageContainer: {
    minHeight: "100vh",
    backgroundColor: theme.background,
    color: theme.textPrimary,
    fontFamily: typography.fontFamily,
    padding: spacing.lg,
  } as React.CSSProperties,

  // Header de página com título
  pageHeader: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: spacing.xl,
    paddingBottom: spacing.md,
    borderBottom: `1px solid ${theme.border}`,
  } as React.CSSProperties,

  // Título principal de página
  pageTitle: {
    ...typography.h1,
    color: theme.textPrimary,
    margin: 0,
    display: "flex",
    alignItems: "center",
    gap: spacing.sm,
  } as React.CSSProperties,

  // Subtítulo/descrição de página
  pageSubtitle: {
    ...typography.body,
    color: theme.textSecondary,
    marginTop: spacing.xs,
  } as React.CSSProperties,

  // Card padrão
  card: {
    backgroundColor: theme.surface,
    border: `1px solid ${theme.border}`,
    borderRadius: radius.lg,
    padding: spacing.cardPadding,
    boxShadow: shadows.card,
    transition: "box-shadow 0.2s ease, border-color 0.2s ease",
  } as React.CSSProperties,

  // Card com hover
  cardInteractive: {
    backgroundColor: theme.surface,
    border: `1px solid ${theme.border}`,
    borderRadius: radius.lg,
    padding: spacing.cardPadding,
    boxShadow: shadows.card,
    cursor: "pointer",
    transition: "all 0.2s ease",
  } as React.CSSProperties,

  // Card compacto (para métricas, etc)
  cardCompact: {
    backgroundColor: theme.surface,
    border: `1px solid ${theme.border}`,
    borderRadius: radius.md,
    padding: spacing.cardPaddingSm,
    boxShadow: shadows.card,
  } as React.CSSProperties,

  // Título de card/seção
  cardTitle: {
    ...typography.h3,
    color: theme.textSecondary,
    marginBottom: spacing.md,
    display: "flex",
    alignItems: "center",
    gap: spacing.sm,
  } as React.CSSProperties,

  // Grid de 2 colunas
  grid2: {
    display: "grid",
    gridTemplateColumns: "repeat(2, 1fr)",
    gap: spacing.lg,
  } as React.CSSProperties,

  // Grid de 3 colunas
  grid3: {
    display: "grid",
    gridTemplateColumns: "repeat(3, 1fr)",
    gap: spacing.lg,
  } as React.CSSProperties,

  // Grid de 4 colunas
  grid4: {
    display: "grid",
    gridTemplateColumns: "repeat(4, 1fr)",
    gap: spacing.md,
  } as React.CSSProperties,

  // Grid responsivo
  gridAuto: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
    gap: spacing.lg,
  } as React.CSSProperties,

  // Input/Select padrão
  input: {
    width: "100%",
    padding: `${spacing.sm} ${spacing.md}`,
    backgroundColor: theme.inputBackground,
    border: `1px solid ${theme.inputBorder}`,
    borderRadius: radius.md,
    color: theme.textPrimary,
    fontSize: typography.body.fontSize,
    fontFamily: typography.fontFamily,
    outline: "none",
    transition: "border-color 0.2s ease, box-shadow 0.2s ease",
  } as React.CSSProperties,

  // Label de input
  inputLabel: {
    ...typography.caption,
    color: theme.textSecondary,
    marginBottom: spacing.xs,
    display: "flex",
    alignItems: "center",
    gap: spacing.xs,
  } as React.CSSProperties,

  // Grupo de input (label + input)
  inputGroup: {
    marginBottom: spacing.md,
  } as React.CSSProperties,

  // Botão primário
  buttonPrimary: {
    display: "inline-flex",
    alignItems: "center",
    justifyContent: "center",
    gap: spacing.sm,
    padding: `${spacing.sm} ${spacing.lg}`,
    backgroundColor: theme.accentPrimary,
    color: "#FFFFFF",
    border: "none",
    borderRadius: radius.md,
    fontSize: typography.body.fontSize,
    fontWeight: 600,
    fontFamily: typography.fontFamily,
    cursor: "pointer",
    transition: "all 0.2s ease",
  } as React.CSSProperties,

  // Botão secundário (outline)
  buttonSecondary: {
    display: "inline-flex",
    alignItems: "center",
    justifyContent: "center",
    gap: spacing.sm,
    padding: `${spacing.sm} ${spacing.lg}`,
    backgroundColor: "transparent",
    color: theme.accentPrimary,
    border: `1px solid ${theme.accentPrimary}`,
    borderRadius: radius.md,
    fontSize: typography.body.fontSize,
    fontWeight: 600,
    fontFamily: typography.fontFamily,
    cursor: "pointer",
    transition: "all 0.2s ease",
  } as React.CSSProperties,

  // Tag/Badge
  tag: {
    display: "inline-flex",
    alignItems: "center",
    gap: spacing.xs,
    padding: `${spacing.xs} ${spacing.sm}`,
    backgroundColor: `${theme.accentPrimary}20`,
    color: theme.accentPrimary,
    borderRadius: radius.sm,
    fontSize: typography.small.fontSize,
    fontWeight: 500,
  } as React.CSSProperties,

  // Status indicator (bolinha)
  statusDot: (isActive: boolean) =>
    ({
      width: "10px",
      height: "10px",
      borderRadius: radius.round,
      backgroundColor: isActive ? theme.success : theme.danger,
      boxShadow: `0 0 8px ${isActive ? theme.success : theme.danger}`,
    }) as React.CSSProperties,

  // Divider horizontal
  divider: {
    height: "1px",
    backgroundColor: theme.border,
    margin: `${spacing.lg} 0`,
  } as React.CSSProperties,

  // Mensagem de erro
  errorBox: {
    display: "flex",
    alignItems: "center",
    gap: spacing.sm,
    padding: spacing.md,
    backgroundColor: `${theme.danger}15`,
    border: `1px solid ${theme.danger}40`,
    borderRadius: radius.md,
    color: theme.danger,
    fontSize: typography.body.fontSize,
  } as React.CSSProperties,

  // Mensagem de sucesso
  successBox: {
    display: "flex",
    alignItems: "center",
    gap: spacing.sm,
    padding: spacing.md,
    backgroundColor: `${theme.success}15`,
    border: `1px solid ${theme.success}40`,
    borderRadius: radius.md,
    color: theme.success,
    fontSize: typography.body.fontSize,
  } as React.CSSProperties,

  // Texto de loading
  loadingText: {
    ...typography.small,
    color: theme.textTertiary,
    display: "flex",
    alignItems: "center",
    gap: spacing.sm,
  } as React.CSSProperties,

  // Row com hover
  listRow: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    padding: spacing.sm,
    borderRadius: radius.sm,
    transition: "background-color 0.15s ease",
    cursor: "pointer",
  } as React.CSSProperties,

  // Valor de métrica grande
  metricValue: {
    fontSize: "2rem",
    fontWeight: 700,
    color: theme.accentPrimary,
    lineHeight: 1,
  } as React.CSSProperties,

  // Label de métrica
  metricLabel: {
    ...typography.caption,
    color: theme.textTertiary,
    marginTop: spacing.xs,
  } as React.CSSProperties,

  // Ícone decorativo
  iconBox: (color: string) =>
    ({
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      width: "40px",
      height: "40px",
      borderRadius: radius.md,
      backgroundColor: `${color}15`,
      color: color,
    }) as React.CSSProperties,

  // Flex row com align center
  flexRow: {
    display: "flex",
    alignItems: "center",
    gap: spacing.md,
  } as React.CSSProperties,

  // Flex col
  flexCol: {
    display: "flex",
    flexDirection: "column" as const,
    gap: spacing.sm,
  } as React.CSSProperties,

  // Scroll container
  scrollContainer: {
    maxHeight: "400px",
    overflowY: "auto" as const,
    paddingRight: spacing.sm,
  } as React.CSSProperties,
});

// ─────────────────────────────────────────────────────────────────────────────
// ANIMAÇÕES (para framer-motion)
// ─────────────────────────────────────────────────────────────────────────────

export const animations = {
  fadeIn: {
    initial: { opacity: 0 },
    animate: { opacity: 1 },
    transition: { duration: 0.3 },
  },
  slideUp: {
    initial: { opacity: 0, y: 20 },
    animate: { opacity: 1, y: 0 },
    transition: { duration: 0.4 },
  },
  slideDown: {
    initial: { opacity: 0, y: -10 },
    animate: { opacity: 1, y: 0 },
    transition: { duration: 0.3 },
  },
  scaleIn: {
    initial: { opacity: 0, scale: 0.95 },
    animate: { opacity: 1, scale: 1 },
    transition: { duration: 0.2 },
  },
  staggerChildren: {
    animate: {
      transition: {
        staggerChildren: 0.1,
      },
    },
  },
};

export default createStyles;
