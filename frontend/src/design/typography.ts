/**
 * Typography System — AutomAção CAD Enterprise v2.0
 * 
 * Font Stack:
 * - Satoshi: Display, headings (modern, Linear/Vercel style)
 * - Inter: UI, body text (highly legible)
 * - JetBrains Mono: Code, metrics (monospace)
 * 
 * @usage import { typography, fontFamily } from '@/design/typography';
 */

import type { CSSProperties } from 'react';

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// FONT FAMILIES
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

export const fontFamily = {
  // Display/Headings - Satoshi (modern geometric sans)
  display: '"Satoshi", "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
  
  // UI/Body - Inter (excellent legibility)
  sans: '"Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", sans-serif',
  
  // Monospace - JetBrains Mono (developer friendly)
  mono: '"JetBrains Mono", "Fira Code", "SF Mono", Monaco, Consolas, "Liberation Mono", monospace',
} as const;


// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// FONT SIZES — Modular scale (1.25 ratio)
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

export const fontSize = {
  // Extra small
  xs: '0.75rem',      // 12px
  
  // Small
  sm: '0.875rem',     // 14px
  
  // Base
  base: '1rem',       // 16px
  
  // Large
  lg: '1.125rem',     // 18px
  
  // Extra large
  xl: '1.25rem',      // 20px
  '2xl': '1.5rem',    // 24px
  '3xl': '1.875rem',  // 30px
  '4xl': '2.25rem',   // 36px
  '5xl': '3rem',      // 48px
  '6xl': '3.75rem',   // 60px
  '7xl': '4.5rem',    // 72px
  '8xl': '6rem',      // 96px
  '9xl': '8rem',      // 128px
} as const;


// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// FONT WEIGHTS
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

export const fontWeight = {
  thin: 100,
  extralight: 200,
  light: 300,
  normal: 400,
  medium: 500,
  semibold: 600,
  bold: 700,
  extrabold: 800,
  black: 900,
} as const;


// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// LINE HEIGHTS
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

export const lineHeight = {
  none: 1,
  tight: 1.1,
  snug: 1.25,
  normal: 1.5,
  relaxed: 1.625,
  loose: 2,
} as const;


// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// LETTER SPACING
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

export const letterSpacing = {
  tighter: '-0.05em',
  tight: '-0.025em',
  normal: '0',
  wide: '0.025em',
  wider: '0.05em',
  widest: '0.1em',
} as const;


// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// TEXT STYLES — Pre-composed typography
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

export type TextStyle = {
  fontFamily: string;
  fontSize: string;
  fontWeight: number;
  lineHeight: number;
  letterSpacing: string;
};

