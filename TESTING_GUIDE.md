# Testing Guide - Example Flows and Crews

This guide provides step-by-step instructions for creating and testing example flows and crews in the CrewAI Platform.

## Prerequisites

1. All services running via `docker-compose up`
2. Frontend accessible at `http://localhost:3001`
3. Backend API accessible at `http://localhost:8000`
4. User account created and logged in

## Table of Contents

- [Creating an Example Flow](#creating-an-example-flow)
- [Testing Flow Features](#testing-flow-features)
- [Creating an Example Crew](#creating-an-example-crew)
- [Testing Crew Features](#testing-crew-features)
- [End-to-End Flow Execution](#end-to-end-flow-execution)

---

## Creating an Example Flow

### Flow: "Research to Report Workflow"

This example demonstrates a complete workflow with Input → Agent → Condition → Agent → Output.

#### Step 1: Navigate to Flows

1. Open http://localhost:3001/flows
2. Click "Create Flow" button

#### Step 2: Configure Flow Properties

1. Click "Properties" button in toolbar
2. Set the following:
   - **Name**: `Research to Report Workflow`
   - **Description**: `A complete workflow demonstrating input → processing → output flow`
   - **Variables**: Leave empty for now
3. Click "Save Changes"

#### Step 3: Add Input Node

1. From the Node Palette on the left, drag **Input** node to the canvas
2. Position it at the top (approximately x: 100, y: 100)
3. Click the node to select it
4. In the Property Panel on the right, configure:
   - **Label**: `Research Topic`
   - **Description**: `Enter the research topic and parameters`
   - **Inputs**:
     ```json
     [
       {"name": "topic", "type": "string", "required": true},
       {"name": "depth", "type": "string", "required": false}
     ]
     ```

#### Step 4: Add First Agent Node

1. Drag **Agent** node to the canvas below the Input node
2. Position it at (approximately x: 100, y: 280)
3. Configure in Property Panel:
   - **Label**: `Research Phase`
   - **Task**: `Research the topic provided in the input`
   - **Expected Output**: `Comprehensive research summary with key findings`

#### Step 5: Add Condition Node

1. Drag **Condition** node below the first Agent
2. Position it at (approximately x: 100, y: 460)
3. Configure:
   - **Label**: `Quality Gate`
   - **Condition**: `word_count >= 100`
   - **Description**: `Verify research quality meets minimum requirements`

#### Step 6: Add Second Agent Node

1. Drag **Agent** node to the right of the Condition node
2. Position it at (approximately x: 400, y: 460)
3. Configure:
   - **Label**: `Report Writing`
   - **Task**: `Create a comprehensive, well-structured report based on the research`
   - **Expected Output**: `Well-formatted report with introduction, body, and conclusion`

#### Step 7: Add Output Node

1. Drag **Output** node below the second Agent
2. Position it at (approximately x: 400, y: 640)
3. Configure:
   - **Label**: `Final Report`
   - **Description**: `The completed research report`
   - **Outputs**:
     ```json
     [
       {"name": "report", "type": "string"},
       {"name": "word_count", "type": "number"},
       {"name": "metadata", "type": "object"}
     ]
     ```

#### Step 8: Connect Nodes

1. Click and drag from the **bottom handle** of Input node to the **top handle** of first Agent node
2. Connect first Agent → Condition node
3. Connect Condition → second Agent node
4. Connect second Agent → Output node

Your flow should now look like this:
```
Input (Research Topic)
  ↓
Agent (Research Phase)
  ↓
Condition (Quality Gate)
  ↓
Agent (Report Writing)
  ↓
Output (Final Report)
```

#### Step 9: Save the Flow

1. Click "Save" in the toolbar
2. Verify you see a success message
3. Flow should be saved and visible in the flows list

---

## Testing Flow Features

### 1. Node Manipulation

#### Test: Drag and Drop
- ✅ Drag new nodes from palette onto canvas
- ✅ Nodes should appear at mouse position
- ✅ Newly created nodes should have default data

#### Test: Node Selection
- ✅ Click a node to select it
- ✅ Selected node should show blue border and ring
- ✅ Property panel should display node properties
- ✅ Click canvas background to deselect

#### Test: Node Editing
- ✅ Select a node
- ✅ Edit properties in Property Panel
- ✅ Changes should be reflected immediately
- ✅ Save button should update flow

#### Test: Node Resizing (Input/Output nodes only)
- ✅ Hover over Input or Output node edge
- ✅ Cursor should change to resize
- ✅ Drag to resize node
- ✅ Width should persist after save/reload

#### Test: Node Deletion
- ✅ Select a node
- ✅ Press Delete or Backspace key
- ✅ Node should be removed
- ✅ Connected edges should also be removed

### 2. Connection Management

#### Test: Creating Connections
- ✅ Drag from source handle (bottom) to target handle (top)
- ✅ Connection should appear as curved line
- ✅ Connection should have delete button in center

#### Test: Connection Validation
- ✅ Try connecting Input directly to Output
- ✅ Should show error: "Invalid connection"
- ✅ Valid connections (Agent→Agent) should work

#### Test: Deleting Connections
- ✅ Click connection to select it
- ✅ Press Delete or Backspace
- ✅ Connection should be removed
- ✅ **OR** click the X button on the connection
- ✅ Connection should be removed

### 3. Flow Properties

#### Test: Edit Flow Name In-Place
- ✅ Click flow name in toolbar
- ✅ Name should become editable input
- ✅ Type new name and press Enter
- ✅ Name should update in toolbar and database

#### Test: Flow Properties Panel
- ✅ Click "Properties" button
- ✅ Panel should slide in from right
- ✅ Edit name, description, variables
- ✅ Click "Save Changes"
- ✅ Changes should persist
- ✅ Click X or outside to close panel

### 4. Save and Discard

#### Test: Save Flow
- ✅ Make changes to flow
- ✅ Click "Save" button
- ✅ Should show success toast
- ✅ Should navigate to /flows list
- ✅ Changes should be persisted

#### Test: Delete Flow
- ✅ Click "Delete" button
- ✅ Should show confirmation dialog
- ✅ Confirm deletion
- ✅ Should navigate to /flows list
- ✅ Flow should be removed from database

### 5. Flow Execution

#### Test: Execute Flow with Inputs
- ✅ Click "Execute" button
- ✅ Modal should appear asking for inputs
- ✅ Should show input fields for each Input node variable:
   - `topic` (string input)
   - `depth` (string input)
- ✅ Fill in values:
   ```
   topic: "AI Safety"
   depth: "detailed"
   ```
- ✅ Click "Execute"
- ✅ Should create execution and redirect to execution page
- ✅ Should show execution status and logs

---

## Creating an Example Crew

### Crew: "Content Creation Team"

This example demonstrates a crew with multiple agents working sequentially.

#### Step 1: Navigate to Crews

1. Open http://localhost:3001/crews
2. Click "Create Crew" button

#### Step 2: Configure Crew Properties

1. Set the following:
   - **Name**: `Content Creation Team`
   - **Description**: `A crew that researches topics and creates high-quality content`
   - **Process**: `Sequential`
   - **Memory**: Enable
   - **Verbose**: Enable

#### Step 3: Create or Select Agents

You'll need at least 2 agents. If none exist, create them first:

**Agent 1: Research Analyst**
- Name: `Research Analyst`
- Role: `Senior Research Analyst`
- Goal: `Conduct thorough research on given topics`
- Backstory: `You are a meticulous researcher with years of experience`

**Agent 2: Content Writer**
- Name: `Content Writer`
- Role: `Professional Content Writer`
- Goal: `Create engaging and well-structured content`
- Backstory: `You are a skilled writer who excels at transforming research into compelling narratives`

#### Step 4: Add Agents to Crew

1. In crew configuration, add agents in order:
   - Position 1: Research Analyst
   - Position 2: Content Writer

#### Step 5: Save Crew

1. Click "Save" or "Create"
2. Crew should be visible in crews list

---

## Testing Crew Features

### 1. Crew Creation
- ✅ Create new crew via UI
- ✅ All fields should be saved correctly
- ✅ Agents should be associated in correct order

### 2. Crew Editing
- ✅ Edit crew properties
- ✅ Add/remove agents
- ✅ Reorder agents
- ✅ Changes should persist

### 3. Crew Execution
- ✅ Execute crew with a task
- ✅ Agents should run in sequential order
- ✅ Execution logs should show agent activities

---

## End-to-End Flow Execution

### Test: Complete Flow Execution

1. **Create Flow** (as described above)
2. **Add Real Agents** to Agent nodes:
   - Edit each Agent node
   - Select an actual agent from your agents list
   - Or create placeholder agents

3. **Execute Flow**:
   ```
   Input:
   {
     "topic": "The Future of AI in Healthcare",
     "depth": "comprehensive"
   }
   ```

4. **Monitor Execution**:
   - Navigate to Executions page
   - View execution details
   - Monitor real-time logs
   - Check execution status (running → completed/failed)

5. **Verify Results**:
   - Check output values
   - Verify all nodes executed in correct order
   - Review execution metadata

### Test: Error Handling

1. **Execute with Missing Required Input**:
   - Leave `topic` empty
   - Should show validation error

2. **Execute with Invalid Data**:
   - Provide wrong data type
   - Should show type error

3. **Execution Failure**:
   - If agent fails, execution status should be "failed"
   - Error message should be displayed
   - Logs should show failure reason

---

## UI/UX Verification Checklist

### Navigation
- ✅ Breadcrumbs show correct path
- ✅ Navigation menu items work
- ✅ User profile menu accessible

### Flow Editor
- ✅ Node palette visible and functional
- ✅ Canvas allows pan and zoom
- ✅ MiniMap shows overall flow structure
- ✅ Controls (zoom, fit view) work
- ✅ Keyboard shortcuts work (Delete, Backspace)

### Visual Consistency
- ✅ All nodes have consistent styling:
   - min-w-[220px] (260px for Input/Output)
   - rounded-2xl borders
   - shadow-lg
   - gradient backgrounds
- ✅ Handles are consistent size (w-10 h-10)
- ✅ Icons and colors match node types

### Responsive Design
- ✅ UI works on different screen sizes
- ✅ Panels slide in/out smoothly
- ✅ No overflow or layout issues

### Accessibility
- ✅ Keyboard navigation works
- ✅ Focus indicators visible
- ✅ ARIA labels present
- ✅ Color contrast meets standards

---

## Performance Verification

### Load Testing
1. Create flow with 20+ nodes
2. Verify smooth dragging and selection
3. Check save/load performance

### Real-time Updates
1. Execute flow
2. Verify logs stream in real-time
3. Check WebSocket connection stability

---

## Summary

**Features to Test:**

| Feature | Status | Notes |
|---------|--------|-------|
| Flow Creation | ✅ | Via UI |
| Node Drag & Drop | ✅ | All node types |
| Node Selection | ✅ | Click to select |
| Node Editing | ✅ | Property panel |
| Node Deletion | ✅ | Delete/Backspace |
| Node Resizing | ✅ | Input/Output only |
| Connection Creation | ✅ | Drag handles |
| Connection Validation | ✅ | Input→Output blocked |
| Connection Deletion | ✅ | Key + button |
| Flow Properties | ✅ | Side panel |
| Flow Name Edit | ✅ | In-place |
| Flow Save | ✅ | Returns to list |
| Flow Delete | ✅ | With confirmation |
| Flow Execution | ✅ | With input modal |
| Execution Monitoring | ✅ | Real-time logs |
| Crew Creation | ✅ | Via UI |
| Crew Execution | ✅ | Sequential process |

**All major features implemented and ready for testing!**
