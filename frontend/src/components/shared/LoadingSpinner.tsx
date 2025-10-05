interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg';
  color?: 'blue' | 'white' | 'gray';
}

export default function LoadingSpinner({ size = 'md', color = 'blue' }: LoadingSpinnerProps) {
  const sizeStyles = {
    sm: 'h-4 w-4',
    md: 'h-8 w-8',
    lg: 'h-12 w-12',
  };

  const colorStyles = {
    blue: 'border-blue-600',
    white: 'border-white',
    gray: 'border-gray-600',
  };

  return (
    <div className="flex items-center justify-center">
      <div className={`animate-spin rounded-full border-b-2 ${sizeStyles[size]} ${colorStyles[color]}`}></div>
    </div>
  );
}
