/**
 * Animation System — AutomAção CAD Enterprise v2.0
 * 
 * Framer Motion variants for consistent, performant animations.
 * Standardized durations and easing for enterprise feel.
 * 
 * @usage import { fadeIn, slideUp, staggerContainer } from '@/design/animations';
 */

import type { Variants, Transition, TargetAndTransition } from 'framer-motion';

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// DURATION CONSTANTS
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

export const duration = {
  instant: 0,
  fast: 0.1,
  normal: 0.2,
  slow: 0.3,
  slower: 0.5,
  slowest: 0.8,
} as const;


// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// EASING CURVES
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

export const easing = {
  // Standard curves
  linear: [0, 0, 1, 1] as const,
  easeIn: [0.4, 0, 1, 1] as const,
  easeOut: [0, 0, 0.2, 1] as const,
  easeInOut: [0.4, 0, 0.2, 1] as const,
  
  // Premium curves
  spring: [0.34, 1.56, 0.64, 1] as const,  // Bouncy feel
  smooth: [0.25, 0.1, 0.25, 1] as const,   // Apple-style
  bounce: [0.68, -0.55, 0.265, 1.55] as const,
  
  // Framer Motion spring configs
  springConfig: {
    type: 'spring' as const,
    stiffness: 400,
    damping: 30,
  },
  
  gentleSpring: {
    type: 'spring' as const,
    stiffness: 200,
    damping: 20,
  },
  
  bouncySpring: {
    type: 'spring' as const,
    stiffness: 500,
    damping: 25,
    mass: 0.8,
  },
} as const;


// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// STANDARD TRANSITIONS
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

export const transition = {
  fast: {
    duration: duration.fast,
    ease: easing.easeOut,
  } as Transition,
  
  normal: {
    duration: duration.normal,
    ease: easing.easeOut,
  } as Transition,
  
  slow: {
    duration: duration.slow,
    ease: easing.easeInOut,
  } as Transition,
  
  spring: easing.springConfig,
  gentleSpring: easing.gentleSpring,
  bouncySpring: easing.bouncySpring,
} as const;


// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// FADE VARIANTS
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

export const fadeIn: Variants = {
  hidden: { 
    opacity: 0 
  },
  visible: { 
    opacity: 1,
    transition: transition.normal,
  },
  exit: { 
    opacity: 0,
    transition: transition.fast,
  },
};

export const fadeInScale: Variants = {
  hidden: { 
    opacity: 0, 
    scale: 0.95 
  },
  visible: { 
    opacity: 1, 
    scale: 1,
    transition: transition.spring,
  },
  exit: { 
    opacity: 0, 
    scale: 0.95,
    transition: transition.fast,
  },
};


// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// SLIDE VARIANTS
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

export const slideUp: Variants = {
  hidden: { 
    opacity: 0, 
    y: 20 
  },
  visible: { 
    opacity: 1, 
    y: 0,
    transition: transition.spring,
  },
  exit: { 
    opacity: 0, 
    y: 10,
    transition: transition.fast,
  },
};

export const slideDown: Variants = {
  hidden: { 
    opacity: 0, 
    y: -20 
  },
  visible: { 
    opacity: 1, 
    y: 0,
    transition: transition.spring,
  },
  exit: { 
    opacity: 0, 
    y: -10,
    transition: transition.fast,
  },
};

export const slideLeft: Variants = {
  hidden: { 
    opacity: 0, 
    x: 20 
  },
  visible: { 
    opacity: 1, 
    x: 0,
    transition: transition.spring,
  },
  exit: { 
    opacity: 0, 
    x: 10,
    transition: transition.fast,
  },
};

export const slideRight: Variants = {
  hidden: { 
    opacity: 0, 
    x: -20 
  },
  visible: { 
    opacity: 1, 
    x: 0,
    transition: transition.spring,
  },
  exit: { 
    opacity: 0, 
    x: -10,
    transition: transition.fast,
  },
};


// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// STAGGER VARIANTS — For lists
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

export const staggerContainer: Variants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.05,
      delayChildren: 0.1,
    },
  },
  exit: {
    opacity: 0,
    transition: {
      staggerChildren: 0.03,
      staggerDirection: -1,
    },
  },
};

export const staggerItem: Variants = {
  hidden: { 
    opacity: 0, 
    y: 16 
  },
  visible: { 
    opacity: 1, 
    y: 0,
    transition: transition.spring,
  },
  exit: { 
    opacity: 0, 
    y: 8,
    transition: transition.fast,
  },
};

// Slower stagger for cards/larger items
export const staggerContainerSlow: Variants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1,
      delayChildren: 0.15,
    },
  },
};


// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// SCALE VARIANTS
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

export const scaleIn: Variants = {
  hidden: { 
    opacity: 0, 
    scale: 0.8 
  },
  visible: { 
    opacity: 1, 
    scale: 1,
    transition: transition.bouncySpring,
  },
  exit: { 
    opacity: 0, 
    scale: 0.9,
    transition: transition.fast,
  },
};

