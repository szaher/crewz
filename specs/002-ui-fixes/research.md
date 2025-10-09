# Technical Research: UI Fixes and Enhancements

**Feature**: 002-ui-fixes
**Date**: 2025-10-06
**Status**: Complete

---

## Research Questions & Decisions

### 1. Flow Creation UX Pattern

**Question**: Should flow creation use a modal dialog or dedicated page?

**Options Evaluated**:
1. Modal dialog with basic fields
2. Dedicated creation page with wizard
3. Inline creation (add directly to list)

**Decision**: **Modal dialog for quick creation**

**Rationale**:
- Faster workflow (no page navigation)
- Matches common SaaS patterns (Notion, Airtable, Linear)
- Can always add "Advanced" button to go to dedicated page later
- Keeps user in context of dashboard

**Implementation Notes**:
- Modal should be 500-600px wide
- Fields: Name (required), Description (optional), Initial variables (optional, collapsible)
- Submit should create flow and redirect to editor
- Cancel should close modal without creating

---

### 2. Inline Editing Pattern

**Question**: How should flow name editing work in the editor?

**Options Evaluated**:
1. Click-to-edit (double-click on name)
2. Always editable text input
3. Edit button next to name
4. Edit mode toggle

**Decision**: **Click-to-edit with pencil icon hint**

**Rationale**:
- Discoverability: Pencil icon signals editability
- Clean UI: No extra buttons when not editing
- Common pattern: Figma, Miro, Notion use this
- Accessible: Can be triggered by keyboard (Enter key)

**Implementation Notes**:
```tsx
// State: isEditing, name
// On click: set isEditing = true, focus input
// On blur/Enter: save, set isEditing = false
// On Escape: cancel, restore original name
```

---

### 3. Navigation Architecture

**Question**: How should breadcrumbs and navigation state be managed?

**Options Evaluated**:
1. Static breadcrumbs based on route
2. Dynamic breadcrumbs from Zustand store
3. No breadcrumbs, only back button
4. Breadcrumbs generated from route + data (e.g., flow name)

**Decision**: **Route-based breadcrumbs with data injection**

**Rationale**:
- Route provides structure (Dashboard > Flows > Edit)
- Data provides context ([Flow Name] instead of [flow_id])
- No extra state management needed beyond current stores
- Works with Next.js routing naturally

**Implementation Notes**:
```tsx
// Use Next.js usePathname() + useParams()
// Map routes to breadcrumb labels
// Inject dynamic data (flow name, etc.) from stores
```

---

### 4. Metrics Dashboard Charting Library

**Question**: Which React charting library should we use?

**Options Evaluated**:

| Library | Pros | Cons | Bundle Size | Score |
|---------|------|------|-------------|-------|
| **Recharts** | - Native React<br>- Good docs<br>- Composable | - Larger bundle<br>- Limited customization | ~96kb | ⭐⭐⭐⭐ |
| **Chart.js** | - Very popular<br>- Feature-rich | - Imperative API<br>- React wrapper needed | ~186kb | ⭐⭐⭐ |
| **Victory** | - Composable<br>- React Native support | - Verbose API<br>- Large bundle | ~185kb | ⭐⭐ |
| **Nivo** | - Beautiful defaults<br>- D3-based | - Large bundle<br>- Complex API | ~120kb+ | ⭐⭐⭐ |

**Decision**: **Recharts**

**Rationale**:
- Good balance of bundle size and features
- Declarative React API (fits our stack)
- Sufficient customization for our needs
- Good TypeScript support
- Proven in production apps

**Implementation Notes**:
```bash
npm install recharts
```

Chart types needed:
- Line chart for execution trends over time
- Bar chart for execution counts by status
- Pie/Donut chart for error distribution (optional)

---

### 5. Real-Time Metrics Updates

**Question**: How should metrics dashboard update in real-time?

**Options Evaluated**:
1. **Polling**: setInterval to fetch every N seconds
2. **Server-Sent Events (SSE)**: Backend pushes updates
3. **WebSocket**: Bidirectional connection
4. **No real-time**: Manual refresh only

**Decision**: **Polling with 30-second interval**

