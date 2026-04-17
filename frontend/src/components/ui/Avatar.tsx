/**
 * Avatar Component — AutomAção CAD Enterprise v2.0
 *
 * Elegant user avatar with status indicator and fallback initials.
 *
 * @usage
 * <Avatar src="/user.jpg" name="John Doe" />
 * <Avatar name="John Doe" status="online" />
 * <AvatarGroup max={3}>
 *   <Avatar src="/user1.jpg" />
 *   <Avatar src="/user2.jpg" />
 * </AvatarGroup>
 */

import React, { useState } from "react";
import { motion } from "framer-motion";
import { User } from "lucide-react";
import { colors, radius, shadows, spacing } from "../../design/tokens";
import { fontFamily, fontSize, fontWeight } from "../../design/typography";

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// TYPES
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

export type AvatarSize = "xs" | "sm" | "md" | "lg" | "xl" | "2xl";
export type AvatarStatus = "online" | "offline" | "away" | "busy" | "dnd";

export interface AvatarProps {
  src?: string;
  name?: string;
  size?: AvatarSize;
  status?: AvatarStatus;
  showStatus?: boolean;
  variant?: "circle" | "rounded" | "square";
  bordered?: boolean;
  className?: string;
  onClick?: () => void;
}

export interface AvatarGroupProps {
  max?: number;
  size?: AvatarSize;
  children: React.ReactNode;
  className?: string;
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// CONFIG
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

const sizeConfig: Record<
  AvatarSize,
  {
    size: number;
    fontSize: string;
    statusSize: number;
    iconSize: number;
  }
> = {
  xs: { size: 24, fontSize: fontSize.xs, statusSize: 6, iconSize: 12 },
  sm: { size: 32, fontSize: fontSize.xs, statusSize: 8, iconSize: 14 },
  md: { size: 40, fontSize: fontSize.sm, statusSize: 10, iconSize: 16 },
  lg: { size: 48, fontSize: fontSize.base, statusSize: 12, iconSize: 20 },
  xl: { size: 64, fontSize: fontSize.lg, statusSize: 14, iconSize: 24 },
  "2xl": { size: 96, fontSize: fontSize.xl, statusSize: 16, iconSize: 32 },
};

const statusColors: Record<AvatarStatus, string> = {
  online: colors.success.DEFAULT,
  offline: colors.text.tertiary,
  away: colors.warning.DEFAULT,
  busy: colors.danger.DEFAULT,
  dnd: colors.danger.DEFAULT,
};

// Generate gradient colors from name
const getGradientFromName = (name: string): string => {
  const gradients = [
    `linear-gradient(135deg, ${colors.primary.DEFAULT} 0%, ${colors.secondary.DEFAULT} 100%)`,
    `linear-gradient(135deg, #FF6B6B 0%, #FF8E53 100%)`,
    `linear-gradient(135deg, #4ECDC4 0%, #44CF6C 100%)`,
    `linear-gradient(135deg, #A855F7 0%, #EC4899 100%)`,
    `linear-gradient(135deg, #F59E0B 0%, #EF4444 100%)`,
    `linear-gradient(135deg, ${colors.gold.DEFAULT} 0%, #F59E0B 100%)`,
  ];

  const charSum = name
    .split("")
    .reduce((acc, char) => acc + char.charCodeAt(0), 0);
  return gradients[charSum % gradients.length];
};

// Get initials from name
const getInitials = (name: string): string => {
  if (!name) return "";
  const parts = name.trim().split(" ").filter(Boolean);
  if (parts.length === 0) return "";
  if (parts.length === 1) return parts[0].charAt(0).toUpperCase();
  return (parts[0].charAt(0) + parts[parts.length - 1].charAt(0)).toUpperCase();
};

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// MAIN AVATAR COMPONENT
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

export const Avatar: React.FC<AvatarProps> = ({
  src,
  name = "",
  size = "md",
  status,
  showStatus = true,
  variant = "circle",
  bordered = false,
  className = "",
  onClick,
}) => {
  const [imageError, setImageError] = useState(false);
  const config = sizeConfig[size];

  const getBorderRadius = (): string => {
    switch (variant) {
      case "rounded":
        return radius.lg;
      case "square":
        return radius.md;
      default:
        return radius.full;
    }
  };

  const styles = {
    container: {
      position: "relative" as const,
      display: "inline-flex",
      alignItems: "center",
      justifyContent: "center",
      width: `${config.size}px`,
      height: `${config.size}px`,
      borderRadius: getBorderRadius(),
      overflow: "hidden",
      cursor: onClick ? "pointer" : "default",
      flexShrink: 0,
      border: bordered ? `2px solid ${colors.dark.base}` : "none",
      boxShadow: bordered ? shadows.md : "none",
    },

    image: {
      width: "100%",
      height: "100%",
      objectFit: "cover" as const,
    },

    fallback: {
      width: "100%",
      height: "100%",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      background: name ? getGradientFromName(name) : colors.dark.elevated,
      fontFamily: fontFamily.sans,
      fontSize: config.fontSize,
      fontWeight: fontWeight.semibold,
      color: "#ffffff",
      textTransform: "uppercase" as const,
    },

    statusDot: {
      position: "absolute" as const,
      bottom: variant === "circle" ? "2px" : "0",
      right: variant === "circle" ? "2px" : "0",
      width: `${config.statusSize}px`,
      height: `${config.statusSize}px`,
      borderRadius: radius.full,
      backgroundColor: status ? statusColors[status] : colors.text.tertiary,
      border: `2px solid ${colors.dark.base}`,
      boxShadow: shadows.sm,
    },
  };

  const showFallback = !src || imageError;

  return (
    <motion.div
      style={styles.container}
      className={className}
      onClick={onClick}
      whileHover={onClick ? { scale: 1.05 } : {}}
      whileTap={onClick ? { scale: 0.95 } : {}}
    >
      {/* Image or Fallback */}
      {!showFallback ? (
        <img
          src={src}
          alt={name || "Avatar"}
          style={styles.image}
          onError={() => setImageError(true)}
        />
      ) : (
        <div style={styles.fallback}>
          {name ? getInitials(name) : <User size={config.iconSize} />}
        </div>
      )}

      {/* Status Indicator */}
      {status && showStatus && (
        <motion.div
          style={styles.statusDot}
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ type: "spring", stiffness: 500, damping: 30 }}
        />
      )}
    </motion.div>
  );
};

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// AVATAR GROUP COMPONENT
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

