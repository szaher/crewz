import { test, expect } from '@playwright/test';

test.describe('Flow Creation', () => {
  test.beforeEach(async ({ page }) => {
    // Assuming user is already authenticated or we mock authentication
    await page.goto('/flows');
    await page.waitForLoadState('networkidle');
  });

  test('should display flows list page', async ({ page }) => {
    await expect(page.getByRole('heading', { name: /workflows/i })).toBeVisible();
  });

  test('should open create flow modal when Create button is clicked', async ({ page }) => {
    const createButton = page.getByRole('button', { name: /create.*flow/i });
    await createButton.click();

    await expect(page.getByText('Create New Flow')).toBeVisible();
    await expect(page.getByText('Create a workflow to orchestrate your AI agents')).toBeVisible();
  });

  test('should close modal when Cancel button is clicked', async ({ page }) => {
    const createButton = page.getByRole('button', { name: /create.*flow/i });
    await createButton.click();

    const cancelButton = page.getByRole('button', { name: /cancel/i });
    await cancelButton.click();

    await expect(page.getByText('Create New Flow')).not.toBeVisible();
  });

  test('should close modal when backdrop is clicked', async ({ page }) => {
    const createButton = page.getByRole('button', { name: /create.*flow/i });
    await createButton.click();

    // Click backdrop (fixed overlay)
    await page.locator('.fixed.bg-black').click({ position: { x: 10, y: 10 } });

    await expect(page.getByText('Create New Flow')).not.toBeVisible();
  });

  test('should show validation error for empty name', async ({ page }) => {
    const createButton = page.getByRole('button', { name: /create.*flow/i });
    await createButton.click();

    const submitButton = page.getByRole('button', { name: /create flow/i });
    await submitButton.click();

    await expect(page.getByText(/name is required/i)).toBeVisible();
  });

  test('should show validation error for short name', async ({ page }) => {
    const createButton = page.getByRole('button', { name: /create.*flow/i });
    await createButton.click();

    await page.getByLabel(/name/i).fill('ab');
    const submitButton = page.getByRole('button', { name: /create flow/i });
    await submitButton.click();

    await expect(page.getByText(/at least 3 characters/i)).toBeVisible();
  });

  test('should successfully create a flow with valid data', async ({ page }) => {
    // Intercept API call
    await page.route('**/api/v1/flows', async route => {
      if (route.request().method() === 'POST') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            id: 123,
            name: 'E2E Test Flow',
            description: 'Created via E2E test',
            nodes: [],
            edges: [],
            variables: {},
          }),
        });
      } else {
        await route.continue();
      }
    });

    const createButton = page.getByRole('button', { name: /create.*flow/i });
    await createButton.click();

    await page.getByLabel(/name/i).fill('E2E Test Flow');
    await page.getByLabel(/description/i).fill('Created via E2E test');

    const submitButton = page.getByRole('button', { name: /create flow/i });
    await submitButton.click();

    // Should redirect to flow editor
    await page.waitForURL('**/flows/123/edit');
    expect(page.url()).toContain('/flows/123/edit');
  });

  test('should display error message on API failure', async ({ page }) => {
    // Intercept API call and return error
    await page.route('**/api/v1/flows', async route => {
      if (route.request().method() === 'POST') {
        await route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({
            detail: 'Internal server error',
          }),
        });
      } else {
        await route.continue();
      }
    });

    const createButton = page.getByRole('button', { name: /create.*flow/i });
    await createButton.click();

    await page.getByLabel(/name/i).fill('Test Flow');

    const submitButton = page.getByRole('button', { name: /create flow/i });
    await submitButton.click();

    await expect(page.getByText(/failed to create flow/i)).toBeVisible();
  });

  test('should handle network error gracefully', async ({ page }) => {
    // Simulate network failure
    await page.route('**/api/v1/flows', route => route.abort('failed'));

    const createButton = page.getByRole('button', { name: /create.*flow/i });
    await createButton.click();

    await page.getByLabel(/name/i).fill('Test Flow');

    const submitButton = page.getByRole('button', { name: /create flow/i });
    await submitButton.click();

    await expect(page.getByText(/failed/i)).toBeVisible();
  });

  test('should trim whitespace from input fields', async ({ page }) => {
    let capturedRequestBody: any;

    await page.route('**/api/v1/flows', async route => {
      if (route.request().method() === 'POST') {
        capturedRequestBody = await route.request().postDataJSON();
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            id: 456,
            name: 'Trimmed Flow',
            description: 'Trimmed description',
            nodes: [],
            edges: [],
          }),
        });
      } else {
        await route.continue();
      }
    });

    const createButton = page.getByRole('button', { name: /create.*flow/i });
    await createButton.click();

    await page.getByLabel(/name/i).fill('  Trimmed Flow  ');
    await page.getByLabel(/description/i).fill('  Trimmed description  ');

    const submitButton = page.getByRole('button', { name: /create flow/i });
    await submitButton.click();

    await page.waitForURL('**/flows/456/edit');

    expect(capturedRequestBody.name).toBe('Trimmed Flow');
    expect(capturedRequestBody.description).toBe('Trimmed description');
  });

  test('should disable submit button while creating flow', async ({ page }) => {
    // Delay API response
    await page.route('**/api/v1/flows', async route => {
      if (route.request().method() === 'POST') {
        await new Promise(resolve => setTimeout(resolve, 1000));
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            id: 789,
            name: 'Delayed Flow',
            nodes: [],
            edges: [],
          }),
        });
      } else {
        await route.continue();
      }
    });

    const createButton = page.getByRole('button', { name: /create.*flow/i });
    await createButton.click();

    await page.getByLabel(/name/i).fill('Delayed Flow');

    const submitButton = page.getByRole('button', { name: /create flow/i });
    await submitButton.click();

    // Button should be disabled immediately
    await expect(submitButton).toBeDisabled();

    // Wait for navigation
    await page.waitForURL('**/flows/789/edit');
  });

  test('should allow creating flow with only required fields', async ({ page }) => {
    await page.route('**/api/v1/flows', async route => {
      if (route.request().method() === 'POST') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            id: 999,
            name: 'Minimal Flow',
            nodes: [],
            edges: [],
          }),
        });
      } else {
        await route.continue();
      }
    });

    const createButton = page.getByRole('button', { name: /create.*flow/i });
    await createButton.click();

    // Only fill name (description is optional)
    await page.getByLabel(/name/i).fill('Minimal Flow');

    const submitButton = page.getByRole('button', { name: /create flow/i });
    await submitButton.click();

    await page.waitForURL('**/flows/999/edit');
    expect(page.url()).toContain('/flows/999/edit');
  });

  test('should be keyboard accessible', async ({ page }) => {
    const createButton = page.getByRole('button', { name: /create.*flow/i });
    await createButton.click();

    // Tab through form
    await page.keyboard.press('Tab');
    await expect(page.getByLabel(/name/i)).toBeFocused();

    await page.keyboard.press('Tab');
    await expect(page.getByLabel(/description/i)).toBeFocused();

    // Type with keyboard
    await page.keyboard.type('Keyboard Test Flow');

    // Submit with Enter
    await page.keyboard.press('Enter');

    // Should show validation error (description field has focus, not submit)
    // Or should navigate if API is mocked
  });

  test('should persist data when reopening modal after error', async ({ page }) => {
    // First attempt - simulate error
    let attemptCount = 0;
    await page.route('**/api/v1/flows', async route => {
      if (route.request().method() === 'POST') {
        attemptCount++;
        if (attemptCount === 1) {
          await route.fulfill({
            status: 500,
            body: JSON.stringify({ detail: 'Server error' }),
          });
        } else {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
              id: 111,
              name: 'Retry Flow',
              nodes: [],
              edges: [],
            }),
          });
        }
      } else {
        await route.continue();
      }
    });

    const createButton = page.getByRole('button', { name: /create.*flow/i });
    await createButton.click();

    await page.getByLabel(/name/i).fill('Retry Flow');
    await page.getByLabel(/description/i).fill('Test retry');

    const submitButton = page.getByRole('button', { name: /create flow/i });
    await submitButton.click();

    // Should show error
    await expect(page.getByText(/server error/i)).toBeVisible();

    // Data should still be in form
    await expect(page.getByLabel(/name/i)).toHaveValue('Retry Flow');
    await expect(page.getByLabel(/description/i)).toHaveValue('Test retry');

    // Retry submission
    await submitButton.click();

    // Should succeed
    await page.waitForURL('**/flows/111/edit');
  });
});
