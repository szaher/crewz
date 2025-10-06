import { test, expect } from '@playwright/test';

/**
 * E2E Test: Scenario 4 - Multi-User Collaboration
 *
 * This test validates multi-tenant collaboration features:
 * 1. Admin inviting a new user
 * 2. User accepting invite and setting password
 * 3. User creating resources with assigned role
 * 4. Admin viewing shared resources
 * 5. RBAC permission enforcement
 * 6. Resource sharing and permission updates
 */

test.describe('Scenario 4: Multi-User Collaboration', () => {
  const uniqueId = Date.now();
  const testData = {
    admin: {
      email: `admin-${uniqueId}@collab.com`,
      password: 'AdminPass123!',
    },
    editor: {
      email: `editor-${uniqueId}@collab.com`,
      password: 'EditorPass123!',
    },
    viewer: {
      email: `viewer-${uniqueId}@collab.com`,
      password: 'ViewerPass123!',
    },
    tenantName: `CollabOrg ${uniqueId}`,
    tenantSlug: `collab-${uniqueId}`,
    flowName: 'Shared Test Flow',
  };

  let inviteToken: string;

  test.beforeEach(async ({ page }) => {
    // Admin registers tenant
    await page.goto('/auth/register');
    await page.fill('input[name="email"]', testData.admin.email);
    await page.fill('input[name="password"]', testData.admin.password);
    await page.fill('input[name="tenant_name"]', testData.tenantName);
    await page.fill('input[name="tenant_slug"]', testData.tenantSlug);
    await page.click('button[type="submit"]');

    await expect(page).toHaveURL(/\/dashboard/);
  });

  test('should support complete multi-user collaboration workflow', async ({ page, context }) => {
    // Step 1: Admin invites Editor
    await test.step('Admin invites editor user', async () => {
      await page.goto('/users');
      await page.click('button:has-text("Invite User")');

      await page.fill('input[name="email"]', testData.editor.email);
      await page.selectOption('select[name="role"]', 'editor');
      await page.click('button:has-text("Send Invite")');

      // Should show success message
      await expect(page.getByText('Invite sent successfully')).toBeVisible();

      // In test environment, capture invite token from UI or logs
      // For now, we'll simulate this by getting it from the invite list
      const inviteRow = page.locator(`tr:has-text("${testData.editor.email}")`);
      await expect(inviteRow).toBeVisible();

      // Click to view invite details and get token
      await inviteRow.click();
      inviteToken = await page.locator('[data-testid="invite-token"]').textContent() || '';
      expect(inviteToken).toBeTruthy();
    });

    // Step 2: Editor accepts invite (in new browser context)
    await test.step('Editor accepts invite and sets password', async () => {
      const editorPage = await context.newPage();
      await editorPage.goto(`/auth/accept-invite?token=${inviteToken}`);

      await editorPage.fill('input[name="password"]', testData.editor.password);
      await editorPage.fill('input[name="confirm_password"]', testData.editor.password);
      await editorPage.click('button:has-text("Accept Invite")');

      // Should redirect to dashboard
      await expect(editorPage).toHaveURL(/\/dashboard/);
      await expect(editorPage.getByText(testData.tenantName)).toBeVisible();

      await editorPage.close();
    });

    // Step 3: Editor logs in and creates flow
    await test.step('Editor creates a new flow', async () => {
      // Log out admin
      await page.click('[data-testid="user-menu"]');
      await page.click('button:has-text("Log out")');

      // Log in as editor
      await page.goto('/auth/login');
      await page.fill('input[name="email"]', testData.editor.email);
      await page.fill('input[name="password"]', testData.editor.password);
      await page.click('button[type="submit"]');

      await expect(page).toHaveURL(/\/dashboard/);

      // Create flow
      await page.goto('/flows');
      await page.click('button:has-text("Create Flow")');

      // Add simple input->output flow
      const inputNode = page.locator('[data-node-type="input"]').first();
      const canvas = page.locator('.react-flow');
      await inputNode.dragTo(canvas, { targetPosition: { x: 100, y: 200 } });

      const outputNode = page.locator('[data-node-type="output"]').first();
      await outputNode.dragTo(canvas, { targetPosition: { x: 400, y: 200 } });

      // Connect nodes
      const inputHandle = page.locator('.react-flow__node[data-type="input"] .react-flow__handle-right').first();
      const outputHandle = page.locator('.react-flow__node[data-type="output"] .react-flow__handle-left').first();
      await inputHandle.dragTo(outputHandle);

      // Save flow
      await page.fill('input[name="flow_name"]', testData.flowName);
      await page.click('button:has-text("Save Flow")');

      await expect(page.getByText('Flow saved successfully')).toBeVisible();
    });

    // Step 4: Editor shares flow with Admin (View permission)
    await test.step('Editor shares flow with admin (view only)', async () => {
      await page.goto('/flows');
      const flowRow = page.locator(`tr:has-text("${testData.flowName}")`);
      await flowRow.click();

      // Click share button
      await page.click('button:has-text("Share")');

      // Add admin as viewer
      await page.fill('input[name="user_email"]', testData.admin.email);
      await page.selectOption('select[name="permission"]', 'view');
      await page.click('button:has-text("Add")');

      await expect(page.getByText('Sharing updated successfully')).toBeVisible();
    });

    // Step 5: Admin logs in and views shared flow (read-only)
    await test.step('Admin views shared flow (read-only)', async () => {
      // Log out editor
      await page.click('[data-testid="user-menu"]');
      await page.click('button:has-text("Log out")');

      // Log in as admin
      await page.goto('/auth/login');
      await page.fill('input[name="email"]', testData.admin.email);
      await page.fill('input[name="password"]', testData.admin.password);
      await page.click('button[type="submit"]');

      // Go to flows - should see shared flow
      await page.goto('/flows');
      await expect(page.getByText(testData.flowName)).toBeVisible();
      await expect(page.getByText('Shared with you')).toBeVisible();

      // Open flow
      const flowRow = page.locator(`tr:has-text("${testData.flowName}")`);
      await flowRow.click();

      // Should be read-only mode
      await expect(page.getByText(/Read-only|View mode/i)).toBeVisible();

      // Try to edit - should be blocked
      const editButton = page.locator('button:has-text("Edit")');
      if (await editButton.isVisible()) {
        await editButton.click();
        await expect(page.getByText(/Permission denied|You can only view this flow/i)).toBeVisible();
      }
    });

    // Step 6: Editor updates permissions to grant Edit access
    await test.step('Editor grants edit permission to admin', async () => {
      // Log out admin
      await page.click('[data-testid="user-menu"]');
      await page.click('button:has-text("Log out")');

      // Log in as editor
      await page.goto('/auth/login');
      await page.fill('input[name="email"]', testData.editor.email);
      await page.fill('input[name="password"]', testData.editor.password);
      await page.click('button[type="submit"]');

      // Update permissions
      await page.goto('/flows');
      const flowRow = page.locator(`tr:has-text("${testData.flowName}")`);
      await flowRow.click();

      await page.click('button:has-text("Share")');

      // Update admin permission to edit
      const adminRow = page.locator(`tr:has-text("${testData.admin.email}")`);
      await adminRow.locator('select[name="permission"]').selectOption('edit');
      await page.click('button:has-text("Update Permissions")');

      await expect(page.getByText('Permissions updated successfully')).toBeVisible();
    });

    // Step 7: Admin can now edit flow
    await test.step('Admin edits flow with new permissions', async () => {
      // Log out editor
      await page.click('[data-testid="user-menu"]');
      await page.click('button:has-text("Log out")');

      // Log in as admin
      await page.goto('/auth/login');
      await page.fill('input[name="email"]', testData.admin.email);
      await page.fill('input[name="password"]', testData.admin.password);
      await page.click('button[type="submit"]');

      // Open flow
      await page.goto('/flows');
      const flowRow = page.locator(`tr:has-text("${testData.flowName}")`);
      await flowRow.click();

      // Should now have edit access
      await page.click('button:has-text("Edit")');

      // Make a change
      await page.fill('input[name="flow_name"]', `${testData.flowName} (Edited by Admin)`);
      await page.click('button:has-text("Save Flow")');

      await expect(page.getByText('Flow saved successfully')).toBeVisible();
    });
  });

  test('should enforce viewer role permissions', async ({ page, context }) => {
    // Invite viewer user
    await page.goto('/users');
    await page.click('button:has-text("Invite User")');
    await page.fill('input[name="email"]', testData.viewer.email);
    await page.selectOption('select[name="role"]', 'viewer');
    await page.click('button:has-text("Send Invite")');

    const inviteRow = page.locator(`tr:has-text("${testData.viewer.email}")`);
    await inviteRow.click();
    const viewerToken = await page.locator('[data-testid="invite-token"]').textContent() || '';

    // Accept invite
    const viewerPage = await context.newPage();
    await viewerPage.goto(`/auth/accept-invite?token=${viewerToken}`);
    await viewerPage.fill('input[name="password"]', testData.viewer.password);
    await viewerPage.fill('input[name="confirm_password"]', testData.viewer.password);
    await viewerPage.click('button:has-text("Accept Invite")');

    // Try to create flow (should be blocked)
    await viewerPage.goto('/flows');
    const createButton = viewerPage.locator('button:has-text("Create Flow")');

    // Button should be disabled or not visible for viewer
    if (await createButton.isVisible()) {
      await expect(createButton).toBeDisabled();
    } else {
      await expect(createButton).not.toBeVisible();
    }

    await viewerPage.close();
  });

  test('should prevent unauthorized access to admin functions', async ({ page }) => {
    // Invite editor
    await page.goto('/users');
    await page.click('button:has-text("Invite User")');
    await page.fill('input[name="email"]', testData.editor.email);
    await page.selectOption('select[name="role"]', 'editor');
    await page.click('button:has-text("Send Invite")');

    // Log out admin
    await page.click('[data-testid="user-menu"]');
    await page.click('button:has-text("Log out")');

    // Log in as editor (after accepting invite - simulated)
    // For this test, we'll directly try to access admin pages

    // Try to access user management (should be blocked)
    await page.goto('/users');

    // Should redirect or show error
    await expect(page.getByText(/Access denied|Permission required|Not authorized/i)).toBeVisible();
  });
});