export const AvatarGroup: React.FC<AvatarGroupProps> = ({
  max = 4,
  size = "md",
  children,
  className = "",
}) => {
  const config = sizeConfig[size];
  const childArray = React.Children.toArray(children);
  const visibleAvatars = childArray.slice(0, max);
  const remainingCount = childArray.length - max;

  const styles = {
    group: {
      display: "flex",
      alignItems: "center",
    },

    avatarWrapper: {
      marginLeft: size === "xs" || size === "sm" ? "-8px" : "-12px",
      position: "relative" as const,
    },

    firstAvatarWrapper: {
      marginLeft: 0,
    },

    remaining: {
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      width: `${config.size}px`,
      height: `${config.size}px`,
      borderRadius: radius.full,
      backgroundColor: colors.dark.elevated,
      border: `2px solid ${colors.dark.base}`,
      marginLeft: size === "xs" || size === "sm" ? "-8px" : "-12px",
      fontFamily: fontFamily.sans,
      fontSize: config.fontSize,
      fontWeight: fontWeight.medium,
      color: colors.text.secondary,
    },
  };

  return (
    <div style={styles.group} className={className}>
      {visibleAvatars.map((child, index) => (
        <div
          key={index}
          style={{
            ...styles.avatarWrapper,
            ...(index === 0 ? styles.firstAvatarWrapper : {}),
            zIndex: visibleAvatars.length - index,
          }}
        >
          {React.cloneElement(child as React.ReactElement<AvatarProps>, {
            size,
            bordered: true,
          })}
        </div>
      ))}
      {remainingCount > 0 && (
        <div style={styles.remaining}>+{remainingCount}</div>
      )}
    </div>
  );
};

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// AVATAR WITH INFO (for lists, cards, etc.)
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

interface AvatarWithInfoProps extends AvatarProps {
  title: string;
  subtitle?: string;
  action?: React.ReactNode;
}

export const AvatarWithInfo: React.FC<AvatarWithInfoProps> = ({
  title,
  subtitle,
  action,
  ...avatarProps
}) => {
  const styles = {
    container: {
      display: "flex",
      alignItems: "center",
      gap: spacing[3],
    },

    info: {
      flex: 1,
      minWidth: 0,
    },

    title: {
      fontFamily: fontFamily.sans,
      fontSize: fontSize.sm,
      fontWeight: fontWeight.medium,
      color: colors.text.primary,
      margin: 0,
      overflow: "hidden",
      textOverflow: "ellipsis",
      whiteSpace: "nowrap" as const,
    },

    subtitle: {
      fontFamily: fontFamily.sans,
      fontSize: fontSize.xs,
      color: colors.text.secondary,
      margin: 0,
      marginTop: spacing[1],
      overflow: "hidden",
      textOverflow: "ellipsis",
      whiteSpace: "nowrap" as const,
    },
  };

  return (
    <div style={styles.container}>
      <Avatar {...avatarProps} />
      <div style={styles.info}>
        <p style={styles.title}>{title}</p>
        {subtitle && <p style={styles.subtitle}>{subtitle}</p>}
      </div>
      {action && <div>{action}</div>}
    </div>
  );
};

export default Avatar;
