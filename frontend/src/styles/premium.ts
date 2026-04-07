/**
 * ENGENHARIA CAD - Sistema de Design Premium v2.0
 * Estilos globais para consistência visual em todas as páginas
 */

export const COLORS = {
  // Primary
  primary: "#00A1FF",
  primaryDark: "#0077CC",
  primaryLight: "#33B4FF",
  primaryGlow: "rgba(0,161,255,0.4)",
  
  // Backgrounds
  bgDark: "#030508",
  bgPrimary: "#050709", 
  bgSurface: "#0a0d12",
  bgPanel: "#0d1117",
  bgCard: "#111620",
  bgElevated: "#161d28",
  
  // Borders
  border: "#1a2030",
  borderLight: "#232d3f",
  borderAccent: "#00A1FF40",
  
  // Text
  textPrimary: "#FFFFFF",
  textSecondary: "#8899AA",
  textTertiary: "#556677",
  textMuted: "#334455",
  
  // Semantic
  success: "#10B981",
  warning: "#F59E0B",
  danger: "#EF4444",
  info: "#8B5CF6",
  
  // Gradients
  gradientPrimary: "linear-gradient(135deg, #00A1FF 0%, #0077CC 100%)",
  gradientDark: "linear-gradient(135deg, #030508 0%, #0a1628 40%, #071020 70%, #030508 100%)",
  gradientCard: "linear-gradient(180deg, rgba(0,161,255,0.05) 0%, transparent 100%)",
};

export const SHADOWS = {
  sm: "0 2px 8px rgba(0,0,0,0.3)",
  md: "0 4px 16px rgba(0,0,0,0.4)",
  lg: "0 8px 32px rgba(0,0,0,0.5)",
  glow: "0 0 20px rgba(0,161,255,0.3)",
  glowStrong: "0 0 40px rgba(0,161,255,0.4)",
  card: "0 4px 20px rgba(0,0,0,0.3), 0 0 40px rgba(0,161,255,0.05)",
};

export const TYPOGRAPHY = {
  fontFamily: "'Inter', 'Segoe UI', Roboto, -apple-system, sans-serif",
  letterSpacing: {
    tight: "-0.02em",
    normal: "0",
    wide: "0.05em",
    wider: "0.1em",
    widest: "0.15em",
  },
};

