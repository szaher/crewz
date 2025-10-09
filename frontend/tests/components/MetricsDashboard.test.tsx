import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import MetricsDashboard from '@/components/observability/MetricsDashboard';
import { useMetrics } from '@/lib/hooks/useMetrics';

jest.mock('@/lib/hooks/useMetrics');

const mockMetricsData = {
  totalExecutions: 1234,
  successRate: 98.5,
  errorRate: 1.5,
  avgExecutionTime: 2.3,
  trendData: [
    { time: '10:00', executions: 45 },
    { time: '11:00', executions: 52 },
    { time: '12:00', executions: 48 },
  ],
  recentErrors: [
    {
      id: 1,
      timestamp: '2025-01-08T10:30:00Z',
      flow_name: 'Test Flow',
      error: 'Connection timeout',
    },
  ],
};

describe('MetricsDashboard', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Loading State', () => {
    it('should show loading skeleton initially', () => {
      (useMetrics as jest.Mock).mockReturnValue({
        metrics: null,
        loading: true,
        error: null,
        refetch: jest.fn(),
      });

      render(<MetricsDashboard />);

      expect(screen.getByTestId('metrics-loading')).toBeInTheDocument();
    });

    it('should show loading for all metric cards', () => {
      (useMetrics as jest.Mock).mockReturnValue({
        metrics: null,
        loading: true,
        error: null,
        refetch: jest.fn(),
      });

      render(<MetricsDashboard />);

      const skeletons = screen.getAllByTestId('skeleton');
      expect(skeletons.length).toBeGreaterThan(0);
    });
  });

  describe('Error State', () => {
    it('should show error message when fetch fails', () => {
      (useMetrics as jest.Mock).mockReturnValue({
        metrics: null,
        loading: false,
        error: 'Failed to load metrics',
        refetch: jest.fn(),
      });

      render(<MetricsDashboard />);

      expect(screen.getByText(/failed to load metrics/i)).toBeInTheDocument();
    });

    it('should show retry button on error', () => {
      (useMetrics as jest.Mock).mockReturnValue({
        metrics: null,
        loading: false,
        error: 'Network error',
        refetch: jest.fn(),
      });

      render(<MetricsDashboard />);

      expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument();
    });

    it('should call refetch when retry clicked', async () => {
      const mockRefetch = jest.fn();
      (useMetrics as jest.Mock).mockReturnValue({
        metrics: null,
        loading: false,
        error: 'Network error',
        refetch: mockRefetch,
      });

      const user = userEvent.setup();
      render(<MetricsDashboard />);

      const retryButton = screen.getByRole('button', { name: /retry/i });
      await user.click(retryButton);

      expect(mockRefetch).toHaveBeenCalled();
    });
  });

  describe('Empty State', () => {
    it('should show empty state when no data', () => {
      (useMetrics as jest.Mock).mockReturnValue({
        metrics: {
          totalExecutions: 0,
          successRate: 0,
          errorRate: 0,
          avgExecutionTime: 0,
          trendData: [],
          recentErrors: [],
        },
        loading: false,
        error: null,
        refetch: jest.fn(),
      });

      render(<MetricsDashboard />);

      expect(screen.getByText(/no execution data yet/i)).toBeInTheDocument();
    });

    it('should show call-to-action in empty state', () => {
      (useMetrics as jest.Mock).mockReturnValue({
        metrics: {
          totalExecutions: 0,
          successRate: 0,
          errorRate: 0,
          avgExecutionTime: 0,
          trendData: [],
          recentErrors: [],
        },
        loading: false,
        error: null,
        refetch: jest.fn(),
      });

      render(<MetricsDashboard />);

      expect(screen.getByText(/run a flow to see metrics/i)).toBeInTheDocument();
    });
  });

  describe('Metrics Display', () => {
    beforeEach(() => {
      (useMetrics as jest.Mock).mockReturnValue({
        metrics: mockMetricsData,
        loading: false,
        error: null,
        refetch: jest.fn(),
      });
    });

    it('should display total executions', () => {
      render(<MetricsDashboard />);
      expect(screen.getByText('1,234')).toBeInTheDocument();
    });

    it('should display success rate', () => {
      render(<MetricsDashboard />);
      expect(screen.getByText('98.5%')).toBeInTheDocument();
    });

    it('should display error rate', () => {
      render(<MetricsDashboard />);
      expect(screen.getByText('1.5%')).toBeInTheDocument();
    });

    it('should display average execution time', () => {
      render(<MetricsDashboard />);
      expect(screen.getByText('2.3s')).toBeInTheDocument();
    });

    it('should render all metric cards', () => {
      render(<MetricsDashboard />);

      expect(screen.getByText(/total executions/i)).toBeInTheDocument();
      expect(screen.getByText(/success rate/i)).toBeInTheDocument();
      expect(screen.getByText(/error rate/i)).toBeInTheDocument();
      expect(screen.getByText(/average time/i)).toBeInTheDocument();
    });
  });

  describe('Execution Trend Chart', () => {
    beforeEach(() => {
      (useMetrics as jest.Mock).mockReturnValue({
        metrics: mockMetricsData,
        loading: false,
        error: null,
        refetch: jest.fn(),
      });
    });

    it('should render chart container', () => {
      render(<MetricsDashboard />);
      expect(screen.getByTestId('execution-trend-chart')).toBeInTheDocument();
    });

    it('should display chart title', () => {
      render(<MetricsDashboard />);
      expect(screen.getByText(/execution trend/i)).toBeInTheDocument();
    });
  });

  describe('Recent Errors List', () => {
    beforeEach(() => {
      (useMetrics as jest.Mock).mockReturnValue({
        metrics: mockMetricsData,
        loading: false,
        error: null,
        refetch: jest.fn(),
      });
    });

    it('should display recent errors section', () => {
      render(<MetricsDashboard />);
      expect(screen.getByText(/recent errors/i)).toBeInTheDocument();
    });

    it('should display error entries', () => {
      render(<MetricsDashboard />);
      expect(screen.getByText('Test Flow')).toBeInTheDocument();
      expect(screen.getByText('Connection timeout')).toBeInTheDocument();
    });

    it('should show empty message when no errors', () => {
      (useMetrics as jest.Mock).mockReturnValue({
        metrics: { ...mockMetricsData, recentErrors: [] },
        loading: false,
        error: null,
        refetch: jest.fn(),
      });

      render(<MetricsDashboard />);
      expect(screen.getByText(/no recent errors/i)).toBeInTheDocument();
    });
  });

  describe('Time Range Filter', () => {
    beforeEach(() => {
      (useMetrics as jest.Mock).mockReturnValue({
        metrics: mockMetricsData,
        loading: false,
        error: null,
        refetch: jest.fn(),
        setTimeRange: jest.fn(),
      });
    });

    it('should render time range filter', () => {
      render(<MetricsDashboard />);
      expect(screen.getByLabelText(/time range/i)).toBeInTheDocument();
    });

    it('should have time range options', () => {
      render(<MetricsDashboard />);

      const select = screen.getByLabelText(/time range/i);
      expect(select).toBeInTheDocument();
    });

    it('should update metrics when time range changes', async () => {
      const mockSetTimeRange = jest.fn();
      (useMetrics as jest.Mock).mockReturnValue({
        metrics: mockMetricsData,
        loading: false,
        error: null,
        refetch: jest.fn(),
        setTimeRange: mockSetTimeRange,
      });

      const user = userEvent.setup();
      render(<MetricsDashboard />);

      const select = screen.getByLabelText(/time range/i);
      await user.selectOptions(select, '7d');

      expect(mockSetTimeRange).toHaveBeenCalledWith('7d');
    });
  });

  describe('Refresh Functionality', () => {
    it('should have refresh button', () => {
      (useMetrics as jest.Mock).mockReturnValue({
        metrics: mockMetricsData,
        loading: false,
        error: null,
        refetch: jest.fn(),
      });

      render(<MetricsDashboard />);

      expect(screen.getByRole('button', { name: /refresh/i })).toBeInTheDocument();
    });

    it('should call refetch when refresh clicked', async () => {
      const mockRefetch = jest.fn();
      (useMetrics as jest.Mock).mockReturnValue({
        metrics: mockMetricsData,
        loading: false,
        error: null,
        refetch: mockRefetch,
      });

      const user = userEvent.setup();
      render(<MetricsDashboard />);

      const refreshButton = screen.getByRole('button', { name: /refresh/i });
      await user.click(refreshButton);

      expect(mockRefetch).toHaveBeenCalled();
    });

    it('should disable refresh button while loading', () => {
      (useMetrics as jest.Mock).mockReturnValue({
        metrics: mockMetricsData,
        loading: true,
        error: null,
        refetch: jest.fn(),
      });

      render(<MetricsDashboard />);

      const refreshButton = screen.getByRole('button', { name: /refresh/i });
      expect(refreshButton).toBeDisabled();
    });
  });

  describe('Auto-refresh', () => {
    it('should set up auto-refresh interval', () => {
      jest.useFakeTimers();
      const mockRefetch = jest.fn();

      (useMetrics as jest.Mock).mockReturnValue({
        metrics: mockMetricsData,
        loading: false,
        error: null,
        refetch: mockRefetch,
      });

      render(<MetricsDashboard />);

      // Fast-forward 30 seconds
      jest.advanceTimersByTime(30000);

      expect(mockRefetch).toHaveBeenCalled();

      jest.useRealTimers();
    });
  });

  describe('Accessibility', () => {
    beforeEach(() => {
      (useMetrics as jest.Mock).mockReturnValue({
        metrics: mockMetricsData,
        loading: false,
        error: null,
        refetch: jest.fn(),
      });
    });

    it('should have proper heading hierarchy', () => {
      render(<MetricsDashboard />);

      const mainHeading = screen.getByRole('heading', { level: 1 });
      expect(mainHeading).toBeInTheDocument();
    });

    it('should have ARIA labels on interactive elements', () => {
      render(<MetricsDashboard />);

      const refreshButton = screen.getByRole('button', { name: /refresh/i });
      expect(refreshButton).toHaveAttribute('aria-label');
    });

    it('should announce loading state to screen readers', () => {
      (useMetrics as jest.Mock).mockReturnValue({
        metrics: null,
        loading: true,
        error: null,
        refetch: jest.fn(),
      });

      render(<MetricsDashboard />);

      const loadingElement = screen.getByTestId('metrics-loading');
      expect(loadingElement).toHaveAttribute('aria-live', 'polite');
    });
  });
});
