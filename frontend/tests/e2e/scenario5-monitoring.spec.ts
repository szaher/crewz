import { test, expect } from '@playwright/test';

/**
 * E2E Test: Scenario 5 - Execution Monitoring & Cancellation
 *
 * This test validates real-time execution monitoring:
 * 1. Creating a flow with multiple nodes
 * 2. Starting flow execution
 * 3. Monitoring real-time progress via SSE
 * 4. Viewing node-by-node execution status
 * 5. Cancelling running execution
 * 6. Verifying execution logs and state
 */

test.describe('Scenario 5: Execution Monitoring & Cancellation', () => {
  const uniqueId = Date.now();
  const testData = {
    email: `monitor-${uniqueId}@exectest.com`,
    password: 'MonitorPass123!',
    tenantName: `ExecTest ${uniqueId}`,
    tenantSlug: `exectest-${uniqueId}`,
    providerName: 'Monitor Test Provider',
    flowName: 'Multi-Step Process Flow',
  };

  test.beforeEach(async ({ page }) => {
    // Register and log in
    await page.goto('/auth/register');
    await page.fill('input[name="email"]', testData.email);
    await page.fill('input[name="password"]', testData.password);
    await page.fill('input[name="tenant_name"]', testData.tenantName);
    await page.fill('input[name="tenant_slug"]', testData.tenantSlug);
    await page.click('button[type="submit"]');

    await expect(page).toHaveURL(/\/dashboard/);

    // Create LLM Provider for the flow
    await page.goto('/llm-providers');
    await page.click('button:has-text("Add Provider")');
    await page.fill('input[name="name"]', testData.providerName);
    await page.selectOption('select[name="provider_type"]', 'openai');
    await page.fill('input[name="api_key"]', 'sk-test-monitoring');
    await page.fill('input[name="model"]', 'gpt-3.5-turbo');
    await page.click('button:has-text("Save Provider")');

    await expect(page.getByText(testData.providerName)).toBeVisible();
  });

  test('should monitor real-time execution progress with SSE', async ({ page }) => {
    // Step 1: Create multi-step flow
    await test.step('Create flow with multiple LLM nodes', async () => {
      await page.goto('/flows');
      await page.click('button:has-text("Create Flow")');

      const canvas = page.locator('.react-flow');

      // Add Input node
      const inputNode = page.locator('[data-node-type="input"]').first();
      await inputNode.dragTo(canvas, { targetPosition: { x: 100, y: 200 } });

      // Add LLM Node 1
      const llmNode1 = page.locator('[data-node-type="llm"]').first();
      await llmNode1.dragTo(canvas, { targetPosition: { x: 300, y: 200 } });
      await page.locator('.react-flow__node[data-type="llm"]').first().click();
      await page.selectOption('select[name="llm_provider_id"]', { label: testData.providerName });
      await page.fill('textarea[name="prompt"]', 'Step 1: Analyze {{input.text}}');

      // Add LLM Node 2
      const llmNode2 = page.locator('[data-node-type="llm"]').first();
      await llmNode2.dragTo(canvas, { targetPosition: { x: 500, y: 200 } });
      await page.locator('.react-flow__node[data-type="llm"]').nth(1).click();
      await page.selectOption('select[name="llm_provider_id"]', { label: testData.providerName });
      await page.fill('textarea[name="prompt"]', 'Step 2: Summarize the analysis');

      // Add Output node
      const outputNode = page.locator('[data-node-type="output"]').first();
      await outputNode.dragTo(canvas, { targetPosition: { x: 700, y: 200 } });

      // Connect all nodes in sequence
      const handles = page.locator('.react-flow__handle');
      // Input -> LLM1
      await handles.nth(1).dragTo(handles.nth(2)); // input right -> llm1 left
      // LLM1 -> LLM2
      await handles.nth(3).dragTo(handles.nth(4)); // llm1 right -> llm2 left
      // LLM2 -> Output
      await handles.nth(5).dragTo(handles.nth(6)); // llm2 right -> output left

      // Save flow
      await page.fill('input[name="flow_name"]', testData.flowName);
      await page.click('button:has-text("Save Flow")');

      await expect(page.getByText('Flow saved successfully')).toBeVisible();
    });

    // Step 2: Start execution
    await test.step('Start flow execution', async () => {
      await page.click('button:has-text("Execute")');

      await page.fill('textarea[name="input.text"]', 'Test data for multi-step processing');
      await page.click('button:has-text("Run")');

      // Should show execution started
      await expect(page.getByText(/Execution started|Running/)).toBeVisible({ timeout: 10000 });
    });

    // Step 3: Monitor real-time updates
    await test.step('View real-time execution progress', async () => {
      // Navigate to execution details
      await page.click('a:has-text("View Details")');

      // Should show execution status updating in real-time
      await expect(page.locator('[data-testid="execution-status"]')).toBeVisible();

      // Watch for node status updates
      const inputNodeStatus = page.locator('[data-node-id*="input"] [data-testid="node-status"]');
      const llm1NodeStatus = page.locator('[data-node-id*="llm"]').first().locator('[data-testid="node-status"]');
      const llm2NodeStatus = page.locator('[data-node-id*="llm"]').nth(1).locator('[data-testid="node-status"]');

      // Input node should complete quickly
      await expect(inputNodeStatus).toHaveText(/completed|succeeded/i, { timeout: 5000 });

      // LLM1 should show running or completed
      await expect(llm1NodeStatus).toHaveText(/running|processing|completed/i, { timeout: 10000 });
    });

    // Step 4: View execution logs stream
    await test.step('Monitor execution logs via SSE', async () => {
      const logsContainer = page.locator('[data-testid="execution-logs"]');
      await expect(logsContainer).toBeVisible();

      // Logs should update in real-time
      // Wait for multiple log entries to appear
      await expect(logsContainer.locator('[data-testid="log-entry"]')).toHaveCount(3, { timeout: 15000 });

      // Should show node transitions
      await expect(logsContainer.getByText(/Node.*started|Node.*completed/i)).toBeVisible();
    });

    // Step 5: Verify execution completes or is running
    await test.step('Wait for execution to complete', async () => {
      const executionStatus = page.locator('[data-testid="execution-status"]');

      // Wait for final status (allow up to 60s for mock execution)
      await expect(executionStatus).toHaveText(/succeeded|completed|failed/i, { timeout: 60000 });

      // Verify all nodes have final status
      const nodeStatuses = page.locator('[data-testid="node-status"]');
      const count = await nodeStatuses.count();

      for (let i = 0; i < count; i++) {
        const status = await nodeStatuses.nth(i).textContent();
        expect(status).toMatch(/completed|succeeded|failed/i);
      }
    });
  });

  test('should allow cancelling running execution', async ({ page }) => {
    // Create simple flow
    await test.step('Create flow for cancellation test', async () => {
      await page.goto('/flows');
      await page.click('button:has-text("Create Flow")');

      const canvas = page.locator('.react-flow');

      // Simple Input -> LLM -> Output flow
      const inputNode = page.locator('[data-node-type="input"]').first();
      await inputNode.dragTo(canvas, { targetPosition: { x: 100, y: 200 } });

      const llmNode = page.locator('[data-node-type="llm"]').first();
      await llmNode.dragTo(canvas, { targetPosition: { x: 400, y: 200 } });
      await page.locator('.react-flow__node[data-type="llm"]').click();
      await page.selectOption('select[name="llm_provider_id"]', { label: testData.providerName });
      await page.fill('textarea[name="prompt"]', 'Long running task: {{input.text}}');

      const outputNode = page.locator('[data-node-type="output"]').first();
      await outputNode.dragTo(canvas, { targetPosition: { x: 700, y: 200 } });

      // Connect nodes
      const handles = page.locator('.react-flow__handle');
      await handles.nth(1).dragTo(handles.nth(2));
      await handles.nth(3).dragTo(handles.nth(4));

      await page.fill('input[name="flow_name"]', 'Cancellation Test Flow');
      await page.click('button:has-text("Save Flow")');
    });

    // Start execution
    await test.step('Start execution to be cancelled', async () => {
      await page.click('button:has-text("Execute")');
      await page.fill('textarea[name="input.text"]', 'Test data');
      await page.click('button:has-text("Run")');

      await expect(page.getByText(/Running|Execution started/)).toBeVisible({ timeout: 10000 });
    });

    // Cancel execution
    await test.step('Cancel running execution', async () => {
      // Go to execution details
      await page.click('a:has-text("View Details")');

      // Wait for execution to be definitely running
      await expect(page.locator('[data-testid="execution-status"]')).toHaveText(/running|processing/i, { timeout: 10000 });

      // Click cancel button
      await page.click('button:has-text("Cancel")');

      // Confirm cancellation if modal appears
      const confirmButton = page.locator('button:has-text("Confirm")');
      if (await confirmButton.isVisible({ timeout: 2000 })) {
        await confirmButton.click();
      }

      // Verify cancellation
      await expect(page.getByText(/Cancellation requested|Cancelling/i)).toBeVisible({ timeout: 5000 });
    });

    // Verify cancellation completed
    await test.step('Verify execution was cancelled', async () => {
      // Status should change to cancelled
      await expect(page.locator('[data-testid="execution-status"]')).toHaveText(/cancelled|canceled/i, { timeout: 20000 });

      // Check logs for cancellation timestamp
      const logs = page.locator('[data-testid="execution-logs"]');
      await expect(logs.getByText(/cancelled|cancellation/i)).toBeVisible();

      // Execution end time should be set
      await expect(page.locator('[data-testid="end-time"]')).toBeVisible();
    });
  });

  test('should display execution history and filtering', async ({ page }) => {
    // Create and execute multiple flows to build history
    await test.step('Create multiple executions', async () => {
      await page.goto('/flows');

      // Assuming we have a flow from previous tests or create one
      await page.click('button:has-text("Create Flow")');

      // Create simple flow
      const canvas = page.locator('.react-flow');
      const inputNode = page.locator('[data-node-type="input"]').first();
      await inputNode.dragTo(canvas, { targetPosition: { x: 100, y: 200 } });
      const outputNode = page.locator('[data-node-type="output"]').first();
      await outputNode.dragTo(canvas, { targetPosition: { x: 400, y: 200 } });

      // Connect
      const handles = page.locator('.react-flow__handle');
      await handles.nth(1).dragTo(handles.nth(2));

      await page.fill('input[name="flow_name"]', 'History Test Flow');
      await page.click('button:has-text("Save Flow")');

      // Execute 3 times
      for (let i = 0; i < 3; i++) {
        await page.click('button:has-text("Execute")');
        await page.fill('textarea[name="input.text"]', `Execution ${i + 1}`);
        await page.click('button:has-text("Run")');
        await page.waitForTimeout(2000); // Wait between executions
      }
    });

    // View execution history
    await test.step('View and filter execution history', async () => {
      await page.goto('/executions');

      // Should see list of executions
      const executionRows = page.locator('[data-testid="execution-row"]');
      await expect(executionRows).toHaveCount(3, { timeout: 10000 });

      // Test filtering by status
      await page.selectOption('select[name="status_filter"]', 'succeeded');
      // Count should update based on filter
      await page.waitForTimeout(1000);

      // Test filtering by date range
      await page.fill('input[name="date_from"]', new Date(Date.now() - 86400000).toISOString().split('T')[0]);
      await page.fill('input[name="date_to"]', new Date().toISOString().split('T')[0]);
      await page.click('button:has-text("Apply Filters")');

      // Should still see executions from today
      await expect(executionRows.first()).toBeVisible();
    });

    // View individual execution details
    await test.step('View execution details from history', async () => {
      const firstExecution = page.locator('[data-testid="execution-row"]').first();
      await firstExecution.click();

      // Should navigate to execution detail page
      await expect(page).toHaveURL(/\/executions\/.*$/);
      await expect(page.locator('[data-testid="execution-logs"]')).toBeVisible();
    });
  });

  test('should handle execution errors gracefully', async ({ page }) => {
    // This test would create a flow designed to fail
    // and verify error handling and display

    await page.goto('/flows');
    await page.click('button:has-text("Create Flow")');

    // Create flow with invalid configuration (e.g., missing LLM provider)
    const canvas = page.locator('.react-flow');
    const inputNode = page.locator('[data-node-type="input"]').first();
    await inputNode.dragTo(canvas, { targetPosition: { x: 100, y: 200 } });

    const llmNode = page.locator('[data-node-type="llm"]').first();
    await llmNode.dragTo(canvas, { targetPosition: { x: 400, y: 200 } });

    // Don't configure LLM node properly
    const outputNode = page.locator('[data-node-type="output"]').first();
    await outputNode.dragTo(canvas, { targetPosition: { x: 700, y: 200 } });

    await page.fill('input[name="flow_name"]', 'Error Test Flow');
    await page.click('button:has-text("Save Flow")');

    // Try to execute
    await page.click('button:has-text("Execute")');
    await page.fill('textarea[name="input.text"]', 'Test');
    await page.click('button:has-text("Run")');

    // Should show error
    await expect(page.getByText(/Error|Failed|Invalid configuration/i)).toBeVisible({ timeout: 15000 });

    // View execution details
    await page.click('a:has-text("View Details")');

    // Status should be failed
    await expect(page.locator('[data-testid="execution-status"]')).toHaveText(/failed|error/i);

    // Error message should be visible
    await expect(page.locator('[data-testid="error-message"]')).toBeVisible();
  });
});
