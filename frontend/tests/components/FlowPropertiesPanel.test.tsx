import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import FlowPropertiesPanel from '@/components/flows/FlowPropertiesPanel';

const mockFlow = {
  id: 1,
  name: 'Test Flow',
  description: 'Test description',
  variables: { key1: 'value1' },
  created_at: '2025-01-01T00:00:00Z',
  updated_at: '2025-01-02T00:00:00Z',
  version: 1,
};

describe('FlowPropertiesPanel', () => {
  const mockOnSave = jest.fn();
  const mockOnClose = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Rendering', () => {
    it('should not render when closed', () => {
      const { container } = render(
        <FlowPropertiesPanel
          flowId={1}
          initialData={mockFlow}
          isOpen={false}
          onClose={mockOnClose}
        />
      );
      expect(container.firstChild).toBeNull();
    });

    it('should render when open', () => {
      render(
        <FlowPropertiesPanel
          flowId={1}
          initialData={mockFlow}
          isOpen={true}
          onClose={mockOnClose}
        />
      );

      expect(screen.getByText('Flow Properties')).toBeInTheDocument();
    });

    it('should render all tabs', () => {
      render(
        <FlowPropertiesPanel
          flowId={1}
          initialData={mockFlow}
          isOpen={true}
          onClose={mockOnClose}
        />
      );

      expect(screen.getByRole('tab', { name: /general/i })).toBeInTheDocument();
      expect(screen.getByRole('tab', { name: /variables/i })).toBeInTheDocument();
      expect(screen.getByRole('tab', { name: /settings/i })).toBeInTheDocument();
      expect(screen.getByRole('tab', { name: /metadata/i })).toBeInTheDocument();
    });
  });

  describe('General Tab', () => {
    it('should display flow name', () => {
      render(
        <FlowPropertiesPanel
          flowId={1}
          initialData={mockFlow}
          isOpen={true}
          onClose={mockOnClose}
        />
      );

      const nameInput = screen.getByLabelText(/name/i) as HTMLInputElement;
      expect(nameInput.value).toBe('Test Flow');
    });

    it('should display flow description', () => {
      render(
        <FlowPropertiesPanel
          flowId={1}
          initialData={mockFlow}
          isOpen={true}
          onClose={mockOnClose}
        />
      );

      const descInput = screen.getByLabelText(/description/i) as HTMLTextAreaElement;
      expect(descInput.value).toBe('Test description');
    });

    it('should allow editing name', async () => {
      const user = userEvent.setup();
      render(
        <FlowPropertiesPanel
          flowId={1}
          initialData={mockFlow}
          isOpen={true}
          onClose={mockOnClose}
        />
      );

      const nameInput = screen.getByLabelText(/name/i);
      await user.clear(nameInput);
      await user.type(nameInput, 'Updated Flow Name');

      expect(nameInput).toHaveValue('Updated Flow Name');
    });

    it('should allow editing description', async () => {
      const user = userEvent.setup();
      render(
        <FlowPropertiesPanel
          flowId={1}
          initialData={mockFlow}
          isOpen={true}
          onClose={mockOnClose}
        />
      );

      const descInput = screen.getByLabelText(/description/i);
      await user.clear(descInput);
      await user.type(descInput, 'Updated description');

      expect(descInput).toHaveValue('Updated description');
    });
  });

  describe('Variables Tab', () => {
    it('should switch to variables tab', async () => {
      const user = userEvent.setup();
      render(
        <FlowPropertiesPanel
          flowId={1}
          initialData={mockFlow}
          isOpen={true}
          onClose={mockOnClose}
        />
      );

      const variablesTab = screen.getByRole('tab', { name: /variables/i });
      await user.click(variablesTab);

      expect(screen.getByText(/flow variables/i)).toBeInTheDocument();
    });

    it('should display variables as JSON', async () => {
      const user = userEvent.setup();
      render(
        <FlowPropertiesPanel
          flowId={1}
          initialData={mockFlow}
          isOpen={true}
          onClose={mockOnClose}
        />
      );

      await user.click(screen.getByRole('tab', { name: /variables/i }));

      const jsonEditor = screen.getByRole('textbox');
      expect(jsonEditor).toHaveValue(JSON.stringify(mockFlow.variables, null, 2));
    });

    it('should allow editing variables', async () => {
      const user = userEvent.setup();
      render(
        <FlowPropertiesPanel
          flowId={1}
          initialData={mockFlow}
          isOpen={true}
          onClose={mockOnClose}
        />
      );

      await user.click(screen.getByRole('tab', { name: /variables/i }));

      const jsonEditor = screen.getByRole('textbox');
      await user.clear(jsonEditor);
      await user.type(jsonEditor, '{"new_key": "new_value"}');

      expect(jsonEditor).toHaveValue('{"new_key": "new_value"}');
    });
  });

  describe('Settings Tab', () => {
    it('should switch to settings tab', async () => {
      const user = userEvent.setup();
      render(
        <FlowPropertiesPanel
          flowId={1}
          initialData={mockFlow}
          isOpen={true}
          onClose={mockOnClose}
        />
      );

      const settingsTab = screen.getByRole('tab', { name: /settings/i });
      await user.click(settingsTab);

      expect(screen.getByText(/execution settings/i)).toBeInTheDocument();
    });
  });

  describe('Metadata Tab', () => {
    it('should switch to metadata tab', async () => {
      const user = userEvent.setup();
      render(
        <FlowPropertiesPanel
          flowId={1}
          initialData={mockFlow}
          isOpen={true}
          onClose={mockOnClose}
        />
      );

      const metadataTab = screen.getByRole('tab', { name: /metadata/i });
      await user.click(metadataTab);

      expect(screen.getByText(/flow metadata/i)).toBeInTheDocument();
    });

    it('should display created date', async () => {
      const user = userEvent.setup();
      render(
        <FlowPropertiesPanel
          flowId={1}
          initialData={mockFlow}
          isOpen={true}
          onClose={mockOnClose}
        />
      );

      await user.click(screen.getByRole('tab', { name: /metadata/i }));

      expect(screen.getByText(/created/i)).toBeInTheDocument();
    });

    it('should display version', async () => {
      const user = userEvent.setup();
      render(
        <FlowPropertiesPanel
          flowId={1}
          initialData={mockFlow}
          isOpen={true}
          onClose={mockOnClose}
        />
      );

      await user.click(screen.getByRole('tab', { name: /metadata/i }));

      expect(screen.getByText(/version/i)).toBeInTheDocument();
    });
  });

  describe('Save Functionality', () => {
    it('should have save button', () => {
      render(
        <FlowPropertiesPanel
          flowId={1}
          initialData={mockFlow}
          isOpen={true}
          onClose={mockOnClose}
        />
      );

      expect(screen.getByRole('button', { name: /save/i })).toBeInTheDocument();
    });

    it('should have cancel button', () => {
      render(
        <FlowPropertiesPanel
          flowId={1}
          initialData={mockFlow}
          isOpen={true}
          onClose={mockOnClose}
        />
      );

      expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument();
    });

    it('should close panel on cancel', async () => {
      const user = userEvent.setup();
      render(
        <FlowPropertiesPanel
          flowId={1}
          initialData={mockFlow}
          isOpen={true}
          onClose={mockOnClose}
        />
      );

      const cancelButton = screen.getByRole('button', { name: /cancel/i });
      await user.click(cancelButton);

      expect(mockOnClose).toHaveBeenCalled();
    });

    it('should disable save button when no changes', () => {
      render(
        <FlowPropertiesPanel
          flowId={1}
          initialData={mockFlow}
          isOpen={true}
          onClose={mockOnClose}
        />
      );

      const saveButton = screen.getByRole('button', { name: /save/i });
      expect(saveButton).toBeDisabled();
    });

    it('should enable save button when changes made', async () => {
      const user = userEvent.setup();
      render(
        <FlowPropertiesPanel
          flowId={1}
          initialData={mockFlow}
          isOpen={true}
          onClose={mockOnClose}
        />
      );

      const nameInput = screen.getByLabelText(/name/i);
      await user.clear(nameInput);
      await user.type(nameInput, 'Changed Name');

      const saveButton = screen.getByRole('button', { name: /save/i });
      expect(saveButton).not.toBeDisabled();
    });
  });

  describe('Unsaved Changes', () => {
    it('should detect unsaved changes', async () => {
      const user = userEvent.setup();
      render(
        <FlowPropertiesPanel
          flowId={1}
          initialData={mockFlow}
          isOpen={true}
          onClose={mockOnClose}
        />
      );

      const nameInput = screen.getByLabelText(/name/i);
      await user.clear(nameInput);
      await user.type(nameInput, 'Changed Name');

      expect(screen.getByText(/unsaved changes/i)).toBeInTheDocument();
    });

    it('should warn before closing with unsaved changes', async () => {
      const user = userEvent.setup();
      window.confirm = jest.fn(() => false);

      render(
        <FlowPropertiesPanel
          flowId={1}
          initialData={mockFlow}
          isOpen={true}
          onClose={mockOnClose}
        />
      );

      const nameInput = screen.getByLabelText(/name/i);
      await user.clear(nameInput);
      await user.type(nameInput, 'Changed Name');

      const cancelButton = screen.getByRole('button', { name: /cancel/i });
      await user.click(cancelButton);

      expect(window.confirm).toHaveBeenCalled();
      expect(mockOnClose).not.toHaveBeenCalled();
    });
  });

  describe('Animation', () => {
    it('should have slide-in animation class', () => {
      const { container } = render(
        <FlowPropertiesPanel
          flowId={1}
          initialData={mockFlow}
          isOpen={true}
          onClose={mockOnClose}
        />
      );

      const panel = container.firstChild;
      expect(panel).toHaveClass('animate-slide-in');
    });
  });

  describe('Accessibility', () => {
    it('should have proper ARIA labels', () => {
      render(
        <FlowPropertiesPanel
          flowId={1}
          initialData={mockFlow}
          isOpen={true}
          onClose={mockOnClose}
        />
      );

      expect(screen.getByRole('dialog')).toBeInTheDocument();
    });

    it('should trap focus within panel', async () => {
      const user = userEvent.setup();
      render(
        <FlowPropertiesPanel
          flowId={1}
          initialData={mockFlow}
          isOpen={true}
          onClose={mockOnClose}
        />
      );

      // Tab through elements - focus should stay in panel
      await user.tab();
      await user.tab();
      await user.tab();

      const activeElement = document.activeElement;
      const panel = screen.getByRole('dialog');
      expect(panel.contains(activeElement)).toBe(true);
    });
  });
});
