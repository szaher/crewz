# Flow Creation Guide

## Overview

Flows are visual workflows that orchestrate multiple AI agents to accomplish complex tasks. This guide covers creating, configuring, and executing flows.

## Flow Concepts

### Flow Structure

A flow is a directed acyclic graph (DAG) consisting of:

- **Nodes**: Individual tasks performed by agents or tools
- **Edges**: Dependencies between nodes (data flow)
- **Inputs**: Initial data passed to the flow
- **Outputs**: Final results from the flow

### Node Types

1. **Agent Node**: AI agent performs a task using LLM
2. **Tool Node**: Custom Docker tool executes code
3. **Condition Node**: Branching logic based on conditions
4. **Human Input Node**: Waits for human approval/input

## Creating Your First Flow

### Step 1: Access Flow Editor

```
1. Login to platform
2. Navigate to "Flows" in sidebar
3. Click "Create New Flow"
4. Flow editor opens with blank canvas
```

### Step 2: Add Nodes

**Add Agent Node:**
1. Drag "Agent" from left panel to canvas
2. Configure:
   - **Task**: "Analyze the input document and identify key themes"
   - **Expected Output**: "List of 5-10 key themes with explanations"
   - **Agent**: Select from dropdown (e.g., "Research Agent")
   - **Context**: Optional previous node outputs

**Visual Example:**
```
┌────────────────────────────────┐
│      Analyzer Agent Node       │
│                                │
│ Task: Analyze input document   │
│ Output: Key themes             │
│ Agent: Research Agent          │
└────────────────────────────────┘
```

### Step 3: Connect Nodes

Create data flow by connecting nodes:

```
Input → [Analyze] → [Summarize] → [Format] → Output
```

**Connection Rules:**
- Outputs from parent nodes become available as context to child nodes
- No cycles allowed (must be a DAG)
- Multiple inputs can merge into one node

### Step 4: Configure Flow Settings

```json
{
  "name": "Document Analysis Flow",
  "description": "Analyzes documents and generates summaries",
  "timeout": 600,
  "retry_policy": {
    "max_retries": 3,
    "backoff": "exponential"
  },
  "inputs_schema": {
    "document": {
      "type": "string",
      "description": "Document text to analyze"
    }
  }
}
```

### Step 5: Save and Execute

```typescript
// Save flow
await flowApi.create({
  name: "Document Analysis Flow",
  definition: flowDefinition,
  is_active: true
});

// Execute flow
const execution = await flowApi.execute(flowId, {
  inputs: {
    document: "Your document text here..."
  }
});

// Monitor execution
const status = await executionApi.getStatus(execution.id);
```

## Advanced Flow Patterns

### Sequential Processing

```
[Research] → [Analyze] → [Write] → [Review]
```

Each agent builds on previous outputs:

```json
{
  "nodes": [
    {
      "id": "research",
      "type": "agent",
      "agent_id": "researcher",
      "task": "Research topic: {input.topic}"
    },
    {
      "id": "analyze",
      "type": "agent",
      "agent_id": "analyst",
      "task": "Analyze research findings",
      "context": ["{research.output}"]
    },
    {
      "id": "write",
      "type": "agent",
      "agent_id": "writer",
      "task": "Write article based on analysis",
      "context": ["{research.output}", "{analyze.output}"]
    }
  ],
  "edges": [
    {"source": "research", "target": "analyze"},
    {"source": "analyze", "target": "write"}
  ]
}
```

### Parallel Branches

```
            ┌─→ [Branch A] ─┐
[Split] ──┤               ├─→ [Merge]
            └─→ [Branch B] ─┘
```

Process multiple paths simultaneously:

```json
{
  "nodes": [
    {"id": "split", "type": "agent", "task": "Identify key aspects"},
    {"id": "branch_a", "type": "agent", "task": "Analyze technical aspects"},
    {"id": "branch_b", "type": "agent", "task": "Analyze business aspects"},
    {"id": "merge", "type": "agent", "task": "Combine findings"}
  ],
  "edges": [
    {"source": "split", "target": "branch_a"},
    {"source": "split", "target": "branch_b"},
    {"source": "branch_a", "target": "merge"},
    {"source": "branch_b", "target": "merge"}
  ]
}
```

### Conditional Logic

```
[Evaluate] → {condition} ─┬─→ [Path A] (if positive)
                          └─→ [Path B] (if negative)
```

## Real-World Example: Content Creation Pipeline

### Use Case

Automated blog post creation from topic to published article.

### Flow Definition

