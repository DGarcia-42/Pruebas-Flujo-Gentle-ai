import { useState, useEffect } from 'react';
import { apiFetch } from '../api/client';
import type { ApiError } from '../api/client';
import { ChangePasswordForm } from './ChangePasswordForm';

interface UserProfile {
  id: string;
  email: string;
  username: string;
}

interface Props {
  /** Called when the user wants to log out (token cleared by caller). */
  onLogout: () => void;
}

export function Profile({ onLogout }: Props) {
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    apiFetch<UserProfile>('/api/auth/me')
      .then((data) => {
        if (!cancelled && data) setProfile(data);
      })
      .catch((err: ApiError) => {
        if (!cancelled) setLoadError(err.detail ?? 'Failed to load profile');
      });

    return () => {
      cancelled = true;
    };
  }, []);

  if (loadError) {
    return (
      <div className="app-shell">
        <header className="app-topbar">
          <span className="app-topbar__title">Profile</span>
        </header>
        <main className="app-content">
          <p className="message-error" data-testid="profile-load-error">
            {loadError}
          </p>
        </main>
      </div>
    );
  }

  if (!profile) {
    return (
      <div className="app-shell">
        <header className="app-topbar">
          <span className="app-topbar__title">Profile</span>
        </header>
        <main className="app-content">
          <p style={{ color: 'var(--color-ink-muted)', fontSize: 'var(--font-size-sm)' }}>
            Loading…
          </p>
        </main>
      </div>
    );
  }

  return (
    <div className="app-shell">
      <header className="app-topbar">
        <span className="app-topbar__title">Profile</span>
        <button
          type="button"
          className="topbar-action"
          data-testid="logout-btn"
          onClick={onLogout}
        >
          Sign out
        </button>
      </header>

      <main className="app-content">
        {/* Profile card */}
        <section className="profile-card" aria-label="Account details">
          <h2 className="profile-card__heading">Account details</h2>
          <dl className="profile-field-list">
            <div className="profile-field">
              <dt className="profile-field__label">Email</dt>
              <dd
                className="profile-field__value"
                data-testid="profile-email"
              >
                {profile.email}
              </dd>
            </div>
            <div className="profile-field">
              <dt className="profile-field__label">Username</dt>
              <dd
                className="profile-field__value"
                data-testid="profile-username"
              >
                {profile.username}
              </dd>
            </div>
          </dl>
        </section>

        {/* Change-password form */}
        <ChangePasswordForm />
      </main>
    </div>
  );
}
