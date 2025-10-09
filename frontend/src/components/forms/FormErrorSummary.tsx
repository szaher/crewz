'use client';

interface FormErrorSummaryProps {
  errors: Record<string, string | string[]>;
  title?: string;
}

/**
 * Form-level error summary component
 *
 * Displays all form errors in a summary box at the top of the form.
 * Useful for accessibility and providing overview of validation issues.
 *
 * Features:
 * - Lists all field errors
 * - Links to fields with errors (anchor navigation)
 * - ARIA live region for screen readers
 * - Dismissible
 */
export default function FormErrorSummary({
  errors,
  title = 'Please fix the following errors:',
}: FormErrorSummaryProps) {
  const errorEntries = Object.entries(errors).filter(([_, value]) => {
    if (Array.isArray(value)) return value.length > 0;
    return value && value.trim() !== '';
  });

  if (errorEntries.length === 0) return null;

  const formatFieldName = (fieldName: string) => {
    return fieldName
      .replace(/_/g, ' ')
      .replace(/([A-Z])/g, ' $1')
      .replace(/^./, (str) => str.toUpperCase())
      .trim();
  };

  return (
    <div
      className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6"
      role="alert"
      aria-live="polite"
      aria-atomic="true"
    >
      <div className="flex items-start gap-3">
        <span className="text-red-500 text-xl flex-shrink-0">❌</span>
        <div className="flex-1">
          <h3 className="text-sm font-semibold text-red-900 mb-2">{title}</h3>
          <ul className="space-y-1">
            {errorEntries.map(([field, error]) => {
              const errorMessages = Array.isArray(error) ? error : [error];
              return errorMessages.map((msg, index) => (
                <li key={`${field}-${index}`} className="text-sm text-red-800">
                  <a
                    href={`#${field}`}
                    className="hover:underline font-medium"
                    onClick={(e) => {
                      e.preventDefault();
                      const element = document.getElementById(field);
                      element?.focus();
                      element?.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    }}
                  >
                    {formatFieldName(field)}
                  </a>
                  : {msg}
                </li>
              ));
            })}
          </ul>
        </div>
      </div>
    </div>
  );
}
