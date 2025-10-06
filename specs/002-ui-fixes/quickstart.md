# Quickstart Testing Scenarios: UI Fixes

**Feature**: 002-ui-fixes
**Purpose**: User acceptance testing scenarios for UI improvements
**Date**: 2025-10-06

---

## Scenario 1: Create a New Flow

**Goal**: Verify users can create flows from the dashboard

**Prerequisites**:
- User is logged in
- On the dashboard page
- Has permissions to create flows

**Steps**:
1. Navigate to dashboard (`/dashboard`)
2. Click "Create Flow" or "+ New Flow" button
3. Modal dialog should appear
4. Enter flow name: "Customer Onboarding Flow"
5. Enter description: "Automated customer onboarding process"
6. Click "Create" button
7. Should redirect to flow editor (`/flows/{id}/edit`)
8. Flow name should appear in editor header
9. Flow should appear in dashboard flows list (navigate back to verify)

**Expected Results**:
- ✅ Modal opens smoothly
- ✅ Form validation works (name required)
- ✅ Flow created in backend (API call succeeds)
- ✅ Redirect to editor happens automatically
- ✅ Flow appears in flows list

**Error Cases to Test**:
- Submit with empty name → Error: "Name is required"
- Submit with duplicate name → Error: "Flow with this name already exists"
- Backend error → Error message displayed, modal stays open

---

## Scenario 2: Edit Flow Name

**Goal**: Verify users can update flow names in the editor

**Prerequisites**:
- User has at least one flow
- User is viewing flow in editor

**Steps**:
1. Navigate to flow editor (`/flows/{id}/edit`)
2. Click on flow name in header (or click pencil icon)
3. Name should become editable (input field appears)
4. Change name to "Updated Flow Name"
5. Press Enter or click outside input
6. Name should save automatically
7. Success message should appear (toast notification)
8. Refresh page to verify name persisted

**Expected Results**:
- ✅ Click-to-edit works smoothly
- ✅ Input auto-focuses
- ✅ Enter key saves changes
- ✅ Escape key cancels editing
- ✅ Name persists after save
- ✅ Success feedback provided

**Error Cases to Test**:
- Change to empty name → Error: "Name cannot be empty"
- Change to existing name → Error: "Flow with this name already exists"
- Backend error → Error message, name reverts to original

---

## Scenario 3: Navigate Back to Dashboard

**Goal**: Verify navigation works from all pages

**Prerequisites**:
- User is logged in
- Can be on any page

**Test Pages**:
1. From Flow Editor:
   - Click "Dashboard" in header → Should return to dashboard
   - Click logo/home icon → Should return to dashboard

2. From Crews Page:
   - Click "Dashboard" in header → Should return to dashboard

3. From Tools Page:
   - Click "Dashboard" in header → Should return to dashboard

4. From Chat Page:
   - Click "Dashboard" in header → Should return to dashboard

5. From Executions Page:
   - Click "Dashboard" in header → Should return to dashboard

**Expected Results**:
- ✅ Dashboard button visible on all pages
- ✅ Clicking dashboard button navigates to `/dashboard`
- ✅ Navigation is smooth (no flicker)
- ✅ Current page highlighted in nav menu
- ✅ Logo click returns to dashboard

---

## Scenario 4: View Observability Dashboard

**Goal**: Verify metrics dashboard displays correctly

**Prerequisites**:
- User is logged in
- System has some execution history (run a few flows first)

**Steps**:
1. Navigate to dashboard
2. Click "Observability" or "Metrics" in navigation menu
3. Metrics dashboard should load
4. Verify metric cards display:
   - Total Executions (number)
   - Success Rate (percentage)
   - Error Rate (percentage)
   - Average Execution Time (seconds)
5. Verify execution trend chart appears
6. Verify recent errors list appears (if any errors exist)
7. Change time range filter (e.g., Last 24h → Last 7 days)
8. Metrics should update
9. Click "Refresh" button
10. Metrics should reload

