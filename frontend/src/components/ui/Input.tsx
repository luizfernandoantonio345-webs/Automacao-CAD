/**
 * Input Component — AutomAção CAD Enterprise v2.0
 *
 * Premium input component with floating labels, icons, and validation states.
 *
 * @usage
 * <Input label="Email" type="email" leftIcon={<Mail />} />
 * <Input label="Password" type="password" error="Required" />
 */

import React, { forwardRef, InputHTMLAttributes, useState, useId } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { colors, radius, spacing, transitions } from "../../design/tokens";
import {
  fontFamily,
  fontSize,
  fontWeight,
  textStyles,
} from "../../design/typography";
import { fadeIn, slideUp } from "../../design/animations";

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// TYPES
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

export type InputSize = "sm" | "md" | "lg";
export type InputVariant = "default" | "filled" | "glass";

export interface InputProps extends Omit<
  InputHTMLAttributes<HTMLInputElement>,
  "size"
> {
  label?: string;
  helperText?: string;
  error?: string;
  success?: string;
  size?: InputSize;
  variant?: InputVariant;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
  floatingLabel?: boolean;
  fullWidth?: boolean;
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// SIZE STYLES
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

const sizeStyles: Record<
  InputSize,
  { height: string; fontSize: string; padding: string; iconSize: number }
> = {
  sm: {
    height: "36px",
    fontSize: fontSize.sm,
    padding: "0 12px",
    iconSize: 16,
  },
  md: {
    height: "44px",
    fontSize: fontSize.base,
    padding: "0 16px",
    iconSize: 18,
  },
  lg: {
    height: "52px",
    fontSize: fontSize.lg,
    padding: "0 20px",
    iconSize: 20,
  },
};

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// VARIANT STYLES
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

const variantStyles: Record<InputVariant, React.CSSProperties> = {
  default: {
    background: colors.dark.surface,
    border: `1px solid ${colors.border.default}`,
  },
  filled: {
    background: colors.dark.elevated,
    border: `1px solid transparent`,
  },
  glass: {
    background: "rgba(255, 255, 255, 0.03)",
    backdropFilter: "blur(12px)",
    WebkitBackdropFilter: "blur(12px)",
    border: `1px solid ${colors.border.subtle}`,
  },
};

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// INPUT COMPONENT
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

export const Input = forwardRef<HTMLInputElement, InputProps>(
  (
    {
      label,
      helperText,
      error,
      success,
      size = "md",
      variant = "default",
      leftIcon,
      rightIcon,
      floatingLabel = false,
      fullWidth = true,
      disabled,
      id: providedId,
      onFocus,
      onBlur,
      value,
      defaultValue,
      style,
      className,
      ...props
    },
    ref,
  ) => {
    const generatedId = useId();
    const id = providedId || generatedId;
    const [isFocused, setIsFocused] = useState(false);
    const [hasValue, setHasValue] = useState(Boolean(value || defaultValue));

    const sizeStyle = sizeStyles[size];
    const variantStyle = variantStyles[variant];

    const hasError = Boolean(error);
    const hasSuccess = Boolean(success);

    // Determine border color based on state
    const getBorderColor = () => {
      if (hasError) return colors.danger.DEFAULT;
      if (hasSuccess) return colors.success.DEFAULT;
      if (isFocused) return colors.primary.DEFAULT;
      return undefined; // Use variant default
    };

    const borderColor = getBorderColor();

    // Handle focus/blur
    const handleFocus = (e: React.FocusEvent<HTMLInputElement>) => {
      setIsFocused(true);
      onFocus?.(e);
    };

    const handleBlur = (e: React.FocusEvent<HTMLInputElement>) => {
      setIsFocused(false);
      setHasValue(Boolean(e.target.value));
      onBlur?.(e);
    };

    const containerStyles: React.CSSProperties = {
      position: "relative",
      width: fullWidth ? "100%" : "auto",
      ...style,
    };

    const inputWrapperStyles: React.CSSProperties = {
      position: "relative",
      display: "flex",
      alignItems: "center",
      height: sizeStyle.height,
      borderRadius: radius.md,
      transition: `all ${transitions.default}`,
      ...variantStyle,
      ...(borderColor ? { borderColor } : {}),
      ...(isFocused ? { boxShadow: `0 0 0 3px ${colors.primary.soft}` } : {}),
      ...(disabled ? { opacity: 0.5, cursor: "not-allowed" } : {}),
    };

    const inputStyles: React.CSSProperties = {
      flex: 1,
      width: "100%",
      height: "100%",
      padding: sizeStyle.padding,
      paddingLeft: leftIcon
        ? `calc(${sizeStyle.padding.split(" ")[1]} + ${sizeStyle.iconSize + 12}px)`
        : undefined,
      paddingRight: rightIcon
        ? `calc(${sizeStyle.padding.split(" ")[1]} + ${sizeStyle.iconSize + 12}px)`
        : undefined,
      background: "transparent",
      border: "none",
      outline: "none",
      fontFamily: fontFamily.sans,
      fontSize: sizeStyle.fontSize,
      fontWeight: fontWeight.normal,
      color: colors.text.primary,
      caretColor: colors.primary.DEFAULT,
    };

    const iconStyles = (position: "left" | "right"): React.CSSProperties => ({
      position: "absolute",
      [position]: "14px",
      top: "50%",
      transform: "translateY(-50%)",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      width: sizeStyle.iconSize,
      height: sizeStyle.iconSize,
      color: isFocused ? colors.primary.DEFAULT : colors.text.tertiary,
      transition: `color ${transitions.fast}`,
      pointerEvents: "none",
    });

    const labelStyles: React.CSSProperties = {
      display: "block",
      marginBottom: spacing[2],
      ...textStyles.label.md,
      color: hasError ? colors.danger.DEFAULT : colors.text.secondary,
    };

    const floatingLabelStyles: React.CSSProperties = {
      position: "absolute",
      left: leftIcon ? `${sizeStyle.iconSize + 24}px` : "16px",
      top: isFocused || hasValue ? "4px" : "50%",
      transform: isFocused || hasValue ? "translateY(0)" : "translateY(-50%)",
      fontSize: isFocused || hasValue ? fontSize.xs : sizeStyle.fontSize,
      fontWeight: fontWeight.medium,
      color: hasError
        ? colors.danger.DEFAULT
        : isFocused
          ? colors.primary.DEFAULT
          : colors.text.tertiary,
      transition: `all ${transitions.fast}`,
      pointerEvents: "none",
      backgroundColor:
        variant === "default" ? colors.dark.surface : "transparent",
      padding: isFocused || hasValue ? "0 4px" : "0",
    };

    const messageStyles: React.CSSProperties = {
      display: "flex",
      alignItems: "center",
      gap: spacing[1],
      marginTop: spacing[1],
      ...textStyles.caption,
    };

    return (
      <div style={containerStyles}>
        {/* Standard Label */}
        {label && !floatingLabel && (
          <label htmlFor={id} style={labelStyles}>
            {label}
          </label>
        )}

        {/* Input Wrapper */}
        <div style={inputWrapperStyles}>
          {/* Left Icon */}
          {leftIcon && <span style={iconStyles("left")}>{leftIcon}</span>}

          {/* Floating Label */}
          {label && floatingLabel && (
            <span style={floatingLabelStyles}>{label}</span>
          )}

          {/* Input */}
          <input
            ref={ref}
            id={id}
            disabled={disabled}
            aria-invalid={hasError}
            aria-describedby={
              error ? `${id}-error` : helperText ? `${id}-helper` : undefined
            }
            style={inputStyles}
            onFocus={handleFocus}
            onBlur={handleBlur}
            value={value}
            defaultValue={defaultValue}
            {...props}
          />

          {/* Right Icon */}
          {rightIcon && <span style={iconStyles("right")}>{rightIcon}</span>}
        </div>

        {/* Helper/Error/Success Messages */}
        <AnimatePresence mode="wait">
          {error && (
            <motion.p
              key="error"
              id={`${id}-error`}
              role="alert"
              style={{ ...messageStyles, color: colors.danger.DEFAULT }}
              variants={slideUp}
              initial="hidden"
              animate="visible"
              exit="exit"
            >
              <svg
                width="14"
                height="14"
                viewBox="0 0 24 24"
                fill="currentColor"
              >
                <path d="M12 22C6.477 22 2 17.523 2 12S6.477 2 12 2s10 4.477 10 10-4.477 10-10 10zm-1-7v2h2v-2h-2zm0-8v6h2V7h-2z" />
              </svg>
              {error}
            </motion.p>
          )}

          {success && !error && (
            <motion.p
              key="success"
              style={{ ...messageStyles, color: colors.success.DEFAULT }}
              variants={slideUp}
              initial="hidden"
              animate="visible"
              exit="exit"
            >
              <svg
                width="14"
                height="14"
                viewBox="0 0 24 24"
                fill="currentColor"
              >
                <path d="M12 22C6.477 22 2 17.523 2 12S6.477 2 12 2s10 4.477 10 10-4.477 10-10 10zm-.997-6l7.07-7.071-1.414-1.414-5.656 5.657-2.829-2.829-1.414 1.414L11.003 16z" />
              </svg>
              {success}
            </motion.p>
          )}

          {helperText && !error && !success && (
            <motion.p
              key="helper"
              id={`${id}-helper`}
              style={{ ...messageStyles, color: colors.text.tertiary }}
              variants={fadeIn}
              initial="hidden"
              animate="visible"
            >
              {helperText}
            </motion.p>
          )}
        </AnimatePresence>
      </div>
    );
  },
);

Input.displayName = "Input";

export default Input;
