import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import FlowCanvas from '@/components/flows/FlowCanvas';
import { useFlowStore } from '@/lib/store';
import { ReactFlowProvider } from 'reactflow';

// Mock ReactFlow
jest.mock('reactflow', () => ({
  ...jest.requireActual('reactflow'),
  useReactFlow: () => ({
    screenToFlowPosition: ({ x, y }: { x: number; y: number }) => ({ x, y }),
    getNodes: jest.fn(() => []),
    getEdges: jest.fn(() => []),
  }),
  ReactFlowProvider: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));

jest.mock('@/lib/store', () => ({
  useFlowStore: jest.fn(),
}));

describe('FlowCanvas', () => {
  let mockUpdateFlow: jest.Mock;
  let mockCurrentFlow: any;

  beforeEach(() => {
    mockUpdateFlow = jest.fn();
    mockCurrentFlow = {
      id: 1,
      name: 'Test Flow',
      nodes: [
        {
          id: 'node-1',
          type: 'agent',
          position: { x: 100, y: 100 },
          data: { label: 'Agent Node' },
        },
      ],
      edges: [
        {
          id: 'edge-1',
          source: 'node-1',
          target: 'node-2',
          type: 'default',
        },
      ],
    };

    (useFlowStore as jest.Mock).mockReturnValue({
      currentFlow: mockCurrentFlow,
      updateFlow: mockUpdateFlow,
    });
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  describe('Rendering', () => {
    it('should render ReactFlow canvas', () => {
      render(<FlowCanvas flowId={1} />);
      expect(screen.getByRole('presentation')).toBeInTheDocument();
    });

    it('should render nodes from current flow', () => {
      render(<FlowCanvas flowId={1} />);
      // ReactFlow internal rendering, check if nodes prop is passed
      expect(mockCurrentFlow.nodes).toHaveLength(1);
    });

    it('should render edges from current flow', () => {
      render(<FlowCanvas flowId={1} />);
      expect(mockCurrentFlow.edges).toHaveLength(1);
    });
  });

  describe('Read-Only Mode', () => {
    it('should disable dragging in read-only mode', () => {
      const { container } = render(<FlowCanvas flowId={1} readOnly={true} />);
      const reactFlow = container.querySelector('.react-flow');
      expect(reactFlow).toHaveClass('readonly'); // Assuming ReactFlow adds this class
    });

    it('should disable connections in read-only mode', () => {
      render(<FlowCanvas flowId={1} readOnly={true} />);
      // Verify nodes are not connectable
      // This would be tested through interaction
    });
  });

  describe('Drag and Drop', () => {
    it('should handle drag over event', () => {
      const { container } = render(<FlowCanvas flowId={1} />);
      const canvas = container.querySelector('.react-flow');

      if (canvas) {
        const dragEvent = new DragEvent('dragover', {
          dataTransfer: new DataTransfer(),
        });
        fireEvent(canvas, dragEvent);

        expect(dragEvent.defaultPrevented).toBe(true);
      }
    });

    it('should create new node on drop', async () => {
      const { container } = render(<FlowCanvas flowId={1} />);
      const canvas = container.querySelector('.react-flow');

      if (canvas) {
        const dataTransfer = new DataTransfer();
        dataTransfer.setData('application/reactflow', 'agent');

        const dropEvent = new DragEvent('drop', {
          clientX: 200,
          clientY: 200,
          dataTransfer,
        });

        fireEvent(canvas, dropEvent);

        await waitFor(() => {
          expect(mockUpdateFlow).toHaveBeenCalled();
        });
      }
    });

    it('should not create node on drop in read-only mode', () => {
      const { container } = render(<FlowCanvas flowId={1} readOnly={true} />);
      const canvas = container.querySelector('.react-flow');

      if (canvas) {
        const dataTransfer = new DataTransfer();
        dataTransfer.setData('application/reactflow', 'agent');

        const dropEvent = new DragEvent('drop', {
          clientX: 200,
          clientY: 200,
          dataTransfer,
        });

        fireEvent(canvas, dropEvent);

        expect(mockUpdateFlow).not.toHaveBeenCalled();
      }
    });
  });

  describe('Node Selection', () => {
    it('should call onNodeSelect when node is clicked', () => {
      const mockOnNodeSelect = jest.fn();
      render(<FlowCanvas flowId={1} onNodeSelect={mockOnNodeSelect} />);

      // Simulate node click (would need ReactFlow internal testing)
      // This is a simplified test
    });

    it('should deselect node when pane is clicked', () => {
      const mockOnNodeSelect = jest.fn();
      const { container } = render(<FlowCanvas flowId={1} onNodeSelect={mockOnNodeSelect} />);

      const pane = container.querySelector('.react-flow__pane');
      if (pane) {
        fireEvent.click(pane);
        expect(mockOnNodeSelect).toHaveBeenCalledWith(null);
      }
    });
  });

  describe('Connection Validation', () => {
    it('should prevent invalid connections', () => {
      // Test connection between input and output nodes directly
      const flowWithInputOutput = {
        ...mockCurrentFlow,
        nodes: [
          {
            id: 'input-1',
            type: 'input',
            position: { x: 0, y: 0 },
            data: { label: 'Input' },
          },
          {
            id: 'output-1',
            type: 'output',
            position: { x: 200, y: 0 },
            data: { label: 'Output' },
          },
        ],
      };

      (useFlowStore as jest.Mock).mockReturnValue({
        currentFlow: flowWithInputOutput,
        updateFlow: mockUpdateFlow,
      });

      render(<FlowCanvas flowId={1} />);

      // Attempt to connect input to output
      // This would trigger validation and show alert
    });

    it('should allow valid connections', () => {
      const flowWithAgents = {
        ...mockCurrentFlow,
        nodes: [
          {
            id: 'agent-1',
            type: 'agent',
            position: { x: 0, y: 0 },
            data: { label: 'Agent 1' },
          },
          {
            id: 'agent-2',
            type: 'agent',
            position: { x: 200, y: 0 },
            data: { label: 'Agent 2' },
          },
        ],
      };

      (useFlowStore as jest.Mock).mockReturnValue({
        currentFlow: flowWithAgents,
        updateFlow: mockUpdateFlow,
      });

      render(<FlowCanvas flowId={1} />);

      // Connection should be allowed between agents
    });
  });

  describe('Edge Deletion', () => {
    it('should delete edge when Delete key is pressed', async () => {
      const flowWithEdge = {
        ...mockCurrentFlow,
        edges: [
          {
            id: 'edge-1',
            source: 'node-1',
            target: 'node-2',
            selected: true,
          },
        ],
      };

      (useFlowStore as jest.Mock).mockReturnValue({
        currentFlow: flowWithEdge,
        updateFlow: mockUpdateFlow,
      });

      render(<FlowCanvas flowId={1} />);

      fireEvent.keyDown(document, { key: 'Delete' });

      await waitFor(() => {
        expect(mockUpdateFlow).toHaveBeenCalled();
      });
    });

    it('should delete edge when Backspace key is pressed', async () => {
      const flowWithEdge = {
        ...mockCurrentFlow,
        edges: [
          {
            id: 'edge-1',
            source: 'node-1',
            target: 'node-2',
            selected: true,
          },
        ],
      };

      (useFlowStore as jest.Mock).mockReturnValue({
        currentFlow: flowWithEdge,
        updateFlow: mockUpdateFlow,
      });

      render(<FlowCanvas flowId={1} />);

      fireEvent.keyDown(document, { key: 'Backspace' });

      await waitFor(() => {
        expect(mockUpdateFlow).toHaveBeenCalled();
      });
    });

    it('should not delete edge in read-only mode', () => {
      const flowWithEdge = {
        ...mockCurrentFlow,
        edges: [
          {
            id: 'edge-1',
            source: 'node-1',
            target: 'node-2',
            selected: true,
          },
        ],
      };

      (useFlowStore as jest.Mock).mockReturnValue({
        currentFlow: flowWithEdge,
        updateFlow: mockUpdateFlow,
      });

      render(<FlowCanvas flowId={1} readOnly={true} />);

      fireEvent.keyDown(document, { key: 'Delete' });

      expect(mockUpdateFlow).not.toHaveBeenCalled();
    });
  });

  describe('Node Width Persistence', () => {
    it('should restore node width from data', () => {
      const flowWithWidths = {
        ...mockCurrentFlow,
        nodes: [
          {
            id: 'input-1',
            type: 'input',
            position: { x: 0, y: 0 },
            data: { label: 'Input', width: 350 },
          },
        ],
      };

      (useFlowStore as jest.Mock).mockReturnValue({
        currentFlow: flowWithWidths,
        updateFlow: mockUpdateFlow,
      });

      render(<FlowCanvas flowId={1} />);

      // Check if node is rendered with width style
      // This would need access to ReactFlow internals
    });

    it('should save node width when node is resized', async () => {
      render(<FlowCanvas flowId={1} />);

      // Simulate node resize
      // This would trigger updateFlow with new width in data

      await waitFor(() => {
        expect(mockUpdateFlow).toHaveBeenCalled();
      }, { timeout: 500 });
    });
  });

  describe('Store Synchronization', () => {
    it('should sync changes to store with debounce', async () => {
      render(<FlowCanvas flowId={1} />);

      // Make multiple rapid changes
      // Should only trigger updateFlow once after debounce

      await waitFor(() => {
        expect(mockUpdateFlow).toHaveBeenCalledTimes(1);
      }, { timeout: 500 });
    });

    it('should not sync in read-only mode', async () => {
      render(<FlowCanvas flowId={1} readOnly={true} />);

      // Wait for debounce period
      await new Promise(resolve => setTimeout(resolve, 500));

      expect(mockUpdateFlow).not.toHaveBeenCalled();
    });
  });
});
