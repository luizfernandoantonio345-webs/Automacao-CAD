/**
 * Badge Component — AutomAção CAD Enterprise v2.0
 * 
 * Premium badge component for status indicators, counts, and labels.
 * 
 * @usage
 * <Badge variant="primary">New</Badge>
 * <Badge variant="gold" glow>Premium</Badge>
 */

import React from 'react';
import { motion, HTMLMotionProps } from 'framer-motion';
import { colors, radius, spacing } from '../../design/tokens';
import { fontFamily, fontSize, fontWeight } from '../../design/typography';
import { popIn } from '../../design/animations';

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// TYPES
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

export type BadgeVariant = 
  | 'default'
  | 'primary'
  | 'secondary'
  | 'success'
  | 'warning'
  | 'danger'
  | 'gold'
  | 'outline';

export type BadgeSize = 'xs' | 'sm' | 'md';

export interface BadgeProps extends Omit<HTMLMotionProps<'span'>, 'ref'> {
  variant?: BadgeVariant;
  size?: BadgeSize;
  glow?: boolean;
  dot?: boolean;
  animated?: boolean;
  icon?: React.ReactNode;
}


// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// SIZE STYLES
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

const sizeStyles: Record<BadgeSize, React.CSSProperties> = {
  xs: {
    height: '18px',
    padding: '0 6px',
    fontSize: '10px',
    borderRadius: radius.sm,
  },
  sm: {
    height: '22px',
    padding: '0 8px',
    fontSize: fontSize.xs,
    borderRadius: radius.DEFAULT,
  },
  md: {
    height: '26px',
    padding: '0 10px',
    fontSize: fontSize.sm,
    borderRadius: radius.md,
  },
};


// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// VARIANT STYLES
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

interface VariantStyle {
  base: React.CSSProperties;
  glow?: string;
}

const variantStyles: Record<BadgeVariant, VariantStyle> = {
  default: {
    base: {
      background: colors.dark.elevated,
      color: colors.text.secondary,
      border: `1px solid ${colors.border.subtle}`,
    },
  },
  
  primary: {
    base: {
      background: colors.primary.soft,
      color: colors.primary.DEFAULT,
      border: 'none',
    },
    glow: `0 0 12px ${colors.primary.glow}`,
  },
  
  secondary: {
    base: {
      background: colors.secondary.soft,
      color: colors.secondary.DEFAULT,
      border: 'none',
    },
    glow: `0 0 12px ${colors.secondary.glow}`,
  },
  
  success: {
    base: {
      background: colors.success.soft,
      color: colors.success.DEFAULT,
      border: 'none',
    },
    glow: `0 0 12px ${colors.success.glow}`,
  },
  
  warning: {
    base: {
      background: colors.warning.soft,
      color: colors.warning.DEFAULT,
      border: 'none',
    },
    glow: `0 0 12px ${colors.warning.glow}`,
  },
  
  danger: {
    base: {
      background: colors.danger.soft,
      color: colors.danger.DEFAULT,
      border: 'none',
    },
    glow: `0 0 12px ${colors.danger.glow}`,
  },
  
  gold: {
    base: {
      background: colors.gold.soft,
      color: colors.gold.DEFAULT,
      border: 'none',
    },
    glow: `0 0 12px ${colors.gold.glow}`,
  },
  
  outline: {
    base: {
      background: 'transparent',
      color: colors.text.secondary,
      border: `1px solid ${colors.border.default}`,
    },
  },
};


// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// BADGE COMPONENT
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

export const Badge: React.FC<BadgeProps> = ({
  variant = 'default',
  size = 'sm',
  glow = false,
  dot = false,
  animated = false,
  icon,
  children,
  style,
  ...props
}) => {
  const variantStyle = variantStyles[variant];
  const sizeStyle = sizeStyles[size];

  const baseStyles: React.CSSProperties = {
    // Layout
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: spacing[1],
    
    // Typography
    fontFamily: fontFamily.sans,
    fontWeight: fontWeight.semibold,
    lineHeight: 1,
    whiteSpace: 'nowrap',
    textTransform: 'uppercase',
    letterSpacing: '0.025em',
    
    // Apply size
    ...sizeStyle,
    
    // Apply variant
    ...variantStyle.base,
    
    // Apply glow
    ...(glow && variantStyle.glow ? { boxShadow: variantStyle.glow } : {}),
    
    // If dot mode, override sizing
    ...(dot ? {
      width: '8px',
      height: '8px',
      padding: 0,
      borderRadius: radius.full,
    } : {}),
    
    // Custom styles
    ...style,
  };

  // Dot mode renders just a colored dot
  if (dot) {
    return (
      <motion.span
        style={baseStyles}
        variants={animated ? popIn : undefined}
        initial={animated ? 'hidden' : undefined}
        animate={animated ? 'visible' : undefined}
        {...props}
      />
    );
  }

  return (
    <motion.span
      style={baseStyles}
      variants={animated ? popIn : undefined}
      initial={animated ? 'hidden' : undefined}
      animate={animated ? 'visible' : undefined}
      {...props}
    >
      {icon && (
        <span style={{ display: 'flex', width: '12px', height: '12px' }}>
          {icon}
        </span>
      )}
      {children}
    </motion.span>
  );
};

Badge.displayName = 'Badge';

export default Badge;
