# Tasks: UI Functionality Fixes and Enhancements

**Feature**: 002-ui-fixes
**Branch**: `002-ui-fixes`
**Prerequisites**: spec.md, plan.md, research.md, quickstart.md

## Execution Flow
```
1. Load plan.md from feature directory
   → ✓ Found: UI fixes for flow creation, editing, navigation, observability
2. Extract task categories:
   → ✓ Navigation fixes (5 tasks)
   → ✓ Flow creation (15 tasks)
   → ✓ Flow editing (15 tasks)
   → ✓ Observability dashboard (30 tasks)
   → ✓ UI-backend integration (45 tasks)
   → ✓ Testing & Polish (30 tasks)
3. Apply task rules:
   → ✓ Different files = marked [P] for parallel
   → ✓ Same file = sequential (no [P])
4. Number tasks sequentially (T001-T140)
5. Return: SUCCESS (140 tasks ready for execution)
```

## Format: `[ID] [P?] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- Includes exact file paths in descriptions

---

## Phase 1: Navigation Improvements (T001-T010)

### Header Navigation Component
- [x] T001 Update Navigation header in `frontend/src/components/shared/Navigation.tsx` - add Dashboard/Home button
- [x] T002 Add active page highlighting in `frontend/src/components/shared/Navigation.tsx`
- [x] T003 [P] Create Breadcrumbs component in `frontend/src/components/navigation/Breadcrumbs.tsx`
- [x] T004 [P] Create useNavigation hook in `frontend/src/lib/hooks/useNavigation.ts`
- [x] T005 Update all pages to include Navigation component with dashboard button

### User Profile Menu
- [x] T006 [P] Create UserProfileMenu component in `frontend/src/components/navigation/UserProfileMenu.tsx`
- [x] T007 Integrate UserProfileMenu into Navigation header
- [x] T008 [P] Add logout functionality in UserProfileMenu

### Breadcrumbs Integration
- [x] T009 Add breadcrumbs to Flow Editor page (`frontend/src/app/flows/[flow_id]/edit.tsx`)
- [x] T010 Add breadcrumbs to other pages (Crews, Tools, Chat, Executions)

---

## Phase 2: Flow Creation (T011-T025)

### Create Flow Modal Component
- [x] T011 [P] Create CreateFlowModal component in `frontend/src/components/flows/CreateFlowModal.tsx`
- [x] T012 [P] Create FlowForm component (reusable) in `frontend/src/components/flows/FlowForm.tsx`
- [x] T013 Add form validation using zod in FlowForm
- [x] T014 [P] Create useFlows hook in `frontend/src/lib/hooks/useFlows.ts`
- [x] T015 Integrate createFlow API call in useFlows hook

### Dashboard Integration
- [x] T016 Update Dashboard page (`frontend/src/app/dashboard/page.tsx`) to add "Create Flow" button
- [x] T017 Wire CreateFlowModal to Dashboard page
- [x] T018 Handle flow creation success (redirect to editor)
- [x] T019 Handle flow creation errors (display in modal)

### Flow Creation API Integration
- [x] T020 Test API POST /api/v1/flows endpoint exists
- [ ] T021 [P] Add flow creation tests in `frontend/tests/components/CreateFlowModal.test.tsx`
- [ ] T022 [P] Add E2E test for flow creation in `frontend/tests/e2e/flow-creation.spec.ts`

### Flow List Display
- [x] T023 Update Dashboard to display flows list with newly created flows
- [x] T024 Add empty state for flows list ("No flows yet. Create your first flow")
- [x] T025 Add loading state for flows list (skeleton)

---

## Phase 3: Flow Editing (T026-T040)

### Inline Name Editing
- [x] T026 [P] Create FlowNameEditor component in `frontend/src/components/flows/FlowNameEditor.tsx`
- [x] T027 Implement click-to-edit functionality in FlowNameEditor
- [x] T028 Add keyboard support (Enter=save, Escape=cancel)
- [x] T029 Integrate FlowNameEditor into Flow Editor page (`frontend/src/app/flows/[flow_id]/edit.tsx`)

### Flow Properties Panel
- [x] T030 [P] Create FlowPropertiesPanel component in `frontend/src/components/flows/FlowPropertiesPanel.tsx`
- [x] T031 Add General section (name, description)
- [x] T032 [P] Add Variables section with JSON editor in FlowPropertiesPanel
- [x] T033 [P] Add Settings section (timeout, retry policy) in FlowPropertiesPanel
- [x] T034 [P] Add Metadata section (read-only) in FlowPropertiesPanel
- [x] T035 Add slide-in animation for properties panel

### Flow Update API Integration
- [x] T036 Add updateFlow function in useFlows hook
- [x] T037 Wire FlowPropertiesPanel save button to updateFlow API
- [x] T038 Handle update success (show toast, close panel)
- [x] T039 Handle update errors (display in panel)
- [x] T040 Add unsaved changes detection in FlowPropertiesPanel

---

## Phase 4: Observability Dashboard (T041-T070)

