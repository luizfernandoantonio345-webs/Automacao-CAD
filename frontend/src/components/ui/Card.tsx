/**
 * Card Component — AutomAção CAD Enterprise v2.0
 * 
 * Premium card component with glass effect, hover states, and glow.
 * 
 * @usage
 * <Card variant="surface" hover glow>
 *   <Card.Header>Title</Card.Header>
 *   <Card.Body>Content</Card.Body>
 * </Card>
 */

import React, { forwardRef, HTMLAttributes } from 'react';
import { motion, HTMLMotionProps } from 'framer-motion';
import { colors, radius, shadows, transitions, spacing, blur } from '../../design/tokens';
import { fontFamily, textStyles } from '../../design/typography';
import { fadeInScale, hoverLift, hoverGlow } from '../../design/animations';

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// TYPES
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

export type CardVariant = 
  | 'surface'      // Standard card bg
  | 'elevated'     // Slightly lighter bg
  | 'glass'        // Glassmorphism effect
  | 'outline'      // Border only, transparent
  | 'gradient';    // Gradient border

export type CardSize = 'sm' | 'md' | 'lg';

export interface CardProps extends Omit<HTMLMotionProps<'div'>, 'ref'> {
  variant?: CardVariant;
  size?: CardSize;
  hover?: boolean;
  glow?: boolean;
  glowColor?: string;
  noPadding?: boolean;
  animated?: boolean;
}


// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// SIZE STYLES
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

const sizeStyles: Record<CardSize, React.CSSProperties> = {
  sm: {
    padding: spacing[4],    // 16px
    borderRadius: radius.md,
  },
  md: {
    padding: spacing[6],    // 24px
    borderRadius: radius.lg,
  },
  lg: {
    padding: spacing[8],    // 32px
    borderRadius: radius.xl,
  },
};


// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// VARIANT STYLES
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

const variantStyles: Record<CardVariant, React.CSSProperties> = {
  surface: {
    background: colors.dark.surface,
    border: `1px solid ${colors.border.subtle}`,
    boxShadow: shadows.card,
  },
  
  elevated: {
    background: colors.dark.elevated,
    border: `1px solid ${colors.border.default}`,
    boxShadow: shadows.md,
  },
  
  glass: {
    background: 'rgba(255, 255, 255, 0.03)',
    backdropFilter: `blur(${blur.lg})`,
    WebkitBackdropFilter: `blur(${blur.lg})`,
    border: `1px solid ${colors.border.subtle}`,
    boxShadow: shadows.card,
  },
  
  outline: {
    background: 'transparent',
    border: `1px solid ${colors.border.default}`,
    boxShadow: 'none',
  },
  
  gradient: {
    background: colors.dark.surface,
    border: 'none',
    boxShadow: shadows.card,
    // Gradient border is applied via pseudo-element in wrapper
  },
};


// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// GRADIENT BORDER WRAPPER
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

const GradientBorderWrapper: React.FC<{
  children: React.ReactNode;
  borderRadius: string;
}> = ({ children, borderRadius }) => (
  <div
    style={{
      position: 'relative',
      padding: '1px',
      background: colors.gradient.primary,
      borderRadius,
    }}
  >
    {children}
  </div>
);


// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// CARD COMPONENT
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

export const Card = forwardRef<HTMLDivElement, CardProps>(
  (
    {
      variant = 'surface',
      size = 'md',
      hover = false,
      glow = false,
      glowColor = colors.primary.glow,
      noPadding = false,
      animated = true,
      children,
      style,
      ...props
    },
    ref
  ) => {
    const variantStyle = variantStyles[variant];
    const sizeStyle = sizeStyles[size];

    const baseStyles: React.CSSProperties = {
      // Layout
      position: 'relative',
      width: '100%',
      
      // Apply variant
      ...variantStyle,
      
      // Apply size (unless noPadding)
      borderRadius: sizeStyle.borderRadius,
      ...(noPadding ? {} : { padding: sizeStyle.padding }),
      
      // Transition
      transition: `all ${transitions.default}`,
      
      // Custom styles
      ...style,
    };

    const hoverAnimation = hover
      ? {
          ...hoverLift,
          boxShadow: glow
            ? `0 0 20px ${glowColor}, 0 8px 24px rgba(0, 0, 0, 0.3)`
            : shadows.cardHover,
          borderColor: colors.border.strong,
        }
      : undefined;

    const cardContent = (
      <motion.div
        ref={ref}
        style={baseStyles}
        variants={animated ? fadeInScale : undefined}
        initial={animated ? 'hidden' : undefined}
        animate={animated ? 'visible' : undefined}
        whileHover={hoverAnimation}
        {...props}
      >
        {children}
      </motion.div>
    );

    // Wrap with gradient border if variant is gradient
    if (variant === 'gradient') {
      return (
        <GradientBorderWrapper borderRadius={sizeStyle.borderRadius || radius.lg}>
          {cardContent}
        </GradientBorderWrapper>
      );
    }

    return cardContent;
  }
);

Card.displayName = 'Card';


// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// CARD SUBCOMPONENTS
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

interface CardHeaderProps extends HTMLAttributes<HTMLDivElement> {
  title?: string;
  subtitle?: string;
  action?: React.ReactNode;
}

export const CardHeader: React.FC<CardHeaderProps> = ({
  title,
  subtitle,
  action,
  children,
  style,
  ...props
}) => (
  <div
    style={{
      display: 'flex',
      alignItems: 'flex-start',
      justifyContent: 'space-between',
      marginBottom: spacing[4],
      ...style,
    }}
    {...props}
  >
    <div>
      {title && (
        <h3
          style={{
            margin: 0,
            ...textStyles.heading.h3,
            color: colors.text.primary,
          }}
        >
          {title}
        </h3>
      )}
      {subtitle && (
        <p
          style={{
            margin: `${spacing[1]} 0 0`,
            ...textStyles.body.sm,
            color: colors.text.secondary,
          }}
        >
          {subtitle}
        </p>
      )}
      {children}
    </div>
    {action && <div>{action}</div>}
  </div>
);

CardHeader.displayName = 'CardHeader';


interface CardBodyProps extends HTMLAttributes<HTMLDivElement> {}

export const CardBody: React.FC<CardBodyProps> = ({
  children,
  style,
  ...props
}) => (
  <div
    style={{
      ...textStyles.body.md,
      color: colors.text.secondary,
      ...style,
    }}
    {...props}
  >
    {children}
  </div>
);

CardBody.displayName = 'CardBody';


interface CardFooterProps extends HTMLAttributes<HTMLDivElement> {
  align?: 'left' | 'center' | 'right' | 'between';
}

export const CardFooter: React.FC<CardFooterProps> = ({
  align = 'right',
  children,
  style,
  ...props
}) => {
  const justifyContent = {
    left: 'flex-start',
    center: 'center',
    right: 'flex-end',
    between: 'space-between',
  }[align];

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent,
        gap: spacing[3],
        marginTop: spacing[6],
        paddingTop: spacing[4],
        borderTop: `1px solid ${colors.border.subtle}`,
        ...style,
      }}
      {...props}
    >
      {children}
    </div>
  );
};

CardFooter.displayName = 'CardFooter';


// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// COMPOUND EXPORT
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

export default Object.assign(Card, {
  Header: CardHeader,
  Body: CardBody,
  Footer: CardFooter,
});
