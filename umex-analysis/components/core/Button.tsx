/**
 * UMEX Button Component
 * Extracted from production analysis
 */

import React, { forwardRef, ButtonHTMLAttributes } from 'react';
import styles from './Button.module.css';

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger' | 'outline';
  size?: 'sm' | 'md' | 'lg' | 'icon';
  loading?: boolean;
  icon?: React.ReactNode;
  iconPosition?: 'left' | 'right';
  fullWidth?: boolean;
  count?: number;
  countTone?: 'neutral' | 'new' | 'bonus';
  locked?: boolean;
  minWidth?: number;
  tag?: string;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      children,
      variant = 'primary',
      size = 'md',
      loading = false,
      icon,
      iconPosition = 'left',
      fullWidth = false,
      count,
      countTone = 'neutral',
      locked = false,
      minWidth,
      tag,
      className = '',
      disabled,
      ...props
    },
    ref
  ) => {
    const isDisabled = disabled || loading || locked;

    const countToneClass = countTone !== 'neutral' ? styles[`count-${countTone}`] : '';
    const countClass = count !== undefined && count > 0 ? styles.count : '';

    return (
      <button
        ref={ref}
        type="button"
        className={`${styles.button} ${styles[variant]} ${styles[size]} ${
          fullWidth ? styles.fullWidth : ''
        } ${countClass} ${countToneClass} ${className}`}
        disabled={isDisabled}
        style={{ '--launcher-min-width': minWidth ? `${minWidth}px` : undefined } as React.CSSProperties}
        aria-label={locked ? `${tag} (locked)` : tag}
        aria-disabled={isDisabled}
        {...props}
      >
        <span className={styles.iconWrapper}>
          {icon && iconPosition === 'left' && <span className={styles.icon}>{icon}</span>}
          {loading ? (
            <span className={styles.spinner} aria-hidden="true" />
          ) : (
            <>
              {icon && iconPosition === 'left' && <span className={styles.icon}>{icon}</span>}
              <span className={styles.content}>
                {tag && <small className={styles.tag}>{tag}</small>}
                <strong className={styles.label}>{children}</strong>
              </span>
              {icon && iconPosition === 'right' && <span className={styles.icon}>{icon}</span>}
            </>
          )}
          {count !== undefined && count > 0 && (
            <span className={`${styles.countBadge} ${countToneClass}`}>{count}</span>
          )}
          {locked && <span className={styles.lock} aria-hidden="true">🔒</span>}
        </span>
      </button>
    );
  }
);

Button.displayName = 'Button';

/* CSS Module (Button.module.css)
.button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  border: none;
  border-radius: var(--radius-md);
  font-family: var(--font-family-sans);
  font-weight: var(--font-weight-semibold);
  cursor: pointer;
  transition: all var(--transition-normal);
  position: relative;
  overflow: hidden;
}

.button:disabled,
.button[aria-disabled="true"] {
  opacity: 0.5;
  cursor: not-allowed;
}

.primary {
  background: var(--color-brand-primary);
  color: var(--color-brand-primary-on);
}

.primary:hover:not(:disabled) {
  background: var(--color-brand-primary-hover);
}

.primary:active:not(:disabled) {
  background: var(--color-brand-primary-press);
}

.secondary {
  background: var(--color-surface-l2);
  color: var(--color-surface-l2-on);
  border: 1px solid var(--color-app-border-secondary);
}

.secondary:hover:not(:disabled) {
  background: var(--color-surface-l2-hover);
  border-color: var(--color-app-border-secondary-hover);
}

.ghost {
  background: transparent;
  color: var(--color-text-primary);
}

.ghost:hover:not(:disabled) {
  background: var(--color-surface-l1);
}

.danger {
  background: var(--color-error);
  color: var(--color-error-on);
}

.danger:hover:not(:disabled) {
  background: var(--color-error-surface);
}

.outline {
  background: transparent;
  color: var(--color-brand-primary);
  border: 1px solid var(--color-brand-primary);
}

.outline:hover:not(:disabled) {
  background: var(--color-brand-primary-bg);
}

.sm {
  padding: var(--space-1) var(--space-3);
  font-size: var(--font-size-sm);
  min-height: 32px;
}

.md {
  padding: var(--space-2) var(--space-4);
  font-size: var(--font-size-sm);
  min-height: 40px;
}

.lg {
  padding: var(--space-3) var(--space-6);
  font-size: var(--font-size-md);
  min-height: 48px;
}

.icon {
  padding: var(--space-2);
  min-width: 40px;
  min-height: 40px;
}

.fullWidth {
  width: 100%;
}

.iconWrapper {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  position: relative;
}

.content {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.tag {
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-normal);
  opacity: 0.8;
}

.label {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.countBadge {
  position: absolute;
  top: -4px;
  right: -4px;
  min-width: 18px;
  height: 18px;
  padding: 0 5px;
  border-radius: var(--radius-full);
  background: var(--color-brand-primary);
  color: var(--color-brand-primary-on);
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-bold);
  display: flex;
  align-items: center;
  justify-content: center;
}

.count-new {
  background: var(--color-warning);
  animation: pulse 2s infinite;
}

.count-bonus {
  background: var(--color-success);
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.6; }
}

.lock {
  font-size: 14px;
}

.spinner {
  width: 16px;
  height: 16px;
  border: 2px solid currentColor;
  border-right-color: transparent;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
*/