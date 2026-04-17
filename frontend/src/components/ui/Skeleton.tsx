/**
 * Skeleton Component — AutomAção CAD Enterprise v2.0
 *
 * Elegant loading placeholder with shimmer animation.
 *
 * @usage
 * <Skeleton width="100%" height="20px" />
 * <Skeleton variant="circle" size="48px" />
 * <Skeleton variant="text" lines={3} />
 * <SkeletonCard />
 */

import React from "react";
import { motion } from "framer-motion";
import { colors, radius, spacing } from "../../design/tokens";

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// TYPES
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

export interface SkeletonProps {
  variant?: "rectangle" | "circle" | "text" | "rounded";
  width?: string | number;
  height?: string | number;
  size?: string | number; // For circle variant
  lines?: number; // For text variant
  animation?: "pulse" | "shimmer" | "none";
  className?: string;
}

export interface SkeletonCardProps {
  hasImage?: boolean;
  lines?: number;
  className?: string;
}

export interface SkeletonListProps {
  items?: number;
  hasAvatar?: boolean;
  className?: string;
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// KEYFRAMES (inline as CSS variables don't work with motion)
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

const shimmerKeyframes = {
  "0%": { backgroundPosition: "200% 0" },
  "100%": { backgroundPosition: "-200% 0" },
};

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// STYLES
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

const baseStyle: React.CSSProperties = {
  backgroundColor: colors.dark.subtle,
  backgroundImage: `linear-gradient(
    90deg,
    ${colors.dark.subtle} 0%,
    ${colors.dark.elevated} 50%,
    ${colors.dark.subtle} 100%
  )`,
  backgroundSize: "200% 100%",
};

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// MAIN SKELETON COMPONENT
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

export const Skeleton: React.FC<SkeletonProps> = ({
  variant = "rectangle",
  width,
  height,
  size,
  lines = 1,
  animation = "shimmer",
  className = "",
}) => {
  // Get variant-specific styles
  const getVariantStyles = (): React.CSSProperties => {
    switch (variant) {
      case "circle":
        const circleSize = size || "48px";
        return {
          width: circleSize,
          height: circleSize,
          borderRadius: radius.full,
        };
      case "text":
        return {
          width: "100%",
          height: "14px",
          borderRadius: radius.sm,
        };
      case "rounded":
        return {
          width: width || "100%",
          height: height || "20px",
          borderRadius: radius.lg,
        };
      default:
        return {
          width: width || "100%",
          height: height || "20px",
          borderRadius: radius.md,
        };
    }
  };

  // Animation config
  const getAnimationProps = () => {
    switch (animation) {
      case "pulse":
        return {
          animate: { opacity: [1, 0.5, 1] },
          transition: { duration: 1.5, repeat: Infinity, ease: "easeInOut" },
        };
      case "shimmer":
        return {
          animate: { backgroundPosition: ["200% 0", "-200% 0"] },
          transition: { duration: 1.5, repeat: Infinity, ease: "linear" },
        };
      default:
        return {};
    }
  };

  const style: React.CSSProperties = {
    ...baseStyle,
    ...getVariantStyles(),
    display: "block",
  };

  // Multiple lines for text variant
  if (variant === "text" && lines > 1) {
    return (
      <div
        style={{ display: "flex", flexDirection: "column", gap: spacing[2] }}
        className={className}
      >
        {Array.from({ length: lines }).map((_, index) => (
          <motion.div
            key={index}
            style={{
              ...style,
              width: index === lines - 1 ? "70%" : "100%", // Last line shorter
            }}
            {...getAnimationProps()}
          />
        ))}
      </div>
    );
  }

  return (
    <motion.div style={style} className={className} {...getAnimationProps()} />
  );
};

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// SKELETON CARD PRESET
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

export const SkeletonCard: React.FC<SkeletonCardProps> = ({
  hasImage = true,
  lines = 3,
  className = "",
}) => {
  const styles = {
    card: {
      backgroundColor: colors.dark.elevated,
      borderRadius: radius.lg,
      border: `1px solid ${colors.border.subtle}`,
      overflow: "hidden",
    },
    image: {
      width: "100%",
      height: "160px",
    },
    content: {
      padding: spacing[4],
      display: "flex",
      flexDirection: "column" as const,
      gap: spacing[3],
    },
  };

  return (
    <div style={styles.card} className={className}>
      {hasImage && <Skeleton variant="rectangle" width="100%" height="160px" />}
      <div style={styles.content}>
        <Skeleton variant="text" width="60%" height="20px" />
        <Skeleton variant="text" lines={lines} />
      </div>
    </div>
  );
};

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// SKELETON LIST PRESET
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

export const SkeletonList: React.FC<SkeletonListProps> = ({
  items = 5,
  hasAvatar = true,
  className = "",
}) => {
  const styles = {
    list: {
      display: "flex",
      flexDirection: "column" as const,
      gap: spacing[3],
    },
    item: {
      display: "flex",
      alignItems: "center",
      gap: spacing[3],
      padding: spacing[4],
      backgroundColor: colors.dark.elevated,
      borderRadius: radius.lg,
      border: `1px solid ${colors.border.subtle}`,
    },
    content: {
      flex: 1,
      display: "flex",
      flexDirection: "column" as const,
      gap: spacing[2],
    },
  };

  return (
    <div style={styles.list} className={className}>
      {Array.from({ length: items }).map((_, index) => (
        <div key={index} style={styles.item}>
          {hasAvatar && <Skeleton variant="circle" size="48px" />}
          <div style={styles.content}>
            <Skeleton width="40%" height="16px" />
            <Skeleton width="70%" height="14px" />
          </div>
        </div>
      ))}
    </div>
  );
};

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// SKELETON TABLE PRESET
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

interface SkeletonTableProps {
  rows?: number;
  columns?: number;
  className?: string;
}

export const SkeletonTable: React.FC<SkeletonTableProps> = ({
  rows = 5,
  columns = 4,
  className = "",
}) => {
  const styles = {
    table: {
      width: "100%",
      borderRadius: radius.lg,
      border: `1px solid ${colors.border.subtle}`,
      overflow: "hidden",
    },
    header: {
      display: "grid",
      gridTemplateColumns: `repeat(${columns}, 1fr)`,
      gap: spacing[4],
      padding: spacing[4],
      backgroundColor: colors.dark.surface,
      borderBottom: `1px solid ${colors.border.subtle}`,
    },
    body: {
      display: "flex",
      flexDirection: "column" as const,
    },
    row: {
      display: "grid",
      gridTemplateColumns: `repeat(${columns}, 1fr)`,
      gap: spacing[4],
      padding: spacing[4],
      borderBottom: `1px solid ${colors.border.subtle}`,
    },
  };

  return (
    <div style={styles.table} className={className}>
      {/* Header */}
      <div style={styles.header}>
        {Array.from({ length: columns }).map((_, i) => (
          <Skeleton key={i} width="80%" height="14px" />
        ))}
      </div>

      {/* Body */}
      <div style={styles.body}>
        {Array.from({ length: rows }).map((_, rowIndex) => (
          <div
            key={rowIndex}
            style={{
              ...styles.row,
              borderBottom:
                rowIndex === rows - 1 ? "none" : styles.row.borderBottom,
            }}
          >
            {Array.from({ length: columns }).map((_, colIndex) => (
              <Skeleton
                key={colIndex}
                width={colIndex === 0 ? "60%" : "90%"}
                height="14px"
              />
            ))}
          </div>
        ))}
      </div>
    </div>
  );
};

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// SKELETON DASHBOARD KPI
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

export const SkeletonKPI: React.FC<{ className?: string }> = ({
  className,
}) => {
  const styles = {
    card: {
      padding: spacing[5],
      backgroundColor: colors.dark.elevated,
      borderRadius: radius.xl,
      border: `1px solid ${colors.border.subtle}`,
      display: "flex",
      flexDirection: "column" as const,
      gap: spacing[3],
    },
  };

  return (
    <div style={styles.card} className={className}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <Skeleton width="50%" height="14px" />
        <Skeleton variant="circle" size="40px" />
      </div>
      <Skeleton width="70%" height="32px" />
      <Skeleton width="40%" height="12px" />
    </div>
  );
};

export default Skeleton;
