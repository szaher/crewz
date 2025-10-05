'use client';

import { useCallback, useEffect } from 'react';
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
} from 'reactflow';
import 'reactflow/dist/style.css';
import { useFlowStore } from '@/lib/store';
import type { FlowNode, FlowEdge } from '@/types/api';

interface FlowCanvasProps {
  flowId?: number;
  readOnly?: boolean;
}

export default function FlowCanvas({ flowId, readOnly = false }: FlowCanvasProps) {
  const { currentFlow, updateFlow } = useFlowStore();

  // Convert API FlowNode to ReactFlow Node
  const convertToReactFlowNodes = (flowNodes: FlowNode[]): Node[] => {
    return flowNodes.map((node) => ({
      id: node.id,
      type: node.type,
      position: node.position,
      data: node.data,
    }));
  };

  // Convert API FlowEdge to ReactFlow Edge
  const convertToReactFlowEdges = (flowEdges: FlowEdge[]): Edge[] => {
    return flowEdges.map((edge) => ({
      id: edge.id,
      source: edge.source,
      target: edge.target,
      type: edge.type || 'default',
      data: edge.data,
    }));
  };

  const [nodes, setNodes, onNodesChange] = useNodesState(
    currentFlow ? convertToReactFlowNodes(currentFlow.nodes) : []
  );
  const [edges, setEdges, onEdgesChange] = useEdgesState(
    currentFlow ? convertToReactFlowEdges(currentFlow.edges) : []
  );

  // Load flow data when flowId changes
  useEffect(() => {
    if (currentFlow) {
      setNodes(convertToReactFlowNodes(currentFlow.nodes));
      setEdges(convertToReactFlowEdges(currentFlow.edges));
    }
  }, [currentFlow, setNodes, setEdges]);

  // Handle new connections
  const onConnect: OnConnect = useCallback(
    (connection: Connection) => {
      if (readOnly) return;
      setEdges((eds) => addEdge(connection, eds));
    },
    [readOnly, setEdges]
  );

  // Save changes to store when nodes/edges change
  useEffect(() => {
    if (currentFlow && !readOnly) {
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

      updateFlow(currentFlow.id, { nodes: flowNodes, edges: flowEdges });
    }
  }, [nodes, edges, currentFlow, readOnly, updateFlow]);

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

  return (
    <div className="w-full h-full">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={handleNodesChange}
        onEdgesChange={handleEdgesChange}
        onConnect={onConnect}
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
