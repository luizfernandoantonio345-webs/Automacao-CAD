/**
 * Design Tokens — AutomAção CAD Enterprise v2.0
 *
 * Sistema de tokens unificado para consistência visual.
 * Inspirado em: Linear, Vercel, Stripe
 *
 * @usage import { colors, spacing, radius, shadows } from '@/design/tokens';
 */

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// CORES — Paleta Enterprise Luxury
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

export const colors = {
  // Backgrounds (3-level depth system)
  dark: {
    base: "#080B12", // Deepest black - page bg
    surface: "#0D1321", // Cards, panels
    elevated: "#141B2D", // Modals, dropdowns, hovers
    subtle: "#1A2438", // Hover states on surface
  },

  // Primary Brand — Tech Blue
  primary: {
    50: "#E6F4FF",
    100: "#B3DFFF",
    200: "#80CAFF",
    300: "#4DB5FF",
    400: "#1AA0FF",
    500: "#00A1FF", // Main accent
    600: "#0081CC",
    700: "#006199",
    800: "#004066",
    900: "#002033",
    DEFAULT: "#00A1FF",
    glow: "rgba(0, 161, 255, 0.4)",
    soft: "rgba(0, 161, 255, 0.12)",
  },

  // Secondary — Indigo (user choice)
  secondary: {
    50: "#EEF2FF",
    100: "#E0E7FF",
    200: "#C7D2FE",
    300: "#A5B4FC",
    400: "#818CF8",
    500: "#6366F1", // Main secondary
    600: "#4F46E5",
    700: "#4338CA",
    800: "#3730A3",
    900: "#312E81",
    DEFAULT: "#6366F1",
    glow: "rgba(99, 102, 241, 0.4)",
    soft: "rgba(99, 102, 241, 0.12)",
  },

  // Premium Gold — For badges, premium features
  gold: {
    50: "#FFF9E6",
    100: "#FFF0B3",
    200: "#FFE680",
    300: "#FFDC4D",
    400: "#FFD21A",
    500: "#D4AF37", // Classic gold
    600: "#B8860B",
    700: "#8B6914",
    800: "#5C4A0F",
    900: "#2E2507",
    DEFAULT: "#D4AF37",
    glow: "rgba(212, 175, 55, 0.4)",
    soft: "rgba(212, 175, 55, 0.12)",
  },

  // Semantic Colors
  success: {
    50: "#ECFDF5",
    100: "#D1FAE5",
    200: "#A7F3D0",
    300: "#6EE7B7",
    400: "#34D399",
    500: "#10B981",
    600: "#059669",
    700: "#047857",
    DEFAULT: "#10B981",
    glow: "rgba(16, 185, 129, 0.4)",
    soft: "rgba(16, 185, 129, 0.12)",
  },

  warning: {
    50: "#FFFBEB",
    100: "#FEF3C7",
    200: "#FDE68A",
    300: "#FCD34D",
    400: "#FBBF24",
    500: "#F59E0B",
    600: "#D97706",
    700: "#B45309",
    DEFAULT: "#F59E0B",
    glow: "rgba(245, 158, 11, 0.4)",
    soft: "rgba(245, 158, 11, 0.12)",
  },

  danger: {
    50: "#FEF2F2",
    100: "#FEE2E2",
    200: "#FECACA",
    300: "#FCA5A5",
    400: "#F87171",
    500: "#EF4444",
    600: "#DC2626",
    700: "#B91C1C",
    DEFAULT: "#EF4444",
    glow: "rgba(239, 68, 68, 0.4)",
    soft: "rgba(239, 68, 68, 0.12)",
  },

  // Text Colors
  text: {
    primary: "#F8FAFC", // White-ish for dark mode
    secondary: "#94A3B8", // Muted
    tertiary: "#64748B", // Even more muted
    disabled: "#475569", // Disabled state
    inverse: "#0F172A", // For light backgrounds
  },

  // Border Colors
  border: {
    subtle: "rgba(255, 255, 255, 0.06)",
    default: "rgba(255, 255, 255, 0.10)",
    strong: "rgba(255, 255, 255, 0.16)",
    focus: "#00A1FF",
  },

  // CAD-specific colors (neon on dark)
  cad: {
    line: "#39FF14", // Neon green
    yellow: "#FFF000",
    red: "#FF073A",
    cyan: "#00FFFF",
    magenta: "#FF00FF",
    grid: "rgba(57, 255, 20, 0.1)",
  },

  // Overlays
  overlay: {
    light: "rgba(0, 0, 0, 0.4)",
    medium: "rgba(0, 0, 0, 0.6)",
    heavy: "rgba(0, 0, 0, 0.8)",
    blur: "rgba(8, 11, 18, 0.8)",
  },

  // Gradients (as CSS strings)
  gradient: {
    primary: "linear-gradient(135deg, #00A1FF 0%, #6366F1 100%)",
    primaryHover: "linear-gradient(135deg, #33B8FF 0%, #818CF8 100%)",
    gold: "linear-gradient(135deg, #D4AF37 0%, #F5D67A 50%, #D4AF37 100%)",
    surface:
      "linear-gradient(180deg, rgba(255,255,255,0.05) 0%, rgba(255,255,255,0) 100%)",
    radialGlow:
      "radial-gradient(circle at 50% 0%, rgba(0,161,255,0.15) 0%, transparent 50%)",
    mesh: `
      radial-gradient(at 40% 20%, rgba(0, 161, 255, 0.15) 0px, transparent 50%),
      radial-gradient(at 80% 0%, rgba(99, 102, 241, 0.12) 0px, transparent 50%),
      radial-gradient(at 0% 50%, rgba(0, 161, 255, 0.08) 0px, transparent 50%),
      radial-gradient(at 80% 50%, rgba(99, 102, 241, 0.06) 0px, transparent 50%),
      radial-gradient(at 0% 100%, rgba(0, 161, 255, 0.1) 0px, transparent 50%)
    `
      .replace(/\s+/g, " ")
      .trim(),
  },
} as const;

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// SPACING — 4px base scale
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