// Componentes de estilo reutilizáveis
export const premiumStyles = {
  // Container principal com fundo animado
  pageContainer: {
    minHeight: "100vh",
    background: COLORS.gradientDark,
    fontFamily: TYPOGRAPHY.fontFamily,
    color: COLORS.textPrimary,
    position: "relative" as const,
    overflow: "hidden",
  },
  
  // Content wrapper (garante que elementos não saiam)
  contentWrapper: {
    position: "relative" as const,
    width: "100%",
    maxWidth: "1600px",
    margin: "0 auto",
    padding: "24px",
    boxSizing: "border-box" as const,
    overflow: "hidden",
  },
  
  // Main scrollable area
  mainContent: {
    position: "relative" as const,
    flex: 1,
    minHeight: 0,
    overflowY: "auto" as const,
    overflowX: "hidden" as const,
    padding: "24px",
    boxSizing: "border-box" as const,
  },
  
  // Background com grid
  gridOverlay: {
    position: "absolute" as const,
    inset: 0,
    backgroundImage: `
      linear-gradient(rgba(0,161,255,0.03) 1px, transparent 1px),
      linear-gradient(90deg, rgba(0,161,255,0.03) 1px, transparent 1px)
    `,
    backgroundSize: "60px 60px",
    opacity: 0.5,
    pointerEvents: "none" as const,
  },
  
  // Card premium
  card: {
    background: COLORS.bgCard,
    border: `1px solid ${COLORS.border}`,
    borderRadius: "12px",
    boxShadow: SHADOWS.card,
    padding: "24px",
    position: "relative" as const,
    overflow: "hidden",
    maxWidth: "100%",
    boxSizing: "border-box" as const,
  },
  
  // Card com glow
  cardGlow: {
    background: COLORS.bgCard,
    border: `1px solid ${COLORS.borderAccent}`,
    borderRadius: "16px",
    boxShadow: `${SHADOWS.lg}, ${SHADOWS.glow}`,
    padding: "32px",
    position: "relative" as const,
  },
  
  // Header de seção
  sectionHeader: {
    display: "flex",
    alignItems: "center",
    gap: "12px",
    marginBottom: "24px",
  },
  
  sectionIcon: {
    width: "48px",
    height: "48px",
    borderRadius: "12px",
    background: COLORS.gradientPrimary,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    color: "#FFF",
    boxShadow: SHADOWS.glow,
  },
  
  sectionTitle: {
    fontSize: "24px",
    fontWeight: 700,
    color: COLORS.textPrimary,
    margin: 0,
    letterSpacing: TYPOGRAPHY.letterSpacing.tight,
  },
  
  sectionSubtitle: {
    fontSize: "14px",
    color: COLORS.textSecondary,
    margin: 0,
  },
  
  // Botão primário
  button: {
    padding: "14px 28px",
    background: COLORS.gradientPrimary,
    border: "none",
    borderRadius: "8px",
    color: "#FFF",
    fontSize: "14px",
    fontWeight: 600,
    letterSpacing: TYPOGRAPHY.letterSpacing.wide,
    cursor: "pointer",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    gap: "10px",
    boxShadow: SHADOWS.glow,
    transition: "all 0.2s ease",
  },
  
  // Botão secundário
  buttonSecondary: {
    padding: "14px 28px",
    background: "transparent",
    border: `1px solid ${COLORS.border}`,
    borderRadius: "8px",
    color: COLORS.textSecondary,
    fontSize: "14px",
    fontWeight: 500,
    cursor: "pointer",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    gap: "10px",
    transition: "all 0.2s ease",
  },
  
  // Input
  input: {
    width: "100%",
    padding: "14px 16px",
    background: COLORS.bgSurface,
    border: `1px solid ${COLORS.border}`,
    borderRadius: "8px",
    color: COLORS.textPrimary,
    fontSize: "14px",
    outline: "none",
    transition: "all 0.2s ease",
  },
  
  // Label
  label: {
    display: "block",
    fontSize: "11px",
    fontWeight: 600,
    color: COLORS.textTertiary,
    letterSpacing: TYPOGRAPHY.letterSpacing.wider,
    marginBottom: "8px",
    textTransform: "uppercase" as const,
  },
  
  // Badge/Tag
  badge: {
    padding: "4px 12px",
    borderRadius: "20px",
    fontSize: "11px",
    fontWeight: 600,
    letterSpacing: TYPOGRAPHY.letterSpacing.wide,
    textTransform: "uppercase" as const,
  },
  
  // Status indicator
  statusDot: {
    width: "8px",
    height: "8px",
    borderRadius: "50%",
    background: COLORS.success,
    boxShadow: `0 0 8px ${COLORS.success}`,
  },
  
  // Divider
  divider: {
    height: "1px",
    background: COLORS.border,
    margin: "24px 0",
  },
  
  // Stats number
  statValue: {
    fontSize: "36px",
    fontWeight: 800,
    color: COLORS.primary,
    letterSpacing: TYPOGRAPHY.letterSpacing.tight,
  },
  
  statLabel: {
    fontSize: "12px",
    color: COLORS.textTertiary,
    letterSpacing: TYPOGRAPHY.letterSpacing.wider,
    textTransform: "uppercase" as const,
  },
  
  // Accent line (top of cards)
  accentLine: {
    position: "absolute" as const,
    top: 0,
    left: 0,
    right: 0,
    height: "3px",
    background: COLORS.gradientPrimary,
    transformOrigin: "left",
  },
  
  // Glow effect behind cards
  glowEffect: {
    position: "absolute" as const,
    top: "-50%",
    left: "-50%",
    width: "200%",
    height: "200%",
    background: `radial-gradient(circle, ${COLORS.primaryGlow} 0%, transparent 50%)`,
    opacity: 0.15,
    pointerEvents: "none" as const,
  },
  
  // Grid responsivo para cards
  gridResponsive: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
    gap: "16px",
    width: "100%",
    maxWidth: "100%",
    boxSizing: "border-box" as const,
  },
  
  // Grid 4 colunas (com fallback responsivo)
  grid4Cols: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
    gap: "16px",
    width: "100%",
    maxWidth: "100%",
  },
  
  // Grid 3 colunas (com fallback responsivo)
  grid3Cols: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))",
    gap: "20px",
    width: "100%",
    maxWidth: "100%",
  },
  
  // Grid 2 colunas
  grid2Cols: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(350px, 1fr))",
    gap: "24px",
    width: "100%",
    maxWidth: "100%",
  },
  
  // Flex wrap container
  flexWrap: {
    display: "flex",
    flexWrap: "wrap" as const,
    gap: "16px",
    width: "100%",
    maxWidth: "100%",
  },
};

// Função para criar variantes de hover
export const createHoverStyles = (baseColor: string) => ({
  borderColor: `${baseColor}60`,
  boxShadow: `0 8px 32px ${baseColor}20, 0 0 20px ${baseColor}15`,
  transform: "translateY(-2px)",
});

// Animações keyframes (para uso com framer-motion)
export const animations = {
  fadeInUp: {
    initial: { opacity: 0, y: 20 },
    animate: { opacity: 1, y: 0 },
    transition: { duration: 0.5 },
  },
  fadeInLeft: {
    initial: { opacity: 0, x: -30 },
    animate: { opacity: 1, x: 0 },
    transition: { duration: 0.5 },
  },
  fadeInRight: {
    initial: { opacity: 0, x: 30 },
    animate: { opacity: 1, x: 0 },
    transition: { duration: 0.5 },
  },
  scaleIn: {
    initial: { opacity: 0, scale: 0.9 },
    animate: { opacity: 1, scale: 1 },
    transition: { duration: 0.3 },
  },
  slideUp: {
    initial: { y: "100%" },
    animate: { y: 0 },
    transition: { type: "spring", stiffness: 300, damping: 30 },
  },
  pulse: {
    animate: { scale: [1, 1.05, 1] },
    transition: { duration: 2, repeat: Infinity },
  },
  glow: {
    animate: { 
      boxShadow: [
        `0 0 20px ${COLORS.primaryGlow}`,
        `0 0 40px ${COLORS.primaryGlow}`,
        `0 0 20px ${COLORS.primaryGlow}`,
      ],
    },
    transition: { duration: 2, repeat: Infinity },
  },
};

export default { COLORS, SHADOWS, TYPOGRAPHY, premiumStyles, animations };
