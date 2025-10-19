'use client';

import { apiClient } from '@/lib/api-client';

/**
 * Execution API Service
 *
 * Provides API methods for execution management.
 * Includes both existing and new worker-architecture endpoints.
 */

export interface QueueExecutionRequest {
  execution_type: 'crew' | 'flow' | 'task';
  entity_id: string;
  input_params?: Record<string, any>;
  priority?: number; // 0-10, lower = higher priority
  timeout_seconds?: number;
  max_retries?: number;
}

export interface QueueExecutionResponse {
  job_id: string;
  status: string;
  queue_position: number;
  estimated_start_seconds: number | null;
}

export interface ExecutionStatusResponse {
  id: string;
  status: 'pending' | 'queued' | 'running' | 'completed' | 'failed' | 'cancelled';
  queue_position: number | null;
  estimated_start_seconds: number | null;
  worker_id: string | null;
  retry_count: number;
  max_retries: number;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  error_message: string | null;
}

export interface CancelExecutionResponse {
  id: string;
  status: string;
  cancellation_requested: boolean;
  cancelled_at: string;
}

export interface ReExecuteResponse {
  new_job_id: string;
  parent_execution_id: string;
  artifact_version: number;
}

export interface ExecutionArtifact {
  id: string;
  execution_id: string;
  file_name: string;
  file_size: number;
  mime_type: string;
  artifact_type: 'output' | 'log' | 'report' | 'data';
  version_number: number;
  created_at: string;
  expires_at: string;
}

export interface ArtifactsListResponse {
  artifacts: ExecutionArtifact[];
  total: number;
}

export interface ArtifactDownloadResponse {
  artifact_id: string;
  presigned_url: string;
  expires_in_seconds: number;
}

/**
 * Queue a new execution (worker architecture)
 * POST /api/v1/executions/queue
 */
export async function queueExecution(request: QueueExecutionRequest): Promise<QueueExecutionResponse> {
  const response = await apiClient.post('/api/v1/executions/queue', request);
  return response.data;
}

/**
 * Get execution status with queue information
 * GET /api/v1/executions/{id}/status
 */
export async function getExecutionStatus(executionId: string): Promise<ExecutionStatusResponse> {
  const response = await apiClient.get(`/api/v1/executions/${executionId}/status`);
  return response.data;
}

/**
 * Cancel a running or queued execution
 * POST /api/v1/executions/{id}/cancel
 */
export async function cancelExecution(executionId: string): Promise<CancelExecutionResponse> {
  const response = await apiClient.post(`/api/v1/executions/${executionId}/cancel`);
  return response.data;
}

/**
 * Re-execute a completed execution with incremented version
 * POST /api/v1/executions/{id}/re-execute
 */
export async function reExecute(executionId: string): Promise<ReExecuteResponse> {
  const response = await apiClient.post(`/api/v1/executions/${executionId}/re-execute`);
  return response.data;
}

/**
 * Get list of artifacts for an execution
 * GET /api/v1/executions/{id}/artifacts
 */
export async function getExecutionArtifacts(executionId: string): Promise<ArtifactsListResponse> {
  const response = await apiClient.get(`/api/v1/executions/${executionId}/artifacts`);
  return response.data;
}

/**
 * Get presigned download URL for an artifact
 * GET /api/v1/artifacts/{id}/download
 */
export async function getArtifactDownloadUrl(artifactId: string): Promise<ArtifactDownloadResponse> {
  const response = await apiClient.get(`/api/v1/artifacts/${artifactId}/download`);
  return response.data;
}

/**
 * Download artifact directly (opens in new tab)
 */
export async function downloadArtifact(artifactId: string): Promise<void> {
  const { presigned_url } = await getArtifactDownloadUrl(artifactId);

  // Open in new tab
  if (typeof window !== 'undefined') {
    window.open(presigned_url, '_blank');
  }
}

// Export all functions as a service object
export const executionApi = {
  queueExecution,
  getExecutionStatus,
  cancelExecution,
  reExecute,
  getExecutionArtifacts,
  getArtifactDownloadUrl,
  downloadArtifact
};