export const spacing = {
  0: "0",
  px: "1px",
  0.5: "2px",
  1: "4px",
  1.5: "6px",
  2: "8px",
  2.5: "10px",
  3: "12px",
  3.5: "14px",
  4: "16px",
  5: "20px",
  6: "24px",
  7: "28px",
  8: "32px",
  9: "36px",
  10: "40px",
  11: "44px",
  12: "48px",
  14: "56px",
  16: "64px",
  20: "80px",
  24: "96px",
  28: "112px",
  32: "128px",
  36: "144px",
  40: "160px",
  44: "176px",
  48: "192px",
  52: "208px",
  56: "224px",
  60: "240px",
  64: "256px",
  72: "288px",
  80: "320px",
  96: "384px",
} as const;

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// BORDER RADIUS — Consistent rounding
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

export const radius = {
  none: "0",
  sm: "4px",
  DEFAULT: "8px",
  md: "12px",
  lg: "16px",
  xl: "20px",
  "2xl": "24px",
  "3xl": "32px",
  full: "9999px",
} as const;

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// SHADOWS — Layered elevation system
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

export const shadows = {
  none: "none",

  // Subtle shadows for dark theme
  sm: "0 1px 2px 0 rgba(0, 0, 0, 0.3)",
  DEFAULT: "0 1px 3px 0 rgba(0, 0, 0, 0.4), 0 1px 2px -1px rgba(0, 0, 0, 0.4)",
  md: "0 4px 6px -1px rgba(0, 0, 0, 0.4), 0 2px 4px -2px rgba(0, 0, 0, 0.4)",
  lg: "0 10px 15px -3px rgba(0, 0, 0, 0.5), 0 4px 6px -4px rgba(0, 0, 0, 0.5)",
  xl: "0 20px 25px -5px rgba(0, 0, 0, 0.5), 0 8px 10px -6px rgba(0, 0, 0, 0.5)",
  "2xl": "0 25px 50px -12px rgba(0, 0, 0, 0.6)",

  // Glow effects
  glowPrimary:
    "0 0 20px rgba(0, 161, 255, 0.3), 0 0 40px rgba(0, 161, 255, 0.1)",
  glowSecondary:
    "0 0 20px rgba(99, 102, 241, 0.3), 0 0 40px rgba(99, 102, 241, 0.1)",
  glowGold:
    "0 0 20px rgba(212, 175, 55, 0.3), 0 0 40px rgba(212, 175, 55, 0.1)",
  glowSuccess: "0 0 20px rgba(16, 185, 129, 0.3)",
  glowDanger: "0 0 20px rgba(239, 68, 68, 0.3)",

  // Card shadows
  card: "0 0 0 1px rgba(255, 255, 255, 0.06), 0 2px 4px rgba(0, 0, 0, 0.2)",
  cardHover: "0 0 0 1px rgba(0, 161, 255, 0.2), 0 8px 24px rgba(0, 0, 0, 0.3)",

  // Modal shadow
  modal:
    "0 0 0 1px rgba(255, 255, 255, 0.1), 0 25px 50px -12px rgba(0, 0, 0, 0.7)",

  // Inner shadows
  inner: "inset 0 2px 4px 0 rgba(0, 0, 0, 0.3)",
} as const;

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// Z-INDEX — Layering system
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

