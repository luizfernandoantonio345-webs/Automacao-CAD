/**
 * Select Component — AutomAção CAD Enterprise v2.0
 * 
 * Custom styled dropdown select with search, icons, and animations.
 * 
 * @usage
 * <Select
 *   options={[{ value: 'opt1', label: 'Option 1' }]}
 *   value={selected}
 *   onChange={setSelected}
 *   placeholder="Select an option"
 * />
 */

import React, { useState, useRef, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronDown, Check, Search, X } from 'lucide-react';
import { colors, radius, shadows, spacing, zIndex } from '../../design/tokens';
import { fontFamily, fontSize, fontWeight } from '../../design/typography';

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// TYPES
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

export interface SelectOption {
  value: string;
  label: string;
  icon?: React.ReactNode;
  description?: string;
  disabled?: boolean;
}

export interface SelectProps {
  options: SelectOption[];
  value?: string | string[];
  onChange: (value: string | string[]) => void;
  placeholder?: string;
  label?: string;
  helperText?: string;
  error?: string;
  disabled?: boolean;
  searchable?: boolean;
  clearable?: boolean;
  multiple?: boolean;
  variant?: 'default' | 'filled' | 'glass';
  size?: 'sm' | 'md' | 'lg';
  fullWidth?: boolean;
  className?: string;
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// SIZE CONFIG
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

const sizeConfig = {
  sm: {
    height: '36px',
    padding: `0 ${spacing[3]}`,
    fontSize: fontSize.sm,
    iconSize: 16,
  },
  md: {
    height: '44px',
    padding: `0 ${spacing[4]}`,
    fontSize: fontSize.base,
    iconSize: 18,
  },
  lg: {
    height: '52px',
    padding: `0 ${spacing[5]}`,
    fontSize: fontSize.lg,
    iconSize: 20,
  },
};

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// ANIMATION VARIANTS
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

const dropdownVariants = {
  hidden: { 
    opacity: 0, 
    y: -8,
    scale: 0.98,
  },
  visible: { 
    opacity: 1, 
    y: 0,
    scale: 1,
    transition: {
      type: 'spring',
      stiffness: 500,
      damping: 30,
    },
  },
  exit: { 
    opacity: 0, 
    y: -8,
    scale: 0.98,
    transition: { duration: 0.1 },
  },
};

const itemVariants = {
  hidden: { opacity: 0, x: -10 },
  visible: { opacity: 1, x: 0 },
};

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// MAIN SELECT COMPONENT
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

export const Select: React.FC<SelectProps> = ({
  options,
  value,
  onChange,
  placeholder = 'Selecione...',
  label,
  helperText,
  error,
  disabled = false,
  searchable = false,
  clearable = false,
  multiple = false,
  variant = 'default',
  size = 'md',
  fullWidth = false,
  className = '',
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [highlightedIndex, setHighlightedIndex] = useState(-1);
  const containerRef = useRef<HTMLDivElement>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);
  const config = sizeConfig[size];

  // Get selected options
  const selectedValues = multiple 
    ? (Array.isArray(value) ? value : []) 
    : (value ? [value] : []);

  const selectedOptions = options.filter(opt => selectedValues.includes(opt.value));

  // Filter options based on search
  const filteredOptions = searchQuery
    ? options.filter(opt => 
        opt.label.toLowerCase().includes(searchQuery.toLowerCase()) ||
        opt.description?.toLowerCase().includes(searchQuery.toLowerCase())
      )
    : options;

  // Handle click outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
        setSearchQuery('');
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Focus search input when opened
  useEffect(() => {
    if (isOpen && searchable && searchInputRef.current) {
      searchInputRef.current.focus();
    }
  }, [isOpen, searchable]);

  // Handle keyboard navigation
  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (disabled) return;

    switch (e.key) {
      case 'Enter':
      case ' ':
        e.preventDefault();
        if (!isOpen) {
          setIsOpen(true);
        } else if (highlightedIndex >= 0 && filteredOptions[highlightedIndex]) {
          handleSelect(filteredOptions[highlightedIndex].value);
        }
        break;
      case 'Escape':
        setIsOpen(false);
        setSearchQuery('');
        break;
      case 'ArrowDown':
        e.preventDefault();
        if (!isOpen) {
          setIsOpen(true);
        } else {
          setHighlightedIndex(prev => 
            prev < filteredOptions.length - 1 ? prev + 1 : 0
          );
        }
        break;
      case 'ArrowUp':
        e.preventDefault();
        setHighlightedIndex(prev => 
          prev > 0 ? prev - 1 : filteredOptions.length - 1
        );
        break;
    }
  }, [disabled, isOpen, highlightedIndex, filteredOptions]);

  // Handle option selection
  const handleSelect = (optValue: string) => {
    if (multiple) {
      const newValue = selectedValues.includes(optValue)
        ? selectedValues.filter(v => v !== optValue)
        : [...selectedValues, optValue];
      onChange(newValue);
    } else {
      onChange(optValue);
      setIsOpen(false);
      setSearchQuery('');
    }
  };

  // Clear selection
  const handleClear = (e: React.MouseEvent) => {
    e.stopPropagation();
    onChange(multiple ? [] : '');
  };

  // Variant styles
  const getVariantStyles = (): React.CSSProperties => {
    const base: React.CSSProperties = {
      backgroundColor: colors.dark.surface,
      border: `1px solid ${error ? colors.danger.DEFAULT : colors.border.subtle}`,
    };

    switch (variant) {
      case 'filled':
        return {
          ...base,
          backgroundColor: colors.dark.elevated,
        };
      case 'glass':
        return {
          ...base,
          backgroundColor: 'rgba(255, 255, 255, 0.03)',
          backdropFilter: 'blur(12px)',
        };
      default:
        return base;
    }
  };

  // Display text
  const displayText = selectedOptions.length > 0
    ? multiple
      ? selectedOptions.map(o => o.label).join(', ')
      : selectedOptions[0].label
    : placeholder;

  const styles = {
    container: {
      position: 'relative' as const,
      width: fullWidth ? '100%' : 'auto',
      minWidth: '200px',
    },

    label: {
      display: 'block',
      fontFamily: fontFamily.sans,
      fontSize: fontSize.sm,
      fontWeight: fontWeight.medium,
      color: colors.text.secondary,
      marginBottom: spacing[2],
    },

    trigger: {
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      gap: spacing[2],
      width: '100%',
      height: config.height,
      padding: config.padding,
      fontFamily: fontFamily.sans,
      fontSize: config.fontSize,
      color: selectedOptions.length > 0 ? colors.text.primary : colors.text.tertiary,
      borderRadius: radius.md,
      cursor: disabled ? 'not-allowed' : 'pointer',
      opacity: disabled ? 0.5 : 1,
      transition: 'all 150ms ease-out',
      outline: 'none',
      ...getVariantStyles(),
    },

    triggerFocused: {
      borderColor: colors.primary.DEFAULT,
      boxShadow: `0 0 0 3px ${colors.primary.soft}`,
    },

    dropdown: {
      position: 'absolute' as const,
      top: '100%',
      left: 0,
      right: 0,
      marginTop: spacing[1],
      backgroundColor: colors.dark.elevated,
      border: `1px solid ${colors.border.subtle}`,
      borderRadius: radius.lg,
      boxShadow: shadows.lg,
      zIndex: zIndex.dropdown,
      overflow: 'hidden',
      maxHeight: '300px',
    },

    searchContainer: {
      padding: spacing[2],
      borderBottom: `1px solid ${colors.border.subtle}`,
    },

    searchInput: {
      width: '100%',
      padding: `${spacing[2]} ${spacing[3]}`,
      paddingLeft: spacing[9],
      fontFamily: fontFamily.sans,
      fontSize: fontSize.sm,
      color: colors.text.primary,
      backgroundColor: colors.dark.surface,
      border: `1px solid ${colors.border.subtle}`,
      borderRadius: radius.md,
      outline: 'none',
    },

    searchIcon: {
      position: 'absolute' as const,
      left: spacing[5],
      top: '50%',
      transform: 'translateY(-50%)',
      color: colors.text.tertiary,
    },

    optionsList: {
      overflowY: 'auto' as const,
      maxHeight: '250px',
      padding: spacing[1],
    },

    option: {
      display: 'flex',
      alignItems: 'center',
      gap: spacing[3],
      padding: `${spacing[3]} ${spacing[4]}`,
      fontFamily: fontFamily.sans,
      fontSize: config.fontSize,
      color: colors.text.primary,
      borderRadius: radius.md,
      cursor: 'pointer',
      transition: 'all 100ms ease-out',
    },

    optionSelected: {
      backgroundColor: colors.primary.soft,
    },

    optionHighlighted: {
      backgroundColor: colors.dark.subtle,
    },

    optionDisabled: {
      opacity: 0.5,
      cursor: 'not-allowed',
    },

    optionContent: {
      flex: 1,
      display: 'flex',
      flexDirection: 'column' as const,
      gap: '2px',
    },

    optionLabel: {
      fontWeight: fontWeight.medium,
    },

    optionDescription: {
      fontSize: fontSize.xs,
      color: colors.text.tertiary,
    },

    checkIcon: {
      color: colors.primary.DEFAULT,
      flexShrink: 0,
    },

    clearButton: {
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: spacing[1],
      color: colors.text.tertiary,
      borderRadius: radius.sm,
      cursor: 'pointer',
      transition: 'all 100ms ease-out',
    },

    helperText: {
      marginTop: spacing[1],
      fontFamily: fontFamily.sans,
      fontSize: fontSize.xs,
      color: error ? colors.danger.DEFAULT : colors.text.tertiary,
    },

    icons: {
      display: 'flex',
      alignItems: 'center',
      gap: spacing[1],
    },
  };

  return (
    <div ref={containerRef} style={styles.container} className={className}>
      {/* Label */}
      {label && <label style={styles.label}>{label}</label>}

      {/* Trigger Button */}
      <motion.div
        style={{
          ...styles.trigger,
          ...(isOpen ? styles.triggerFocused : {}),
        }}
        onClick={() => !disabled && setIsOpen(!isOpen)}
        onKeyDown={handleKeyDown}
        tabIndex={disabled ? -1 : 0}
        role="combobox"
        aria-expanded={isOpen}
        aria-haspopup="listbox"
        aria-disabled={disabled}
        whileHover={!disabled ? { borderColor: colors.border.default } : {}}
      >
        <span style={{ 
          overflow: 'hidden', 
          textOverflow: 'ellipsis', 
          whiteSpace: 'nowrap',
          flex: 1,
        }}>
          {displayText}
        </span>

        <div style={styles.icons}>
          {/* Clear button */}
          {clearable && selectedOptions.length > 0 && !disabled && (
            <motion.div
              style={styles.clearButton}
              onClick={handleClear}
              whileHover={{ color: colors.text.primary, backgroundColor: colors.dark.subtle }}
            >
              <X size={config.iconSize - 2} />
            </motion.div>
          )}

          {/* Chevron */}
          <motion.div
            animate={{ rotate: isOpen ? 180 : 0 }}
            transition={{ duration: 0.2 }}
            style={{ color: colors.text.tertiary }}
          >
            <ChevronDown size={config.iconSize} />
          </motion.div>
        </div>
      </motion.div>

      {/* Dropdown */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            style={styles.dropdown}
            variants={dropdownVariants}
            initial="hidden"
            animate="visible"
            exit="exit"
          >
            {/* Search Input */}
            {searchable && (
              <div style={{ ...styles.searchContainer, position: 'relative' }}>
                <Search size={16} style={styles.searchIcon} />
                <input
                  ref={searchInputRef}
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Buscar..."
                  style={styles.searchInput}
                />
              </div>
            )}

            {/* Options List */}
            <div style={styles.optionsList} role="listbox">
              {filteredOptions.length === 0 ? (
                <div style={{ 
                  padding: spacing[4], 
                  textAlign: 'center', 
                  color: colors.text.tertiary,
                  fontSize: fontSize.sm,
                }}>
                  Nenhuma opção encontrada
                </div>
              ) : (
                filteredOptions.map((option, index) => {
                  const isSelected = selectedValues.includes(option.value);
                  const isHighlighted = index === highlightedIndex;

                  return (
                    <motion.div
                      key={option.value}
                      style={{
                        ...styles.option,
                        ...(isSelected ? styles.optionSelected : {}),
                        ...(isHighlighted ? styles.optionHighlighted : {}),
                        ...(option.disabled ? styles.optionDisabled : {}),
                      }}
                      onClick={() => !option.disabled && handleSelect(option.value)}
                      onMouseEnter={() => setHighlightedIndex(index)}
                      variants={itemVariants}
                      whileHover={!option.disabled ? { 
                        backgroundColor: isSelected ? colors.primary.soft : colors.dark.subtle 
                      } : {}}
                      role="option"
                      aria-selected={isSelected}
                      aria-disabled={option.disabled}
                    >
                      {/* Icon */}
                      {option.icon && (
                        <span style={{ color: colors.text.tertiary, flexShrink: 0 }}>
                          {option.icon}
                        </span>
                      )}

                      {/* Content */}
                      <div style={styles.optionContent}>
                        <span style={styles.optionLabel}>{option.label}</span>
                        {option.description && (
                          <span style={styles.optionDescription}>{option.description}</span>
                        )}
                      </div>

                      {/* Check Icon */}
                      {isSelected && (
                        <Check size={config.iconSize} style={styles.checkIcon} />
                      )}
                    </motion.div>
                  );
                })
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Helper/Error Text */}
      {(helperText || error) && (
        <p style={styles.helperText}>{error || helperText}</p>
      )}
    </div>
  );
};

export default Select;
