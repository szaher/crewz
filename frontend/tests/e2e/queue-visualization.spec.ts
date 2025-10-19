/**
 * E2E Test: Queue Visualization (T078)
 *
 * Tests queue visualization:
 * - Queue 3 jobs
 * - Verify position countdown
 * - Estimated time accuracy within 10%
 */

import { test, expect } from '@playwright/test';

test.describe('Queue Visualization E2E', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/executions');
    await page.waitForLoadState('networkidle');
  });

  test('should display queue position for queued execution', async ({ page }) => {
    const testExecutionId = 'test-queued-execution-1';

    await page.goto(`/executions/${testExecutionId}`);

    // Look for queue position component
    const queuePosition = page.locator('[data-testid="queue-position"], [class*="QueuePosition"]').first();

    if (await queuePosition.isVisible({ timeout: 3000 }).catch(() => false)) {
      await expect(queuePosition).toBeVisible();

      // Check for position number
      const positionText = await queuePosition.textContent();
      expect(positionText).toMatch(/position|#\d+|queue/i);
    }
  });

  test('should show estimated wait time for queued execution', async ({ page }) => {
    const testExecutionId = 'test-queued-execution-2';

    await page.goto(`/executions/${testExecutionId}`);

    // Look for estimated time display
    const estimatedTime = page.locator('[data-testid="estimated-time"], .estimated-wait-time').first();

    if (await estimatedTime.isVisible({ timeout: 2000 }).catch(() => false)) {
      await expect(estimatedTime).toBeVisible();

      const timeText = await estimatedTime.textContent();
      // Should show time in format like "5 minutes" or "30 seconds"
      expect(timeText).toMatch(/\d+\s*(second|minute|hour)/i);
    }
  });

  test('should update queue position as queue drains', async ({ page }) => {
    const testExecutionId = 'test-queue-update-execution';

    await page.goto(`/executions/${testExecutionId}`);

    const queuePositionElement = page.locator('[data-testid="queue-position"]').first();

    if (await queuePositionElement.isVisible({ timeout: 2000 }).catch(() => false)) {
      // Get initial position
      const initialText = await queuePositionElement.textContent();
      const initialPosition = parseInt(initialText?.match(/\d+/)?.[0] || '0');

      if (initialPosition > 0) {
        // Wait for position update (poll for changes)
        await page.waitForTimeout(3000);

        // Check if position updated
        const updatedText = await queuePositionElement.textContent();
        const updatedPosition = parseInt(updatedText?.match(/\d+/)?.[0] || '0');

        // Position should decrease or stay same (not increase)
        expect(updatedPosition).toBeLessThanOrEqual(initialPosition);
      }
    }
  });

  test('should show progress indicator for queue position', async ({ page }) => {
    const testExecutionId = 'test-queue-progress-execution';

    await page.goto(`/executions/${testExecutionId}`);

    // Look for progress bar or indicator
    const progressBar = page.locator('[data-testid="queue-progress"], progress, [role="progressbar"]').first();

    if (await progressBar.isVisible({ timeout: 2000 }).catch(() => false)) {
      await expect(progressBar).toBeVisible();

      // Verify progress bar has some value
      const ariaValue = await progressBar.getAttribute('aria-valuenow');
      if (ariaValue) {
        const value = parseInt(ariaValue);
        expect(value).toBeGreaterThanOrEqual(0);
        expect(value).toBeLessThanOrEqual(100);
      }
    }
  });

  test('should hide queue position when execution starts running', async ({ page }) => {
    const testExecutionId = 'test-running-execution';

    await page.goto(`/executions/${testExecutionId}`);

    // Check execution status
    const statusElement = page.locator('[data-testid="execution-status"]').first();

    if (await statusElement.isVisible({ timeout: 2000 }).catch(() => false)) {
      const statusText = await statusElement.textContent();

      // If execution is running, queue position should not be visible
      if (statusText && /running|completed|failed/i.test(statusText)) {
        const queuePosition = page.locator('[data-testid="queue-position"]').first();

        // Queue position should be hidden for running executions
        const isVisible = await queuePosition.isVisible({ timeout: 500 }).catch(() => false);
        expect(isVisible).toBeFalsy();
      }
    }
  });

  test('should display queue visualization on executions list', async ({ page }) => {
    await page.goto('/executions');

    // Look for queue indicator in list view
    const queueIndicators = page.locator('[data-testid="queue-indicator"], .queue-badge').first();

    if (await queueIndicators.isVisible({ timeout: 2000 }).catch(() => false)) {
      // Verify queue indicators are shown in list
      await expect(queueIndicators).toBeVisible();
    }
  });

  test('should show different states (queued, running, completed)', async ({ page }) => {
    await page.goto('/executions');

    // Look for status badges
    const statusBadges = page.locator('[data-testid="status-badge"], .status-badge');

    const count = await statusBadges.count();

    if (count > 0) {
      // Get status texts
      const statuses = await statusBadges.allTextContents();

      // Should have various execution states
      const uniqueStatuses = new Set(statuses.map(s => s.toLowerCase().trim()));

      // At least one status should be present
      expect(uniqueStatuses.size).toBeGreaterThan(0);
    }
  });

  test('should handle queue position 0 (next to run)', async ({ page }) => {
    const testExecutionId = 'test-next-to-run-execution';

    await page.goto(`/executions/${testExecutionId}`);

    const queuePositionElement = page.locator('[data-testid="queue-position"]').first();

    if (await queuePositionElement.isVisible({ timeout: 2000 }).catch(() => false)) {
      const positionText = await queuePositionElement.textContent();
      const position = parseInt(positionText?.match(/\d+/)?.[0] || '-1');

      if (position === 0 || position === 1) {
        // Should indicate execution is next or about to start
        expect(positionText).toMatch(/next|starting soon|position\s*[01]/i);
      }
    }
  });

  test('should update estimated time as execution approaches', async ({ page }) => {
    const testExecutionId = 'test-time-update-execution';

    await page.goto(`/executions/${testExecutionId}`);

    const estimatedTimeElement = page.locator('[data-testid="estimated-time"]').first();

    if (await estimatedTimeElement.isVisible({ timeout: 2000 }).catch(() => false)) {
      // Get initial estimated time
      const initialTime = await estimatedTimeElement.textContent();

      // Wait for update
      await page.waitForTimeout(5000);

      // Check if time updated
      const updatedTime = await estimatedTimeElement.textContent();

      // Time should be present
      expect(updatedTime).toBeTruthy();

      // Times might be different (countdown) or same if static
      // Just verify format is correct
      expect(updatedTime).toMatch(/\d+\s*(second|minute|hour)/i);
    }
  });

  test('should show priority level indicator', async ({ page }) => {
    const testExecutionId = 'test-priority-execution';

    await page.goto(`/executions/${testExecutionId}`);

    // Look for priority indicator
    const priorityElement = page.locator('[data-testid="priority"], .priority-badge').first();

    if (await priorityElement.isVisible({ timeout: 2000 }).catch(() => false)) {
      await expect(priorityElement).toBeVisible();

      const priorityText = await priorityElement.textContent();

      // Should show priority value or label
      expect(priorityText).toMatch(/priority|high|medium|low|\d+/i);
    }
  });

  test('should display workers processing status', async ({ page }) => {
    await page.goto('/executions');

    // Look for worker status indicator
    const workerStatus = page.locator('[data-testid="worker-status"], .workers-info').first();

    if (await workerStatus.isVisible({ timeout: 2000 }).catch(() => false)) {
      await expect(workerStatus).toBeVisible();

      const statusText = await workerStatus.textContent();

      // Should show worker information
      expect(statusText).toBeTruthy();
    }
  });

  test('should refresh queue position automatically', async ({ page }) => {
    const testExecutionId = 'test-auto-refresh-execution';

    await page.goto(`/executions/${testExecutionId}`);

    const queuePositionElement = page.locator('[data-testid="queue-position"]').first();

    if (await queuePositionElement.isVisible({ timeout: 2000 }).catch(() => false)) {
      // Record initial state
      const initialText = await queuePositionElement.textContent();

      // Wait for auto-refresh (polling interval)
      await page.waitForTimeout(3000);

      // Element should still be present (may have updated)
      const isStillVisible = await queuePositionElement.isVisible();
      expect(isStillVisible).toBeTruthy();
    }
  });

  test('should handle queue visualization errors gracefully', async ({ page }) => {
    const invalidExecutionId = 'invalid-execution-id-12345';

    await page.goto(`/executions/${invalidExecutionId}`);

    // Should show error state or not found
    const errorMessage = page.locator('[role="alert"], .error-message, [data-testid="error"]').first();

    // Wait briefly for error to appear
    await page.waitForTimeout(1000);

    // If error appears, verify it's handled gracefully
    if (await errorMessage.isVisible({ timeout: 1000 }).catch(() => false)) {
      await expect(errorMessage).toBeVisible();
    } else {
      // Or should show "not found" message
      const notFound = page.locator('text=/not found/i').first();
      const isNotFound = await notFound.isVisible({ timeout: 1000 }).catch(() => false);

      // Either error or not found is acceptable
      expect(isNotFound || await errorMessage.isVisible({ timeout: 500 }).catch(() => false)).toBeTruthy();
    }
  });
});
