import { test, expect } from '@playwright/test';

/**
 * E2E suite for perfil-usuario — scenarios E2E-01..06.
 *
 * Test users are created via the real register API with a unique email
 * per run (user-${Date.now()}@example.com). The backend is in-memory
 * and wiped on restart, so each run registers its own users.
 *
 * E2E-06 session-clear: page.reload() drops the in-memory token
 * (NOT localStorage.clear() — the token lives only in a JS module
 * variable that disappears on full page reload).
 */

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function uniqueEmail(suffix = ''): string {
  return `user-${Date.now()}${suffix}@example.com`;
}

/** Register a new user, then log in. Returns the credentials used. */
async function registerAndLogin(
  page: import('@playwright/test').Page,
  opts?: { email?: string; username?: string; password?: string }
): Promise<{ email: string; username: string; password: string }> {
  const email = opts?.email ?? uniqueEmail();
  const username = opts?.username ?? `user${Date.now()}`;
  const password = opts?.password ?? 'testpass1';

  // Go to register screen
  await page.goto('/');
  // The app lands on login; navigate to register
  const goToRegister = page.getByTestId('go-to-register');
  if (await goToRegister.isVisible()) {
    await goToRegister.click();
  }

  // Fill registration form
  await page.getByTestId('register-email').fill(email);
  await page.getByTestId('register-username').fill(username);
  await page.getByTestId('register-password').fill(password);
  await page.getByTestId('register-submit').click();

  // After successful register, app should land on login
  await expect(page.getByTestId('login-email')).toBeVisible();

  // Fill login form
  await page.getByTestId('login-email').fill(email);
  await page.getByTestId('login-password').fill(password);
  await page.getByTestId('login-submit').click();

  // Wait for profile screen to appear
  await expect(page.getByTestId('profile-email')).toBeVisible({ timeout: 8_000 });

  return { email, username, password };
}

// ---------------------------------------------------------------------------
// E2E-01 — Register then login navigates to profile
// ---------------------------------------------------------------------------
test('E2E-01: register then login shows profile screen', async ({ page }) => {
  const { email, username } = await registerAndLogin(page);

  await expect(page.getByTestId('profile-email')).toBeVisible();
  await expect(page.getByTestId('profile-username')).toBeVisible();

  // Basic sanity: elements are present
  expect(await page.getByTestId('profile-email').textContent()).toBeTruthy();
  expect(await page.getByTestId('profile-username').textContent()).toBeTruthy();

  // Confirm the correct values are displayed (E2E-03 also covered here)
  await expect(page.getByTestId('profile-email')).toHaveText(email);
  await expect(page.getByTestId('profile-username')).toHaveText(username);
});

// ---------------------------------------------------------------------------
// E2E-02 — Profile not accessible without login
// ---------------------------------------------------------------------------
test('E2E-02: profile is not shown without a token', async ({ page }) => {
  // A fresh page has no in-memory token — app starts at login screen.
  await page.goto('/');

  // Login form should be visible — profile data must NOT be shown.
  await expect(page.getByTestId('login-email')).toBeVisible();
  await expect(page.getByTestId('profile-email')).not.toBeVisible();
});

// ---------------------------------------------------------------------------
// E2E-03 — Profile shows correct user data (API data, not hardcoded)
// ---------------------------------------------------------------------------
test('E2E-03: profile displays email and username from the API', async ({ page }) => {
  const { email, username } = await registerAndLogin(page);

  await expect(page.getByTestId('profile-email')).toHaveText(email);
  await expect(page.getByTestId('profile-username')).toHaveText(username);
});

// ---------------------------------------------------------------------------
// E2E-04 — Change password: success path
// ---------------------------------------------------------------------------
test('E2E-04: change password with correct current password shows success', async ({ page }) => {
  const password = `pass${Date.now()}`;
  await registerAndLogin(page, { password });

  // Fill the change-password form
  await page.getByTestId('pw-current').fill(password);
  await page.getByTestId('pw-new').fill('newpassword99');
  await page.getByTestId('pw-submit').click();

  // Success message must become visible
  await expect(page.getByTestId('pw-success')).toBeVisible({ timeout: 8_000 });
  await expect(page.getByTestId('pw-error')).not.toBeVisible();
});

// ---------------------------------------------------------------------------
// E2E-05 — Change password: wrong current password shows error
// ---------------------------------------------------------------------------
test('E2E-05: change password with wrong current password shows error', async ({ page }) => {
  await registerAndLogin(page);

  // Supply an incorrect current password
  await page.getByTestId('pw-current').fill('wrongpassword123');
  await page.getByTestId('pw-new').fill('newpassword99');
  await page.getByTestId('pw-submit').click();

  // Error message must become visible — no redirect, no blank page
  await expect(page.getByTestId('pw-error')).toBeVisible({ timeout: 8_000 });
  await expect(page.getByTestId('pw-success')).not.toBeVisible();
});

// ---------------------------------------------------------------------------
// E2E-06 — Login with new password after change
// ---------------------------------------------------------------------------
test('E2E-06: login with new password succeeds after password change', async ({ page }) => {
  const oldPassword = `old${Date.now()}`;
  const newPassword = `new${Date.now()}`;

  const { email } = await registerAndLogin(page, { password: oldPassword });

  // Change the password
  await page.getByTestId('pw-current').fill(oldPassword);
  await page.getByTestId('pw-new').fill(newPassword);
  await page.getByTestId('pw-submit').click();
  await expect(page.getByTestId('pw-success')).toBeVisible({ timeout: 8_000 });

  // Reload the page — in-memory token is gone, app returns to login screen
  await page.reload();
  await expect(page.getByTestId('login-email')).toBeVisible({ timeout: 8_000 });

  // Log in with the NEW password
  await page.getByTestId('login-email').fill(email);
  await page.getByTestId('login-password').fill(newPassword);
  await page.getByTestId('login-submit').click();

  // Profile screen must appear again
  await expect(page.getByTestId('profile-email')).toBeVisible({ timeout: 8_000 });
});