export const zIndex = {
  behind: -1,
  base: 0,
  docked: 10,
  dropdown: 1000,
  sticky: 1100,
  banner: 1200,
  overlay: 1300,
  modal: 1400,
  popover: 1500,
  skipLink: 1600,
  toast: 1700,
  tooltip: 1800,
} as const;

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// BREAKPOINTS — Mobile-first responsive
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

export const breakpoints = {
  xs: 375, // Small phones
  sm: 640, // Large phones
  md: 768, // Tablets
  lg: 1024, // Laptops
  xl: 1280, // Desktops
  "2xl": 1536, // Large screens
} as const;

// Media query helpers
export const media = {
  xs: `@media (min-width: ${breakpoints.xs}px)`,
  sm: `@media (min-width: ${breakpoints.sm}px)`,
  md: `@media (min-width: ${breakpoints.md}px)`,
  lg: `@media (min-width: ${breakpoints.lg}px)`,
  xl: `@media (min-width: ${breakpoints.xl}px)`,
  "2xl": `@media (min-width: ${breakpoints["2xl"]}px)`,
  // Max-width variants (mobile-first breakpoints)
  maxXs: `@media (max-width: ${breakpoints.xs - 1}px)`,
  maxSm: `@media (max-width: ${breakpoints.sm - 1}px)`,
  maxMd: `@media (max-width: ${breakpoints.md - 1}px)`,
  maxLg: `@media (max-width: ${breakpoints.lg - 1}px)`,
  // Special
  hover: "@media (hover: hover)",
  reducedMotion: "@media (prefers-reduced-motion: reduce)",
  dark: "@media (prefers-color-scheme: dark)",
} as const;

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// TRANSITIONS — Consistent timing
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

export const transitions = {
  // Durations
  duration: {
    instant: "0ms",
    fast: "100ms",
    normal: "200ms",
    slow: "300ms",
    slower: "500ms",
  },

  // Easing curves
  easing: {
    linear: "linear",
    easeIn: "cubic-bezier(0.4, 0, 1, 1)",
    easeOut: "cubic-bezier(0, 0, 0.2, 1)",
    easeInOut: "cubic-bezier(0.4, 0, 0.2, 1)",
    // Premium curves
    spring: "cubic-bezier(0.34, 1.56, 0.64, 1)",
    bounce: "cubic-bezier(0.68, -0.55, 0.265, 1.55)",
    smooth: "cubic-bezier(0.25, 0.1, 0.25, 1)",
  },

  // Pre-composed transitions
  default: "200ms cubic-bezier(0.4, 0, 0.2, 1)",
  fast: "100ms cubic-bezier(0.4, 0, 0.2, 1)",
  slow: "300ms cubic-bezier(0.4, 0, 0.2, 1)",
  colors: "color 200ms, background-color 200ms, border-color 200ms",
  transform: "transform 200ms cubic-bezier(0.34, 1.56, 0.64, 1)",
  opacity: "opacity 200ms ease-out",
  all: "all 200ms cubic-bezier(0.4, 0, 0.2, 1)",
} as const;

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// BLUR — Backdrop effects
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

export const blur = {
  none: "0",
  sm: "4px",
  DEFAULT: "8px",
  md: "12px",
  lg: "16px",
  xl: "24px",
  "2xl": "40px",
  "3xl": "64px",
} as const;

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// EXPORTS — Convenient access
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

export const tokens = {
  colors,
  spacing,
  radius,
  shadows,
  zIndex,
  breakpoints,
  media,
  transitions,
  blur,
} as const;

export default tokens;