**Expected Results**:
- ✅ Dashboard loads within 2 seconds
- ✅ All metric cards display data
- ✅ Chart renders correctly
- ✅ Time range filter works
- ✅ Refresh button updates data
- ✅ Auto-refresh happens every 30 seconds
- ✅ Loading states shown during data fetch

**Empty State**:
- If no executions exist → Show "No execution data yet. Run a flow to see metrics."

**Error State**:
- If backend unavailable → Show error message with retry button

---

## Scenario 5: Edit Flow Properties

**Goal**: Verify users can edit flow metadata and settings

**Prerequisites**:
- User has a flow open in editor

**Steps**:
1. Open flow in editor (`/flows/{id}/edit`)
2. Click "Properties" button or panel icon
3. Properties panel should slide in from right
4. Verify sections visible:
   - General (Name, Description)
   - Variables (key-value editor)
   - Settings (timeout, retry policy)
   - Metadata (created date, version - read-only)
5. Edit description: "Updated description text"
6. Add a variable: `customer_id` = `12345`
7. Click "Save" button
8. Success message should appear
9. Close properties panel
10. Reopen to verify changes persisted

**Expected Results**:
- ✅ Properties panel opens smoothly
- ✅ All fields editable (except metadata)
- ✅ Variables editor supports add/edit/delete
- ✅ Validation works for each field
- ✅ Save persists changes
- ✅ Panel can be closed without saving (shows unsaved warning)

---

## Scenario 6: Create and Manage Crew via UI

**Goal**: Verify crew management UI works end-to-end

**Prerequisites**:
- User has created some agents
- User is on crews page

**Steps**:
1. Navigate to `/crews`
2. Click "Create Crew" button
3. Form should appear (modal or page)
4. Enter crew name: "Support Team"
5. Enter description: "Customer support crew"
6. Select agents from dropdown (add 2-3 agents)
7. Click "Create" button
8. Crew should appear in crews list
9. Click on crew to view details
10. Click "Edit" button
11. Change crew name to "Support Team Updated"
12. Click "Save"
13. Verify changes persisted

**Expected Results**:
- ✅ Crew creation works
- ✅ Agent selection dropdown shows available agents
- ✅ Crew appears in list after creation
- ✅ Crew details page accessible
- ✅ Crew editing works
- ✅ Changes persist after save

---

## Scenario 7: Register and Test Tool via UI

**Goal**: Verify tool management UI works end-to-end

**Prerequisites**:
- User is on tools page

**Steps**:
1. Navigate to `/tools`
2. Click "Register Tool" or "+ New Tool" button
3. Form should appear
4. Enter tool details:
   - Name: "Weather API"
   - Description: "Get current weather data"
   - Type: "REST API"
   - Configuration: (JSON schema for inputs/outputs)
5. Click "Create" button
6. Tool should appear in tools list
7. Click "Test" button next to tool
8. Enter test inputs (e.g., city: "San Francisco")
9. Click "Run Test"
10. Test results should display (API response or error)

**Expected Results**:
- ✅ Tool creation form works
- ✅ JSON schema validation works
- ✅ Tool appears in list after creation
- ✅ Test functionality works
- ✅ Test results displayed clearly
- ✅ Error handling for failed tests

---

## Scenario 8: Monitor Flow Execution in Real-Time

**Goal**: Verify execution monitoring UI works

**Prerequisites**:
- User has a flow with multiple steps
- User executes the flow

**Steps**:
1. Navigate to flow editor
2. Click "Execute" or "Run" button
3. Execution should start
4. Real-time progress should display:
   - Current step highlighted
   - Step status (pending → running → complete)
   - Step outputs visible
5. Navigate to `/executions` page
6. Find the running execution in list
7. Click to view execution details
8. Execution logs should stream in real-time
9. If execution has errors, errors should be highlighted
10. After completion, full execution log visible

