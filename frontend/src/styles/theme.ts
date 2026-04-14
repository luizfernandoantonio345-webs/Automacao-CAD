// Theme Configuration — Engenharia CAD v1.0
// Paleta Petrobras (Azul Corporativo) + modo escuro neon

export type Theme = typeof lightTheme;

export const lightTheme = {
  // Core surfaces
  bg: "#F8F9FA",
  panel: "#FFFFFF",
  panelElevated: "#F4F7FB",
  text: "#212529",

  // Brand / CTA — Azul Petrobras
  accent: "#005596",
  accentHover: "#003F73",
  accentSoft: "rgba(0,85,150,0.12)",
  accentGlow: "rgba(0,85,150,0.28)",
  success: "#28A745",
  danger: "#DC3545",
  warning: "#FFC107",
  info: "#3F6AD8",

  // Estrutura
  border: "#DEE2E6",
  borderStrong: "#CED4DA",
  shadow: "rgba(0,0,0,0.08)",
  shadowMedium: "rgba(0,0,0,0.15)",
  overlay: "rgba(10, 18, 28, 0.35)",

  // Enterprise backgrounds
  gradientPage:
    "radial-gradient(circle at 8% -12%, rgba(0,85,150,0.16) 0%, rgba(0,85,150,0) 44%), radial-gradient(circle at 100% 0%, rgba(63,106,216,0.12) 0%, rgba(63,106,216,0) 32%), #F8F9FA",
  gradientPanel: "linear-gradient(135deg, #FFFFFF 0%, #F7FAFD 100%)",
  gradientAccent: "linear-gradient(135deg, #005596 0%, #3F6AD8 100%)",

  // CAD visual (modo claro — linhas escuras sobre fundo branco)
  cadLine: "#000000",
  cadLineGreen: "#1A7A1A",
  cadLineYellow: "#B8A000",
  cadLineRed: "#DC3545",

  // UI interno (código, inputs, alts)
  codeBackground: "#F1F3F5",
  codeText: "#212529",
  inputBackground: "#FFFFFF",
  inputBorder: "#CED4DA",
  surfaceAlt: "#F1F3F5",

  // Aliases para compatibilidade com componentes existentes
  background: "#F8F9FA",
  surface: "#FFFFFF",
  textPrimary: "#212529",
  textSecondary: "#6C757D",
  textTertiary: "#ADB5BD",
  accentPrimary: "#005596",
  accentSecondary: "#28A745",
  accentWarning: "#FFC107",
  accentDanger: "#DC3545",
  accentInfo: "#3F6AD8",
  borderLight: "#E9ECEF",
  buttonHover: "#003F73",
};

export const darkTheme = {
  // Core surfaces
  bg: "#121212",
  panel: "#1E1E1E",
  panelElevated: "#262A33",
  text: "#E0E0E0",

  // Brand / CTA — Azul vivo para fundo escuro
  accent: "#00A1FF",
  accentHover: "#33B8FF",
  accentSoft: "rgba(0,161,255,0.16)",
  accentGlow: "rgba(0,161,255,0.32)",
  success: "#32CD32",
  danger: "#FF4D4D",
  warning: "#FFD700",
  info: "#6D7BFF",

  // Estrutura
  border: "#333333",
  borderStrong: "#444D5E",
  shadow: "rgba(0,0,0,0.5)",
  shadowMedium: "rgba(0,0,0,0.7)",
  overlay: "rgba(3, 7, 11, 0.62)",

  // Enterprise backgrounds
  gradientPage:
    "radial-gradient(circle at 8% -12%, rgba(0,161,255,0.2) 0%, rgba(0,161,255,0) 42%), radial-gradient(circle at 100% 0%, rgba(109,123,255,0.16) 0%, rgba(109,123,255,0) 30%), #121212",
  gradientPanel: "linear-gradient(145deg, #1B1F28 0%, #171B24 100%)",
  gradientAccent: "linear-gradient(135deg, #00A1FF 0%, #6D7BFF 100%)",

  // CAD visual (modo escuro — neon sobre preto)
  cadLine: "#39FF14", // Neon Green principal
  cadLineGreen: "#39FF14",
  cadLineYellow: "#FFF000",
  cadLineRed: "#FF073A",

  // UI interno
  codeBackground: "#0D1117",
  codeText: "#C9D1D9",
  inputBackground: "#2A2A2A",
  inputBorder: "#444444",
  surfaceAlt: "#2A2A2A",

  // Aliases para compatibilidade com componentes existentes
  background: "#121212",
  surface: "#1E1E1E",
  textPrimary: "#E0E0E0",
  textSecondary: "#AAAAAA",
  textTertiary: "#666666",
  accentPrimary: "#00A1FF",
  accentSecondary: "#32CD32",
  accentWarning: "#FFD700",
  accentDanger: "#FF4D4D",
  accentInfo: "#6D7BFF",
  borderLight: "#444444",
  buttonHover: "#33B8FF",
};

export const getThemeColors = (isDark: boolean): Theme =>
  isDark ? darkTheme : lightTheme;