**Rationale**:
- Backend already has REST endpoints (no SSE/WebSocket)
- Metrics don't need subsecond updates
- Simpler implementation (no connection management)
- Can optimize later if needed
- User can manually refresh anytime

**Implementation Notes**:
```tsx
useEffect(() => {
  fetchMetrics(); // Initial fetch
  const interval = setInterval(fetchMetrics, 30000);
  return () => clearInterval(interval);
}, []);
```

---

## Component Design Specifications

### CreateFlowModal Component

**Purpose**: Modal dialog for creating new flows

**Props**:
```tsx
interface CreateFlowModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (flow: Flow) => void;
}
```

**State**:
```tsx
{
  name: string;
  description: string;
  variables: Record<string, any>;
  isSubmitting: boolean;
  error: string | null;
}
```

**API Integration**:
```tsx
const createFlow = async (data) => {
  const response = await apiClient.post('/api/v1/flows', data);
  if (response.error) throw new Error(response.error);
  return response.data;
};
```

---

### FlowPropertiesPanel Component

**Purpose**: Side panel for editing flow properties

**Props**:
```tsx
interface FlowPropertiesPanelProps {
  flow: Flow;
  isOpen: boolean;
  onClose: () => void;
  onSave: (updates: Partial<Flow>) => Promise<void>;
}
```

**Sections**:
1. **General**: Name, Description
2. **Variables**: Key-value pairs (JSON editor)
3. **Settings**: Execution timeout, retry policy, etc.
4. **Metadata**: Created date, version, last modified (read-only)

---

### MetricsDashboard Component

**Purpose**: Main observability dashboard

**Layout**:
```
+------------------------------------------+
| Time Range Filter: [Last 24h ▼] Refresh |
+------------------------------------------+
|  Total      Success    Error    Avg Time |
|  Executions Rate       Rate     (seconds)|
|  1,234      98.5%      1.5%     2.3s     |
+------------------------------------------+
| Execution Trend (Line Chart)             |
|                                          |
+------------------------------------------+
| Recent Errors (Table)                    |
| Time | Flow | Error                      |
+------------------------------------------+
```

**Metrics Displayed**:
- Total executions (count, 24h)
- Success rate (percentage)
- Error rate (percentage)
- Average execution time (seconds)
- Execution trend chart (last 24h, hourly buckets)
- Recent errors (last 10)

---

## API Integration Patterns

### Standard Hook Pattern

All API integrations follow this pattern:

```tsx
function useFlows() {
  const [flows, setFlows] = useState<Flow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchFlows = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiClient.get('/api/v1/flows');
      if (response.error) throw new Error(response.error);
      setFlows(response.data.flows);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const createFlow = async (data: CreateFlowData) => {
    const response = await apiClient.post('/api/v1/flows', data);
    if (response.error) throw new Error(response.error);
    return response.data;
  };

  const updateFlow = async (id: number, data: Partial<Flow>) => {
    const response = await apiClient.put(`/api/v1/flows/${id}`, data);
    if (response.error) throw new Error(response.error);
    return response.data;
  };

  useEffect(() => {
    fetchFlows();
  }, []);

  return { flows, loading, error, createFlow, updateFlow, refetch: fetchFlows };
}
```

### Error Handling Pattern

All API errors should:
1. Display toast notification (for background operations)
2. Show inline error (for form submissions)
3. Log to console (for debugging)
4. Provide retry option (where applicable)

```tsx
const handleSubmit = async () => {
  try {
    await createFlow(formData);
    toast.success('Flow created successfully');
    onSuccess();
  } catch (error) {
    toast.error('Failed to create flow');
    setFormError(error.message);
    console.error('Flow creation failed:', error);
  }
};
```

### Loading State Pattern

Three types of loading states:

1. **Initial Load**: Full-page skeleton
2. **Refetch**: Subtle spinner in corner
3. **Submit**: Disabled button with spinner

```tsx
{loading ? (
  <Skeleton count={5} />
) : error ? (
  <ErrorState message={error} onRetry={refetch} />
) : flows.length === 0 ? (
  <EmptyState message="No flows yet" action={<CreateFlowButton />} />
) : (
  <FlowList flows={flows} />
)}
```

