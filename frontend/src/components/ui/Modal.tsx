/**
 * Modal Component — AutomAção CAD Enterprise v2.0
 * 
 * Luxurious modal with glass effect, backdrop blur, and smooth animations.
 * Supports center + slide-over variants.
 * 
 * @usage
 * <Modal isOpen={open} onClose={close} title="Settings">
 *   <ModalBody>Content here</ModalBody>
 *   <ModalFooter>
 *     <Button onClick={close}>Cancel</Button>
 *     <Button variant="primary">Save</Button>
 *   </ModalFooter>
 * </Modal>
 */

import React, { useEffect, useCallback, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X } from 'lucide-react';
import { colors, radius, shadows, spacing, blur, zIndex } from '../../design/tokens';
import { fontFamily, fontSize, fontWeight } from '../../design/typography';

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// TYPES
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

export interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  description?: string;
  variant?: 'center' | 'slideOver' | 'fullscreen';
  size?: 'sm' | 'md' | 'lg' | 'xl' | 'full';
  showCloseButton?: boolean;
  closeOnOverlayClick?: boolean;
  closeOnEscape?: boolean;
  children: React.ReactNode;
  className?: string;
}

export interface ModalHeaderProps {
  children?: React.ReactNode;
  className?: string;
}

export interface ModalBodyProps {
  children: React.ReactNode;
  className?: string;
}

export interface ModalFooterProps {
  children: React.ReactNode;
  align?: 'left' | 'center' | 'right' | 'between';
  className?: string;
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// SIZE CONFIG
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

const sizeStyles: Record<string, React.CSSProperties> = {
  sm: { maxWidth: '400px', width: '90%' },
  md: { maxWidth: '500px', width: '90%' },
  lg: { maxWidth: '640px', width: '90%' },
  xl: { maxWidth: '800px', width: '90%' },
  full: { maxWidth: '95%', width: '95%', maxHeight: '95vh' },
};

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// ANIMATION VARIANTS
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

const backdropVariants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1 },
  exit: { opacity: 0 },
};

const centerVariants = {
  hidden: { 
    opacity: 0, 
    scale: 0.95,
    y: 10,
  },
  visible: { 
    opacity: 1, 
    scale: 1,
    y: 0,
    transition: {
      type: 'spring',
      stiffness: 400,
      damping: 30,
    },
  },
  exit: { 
    opacity: 0, 
    scale: 0.95,
    y: 10,
    transition: { duration: 0.15 },
  },
};

const slideOverVariants = {
  hidden: { x: '100%', opacity: 0 },
  visible: { 
    x: 0, 
    opacity: 1,
    transition: {
      type: 'spring',
      stiffness: 300,
      damping: 30,
    },
  },
  exit: { 
    x: '100%', 
    opacity: 0,
    transition: { duration: 0.2 },
  },
};

const fullscreenVariants = {
  hidden: { opacity: 0, scale: 0.98 },
  visible: { 
    opacity: 1, 
    scale: 1,
    transition: { duration: 0.2 },
  },
  exit: { 
    opacity: 0, 
    scale: 0.98,
    transition: { duration: 0.15 },
  },
};

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// STYLES
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

const styles = {
  backdrop: {
    position: 'fixed' as const,
    inset: 0,
    backgroundColor: 'rgba(0, 0, 0, 0.7)',
    backdropFilter: `blur(${blur.sm})`,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: zIndex.modal,
    padding: spacing[4],
  },

  slideOverBackdrop: {
    position: 'fixed' as const,
    inset: 0,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    backdropFilter: `blur(${blur.sm})`,
    display: 'flex',
    justifyContent: 'flex-end',
    zIndex: zIndex.modal,
  },

  modalCenter: {
    backgroundColor: colors.dark.elevated,
    borderRadius: radius.xl,
    border: `1px solid ${colors.border.subtle}`,
    boxShadow: shadows['2xl'],
    display: 'flex',
    flexDirection: 'column' as const,
    maxHeight: '85vh',
    overflow: 'hidden',
  },

  modalSlideOver: {
    backgroundColor: colors.dark.elevated,
    borderLeft: `1px solid ${colors.border.subtle}`,
    boxShadow: shadows['2xl'],
    display: 'flex',
    flexDirection: 'column' as const,
    height: '100vh',
    width: '100%',
    maxWidth: '480px',
  },

  modalFullscreen: {
    backgroundColor: colors.dark.base,
    display: 'flex',
    flexDirection: 'column' as const,
    width: '100vw',
    height: '100vh',
  },

  header: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: `${spacing[5]} ${spacing[6]}`,
    borderBottom: `1px solid ${colors.border.subtle}`,
    flexShrink: 0,
  },

  headerContent: {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: spacing[1],
  },

  title: {
    fontFamily: fontFamily.display,
    fontSize: fontSize.lg,
    fontWeight: fontWeight.semibold,
    color: colors.text.primary,
    margin: 0,
    lineHeight: 1.3,
  },

  description: {
    fontFamily: fontFamily.sans,
    fontSize: fontSize.sm,
    color: colors.text.secondary,
    margin: 0,
  },

  closeButton: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    width: '36px',
    height: '36px',
    borderRadius: radius.md,
    border: 'none',
    backgroundColor: 'transparent',
    color: colors.text.tertiary,
    cursor: 'pointer',
    transition: 'all 150ms ease-out',
    flexShrink: 0,
  },

  body: {
    flex: 1,
    overflowY: 'auto' as const,
    padding: spacing[6],
  },

  footer: {
    display: 'flex',
    gap: spacing[3],
    padding: `${spacing[4]} ${spacing[6]}`,
    borderTop: `1px solid ${colors.border.subtle}`,
    flexShrink: 0,
  },
};

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// MODAL HEADER COMPONENT
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

