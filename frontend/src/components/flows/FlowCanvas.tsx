'use client';

import { useCallback, useEffect, DragEvent, useRef, KeyboardEvent } from 'react';
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
  EdgeTypes,
  getBezierPath,
  EdgeProps,
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

// Custom edge with delete button
function DeletableEdge({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  style = {},
  markerEnd,
  data,
}: EdgeProps) {
  const [edgePath, labelX, labelY] = getBezierPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
  });

  return (
    <>
      <path
        id={id}
        style={style}
        className="react-flow__edge-path"
        d={edgePath}
        markerEnd={markerEnd}
      />
      <foreignObject
        width={20}
        height={20}
        x={labelX - 10}
        y={labelY - 10}
        className="edgebutton-foreignobject"
        requiredExtensions="http://www.w3.org/1999/xhtml"
      >
        <div className="flex items-center justify-center w-full h-full">
          <button
            className="w-5 h-5 bg-red-500 text-white rounded-full text-xs font-bold hover:bg-red-600 flex items-center justify-center shadow-md cursor-pointer border border-white"
            onClick={(event) => {
              event.stopPropagation();
              data?.onDelete?.(id);
            }}
            title="Delete connection"
          >
            ×
          </button>
        </div>
      </foreignObject>
    </>
  );
}

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

// Register custom edge types
const edgeTypes: EdgeTypes = {
  default: DeletableEdge,
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
    return flowNodes.map((node) => {
      // If a node has a persisted width in its data, apply it to the React Flow node style
      const widthFromData = (node as any)?.data?.width as number | undefined;
      const style = widthFromData ? { width: widthFromData } : undefined;

      // Inject ephemeral UI flags without persisting them back
      const dataWithUi = { ...(node.data as any), __ui: { readOnly } };

      return {
        id: node.id,
        type: node.type,
        position: node.position,
        data: dataWithUi,
        ...(style ? { style } : {}),
      } as Node;
    });
  }, [readOnly]);

  // Convert API FlowEdge to ReactFlow Edge (without delete handler initially)
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

  // Delete edge handler (defined after setEdges)
  const handleDeleteEdge = useCallback(
    (edgeId: string) => {
      setEdges((eds) => eds.filter((e) => e.id !== edgeId));
    },
    [setEdges]
  );

  // Load flow data when flowId changes (only once on mount or flowId change)
  useEffect(() => {
    if (currentFlow && currentFlow.nodes) {
      setNodes(convertToReactFlowNodes(currentFlow.nodes));
      // Add delete handler to edges when loading
      const edgesWithHandlers = convertToReactFlowEdges(currentFlow.edges || []).map((edge) => ({
        ...edge,
        data: { ...edge.data, onDelete: handleDeleteEdge },
      }));
      setEdges(edgesWithHandlers);
    }
  }, [convertToReactFlowEdges, convertToReactFlowNodes, currentFlow, handleDeleteEdge, setEdges, setNodes]);

  // Handle keyboard events (Delete/Backspace key)
  useEffect(() => {
    const handleKeyDown = (event: globalThis.KeyboardEvent) => {
      if (readOnly) return;

      if (event.key === 'Delete' || event.key === 'Backspace') {
        const hasSelectedEdges = edges.some((e) => e.selected);
        const hasSelectedNodes = nodes.some((n) => n.selected);
        if (hasSelectedEdges || hasSelectedNodes) {
          event.preventDefault();
        }
        if (hasSelectedEdges) {
          setEdges((eds) => eds.filter((edge) => !edge.selected));
        }
        if (hasSelectedNodes) {
          const selectedNodeIds = new Set(nodes.filter((n) => n.selected).map((n) => n.id));
          setNodes((nds) => nds.filter((n) => !n.selected));
          // also remove edges connected to deleted nodes
          setEdges((eds) => eds.filter((e) => !selectedNodeIds.has(e.source) && !selectedNodeIds.has(e.target)));
          // clear selection in parent UI
          onNodeSelect?.(null);
        }
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [edges, nodes, readOnly, setEdges, setNodes, onNodeSelect]);

  // Sync nodes/edges changes back to store (with debounce to avoid loops)
  useEffect(() => {
    if (!currentFlow || readOnly) return;

    const timeoutId = setTimeout(() => {
      const flowNodes: FlowNode[] = nodes.map((node) => {
        // capture measured or styled width so it persists in node.data
        const measuredWidth = (node as any).width as number | undefined;
        const styledWidth = (node.style as any)?.width as number | undefined;
        const width = measuredWidth ?? styledWidth;
        const nextData: any = { ...(node.data as any) };
        // strip ephemeral ui flags
        if (nextData && nextData.__ui) {
          delete nextData.__ui;
        }
        if (width) nextData.width = width;

        return {
          id: node.id,
          type: node.type as FlowNode['type'],
          position: node.position,
          data: nextData,
        } as FlowNode;
      });

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

  // Validate connection
  const isValidConnection = useCallback(
    (connection: Connection) => {
      if (!connection.source || !connection.target) return false;

      // Find source and target nodes
      const sourceNode = nodes.find((n) => n.id === connection.source);
      const targetNode = nodes.find((n) => n.id === connection.target);

      if (!sourceNode || !targetNode) return false;

      // Validation rules:
      // 1. Input nodes can only be sources (already enforced by handles)
      // 2. Output nodes can only be targets (already enforced by handles)
      // 3. Prevent cycles (optional - for now we allow them)
      // 4. Input nodes cannot connect to output nodes directly
      if (sourceNode.type === 'input' && targetNode.type === 'output') {
        return false; // Input cannot connect directly to output
      }

      return true;
    },
    [nodes]
  );

  // Handle new connections
  const onConnect: OnConnect = useCallback(
    (connection: Connection) => {
      if (readOnly) return;

      if (!isValidConnection(connection)) {
        alert('Invalid connection: Input nodes cannot connect directly to Output nodes.');
        return;
      }

      setEdges((eds) =>
        addEdge({ ...connection, data: { onDelete: handleDeleteEdge } }, eds)
      );
    },
    [readOnly, isValidConnection, setEdges, handleDeleteEdge]
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
          // persist a larger default width in data so it survives store reloads
          width: 300,
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

      // default widths for consistency across node types
      const defaultWidth = type === 'input' ? 300 : 260;
      defaultData = { ...defaultData, width: defaultWidth };

      const newNode: Node = {
        id: `node_${nodeIdCounter.current++}`,
        type,
        position,
        data: defaultData,
        // Provide default width and persist in data
        style: { width: defaultWidth },
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
        edgeTypes={edgeTypes}
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
        deleteKeyCode={null}
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