### Metrics Dashboard Page
- [x] T041 [P] Create Observability dashboard page in `frontend/src/app/observability/index.tsx`
- [x] T042 [P] Create MetricsDashboard component in `frontend/src/components/observability/MetricsDashboard.tsx`
- [x] T043 Add link to Observability in main navigation

### Metrics API Integration
- [x] T044 [P] Create useMetrics hook in `frontend/src/lib/hooks/useMetrics.ts`
- [x] T045 Implement fetchMetrics function calling GET /api/v1/executions with aggregation
- [x] T046 Add auto-refresh with 30-second interval in useMetrics

### Metric Cards
- [x] T047 [P] Create MetricsCard component in `frontend/src/components/observability/MetricsCard.tsx`
- [x] T048 [P] Create TotalExecutionsCard in `frontend/src/components/observability/metrics/TotalExecutionsCard.tsx`
- [x] T049 [P] Create SuccessRateCard in `frontend/src/components/observability/metrics/SuccessRateCard.tsx`
- [x] T050 [P] Create ErrorRateCard in `frontend/src/components/observability/metrics/ErrorRateCard.tsx`
- [x] T051 [P] Create AvgTimeCard in `frontend/src/components/observability/metrics/AvgTimeCard.tsx`
- [x] T052 Integrate all metric cards into MetricsDashboard

### Execution Trend Chart
- [x] T053 Install recharts library (`npm install recharts`)
- [x] T054 [P] Create ExecutionTrendChart component in `frontend/src/components/observability/ExecutionTrendChart.tsx`
- [x] T055 Implement line chart showing executions over time (hourly buckets)
- [x] T056 Add hover tooltips to chart
- [x] T057 Integrate ExecutionTrendChart into MetricsDashboard

### Recent Errors List
- [x] T058 [P] Create ErrorsList component in `frontend/src/components/observability/ErrorsList.tsx`
- [x] T059 Fetch recent errors from GET /api/v1/executions?status=failed&limit=10
- [x] T060 Display errors in table (time, flow name, error message)
- [x] T061 Add click to view execution details
- [x] T062 Integrate ErrorsList into MetricsDashboard

### Time Range Filter
- [x] T063 [P] Create TimeRangeFilter component in `frontend/src/components/observability/TimeRangeFilter.tsx`
- [x] T064 Add time range options (Last Hour, 24h, 7 days, 30 days)
- [x] T065 Wire time range to metrics fetching
- [x] T066 Update charts when time range changes

### Dashboard Polish
- [x] T067 Add loading state for metrics dashboard (skeleton)
- [x] T068 Add error state for metrics dashboard (retry button)
- [x] T069 Add empty state ("No execution data yet")
- [x] T070 Add refresh button to manually update metrics

---

## Phase 5: UI-Backend Integration Fixes (T071-T115)

### Crew Management Integration
- [x] T071 Verify Crew API endpoints exist (GET, POST, PUT, DELETE /api/v1/crews)
- [x] T072 [P] Create useCrews hook in `frontend/src/lib/hooks/useCrews.ts`
- [x] T073 Update CrewBuilder component (`frontend/src/components/crews/CrewBuilder.tsx`) to use useCrews
- [x] T074 Add createCrew function to useCrews hook
- [x] T075 Add updateCrew function to useCrews hook
- [x] T076 Add deleteCrew function to useCrews hook
- [x] T077 Fix crew list display in `/crews` page
- [x] T078 Add loading/error/empty states to crew list
- [x] T079 Test crew creation, editing, deletion end-to-end

### Agent Management Integration
- [x] T080 [P] Create useAgents hook in `frontend/src/lib/hooks/useAgents.ts`
- [ ] T081 Update agent management page to use useAgents hook
- [x] T082 Add createAgent, updateAgent, deleteAgent functions
- [ ] T083 Fix agent form submission
- [ ] T084 Fix agent list display
- [ ] T085 Add loading/error/empty states to agent UI

### Tool Registry Integration
- [x] T086 [P] Create useTools hook in `frontend/src/lib/hooks/useTools.ts`
- [ ] T087 Update ToolRegistry component to use useTools hook
- [x] T088 Add createTool, updateTool, deleteTool functions
- [x] T089 Add validateTool function (POST /api/v1/tools/{id}/validate)
- [ ] T090 Fix tool registration form
- [ ] T091 Fix tool list display
- [ ] T092 Add test tool functionality UI
- [ ] T093 Add loading/error/empty states to tool UI

### LLM Provider Management Integration
- [x] T094 [P] Create useLLMProviders hook in `frontend/src/lib/hooks/useLLMProviders.ts`
- [ ] T095 Update LLM provider management page to use useLLMProviders hook
- [x] T096 Add createProvider, updateProvider, deleteProvider functions
- [x] T097 Add testConnection function
- [ ] T098 Fix provider configuration form
- [ ] T099 Fix provider list display
- [ ] T100 Mask API keys in UI (show *****)
- [ ] T101 Add loading/error/empty states to provider UI

