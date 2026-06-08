import { useState } from 'react';
import type { FormEvent } from 'react';
import { login } from '../api/client';
import { setToken } from '../auth/storage';
import type { ApiError } from '../api/client';

interface Props {
  onSuccess: () => void;
  onGoToRegister: () => void;
}

export function LoginForm({ onSuccess, onGoToRegister }: Props) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const result = await login({ email, password });
      if (result?.access_token) {
        setToken(result.access_token);
        onSuccess();
      }
    } catch (err) {
      const apiErr = err as ApiError;
      setError(apiErr.detail ?? 'Login failed');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="auth-layout">
      <div className="auth-card">
        <h1 className="auth-card__title">Sign in</h1>

        <form onSubmit={handleSubmit} noValidate>
          <div className="form-group">
            <label htmlFor="login-email" className="form-label">
              Email
            </label>
            <input
              id="login-email"
              data-testid="login-email"
              type="email"
              className="form-input"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              disabled={loading}
              autoComplete="email"
            />
          </div>

          <div className="form-group">
            <label htmlFor="login-password" className="form-label">
              Password
            </label>
            <input
              id="login-password"
              data-testid="login-password"
              type="password"
              className="form-input"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              disabled={loading}
              autoComplete="current-password"
            />
          </div>

          {error && (
            <p data-testid="login-error" className="message-error">
              {error}
            </p>
          )}

          <button
            type="submit"
            className="btn-primary"
            disabled={loading}
          >
            {loading ? 'Signing in…' : 'Sign in'}
          </button>
        </form>

        <p className="auth-switch">
          Don't have an account?{' '}
          <button
            type="button"
            data-testid="go-to-register"
            onClick={onGoToRegister}
          >
            Register
          </button>
        </p>
      </div>
    </div>
  );
}
