import { useState } from 'react';
import type { FormEvent } from 'react';
import { apiFetch } from '../api/client';
import type { ApiError } from '../api/client';

export function ChangePasswordForm() {
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setSuccessMsg(null);
    setErrorMsg(null);
    setLoading(true);

    try {
      await apiFetch('/api/auth/me/password', {
        method: 'PUT',
        body: JSON.stringify({
          current_password: currentPassword,
          new_password: newPassword,
        }),
      });
      // 204 → apiFetch returns null, no error thrown → success
      setSuccessMsg('Password updated successfully');
      setCurrentPassword('');
      setNewPassword('');
    } catch (err) {
      const apiErr = err as ApiError;
      setErrorMsg(apiErr.detail ?? 'Failed to update password');
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="profile-card" aria-label="Change password" style={{ marginTop: 'var(--space-6)' }}>
      <h2 className="profile-card__heading">Change password</h2>

      <form onSubmit={handleSubmit} noValidate>
        <div className="form-group">
          <label htmlFor="pw-current" className="form-label">
            Current password
          </label>
          <input
            id="pw-current"
            data-testid="pw-current"
            type="password"
            className="form-input"
            value={currentPassword}
            onChange={(e) => setCurrentPassword(e.target.value)}
            required
            disabled={loading}
            autoComplete="current-password"
          />
        </div>

        <div className="form-group">
          <label htmlFor="pw-new" className="form-label">
            New password
          </label>
          <input
            id="pw-new"
            data-testid="pw-new"
            type="password"
            className="form-input"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            required
            disabled={loading}
            autoComplete="new-password"
          />
        </div>

        {successMsg && (
          <p data-testid="pw-success" className="message-success">
            {successMsg}
          </p>
        )}

        {errorMsg && (
          <p data-testid="pw-error" className="message-error">
            {errorMsg}
          </p>
        )}

        <button
          type="submit"
          data-testid="pw-submit"
          className="btn-primary"
          disabled={loading}
        >
          {loading ? 'Updating…' : 'Update password'}
        </button>
      </form>
    </section>
  );
}
