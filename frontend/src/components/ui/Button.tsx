/**
 * Button Component — AutomAção CAD Enterprise v2.0
 * 
 * Premium button component with multiple variants, sizes, and states.
 * Features glow effects, gradients, and smooth animations.
 * 
 * @usage
 * <Button variant="primary" size="md">Click me</Button>
 * <Button variant="ghost" leftIcon={<Plus />}>Add Item</Button>
 */

import React, { forwardRef, ButtonHTMLAttributes } from 'react';
import { motion, HTMLMotionProps } from 'framer-motion';
import { colors, radius, shadows, transitions } from '../../design/tokens';
import { fontFamily, fontSize, fontWeight } from '../../design/typography';
import { tapScale, hoverLift } from '../../design/animations';

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// TYPES
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

export type ButtonVariant = 
  | 'primary'      // Gradient blue, main CTA
  | 'secondary'    // Indigo accent
  | 'outline'      // Bordered, transparent bg
  | 'ghost'        // No border, subtle hover
  | 'danger'       // Red, destructive actions
  | 'success'      // Green, confirmations
  | 'gold'         // Premium/upgrade actions
  | 'glass';       // Glassmorphism effect

export type ButtonSize = 'xs' | 'sm' | 'md' | 'lg' | 'xl';

export interface ButtonProps extends Omit<HTMLMotionProps<'button'>, 'ref'> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
  isLoading?: boolean;
  isDisabled?: boolean;
  fullWidth?: boolean;
  glow?: boolean;
}


// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// SIZE STYLES
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

const sizeStyles: Record<ButtonSize, React.CSSProperties> = {
  xs: {
    height: '28px',
    padding: '0 10px',
    fontSize: fontSize.xs,
    gap: '4px',
    borderRadius: radius.sm,
  },
  sm: {
    height: '32px',
    padding: '0 12px',
    fontSize: fontSize.sm,
    gap: '6px',
    borderRadius: radius.DEFAULT,
  },
  md: {
    height: '40px',
    padding: '0 16px',
    fontSize: fontSize.sm,
    gap: '8px',
    borderRadius: radius.md,
  },
  lg: {
    height: '48px',
    padding: '0 24px',
    fontSize: fontSize.base,
    gap: '10px',
    borderRadius: radius.md,
  },
  xl: {
    height: '56px',
    padding: '0 32px',
    fontSize: fontSize.lg,
    gap: '12px',
    borderRadius: radius.lg,
  },
};


// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// VARIANT STYLES
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

interface VariantStyle {
  base: React.CSSProperties;
  hover: React.CSSProperties;
  active: React.CSSProperties;
  glow?: string;
}

const variantStyles: Record<ButtonVariant, VariantStyle> = {
  primary: {
    base: {
      background: colors.gradient.primary,
      color: '#FFFFFF',
      border: 'none',
    },
    hover: {
      background: colors.gradient.primaryHover,
    },
    active: {
      background: colors.gradient.primary,
    },
    glow: shadows.glowPrimary,
  },
  
  secondary: {
    base: {
      background: colors.secondary.DEFAULT,
      color: '#FFFFFF',
      border: 'none',
    },
    hover: {
      background: colors.secondary[400],
    },
    active: {
      background: colors.secondary[600],
    },
    glow: shadows.glowSecondary,
  },
  
  outline: {
    base: {
      background: 'transparent',
      color: colors.primary.DEFAULT,
      border: `1px solid ${colors.border.strong}`,
    },
    hover: {
      background: colors.primary.soft,
      borderColor: colors.primary.DEFAULT,
    },
    active: {
      background: 'rgba(0, 161, 255, 0.2)',
    },
    glow: shadows.glowPrimary,
  },
  
  ghost: {
    base: {
      background: 'transparent',
      color: colors.text.secondary,
      border: 'none',
    },
    hover: {
      background: 'rgba(255, 255, 255, 0.06)',
      color: colors.text.primary,
    },
    active: {
      background: 'rgba(255, 255, 255, 0.1)',
    },
  },
  
  danger: {
    base: {
      background: colors.danger.DEFAULT,
      color: '#FFFFFF',
      border: 'none',
    },
    hover: {
      background: colors.danger[400],
    },
    active: {
      background: colors.danger[600],
    },
    glow: shadows.glowDanger,
  },
  
  success: {
    base: {
      background: colors.success.DEFAULT,
      color: '#FFFFFF',
      border: 'none',
    },
    hover: {
      background: colors.success[400],
    },
    active: {
      background: colors.success[600],
    },
    glow: shadows.glowSuccess,
  },
  
  gold: {
    base: {
      background: colors.gradient.gold,
      color: '#000000',
      border: 'none',
    },
    hover: {
      filter: 'brightness(1.1)',
    },
    active: {
      filter: 'brightness(0.95)',
    },
    glow: shadows.glowGold,
  },
  
  glass: {
    base: {
      background: 'rgba(255, 255, 255, 0.06)',
      backdropFilter: 'blur(12px)',
      color: colors.text.primary,
      border: `1px solid ${colors.border.subtle}`,
    },
    hover: {
      background: 'rgba(255, 255, 255, 0.1)',
      borderColor: colors.border.default,
    },
    active: {
      background: 'rgba(255, 255, 255, 0.08)',
    },
  },
};


// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// LOADING SPINNER
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

const LoadingSpinner: React.FC<{ size: ButtonSize }> = ({ size }) => {
  const spinnerSize = {
    xs: 12,
    sm: 14,
    md: 16,
    lg: 18,
    xl: 20,
  }[size];

  return (
    <motion.svg
      width={spinnerSize}
      height={spinnerSize}
      viewBox="0 0 24 24"
      fill="none"
      animate={{ rotate: 360 }}
      transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
    >
      <circle
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="3"
        strokeLinecap="round"
        strokeDasharray="31.4 31.4"
        opacity={0.3}
      />
      <circle
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="3"
        strokeLinecap="round"
        strokeDasharray="31.4 31.4"
        strokeDashoffset="75"
      />
    </motion.svg>
  );
};


// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// BUTTON COMPONENT
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      variant = 'primary',
      size = 'md',
      leftIcon,
      rightIcon,
      isLoading = false,
      isDisabled = false,
      fullWidth = false,
      glow = false,
      children,
      style,
      ...props
    },
    ref
  ) => {
    const variantStyle = variantStyles[variant];
    const sizeStyle = sizeStyles[size];
    const disabled = isDisabled || isLoading;

    const baseStyles: React.CSSProperties = {
      // Reset
      outline: 'none',
      cursor: disabled ? 'not-allowed' : 'pointer',
      
      // Layout
      display: 'inline-flex',
      alignItems: 'center',
      justifyContent: 'center',
      width: fullWidth ? '100%' : 'auto',
      
      // Typography
      fontFamily: fontFamily.sans,
      fontWeight: fontWeight.medium,
      whiteSpace: 'nowrap',
      
      // Transitions
      transition: `all ${transitions.default}`,
      
      // Apply size
      ...sizeStyle,
      
      // Apply variant
      ...variantStyle.base,
      
      // Apply glow if enabled
      ...(glow && variantStyle.glow ? { boxShadow: variantStyle.glow } : {}),
      
      // Disabled state
      ...(disabled ? { opacity: 0.5, pointerEvents: 'none' as const } : {}),
      
      // Custom styles
      ...style,
    };

    return (
      <motion.button
        ref={ref}
        style={baseStyles}
        whileHover={!disabled ? { ...hoverLift, ...variantStyle.hover } : undefined}
        whileTap={!disabled ? tapScale : undefined}
        disabled={disabled}
        aria-disabled={disabled}
        aria-busy={isLoading}
        {...props}
      >
        {isLoading ? (
          <LoadingSpinner size={size} />
        ) : (
          <>
            {leftIcon && <span style={{ display: 'flex' }}>{leftIcon}</span>}
            {children}
            {rightIcon && <span style={{ display: 'flex' }}>{rightIcon}</span>}
          </>
        )}
      </motion.button>
    );
  }
);

Button.displayName = 'Button';

export default Button;
