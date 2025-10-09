import { TIME_RANGES } from '@/lib/hooks/useMetrics';

interface TimeRangeFilterProps {
  value: string;
  onChange: (value: string) => void;
}

export default function TimeRangeFilter({ value, onChange }: TimeRangeFilterProps) {
  return (
    <div className="flex items-center gap-2">
      <label className="text-sm font-medium text-gray-700">Time Range:</label>
      <div className="flex gap-1 bg-gray-100 p-1 rounded-lg">
        {TIME_RANGES.map((range) => (
          <button
            key={range.value}
            onClick={() => onChange(range.value)}
            className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
              value === range.value
                ? 'bg-white text-blue-600 shadow-sm'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            {range.label}
          </button>
        ))}
      </div>
    </div>
  );
}