export const ModalHeader: React.FC<ModalHeaderProps> = ({ 
  children, 
  className = '' 
}) => {
  return (
    <div style={styles.header} className={className}>
      {children}
    </div>
  );
};

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// MODAL BODY COMPONENT
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

export const ModalBody: React.FC<ModalBodyProps> = ({ 
  children, 
  className = '' 
}) => {
  return (
    <div style={styles.body} className={className}>
      {children}
    </div>
  );
};

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// MODAL FOOTER COMPONENT
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

export const ModalFooter: React.FC<ModalFooterProps> = ({ 
  children, 
  align = 'right',
  className = '' 
}) => {
  const alignStyles: Record<string, React.CSSProperties> = {
    left: { justifyContent: 'flex-start' },
    center: { justifyContent: 'center' },
    right: { justifyContent: 'flex-end' },
    between: { justifyContent: 'space-between' },
  };

  return (
    <div 
      style={{ ...styles.footer, ...alignStyles[align] }} 
      className={className}
    >
      {children}
    </div>
  );
};

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// MAIN MODAL COMPONENT
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

export const Modal: React.FC<ModalProps> = ({
  isOpen,
  onClose,
  title,
  description,
  variant = 'center',
  size = 'md',
  showCloseButton = true,
  closeOnOverlayClick = true,
  closeOnEscape = true,
  children,
  className = '',
}) => {
  const modalRef = useRef<HTMLDivElement>(null);

  // Handle escape key
  const handleEscape = useCallback((e: KeyboardEvent) => {
    if (e.key === 'Escape' && closeOnEscape) {
      onClose();
    }
  }, [closeOnEscape, onClose]);

  // Handle overlay click
  const handleOverlayClick = useCallback((e: React.MouseEvent) => {
    if (closeOnOverlayClick && e.target === e.currentTarget) {
      onClose();
    }
  }, [closeOnOverlayClick, onClose]);

  // Lock body scroll when open
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
      document.addEventListener('keydown', handleEscape);
    }
    return () => {
      document.body.style.overflow = '';
      document.removeEventListener('keydown', handleEscape);
    };
  }, [isOpen, handleEscape]);

  // Focus trap
  useEffect(() => {
    if (isOpen && modalRef.current) {
      modalRef.current.focus();
    }
  }, [isOpen]);

  // Get variant-specific styles and animations
  const getModalConfig = () => {
    switch (variant) {
      case 'slideOver':
        return {
          backdrop: styles.slideOverBackdrop,
          modal: styles.modalSlideOver,
          variants: slideOverVariants,
        };
      case 'fullscreen':
        return {
          backdrop: { ...styles.backdrop, padding: 0 },
          modal: styles.modalFullscreen,
          variants: fullscreenVariants,
        };
      default:
        return {
          backdrop: styles.backdrop,
          modal: { ...styles.modalCenter, ...sizeStyles[size] },
          variants: centerVariants,
        };
    }
  };

  const config = getModalConfig();

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          style={config.backdrop}
          variants={backdropVariants}
          initial="hidden"
          animate="visible"
          exit="exit"
          onClick={handleOverlayClick}
        >
          <motion.div
            ref={modalRef}
            style={config.modal}
            variants={config.variants}
            initial="hidden"
            animate="visible"
            exit="exit"
            role="dialog"
            aria-modal="true"
            aria-labelledby={title ? 'modal-title' : undefined}
            aria-describedby={description ? 'modal-description' : undefined}
            tabIndex={-1}
            className={className}
          >
            {/* Header with title */}
            {(title || showCloseButton) && (
              <div style={styles.header}>
                <div style={styles.headerContent}>
                  {title && (
                    <h2 id="modal-title" style={styles.title}>
                      {title}
                    </h2>
                  )}
                  {description && (
                    <p id="modal-description" style={styles.description}>
                      {description}
                    </p>
                  )}
                </div>
                {showCloseButton && (
                  <motion.button
                    style={styles.closeButton}
                    onClick={onClose}
                    whileHover={{ 
                      backgroundColor: colors.dark.subtle,
                      color: colors.text.primary,
                    }}
                    whileTap={{ scale: 0.95 }}
                    aria-label="Fechar modal"
                  >
                    <X size={20} />
                  </motion.button>
                )}
              </div>
            )}

            {/* Content */}
            {children}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};

export default Modal;
