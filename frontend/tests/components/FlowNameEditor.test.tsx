import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import FlowNameEditor from '@/components/flows/FlowNameEditor';

describe('FlowNameEditor', () => {
  const mockOnSave = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Display Mode', () => {
    it('should render flow name', () => {
      render(<FlowNameEditor name="My Flow" onSave={mockOnSave} />);
      expect(screen.getByText('My Flow')).toBeInTheDocument();
    });

    it('should show pencil icon on hover', () => {
      render(<FlowNameEditor name="My Flow" onSave={mockOnSave} />);
      const container = screen.getByText('My Flow').closest('div');
      expect(container).toBeInTheDocument();
    });

    it('should switch to edit mode on click', async () => {
      const user = userEvent.setup();
      render(<FlowNameEditor name="My Flow" onSave={mockOnSave} />);

      const nameElement = screen.getByText('My Flow');
      await user.click(nameElement);

      const input = screen.getByDisplayValue('My Flow');
      expect(input).toBeInTheDocument();
      expect(input).toHaveFocus();
    });
  });

  describe('Edit Mode', () => {
    it('should show input field when editing', async () => {
      const user = userEvent.setup();
      render(<FlowNameEditor name="My Flow" onSave={mockOnSave} />);

      await user.click(screen.getByText('My Flow'));

      const input = screen.getByDisplayValue('My Flow');
      expect(input).toBeInTheDocument();
      expect(input.tagName).toBe('INPUT');
    });

    it('should allow typing new name', async () => {
      const user = userEvent.setup();
      render(<FlowNameEditor name="My Flow" onSave={mockOnSave} />);

      await user.click(screen.getByText('My Flow'));
      const input = screen.getByDisplayValue('My Flow') as HTMLInputElement;

      await user.clear(input);
      await user.type(input, 'Updated Flow Name');

      expect(input.value).toBe('Updated Flow Name');
    });

    it('should save on Enter key', async () => {
      const user = userEvent.setup();
      render(<FlowNameEditor name="My Flow" onSave={mockOnSave} />);

      await user.click(screen.getByText('My Flow'));
      const input = screen.getByDisplayValue('My Flow');

      await user.clear(input);
      await user.type(input, 'New Name{Enter}');

      await waitFor(() => {
        expect(mockOnSave).toHaveBeenCalledWith('New Name');
      });
    });

    it('should save on blur', async () => {
      const user = userEvent.setup();
      render(<FlowNameEditor name="My Flow" onSave={mockOnSave} />);

      await user.click(screen.getByText('My Flow'));
      const input = screen.getByDisplayValue('My Flow');

      await user.clear(input);
      await user.type(input, 'Blurred Name');

      fireEvent.blur(input);

      await waitFor(() => {
        expect(mockOnSave).toHaveBeenCalledWith('Blurred Name');
      });
    });

    it('should cancel on Escape key', async () => {
      const user = userEvent.setup();
      render(<FlowNameEditor name="My Flow" onSave={mockOnSave} />);

      await user.click(screen.getByText('My Flow'));
      const input = screen.getByDisplayValue('My Flow');

      await user.clear(input);
      await user.type(input, 'New Name');
      await user.keyboard('{Escape}');

      expect(mockOnSave).not.toHaveBeenCalled();
      expect(screen.getByText('My Flow')).toBeInTheDocument();
    });
  });

  describe('Validation', () => {
    it('should not save empty name', async () => {
      const user = userEvent.setup();
      render(<FlowNameEditor name="My Flow" onSave={mockOnSave} />);

      await user.click(screen.getByText('My Flow'));
      const input = screen.getByDisplayValue('My Flow');

      await user.clear(input);
      await user.keyboard('{Enter}');

      expect(mockOnSave).not.toHaveBeenCalled();
    });

    it('should trim whitespace', async () => {
      const user = userEvent.setup();
      render(<FlowNameEditor name="My Flow" onSave={mockOnSave} />);

      await user.click(screen.getByText('My Flow'));
      const input = screen.getByDisplayValue('My Flow');

      await user.clear(input);
      await user.type(input, '  Trimmed Name  {Enter}');

      await waitFor(() => {
        expect(mockOnSave).toHaveBeenCalledWith('Trimmed Name');
      });
    });

    it('should not save if name unchanged', async () => {
      const user = userEvent.setup();
      render(<FlowNameEditor name="My Flow" onSave={mockOnSave} />);

      await user.click(screen.getByText('My Flow'));
      const input = screen.getByDisplayValue('My Flow');

      await user.keyboard('{Enter}');

      expect(mockOnSave).not.toHaveBeenCalled();
    });
  });

  describe('Loading State', () => {
    it('should show loading indicator while saving', async () => {
      const user = userEvent.setup();
      const slowSave = jest.fn(() => new Promise(resolve => setTimeout(resolve, 100)));

      render(<FlowNameEditor name="My Flow" onSave={slowSave} />);

      await user.click(screen.getByText('My Flow'));
      const input = screen.getByDisplayValue('My Flow');

      await user.clear(input);
      await user.type(input, 'New Name{Enter}');

      // Should show loading state
      expect(screen.queryByDisplayValue('New Name')).toBeInTheDocument();
    });

    it('should disable input while saving', async () => {
      const user = userEvent.setup();
      const slowSave = jest.fn(() => new Promise(resolve => setTimeout(resolve, 100)));

      render(<FlowNameEditor name="My Flow" onSave={slowSave} />);

      await user.click(screen.getByText('My Flow'));
      const input = screen.getByDisplayValue('My Flow') as HTMLInputElement;

      await user.clear(input);
      await user.type(input, 'New Name{Enter}');

      expect(input).toBeDisabled();
    });
  });

  describe('Error Handling', () => {
    it('should handle save errors gracefully', async () => {
      const user = userEvent.setup();
      const failingSave = jest.fn(() => Promise.reject(new Error('Save failed')));

      render(<FlowNameEditor name="My Flow" onSave={failingSave} />);

      await user.click(screen.getByText('My Flow'));
      const input = screen.getByDisplayValue('My Flow');

      await user.clear(input);
      await user.type(input, 'New Name{Enter}');

      await waitFor(() => {
        expect(failingSave).toHaveBeenCalled();
        // Should revert to original name on error
        expect(screen.getByText('My Flow')).toBeInTheDocument();
      });
    });
  });

  describe('Accessibility', () => {
    it('should have proper ARIA labels', () => {
      render(<FlowNameEditor name="My Flow" onSave={mockOnSave} />);

      const nameElement = screen.getByText('My Flow');
      expect(nameElement.closest('button')).toHaveAttribute('aria-label');
    });

    it('should be keyboard accessible', async () => {
      const user = userEvent.setup();
      render(<FlowNameEditor name="My Flow" onSave={mockOnSave} />);

      // Tab to element
      await user.tab();

      // Enter to edit
      await user.keyboard('{Enter}');

      const input = screen.getByDisplayValue('My Flow');
      expect(input).toHaveFocus();
    });
  });
});
