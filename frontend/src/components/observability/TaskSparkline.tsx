'use client';

import { ResponsiveContainer, LineChart, Line, Tooltip, Legend, CartesianGrid } from 'recharts';
import { ExecutionTrend } from '@/lib/hooks/useMetrics';

interface TaskSparklineProps {
  data: ExecutionTrend[];
}

export default function TaskSparkline({ data }: TaskSparklineProps) {
  // Handle undefined or empty data
  if (!data || data.length === 0) {
    return (
      <div className="w-full h-24 flex items-center justify-center text-gray-400 text-sm">
        No data available
      </div>
    );
  }

  const formatted = data.map(d => ({
    time: new Date(d.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    Total: d.count,
    Failed: d.failedCount,
    Success: d.successCount,
  }));

  return (
    <div className="w-full h-24">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={formatted} margin={{ top: 5, right: 10, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <Tooltip
            contentStyle={{
              backgroundColor: '#ffffff',
              border: '1px solid #e5e7eb',
              borderRadius: '8px',
              boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)',
            }}
          />
          <Legend wrapperStyle={{ fontSize: 12 }} iconType="line" />
          <Line type="monotone" dataKey="Total" stroke="#f59e0b" strokeWidth={2} dot={false} />
          <Line type="monotone" dataKey="Failed" stroke="#ef4444" strokeWidth={2} dot={false} />
          <Line type="monotone" dataKey="Success" stroke="#10b981" strokeWidth={2} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