```json
{
  "name": "Blog Post Creation Pipeline",
  "description": "End-to-end blog post generation",
  "nodes": [
    {
      "id": "research",
      "type": "agent",
      "agent_id": "researcher",
      "task": "Research topic: {input.topic}. Find latest trends, statistics, expert opinions.",
      "expected_output": "Comprehensive research report with sources"
    },
    {
      "id": "outline",
      "type": "agent",
      "agent_id": "writer",
      "task": "Create blog post outline based on research",
      "expected_output": "Structured outline with H2/H3 headings",
      "context": ["{research.output}"]
    },
    {
      "id": "draft",
      "type": "agent",
      "agent_id": "writer",
      "task": "Write full blog post following outline",
      "expected_output": "Complete blog post draft (800-1200 words)",
      "context": ["{research.output}", "{outline.output}"]
    },
    {
      "id": "seo_optimize",
      "type": "tool",
      "tool_id": "seo_analyzer",
      "inputs": {
        "content": "{draft.output}",
        "target_keyword": "{input.keyword}"
      }
    },
    {
      "id": "review",
      "type": "agent",
      "agent_id": "editor",
      "task": "Review and edit for grammar, clarity, engagement",
      "expected_output": "Polished final draft with suggested improvements",
      "context": ["{draft.output}", "{seo_optimize.output}"]
    },
    {
      "id": "human_approval",
      "type": "human_input",
      "prompt": "Review final blog post. Approve or request changes?",
      "options": ["approve", "request_changes"]
    },
    {
      "id": "publish",
      "type": "tool",
      "tool_id": "cms_publisher",
      "inputs": {
        "content": "{review.output}",
        "status": "draft"
      },
      "condition": "{human_approval.choice} == 'approve'"
    }
  ],
  "edges": [
    {"source": "research", "target": "outline"},
    {"source": "outline", "target": "draft"},
    {"source": "draft", "target": "seo_optimize"},
    {"source": "draft", "target": "review"},
    {"source": "seo_optimize", "target": "review"},
    {"source": "review", "target": "human_approval"},
    {"source": "human_approval", "target": "publish"}
  ]
}
```

### Execution

```bash
# Execute via API
curl -X POST http://localhost:8000/api/v1/flows/{flow_id}/execute \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "inputs": {
      "topic": "The Future of AI in Healthcare",
      "keyword": "AI healthcare"
    }
  }'

# Monitor via WebSocket
ws://localhost:8000/api/v1/ws/executions/{execution_id}
```

## Best Practices

### 1. Design for Modularity

Break complex tasks into smaller, reusable agents:

```
❌ Bad: Single "do everything" agent
✅ Good: Specialized agents (research, analyze, write, edit)
```

### 2. Clear Task Descriptions

```python
# ❌ Vague
task = "Do some analysis"

# ✅ Specific
task = """
Analyze the sales data for Q4 2024 and:
1. Identify top 5 performing products
2. Calculate growth rate vs Q3
3. Highlight concerning trends
4. Provide 3 actionable recommendations
"""
```

### 3. Error Handling

Configure retry policies and timeouts:

```json
{
  "retry_policy": {
    "max_retries": 3,
    "backoff": "exponential",
    "retry_on": ["llm_error", "timeout"]
  },
  "timeout": 600,
  "fallback_llm_provider": "secondary_provider"
}
```

### 4. Testing

Test flows incrementally:

```bash
# Test individual nodes first
pytest tests/test_flow_nodes.py

# Test full flow with mock data
pytest tests/test_document_analysis_flow.py

# Load test with realistic data
locust -f tests/load/flow_execution.py
```

## Monitoring Execution

### Real-Time Status

```typescript
// Subscribe to execution updates
const ws = new WebSocket(`ws://api/ws/executions/${executionId}`);

ws.onmessage = (event) => {
  const update = JSON.parse(event.data);
  console.log(`Node ${update.node_id}: ${update.status}`);

  if (update.status === 'completed') {
    console.log(`Output: ${update.output}`);
  }
};
```

### Execution Logs

```bash
# Get detailed logs
curl http://localhost:8000/api/v1/executions/{execution_id}/logs

# View in MongoDB
mongosh
db.execution_logs_{tenant_id}.find({
  execution_id: "abc-123"
}).sort({timestamp: -1})
```

## Troubleshooting

### Flow Won't Execute

**Issue:** "Invalid DAG: cycle detected"

**Solution:** Remove circular dependencies. Use topological sort visualization.

### Timeout Errors

**Issue:** "Execution timeout after 600s"

**Solution:**
- Increase timeout in flow config
- Break into smaller sub-flows
- Optimize agent prompts

### LLM Errors

**Issue:** "Rate limit exceeded"

**Solution:**
- Configure LLM provider failover
- Add retry logic with backoff
- Implement caching for repeated prompts

## Next Steps

- [Add Custom Tools](./adding-tools.md)
- [Deploy to Production](./deploying-k8s.md)
- [Review Architecture](../architecture/system-overview.md)
