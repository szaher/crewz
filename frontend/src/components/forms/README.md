# Form Error Handling Components

Comprehensive form error handling utilities with accessibility, validation, and retry logic.

## Components

### FormField
Reusable form field wrapper with label, error display, and accessibility.

```tsx
import FormField from '@/components/forms/FormField';

<FormField
  label="Email"
  htmlFor="email"
  error={errors.email}
  required
  helpText="We'll never share your email"
>
  <input
    id="email"
    type="email"
    value={formData.email}
    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
    aria-invalid={!!errors.email}
    aria-describedby={errors.email ? 'email-error' : undefined}
    className="w-full px-3 py-2 border rounded-md"
  />
</FormField>
```

### FormErrorSummary
Form-level error summary with accessibility.

```tsx
import FormErrorSummary from '@/components/forms/FormErrorSummary';

<FormErrorSummary
  errors={errors}
  title="Please fix the following errors:"
/>
```

## Hooks

### useFormSubmit
Comprehensive form submission handler with validation, retry, and toast notifications.

```tsx
import { useFormSubmit } from '@/lib/hooks/useFormSubmit';

function MyForm() {
  const { handleSubmit, loading, errors, formError } = useFormSubmit({
    onSuccess: (data) => {
      router.push(`/items/${data.id}`);
    },
    successMessage: 'Item created successfully!',
    enableRetry: true,
  });

  const onSubmit = handleSubmit(async (formData) => {
    return await apiClient.post('/api/items', formData);
  });

  return (
    <form onSubmit={(e) => { e.preventDefault(); onSubmit(formData); }}>
      <FormErrorSummary errors={errors} />

      {formError && (
        <div className="bg-red-50 border border-red-200 rounded p-4 mb-4">
          <p className="text-sm text-red-800">{formError}</p>
        </div>
      )}

      <FormField label="Name" htmlFor="name" error={errors.name} required>
        <input
          id="name"
          value={formData.name}
          onChange={(e) => setFormData({ ...formData, name: e.target.value })}
          className="w-full px-3 py-2 border rounded-md"
        />
      </FormField>

      <button
        type="submit"
        disabled={loading}
        className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
      >
        {loading ? 'Saving...' : 'Save'}
      </button>
    </form>
  );
}
```

### useApiOperation
Simpler hook for non-form API operations.

```tsx
import { useApiOperation } from '@/lib/hooks/useFormSubmit';

function DeleteButton({ itemId }: { itemId: number }) {
  const { execute, loading } = useApiOperation({
    successMessage: 'Item deleted successfully!',
    enableRetry: false,
  });

  const handleDelete = async () => {
    if (!confirm('Are you sure?')) return;

    try {
      await execute(() => apiClient.delete(`/api/items/${itemId}`));
      // Item deleted, refresh list
      refetch();
    } catch (error) {
      // Error already handled (toast shown)
    }
  };

  return (
    <button
      onClick={handleDelete}
      disabled={loading}
      className="px-3 py-1 bg-red-600 text-white rounded"
    >
      {loading ? 'Deleting...' : 'Delete'}
    </button>
  );
}
```

## Utilities

### Error Handler
Comprehensive error parsing and retry logic.

```tsx
import {
  parseErrorResponse,
  parseValidationErrors,
  retryWithBackoff,
  getErrorMessage,
  isNetworkError,
  isRetryableError,
} from '@/lib/error-handler';

// Parse error details
const errorDetail = parseErrorResponse(error);
console.log(errorDetail.message); // User-friendly message
console.log(errorDetail.type); // 'validation' | 'network' | 'server' | 'client'
console.log(errorDetail.retryable); // boolean

// Parse validation errors for form fields
const fieldErrors = parseValidationErrors(error);
// { email: 'Invalid email format', name: 'Name is required' }

// Retry with exponential backoff
const data = await retryWithBackoff(
  () => apiClient.get('/api/data'),
  {
    maxRetries: 3,
    initialDelay: 1000,
    maxDelay: 10000,
  }
);

// Check error type
if (isNetworkError(error)) {
  // Show "Check your connection" message
}

if (isRetryableError(error)) {
  // Offer retry button
}

// Get user-friendly message
const message = getErrorMessage(error);
```

## Features

✅ **Backend Validation**: Parses Pydantic and FastAPI validation errors
✅ **Inline Field Errors**: Shows errors next to each field with proper ARIA
✅ **Error Summary**: Lists all errors at top of form with anchor links
✅ **Retry Logic**: Automatic retry for network errors with exponential backoff
✅ **Toast Notifications**: Success/error toasts for all operations
✅ **Accessibility**: ARIA labels, live regions, keyboard navigation
✅ **Loading States**: Automatic loading state management
✅ **Type Safety**: Full TypeScript support

## Error Types Handled

- **Validation (400, 422)**: Field-level validation errors from backend
- **Authentication (401)**: Session expired, redirect to login
- **Authorization (403)**: Permission denied
- **Not Found (404)**: Resource doesn't exist
- **Server Error (500+)**: Backend error, show retry
- **Network Error**: Connection issues, auto-retry
- **Timeout**: Request timeout, offer retry

## Backend Error Formats Supported

### Pydantic Validation (FastAPI)
```json
{
  "detail": [
    {
      "loc": ["body", "email"],
      "msg": "value is not a valid email address",
      "type": "value_error.email"
    }
  ]
}
```

### Simple Error
```json
{
  "detail": "Resource not found"
}
```

### Custom Error Object
```json
{
  "message": "Operation failed",
  "code": "CUSTOM_ERROR"
}
```

## Best Practices

1. **Always use FormField** for consistent styling and accessibility
2. **Show FormErrorSummary** at top of forms for overview
3. **Enable retry** for data fetching, disable for mutations
4. **Provide successMessage** for positive feedback
5. **Handle onSuccess** for navigation after form submission
6. **Log errors** to console for debugging (done automatically)
7. **Test with screen readers** to ensure accessibility

## Migration Guide

### Old Pattern
```tsx
const [loading, setLoading] = useState(false);
const [error, setError] = useState('');

const handleSubmit = async (e) => {
  e.preventDefault();
  setLoading(true);
  try {
    const response = await apiClient.post('/api/items', formData);
    if (response.error) throw response.error;
    alert('Success!');
    router.push('/success');
  } catch (err) {
    setError(err.message);
  } finally {
    setLoading(false);
  }
};
```

### New Pattern
```tsx
const { handleSubmit, loading, errors, formError } = useFormSubmit({
  onSuccess: (data) => router.push('/success'),
  successMessage: 'Item created successfully!',
  enableRetry: true,
});

const onSubmit = handleSubmit(async (formData) => {
  return await apiClient.post('/api/items', formData);
});
```

**Benefits**: Automatic error parsing, field validation, toast notifications, retry logic, loading state, accessibility.
