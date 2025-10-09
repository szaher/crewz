import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useRouter } from 'next/navigation';
import CreateFlowModal from '@/components/flows/CreateFlowModal';
import { useFlows } from '@/lib/hooks/useFlows';

// Mock dependencies
jest.mock('next/navigation', () => ({
  useRouter: jest.fn(),
}));

jest.mock('@/lib/hooks/useFlows', () => ({
  useFlows: jest.fn(),
}));

describe('CreateFlowModal', () => {
  let mockPush: jest.Mock;
  let mockCreateFlow: jest.Mock;
  let mockOnClose: jest.Mock;

  beforeEach(() => {
    mockPush = jest.fn();
    mockCreateFlow = jest.fn();
    mockOnClose = jest.fn();

    (useRouter as jest.Mock).mockReturnValue({
      push: mockPush,
    });

    (useFlows as jest.Mock).mockReturnValue({
      createFlow: mockCreateFlow,
    });
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  describe('Rendering', () => {
    it('should not render when isOpen is false', () => {
      const { container } = render(
        <CreateFlowModal isOpen={false} onClose={mockOnClose} />
      );
      expect(container.firstChild).toBeNull();
    });

    it('should render modal when isOpen is true', () => {
      render(<CreateFlowModal isOpen={true} onClose={mockOnClose} />);

      expect(screen.getByText('Create New Flow')).toBeInTheDocument();
      expect(screen.getByText('Create a workflow to orchestrate your AI agents')).toBeInTheDocument();
    });

    it('should render form fields', () => {
      render(<CreateFlowModal isOpen={true} onClose={mockOnClose} />);

      expect(screen.getByLabelText(/name/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/description/i)).toBeInTheDocument();
    });

    it('should render action buttons', () => {
      render(<CreateFlowModal isOpen={true} onClose={mockOnClose} />);

      expect(screen.getByRole('button', { name: /create flow/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument();
    });
  });

  describe('User Interactions', () => {
    it('should close modal when backdrop is clicked', async () => {
      render(<CreateFlowModal isOpen={true} onClose={mockOnClose} />);

      const backdrop = screen.getByText('Create New Flow').closest('.fixed')?.previousSibling;
      if (backdrop) {
        fireEvent.click(backdrop as Element);
        expect(mockOnClose).toHaveBeenCalledTimes(1);
      }
    });

    it('should close modal when Cancel button is clicked', async () => {
      render(<CreateFlowModal isOpen={true} onClose={mockOnClose} />);

      const cancelButton = screen.getByRole('button', { name: /cancel/i });
      fireEvent.click(cancelButton);

      expect(mockOnClose).toHaveBeenCalledTimes(1);
    });

    it('should allow typing in name field', async () => {
      const user = userEvent.setup();
      render(<CreateFlowModal isOpen={true} onClose={mockOnClose} />);

      const nameInput = screen.getByLabelText(/name/i) as HTMLInputElement;
      await user.type(nameInput, 'My Test Flow');

      expect(nameInput.value).toBe('My Test Flow');
    });

    it('should allow typing in description field', async () => {
      const user = userEvent.setup();
      render(<CreateFlowModal isOpen={true} onClose={mockOnClose} />);

      const descInput = screen.getByLabelText(/description/i) as HTMLTextAreaElement;
      await user.type(descInput, 'Test description');

      expect(descInput.value).toBe('Test description');
    });
  });

  describe('Form Validation', () => {
    it('should show error when name is empty', async () => {
      render(<CreateFlowModal isOpen={true} onClose={mockOnClose} />);

      const submitButton = screen.getByRole('button', { name: /create flow/i });
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText(/name is required/i)).toBeInTheDocument();
      });
    });

    it('should show error when name is too short', async () => {
      const user = userEvent.setup();
      render(<CreateFlowModal isOpen={true} onClose={mockOnClose} />);

      const nameInput = screen.getByLabelText(/name/i);
      await user.type(nameInput, 'ab');

      const submitButton = screen.getByRole('button', { name: /create flow/i });
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText(/at least 3 characters/i)).toBeInTheDocument();
      });
    });

    it('should not submit when validation fails', async () => {
      render(<CreateFlowModal isOpen={true} onClose={mockOnClose} />);

      const submitButton = screen.getByRole('button', { name: /create flow/i });
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(mockCreateFlow).not.toHaveBeenCalled();
      });
    });
  });

  describe('Form Submission', () => {
    it('should successfully create flow with valid data', async () => {
      const user = userEvent.setup();
      const mockFlow = { id: 123, name: 'Test Flow', description: 'Test description' };
      mockCreateFlow.mockResolvedValue(mockFlow);

      render(<CreateFlowModal isOpen={true} onClose={mockOnClose} />);

      // Fill in form
      const nameInput = screen.getByLabelText(/name/i);
      await user.type(nameInput, 'Test Flow');

      const descInput = screen.getByLabelText(/description/i);
      await user.type(descInput, 'Test description');

      // Submit
      const submitButton = screen.getByRole('button', { name: /create flow/i });
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(mockCreateFlow).toHaveBeenCalledWith({
          name: 'Test Flow',
          description: 'Test description',
          variables: {},
        });
      });
    });

    it('should trim whitespace from name and description', async () => {
      const user = userEvent.setup();
      const mockFlow = { id: 123, name: 'Test Flow', description: 'Test description' };
      mockCreateFlow.mockResolvedValue(mockFlow);

      render(<CreateFlowModal isOpen={true} onClose={mockOnClose} />);

      const nameInput = screen.getByLabelText(/name/i);
      await user.type(nameInput, '  Test Flow  ');

      const descInput = screen.getByLabelText(/description/i);
      await user.type(descInput, '  Test description  ');

      const submitButton = screen.getByRole('button', { name: /create flow/i });
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(mockCreateFlow).toHaveBeenCalledWith({
          name: 'Test Flow',
          description: 'Test description',
          variables: {},
        });
      });
    });

    it('should navigate to flow editor on success', async () => {
      const user = userEvent.setup();
      const mockFlow = { id: 456, name: 'New Flow' };
      mockCreateFlow.mockResolvedValue(mockFlow);

      render(<CreateFlowModal isOpen={true} onClose={mockOnClose} />);

      const nameInput = screen.getByLabelText(/name/i);
      await user.type(nameInput, 'New Flow');

      const submitButton = screen.getByRole('button', { name: /create flow/i });
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(mockPush).toHaveBeenCalledWith('/flows/456/edit');
      });
    });

    it('should close modal on success', async () => {
      const user = userEvent.setup();
      const mockFlow = { id: 789, name: 'Another Flow' };
      mockCreateFlow.mockResolvedValue(mockFlow);

      render(<CreateFlowModal isOpen={true} onClose={mockOnClose} />);

      const nameInput = screen.getByLabelText(/name/i);
      await user.type(nameInput, 'Another Flow');

      const submitButton = screen.getByRole('button', { name: /create flow/i });
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(mockOnClose).toHaveBeenCalled();
      });
    });

    it('should disable submit button while submitting', async () => {
      const user = userEvent.setup();
      mockCreateFlow.mockImplementation(() => new Promise(resolve => setTimeout(() => resolve({ id: 1 }), 100)));

      render(<CreateFlowModal isOpen={true} onClose={mockOnClose} />);

      const nameInput = screen.getByLabelText(/name/i);
      await user.type(nameInput, 'Test Flow');

      const submitButton = screen.getByRole('button', { name: /create flow/i });
      fireEvent.click(submitButton);

      expect(submitButton).toBeDisabled();

      await waitFor(() => {
        expect(submitButton).not.toBeDisabled();
      });
    });
  });

  describe('Error Handling', () => {
    it('should display error message on API failure', async () => {
      const user = userEvent.setup();
      mockCreateFlow.mockRejectedValue(new Error('Network error'));

      render(<CreateFlowModal isOpen={true} onClose={mockOnClose} />);

      const nameInput = screen.getByLabelText(/name/i);
      await user.type(nameInput, 'Test Flow');

      const submitButton = screen.getByRole('button', { name: /create flow/i });
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText(/network error/i)).toBeInTheDocument();
      });
    });

    it('should not close modal on error', async () => {
      const user = userEvent.setup();
      mockCreateFlow.mockRejectedValue(new Error('Server error'));

      render(<CreateFlowModal isOpen={true} onClose={mockOnClose} />);

      const nameInput = screen.getByLabelText(/name/i);
      await user.type(nameInput, 'Test Flow');

      const submitButton = screen.getByRole('button', { name: /create flow/i });
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText(/server error/i)).toBeInTheDocument();
      });

      expect(mockOnClose).not.toHaveBeenCalled();
    });

    it('should clear error when modal is closed and reopened', async () => {
      const user = userEvent.setup();
      mockCreateFlow.mockRejectedValue(new Error('Test error'));

      const { rerender } = render(<CreateFlowModal isOpen={true} onClose={mockOnClose} />);

      const nameInput = screen.getByLabelText(/name/i);
      await user.type(nameInput, 'Test Flow');

      const submitButton = screen.getByRole('button', { name: /create flow/i });
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText(/test error/i)).toBeInTheDocument();
      });

      // Close modal
      const cancelButton = screen.getByRole('button', { name: /cancel/i });
      fireEvent.click(cancelButton);

      // Reopen modal
      rerender(<CreateFlowModal isOpen={false} onClose={mockOnClose} />);
      rerender(<CreateFlowModal isOpen={true} onClose={mockOnClose} />);

      expect(screen.queryByText(/test error/i)).not.toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('should have proper ARIA labels', () => {
      render(<CreateFlowModal isOpen={true} onClose={mockOnClose} />);

      expect(screen.getByLabelText(/name/i)).toHaveAttribute('id');
      expect(screen.getByLabelText(/description/i)).toHaveAttribute('id');
    });

    it('should have proper heading hierarchy', () => {
      render(<CreateFlowModal isOpen={true} onClose={mockOnClose} />);

      const heading = screen.getByText('Create New Flow');
      expect(heading.tagName).toBe('H2');
    });

    it('should be keyboard navigable', async () => {
      const user = userEvent.setup();
      render(<CreateFlowModal isOpen={true} onClose={mockOnClose} />);

      // Tab through form elements
      await user.tab();
      expect(screen.getByLabelText(/name/i)).toHaveFocus();

      await user.tab();
      expect(screen.getByLabelText(/description/i)).toHaveFocus();
    });
  });
});
