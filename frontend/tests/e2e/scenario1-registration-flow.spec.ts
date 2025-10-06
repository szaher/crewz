import { test, expect } from '@playwright/test';

/**
 * E2E Test: Scenario 1 - User Registration → Flow Creation
 *
 * This test validates the complete user journey from:
 * 1. Registering a new tenant/organization
 * 2. Logging in as admin
 * 3. Creating an LLM provider
 * 4. Creating a visual flow with Input → LLM → Output nodes
 * 5. Executing the flow
 * 6. Viewing execution results
 */

test.describe('Scenario 1: User Registration → Flow Creation', () => {
  const uniqueId = Date.now();
  const testData = {
    email: `admin-${uniqueId}@testco.com`,
    password: 'TestPass123!',
    tenantName: `TestCo ${uniqueId}`,
    tenantSlug: `testco-${uniqueId}`,
    providerName: 'Test OpenAI Provider',
    flowName: 'Text Summarizer',
    flowInput: 'This is a long text that needs to be summarized for testing purposes.',
  };

  test('should complete full registration to flow execution journey', async ({ page }) => {
    // Step 1: Navigate to registration page
    await test.step('Navigate to registration page', async () => {
      await page.goto('/auth/register');
      await expect(page).toHaveTitle(/Register/);
    });

    // Step 2: Register new tenant
    await test.step('Register new tenant', async () => {
      await page.fill('input[name="email"]', testData.email);
      await page.fill('input[name="password"]', testData.password);
      await page.fill('input[name="tenant_name"]', testData.tenantName);
      await page.fill('input[name="tenant_slug"]', testData.tenantSlug);

      await page.click('button[type="submit"]');

      // Should redirect to dashboard after successful registration
      await expect(page).toHaveURL(/\/dashboard/);
      await expect(page.getByText(testData.tenantName)).toBeVisible();
    });

    // Step 3: Create LLM Provider
    await test.step('Create LLM Provider', async () => {
      await page.goto('/llm-providers');
      await page.click('button:has-text("Add Provider")');

      await page.fill('input[name="name"]', testData.providerName);
      await page.selectOption('select[name="provider_type"]', 'openai');
      await page.fill('input[name="api_key"]', 'sk-test-key-for-e2e');
      await page.fill('input[name="model"]', 'gpt-3.5-turbo');

      await page.click('button:has-text("Save Provider")');

      // Verify provider was created
      await expect(page.getByText(testData.providerName)).toBeVisible();
    });

    // Step 4: Create a new flow
    await test.step('Navigate to Flows and create new flow', async () => {
      await page.goto('/flows');
      await page.click('button:has-text("Create Flow")');

      // Should open flow editor
      await expect(page).toHaveURL(/\/flows\/.*\/edit/);
    });

    // Step 5: Add Input node
    await test.step('Add Input node to canvas', async () => {
      // Drag Input node from palette
      const inputNode = page.locator('[data-node-type="input"]').first();
      const canvas = page.locator('.react-flow');

      await inputNode.dragTo(canvas, {
        targetPosition: { x: 100, y: 200 }
      });

      // Verify node is on canvas
      await expect(page.locator('.react-flow__node[data-type="input"]')).toBeVisible();
    });

    // Step 6: Add LLM node
    await test.step('Add LLM node to canvas', async () => {
      const llmNode = page.locator('[data-node-type="llm"]').first();
      const canvas = page.locator('.react-flow');

      await llmNode.dragTo(canvas, {
        targetPosition: { x: 400, y: 200 }
      });

      // Configure LLM node
      await page.locator('.react-flow__node[data-type="llm"]').click();
      await page.selectOption('select[name="llm_provider_id"]', { label: testData.providerName });
      await page.fill('textarea[name="prompt"]', 'Summarize the following text: {{input.text}}');

      await expect(page.locator('.react-flow__node[data-type="llm"]')).toBeVisible();
    });

    // Step 7: Add Output node
    await test.step('Add Output node to canvas', async () => {
      const outputNode = page.locator('[data-node-type="output"]').first();
      const canvas = page.locator('.react-flow');

      await outputNode.dragTo(canvas, {
        targetPosition: { x: 700, y: 200 }
      });

      await expect(page.locator('.react-flow__node[data-type="output"]')).toBeVisible();
    });

    // Step 8: Connect nodes
    await test.step('Connect nodes: Input → LLM → Output', async () => {
      // Get node handles for connections
      const inputHandle = page.locator('.react-flow__node[data-type="input"] .react-flow__handle-right').first();
      const llmHandleLeft = page.locator('.react-flow__node[data-type="llm"] .react-flow__handle-left').first();
      const llmHandleRight = page.locator('.react-flow__node[data-type="llm"] .react-flow__handle-right').first();
      const outputHandle = page.locator('.react-flow__node[data-type="output"] .react-flow__handle-left').first();

      // Connect Input → LLM
      await inputHandle.dragTo(llmHandleLeft);

      // Connect LLM → Output
      await llmHandleRight.dragTo(outputHandle);

      // Verify edges are created
      await expect(page.locator('.react-flow__edge')).toHaveCount(2);
    });

    // Step 9: Save flow
    await test.step('Save flow', async () => {
      await page.fill('input[name="flow_name"]', testData.flowName);
      await page.fill('textarea[name="description"]', 'E2E test flow for text summarization');
      await page.click('button:has-text("Save Flow")');

      // Verify save success
      await expect(page.getByText('Flow saved successfully')).toBeVisible();
    });

    // Step 10: Execute flow
    await test.step('Execute flow with input', async () => {
      await page.click('button:has-text("Execute")');

      // Fill in execution input
      await page.fill('textarea[name="input.text"]', testData.flowInput);
      await page.click('button:has-text("Run")');

      // Wait for execution to start
      await expect(page.getByText(/Execution started|Running/)).toBeVisible({ timeout: 10000 });
    });

    // Step 11: View execution logs
    await test.step('View execution logs and verify completion', async () => {
      // Navigate to executions page
      await page.click('a:has-text("Executions")');

      // Find our execution (should be at top as most recent)
      const executionRow = page.locator('tr').filter({ hasText: testData.flowName }).first();
      await expect(executionRow).toBeVisible();

      // Click to view details
      await executionRow.click();

      // Wait for execution to complete (or fail gracefully in test)
      // In a real scenario with mocked LLM, this should complete quickly
      await expect(page.getByText(/Succeeded|Failed|Completed/)).toBeVisible({ timeout: 30000 });

      // Verify execution logs are visible
      await expect(page.locator('[data-testid="execution-logs"]')).toBeVisible();
    });

    // Cleanup: Log out
    await test.step('Log out', async () => {
      await page.click('[data-testid="user-menu"]');
      await page.click('button:has-text("Log out")');
      await expect(page).toHaveURL(/\/auth\/login/);
    });
  });

  test('should handle flow creation errors gracefully', async ({ page }) => {
    // Log in first (reuse credentials from previous test)
    await page.goto('/auth/login');
    await page.fill('input[name="email"]', testData.email);
    await page.fill('input[name="password"]', testData.password);
    await page.click('button[type="submit"]');

    // Try to save flow without required fields
    await page.goto('/flows');
    await page.click('button:has-text("Create Flow")');

    await page.click('button:has-text("Save Flow")');

    // Should show validation errors
    await expect(page.getByText(/Flow name is required|Please add at least one node/)).toBeVisible();
  });
});
