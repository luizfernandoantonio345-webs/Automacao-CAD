// Theme Configuration — Engenharia CAD v1.0
// Paleta Petrobras (Azul Corporativo) + modo escuro neon

export type Theme = typeof lightTheme;

export const lightTheme = {
  // Core surfaces
  bg: '#F8F9FA',
  panel: '#FFFFFF',
  text: '#212529',

  // Brand / CTA — Azul Petrobras
  accent: '#005596',
  accentHover: '#003F73',
  success: '#28A745',
  danger: '#DC3545',
  warning: '#FFC107',

  // Estrutura
  border: '#DEE2E6',
  shadow: 'rgba(0,0,0,0.08)',
  shadowMedium: 'rgba(0,0,0,0.15)',

  // CAD visual (modo claro — linhas escuras sobre fundo branco)
  cadLine: '#000000',
  cadLineGreen: '#1A7A1A',
  cadLineYellow: '#B8A000',
  cadLineRed: '#DC3545',

  // UI interno (código, inputs, alts)
  codeBackground: '#F1F3F5',
  codeText: '#212529',
  inputBackground: '#FFFFFF',
  inputBorder: '#CED4DA',
  surfaceAlt: '#F1F3F5',

  // Aliases para compatibilidade com componentes existentes
  background: '#F8F9FA',
  surface: '#FFFFFF',
  textPrimary: '#212529',
  textSecondary: '#6C757D',
  textTertiary: '#ADB5BD',
  accentPrimary: '#005596',
  accentSecondary: '#28A745',
  accentWarning: '#FFC107',
  accentDanger: '#DC3545',
  borderLight: '#E9ECEF',
  buttonHover: '#003F73',
};

export const darkTheme = {
  // Core surfaces
  bg: '#121212',
  panel: '#1E1E1E',
  text: '#E0E0E0',

  // Brand / CTA — Azul vivo para fundo escuro
  accent: '#00A1FF',
  accentHover: '#33B8FF',
  success: '#32CD32',
  danger: '#FF4D4D',
  warning: '#FFD700',

  // Estrutura
  border: '#333333',
  shadow: 'rgba(0,0,0,0.5)',
  shadowMedium: 'rgba(0,0,0,0.7)',

  // CAD visual (modo escuro — neon sobre preto)
  cadLine: '#39FF14',       // Neon Green principal
  cadLineGreen: '#39FF14',
  cadLineYellow: '#FFF000',
  cadLineRed: '#FF073A',

  // UI interno
  codeBackground: '#0D1117',
  codeText: '#C9D1D9',
  inputBackground: '#2A2A2A',
  inputBorder: '#444444',
  surfaceAlt: '#2A2A2A',

  // Aliases para compatibilidade com componentes existentes
  background: '#121212',
  surface: '#1E1E1E',
  textPrimary: '#E0E0E0',
  textSecondary: '#AAAAAA',
  textTertiary: '#666666',
  accentPrimary: '#00A1FF',
  accentSecondary: '#32CD32',
  accentWarning: '#FFD700',
  accentDanger: '#FF4D4D',
  borderLight: '#444444',
  buttonHover: '#33B8FF',
};

export const getThemeColors = (isDark: boolean): Theme =>
  isDark ? darkTheme : lightTheme;
