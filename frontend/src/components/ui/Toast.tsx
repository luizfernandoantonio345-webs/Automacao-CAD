/**
 * Toast Component — AutomAção CAD Enterprise v2.0
 *
 * Elegant toast notifications with auto-dismiss and stacking.
 *
 * @usage
 * // Wrap app with ToastProvider
 * <ToastProvider>
 *   <App />
 * </ToastProvider>
 *
 * // Use hook to show toasts
 * const { toast } = useToast();
 * toast.success('Saved successfully!');
 * toast.error('Something went wrong');
 */

import React, { createContext, useContext, useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { CheckCircle, XCircle, AlertTriangle, Info, X } from "lucide-react";
import { colors, radius, shadows, spacing, zIndex } from "../../design/tokens";
import { fontFamily, fontSize, fontWeight } from "../../design/typography";

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// TYPES
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

export type ToastType = "success" | "error" | "warning" | "info";
export type ToastPosition =
  | "top-right"
  | "top-left"
  | "top-center"
  | "bottom-right"
  | "bottom-left"
  | "bottom-center";

export interface ToastItem {
  id: string;
  type: ToastType;
  title: string;
  description?: string;
  duration?: number;
  action?: {
    label: string;
    onClick: () => void;
  };
}

export interface ToastProps {
  toast: ToastItem;
  onDismiss: (id: string) => void;
}

interface ToastContextValue {
  toasts: ToastItem[];
  addToast: (toast: Omit<ToastItem, "id">) => string;
  removeToast: (id: string) => void;
  toast: {
    success: (title: string, description?: string) => string;
    error: (title: string, description?: string) => string;
    warning: (title: string, description?: string) => string;
    info: (title: string, description?: string) => string;
  };
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// CONTEXT
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

const ToastContext = createContext<ToastContextValue | null>(null);

export const useToast = () => {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error("useToast must be used within a ToastProvider");
  }
  return context;
};

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// CONFIG
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

const typeConfig = {
  success: {
    icon: CheckCircle,
    color: colors.success.DEFAULT,
    background: colors.success.soft,
    border: colors.success.DEFAULT,
  },
  error: {
    icon: XCircle,
    color: colors.danger.DEFAULT,
    background: colors.danger.soft,
    border: colors.danger.DEFAULT,
  },
  warning: {
    icon: AlertTriangle,
    color: colors.warning.DEFAULT,
    background: colors.warning.soft,
    border: colors.warning.DEFAULT,
  },
  info: {
    icon: Info,
    color: colors.primary.DEFAULT,
    background: colors.primary.soft,
    border: colors.primary.DEFAULT,
  },
};

const positionStyles: Record<ToastPosition, React.CSSProperties> = {
  "top-right": { top: spacing[4], right: spacing[4] },
  "top-left": { top: spacing[4], left: spacing[4] },
  "top-center": { top: spacing[4], left: "50%", transform: "translateX(-50%)" },
  "bottom-right": { bottom: spacing[4], right: spacing[4] },
  "bottom-left": { bottom: spacing[4], left: spacing[4] },
  "bottom-center": {
    bottom: spacing[4],
    left: "50%",
    transform: "translateX(-50%)",
  },
};

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// ANIMATION VARIANTS
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

const toastVariants = {
  hidden: {
    opacity: 0,
    y: -20,
    scale: 0.95,
  },
  visible: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: {
      type: "spring",
      stiffness: 400,
      damping: 25,
    },
  },
  exit: {
    opacity: 0,
    x: 100,
    scale: 0.95,
    transition: {
      duration: 0.2,
    },
  },
};

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// SINGLE TOAST COMPONENT
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

