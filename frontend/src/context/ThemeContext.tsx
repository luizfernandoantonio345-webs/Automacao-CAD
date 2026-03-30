import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { getThemeColors, type Theme } from '../styles/theme';

interface ThemeContextType {
  isDark: boolean;
  theme: Theme;
  toggleTheme: () => void;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

export const ThemeProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [isDark, setIsDark] = useState<boolean>(() => {
    // Carregar preferência do localStorage
    const saved = localStorage.getItem('theme-preference');
    if (saved) return saved === 'dark';
    // Preferência do sistema
    return window.matchMedia('(prefers-color-scheme: dark)').matches;
  });

  const theme = getThemeColors(isDark);

  useEffect(() => {
    // Persistir preferência
    localStorage.setItem('theme-preference', isDark ? 'dark' : 'light');
    
    // Aplicar ao documento
    document.documentElement.style.backgroundColor = theme.background;
    document.documentElement.style.color = theme.textPrimary;
  }, [isDark, theme]);

  const toggleTheme = () => {
    setIsDark(prev => !prev);
  };

  return (
    <ThemeContext.Provider value={{ isDark, theme, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  );
};

export const useTheme = (): ThemeContextType => {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme deve ser usado dentro de ThemeProvider');
  }
  return context;
};
