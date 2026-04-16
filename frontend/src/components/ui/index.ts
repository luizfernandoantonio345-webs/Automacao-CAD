/**
 * UI Components — AutomAção CAD Enterprise v2.0
 * 
 * Centralized export for all UI components.
 * 
 * @usage import { Button, Card, Input } from '@/components/ui';
 */

// Core Components
export { Button, type ButtonProps, type ButtonVariant, type ButtonSize } from './Button';
export { default as Card, CardHeader, CardBody, CardFooter, type CardProps, type CardVariant, type CardSize } from './Card';
export { Input, type InputProps, type InputSize, type InputVariant } from './Input';
export { BottomTabBar, type BottomTabBarProps, type TabItem } from './BottomTabBar';
export { Badge, type BadgeProps, type BadgeVariant } from './Badge';

// Modal
export { Modal, ModalHeader, ModalBody, ModalFooter, type ModalProps } from './Modal';

// Select
export { Select, type SelectProps, type SelectOption } from './Select';

// Tabs
export { Tabs, TabsList, TabsTrigger, TabsContent, type TabsProps, type TabsTriggerProps } from './Tabs';

// Toast Notifications
export { ToastProvider, useToast, type ToastItem, type ToastType, type ToastPosition } from './Toast';

// Loading Skeletons
export { Skeleton, SkeletonCard, SkeletonList, SkeletonTable, SkeletonKPI, type SkeletonProps } from './Skeleton';

// Avatar
export { Avatar, AvatarGroup, AvatarWithInfo, type AvatarProps, type AvatarSize, type AvatarStatus } from './Avatar';