### Execution Monitoring Integration
- [x] T102 [P] Create useExecutions hook in `frontend/src/lib/hooks/useExecutions.ts`
- [ ] T103 Update execution list page to use useExecutions hook
- [x] T104 Add fetchExecutionDetails function
- [x] T105 Add fetchExecutionLogs function (SSE streaming)
- [x] T106 Add cancelExecution function
- [ ] T107 Fix execution list display
- [ ] T108 Fix execution details page
- [ ] T109 Implement real-time log streaming
- [ ] T110 Add loading/error/empty states to execution UI

### Form Error Handling
- [ ] T111 Update all forms to display backend validation errors
- [ ] T112 Add inline field errors (aria-describedby)
- [ ] T113 Add form-level error summary
- [ ] T114 Add retry logic for network errors
- [ ] T115 Add toast notifications for all API operations

---

## Phase 6: Testing & Polish (T116-T140)

### Unit Tests
- [ ] T116 [P] Write tests for CreateFlowModal in `frontend/tests/components/CreateFlowModal.test.tsx`
- [ ] T117 [P] Write tests for FlowNameEditor in `frontend/tests/components/FlowNameEditor.test.tsx`
- [ ] T118 [P] Write tests for FlowPropertiesPanel in `frontend/tests/components/FlowPropertiesPanel.test.tsx`
- [ ] T119 [P] Write tests for MetricsDashboard in `frontend/tests/components/MetricsDashboard.test.tsx`
- [ ] T120 [P] Write tests for all custom hooks (useFlows, useMetrics, etc.)

### E2E Tests
- [ ] T121 [P] Write E2E test for flow creation in `frontend/tests/e2e/flow-creation.spec.ts`
- [ ] T122 [P] Write E2E test for flow editing in `frontend/tests/e2e/flow-editing.spec.ts`
- [ ] T123 [P] Write E2E test for navigation in `frontend/tests/e2e/navigation.spec.ts`
- [ ] T124 [P] Write E2E test for observability dashboard in `frontend/tests/e2e/observability.spec.ts`
- [ ] T125 [P] Write E2E test for crew management in `frontend/tests/e2e/crew-management.spec.ts`

### Accessibility
- [ ] T126 Run accessibility audit on all new components
- [ ] T127 Fix keyboard navigation issues
- [ ] T128 Add ARIA labels to all interactive elements
- [ ] T129 Test with screen reader (VoiceOver/NVDA)
- [ ] T130 Fix color contrast issues

### Performance
- [ ] T131 Optimize bundle size (code splitting, tree shaking)
- [ ] T132 Lazy load charting library (next/dynamic)
- [ ] T133 Memoize expensive components
- [ ] T134 Add pagination to long lists
- [ ] T135 Profile and optimize render performance

### Cross-Browser Testing
- [ ] T136 Test in Chrome (latest)
- [ ] T137 Test in Firefox (latest)
- [ ] T138 Test in Safari (latest)
- [ ] T139 Test in Edge (latest)

### Final Polish
- [ ] T140 Code cleanup, remove console.logs, update documentation

---

## Dependencies

**Phase 1 before Phase 2**:
- Navigation must work before flow creation (users need to navigate back)

**Phase 2 before Phase 3**:
- Flow creation must work before flow editing (need flows to edit)

**Phase 2 & 3 before Phase 4**:
- Flows must exist before observability can show meaningful data

**Phase 1-4 before Phase 5**:
- Core UI must work before fixing remaining integrations

**All phases before Phase 6**:
- Implementation complete before testing and polish

---

## Parallel Execution Examples

### Example 1: Metric Cards (T048-T051)
All metric cards are independent components - can build in parallel:
```bash
Task: "Create TotalExecutionsCard"
Task: "Create SuccessRateCard"
Task: "Create ErrorRateCard"
Task: "Create AvgTimeCard"
```

### Example 2: Custom Hooks (T044, T072, T080, T086, T094, T102)
All hooks are independent files - can build in parallel:
```bash
Task: "Create useMetrics hook"
Task: "Create useCrews hook"
Task: "Create useAgents hook"
Task: "Create useTools hook"
Task: "Create useLLMProviders hook"
Task: "Create useExecutions hook"
```

### Example 3: Unit Tests (T116-T120)
All test files are independent - can write in parallel:
```bash
Task: "Write tests for CreateFlowModal"
Task: "Write tests for FlowNameEditor"
Task: "Write tests for FlowPropertiesPanel"
Task: "Write tests for MetricsDashboard"
Task: "Write tests for all hooks"
```

---

## Notes

- **[P] tasks** = Different files, no dependencies - safe for parallel execution
- **Non-[P] tasks** = Shared files or sequential dependencies
- All API integrations assume backend endpoints are functional
- Testing should happen incrementally (test each component as built)
- Commit after completing each logical group (e.g., all navigation, all flow creation)

---

## Validation Checklist

- [x] All user scenarios from spec.md have corresponding tasks
- [x] All components have test tasks
- [x] Parallel tasks ([P]) are truly independent (different files)
- [x] Each task specifies exact file path
- [x] Dependencies documented clearly
- [x] Testing tasks included for all features

**Total Tasks**: 140
**Estimated Duration**: 3 weeks (with 2-3 developers)
**Parallel Execution Opportunities**: 50+ tasks marked [P]

---

*Ready for implementation. Run tasks sequentially or leverage [P] tasks for parallel development.*