**Expected Results**:
- ✅ Execution starts when clicked
- ✅ Real-time progress updates
- ✅ Step statuses update live
- ✅ Execution appears in executions list
- ✅ Execution details page works
- ✅ Logs stream in real-time
- ✅ Error states highlighted

---

## Scenario 9: Configure LLM Provider

**Goal**: Verify LLM provider management UI works

**Prerequisites**:
- User is on LLM providers page or settings

**Steps**:
1. Navigate to `/llm-providers` or settings
2. Click "Add Provider" button
3. Form should appear
4. Select provider type: "OpenAI"
5. Enter provider details:
   - Name: "OpenAI GPT-4"
   - API Key: (enter key)
   - Model: "gpt-4"
   - Configuration: (temperature, max_tokens, etc.)
6. Click "Test Connection" button
7. Should verify API key works
8. Click "Save" button
9. Provider should appear in list
10. Try editing provider (click edit icon)
11. Update model to "gpt-4-turbo"
12. Save changes

**Expected Results**:
- ✅ Provider creation form works
- ✅ Test connection button validates API key
- ✅ Provider appears in list after creation
- ✅ Provider editing works
- ✅ API key masked in UI (shows *****)
- ✅ Changes persist after save

---

## Scenario 10: Handle Backend Errors Gracefully

**Goal**: Verify UI handles errors properly

**Prerequisites**:
- Ability to simulate backend errors (mock API or kill backend)

**Test Cases**:

1. **Backend Unavailable**:
   - Stop backend server
   - Try to load dashboard
   - Should show: "Unable to connect to server. Please try again."
   - Retry button should reload

2. **API Error (500)**:
   - Trigger server error (bad data)
   - Should show: "Something went wrong. Please try again."
   - Error logged to console

3. **Authentication Error (401)**:
   - Invalidate token
   - Make API request
   - Should auto-logout and redirect to login
   - Should show: "Session expired. Please log in again."

4. **Validation Error (400)**:
   - Submit invalid form data
   - Should show inline validation errors
   - Fields highlighted in red

5. **Network Error**:
   - Disconnect internet
   - Try to make API call
   - Should show: "Network error. Please check your connection."

**Expected Results**:
- ✅ All errors handled gracefully
- ✅ Error messages clear and actionable
- ✅ Retry options provided where applicable
- ✅ No crashes or white screens
- ✅ Errors logged for debugging

---

## Performance Benchmarks

**Dashboard Load Time**:
- Initial load: < 2 seconds
- With 100 flows: < 3 seconds
- With 1000 executions: < 3 seconds

**Flow Editor Load Time**:
- Simple flow (5 nodes): < 1 second
- Complex flow (50 nodes): < 2 seconds
- Very large flow (200 nodes): < 5 seconds

**Metrics Dashboard Load Time**:
- With 24h of data: < 2 seconds
- With 7 days of data: < 3 seconds
- With 30 days of data: < 5 seconds

**Interaction Response Time**:
- Button clicks: < 100ms feedback
- Form submissions: < 500ms response
- Navigation: < 200ms page transition

---

## Accessibility Testing

**Keyboard Navigation**:
- Tab through all interactive elements
- Arrow keys navigate menus/dropdowns
- Enter/Space activate buttons
- Escape closes modals/panels

**Screen Reader Testing**:
- All buttons have descriptive labels
- Form errors announced
- Loading states announced
- Status changes announced

**Visual Testing**:
- High contrast mode works
- Text readable at 200% zoom
- No color-only indicators
- Focus indicators visible

---

## Cross-Browser Testing

**Browsers to Test**:
- Chrome (latest)
- Firefox (latest)
- Safari (latest)
- Edge (latest)

**Features to Verify**:
- Layout consistency
- Form functionality
- Chart rendering
- Modal/dropdown behavior
- Animation smoothness

---

**Testing Complete**: All scenarios pass → Ready for production deployment
