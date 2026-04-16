/**
 * BottomTabBar Component — AutomAção CAD Enterprise v2.0
 * 
 * Mobile-first bottom navigation bar with 4-5 main tabs.
 * Fixed at bottom on mobile, hidden on desktop.
 * 
 * @usage
 * <BottomTabBar
 *   items={[
 *     { id: 'home', icon: <Home />, label: 'Home', path: '/' },
 *     { id: 'cad', icon: <Layers />, label: 'CAD', path: '/cad' },
 *   ]}
 *   activeId="home"
 * />
 */

import React from 'react';
import { motion } from 'framer-motion';
import { useNavigate, useLocation } from 'react-router-dom';
import { colors, radius, shadows, spacing, zIndex, blur, breakpoints } from '../../design/tokens';
import { fontFamily, fontSize, fontWeight } from '../../design/typography';
import { tapScale } from '../../design/animations';

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// TYPES
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

export interface TabItem {
  id: string;
  icon: React.ReactNode;
  label: string;
  path: string;
  badge?: number | string;
}

export interface BottomTabBarProps {
  items: TabItem[];
  activeId?: string;
  onTabChange?: (id: string, path: string) => void;
  hideOnDesktop?: boolean;
}


// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// COMPONENT
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

export const BottomTabBar: React.FC<BottomTabBarProps> = ({
  items,
  activeId,
  onTabChange,
  hideOnDesktop = true,
}) => {
  const navigate = useNavigate();
  const location = useLocation();
  
  // Determine active tab from current route if not provided
  const currentActiveId = activeId || items.find(item => 
    location.pathname === item.path || 
    (item.path !== '/' && location.pathname.startsWith(item.path))
  )?.id || items[0]?.id;

  const handleTabClick = (item: TabItem) => {
    if (onTabChange) {
      onTabChange(item.id, item.path);
    } else {
      navigate(item.path);
    }
  };

  // Safe area padding for iOS devices
  const safeAreaBottom = 'env(safe-area-inset-bottom, 0px)';

  const containerStyles: React.CSSProperties = {
    position: 'fixed',
    bottom: 0,
    left: 0,
    right: 0,
    zIndex: zIndex.docked,
    
    // Glass effect
    background: 'rgba(8, 11, 18, 0.85)',
    backdropFilter: `blur(${blur.lg})`,
    WebkitBackdropFilter: `blur(${blur.lg})`,
    
    // Border & shadow
    borderTop: `1px solid ${colors.border.subtle}`,
    boxShadow: '0 -4px 20px rgba(0, 0, 0, 0.3)',
    
    // Safe area padding
    paddingBottom: safeAreaBottom,
  };

  const innerContainerStyles: React.CSSProperties = {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-around',
    height: '64px',
    maxWidth: '600px',
    margin: '0 auto',
    padding: `0 ${spacing[2]}`,
  };

  return (
    <>
      {/* Spacer to prevent content from being hidden behind the bar */}
      <div 
        style={{ 
          height: '64px',
          paddingBottom: safeAreaBottom,
        }} 
        aria-hidden="true"
        className="bottom-tab-spacer"
      />
      
      <nav
        role="navigation"
        aria-label="Main navigation"
        style={containerStyles}
        className={hideOnDesktop ? 'bottom-tab-bar-mobile' : ''}
      >
        <div style={innerContainerStyles}>
          {items.map((item) => (
            <TabButton
              key={item.id}
              item={item}
              isActive={item.id === currentActiveId}
              onClick={() => handleTabClick(item)}
            />
          ))}
        </div>
      </nav>
      
      {/* CSS for hiding on desktop */}
      {hideOnDesktop && (
        <style>{`
          @media (min-width: ${breakpoints.lg}px) {
            .bottom-tab-bar-mobile,
            .bottom-tab-spacer {
              display: none !important;
            }
          }
        `}</style>
      )}
    </>
  );
};


// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// TAB BUTTON
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

interface TabButtonProps {
  item: TabItem;
  isActive: boolean;
  onClick: () => void;
}

const TabButton: React.FC<TabButtonProps> = ({ item, isActive, onClick }) => {
  const buttonStyles: React.CSSProperties = {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '4px',
    
    // Size
    flex: 1,
    maxWidth: '80px',
    height: '56px',
    padding: '8px 12px',
    
    // Reset
    background: 'transparent',
    border: 'none',
    outline: 'none',
    cursor: 'pointer',
    
    // Transitions
    transition: 'all 200ms ease-out',
    
    // Touch target
    WebkitTapHighlightColor: 'transparent',
  };

  const iconWrapperStyles: React.CSSProperties = {
    position: 'relative',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    width: '44px',
    height: '28px',
    borderRadius: radius.full,
    background: isActive ? colors.primary.soft : 'transparent',
    transition: 'all 200ms ease-out',
  };

  const iconStyles: React.CSSProperties = {
    width: '22px',
    height: '22px',
    color: isActive ? colors.primary.DEFAULT : colors.text.tertiary,
    transition: 'color 200ms ease-out',
  };

  const labelStyles: React.CSSProperties = {
    fontFamily: fontFamily.sans,
    fontSize: '11px',
    fontWeight: isActive ? fontWeight.semibold : fontWeight.medium,
    color: isActive ? colors.primary.DEFAULT : colors.text.tertiary,
    transition: 'all 200ms ease-out',
    whiteSpace: 'nowrap',
  };

  const badgeStyles: React.CSSProperties = {
    position: 'absolute',
    top: '-2px',
    right: '4px',
    minWidth: '16px',
    height: '16px',
    padding: '0 4px',
    borderRadius: radius.full,
    background: colors.danger.DEFAULT,
    color: '#FFFFFF',
    fontSize: '10px',
    fontWeight: fontWeight.bold,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  };

  return (
    <motion.button
      style={buttonStyles}
      onClick={onClick}
      whileTap={tapScale}
      aria-label={item.label}
      aria-current={isActive ? 'page' : undefined}
    >
      <div style={iconWrapperStyles}>
        {/* Active indicator pill */}
        {isActive && (
          <motion.div
            layoutId="activeTab"
            style={{
              position: 'absolute',
              inset: 0,
              borderRadius: radius.full,
              background: colors.primary.soft,
            }}
            transition={{
              type: 'spring',
              stiffness: 500,
              damping: 35,
            }}
          />
        )}
        
        <span style={iconStyles}>
          {item.icon}
        </span>
        
        {/* Badge */}
        {item.badge !== undefined && (
          <span style={badgeStyles}>
            {typeof item.badge === 'number' && item.badge > 99 ? '99+' : item.badge}
          </span>
        )}
      </div>
      
      <span style={labelStyles}>
        {item.label}
      </span>
    </motion.button>
  );
};

BottomTabBar.displayName = 'BottomTabBar';

export default BottomTabBar;