export const textStyles = {
  // Display styles (Satoshi) — Hero sections, major headings
  display: {
    '2xl': {
      fontFamily: fontFamily.display,
      fontSize: fontSize['7xl'],    // 72px
      fontWeight: fontWeight.bold,
      lineHeight: lineHeight.tight,
      letterSpacing: letterSpacing.tight,
    },
    xl: {
      fontFamily: fontFamily.display,
      fontSize: fontSize['6xl'],    // 60px
      fontWeight: fontWeight.bold,
      lineHeight: lineHeight.tight,
      letterSpacing: letterSpacing.tight,
    },
    lg: {
      fontFamily: fontFamily.display,
      fontSize: fontSize['5xl'],    // 48px
      fontWeight: fontWeight.bold,
      lineHeight: lineHeight.tight,
      letterSpacing: letterSpacing.tight,
    },
    md: {
      fontFamily: fontFamily.display,
      fontSize: fontSize['4xl'],    // 36px
      fontWeight: fontWeight.semibold,
      lineHeight: lineHeight.snug,
      letterSpacing: letterSpacing.tight,
    },
    sm: {
      fontFamily: fontFamily.display,
      fontSize: fontSize['3xl'],    // 30px
      fontWeight: fontWeight.semibold,
      lineHeight: lineHeight.snug,
      letterSpacing: letterSpacing.normal,
    },
  },

  // Heading styles (Satoshi) — Section headings
  heading: {
    h1: {
      fontFamily: fontFamily.display,
      fontSize: fontSize['3xl'],    // 30px
      fontWeight: fontWeight.semibold,
      lineHeight: lineHeight.snug,
      letterSpacing: letterSpacing.tight,
    },
    h2: {
      fontFamily: fontFamily.display,
      fontSize: fontSize['2xl'],    // 24px
      fontWeight: fontWeight.semibold,
      lineHeight: lineHeight.snug,
      letterSpacing: letterSpacing.normal,
    },
    h3: {
      fontFamily: fontFamily.display,
      fontSize: fontSize.xl,        // 20px
      fontWeight: fontWeight.semibold,
      lineHeight: lineHeight.normal,
      letterSpacing: letterSpacing.normal,
    },
    h4: {
      fontFamily: fontFamily.display,
      fontSize: fontSize.lg,        // 18px
      fontWeight: fontWeight.medium,
      lineHeight: lineHeight.normal,
      letterSpacing: letterSpacing.normal,
    },
    h5: {
      fontFamily: fontFamily.display,
      fontSize: fontSize.base,      // 16px
      fontWeight: fontWeight.medium,
      lineHeight: lineHeight.normal,
      letterSpacing: letterSpacing.normal,
    },
    h6: {
      fontFamily: fontFamily.display,
      fontSize: fontSize.sm,        // 14px
      fontWeight: fontWeight.medium,
      lineHeight: lineHeight.normal,
      letterSpacing: letterSpacing.normal,
    },
  },

  // Body styles (Inter) — Paragraphs, UI text
  body: {
    lg: {
      fontFamily: fontFamily.sans,
      fontSize: fontSize.lg,        // 18px
      fontWeight: fontWeight.normal,
      lineHeight: lineHeight.relaxed,
      letterSpacing: letterSpacing.normal,
    },
    md: {
      fontFamily: fontFamily.sans,
      fontSize: fontSize.base,      // 16px
      fontWeight: fontWeight.normal,
      lineHeight: lineHeight.normal,
      letterSpacing: letterSpacing.normal,
    },
    sm: {
      fontFamily: fontFamily.sans,
      fontSize: fontSize.sm,        // 14px
      fontWeight: fontWeight.normal,
      lineHeight: lineHeight.normal,
      letterSpacing: letterSpacing.normal,
    },
    xs: {
      fontFamily: fontFamily.sans,
      fontSize: fontSize.xs,        // 12px
      fontWeight: fontWeight.normal,
      lineHeight: lineHeight.normal,
      letterSpacing: letterSpacing.normal,
    },
  },

  // Label styles (Inter) — Form labels, buttons
  label: {
    lg: {
      fontFamily: fontFamily.sans,
      fontSize: fontSize.base,      // 16px
      fontWeight: fontWeight.medium,
      lineHeight: lineHeight.none,
      letterSpacing: letterSpacing.normal,
    },
    md: {
      fontFamily: fontFamily.sans,
      fontSize: fontSize.sm,        // 14px
      fontWeight: fontWeight.medium,
      lineHeight: lineHeight.none,
      letterSpacing: letterSpacing.normal,
    },
    sm: {
      fontFamily: fontFamily.sans,
      fontSize: fontSize.xs,        // 12px
      fontWeight: fontWeight.medium,
      lineHeight: lineHeight.none,
      letterSpacing: letterSpacing.wide,
    },
  },

  // Code styles (JetBrains Mono)
  code: {
    lg: {
      fontFamily: fontFamily.mono,
      fontSize: fontSize.base,      // 16px
      fontWeight: fontWeight.normal,
      lineHeight: lineHeight.relaxed,
      letterSpacing: letterSpacing.normal,
    },
    md: {
      fontFamily: fontFamily.mono,
      fontSize: fontSize.sm,        // 14px
      fontWeight: fontWeight.normal,
      lineHeight: lineHeight.relaxed,
      letterSpacing: letterSpacing.normal,
    },
    sm: {
      fontFamily: fontFamily.mono,
      fontSize: fontSize.xs,        // 12px
      fontWeight: fontWeight.normal,
      lineHeight: lineHeight.relaxed,
      letterSpacing: letterSpacing.normal,
    },
  },

  // Overline/Caption styles
  overline: {
    fontFamily: fontFamily.sans,
    fontSize: fontSize.xs,          // 12px
    fontWeight: fontWeight.semibold,
    lineHeight: lineHeight.none,
    letterSpacing: letterSpacing.widest,
  },

  caption: {
    fontFamily: fontFamily.sans,
    fontSize: fontSize.xs,          // 12px
    fontWeight: fontWeight.normal,
    lineHeight: lineHeight.normal,
    letterSpacing: letterSpacing.normal,
  },

} as const;


// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// CSS HELPER — Apply text style as inline style
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

export function applyTextStyle(style: TextStyle): CSSProperties {
  return {
    fontFamily: style.fontFamily,
    fontSize: style.fontSize,
    fontWeight: style.fontWeight,
    lineHeight: style.lineHeight,
    letterSpacing: style.letterSpacing,
  };
}


// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// FONT LOADER — CSS @font-face rules
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

// Google Fonts import URL
export const googleFontsUrl = 
  'https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap';

// Satoshi from Fontshare (free for commercial use)
export const satoshiFontUrl = 'https://api.fontshare.com/v2/css?f[]=satoshi@400,500,600,700,900&display=swap';

// Combined CSS imports
export const fontImports = `
  @import url('${satoshiFontUrl}');
  @import url('${googleFontsUrl}');
`;


// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// EXPORTS
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

export const typography = {
  fontFamily,
  fontSize,
  fontWeight,
  lineHeight,
  letterSpacing,
  textStyles,
} as const;

export default typography;