---

## Accessibility Requirements

### Keyboard Navigation
- All interactive elements must be keyboard accessible
- Tab order must be logical
- Focus indicators must be visible
- Escape key closes modals/panels

### Screen Reader Support
- Proper ARIA labels on all controls
- Status updates announced (via aria-live)
- Error messages associated with form fields (aria-describedby)
- Loading states announced

### Color & Contrast
- Don't rely on color alone for status
- Meet WCAG AA contrast ratios (4.5:1 for text)
- Use icons + text for status indicators

---

## Performance Considerations

### Bundle Size
- Lazy load charting library (next/dynamic)
- Code-split observability dashboard
- Tree-shake unused UI components

### Rendering Performance
- Memoize chart components
- Virtualize long lists (if >100 items)
- Debounce search inputs

### API Efficiency
- Cache API responses (SWR or React Query pattern)
- Batch API calls where possible
- Use pagination for large datasets

---

## Testing Strategy

### Unit Tests (Jest + React Testing Library)
```tsx
describe('CreateFlowModal', () => {
  it('renders form fields', () => {
    render(<CreateFlowModal isOpen={true} onClose={jest.fn()} onSuccess={jest.fn()} />);
    expect(screen.getByLabelText('Name')).toBeInTheDocument();
  });

  it('validates required fields', async () => {
    render(<CreateFlowModal isOpen={true} onClose={jest.fn()} onSuccess={jest.fn()} />);
    fireEvent.click(screen.getByText('Create'));
    expect(await screen.findByText('Name is required')).toBeInTheDocument();
  });

  it('calls API on submit', async () => {
    const onSuccess = jest.fn();
    render(<CreateFlowModal isOpen={true} onClose={jest.fn()} onSuccess={onSuccess} />);

    fireEvent.change(screen.getByLabelText('Name'), { target: { value: 'Test Flow' } });
    fireEvent.click(screen.getByText('Create'));

    await waitFor(() => expect(onSuccess).toHaveBeenCalled());
  });
});
```

### E2E Tests (Playwright)
```tsx
test('create flow end-to-end', async ({ page }) => {
  await page.goto('/dashboard');
  await page.click('text=Create Flow');
  await page.fill('[name="name"]', 'My Test Flow');
  await page.fill('[name="description"]', 'Test description');
  await page.click('button:has-text("Create")');

  await expect(page).toHaveURL(/\/flows\/\d+\/edit/);
  await expect(page.locator('h1')).toContainText('My Test Flow');
});
```

---

## Dependencies & Installation

### New Dependencies
```json
{
  "dependencies": {
    "recharts": "^2.10.0"
  },
  "devDependencies": {
    "@testing-library/user-event": "^14.5.0"
  }
}
```

### Existing Dependencies (Used)
- react-flow: Flow editor
- zustand: State management
- tailwindcss: Styling
- @headlessui/react: Modal, dropdown components
- react-hook-form: Form management
- zod: Form validation

---

## Implementation Priorities

### Phase 1 (High Priority - Week 1)
1. Navigation improvements (dashboard button, breadcrumbs)
2. Flow creation modal
3. Flow name editing

### Phase 2 (Medium Priority - Week 1-2)
4. Flow properties panel
5. Observability dashboard skeleton
6. Basic metrics display

### Phase 3 (Medium Priority - Week 2)
7. Metrics charting
8. Real-time updates
9. UI-backend integration fixes

### Phase 4 (Lower Priority - Week 3)
10. Advanced filtering
11. Performance optimizations
12. Accessibility audit

---

## Open Questions

1. **Metrics Aggregation**: Does backend provide pre-aggregated metrics or do we aggregate in frontend?
   - *Investigation needed*: Check `/api/v1/metrics` endpoint

2. **Flow Versioning**: Should version history be accessible from properties panel?
   - *Decision pending*: Defer to future enhancement

3. **Collaborative Editing**: If two users edit same flow, how to handle conflicts?
   - *Decision*: Out of scope for this phase, show "edited by X" indicator only

---

**Research Complete**: Ready for task breakdown via `/tasks` command.
