/**
 * Tabs Component — AutomAção CAD Enterprise v2.0
 * 
 * Elegant tabs with underline or pills variants and smooth animations.
 * 
 * @usage
 * <Tabs value={activeTab} onChange={setActiveTab}>
 *   <TabsList>
 *     <TabsTrigger value="account">Conta</TabsTrigger>
 *     <TabsTrigger value="security">Segurança</TabsTrigger>
 *   </TabsList>
 *   <TabsContent value="account">Account content...</TabsContent>
 *   <TabsContent value="security">Security content...</TabsContent>
 * </Tabs>
 */

import React, { createContext, useContext, useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { colors, radius, spacing } from '../../design/tokens';
import { fontFamily, fontSize, fontWeight } from '../../design/typography';

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// TYPES
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

export interface TabsProps {
  value: string;
  onChange: (value: string) => void;
  variant?: 'underline' | 'pills' | 'bordered';
  size?: 'sm' | 'md' | 'lg';
  fullWidth?: boolean;
  children: React.ReactNode;
  className?: string;
}

export interface TabsListProps {
  children: React.ReactNode;
  className?: string;
}

export interface TabsTriggerProps {
  value: string;
  disabled?: boolean;
  icon?: React.ReactNode;
  badge?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}

export interface TabsContentProps {
  value: string;
  forceMount?: boolean;
  children: React.ReactNode;
  className?: string;
}

interface TabsContextValue {
  value: string;
  onChange: (value: string) => void;
  variant: 'underline' | 'pills' | 'bordered';
  size: 'sm' | 'md' | 'lg';
  fullWidth: boolean;
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// CONTEXT
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

const TabsContext = createContext<TabsContextValue | null>(null);

const useTabs = () => {
  const context = useContext(TabsContext);
  if (!context) {
    throw new Error('Tabs components must be used within a Tabs provider');
  }
  return context;
};

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// SIZE CONFIG
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

const sizeConfig = {
  sm: {
    padding: `${spacing[2]} ${spacing[3]}`,
    fontSize: fontSize.sm,
    gap: spacing[1],
    iconSize: 14,
  },
  md: {
    padding: `${spacing[2]} ${spacing[4]}`,
    fontSize: fontSize.base,
    gap: spacing[2],
    iconSize: 16,
  },
  lg: {
    padding: `${spacing[3]} ${spacing[5]}`,
    fontSize: fontSize.lg,
    gap: spacing[2],
    iconSize: 18,
  },
};

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// ANIMATION VARIANTS
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

const contentVariants = {
  hidden: { 
    opacity: 0, 
    y: 8,
  },
  visible: { 
    opacity: 1, 
    y: 0,
    transition: {
      duration: 0.2,
      ease: 'easeOut',
    },
  },
  exit: { 
    opacity: 0,
    y: -8,
    transition: {
      duration: 0.15,
    },
  },
};

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// MAIN TABS COMPONENT
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

export const Tabs: React.FC<TabsProps> = ({
  value,
  onChange,
  variant = 'underline',
  size = 'md',
  fullWidth = false,
  children,
  className = '',
}) => {
  return (
    <TabsContext.Provider value={{ value, onChange, variant, size, fullWidth }}>
      <div className={className}>
        {children}
      </div>
    </TabsContext.Provider>
  );
};

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// TABS LIST COMPONENT
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

export const TabsList: React.FC<TabsListProps> = ({ 
  children, 
  className = '' 
}) => {
  const { variant, fullWidth } = useTabs();
  const [indicatorStyle, setIndicatorStyle] = useState({ left: 0, width: 0 });
  const listRef = useRef<HTMLDivElement>(null);

  // Update indicator position when value changes
  useEffect(() => {
    if (variant === 'underline' && listRef.current) {
      const activeTab = listRef.current.querySelector('[data-state="active"]') as HTMLElement;
      if (activeTab) {
        setIndicatorStyle({
          left: activeTab.offsetLeft,
          width: activeTab.offsetWidth,
        });
      }
    }
  }, [variant]);

  const getVariantStyles = (): React.CSSProperties => {
    switch (variant) {
      case 'pills':
        return {
          backgroundColor: colors.dark.surface,
          padding: spacing[1],
          borderRadius: radius.lg,
        };
      case 'bordered':
        return {
          borderBottom: `1px solid ${colors.border.subtle}`,
        };
      default:
        return {
          borderBottom: `1px solid ${colors.border.subtle}`,
          position: 'relative',
        };
    }
  };

  const styles = {
    list: {
      display: 'flex',
      alignItems: 'center',
      gap: variant === 'pills' ? spacing[1] : spacing[2],
      width: fullWidth ? '100%' : 'auto',
      ...getVariantStyles(),
    } as React.CSSProperties,

    indicator: {
      position: 'absolute' as const,
      bottom: '-1px',
      height: '2px',
      backgroundColor: colors.primary.DEFAULT,
      borderRadius: radius.full,
      transition: 'all 200ms cubic-bezier(0.4, 0, 0.2, 1)',
    },
  };

  return (
    <div ref={listRef} style={styles.list} role="tablist" className={className}>
      {children}
      {variant === 'underline' && (
        <motion.div
          style={{
            ...styles.indicator,
            left: indicatorStyle.left,
            width: indicatorStyle.width,
          }}
          layout
          layoutId="tab-indicator"
        />
      )}
    </div>
  );
};

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// TABS TRIGGER COMPONENT
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

export const TabsTrigger: React.FC<TabsTriggerProps> = ({
  value: triggerValue,
  disabled = false,
  icon,
  badge,
  children,
  className = '',
}) => {
  const { value, onChange, variant, size, fullWidth } = useTabs();
  const isActive = value === triggerValue;
  const config = sizeConfig[size];

  const getVariantStyles = (): React.CSSProperties => {
    switch (variant) {
      case 'pills':
        return {
          backgroundColor: isActive ? colors.primary.DEFAULT : 'transparent',
          color: isActive ? '#ffffff' : colors.text.secondary,
          borderRadius: radius.md,
        };
      case 'bordered':
        return {
          backgroundColor: isActive ? colors.dark.elevated : 'transparent',
          color: isActive ? colors.text.primary : colors.text.secondary,
          borderBottom: isActive 
            ? `2px solid ${colors.primary.DEFAULT}` 
            : '2px solid transparent',
          marginBottom: '-1px',
        };
      default: // underline
        return {
          color: isActive ? colors.primary.DEFAULT : colors.text.secondary,
          paddingBottom: spacing[3],
        };
    }
  };

  const styles = {
    trigger: {
      display: 'inline-flex',
      alignItems: 'center',
      justifyContent: 'center',
      gap: config.gap,
      padding: config.padding,
      fontFamily: fontFamily.sans,
      fontSize: config.fontSize,
      fontWeight: isActive ? fontWeight.medium : fontWeight.normal,
      border: 'none',
      background: 'none',
      cursor: disabled ? 'not-allowed' : 'pointer',
      opacity: disabled ? 0.5 : 1,
      flex: fullWidth ? 1 : 'none',
      transition: 'all 150ms ease-out',
      whiteSpace: 'nowrap' as const,
      ...getVariantStyles(),
    } as React.CSSProperties,

    badge: {
      marginLeft: spacing[2],
    },
  };

  return (
    <motion.button
      style={styles.trigger}
      onClick={() => !disabled && onChange(triggerValue)}
      role="tab"
      aria-selected={isActive}
      aria-disabled={disabled}
      data-state={isActive ? 'active' : 'inactive'}
      whileHover={!disabled && variant !== 'underline' ? { 
        backgroundColor: isActive 
          ? variant === 'pills' ? colors.primary[600] : colors.dark.elevated
          : colors.dark.subtle 
      } : {}}
      whileTap={!disabled ? { scale: 0.98 } : {}}
      className={className}
    >
      {icon && (
        <span style={{ 
          display: 'flex', 
          alignItems: 'center',
          opacity: isActive ? 1 : 0.7,
        }}>
          {icon}
        </span>
      )}
      {children}
      {badge && <span style={styles.badge}>{badge}</span>}
    </motion.button>
  );
};

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// TABS CONTENT COMPONENT
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

export const TabsContent: React.FC<TabsContentProps> = ({
  value: contentValue,
  forceMount = false,
  children,
  className = '',
}) => {
  const { value } = useTabs();
  const isActive = value === contentValue;

  const styles = {
    content: {
      paddingTop: spacing[4],
    },
  };

  // Force mount shows content but hides with CSS
  if (forceMount) {
    return (
      <div
        style={{
          ...styles.content,
          display: isActive ? 'block' : 'none',
        }}
        role="tabpanel"
        aria-hidden={!isActive}
        className={className}
      >
        {children}
      </div>
    );
  }

  // Default: animate in/out
  return (
    <AnimatePresence mode="wait">
      {isActive && (
        <motion.div
          key={contentValue}
          style={styles.content}
          variants={contentVariants}
          initial="hidden"
          animate="visible"
          exit="exit"
          role="tabpanel"
          className={className}
        >
          {children}
        </motion.div>
      )}
    </AnimatePresence>
  );
};

export default Tabs;
