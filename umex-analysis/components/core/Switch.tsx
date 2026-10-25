/**
 * UMEX Switch Component
 * Extracted from production: Switch-ByDNXrl6.js
 */

import React, { forwardRef, InputHTMLAttributes } from 'react';
import styles from './Switch.module.css';

export interface SwitchProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'type'> {
  label?: string;
  description?: string;
  size?: 'sm' | 'md' | 'lg';
  disabled?: boolean;
}

export const Switch = forwardRef<HTMLInputElement, SwitchProps>(
  ({ label, description, size = 'md', disabled = false, className = '', id, ...props }, ref) => {
    const switchId = id || `switch-${Math.random().toString(36).slice(2, 9)}`;

    return (
      <label className={`${styles.switch} ${styles[size]} ${disabled ? styles.disabled : ''} ${className}`}>
        <input
          ref={ref}
          type="checkbox"
          id={switchId}
          disabled={disabled}
          className={styles.input}
          {...props}
        />
        <span className={styles.slider} aria-hidden="true">
          <span className={styles.thumb} />
        </span>
        {(label || description) && (
          <div className={styles.labels}>
            {label && <span className={styles.label}>{label}</span>}
            {description && <span className={styles.description}>{description}</span>}
          </div>
        )}
      </label>
    );
  }
);

Switch.displayName = 'Switch';

/* CSS Module (Switch.module.css)
.switch {
  display: inline-flex;
  align-items: center;
  gap: var(--space-3);
  cursor: pointer;
  user-select: none;
}

.switch.disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.input {
  position: absolute;
  opacity: 0;
  width: 0;
  height: 0;
}

.slider {
  position: relative;
  display: flex;
  align-items: center;
  background: var(--color-surface-l2);
  border: 1px solid var(--color-app-border-secondary);
  border-radius: var(--radius-full);
  transition: all var(--transition-normal);
}

.sm .slider {
  width: 36px;
  height: 20px;
}

.md .slider {
  width: 44px;
  height: 24px;
}

.lg .slider {
  width: 52px;
  height: 28px;
}

.input:checked + .slider {
  background: var(--color-brand-primary);
  border-color: var(--color-brand-primary);
}

.input:focus-visible + .slider {
  outline: 2px solid var(--color-brand-primary);
  outline-offset: 2px;
}

.thumb {
  position: absolute;
  top: 2px;
  left: 2px;
  background: var(--color-text-white);
  border-radius: var(--radius-full);
  box-shadow: var(--shadow-sm);
  transition: transform var(--transition-normal);
}

.sm .thumb {
  width: 14px;
  height: 14px;
}

.md .thumb {
  width: 18px;
  height: 18px;
}

.lg .thumb {
  width: 22px;
  height: 22px;
}

.input:checked + .slider .thumb {
  transform: translateX(calc(100% + 2px));
}

.labels {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  min-width: 0;
}

.label {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  color: var(--color-text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.description {
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary-l2);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
*/