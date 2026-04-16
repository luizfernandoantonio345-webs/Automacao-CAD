/**
 * Design System — AutomAção CAD Enterprise v2.0
 * 
 * Central export for all design tokens, typography, and animations.
 * 
 * @usage import { tokens, typography, animations } from '@/design';
 */

// Core tokens
export * from './tokens';
export { default as tokens } from './tokens';

// Typography
export * from './typography';
export { default as typography } from './typography';

// Animations
export * from './animations';
export { default as animations } from './animations';

// Re-export commonly used items at top level for convenience
export { 
  colors, 
  spacing, 
  radius, 
  shadows, 
  zIndex, 
  breakpoints, 
  media, 
  transitions,
  blur,
} from './tokens';

export {
  fontFamily,
  fontSize,
  fontWeight,
  lineHeight,
  letterSpacing,
  textStyles,
  applyTextStyle,
  googleFontsUrl,
  satoshiFontUrl,
  fontImports,
} from './typography';

export {
  duration,
  easing,
  transition,
  fadeIn,
  fadeInScale,
  slideUp,
  slideDown,
  slideLeft,
  slideRight,
  scaleIn,
  popIn,
  staggerContainer,
  staggerItem,
  staggerContainerSlow,
  hoverLift,
  hoverScale,
  hoverGlow,
  tapScale,
  tapPush,
  modal,
  backdrop,
  drawer,
  toast,
  shimmer,
  pageTransition,
  createStagger,
  createSlide,
} from './animations';
