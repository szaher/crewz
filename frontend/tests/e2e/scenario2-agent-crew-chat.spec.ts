import { test, expect } from '@playwright/test';

/**
 * E2E Test: Scenario 2 - Agent Creation → Crew → Chat
 *
 * This test validates the complete crew interaction journey:
 * 1. Creating an AI agent with LLM provider
 * 2. Creating a crew with the agent
 * 3. Starting a chat session with the crew
 * 4. Sending messages and verifying responses
 * 5. Verifying context is maintained across messages
 */

test.describe('Scenario 2: Agent Creation → Crew → Chat', () => {
  const uniqueId = Date.now();
  const testData = {
    email: `user-${uniqueId}@crewtest.com`,
    password: 'CrewPass123!',
    tenantName: `CrewTest ${uniqueId}`,
    tenantSlug: `crewtest-${uniqueId}`,
    providerName: 'Chat Test Provider',
    agentName: 'Research Assistant',
    agentPrompt: 'You are a helpful research assistant that provides detailed and accurate information. Always cite your reasoning steps.',
    crewName: 'Research Team',
    chatMessages: [
      'What are the benefits of multi-tenant architecture?',
      'Can you elaborate on data isolation?',
    ],
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

    // Create LLM Provider
    await page.goto('/llm-providers');
    await page.click('button:has-text("Add Provider")');
    await page.fill('input[name="name"]', testData.providerName);
    await page.selectOption('select[name="provider_type"]', 'openai');
    await page.fill('input[name="api_key"]', 'sk-test-key-e2e');
    await page.fill('input[name="model"]', 'gpt-4');
    await page.click('button:has-text("Save Provider")');

    await expect(page.getByText(testData.providerName)).toBeVisible();
  });

  test('should create agent, crew, and chat successfully', async ({ page }) => {
    // Step 1: Create Agent
    await test.step('Create agent with LLM provider', async () => {
      await page.goto('/agents');
      await page.click('button:has-text("Create Agent")');

      await page.fill('input[name="name"]', testData.agentName);
      await page.fill('textarea[name="description"]', 'An AI assistant for research tasks');
      await page.fill('textarea[name="system_prompt"]', testData.agentPrompt);
      await page.selectOption('select[name="llm_provider_id"]', { label: testData.providerName });

      // Configure agent settings
      await page.fill('input[name="config.temperature"]', '0.7');
      await page.fill('input[name="config.max_tokens"]', '2000');

      await page.click('button:has-text("Save Agent")');

      // Verify agent created
      await expect(page.getByText(testData.agentName)).toBeVisible();
      await expect(page.getByText('Agent created successfully')).toBeVisible();
    });

    // Step 2: Create Crew with Agent
    await test.step('Create crew and add agent', async () => {
      await page.goto('/crews');
      await page.click('button:has-text("Create Crew")');

      await page.fill('input[name="name"]', testData.crewName);
      await page.fill('textarea[name="description"]', 'A research-focused crew for E2E testing');
      await page.selectOption('select[name="collaboration_pattern"]', 'sequential');

      // Add agent to crew
      await page.click('button:has-text("Add Agent")');
      await page.selectOption('select[name="agent_id"]', { label: testData.agentName });
      await page.click('button:has-text("Confirm")');

      // Verify agent is in crew
      await expect(page.getByText(testData.agentName)).toBeVisible();

      await page.click('button:has-text("Save Crew")');

      // Verify crew created
      await expect(page.getByText('Crew created successfully')).toBeVisible();
    });

    // Step 3: Start Chat Session
    await test.step('Navigate to chat and start new session', async () => {
      await page.goto('/chat');
      await page.click('button:has-text("New Chat")');

      // Select crew for chat
      await page.selectOption('select[name="crew_id"]', { label: testData.crewName });
      await page.click('button:has-text("Start Chat")');

      // Verify chat interface is loaded
      await expect(page.locator('[data-testid="chat-window"]')).toBeVisible();
      await expect(page.getByText(testData.crewName)).toBeVisible();
    });

    // Step 4: Send first message
    await test.step('Send first message and verify response', async () => {
      const messageInput = page.locator('textarea[placeholder*="Type a message"]');
      await messageInput.fill(testData.chatMessages[0]);
      await page.click('button[aria-label="Send message"]');

      // Verify message is sent
      await expect(page.getByText(testData.chatMessages[0])).toBeVisible();

      // Wait for agent response (with loading indicator)
      await expect(page.locator('[data-testid="typing-indicator"]')).toBeVisible({ timeout: 5000 });

      // Wait for actual response (mock or real)
      // In test environment, this should be mocked to respond quickly
      await expect(page.locator('[data-testid="assistant-message"]').first()).toBeVisible({ timeout: 30000 });

      // Verify reasoning steps are visible
      await expect(page.locator('[data-testid="execution-trace"]')).toBeVisible();
    });

    // Step 5: Send follow-up message
    await test.step('Send follow-up message to test context retention', async () => {
      const messageInput = page.locator('textarea[placeholder*="Type a message"]');
      await messageInput.fill(testData.chatMessages[1]);
      await page.click('button[aria-label="Send message"]');

      // Verify message is sent
      await expect(page.getByText(testData.chatMessages[1])).toBeVisible();

      // Wait for response
      await expect(page.locator('[data-testid="typing-indicator"]')).toBeVisible({ timeout: 5000 });
      await expect(page.locator('[data-testid="assistant-message"]').nth(1)).toBeVisible({ timeout: 30000 });

      // Verify both messages are in chat history
      const messages = page.locator('[data-testid="chat-message"]');
      await expect(messages).toHaveCount(4); // 2 user + 2 assistant messages
    });

    // Step 6: Verify tool invocations (if any)
    await test.step('Check for tool invocations in execution trace', async () => {
      const executionTrace = page.locator('[data-testid="execution-trace"]').first();
      await executionTrace.click(); // Expand trace

      // Should show agent reasoning even if no tools were invoked
      await expect(page.locator('[data-testid="agent-step"]')).toBeVisible();
    });

    // Step 7: Test chat session persistence
    await test.step('Verify chat session is saved', async () => {
      // Navigate away and back
      await page.goto('/dashboard');
      await page.goto('/chat');

      // Should see recent chat session
      await expect(page.getByText(testData.crewName)).toBeVisible();

      // Click to open session
      await page.locator(`[data-session-crew="${testData.crewName}"]`).click();

      // Verify messages are persisted
      await expect(page.getByText(testData.chatMessages[0])).toBeVisible();
      await expect(page.getByText(testData.chatMessages[1])).toBeVisible();
    });
  });

  test('should handle crew without agents gracefully', async ({ page }) => {
    await page.goto('/crews');
    await page.click('button:has-text("Create Crew")');

    await page.fill('input[name="name"]', 'Empty Crew');
    await page.fill('textarea[name="description"]', 'Test crew with no agents');

    await page.click('button:has-text("Save Crew")');

    // Should show validation error
    await expect(page.getByText(/Must have at least one agent|Crew requires agents/)).toBeVisible();
  });

  test('should allow editing agent configuration', async ({ page }) => {
    // Create agent first
    await page.goto('/agents');
    await page.click('button:has-text("Create Agent")');
    await page.fill('input[name="name"]', testData.agentName);
    await page.fill('textarea[name="system_prompt"]', 'Original prompt');
    await page.selectOption('select[name="llm_provider_id"]', { label: testData.providerName });
    await page.click('button:has-text("Save Agent")');

    // Edit agent
    await page.click(`[data-testid="edit-agent-${testData.agentName}"]`);
    await page.fill('textarea[name="system_prompt"]', 'Updated prompt for testing');
    await page.click('button:has-text("Save Changes")');

    // Verify update
    await expect(page.getByText('Agent updated successfully')).toBeVisible();
    await expect(page.getByText('Updated prompt for testing')).toBeVisible();
  });
});
