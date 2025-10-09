// Must match backend enum values in backend/src/models/task.py
export type TaskOutputFormat = 'text' | 'json' | 'pydantic';

export interface Task {
  id: number;
  name: string;
  description: string;
  expected_output: string;
  agent_id?: number;
  crew_id?: number;
  order: number;
  async_execution: boolean;
  output_format: TaskOutputFormat;
  output_file?: string;
  context?: string;
  tools_config?: string;
  created_at: string;
  updated_at: string;
}

export interface TaskCreate {
  name: string;
  description: string;
  expected_output: string;
  agent_id?: number;
  crew_id?: number;
  order?: number;
  async_execution?: boolean;
  output_format?: TaskOutputFormat;
  output_file?: string;
  context?: string;
  tools_config?: string;
}

export interface TaskUpdate {
  name?: string;
  description?: string;
  expected_output?: string;
  agent_id?: number;
  crew_id?: number;
  order?: number;
  async_execution?: boolean;
  output_format?: TaskOutputFormat;
  output_file?: string;
  context?: string;
  tools_config?: string;
}
