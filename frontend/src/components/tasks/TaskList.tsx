'use client';

import { Task } from '@/types/task';

interface TaskListProps {
  tasks: Task[];
  onEdit: (task: Task) => void;
  onDelete: (taskId: number) => void;
  agentNames?: Record<number, string>;
}

export default function TaskList({ tasks, onEdit, onDelete, agentNames = {} }: TaskListProps) {
  if (tasks.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        No tasks yet. Create your first task to get started.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {tasks.map((task) => (
        <div
          key={task.id}
          className="bg-white border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow"
        >
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <div className="flex items-center gap-3 mb-2">
                <h3 className="text-lg font-semibold text-gray-900">{task.name}</h3>
                <span className="px-2 py-1 text-xs font-medium rounded bg-blue-100 text-blue-800">
                  Order: {task.order}
                </span>
                {task.async_execution && (
                  <span className="px-2 py-1 text-xs font-medium rounded bg-purple-100 text-purple-800">
                    Async
                  </span>
                )}
              </div>

              <p className="text-sm text-gray-600 mb-3">{task.description}</p>

              <div className="space-y-2">
                <div>
                  <span className="text-xs font-medium text-gray-500">Expected Output:</span>
                  <p className="text-sm text-gray-700">{task.expected_output}</p>
                </div>

                {task.agent_id && (
                  <div>
                    <span className="text-xs font-medium text-gray-500">Assigned to:</span>
                    <span className="text-sm text-gray-700 ml-2">
                      {agentNames[task.agent_id] || `Agent #${task.agent_id}`}
                    </span>
                  </div>
                )}

                {task.context && (
                  <div>
                    <span className="text-xs font-medium text-gray-500">Context:</span>
                    <p className="text-sm text-gray-700">{task.context}</p>
                  </div>
                )}
              </div>

              <div className="flex items-center gap-2 mt-3">
                <span className="px-2 py-1 text-xs rounded bg-gray-100 text-gray-700">
                  {task.output_format}
                </span>
                {task.output_file && (
                  <span className="px-2 py-1 text-xs rounded bg-gray-100 text-gray-700">
                    📄 {task.output_file}
                  </span>
                )}
              </div>
            </div>

            <div className="flex gap-2 ml-4">
              <button
                onClick={() => onEdit(task)}
                className="px-3 py-1 text-sm font-medium text-blue-600 hover:bg-blue-50 rounded-md"
              >
                Edit
              </button>
              <button
                onClick={() => {
                  if (confirm(`Are you sure you want to delete task "${task.name}"?`)) {
                    onDelete(task.id);
                  }
                }}
                className="px-3 py-1 text-sm font-medium text-red-600 hover:bg-red-50 rounded-md"
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