export const popIn: Variants = {
  hidden: { 
    opacity: 0, 
    scale: 0.5 
  },
  visible: { 
    opacity: 1, 
    scale: 1,
    transition: easing.bouncySpring,
  },
  exit: { 
    opacity: 0, 
    scale: 0.8,
    transition: transition.fast,
  },
};


// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// HOVER/TAP STATES
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

export const hoverLift: TargetAndTransition = {
  y: -4,
  transition: transition.spring,
};

export const hoverScale: TargetAndTransition = {
  scale: 1.02,
  transition: transition.spring,
};

export const hoverGlow = (color: string = 'rgba(0, 161, 255, 0.3)'): TargetAndTransition => ({
  boxShadow: `0 0 20px ${color}, 0 4px 16px rgba(0, 0, 0, 0.3)`,
  transition: transition.normal,
});

export const tapScale: TargetAndTransition = {
  scale: 0.98,
  transition: transition.fast,
};

export const tapPush: TargetAndTransition = {
  scale: 0.95,
  transition: transition.fast,
};


// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// SPECIAL EFFECTS
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

// Modal/Dialog animation
export const modal: Variants = {
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
      stiffness: 300,
      damping: 25,
    },
  },
  exit: { 
    opacity: 0, 
    scale: 0.98,
    y: 5,
    transition: {
      duration: 0.15,
      ease: easing.easeIn,
    },
  },
};

// Backdrop/Overlay animation
export const backdrop: Variants = {
  hidden: { 
    opacity: 0 
  },
  visible: { 
    opacity: 1,
    transition: { duration: 0.2 },
  },
  exit: { 
    opacity: 0,
    transition: { duration: 0.15 },
  },
};

// Sidebar/Drawer animation
export const drawer: Variants = {
  hidden: { 
    x: '-100%',
    opacity: 0.5,
  },
  visible: { 
    x: 0,
    opacity: 1,
    transition: transition.spring,
  },
  exit: { 
    x: '-100%',
    opacity: 0.5,
    transition: transition.normal,
  },
};

// Toast notification
export const toast: Variants = {
  hidden: { 
    opacity: 0, 
    y: 50,
    scale: 0.9,
  },
  visible: { 
    opacity: 1, 
    y: 0,
    scale: 1,
    transition: transition.spring,
  },
  exit: { 
    opacity: 0, 
    scale: 0.9,
    transition: transition.fast,
  },
};

// Shimmer effect (for loading states)
export const shimmer = {
  animate: {
    backgroundPosition: ['200% 0', '-200% 0'],
    transition: {
      duration: 1.5,
      repeat: Infinity,
      ease: 'linear',
    },
  },
};


// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// PAGE TRANSITIONS
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

export const pageTransition: Variants = {
  hidden: { 
    opacity: 0,
  },
  visible: { 
    opacity: 1,
    transition: {
      duration: 0.3,
      when: 'beforeChildren',
      staggerChildren: 0.1,
    },
  },
  exit: { 
    opacity: 0,
    transition: {
      duration: 0.2,
    },
  },
};


// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// UTILITY FUNCTIONS
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

/**
 * Creates a custom stagger container with specified delay
 */
export function createStagger(staggerDelay: number = 0.05): Variants {
  return {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: staggerDelay,
        delayChildren: 0.1,
      },
    },
  };
}

/**
 * Creates a slide variant with custom distance
 */
export function createSlide(
  direction: 'up' | 'down' | 'left' | 'right', 
  distance: number = 20
): Variants {
  const isVertical = direction === 'up' || direction === 'down';
  const sign = direction === 'down' || direction === 'right' ? -1 : 1;
  
  if (isVertical) {
    return {
      hidden: { 
        opacity: 0, 
        y: distance * sign,
      },
      visible: { 
        opacity: 1, 
        y: 0,
        transition: transition.spring,
      },
      exit: { 
        opacity: 0, 
        y: (distance / 2) * sign,
        transition: transition.fast,
      },
    };
  } else {
    return {
      hidden: { 
        opacity: 0, 
        x: distance * sign,
      },
      visible: { 
        opacity: 1, 
        x: 0,
        transition: transition.spring,
      },
      exit: { 
        opacity: 0, 
        x: (distance / 2) * sign,
        transition: transition.fast,
      },
    };
  }
}


// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// EXPORTS
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

export const animations = {
  duration,
  easing,
  transition,
  // Variants
  fadeIn,
  fadeInScale,
  slideUp,
  slideDown,
  slideLeft,
  slideRight,
  scaleIn,
  popIn,
  staggerContainer,
  staggerItem,
  staggerContainerSlow,
  // States
  hoverLift,
  hoverScale,
  hoverGlow,
  tapScale,
  tapPush,
  // Special
  modal,
  backdrop,
  drawer,
  toast,
  shimmer,
  pageTransition,
  // Utilities
  createStagger,
  createSlide,
} as const;

export default animations;
