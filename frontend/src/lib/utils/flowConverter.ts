import type { FlowNode, FlowEdge } from '@/types/api';

interface FlowStep {
  id: string;
  name: string;
  description: string;
  type: 'agent' | 'crew' | 'tool' | 'flow' | 'router';
  // Agent step
  agent_id?: string;
  task_description?: string;
  // Crew step
  crew_id?: string;
  // Tool step
  tool_id?: string;
  // Flow step (hierarchical)
  flow_id?: string;
  // Router step (conditional)
  condition?: string;
  router_paths?: Array<{ condition: string; next_step_id?: string }>;
  // Common
  config?: Record<string, any>;
}

/**
 * Convert sequential flow steps to nodes and edges format for backend
 * Supports CrewAI-compliant flow types: agent, crew, tool, flow (hierarchical), router (conditional)
 */
export function convertStepsToNodesAndEdges(steps: FlowStep[]): {
  nodes: FlowNode[];
  edges: FlowEdge[];
} {
  const nodes: FlowNode[] = [];
  const edges: FlowEdge[] = [];

  // Create nodes from steps
  steps.forEach((step, index) => {
    const baseNode = {
      id: step.id,
      position: {
        x: 100,
        y: 100 + (index * 150), // Auto-layout vertically
      },
    };

    let node: FlowNode;

    switch (step.type) {
      case 'agent':
        node = {
          ...baseNode,
          type: 'agent',
          data: {
            label: step.name,
            agent_id: step.agent_id,
            task_description: step.task_description,
            description: step.description,
            config: step.config || {},
          },
        };
        break;

      case 'crew':
        node = {
          ...baseNode,
          type: 'crew',
          data: {
            label: step.name,
            crew_id: step.crew_id,
            description: step.description,
            config: step.config || {},
          },
        };
        break;

      case 'tool':
        node = {
          ...baseNode,
          type: 'tool',
          data: {
            label: step.name,
            tool_id: step.tool_id,
            description: step.description,
            config: step.config || {},
          },
        };
        break;

      case 'flow':
        node = {
          ...baseNode,
          type: 'flow',
          data: {
            label: step.name,
            flow_id: step.flow_id,
            description: step.description,
            config: step.config || {},
          },
        };
        break;

      case 'router':
        node = {
          ...baseNode,
          type: 'router',
          data: {
            label: step.name,
            condition: step.condition,
            router_paths: step.router_paths || [],
            description: step.description,
            config: step.config || {},
          },
        };
        break;

      default:
        // Fallback for unknown types
        node = {
          ...baseNode,
          type: 'agent',
          data: {
            label: step.name,
            description: step.description,
            config: step.config || {},
          },
        };
    }

    nodes.push(node);
  });

  // Create edges connecting steps sequentially
  for (let i = 0; i < steps.length - 1; i++) {
    const edge: FlowEdge = {
      id: `edge-${steps[i].id}-${steps[i + 1].id}`,
      source: steps[i].id,
      target: steps[i + 1].id,
      type: 'default',
    };

    edges.push(edge);
  }

  return { nodes, edges };
}

/**
 * Convert nodes and edges back to sequential steps
 * Supports all CrewAI-compliant node types
 */
export function convertNodesToSteps(nodes: FlowNode[], edges: FlowEdge[]): FlowStep[] {
  if (nodes.length === 0) return [];

  // Build adjacency map for ordering
  const adjacencyMap = new Map<string, string>();
  edges.forEach(edge => {
    adjacencyMap.set(edge.source, edge.target);
  });

  // Find the first node (no incoming edges)
  const nodesWithIncoming = new Set(edges.map(e => e.target));
  let currentId = nodes.find(n => !nodesWithIncoming.has(n.id))?.id;

  if (!currentId) {
    // Fallback: if no clear start, use first node
    currentId = nodes[0].id;
  }

  const steps: FlowStep[] = [];
  const visited = new Set<string>();

  // Traverse the flow sequentially
  while (currentId && !visited.has(currentId)) {
    visited.add(currentId);

    const node = nodes.find(n => n.id === currentId);
    if (!node) break;

    // Determine step type from node
    let stepType: FlowStep['type'] = 'agent'; // default
    if (node.type === 'agent') stepType = 'agent';
    else if (node.type === 'crew') stepType = 'crew';
    else if (node.type === 'tool') stepType = 'tool';
    else if (node.type === 'flow') stepType = 'flow';
    else if (node.type === 'router') stepType = 'router';

    const step: FlowStep = {
      id: node.id,
      name: node.data.label || `Step ${steps.length + 1}`,
      description: node.data.description || '',
      type: stepType,
      // Agent fields
      agent_id: node.data.agent_id,
      task_description: node.data.task_description,
      // Crew fields
      crew_id: node.data.crew_id,
      // Tool fields
      tool_id: node.data.tool_id,
      // Flow fields
      flow_id: node.data.flow_id,
      // Router fields
      condition: node.data.condition,
      router_paths: node.data.router_paths,
      // Common
      config: node.data.config,
    };

    steps.push(step);

    // Move to next node
    currentId = adjacencyMap.get(currentId);
  }

  return steps;
}
