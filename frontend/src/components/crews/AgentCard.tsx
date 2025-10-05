'use client';

import type { Agent } from '@/types/api';

interface AgentCardProps {
  agent: Agent;
  selected: boolean;
  onToggle: () => void;
}

export default function AgentCard({ agent, selected, onToggle }: AgentCardProps) {
  return (
    <div
      onClick={onToggle}
      className={`
        p-4 rounded-lg border-2 cursor-pointer transition-all
        ${selected
          ? 'border-blue-500 bg-blue-50'
          : 'border-gray-200 bg-white hover:border-gray-300'
        }
      `}
    >
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <h4 className="font-medium text-gray-900">{agent.name}</h4>
            {selected && (
              <svg className="w-5 h-5 text-blue-600" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
              </svg>
            )}
          </div>
          <p className="text-sm text-gray-600 mt-1">{agent.role}</p>
          {agent.goal && (
            <p className="text-xs text-gray-500 mt-2 line-clamp-2">{agent.goal}</p>
          )}
        </div>
      </div>

      <div className="mt-3 flex items-center gap-2">
        <span className={`
          px-2 py-1 text-xs font-medium rounded
          ${agent.is_active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}
        `}>
          {agent.is_active ? 'Active' : 'Inactive'}
        </span>
        {agent.tools && agent.tools.length > 0 && (
          <span className="px-2 py-1 text-xs font-medium rounded bg-purple-100 text-purple-800">
            {agent.tools.length} tool{agent.tools.length !== 1 ? 's' : ''}
          </span>
        )}
      </div>
    </div>
  );
}
