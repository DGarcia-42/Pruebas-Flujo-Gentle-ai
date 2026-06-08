import { test, expect } from '@playwright/test';

/**
 * E2E suite for detallar-tareas — scenarios E2E-07, E2E-08, E2E-09.
 *
 * Tasks are unauthenticated. The tests navigate to the tasks view directly
 * via the nav-tasks button (no login required).
 *
 * E2E-09 uses page.request.post to inject a past-date task directly through
 * the API (bypasses the create-time 422 validator). The backend accepts
 * past due_dates on update; this injection route is legitimate per design.
 *
 * Unique title per run: `Task-${Date.now()}` prevents cross-test pollution
 * in the shared in-memory store.
 */

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Navigate to the tasks view from the app's initial screen. */
async function goToTasksView(page: import('@playwright/test').Page): Promise<void> {
  await page.goto('/');
  // The app lands on the login screen for unauthenticated users.
  // The tasks view is accessible via the nav-tasks button, which is
  // present regardless of auth state (tasks are public).
  await page.getByTestId('nav-tasks').click();
  // Wait for the create-form to be visible as signal that tasks view loaded
  await expect(page.getByTestId('task-title')).toBeVisible({ timeout: 8_000 });
}

/** Inject an overdue task via API (create without due_date, then PUT with past date). */
async function createOverdueTaskViaApi(
  page: import('@playwright/test').Page,
  title: string,
  pastDate: string
): Promise<void> {
  // Step 1: Create the task without a due_date (avoids 422 on create)
  const createResponse = await page.request.post('http://localhost:8000/api/tasks', {
    data: { title },
    headers: { 'Content-Type': 'application/json' },
  });
  if (!createResponse.ok()) {
    throw new Error(`createOverdueTaskViaApi (create) failed: ${createResponse.status()} ${await createResponse.text()}`);
  }
  const task = await createResponse.json() as { id: string };

  // Step 2: Update with a past due_date — PUT has no past-date restriction per spec
  const updateResponse = await page.request.put(`http://localhost:8000/api/tasks/${task.id}`, {
    data: { due_date: pastDate },
    headers: { 'Content-Type': 'application/json' },
  });
  if (!updateResponse.ok()) {
    throw new Error(`createOverdueTaskViaApi (update) failed: ${updateResponse.status()} ${await updateResponse.text()}`);
  }
}

/** Returns yesterday's date as an ISO string (YYYY-MM-DD). */
function yesterday(): string {
  const d = new Date();
  d.setDate(d.getDate() - 1);
  return d.toISOString().split('T')[0];
}

/** Returns tomorrow's date as an ISO string (YYYY-MM-DD). */
function tomorrow(): string {
  const d = new Date();
  d.setDate(d.getDate() + 1);
  return d.toISOString().split('T')[0];
}

// ---------------------------------------------------------------------------
// E2E-07 — Create task with ALL fields, verify it appears in the list
// ---------------------------------------------------------------------------
test('E2E-07: create task with all fields appears in list with due date shown', async ({ page }) => {
  const title = `Task-E2E07-${Date.now()}`;
  const description = `Description for ${title}`;
  const dueDate = tomorrow();

  await goToTasksView(page);

  // Fill all form fields
  await page.getByTestId('task-title').fill(title);
  await page.getByTestId('task-description').fill(description);
  await page.getByTestId('task-due-date').fill(dueDate);
  await page.getByTestId('task-submit').click();

  // The task must appear in the list
  await expect(page.getByText(title)).toBeVisible({ timeout: 8_000 });

  // Description must be shown
  await expect(page.getByText(description)).toBeVisible({ timeout: 8_000 });

  // Due date must be shown (rendered via toLocaleDateString — not exact ISO)
  // Assert at least one due-date element is present for a task with a date
  const dueDateElements = page.locator('[data-testid="task-due-date-display"]');
  await expect(dueDateElements.first()).toBeVisible({ timeout: 8_000 });
});

// ---------------------------------------------------------------------------
// E2E-08 — Create task with title only, no crash on empty optional fields
// ---------------------------------------------------------------------------
test('E2E-08: create task with title only appears without optional fields', async ({ page }) => {
  const title = `Task-E2E08-${Date.now()}`;

  await goToTasksView(page);

  // Fill only the required field
  await page.getByTestId('task-title').fill(title);
  await page.getByTestId('task-submit').click();

  // Task must appear in the list
  await expect(page.getByText(title)).toBeVisible({ timeout: 8_000 });

  // The overdue badge must NOT be visible for this task row
  // (no due_date set, so it cannot be overdue)
  // We locate the task item that contains this title and assert no badge inside it
  const taskItem = page.locator('[data-testid="task-item"]').filter({ hasText: title });
  await expect(taskItem).toBeVisible({ timeout: 8_000 });
  await expect(taskItem.locator('[data-testid="badge-overdue"]')).not.toBeVisible();
  await expect(taskItem.locator('[data-testid="task-due-date-display"]')).not.toBeVisible();
});

// ---------------------------------------------------------------------------
// E2E-09 — Overdue highlight: inject past-date task via API, assert badge
// ---------------------------------------------------------------------------
test('E2E-09: task with past due_date shows overdue badge', async ({ page }) => {
  const title = `Task-E2E09-${Date.now()}`;

  // Inject a task with a past due_date via create+update (bypasses create-time 422 validator)
  await createOverdueTaskViaApi(page, title, yesterday());

  // Navigate to the tasks view
  await goToTasksView(page);

  // The task must be visible in the list
  await expect(page.getByText(title)).toBeVisible({ timeout: 8_000 });

  // The overdue badge must be present on this task item
  const taskItem = page.locator('[data-testid="task-item"]').filter({ hasText: title });
  await expect(taskItem).toBeVisible({ timeout: 8_000 });
  await expect(taskItem.locator('[data-testid="badge-overdue"]')).toBeVisible({ timeout: 8_000 });
});
