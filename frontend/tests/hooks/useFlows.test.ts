import { renderHook, waitFor } from '@testing-library/react';
import { useFlows } from '@/lib/hooks/useFlows';
import { apiClient } from '@/lib/api-client';

jest.mock('@/lib/api-client');

describe('useFlows', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('fetchFlows', () => {
    it('should fetch flows successfully', async () => {
      const mockFlows = [
        { id: 1, name: 'Flow 1', description: 'Test flow 1' },
        { id: 2, name: 'Flow 2', description: 'Test flow 2' },
      ];

      (apiClient.get as jest.Mock).mockResolvedValue({ data: mockFlows });

      const { result } = renderHook(() => useFlows());

      await waitFor(() => {
        expect(result.current.flows).toEqual(mockFlows);
        expect(result.current.loading).toBe(false);
      });
    });

    it('should handle fetch error', async () => {
      const mockError = new Error('Network error');
      (apiClient.get as jest.Mock).mockRejectedValue(mockError);

      const { result } = renderHook(() => useFlows());

      await waitFor(() => {
        expect(result.current.error).toBe(mockError.message);
        expect(result.current.loading).toBe(false);
      });
    });

    it('should set loading state while fetching', async () => {
      (apiClient.get as jest.Mock).mockImplementation(
        () => new Promise(resolve => setTimeout(() => resolve({ data: [] }), 100))
      );

      const { result } = renderHook(() => useFlows());

      expect(result.current.loading).toBe(true);

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });
    });
  });

  describe('createFlow', () => {
    it('should create flow successfully', async () => {
      const newFlow = {
        name: 'New Flow',
        description: 'Test description',
        variables: {},
      };

      const createdFlow = {
        id: 123,
        ...newFlow,
        nodes: [],
        edges: [],
      };

      (apiClient.post as jest.Mock).mockResolvedValue({ data: createdFlow });

      const { result } = renderHook(() => useFlows());

      const flow = await result.current.createFlow(newFlow);

      expect(flow).toEqual(createdFlow);
      expect(apiClient.post).toHaveBeenCalledWith('/api/v1/flows', newFlow);
    });

    it('should throw error on create failure', async () => {
      const mockError = new Error('Create failed');
      (apiClient.post as jest.Mock).mockRejectedValue(mockError);

      const { result } = renderHook(() => useFlows());

      await expect(
        result.current.createFlow({ name: 'Test' })
      ).rejects.toThrow('Create failed');
    });

    it('should add created flow to flows list', async () => {
      const existingFlows = [
        { id: 1, name: 'Existing Flow' },
      ];

      const newFlow = {
        id: 2,
        name: 'New Flow',
        nodes: [],
        edges: [],
      };

      (apiClient.get as jest.Mock).mockResolvedValue({ data: existingFlows });
      (apiClient.post as jest.Mock).mockResolvedValue({ data: newFlow });

      const { result } = renderHook(() => useFlows());

      await waitFor(() => {
        expect(result.current.flows).toHaveLength(1);
      });

      await result.current.createFlow({ name: 'New Flow' });

      await waitFor(() => {
        expect(result.current.flows).toHaveLength(2);
        expect(result.current.flows).toContainEqual(newFlow);
      });
    });
  });

  describe('updateFlow', () => {
    it('should update flow successfully', async () => {
      const updatedFlow = {
        id: 1,
        name: 'Updated Flow',
        description: 'Updated description',
      };

      (apiClient.put as jest.Mock).mockResolvedValue({ data: updatedFlow });

      const { result } = renderHook(() => useFlows());

      const flow = await result.current.updateFlow(1, {
        name: 'Updated Flow',
        description: 'Updated description',
      });

      expect(flow).toEqual(updatedFlow);
      expect(apiClient.put).toHaveBeenCalledWith('/api/v1/flows/1', {
        name: 'Updated Flow',
        description: 'Updated description',
      });
    });

    it('should update flow in flows list', async () => {
      const existingFlows = [
        { id: 1, name: 'Original Flow' },
        { id: 2, name: 'Other Flow' },
      ];

      const updatedFlow = {
        id: 1,
        name: 'Updated Flow',
      };

      (apiClient.get as jest.Mock).mockResolvedValue({ data: existingFlows });
      (apiClient.put as jest.Mock).mockResolvedValue({ data: updatedFlow });

      const { result } = renderHook(() => useFlows());

      await waitFor(() => {
        expect(result.current.flows).toHaveLength(2);
      });

      await result.current.updateFlow(1, { name: 'Updated Flow' });

      await waitFor(() => {
        const flow = result.current.flows.find(f => f.id === 1);
        expect(flow?.name).toBe('Updated Flow');
      });
    });
  });

  describe('deleteFlow', () => {
    it('should delete flow successfully', async () => {
      (apiClient.delete as jest.Mock).mockResolvedValue({});

      const { result } = renderHook(() => useFlows());

      await result.current.deleteFlow(1);

      expect(apiClient.delete).toHaveBeenCalledWith('/api/v1/flows/1');
    });

    it('should remove flow from flows list', async () => {
      const existingFlows = [
        { id: 1, name: 'Flow to Delete' },
        { id: 2, name: 'Flow to Keep' },
      ];

      (apiClient.get as jest.Mock).mockResolvedValue({ data: existingFlows });
      (apiClient.delete as jest.Mock).mockResolvedValue({});

      const { result } = renderHook(() => useFlows());

      await waitFor(() => {
        expect(result.current.flows).toHaveLength(2);
      });

      await result.current.deleteFlow(1);

      await waitFor(() => {
        expect(result.current.flows).toHaveLength(1);
        expect(result.current.flows[0].id).toBe(2);
      });
    });

    it('should throw error on delete failure', async () => {
      const mockError = new Error('Delete failed');
      (apiClient.delete as jest.Mock).mockRejectedValue(mockError);

      const { result } = renderHook(() => useFlows());

      await expect(result.current.deleteFlow(1)).rejects.toThrow('Delete failed');
    });
  });

  describe('executeFlow', () => {
    it('should execute flow with inputs', async () => {
      const executionResult = {
        execution_id: 'exec-123',
        status: 'running',
      };

      (apiClient.post as jest.Mock).mockResolvedValue({ data: executionResult });

      const { result } = renderHook(() => useFlows());

      const inputs = { input1: 'value1', input2: 'value2' };
      const execution = await result.current.executeFlow(1, inputs);

      expect(execution).toEqual(executionResult);
      expect(apiClient.post).toHaveBeenCalledWith('/api/v1/flows/1/execute', {
        inputs,
      });
    });

    it('should execute flow without inputs', async () => {
      const executionResult = {
        execution_id: 'exec-456',
        status: 'running',
      };

      (apiClient.post as jest.Mock).mockResolvedValue({ data: executionResult });

      const { result } = renderHook(() => useFlows());

      const execution = await result.current.executeFlow(1);

      expect(execution).toEqual(executionResult);
      expect(apiClient.post).toHaveBeenCalledWith('/api/v1/flows/1/execute', {
        inputs: {},
      });
    });

    it('should handle execution error', async () => {
      const mockError = new Error('Execution failed');
      (apiClient.post as jest.Mock).mockRejectedValue(mockError);

      const { result } = renderHook(() => useFlows());

      await expect(result.current.executeFlow(1)).rejects.toThrow('Execution failed');
    });
  });

  describe('getFlowById', () => {
    it('should fetch single flow by ID', async () => {
      const mockFlow = {
        id: 1,
        name: 'Test Flow',
        description: 'Test description',
        nodes: [],
        edges: [],
      };

      (apiClient.get as jest.Mock).mockResolvedValue({ data: mockFlow });

      const { result } = renderHook(() => useFlows());

      const flow = await result.current.getFlowById(1);

      expect(flow).toEqual(mockFlow);
      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/flows/1');
    });

    it('should throw error if flow not found', async () => {
      (apiClient.get as jest.Mock).mockRejectedValue(new Error('Not found'));

      const { result } = renderHook(() => useFlows());

      await expect(result.current.getFlowById(999)).rejects.toThrow('Not found');
    });
  });

  describe('Error State Management', () => {
    it('should clear error on successful operation', async () => {
      const mockError = new Error('Initial error');
      (apiClient.get as jest.Mock)
        .mockRejectedValueOnce(mockError)
        .mockResolvedValueOnce({ data: [] });

      const { result, rerender } = renderHook(() => useFlows());

      await waitFor(() => {
        expect(result.current.error).toBe(mockError.message);
      });

      // Retry
      rerender();

      await waitFor(() => {
        expect(result.current.error).toBeNull();
      });
    });
  });

  describe('Concurrent Operations', () => {
    it('should handle multiple simultaneous fetches', async () => {
      const mockFlows = [{ id: 1, name: 'Flow 1' }];
      (apiClient.get as jest.Mock).mockResolvedValue({ data: mockFlows });

      const { result } = renderHook(() => useFlows());

      // Trigger multiple fetches
      await Promise.all([
        result.current.fetchFlows(),
        result.current.fetchFlows(),
        result.current.fetchFlows(),
      ]);

      // Should handle gracefully without race conditions
      expect(result.current.flows).toEqual(mockFlows);
    });
  });
});
