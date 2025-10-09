'use client';

import { ReactNode } from 'react';

interface FormFieldProps {
  label: string;
  htmlFor: string;
  error?: string;
  required?: boolean;
  helpText?: string;
  children: ReactNode;
}

/**
 * Reusable form field wrapper with label, error display, and accessibility
 *
 * Features:
 * - Accessible label association
 * - Error message with aria-describedby
 * - Required field indicator
 * - Help text support
 * - Consistent styling
 */
export default function FormField({
  label,
  htmlFor,
  error,
  required = false,
  helpText,
  children,
}: FormFieldProps) {
  const errorId = `${htmlFor}-error`;
  const helpId = `${htmlFor}-help`;

  return (
    <div className="space-y-1">
      <label
        htmlFor={htmlFor}
        className="block text-sm font-medium text-gray-700"
      >
        {label}
        {required && <span className="text-red-500 ml-1">*</span>}
      </label>

      <div className="relative">
        {children}
      </div>

      {error && (
        <p
          id={errorId}
          className="text-sm text-red-600 flex items-center gap-1"
          role="alert"
        >
          <span className="text-red-500">⚠</span>
          {error}
        </p>
      )}

      {helpText && !error && (
        <p id={helpId} className="text-xs text-gray-500">
          {helpText}
        </p>
      )}
    </div>
  );
}