const Toast: React.FC<ToastProps> = ({ toast, onDismiss }) => {
  const config = typeConfig[toast.type];
  const Icon = config.icon;

  const styles = {
    toast: {
      display: "flex",
      alignItems: "flex-start",
      gap: spacing[3],
      padding: spacing[4],
      backgroundColor: colors.dark.elevated,
      borderRadius: radius.lg,
      border: `1px solid ${colors.border.subtle}`,
      borderLeft: `4px solid ${config.border}`,
      boxShadow: shadows.lg,
      minWidth: "320px",
      maxWidth: "420px",
    },

    iconWrapper: {
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      width: "24px",
      height: "24px",
      borderRadius: radius.full,
      backgroundColor: config.background,
      flexShrink: 0,
    },

    icon: {
      color: config.color,
    },

    content: {
      flex: 1,
      minWidth: 0,
    },

    title: {
      fontFamily: fontFamily.sans,
      fontSize: fontSize.sm,
      fontWeight: fontWeight.semibold,
      color: colors.text.primary,
      margin: 0,
      lineHeight: 1.4,
    },

    description: {
      fontFamily: fontFamily.sans,
      fontSize: fontSize.sm,
      color: colors.text.secondary,
      margin: 0,
      marginTop: spacing[1],
      lineHeight: 1.5,
    },

    closeButton: {
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      width: "24px",
      height: "24px",
      padding: 0,
      border: "none",
      background: "none",
      color: colors.text.tertiary,
      cursor: "pointer",
      borderRadius: radius.sm,
      transition: "all 150ms ease-out",
      flexShrink: 0,
    },

    action: {
      marginTop: spacing[3],
      padding: `${spacing[2]} ${spacing[3]}`,
      fontFamily: fontFamily.sans,
      fontSize: fontSize.sm,
      fontWeight: fontWeight.medium,
      color: config.color,
      backgroundColor: "transparent",
      border: `1px solid ${config.color}`,
      borderRadius: radius.md,
      cursor: "pointer",
      transition: "all 150ms ease-out",
    },

    progressBar: {
      position: "absolute" as const,
      bottom: 0,
      left: 0,
      height: "3px",
      backgroundColor: config.color,
      borderRadius: `0 0 0 ${radius.lg}`,
    },
  };

  return (
    <motion.div
      style={{ ...styles.toast, position: "relative", overflow: "hidden" }}
      variants={toastVariants}
      initial="hidden"
      animate="visible"
      exit="exit"
      layout
    >
      {/* Icon */}
      <div style={styles.iconWrapper}>
        <Icon size={14} style={styles.icon} />
      </div>

      {/* Content */}
      <div style={styles.content}>
        <p style={styles.title}>{toast.title}</p>
        {toast.description && (
          <p style={styles.description}>{toast.description}</p>
        )}
        {toast.action && (
          <motion.button
            style={styles.action}
            onClick={() => {
              toast.action?.onClick();
              onDismiss(toast.id);
            }}
            whileHover={{ backgroundColor: config.background }}
            whileTap={{ scale: 0.98 }}
          >
            {toast.action.label}
          </motion.button>
        )}
      </div>

      {/* Close Button */}
      <motion.button
        style={styles.closeButton}
        onClick={() => onDismiss(toast.id)}
        whileHover={{
          backgroundColor: colors.dark.subtle,
          color: colors.text.primary,
        }}
        whileTap={{ scale: 0.9 }}
        aria-label="Fechar notificação"
      >
        <X size={16} />
      </motion.button>

      {/* Progress Bar */}
      {toast.duration && toast.duration > 0 && (
        <motion.div
          style={styles.progressBar}
          initial={{ width: "100%" }}
          animate={{ width: "0%" }}
          transition={{ duration: toast.duration / 1000, ease: "linear" }}
        />
      )}
    </motion.div>
  );
};

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// TOAST PROVIDER
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

interface ToastProviderProps {
  position?: ToastPosition;
  maxToasts?: number;
  children: React.ReactNode;
}

export const ToastProvider: React.FC<ToastProviderProps> = ({
  position = "top-right",
  maxToasts = 5,
  children,
}) => {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const generateId = () =>
    `toast-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

  const addToast = useCallback(
    (toast: Omit<ToastItem, "id">) => {
      const id = generateId();
      const duration = toast.duration ?? 5000;

      setToasts((prev) => {
        const newToasts = [...prev, { ...toast, id, duration }];
        // Limit number of toasts
        return newToasts.slice(-maxToasts);
      });

      // Auto dismiss
      if (duration > 0) {
        setTimeout(() => {
          removeToast(id);
        }, duration);
      }

      return id;
    },
    [maxToasts],
  );

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  // Shorthand methods
  const toast = {
    success: (title: string, description?: string) =>
      addToast({ type: "success", title, description }),
    error: (title: string, description?: string) =>
      addToast({ type: "error", title, description }),
    warning: (title: string, description?: string) =>
      addToast({ type: "warning", title, description }),
    info: (title: string, description?: string) =>
      addToast({ type: "info", title, description }),
  };

  const containerStyles: React.CSSProperties = {
    position: "fixed",
    display: "flex",
    flexDirection: position.startsWith("bottom") ? "column-reverse" : "column",
    gap: spacing[3],
    zIndex: zIndex.toast,
    pointerEvents: "none",
    ...positionStyles[position],
  };

  return (
    <ToastContext.Provider value={{ toasts, addToast, removeToast, toast }}>
      {children}
      <div style={containerStyles}>
        <AnimatePresence mode="popLayout">
          {toasts.map((t) => (
            <div key={t.id} style={{ pointerEvents: "auto" }}>
              <Toast toast={t} onDismiss={removeToast} />
            </div>
          ))}
        </AnimatePresence>
      </div>
    </ToastContext.Provider>
  );
};

export default Toast;
