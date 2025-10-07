'use client';

import { useCallback, useEffect, DragEvent, useRef } from 'react';
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  Node,
  Edge,
  Connection,
  addEdge,
  useNodesState,
  useEdgesState,
  OnConnect,
  OnNodesChange,
  OnEdgesChange,
  useReactFlow,
  ReactFlowProvider,
  NodeTypes,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { useFlowStore } from '@/lib/store';
import type { FlowNode, FlowEdge } from '@/types/api';

// Import custom node components
import AgentNode from './nodes/AgentNode';
import ToolNode from './nodes/ToolNode';
import LLMNode from './nodes/LLMNode';
import ConditionNode from './nodes/ConditionNode';
import InputNode from './nodes/InputNode';
import OutputNode from './nodes/OutputNode';

// Register custom node types
const nodeTypes: NodeTypes = {
  agent: AgentNode,
  tool: ToolNode,
  llm: LLMNode,
  condition: ConditionNode,
  crew: AgentNode, // Reuse AgentNode for crew
  input: InputNode,
  output: OutputNode,
  decision: ConditionNode, // Reuse ConditionNode for decision
};

interface FlowCanvasProps {
  flowId?: number;
  readOnly?: boolean;
  onNodeSelect?: (node: Node | null) => void;
}

function FlowCanvasInner({ flowId, readOnly = false, onNodeSelect }: FlowCanvasProps) {
  const { currentFlow, updateFlow } = useFlowStore();
  const reactFlowWrapper = useRef<HTMLDivElement>(null);
  const { screenToFlowPosition } = useReactFlow();
  const nodeIdCounter = useRef(1);

  // Convert API FlowNode to ReactFlow Node
  const convertToReactFlowNodes = useCallback((flowNodes: FlowNode[]): Node[] => {
    return flowNodes.map((node) => ({
      id: node.id,
      type: node.type,
      position: node.position,
      data: node.data,
    }));
  }, []);

  // Convert API FlowEdge to ReactFlow Edge
  const convertToReactFlowEdges = useCallback((flowEdges: FlowEdge[]): Edge[] => {
    return flowEdges.map((edge) => ({
      id: edge.id,
      source: edge.source,
      target: edge.target,
      type: edge.type || 'default',
      data: edge.data,
    }));
  }, []);

  const [nodes, setNodes, onNodesChange] = useNodesState(
    currentFlow ? convertToReactFlowNodes(currentFlow.nodes) : []
  );
  const [edges, setEdges, onEdgesChange] = useEdgesState(
    currentFlow ? convertToReactFlowEdges(currentFlow.edges || []) : []
  );

  // Load flow data when flowId changes (only once on mount or flowId change)
  useEffect(() => {
    if (currentFlow && currentFlow.nodes) {
      setNodes(convertToReactFlowNodes(currentFlow.nodes));
      setEdges(convertToReactFlowEdges(currentFlow.edges || []));
    }
  }, [convertToReactFlowEdges, convertToReactFlowNodes, currentFlow, setEdges, setNodes]);

  // Sync nodes/edges changes back to store (with debounce to avoid loops)
  useEffect(() => {
    if (!currentFlow || readOnly) return;

    const timeoutId = setTimeout(() => {
      const flowNodes: FlowNode[] = nodes.map((node) => ({
        id: node.id,
        type: node.type as FlowNode['type'],
        position: node.position,
        data: node.data,
      }));

      const flowEdges: FlowEdge[] = edges.map((edge) => ({
        id: edge.id,
        source: edge.source,
        target: edge.target,
        type: edge.type as FlowEdge['type'],
        data: edge.data,
      }));

      // Only update if there are actual changes
      const nodesChanged = JSON.stringify(flowNodes) !== JSON.stringify(currentFlow.nodes);
      const edgesChanged = JSON.stringify(flowEdges) !== JSON.stringify(currentFlow.edges);

      if (nodesChanged || edgesChanged) {
        updateFlow(currentFlow.id, { nodes: flowNodes, edges: flowEdges });
      }
    }, 300); // 300ms debounce

    return () => clearTimeout(timeoutId);
  }, [currentFlow, edges, nodes, readOnly, updateFlow]);

  // Handle new connections
  const onConnect: OnConnect = useCallback(
    (connection: Connection) => {
      if (readOnly) return;
      setEdges((eds) => addEdge(connection, eds));
    },
    [readOnly, setEdges]
  );

  const handleNodesChange: OnNodesChange = useCallback(
    (changes) => {
      if (!readOnly) {
        onNodesChange(changes);
      }
    },
    [readOnly, onNodesChange]
  );

  const handleEdgesChange: OnEdgesChange = useCallback(
    (changes) => {
      if (!readOnly) {
        onEdgesChange(changes);
      }
    },
    [readOnly, onEdgesChange]
  );

  // Handle drag over to allow drop
  const onDragOver = useCallback((event: DragEvent) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }, []);

  // Handle drop to create new node
  const onDrop = useCallback(
    (event: DragEvent) => {
      event.preventDefault();

      if (readOnly) return;

      const type = event.dataTransfer.getData('application/reactflow');
      if (!type) return;

      const position = screenToFlowPosition({
        x: event.clientX,
        y: event.clientY,
      });

      // Create default data based on node type
      let defaultData: any = {
        label: `${type.charAt(0).toUpperCase() + type.slice(1)} Node`,
      };

      // Special defaults for input/output nodes
      if (type === 'input') {
        defaultData = {
          label: 'Flow Input',
          description: 'Define input variables for this flow',
          inputs: [
            { name: 'input_1', type: 'string', required: true },
          ],
        };
      } else if (type === 'output') {
        defaultData = {
          label: 'Flow Output',
          description: 'Define output variables from this flow',
          outputs: [
            { name: 'result', type: 'string' },
          ],
        };
      }

      const newNode: Node = {
        id: `node_${nodeIdCounter.current++}`,
        type,
        position,
        data: defaultData,
      };

      setNodes((nds) => nds.concat(newNode));

      // Auto-select the new node
      onNodeSelect?.(newNode);
    },
    [readOnly, screenToFlowPosition, setNodes, onNodeSelect]
  );

  // Handle node click
  const onNodeClick = useCallback(
    (event: React.MouseEvent, node: Node) => {
      if (!readOnly) {
        onNodeSelect?.(node);
      }
    },
    [readOnly, onNodeSelect]
  );

  // Handle pane click (deselect)
  const onPaneClick = useCallback(() => {
    onNodeSelect?.(null);
  }, [onNodeSelect]);

  return (
    <div ref={reactFlowWrapper} className="w-full h-full">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        onNodesChange={handleNodesChange}
        onEdgesChange={handleEdgesChange}
        onConnect={onConnect}
        onDrop={onDrop}
        onDragOver={onDragOver}
        onNodeClick={onNodeClick}
        onPaneClick={onPaneClick}
        fitView
        nodesDraggable={!readOnly}
        nodesConnectable={!readOnly}
        elementsSelectable={!readOnly}
      >
        <Background />
        <Controls />
        <MiniMap />
      </ReactFlow>
    </div>
  );
}

// Wrap with ReactFlowProvider to enable useReactFlow hook
export default function FlowCanvas(props: FlowCanvasProps) {
  return (
    <ReactFlowProvider>
      <FlowCanvasInner {...props} />
    </ReactFlowProvider>
  );
}
