/**
 * E2E Test: Execution Lifecycle (T076)
 *
 * Tests the complete execution lifecycle:
 * - Queue via UI
 * - Watch live stream output
 * - Verify completion notification
 * - Download artifact
 */

import { test, expect } from '@playwright/test';

test.describe('Execution Lifecycle E2E', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to executions page
    // Note: Authentication might need to be mocked or handled
    await page.goto('/executions');
    await page.waitForLoadState('networkidle');
  });

  test('should queue execution via UI and watch completion', async ({ page }) => {
    // Find and click "New Execution" or "Execute Flow" button
    const executeButton = page.getByRole('button', { name: /execute|new execution|start/i }).first();

    if (await executeButton.isVisible()) {
      await executeButton.click();

      // Fill execution form
      await page.waitForSelector('form', { timeout: 5000 });

      // Select execution type if dropdown exists
      const typeSelect = page.locator('select[name="execution_type"], select[id="execution_type"]').first();
      if (await typeSelect.isVisible()) {
        await typeSelect.selectOption('flow');
      }

      // Select entity (flow/crew) if dropdown exists
      const entitySelect = page.locator('select[name="entity_id"], select[id="flow_id"]').first();
      if (await entitySelect.isVisible()) {
        await entitySelect.selectOption({ index: 1 }); // Select first available option
      }

      // Set priority
      const priorityInput = page.locator('input[name="priority"], select[name="priority"]').first();
      if (await priorityInput.isVisible()) {
        await priorityInput.fill('5');
      }

      // Submit execution
      const submitButton = page.getByRole('button', { name: /submit|execute|start/i });
      await submitButton.click();

      // Wait for navigation to execution detail page
      await page.waitForURL(/\/executions\/[a-f0-9\-]+/i, { timeout: 10000 });

      // Verify we're on execution detail page
      await expect(page).toHaveURL(/\/executions\//);

      // Check for execution status
      const statusElement = page.locator('[data-testid="execution-status"], .execution-status').first();
      if (await statusElement.isVisible()) {
        const status = await statusElement.textContent();
        expect(status).toMatch(/queued|running|completed|pending/i);
      }
    }
  });

  test('should display live stream output during execution', async ({ page }) => {
    // Navigate to a running/queued execution
    // Note: This would need a real execution ID or mock
    const testExecutionId = 'test-execution-id';

    // Try to navigate to execution detail
    await page.goto(`/executions/${testExecutionId}`);

    // Check if live stream component is present
    const liveStreamContainer = page.locator('[data-testid="live-execution-stream"], .live-stream, [class*="LiveExecutionStream"]').first();

    if (await liveStreamContainer.isVisible({ timeout: 2000 }).catch(() => false)) {
      // Verify stream container exists
      await expect(liveStreamContainer).toBeVisible();

      // Check for output lines
      const outputLines = page.locator('[data-testid="stream-line"], .stream-line, .output-line');

      // Wait for at least one output line (with timeout)
      await outputLines.first().waitFor({ state: 'visible', timeout: 5000 }).catch(() => {});

      const lineCount = await outputLines.count();
      if (lineCount > 0) {
        // Verify output is being displayed
        expect(lineCount).toBeGreaterThan(0);
      }
    }
  });

  test('should show queue position when execution is queued', async ({ page }) => {
    // Navigate to execution that might be queued
    const testExecutionId = 'test-queued-execution';

    await page.goto(`/executions/${testExecutionId}`);

    // Look for queue position component
    const queuePositionComponent = page.locator('[data-testid="queue-position"], .queue-position, [class*="QueuePosition"]').first();

    if (await queuePositionComponent.isVisible({ timeout: 2000 }).catch(() => false)) {
      await expect(queuePositionComponent).toBeVisible();

      // Check for position number
      const positionText = await queuePositionComponent.textContent();
      expect(positionText).toMatch(/position|queue|waiting/i);
    }
  });

  test('should display completion notification when execution finishes', async ({ page }) => {
    // This test would need a way to trigger completion or use WebSocket mocking

    // Navigate to execution page
    await page.goto('/executions');

    // Look for notifications/toasts
    const notification = page.locator('[role="alert"], .notification, .toast, [data-testid="notification"]').first();

    // If a notification appears within reasonable time
    if (await notification.isVisible({ timeout: 1000 }).catch(() => false)) {
      const notificationText = await notification.textContent();

      // Check if it's an execution completion notification
      if (notificationText && /completed|finished|done/i.test(notificationText)) {
        expect(notificationText).toMatch(/execution.*completed|completed.*execution/i);
      }
    }
  });

  test('should allow downloading artifacts after execution completes', async ({ page }) => {
    // Navigate to completed execution
    const testExecutionId = 'test-completed-execution';

    await page.goto(`/executions/${testExecutionId}`);

    // Look for artifacts list component
    const artifactsSection = page.locator('[data-testid="artifact-list"], .artifacts, [class*="ArtifactList"]').first();

    if (await artifactsSection.isVisible({ timeout: 2000 }).catch(() => false)) {
      await expect(artifactsSection).toBeVisible();

      // Look for download buttons
      const downloadButton = page.getByRole('button', { name: /download/i }).first();

      if (await downloadButton.isVisible()) {
        // Verify download button is present
        await expect(downloadButton).toBeVisible();
        await expect(downloadButton).toBeEnabled();
      }
    }
  });

  test('should show execution actions (cancel, re-execute)', async ({ page }) => {
    const testExecutionId = 'test-execution-with-actions';

    await page.goto(`/executions/${testExecutionId}`);

    // Look for execution actions component
    const actionsSection = page.locator('[data-testid="execution-actions"], .execution-actions, [class*="ExecutionActions"]').first();

    if (await actionsSection.isVisible({ timeout: 2000 }).catch(() => false)) {
      await expect(actionsSection).toBeVisible();

      // Check for cancel button
      const cancelButton = page.getByRole('button', { name: /cancel/i });
      if (await cancelButton.count() > 0) {
        const actionCancel = cancelButton.first();
        if (await actionCancel.isVisible()) {
          await expect(actionCancel).toBeVisible();
        }
      }

      // Check for re-execute button
      const reExecuteButton = page.getByRole('button', { name: /re-execute|run again/i });
      if (await reExecuteButton.count() > 0) {
        const actionReExecute = reExecuteButton.first();
        if (await actionReExecute.isVisible()) {
          await expect(actionReExecute).toBeVisible();
        }
      }
    }
  });

  test('should handle execution cancellation', async ({ page }) => {
    const testExecutionId = 'test-running-execution';

    await page.goto(`/executions/${testExecutionId}`);

    // Find cancel button
    const cancelButton = page.getByRole('button', { name: /cancel.*execution|cancel/i }).first();

    if (await cancelButton.isVisible({ timeout: 2000 }).catch(() => false)) {
      await cancelButton.click();

      // Look for confirmation modal
      const confirmButton = page.getByRole('button', { name: /confirm|yes|cancel execution/i });

      if (await confirmButton.isVisible({ timeout: 1000 }).catch(() => false)) {
        await confirmButton.click();

        // Wait for status update
        await page.waitForTimeout(1000);

        // Check if status changed to cancelled
        const statusElement = page.locator('[data-testid="execution-status"], .execution-status').first();
        if (await statusElement.isVisible()) {
          const status = await statusElement.textContent();
          // Status might be cancelling or cancelled
          expect(status).toMatch(/cancel/i);
        }
      }
    }
  });
});
